"""Units written in column headers, and the axis labels that come from them."""

import shutil
from pathlib import Path

import pytest

from labharness.core.errors import LabHarnessError
from labharness.core.units import split_unit


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("t (min)", ("t", "min")),
        ("t [min]", ("t", "min")),
        ("t / min", ("t", "min")),
        ("ee (%)", ("ee", "%")),
        ("k_obs (s-1)", ("k_obs", "s-1")),
        ("Absorbance", ("Absorbance", None)),
        ("A/B ratio", ("A/B ratio", None)),
    ],
)
def test_the_unit_is_read_from_the_header(header: str, expected: tuple[str, str | None]) -> None:
    assert split_unit(header) == expected


@pytest.mark.skipif(
    shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution for the font"
)
def test_a_plot_takes_its_axis_labels_from_the_headers(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from labharness.modules.plots import Series, regression_plot

    source = tmp_path / "decay.csv"
    source.write_text("t / min;c (mM)\n0;1,00\n30;0,64\n60;0,41\n", encoding="utf-8")
    output = tmp_path / "decay.pdf"

    regression_plot(output, Series(csv=source, x="t / min", y="c (mM)"))

    assert output.is_file()


def test_a_header_without_a_unit_is_not_drawn_without_one(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from labharness.modules.plots import Series, regression_plot

    source = tmp_path / "decay.csv"
    source.write_text("t (min);c\n0;1,00\n30;0,64\n60;0,41\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="'c' has no unit.*y_label="):
        regression_plot(tmp_path / "decay.pdf", Series(csv=source, x="t (min)", y="c"))
