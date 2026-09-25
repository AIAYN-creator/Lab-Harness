"""docs/cli.md is generated from the command line itself, so it cannot fall behind it."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGENERATE = (
    "uv run python -m typer labharness.cli.app utils docs --name labharness --output docs/cli.md"
)


def test_the_command_reference_is_what_the_command_line_says(tmp_path: Path) -> None:
    generated = tmp_path / "cli.md"
    subprocess.run(
        [sys.executable, "-m", "typer", "labharness.cli.app", "utils", "docs"]
        + ["--name", "labharness", "--output", str(generated)],
        check=True,
        capture_output=True,
    )

    committed = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    assert generated.read_text(encoding="utf-8") == committed, f"out of date: run {REGENERATE}"
