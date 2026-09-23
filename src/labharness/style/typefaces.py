"""The catalogue of typefaces a workspace can use, read from ``typefaces.toml``.

A typeface is data, like a journal style: what LaTeX loads, which OpenType file Matplotlib and
RDKit draw with, and which fonts it may leave in a PDF. Choosing one never touches a module.
"""

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources

from labharness.core.errors import LabHarnessError

CATALOGUE = "typefaces.toml"
MATHTEXT = ("cm", "custom")


@dataclass(frozen=True)
class Typeface:
    id: str
    name: str
    family: str
    latex_packages: tuple[str, ...]
    font_file: str
    mathtext: str
    pdf_fonts: tuple[str, ...]
    tex_package: str

    def owns_pdf_font(self, base_font: str) -> bool:
        """Whether a font found in a PDF (``ABCDEF+TeXGyreTermes-Regular``) belongs to it."""
        name = base_font.lstrip("/").split("+")[-1]
        return name.startswith(self.pdf_fonts)


@cache
def _catalogue() -> dict[str, Typeface]:
    text = resources.files("labharness.style").joinpath(CATALOGUE).read_text(encoding="utf-8")
    entries = tomllib.loads(text)
    typefaces = {}
    for key, entry in entries.items():
        if entry["mathtext"] not in MATHTEXT:  # pragma: no cover - a broken catalogue
            raise LabHarnessError(f"{CATALOGUE}: '{key}' has an unknown mathtext set")
        typefaces[key] = Typeface(
            id=key,
            name=entry["name"],
            family=entry["family"],
            latex_packages=tuple(entry["latex_packages"]),
            font_file=entry["font_file"],
            mathtext=entry["mathtext"],
            pdf_fonts=tuple(entry["pdf_fonts"]),
            tex_package=entry["tex_package"],
        )
    return typefaces


def available_typefaces() -> list[str]:
    return list(_catalogue())


def load_typeface(typeface: str) -> Typeface:
    """A typeface of the catalogue, or an error listing the ones there are."""
    try:
        return _catalogue()[typeface]
    except KeyError:
        known = ", ".join(available_typefaces())
        raise LabHarnessError(f"unknown typeface '{typeface}'. Available: {known}") from None
