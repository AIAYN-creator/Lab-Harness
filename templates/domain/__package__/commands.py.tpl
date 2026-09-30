"""The commands this package adds to the command line, if any: delete this file and its entry
point in pyproject.toml if it does not need one."""

import typer


def register(app: typer.Typer) -> None:
    @app.command("{{domain}}-hello")
    def hello() -> None:
        """Say hello, from {{domain}}."""
        typer.echo("hello from {{domain}}")
