"""Translating a style into RDKit drawing options.

RDKit is not imported here: the caller passes the ``MolDrawOptions`` object, so the core
keeps working with no extras installed.
"""

from typing import Any

from labharness.style.fonts import find_font_file
from labharness.style.tokens import Style


def apply_to_draw_options(options: Any, style: Style) -> None:
    """Apply the journal geometry and typeface to an RDKit ``MolDrawOptions``."""
    structures = style.structures

    # Fixing the bond length is what makes every structure in the document the same scale.
    options.fixedBondLength = structures.bond_length_pt
    options.bondLineWidth = structures.line_width_pt
    options.scaleBondWidth = False
    options.multipleBondOffset = structures.double_bond_offset

    # Atom labels in the document typeface, taken from the LaTeX installation.
    options.fontFile = str(find_font_file(style.typography.font_file))

    # Structures are monochrome unless a figure asks otherwise.
    options.useBWAtomPalette()
