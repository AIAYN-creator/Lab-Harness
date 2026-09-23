"""Diagrams: TikZ and chemfig sources compiled on their own into vector PDFs.

Compiling each diagram separately is what keeps the document fast: the manuscript only ever
includes a finished PDF, and a mechanism that takes two LaTeX passes costs those passes once,
not on every save of the paper.
"""

import shutil
import tempfile
from pathlib import Path

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError
from labharness.core.latex import run_pdflatex
from labharness.style.latex import tikz_preamble
from labharness.style.tokens import Style, load_style

DOCUMENT = r"""\documentclass[border={border}pt]{{standalone}}
{preamble}
\begin{{document}}
{body}
\end{{document}}
"""

DEFAULT_BORDER_PT = 2


def build_document(body: str, style: Style, border_pt: float = DEFAULT_BORDER_PT) -> str:
    """Wrap a figure body in a standalone document carrying the shared style.

    The source in ``scripts/`` holds only the drawing, so a figure cannot quietly use its own
    fonts or its own bond lengths: the preamble always comes from the journal style.
    """
    return DOCUMENT.format(
        border=border_pt, preamble=tikz_preamble(style).strip(), body=body.strip()
    )


def render_diagram(
    source: Path | str,
    output: Path | str,
    style: Style | None = None,
    border_pt: float = DEFAULT_BORDER_PT,
    engine: str = "pdflatex",
) -> Path:
    """Compile a TikZ or chemfig source into ``output``, with the workspace's engine."""
    source = Path(source)
    if not source.is_file():
        raise LabHarnessError(f"'{source}' does not exist")

    style = style or load_style()
    document = build_document(source.read_text(encoding="utf-8"), style, border_pt)

    with tempfile.TemporaryDirectory(prefix="labharness-diagram-") as folder:
        working = Path(folder) / f"{source.stem}.tex"
        working.write_text(document, encoding="utf-8")

        # A standalone diagram has no bibliography and no table of contents: pdflatex, and a
        # second pass only when LaTeX asks for it, which chemfig arrows do.
        result = run_pdflatex(working, passes=3, engine=engine)
        if not result.ok or result.pdf is None:
            raise LabHarnessError(f"'{source.name}' did not compile:\n{result.summary}")

        output = Path(output)
        with atomic_output(output) as temporary:
            shutil.copyfile(result.pdf, temporary)
    return output
