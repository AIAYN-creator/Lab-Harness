"""{{domain}}: what LabHarness draws for this field.

This is the example that came with ``labharness new-domain``: it writes a file. Replace ``render``
with what your field draws, and keep using LabHarness's core (``labharness.core``) for what every
module needs: atomic output, reading tables, the journal's style.
"""

from pathlib import Path

from labharness.core.atomic import atomic_output


def render(output: str, text: str) -> None:
    """Write ``text`` to ``output``, so that a half-written file is never seen."""
    with atomic_output(Path(output)) as temporary:
        temporary.write_text(text, encoding="utf-8")
