"""Rebuilding figures and the document, measuring how long each phase takes."""

import contextlib
import os
import runpy
import time
import traceback
import warnings
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from labharness.core.errors import LabHarnessError, LabHarnessWarning
from labharness.core.latex import run_pdflatex
from labharness.core.lock import DataReport, check_data
from labharness.core.manifest import Figure, Workspace
from labharness.watch.latex import CompileResult, compile_document


@dataclass(frozen=True)
class FigureResult:
    figure: Figure
    ok: bool
    seconds: float
    error: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass
class BuildResult:
    figures: list[FigureResult] = field(default_factory=list)
    compilation: CompileResult | None = None
    # What changed in data/ since it was last accepted. Reported, never blocking.
    data: DataReport = field(default_factory=DataReport)
    figures_seconds: float = 0.0
    latex_seconds: float = 0.0

    @property
    def ok(self) -> bool:
        figures_ok = all(result.ok for result in self.figures)
        return figures_ok and (self.compilation is None or self.compilation.ok)

    @property
    def total_seconds(self) -> float:
        return self.figures_seconds + self.latex_seconds


def build(
    workspace: Workspace,
    figures: Sequence[Figure] | None = None,
    compile_latex: bool = True,
    quick: bool = False,
) -> BuildResult:
    """Rebuild the given figures (all of them by default) and compile the document.

    ``quick`` takes the short path through LaTeX, which is safe when only a figure changed.
    If it fails, the full build happens anyway, so a bibliography that needed it is never
    left broken.
    """
    result = BuildResult(data=check_data(workspace.root))

    started = time.perf_counter()
    for figure in workspace.figures if figures is None else figures:
        result.figures.append(build_figure(workspace, figure))
    result.figures_seconds = time.perf_counter() - started

    if compile_latex and all(item.ok for item in result.figures):
        started = time.perf_counter()
        refresh_document_style(workspace)
        if quick:
            result.compilation = run_pdflatex(workspace.document, engine=workspace.engine)
            if not result.compilation.ok:
                result.compilation = _compile(workspace)
        else:
            result.compilation = _compile(workspace)
        result.latex_seconds = time.perf_counter() - started

    return result


def _compile(workspace: Workspace) -> CompileResult:
    return compile_document(workspace.document, workspace.builder, workspace.engine)


def refresh_document_style(workspace: Workspace) -> bool:
    """Rewrite ``labharness-style.tex`` if the workspace's journal or typeface changed.

    The file is generated, and says so in its first line; one without that line was written
    by someone, and is left alone. Returns whether it was rewritten.
    """
    from labharness.core.manifest import STYLE_NAME
    from labharness.style import load_style
    from labharness.style.latex import GENERATED_MARK, document_preamble

    path = workspace.root / STYLE_NAME
    wanted = document_preamble(load_style(workspace.journal, workspace.font))
    current = path.read_text(encoding="utf-8") if path.is_file() else None
    if current is not None and not current.startswith(GENERATED_MARK):
        return False
    if current is not None and current.splitlines() == wanted.splitlines():
        return False
    path.write_text(wanted, encoding="utf-8", newline="\n")
    return True


def build_figure(workspace: Workspace, figure: Figure) -> FigureResult:
    """Run one figure script.

    Python scripts run in this process on purpose: the watcher has already paid for
    importing RDKit, SciPy and Matplotlib, so a rebuild costs milliseconds instead of the
    second a fresh interpreter would need.
    """
    script = workspace.root / figure.script
    started = time.perf_counter()

    if not script.is_file():
        return FigureResult(figure, ok=False, seconds=0.0, error=f"{figure.script} does not exist")

    if script.suffix == ".tex":
        return _build_diagram(workspace, figure, script, started)

    if script.suffix != ".py":
        return FigureResult(
            figure, ok=False, seconds=0.0, error=f"do not know how to build {figure.script}"
        )

    from labharness.style.tokens import using_journal

    with _collecting_warnings() as collected:
        try:
            with (
                _working_directory(workspace.root),
                using_journal(workspace.journal, workspace.font),
            ):
                runpy.run_path(str(script), run_name="__main__")
        except LabHarnessError as error:  # a problem in the data or the call: the message says it
            return FigureResult(
                figure,
                ok=False,
                seconds=time.perf_counter() - started,
                error=str(error),
                warnings=tuple(collected),
            )
        except Exception:  # noqa: BLE001 - a broken script must not stop the watcher
            return FigureResult(
                figure,
                ok=False,
                seconds=time.perf_counter() - started,
                error=traceback.format_exc(limit=3),
                warnings=tuple(collected),
            )

    seconds = time.perf_counter() - started
    if not (workspace.root / figure.output).is_file():
        return FigureResult(
            figure, ok=False, seconds=seconds, error=f"{figure.script} produced no {figure.output}"
        )
    return FigureResult(figure, ok=True, seconds=seconds, warnings=tuple(collected))


@contextlib.contextmanager
def _collecting_warnings() -> Iterator[list[str]]:
    """The LabHarness warnings a figure raised, every time it is built.

    Python shows a warning once per place in the code; the watcher rebuilds the same figure
    many times, and the person has to see it on every rebuild that still has the problem.
    """
    collected: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", LabHarnessWarning)
        yield collected
    collected.extend(
        str(warning.message)
        for warning in caught
        if issubclass(warning.category, LabHarnessWarning)
    )


def _build_diagram(
    workspace: Workspace, figure: Figure, script: Path, started: float
) -> FigureResult:
    """Compile a TikZ or chemfig source through the diagrams module."""
    from labharness.modules.diagrams import render_diagram
    from labharness.style import load_style

    try:
        render_diagram(
            script,
            workspace.root / figure.output,
            style=load_style(workspace.journal, workspace.font),
            engine=workspace.engine,
        )
    except Exception as error:  # noqa: BLE001 - a broken figure must not stop the watcher
        return FigureResult(
            figure, ok=False, seconds=time.perf_counter() - started, error=str(error)
        )

    return FigureResult(figure, ok=True, seconds=time.perf_counter() - started)


@contextlib.contextmanager
def _working_directory(folder: Path) -> Iterator[None]:
    """Scripts use paths relative to the workspace, like a person would type them."""
    previous = Path.cwd()
    os.chdir(folder)
    try:
        yield
    finally:
        os.chdir(previous)
