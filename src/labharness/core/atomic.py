"""Writing outputs atomically.

Every module writes this way: the watcher recompiles as soon as a figure changes, and LaTeX
must never open a PDF that is still being written.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_output(output: Path) -> Iterator[Path]:
    """Yield a temporary path to write to, then move it into place.

    If the writer raises, the temporary file is removed and the previous output is left
    untouched, so a broken script never destroys the figure that was working.
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")

    try:
        yield temporary
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
