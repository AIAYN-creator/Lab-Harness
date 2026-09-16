"""Compiling the document with latexmk.

A thin wrapper over :mod:`labharness.core.latex`, which the diagrams module shares: both
compile LaTeX, one the manuscript and the other each figure on its own.
"""

from pathlib import Path

from labharness.core.latex import LatexResult, run_latexmk

CompileResult = LatexResult


def compile_document(document: Path) -> LatexResult:
    """Run latexmk once over ``document``."""
    return run_latexmk(document)
