"""Diagrams: reaction mechanisms, flowcharts and technical frameworks.

Mechanisms use chemfig with arrow pushing; flowcharts and frameworks use TikZ nodes and
paths. RDKit is never used here: it cannot draw electron-pushing arrows reliably.

Needs only a LaTeX distribution, so it ships with the core.

    from labharness.modules.diagrams import render_diagram

    render_diagram("scripts/mechanism.tex", "figures/mechanism.pdf")
"""

from labharness.modules.diagrams.tikz import build_document, render_diagram

__all__ = ["build_document", "render_diagram"]
