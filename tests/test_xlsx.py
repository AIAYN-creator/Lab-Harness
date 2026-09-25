"""Excel workbooks, read through the same reader as CSV, each cell as Excel shows it."""

from pathlib import Path

import pytest

from labharness.core.errors import LabHarnessError, LabHarnessWarning
from labharness.core.tabular import read_rows

openpyxl = pytest.importorskip("openpyxl")


def workbook(path: Path, rows: list[list[object]], formats: dict[str, str] | None = None) -> Path:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "results"
    for row in rows:
        sheet.append(row)
    for coordinate, number_format in (formats or {}).items():
        sheet[coordinate].number_format = number_format
    book.create_sheet("notes").append(["nothing to see"])
    book.save(path)
    return path


def test_a_fixed_number_format_keeps_its_trailing_zeros(tmp_path: Path) -> None:
    source = workbook(
        tmp_path / "t.xlsx",
        [["entry", "ee (%)"], [1, 0.12], [2, 0.5]],
        {"B2": "0.000", "B3": "0.000"},
    )

    read = read_rows(source)

    assert read.headers == ["entry", "ee (%)"]
    assert read.rows == [["1", "0.120"], ["2", "0.500"]]


def test_numbers_without_fixed_decimals_warn_that_zeros_may_be_lost(tmp_path: Path) -> None:
    source = workbook(tmp_path / "t.xlsx", [["t", "c"], [0, 1.0], [30, 0.64]])

    with pytest.warns(LabHarnessWarning, match="trailing zeros"):
        read = read_rows(source)

    assert read.rows == [["0", "1"], ["30", "0.64"]]


def test_a_sheet_and_a_range_are_chosen_by_name(tmp_path: Path) -> None:
    source = workbook(
        tmp_path / "t.xlsx",
        [["Instrument: HPLC-1", None, None], ["entry", "yield", "note"], [1, 92, "clean"]],
    )

    read = read_rows(source, sheet="results", cells="A2:B3")

    assert read.headers == ["entry", "yield"]
    assert read.rows == [["1", "92"]]
    with pytest.raises(LabHarnessError, match="It has: results, notes"):
        read_rows(source, sheet="summary")


def test_metadata_above_the_header_is_skipped_as_in_a_csv(tmp_path: Path) -> None:
    source = workbook(tmp_path / "t.xlsx", [["Operator: A. N. Other"], ["t", "c"], [0, 1], [5, 2]])

    with pytest.warns(LabHarnessWarning, match="skip=1"):
        read = read_rows(source)

    assert read.headers == ["t", "c"]
    assert read.header_line == 2


def test_a_formula_excel_never_calculated_stops_the_read(tmp_path: Path) -> None:
    source = workbook(tmp_path / "t.xlsx", [["a", "b"], [1, "=A2*2"]])

    with pytest.raises(LabHarnessError, match="cell B2: a formula Excel never calculated"):
        read_rows(source)


def test_a_plot_and_a_table_read_a_workbook_like_a_csv(tmp_path: Path) -> None:
    pytest.importorskip("numpy")
    from labharness.modules.plots import Series, read_series
    from labharness.modules.tables import read_table

    source = workbook(tmp_path / "t.xlsx", [["t", "c"], [0, 1], [30, 2], [60, 3]])

    assert read_table(source).column("c") == ["1", "2", "3"]
    assert list(read_series(Series(csv=source, x="t", y="c")).y) == [1.0, 2.0, 3.0]


def test_a_damaged_workbook_says_so_instead_of_crashing(tmp_path: Path) -> None:
    source = tmp_path / "t.xlsx"
    source.write_bytes(b"PK not really a workbook")

    with pytest.raises(LabHarnessError, match="not a workbook Excel could open"):
        read_rows(source)
