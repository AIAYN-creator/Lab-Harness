"""The commands chemistry adds to the command line: ``resolve`` and ``library check``.

They are registered by the ``labharness.commands`` entry point, like any domain's: the core
does not know they exist.
"""

from pathlib import Path
from typing import Annotated

import typer

from labharness.cli.support import EXIT_ERROR, reporting_errors
from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME, load_workspace
from labharness.modules.chem import check as check_compound
from labharness.modules.chem import load_library, resolve_name, write_smiles
from labharness.modules.chem.library import workspace_library


def register(app: typer.Typer) -> None:
    """Add this module's commands to the command line."""
    library_app = typer.Typer(
        no_args_is_help=True,
        help="The lab's compound inventory, named by [library] in the manifest.",
    )
    app.add_typer(library_app, name="library")

    @app.command()
    def resolve(
        name: Annotated[
            str, typer.Argument(help="A compound of the lab library, or a systematic IUPAC name.")
        ],
        output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the SMILES.")],
    ) -> None:
        """Turn a name into a SMILES file, offline: the lab library first, then OPSIN."""
        with reporting_errors():
            library, problem = workspace_library()
            found = library.find(name) if library is not None else None
            if library is not None and found is not None:
                smiles = found.smiles
                source = f"from library: {library.source.name}, row {found.row} ({found.label})"
                write_smiles(output, smiles, source)
            else:
                smiles = resolve_name(name, output=output)

        if problem:
            typer.secho(f"note: {problem}", fg=typer.colors.YELLOW)
        typer.secho(f"{smiles}", fg=typer.colors.GREEN)
        typer.echo(f"{'from the lab library' if found else 'from OPSIN'}, written to {output}.")
        for finding in check_compound(found) if found else []:
            typer.secho(f"  warning: {finding}", fg=typer.colors.YELLOW)
        typer.echo("Check it before using it in a figure.")

    @library_app.command("check")
    def library_check() -> None:
        """Check every compound: unreadable SMILES, missing stereochemistry, wrong formula."""
        with reporting_errors():
            workspace = load_workspace()
            settings = workspace.library
            if settings is None:
                raise LabHarnessError(
                    f'{MANIFEST_NAME} has no [library]. Add one: file = "data/..."'
                )
            library = load_library(
                workspace.root / settings.file, settings.sheet, dict(settings.columns)
            )

        problems = [*library.rejected, *library.findings]
        typer.echo(f"{library.source.name}: {len(library.compounds)} compounds read")
        for problem in problems:
            typer.secho(f"  {problem}", fg=typer.colors.YELLOW)
        if problems:
            typer.echo(f"{len(problems)} to review. Nothing in the inventory was changed.")
            raise typer.Exit(EXIT_ERROR)
        typer.secho("Nothing to review.", fg=typer.colors.GREEN)
