"""Creating a workspace from the template."""

import shutil
from collections.abc import Sequence
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME, STYLE_NAME
from labharness.core.templates import (
    DEFAULT_JOURNAL,
    JOURNALS,
    STYLE_FILE,
    journal_template,
    template_root,
)

# What a workspace gets when no field is named: what it got before fields could be chosen.
DEFAULT_FIELDS = ("chemistry",)


def create_workspace(
    target: Path,
    journal: str = DEFAULT_JOURNAL,
    force: bool = False,
    font: str | None = None,
    fields: Sequence[str] = DEFAULT_FIELDS,
) -> Path:
    """Copy the template into ``target`` and drop in the chosen journal files.

    The workspace records its journal, and its typeface when one is chosen, in the manifest,
    and its LaTeX style is generated from them, so figures and document can never disagree
    about how they look. Next to the general rules for AI agents go the rules of each of
    ``fields``, and ``CLAUDE.md`` imports all of them.
    """
    from labharness.core.domains import fields as installed_fields
    from labharness.style.latex import document_preamble
    from labharness.style.tokens import load_style
    from labharness.style.typefaces import load_typeface

    folder = journal_template(journal)
    if font is not None:
        load_typeface(font)  # before anything is written: an unknown name lists the known ones
    known = installed_fields()
    unknown = [name for name in fields if name not in known]
    if unknown:
        raise LabHarnessError(
            f"unknown field {', '.join(map(repr, unknown))}. Installed: {', '.join(known)}"
        )
    target = target.expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise LabHarnessError(f"'{target}' is not empty. Use --force to write into it anyway.")

    # The journals folder is not part of a workspace: only the chosen journal is copied,
    # flattened into the root. Its style.toml stays in the package: it is read, not edited.
    shutil.copytree(
        template_root(),
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(JOURNALS),
    )
    for source in folder.iterdir():
        if source.name != STYLE_FILE:
            shutil.copy(source, target / source.name)

    manifest = target / MANIFEST_NAME
    if not manifest.is_file():  # pragma: no cover - template would be broken
        raise LabHarnessError(f"the template produced no {MANIFEST_NAME}")

    text = _with_settings(manifest.read_text(encoding="utf-8"), journal, font)
    manifest.write_text(text, encoding="utf-8", newline="\n")
    preamble = document_preamble(load_style(journal, font))
    (target / STYLE_NAME).write_text(preamble, encoding="utf-8", newline="\n")

    chosen = list(dict.fromkeys(fields))  # each once, in the order asked for
    for name in chosen:
        shutil.copy(known[name].rules(), target / f"AGENTS.{name}.md")
    imports = ["@AGENTS.md", *(f"@AGENTS.{name}.md" for name in chosen)]
    (target / "CLAUDE.md").write_text("\n".join(imports) + "\n", encoding="utf-8", newline="\n")
    return target


def _with_settings(manifest: str, journal: str, font: str | None) -> str:
    """Put the journal and the font at the top of the manifest, after its opening comments."""
    lines = manifest.splitlines()
    header = 0
    while header < len(lines) and lines[header].startswith("#"):
        header += 1
    entry = [f'journal = "{journal}"', *([f'font = "{font}"'] if font else [])]
    return "\n".join([*lines[:header], "", *entry, *lines[header:]]) + "\n"
