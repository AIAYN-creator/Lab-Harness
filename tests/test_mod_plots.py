"""The plots module: measurements in, a fitted figure and its numbers out."""

import importlib.util
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import LabHarnessError
from labharness.modules.plots import Series, fit, read_series, regression_plot
from labharness.style import load_style

needs_plots = pytest.mark.skipif(
    importlib.util.find_spec("scipy") is None, reason="needs the plots extra"
)
needs_font = pytest.mark.skipif(
    shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution for the font"
)

# Exported by a spreadsheet in a language that uses the comma as the decimal mark.
SPANISH_CSV = (
    "conc;abs_1;abs_2;abs_3\n"
    "0,10;0,121;0,119;0,123\n"
    "0,20;0,240;0,238;0,242\n"
    "0,30;0,361;0,359;0,363\n"
    "0,40;0,478;0,476;0,480\n"
)
PLAIN_CSV = "x,y\n1,3.0\n2,5.0\n3,7.0\n4,9.0\n"


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


@needs_plots
def test_a_spreadsheet_export_with_semicolons_and_commas_is_read(tmp_path: Path) -> None:
    source = write(tmp_path / "calibration.csv", SPANISH_CSV)

    points = read_series(Series(csv=source, x="conc", y=["abs_1", "abs_2", "abs_3"]))

    assert list(points.x) == [0.1, 0.2, 0.3, 0.4]
    assert points.y[0] == pytest.approx(0.121, abs=1e-6)
    assert points.error_source == "replicates"
    assert points.error[0] == pytest.approx(0.002, abs=1e-6)


@needs_plots
def test_two_replicates_are_used_but_flagged(tmp_path: Path) -> None:
    source = write(tmp_path / "two.csv", "x;y_1;y_2\n1;1,00;1,02\n2;2,00;2,04\n")

    points = read_series(Series(csv=source, x="x", y=["y_1", "y_2"]))

    assert points.error_source == "replicates"
    assert any("weak estimate" in warning for warning in points.warnings)


@needs_plots
def test_repeated_rows_are_grouped_into_one_point_with_its_deviation(tmp_path: Path) -> None:
    source = write(tmp_path / "rows.csv", "x,y\n1,10.0\n1,10.2\n1,9.8\n2,20.0\n2,20.2\n2,19.8\n")

    points = read_series(Series(csv=source, x="x", y="y"))

    assert list(points.x) == [1.0, 2.0]
    assert points.error_source == "replicates"
    assert points.error[0] == pytest.approx(0.2, abs=1e-6)


@needs_plots
def test_without_replicates_the_error_comes_from_the_decimals_written_down(tmp_path: Path) -> None:
    source = write(tmp_path / "single.csv", "x,y\n1,0.123\n2,0.246\n3,0.369\n")

    points = read_series(Series(csv=source, x="x", y="y"))

    assert points.error_source == "resolution"
    assert all(value == pytest.approx(0.001) for value in points.error)


@needs_plots
def test_an_explicit_error_column_wins(tmp_path: Path) -> None:
    source = write(tmp_path / "explicit.csv", "x,y,y_sd\n1,10.0,0.5\n2,20.0,0.7\n")

    points = read_series(Series(csv=source, x="x", y="y", error_column="y_sd"))

    assert points.error_source == "error column"
    assert list(points.error) == [0.5, 0.7]


@needs_plots
def test_a_missing_column_lists_the_ones_that_exist(tmp_path: Path) -> None:
    source = write(tmp_path / "plain.csv", PLAIN_CSV)

    with pytest.raises(LabHarnessError, match="has no column 'nope'"):
        read_series(Series(csv=source, x="nope", y="y"))


