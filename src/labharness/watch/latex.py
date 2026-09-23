"""Compiling the document.

A thin wrapper over :mod:`labharness.core.latex`, which the diagrams module shares: both
compile LaTeX, one the manuscript and the other each figure on its own.
"""

from pathlib import Path

from labharness.core.latex import LatexResult, run_full_build, run_latexmk
from labharness.core.manifest import DEFAULT_BUILDER

CompileResult = LatexResult


def compile_document(document: Path, builder: str = DEFAULT_BUILDER) -> LatexResult:
    """Compile ``document`` completely, with LabHarness's own passes or with latexmk."""
    if builder == "latexmk":
        return run_latexmk(document)
    return run_full_build(document)
