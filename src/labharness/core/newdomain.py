"""``labharness new-domain``: a package for a field, ready to fill in.

The package is the template in ``templates/domain/``, with the name of the field put in. It is
an ordinary Python package that declares what it brings through entry points (ADR 31), so
nothing here touches LabHarness: this only writes a folder.
"""

import re
import unicodedata
from pathlib import Path

from labharness.core.domains import fields, figure_kinds, installed_modules
from labharness.core.errors import LabHarnessError
from labharness.core.templates import DOMAIN, template_root

PREFIX = "labharness"
SUFFIX = ".tpl"  # on the template's Python and TOML files, so no tool reads them as code


def domain_name(text: str) -> str:
    """``Arquitectura y obra`` -> ``arquitectura_y_obra``: what a Python package can be called."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-z0-9]+", "_", plain.lower()).strip("_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise LabHarnessError(
            f"'{text}' cannot be the name of a domain: letters and digits, starting with a letter"
        )
    return name


def create_domain(name: str, path: Path | None = None, force: bool = False) -> Path:
    """Write the package for ``name`` and return its folder."""
    domain = domain_name(name)
    taken = {
        *(module.name for module in installed_modules()),
        *figure_kinds(),
        *fields(),
    }
    if domain in taken:
        raise LabHarnessError(f"'{domain}' is already a module, a kind of figure or a field")

    target = path or Path(f"{PREFIX}-{domain.replace('_', '-')}")
    if target.exists() and any(target.iterdir()) and not force:
        raise LabHarnessError(f"'{target}' is not empty. Use --force to write into it anyway.")

    words = {
        "{{domain}}": domain,
        "{{package}}": f"{PREFIX}_{domain}",
        "{{distribution}}": f"{PREFIX}-{domain.replace('_', '-')}",
    }
    source = template_root(DOMAIN)
    for file in sorted(source.rglob("*")):
        if not file.is_file() or "__pycache__" in file.parts:
            continue
        relative = file.relative_to(source).as_posix().removesuffix(SUFFIX)
        relative = relative.replace("__package__", words["{{package}}"])
        relative = relative.replace("__domain__", domain)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = file.read_text(encoding="utf-8")
        for placeholder, value in words.items():
            text = text.replace(placeholder, value)
        destination.write_text(text, encoding="utf-8", newline="\n")
    return target