@needs_plots
def test_a_linear_fit_recovers_the_line(tmp_path: Path) -> None:
    source = write(tmp_path / "line.csv", PLAIN_CSV)
    points = read_series(Series(csv=source, x="x", y="y"))

    result = fit(points.x, points.y, points.error, model="linear")

    assert result["slope"].value == pytest.approx(2.0, abs=1e-9)
    assert result["intercept"].value == pytest.approx(1.0, abs=1e-9)
    assert result.r_squared == pytest.approx(1.0)


@needs_plots
def test_an_exponential_is_fitted_without_linearising_it() -> None:
    numpy = pytest.importorskip("numpy")
    x = numpy.linspace(0.0, 2.0, 12)
    y = 3.0 * numpy.exp(0.75 * x)

    result = fit(x, y, None, model="exp")

    assert result["a"].value == pytest.approx(3.0, rel=1e-4)
    assert result["b"].value == pytest.approx(0.75, rel=1e-4)


@needs_plots
def test_a_custom_function_names_its_own_parameters() -> None:
    numpy = pytest.importorskip("numpy")

    def arrhenius(inverse_t: object, a: float, ea: float) -> object:
        return a * numpy.exp(-ea * numpy.asarray(inverse_t))

    x = numpy.linspace(0.002, 0.004, 10)
    y = arrhenius(x, 5.0e3, 900.0)

    result = fit(x, y, None, function=arrhenius, p0=[1.0e3, 500.0])

    assert result["ea"].value == pytest.approx(900.0, rel=1e-3)
    assert [parameter.name for parameter in result.parameters] == ["a", "ea"]


@needs_plots
def test_an_unknown_model_lists_the_ones_that_exist() -> None:
    numpy = pytest.importorskip("numpy")

    with pytest.raises(LabHarnessError, match="linear"):
        fit(numpy.array([1.0, 2.0]), numpy.array([1.0, 2.0]), None, model="sigmoid")


@needs_plots
def test_a_value_is_rounded_to_the_precision_of_its_uncertainty() -> None:
    from labharness.modules.plots.fits import Parameter

    # Two significant figures in the uncertainty, and the value to the same decimal.
    assert Parameter("k", 0.012345, 0.00042).rounded() == ("0.01235", "0.00042")
    assert Parameter("k", 12.3456, 0.21).rounded() == ("12.35", "0.21")


@needs_plots
@needs_font
def test_a_plot_is_written_at_the_journal_width_with_its_numbers(tmp_path: Path) -> None:
    style = load_style()
    source = write(tmp_path / "calibration.csv", SPANISH_CSV)

    result = regression_plot(
        output=tmp_path / "figures" / "calibration.pdf",
        series=Series(csv=source, x="conc", y=["abs_1", "abs_2", "abs_3"]),
        x_label=("Concentration", "mM"),
        y_label=("Absorbance", None),
    )

    assert result.output.read_bytes().startswith(b"%PDF")
    page = PdfReader(str(result.output)).pages[0]
    assert float(page.mediabox.width) == pytest.approx(
        style.dimensions.single_column_in * 72, abs=2
    )

    macros = result.macros.read_text(encoding="utf-8")
    assert "\\newcommand{\\FitCalibrationSlope}" in macros
    assert "\\newcommand{\\FitCalibrationSlopeError}" in macros
    assert "\\newcommand{\\FitCalibrationRSquared}" in macros


@needs_plots
@needs_font
def test_a_plot_without_axis_labels_is_refused(tmp_path: Path) -> None:
    source = write(tmp_path / "plain.csv", PLAIN_CSV)

    with pytest.raises(LabHarnessError, match="x_label is required"):
        regression_plot(
            output=tmp_path / "out.pdf",
            series=Series(csv=source, x="x", y="y"),
            x_label=("", None),
            y_label=("Signal", None),
        )


def test_a_point_in_a_semicolon_file_is_a_decimal_point(tmp_path: Path) -> None:
    source = write(tmp_path / "t.csv", "t;c\n0;1.5\n30;0.637\n")

    points = read_series(Series(csv=source, x="t", y="c"))

    assert list(points.y) == [1.5, 0.637]
