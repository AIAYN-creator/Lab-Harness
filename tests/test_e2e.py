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
SLOPE = re.compile(r"\\newcommand\{\\FitCalibrationSlope\}\{([0-9.]+)\}")


def _missing() -> str | None:
    for module, extra in (("rdkit", "chem"), ("scipy", "plots"), ("matplotlib", "plots")):
        if importlib.util.find_spec(module) is None:
            return f"needs the {extra} extra"
    for tool in ("latexmk", "pdflatex", "kpsewhich"):
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
    for figure in ("catalyst.pdf", "calibration.pdf", "mechanism.pdf"):
        assert (workspace / "figures" / figure).read_bytes().startswith(b"%PDF"), figure
    assert (workspace / "paper.pdf").read_bytes().startswith(b"%PDF")


def test_a_changed_measurement_reaches_the_number_quoted_in_the_text(workspace: Path) -> None:
    project = load_workspace(workspace)
    build(project)

    macros = workspace / "figures" / "calibration.fit.tex"
    before = SLOPE.search(macros.read_text(encoding="utf-8"))
    assert before is not None

    # Same experiment, the last point doubled: the slope has to move, and so has the PDF.
    data = workspace / "data" / "calibration.csv"
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

    calibration = [figure for figure in project.figures if figure.name == "calibration"]
    result = build(project, figures=calibration, quick=True)

    assert result.ok, result.compilation.summary if result.compilation else None
    after = SLOPE.search(macros.read_text(encoding="utf-8"))
    assert after is not None
    assert float(after.group(1)) != float(before.group(1))
    assert (workspace / "paper.pdf").read_bytes() != pdf_before


def test_the_quick_path_is_used_for_a_figure_and_is_faster(workspace: Path) -> None:
    project = load_workspace(workspace)
    build(project)
    calibration = [figure for figure in project.figures if figure.name == "calibration"]

    quick = build(project, figures=calibration, quick=True)
    full = build(project, figures=calibration, quick=False)

    assert quick.ok and full.ok
    # One pdflatex pass against latexmk, which pays for itself before it runs anything.
    assert quick.latex_seconds < full.latex_seconds
