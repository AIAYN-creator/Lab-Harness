"""docs/usage.md has a section for every command, so a new one cannot be left undocumented."""

import re
from pathlib import Path
from typing import Any

import typer.main

from labharness.cli import app

USAGE = Path(__file__).resolve().parents[1] / "docs" / "usage.md"


def command_paths(command: Any, prefix: str = "") -> list[str]:
    """Every command of the command line, with its parents: ``hook install``, ``resolve``..."""
    if not hasattr(command, "commands"):  # a command, not a group of them
        return [prefix]
    paths = []
    for name, sub in command.commands.items():
        paths += command_paths(sub, f"{prefix} {name}".strip())
    return paths


def test_every_command_has_a_section_in_the_usage_guide() -> None:
    headings = set(re.findall(r"^### `labharness ([^`]+)`", USAGE.read_text("utf-8"), re.M))

    undocumented = [
        path
        for path in command_paths(typer.main.get_command(app))
        if not any(path == heading or path.startswith(f"{heading} ") for heading in headings)
    ]

    assert undocumented == []
