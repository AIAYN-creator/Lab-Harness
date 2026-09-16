"""Event-driven orchestrator behind ``labharness watch`` and ``labharness build``.

It watches the data, the scripts, the manifest and the document; rebuilds only the affected
figures; recompiles the PDF; and reports how long each phase took. Modules know nothing
about it, which is what lets a graphical interface reuse them later.
"""

from labharness.watch.latex import CompileResult, compile_document
from labharness.watch.runner import BuildResult, FigureResult, build, build_figure
from labharness.watch.session import DEFAULT_DEBOUNCE_MS, Cycle, changes_to_cycles, watch
from labharness.watch.viewer import find_viewer, open_pdf

__all__ = [
    "DEFAULT_DEBOUNCE_MS",
    "BuildResult",
    "CompileResult",
    "Cycle",
    "FigureResult",
    "build",
    "build_figure",
    "changes_to_cycles",
    "compile_document",
    "find_viewer",
    "open_pdf",
    "watch",
]
