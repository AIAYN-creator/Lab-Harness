"""What the watcher does, as data, for a terminal, a page or an application to show.

The text ``labharness watch`` prints is one way of showing these events. ``labharness watch
--json`` writes them one per line, and the working environment of v1.5 listens to the same ones
(ADR 32). They carry paths, times and messages, never the contents of the data.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from labharness.core.manifest import Figure
from labharness.watch.runner import BuildResult

Event = dict[str, Any]


def starting(root: Path, changed: Sequence[Path], figures: Sequence[Figure]) -> list[Event]:
    """What happens before a rebuild: which files were saved, and what is rebuilt."""
    return [
        *({"event": "changed", "path": _relative(root, path)} for path in changed),
        {"event": "building", "outputs": [figure.output.as_posix() for figure in figures]},
    ]


def finished(result: BuildResult) -> list[Event]:
    """What a rebuild did: data that changed, each figure or table, and LaTeX."""
    events: list[Event] = [
        {"event": "data", "path": change.path, "message": change.message}
        for change in result.data.changes
    ]
    events += [
        {
            "event": "built",
            "output": built.figure.output.as_posix(),
            "kind": built.figure.kind,
            "ok": built.ok,
            "seconds": round(built.seconds, 3),
            "warnings": list(built.warnings),
            "error": built.error,
        }
        for built in result.figures
    ]
    if result.compilation is not None:
        events.append(
            {
                "event": "compiled",
                "ok": result.compilation.ok,
                "seconds": round(result.latex_seconds, 3),
                "errors": list(result.compilation.errors[:5]),
            }
        )
    return events


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
