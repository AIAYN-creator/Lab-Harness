"""The LabHarness command line.

A thin layer: every command reads its workspace, calls into the core or the watcher, and
prints the result. No figure logic lives here, so a graphical interface can reuse the same
functions later.
"""

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer

from labharness import __version__
from labharness.core.add import KINDS, add_figure
from labharness.core.errors import LabHarnessError, MissingExtraError
from labharness.core.githook import git_root, install_hook, main_check
from labharness.core.lock import LOCK_NAME
from labharness.core.lock import accept as accept_changes
from labharness.core.manifest import MANIFEST_NAME, Figure, Workspace, load_workspace
from labharness.core.templates import DEFAULT_JOURNAL
from labharness.core.workspace import create_workspace
from labharness.doctor import everything_required_passes, run_checks
from labharness.eject import eject
from labharness.modules.chem import resolve_name
from labharness.preview import DEFAULT_DPI, Preview, preview_document, preview_figures
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
hook_app = typer.Typer(
    no_args_is_help=True, help="The git hook that stops unaccepted data changes being committed."
)
app.add_typer(hook_app, name="hook")


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
    if git_root(target) is not None:
        with _reporting_errors():
            hook = install_hook(target)
        typer.echo(f"Git hook installed in {hook}: unaccepted data changes cannot be committed.")
    else:
        typer.echo("Not a git repository: after 'git init', run 'labharness hook install'.")
    typer.echo("Next: add a figure with 'labharness add', then run 'labharness watch'.")


@app.command()
def add(
    kind: Annotated[str, typer.Argument(help=f"Kind of figure: {', '.join(KINDS)}.")],
    name: Annotated[str, typer.Argument(help="Name of the script and of figures/<name>.pdf.")],
    input_files: Annotated[
        list[Path] | None,
        typer.Option("--input", help="A file the figure depends on. Repeatable."),
    ] = None,
    insert: Annotated[
        bool, typer.Option(help="Also add the figure block to paper.tex, before the references.")
    ] = False,
    edit: Annotated[bool, typer.Option(help="Open the new script in your editor.")] = False,
    force: Annotated[bool, typer.Option(help="Replace a script that already exists.")] = False,
) -> None:
    """Add a figure: write its script from a template and declare it in the manifest."""
    with _reporting_errors():
        workspace = load_workspace()
        added = add_figure(workspace, kind, name, inputs=input_files, insert=insert, force=force)

    typer.secho(f"Added {added.output.as_posix()}", fg=typer.colors.GREEN)
    typer.echo(f"  script    {added.script.as_posix()}")
    inputs = ", ".join(path.as_posix() for path in added.inputs) or "none"
    typer.echo(f"  inputs    {inputs}")
    typer.echo(f"  manifest  {MANIFEST_NAME}")
    for note in added.notes:
        typer.secho(f"  note: {note}", fg=typer.colors.YELLOW)

    if added.inserted:
        typer.echo(f"  document  figure block added to {workspace.document.name}")
    else:
        typer.echo("\nPaste this where the figure belongs in paper.tex:\n")
        typer.echo(added.latex)

    if edit:
        _open_in_editor(workspace.root / added.script)


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
def preview(
    only: Annotated[str | None, typer.Option(help="Preview a single figure, by name.")] = None,
    document: Annotated[
        bool, typer.Option(help="Also render every page of the compiled paper.pdf.")
    ] = False,
    dpi: Annotated[int, typer.Option(min=36, max=1200, help="Resolution of the images.")] = (
        DEFAULT_DPI
    ),
) -> None:
    """Render figures as PNG images, to look at them before trusting them."""
    with _reporting_errors():
        workspace = load_workspace()
        results = preview_figures(workspace, _selected(workspace, only), dpi=dpi)
        if document:
            results.append(preview_document(workspace, dpi=dpi))

    for result in results:
        _print_preview(result, workspace.root)
    if not all(result.ok for result in results):
        raise typer.Exit(EXIT_ERROR)


@app.command("eject")
def eject_command(
    target: Annotated[Path, typer.Argument(help="New folder for the standalone copy.")],
    force: Annotated[bool, typer.Option(help="Write into a folder that is not empty.")] = False,
) -> None:
    """Copy this workspace into a folder that regenerates without LabHarness."""
    with _reporting_errors():
        workspace = load_workspace()
        ejected = eject(workspace, target, force=force)

    typer.secho(f"Ejected to {ejected.target}", fg=typer.colors.GREEN)
    modules = ", ".join(ejected.modules) or "none"
    typer.echo(f"  _labharness/  core, style and the modules the scripts use: {modules}")
    typer.echo(f"  scripts       {len(ejected.scripts)} Python, {len(ejected.diagrams)} diagrams")
    typer.echo("The original workspace is untouched; keep working there with LabHarness.")


@app.command()
def accept(
    files: Annotated[list[str], typer.Argument(help="Data files whose change you accept.")],
) -> None:
    """Accept a change to a raw data file, recording who, when and what it replaced."""
    with _reporting_errors():
        workspace = load_workspace()
        accepted = accept_changes(workspace.root, files)

    for change in accepted:
        typer.secho(f"Accepted: {change.message}", fg=typer.colors.GREEN)
    typer.echo(f"Recorded in {LOCK_NAME}.")


@hook_app.command("install")
def hook_install(
    force: Annotated[
        bool, typer.Option(help="Replace a pre-commit hook LabHarness did not write.")
    ] = False,
) -> None:
    """Install the pre-commit hook in the git repository of this workspace."""
    with _reporting_errors():
        workspace = load_workspace()
        hook = install_hook(workspace.root, force=force)
    typer.secho(f"Installed {hook}", fg=typer.colors.GREEN)


@hook_app.command("check")
def hook_check() -> None:
    """What the hook runs: refuse staged data changes that were not accepted."""
    raise typer.Exit(main_check(Path.cwd()))


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
    for name in result.data.registered:
        typer.echo(f"  {name}  registered in {LOCK_NAME}")
    for change in result.data.changes:
        typer.secho(f"  {change.message}", fg=typer.colors.RED)
    if result.data.changes:
        typer.echo("      If the change is intended: labharness accept <file>")
    for figure in result.figures:
        if figure.ok:
            typer.echo(f"  {figure.figure.output}  {_ms(figure.seconds)}")
        else:
            typer.secho(f"  {figure.figure.output}  failed", fg=typer.colors.RED)
            typer.echo(f"      {figure.error}")
        for warning in figure.warnings:
            typer.secho(f"      warning: {warning}", fg=typer.colors.YELLOW)

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


def _open_in_editor(path: Path) -> None:
    """Open a script in $VISUAL or $EDITOR, or VS Code if it is installed.

    Never the operating system's default handler: on Windows that can mean running a
    ``.py`` file instead of opening it.
    """
    command = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if command:
        subprocess.run([*shlex.split(command, posix=os.name != "nt"), str(path)], check=False)
    elif shutil.which("code"):
        subprocess.run([shutil.which("code") or "code", str(path)], check=False)
    else:
        typer.secho(
            "No editor found: set the EDITOR environment variable, or open the script yourself.",
            fg=typer.colors.YELLOW,
        )


def _print_preview(result: Preview, root: Path) -> None:
    source = result.source.relative_to(root).as_posix()
    if not result.ok:
        typer.secho(f"  {source}  failed: {result.error}", fg=typer.colors.RED)
        return
    for image in result.images:
        typer.echo(f"  {source}  ->  {image.relative_to(root).as_posix()}")


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
