"""Shared style: one typeface and one set of dimensions for every figure of a document.

Style is data (the ``style.toml`` of each journal folder) translated for each engine:

- :func:`labharness.style.latex.document_preamble` and
  :func:`labharness.style.latex.tikz_preamble` for LaTeX, TikZ and chemfig;
- :func:`labharness.style.rdkit.apply_to_draw_options` for chemical structures;
- :func:`labharness.style.mpl.rcparams` for plots.

Modules never hard-code fonts, sizes or colours: they ask for them here.
"""

from labharness.core.templates import available_journals
from labharness.style.fonts import find_font_file
from labharness.style.tokens import (
    Dimensions,
    Latex,
    Plots,
    Structures,
    Style,
    Typography,
    current_journal,
    current_typeface,
    load_style,
    using_journal,
)
from labharness.style.typefaces import Typeface, available_typefaces, load_typeface

__all__ = [
    "Dimensions",
    "Latex",
    "Plots",
    "Structures",
    "Style",
    "Typeface",
    "Typography",
    "available_journals",
    "available_typefaces",
    "current_journal",
    "current_typeface",
    "find_font_file",
    "load_style",
    "load_typeface",
    "using_journal",
]
