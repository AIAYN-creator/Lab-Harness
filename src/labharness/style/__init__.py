"""Shared style: one typeface and one set of dimensions for every figure of a document.

Style is data (one file per journal under ``journals/``) translated for each engine:

- :func:`labharness.style.latex.document_preamble` and
  :func:`labharness.style.latex.tikz_preamble` for LaTeX, TikZ and chemfig;
- :func:`labharness.style.rdkit.apply_to_draw_options` for chemical structures;
- :func:`labharness.style.mpl.rcparams` for plots.

Modules never hard-code fonts, sizes or colours: they ask for them here.
"""

from labharness.style.fonts import find_font_file
from labharness.style.tokens import (
    Dimensions,
    Plots,
    Structures,
    Style,
    Typography,
    available_journals,
    load_style,
)

__all__ = [
    "Dimensions",
    "Plots",
    "Structures",
    "Style",
    "Typography",
    "available_journals",
    "find_font_file",
    "load_style",
]
