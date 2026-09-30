"""The command this domain adds to the command line."""

import typer


def register(app: typer.Typer) -> None:
    @app.command()
    def hello() -> None:
        """Say hello, from a domain."""
        typer.echo("hello from a domain")
