"""Translating a style into Matplotlib settings.

Matplotlib is not imported here: the caller passes the module, so the core keeps working
with no extras installed.
"""

from types import ModuleType
from typing import Any

from labharness.style.fonts import find_font_file
from labharness.style.tokens import Style


def rcparams(style: Style, width_in: float | None = None) -> dict[str, Any]:
    """Matplotlib ``rcParams`` for a figure of this journal.

    The figure is built at its final printed size, so it is included without scaling and its
    text ends up exactly the size asked for here.
    """
    typography = style.typography
    plots = style.plots
    width = width_in if width_in is not None else style.dimensions.single_column_in

    return {
        # Same typeface as the document. No usetex: it would cost seconds per figure.
        "font.family": "serif",
        "font.serif": [typography.family],
        **_mathtext(typography.mathtext, typography.family),
        "font.size": typography.base_size_pt,
        "axes.labelsize": typography.base_size_pt,
        "axes.titlesize": typography.base_size_pt,
        "legend.fontsize": typography.small_size_pt,
        "xtick.labelsize": typography.small_size_pt,
        "ytick.labelsize": typography.small_size_pt,
        "axes.grid": plots.grid,
        "axes.linewidth": plots.line_width_pt,
        "lines.linewidth": plots.line_width_pt,
        "lines.markersize": plots.marker_size_pt,
        "xtick.major.width": plots.line_width_pt,
        "ytick.major.width": plots.line_width_pt,
        "errorbar.capsize": plots.error_capsize_pt,
        "figure.figsize": (width, width / style.dimensions.aspect_ratio),
        # Keeps the requested size instead of cropping to the content, and still avoids
        # clipped labels.
        "figure.constrained_layout.use": True,
        # Embed the fonts as TrueType so the PDF is self-contained and searchable.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.transparent": False,
    }


def _mathtext(fontset: str, family: str) -> dict[str, Any]:
    """Maths in the same typeface: a built-in set when one matches, the family otherwise."""
    if fontset != "custom":
        return {"mathtext.fontset": fontset}
    return {
        "mathtext.fontset": "custom",
        "mathtext.rm": family,
        "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold",
    }


def palette(style: Style) -> list[str]:
    """Series colours, in order. Readable with any colour vision deficiency."""
    return list(style.plots.palette)


def apply(matplotlib: ModuleType, style: Style, width_in: float | None = None) -> None:
    """Register the document typeface with Matplotlib and apply the style.

    Setting ``font.serif`` is not enough: Matplotlib only knows the fonts in its own
    registry, so the file has to be handed to it first or it silently falls back to its
    default face and the figure stops matching the document.
    """
    typography = style.typography
    font = find_font_file(typography.font_file, typography.tex_package)
    matplotlib.font_manager.fontManager.addfont(str(font))
    # The italic and bold faces too, when they sit next to the regular one: maths is set in
    # italic, and without them Matplotlib fakes both from the upright face.
    for face in ("Italic", "Bold"):
        sibling = font.with_name(
            font.name.replace("Regular", face).replace("regular", face.lower())
        )
        if sibling != font and sibling.is_file():
            matplotlib.font_manager.fontManager.addfont(str(sibling))
    matplotlib.rcParams.update(rcparams(style, width_in=width_in))
