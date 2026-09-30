"""A toy domain: writes a file, and uses LabHarness's core to do it."""

from pathlib import Path

from labharness.core.atomic import atomic_output


def note(output: str, text: str) -> None:
    with atomic_output(Path(output)) as temporary:
        temporary.write_text(text, encoding="utf-8")
