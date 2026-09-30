"""What every command shares, and a domain's commands too: how errors are told, and exit codes."""

import typer

from labharness.core.errors import LabHarnessError, MissingExtraError

EXIT_ERROR = 1
EXIT_MISSING_DEPENDENCY = 3


class reporting_errors:
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
