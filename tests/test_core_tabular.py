"""The one reader every module uses, against what instruments and spreadsheets write."""

import warnings
from pathlib import Path

import pytest

from labharness.core.errors import LabHarnessError, LabHarnessWarning
from labharness.core.tabular import parse_decimal, read_rows

INSTRUMENT_EXPORT = """\
Instrument: HPLC-1
Operator: A. N. Other
Method: chiral_OD-H

time;signal
0,00;1,2
0,01;1,5
"""


def write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "cp1252"])
def test_every_encoding_old_software_writes_is_read(tmp_path: Path, encoding: str) -> None:
    source = write(tmp_path / "t.csv", "compuesto;ee\n(S)-éster;92\n", encoding)

    read = read_rows(source)

    assert read.headers == ["compuesto", "ee"]
    assert read.rows == [["(S)-éster", "92"]]


def test_metadata_above_the_header_is_skipped_and_reported(tmp_path: Path) -> None:
    source = write(tmp_path / "hplc.csv", INSTRUMENT_EXPORT)

    with pytest.warns(LabHarnessWarning, match="skip=4"):
        read = read_rows(source)

    assert read.headers == ["time", "signal"]
    assert read.rows == [["0,00", "1,2"], ["0,01", "1,5"]]
    assert read.header_line == 5


def test_saying_how_many_lines_to_skip_silences_the_warning(tmp_path: Path) -> None:
    source = write(tmp_path / "hplc.csv", INSTRUMENT_EXPORT)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        read = read_rows(source, skip=4)

    assert read.headers == ["time", "signal"]


def test_a_summary_row_at_the_end_stops_the_read_and_says_how_to_drop_it(tmp_path: Path) -> None:
    source = write(tmp_path / "peaks.csv", "peak;area\n1;120\n2;80\nTotal;200;100 %\n")

    with pytest.raises(LabHarnessError, match="line 4.*skip_footer=1"):
        read_rows(source)

    assert read_rows(source, skip_footer=1).rows == [["1", "120"], ["2", "80"]]


def test_short_rows_are_padded_not_dropped(tmp_path: Path) -> None:
    source = write(tmp_path / "t.csv", "a,b,c\n1,2,3\n4,5\n")

    assert read_rows(source).rows == [["1", "2", "3"], ["4", "5", ""]]


@pytest.mark.parametrize(
    ("text", "delimiter"),
    [
        ("a;b\n1,5;2,25\n", ";"),
        ("a\tb\n1,5\t2,25\n", "\t"),
        ("a|b\n1|2\n", "|"),
        ("a,b\n1.5,2\n", ","),
    ],
)
def test_the_delimiter_is_worked_out_from_the_data(
    tmp_path: Path, text: str, delimiter: str
) -> None:
    assert read_rows(write(tmp_path / "t.csv", text)).delimiter == delimiter


@pytest.mark.parametrize(
    ("text", "expected"),
    [("1,5", "1.5"), ("1.5", "1.5"), ("−0,25", "-0.25"), ("1.2e-3", "0.0012"), ("+3", "3")],
)
def test_numbers_are_read_with_either_decimal_mark(text: str, expected: str) -> None:
    number = parse_decimal(text)
    assert number is not None and number == parse_decimal(expected)


@pytest.mark.parametrize("text", ["1.234,5", "n.d.", "", "—", "nan", "inf"])
def test_what_is_not_clearly_a_number_is_not_read_as_one(text: str) -> None:
    assert parse_decimal(text) is None


def test_other_formats_are_asked_to_be_exported(tmp_path: Path) -> None:
    source = tmp_path / "t.xlsx"
    source.write_bytes(b"PK")

    with pytest.raises(LabHarnessError, match="Export it to CSV"):
        read_rows(source)
