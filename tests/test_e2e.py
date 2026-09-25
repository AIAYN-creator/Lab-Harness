"""The whole pipeline, on the workspace used for the demo.

This is the test that would have caught every integration problem found by hand: a figure
that does not reach the PDF, a fitted value that does not follow the data, a diagram the
watcher does not know how to build.
"""

import importlib.util
import re
import shutil
from pathlib import Path

import pytest

from labharness.core.manifest import load_workspace
from labharness.watch.runner import build

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo"
RATE = re.compile(r"\\newcommand\{\\FitDecayB\}\{(-?[0-9.]+)\}")


def _missing() -> str | None:
    for module, extra in (("rdkit", "chem"), ("scipy", "plots"), ("matplotlib", "plots")):
        if importlib.util.find_spec(module) is None:
            return f"needs the {extra} extra"
    for tool in ("pdflatex", "bibtex", "kpsewhich"):
        if shutil.which(tool) is None:
            return "needs a LaTeX distribution"
    return None


pytestmark = [
    pytest.mark.latex,
    pytest.mark.skipif(_missing() is not None, reason=_missing() or ""),
]


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A clean copy of the demo, so the test never writes into the repository."""
    target = tmp_path_factory.mktemp("demo")
    shutil.copytree(DEMO, target, dirs_exist_ok=True)
    for stale in (target / "figures").glob("*.pdf"):
        stale.unlink()
    return target


def test_the_demo_builds_every_kind_of_figure_into_one_document(workspace: Path) -> None:
    result = build(load_workspace(workspace))

    assert result.ok, [figure.error for figure in result.figures if not figure.ok]
    for figure in ("atenolol.pdf", "decay.pdf", "kapp.pdf", "mechanism.pdf", "iodination.pdf"):
        assert (workspace / "figures" / figure).read_bytes().startswith(b"%PDF"), figure
    assert (workspace / "paper.pdf").read_bytes().startswith(b"%PDF")


def test_a_changed_measurement_reaches_the_number_quoted_in_the_text(workspace: Path) -> None:
    project = load_workspace(workspace)
    build(project)

    macros = workspace / "figures" / "decay.fit.tex"
    before = RATE.search(macros.read_text(encoding="utf-8"))
    assert before is not None

    # Same experiment, the last point doubled: the slope has to move, and so has the PDF.
    data = workspace / "data" / "decay.csv"
    header, *rows = data.read_text(encoding="utf-8").strip().splitlines()
    columns = rows[-1].split(";")
    rows[-1] = ";".join(
        [
            columns[0],
            *[
                f"{float(value.replace(',', '.')) * 2:.3f}".replace(".", ",")
                for value in columns[1:]
            ],
        ]
    )
    data.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    pdf_before = (workspace / "paper.pdf").read_bytes()

    decay = [figure for figure in project.figures if figure.name == "decay"]
    result = build(project, figures=decay, quick=True)

    assert result.ok, result.compilation.summary if result.compilation else None
    after = RATE.search(macros.read_text(encoding="utf-8"))
    assert after is not None
    assert float(after.group(1)) != float(before.group(1))
    assert (workspace / "paper.pdf").read_bytes() != pdf_before


def test_a_rebuild_costs_one_pass_whichever_path_it_takes(workspace: Path) -> None:
    project = load_workspace(workspace)
    build(project)
    decay = [figure for figure in project.figures if figure.name == "decay"]

    quick = build(project, figures=decay, quick=True)
    full = build(project, figures=decay, quick=False)

    assert quick.ok and full.ok
    assert quick.compilation is not None and full.compilation is not None
    # A figure changed, nothing new was cited: one pass either way, and no BibTeX. latexmk
    # used to spend a second deciding that before running anything.
    assert quick.compilation.passes == 1
    assert full.compilation.passes == 1
    assert not full.compilation.bibliography
