"""The LabHarness command line.

A thin layer: every command reads its workspace, calls into the core or the watcher, and
prints the result. No figure logic lives here, so a graphical interface can reuse the same
functions later.
"""

import time
from pathlib import Path
from typing import Annotated

import typer

from labharness import __version__
from labharness.core.errors import LabHarnessError, MissingExtraError
from labharness.core.manifest import Figure, Workspace, load_workspace
from labharness.core.templates import DEFAULT_JOURNAL
from labharness.core.workspace import create_workspace
from labharness.doctor import everything_required_passes, run_checks
from labharness.modules.chem import resolve_name
from labharness.watch.runner import BuildResult
from labharness.watch.runner import build as run_build
from labharness.watch.session import DEFAULT_DEBOUNCE_MS, Cycle, watch
from labharness.watch.viewer import open_pdf

EXIT_ERROR = 1
EXIT_MISSING_DEPENDENCY = 3

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    invoke_without_command=True,
    help="Turn raw lab data into publication-ready LaTeX figures, and keep the PDF in sync.",
)


@app.callback()
def _main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", help="Print the LabHarness version and exit.")
    ] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def init(
    path: Annotated[Path, typer.Argument(help="Where to create the workspace.")] = Path("."),
    journal: Annotated[str, typer.Option(help="Journal template to use.")] = DEFAULT_JOURNAL,
    force: Annotated[bool, typer.Option(help="Write into a folder that is not empty.")] = False,
) -> None:
    """Create a workspace: manuscript, data, scripts, figures and manifest."""
    with _reporting_errors():
        target = create_workspace(path, journal=journal, force=force)

    typer.secho(f"Workspace created in {target}", fg=typer.colors.GREEN)
    typer.echo("Next: add a figure with 'labharness add', then run 'labharness watch'.")


@app.command()
def build(
    only: Annotated[str | None, typer.Option(help="Rebuild a single figure, by name.")] = None,
    no_latex: Annotated[bool, typer.Option(help="Rebuild figures without compiling.")] = False,
) -> None:
    """Rebuild the figures and compile the document once."""
    with _reporting_errors():
        workspace = load_workspace()
        figures = _selected(workspace, only)
        result = _build(workspace, figures, compile_latex=not no_latex)

    _print_result(result)
    if not result.ok:
        raise typer.Exit(EXIT_ERROR)


@app.command("watch")
def watch_command(
    no_open: Annotated[bool, typer.Option("--no-open", help="Do not open the PDF viewer.")] = False,
    debounce: Annotated[
        int, typer.Option(help="Milliseconds used to group rapid saves.")
    ] = DEFAULT_DEBOUNCE_MS,
) -> None:
    """Watch the workspace and rebuild on every save."""
    with _reporting_errors():
        workspace = load_workspace()
        typer.secho(f"Watching {workspace.root}", fg=typer.colors.GREEN)

        first = _build(workspace, list(workspace.figures), compile_latex=True)
        _print_result(first)

        pdf = first.compilation.pdf if first.compilation is not None else None
        if not no_open and pdf is not None and not open_pdf(pdf):
            typer.secho(
                "No PDF viewer found. Install SumatraPDF (Windows) or Skim (macOS); "
                "Adobe Acrobat locks the file and stops the rebuild.",
                fg=typer.colors.YELLOW,
            )

        typer.echo("Waiting for changes. Press Ctrl+C to stop.")
        try:
            watch(workspace, on_cycle=_print_cycle, debounce_ms=debounce)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            typer.echo("Stopped.")


@app.command()
def resolve(
    name: Annotated[str, typer.Argument(help="Systematic IUPAC name, in quotes.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the SMILES.")],
) -> None:
    """Turn an IUPAC name into a SMILES file, offline, with OPSIN."""
    with _reporting_errors():
        smiles = resolve_name(name, output=output)

    typer.secho(f"{smiles}", fg=typer.colors.GREEN)
    typer.echo(f"written to {output}. Check it before using it in a figure.")


@app.command()
def doctor() -> None:
    """Check that this machine has everything LabHarness needs."""
    checks = run_checks()
    for check in checks:
        if check.ok:
            mark, colour = "OK  ", typer.colors.GREEN
        elif check.required:
            mark, colour = "FAIL", typer.colors.RED
        else:
            mark, colour = "WARN", typer.colors.YELLOW
        typer.secho(f"{mark} {check.name}: {check.detail}", fg=colour)
        if check.hint and not check.ok:
            typer.echo(f"       {check.hint}")

    if not everything_required_passes(checks):
        raise typer.Exit(EXIT_MISSING_DEPENDENCY)


def _selected(workspace: Workspace, only: str | None) -> list[Figure] | None:
    if only is None:
        return None
    chosen = [figure for figure in workspace.figures if figure.name == only]
    if not chosen:
        known = ", ".join(figure.name for figure in workspace.figures) or "none"
        raise LabHarnessError(f"no figure called '{only}' in the manifest. Known figures: {known}")
    return chosen


def _build(workspace: Workspace, figures: list[Figure] | None, compile_latex: bool) -> BuildResult:
    return run_build(workspace, figures=figures, compile_latex=compile_latex)


def _print_result(result: BuildResult) -> None:
    for figure in result.figures:
        if figure.ok:
            typer.echo(f"  {figure.figure.output}  {_ms(figure.seconds)}")
        else:
            typer.secho(f"  {figure.figure.output}  failed", fg=typer.colors.RED)
            typer.echo(f"      {figure.error}")

    compilation = result.compilation
    if compilation is not None and not compilation.ok:
        typer.secho("  LaTeX failed", fg=typer.colors.RED)
        for line in compilation.errors[:5]:
            typer.echo(f"      {line}")

    typer.echo(
        f"  figures {_ms(result.figures_seconds)}  |  latex {_ms(result.latex_seconds)}  |  "
        f"total {_ms(result.total_seconds)}"
    )


def _print_cycle(cycle: Cycle) -> None:
    changed = ", ".join(path.name for path in cycle.changed)
    typer.echo(f"\n{time.strftime('%H:%M:%S')}  {changed}")
    _print_result(cycle.result)


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms"


class _reporting_errors:
    """Turn LabHarness errors into a clear message and the right exit code."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, kind: object, error: BaseException | None, traceback: object) -> None:
        if isinstance(error, MissingExtraError):
            typer.secho(str(error), fg=typer.colors.RED)
            raise typer.Exit(EXIT_MISSING_DEPENDENCY) from None
        if isinstance(error, LabHarnessError):
            typer.secho(str(error), fg=typer.colors.RED)
            raise typer.Exit(EXIT_ERROR) from None


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
