"""The watch loop: react to every save, rebuild only what changed, recompile."""

import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from labharness.core.manifest import Figure, Workspace
from labharness.watch.runner import BuildResult, build

DEFAULT_DEBOUNCE_MS = 100


@dataclass(frozen=True)
class Cycle:
    """One save and everything it caused."""

    changed: tuple[Path, ...]
    rebuilt: tuple[Figure, ...]
    result: BuildResult
    started_at: float

    @property
    def total_seconds(self) -> float:
        return self.result.total_seconds


def changes_to_cycles(
    workspace: Workspace,
    change_batches: Iterable[set[Path]],
) -> Iterator[Cycle]:
    """Turn batches of changed paths into rebuilds.

    Kept separate from the file watcher so the whole reaction can be tested without
    touching the filesystem clock.
    """
    for batch in change_batches:
        started = time.perf_counter()
        affected: list[Figure] = []
        for path in sorted(batch):
            for figure in workspace.figures_affected_by(path):
                if figure not in affected:
                    affected.append(figure)

        document_changed = any(path.name == workspace.document.name for path in batch)
        if not affected and not document_changed:
            continue

        result = build(workspace, figures=affected, compile_latex=True)
        yield Cycle(
            changed=tuple(sorted(batch)),
            rebuilt=tuple(affected),
            result=result,
            started_at=started,
        )


def watch(
    workspace: Workspace,
    on_cycle: Callable[[Cycle], None],
    debounce_ms: int = DEFAULT_DEBOUNCE_MS,
    stop: Callable[[], bool] | None = None,
) -> None:
    """Watch the workspace until interrupted, calling ``on_cycle`` after every rebuild.

    Events, not polling: nothing is checked on a timer, so the only delay between saving a
    file and rebuilding is the debounce that groups editors which save in two steps.
    """
    from watchfiles import watch as watch_files

    paths = [path for path in workspace.watched_paths if path.exists()]
    batches = (
        {Path(path) for _, path in changes}
        for changes in watch_files(*paths, debounce=debounce_ms, step=10)
    )

    for cycle in changes_to_cycles(workspace, batches):
        on_cycle(cycle)
        if stop is not None and stop():
            return
