"""Tables: any table written in LaTeX as it is, and changed only on request."""

import shutil
import subprocess
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from labharness.core import LabHarnessError, create_workspace
from labharness.modules.tables import (
    from_rows,
    read_table,
    round_significant,
    write_table,
)

# Exported by a Spanish Excel: semicolons, decimal commas, an empty cell, a note column.
OPTIMISATION = """entry;catalyst;solvent;T (°C);conversion (%);ee (%);ee_err;note
1;L1;toluene;25;95;92,347;1,2;
2;L1;THF;25;88;85,0;0,5;
3;L2;toluene;0;99;97;;at 0 °C for 48 h
4;L2;toluene;-20;;96,4;0,31;at 0 °C for 48 h
"""


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "optimisation.csv"
    path.write_text(OPTIMISATION, encoding="utf-8")
    return path


def body(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index(r"\midrule") + 1
    return [line for line in lines[start:] if not line.startswith("\\")]


# --- as it is ------------------------------------------------------------------------------


def test_a_table_is_written_exactly_as_it_was_given(csv_file: Path, tmp_path: Path) -> None:
    out = write_table(read_table(csv_file), tmp_path / "t.tex")

    rows = body(out)
    # 92,347 stays 92.347 and 97 stays 97: nothing is rounded, padded or recomputed.
    assert rows[0] == "1 & L1 & toluene & 25 & 95 & 92.347 & 1.2 & {---} \\\\"
    assert rows[2].startswith("3 & L2 & toluene & 0 & 99 & 97 & {---} & at 0 °C for 48 h")
    assert "{T (°C)}" in out.read_text(encoding="utf-8")  # units in the header, as written


def test_no_column_is_assumed(tmp_path: Path) -> None:
    # Anything at all: no R², no parameters, no expected headers.
    table = from_rows(
        ["Sample", "Colour", "Mass / g"], [["A", "red", "1.0"], ["B", "blue", "2.25"]]
    )

    text = write_table(table, tmp_path / "t.tex").read_text(encoding="utf-8")

    assert r"\begin{tabular}{l l S[table-format=1.2]}" in text
    assert "A & red & 1.0 \\\\" in text


def test_text_is_escaped_and_maths_left_alone(tmp_path: Path) -> None:
    table = from_rows(["name", "x"], [["A & B_1", "1"], ["$\\alpha$-pinene", "2"]])

    text = write_table(table, tmp_path / "t.tex").read_text(encoding="utf-8")

    assert "A \\& B\\_1" in text and "$\\alpha$-pinene" in text


@pytest.mark.parametrize(
    ("raw", "encoding"),
    [("utf-8", "utf-8"), ("utf-16", "utf-16"), ("cp1252", "cp1252")],
)
def test_old_and_new_encodings_are_read(tmp_path: Path, raw: str, encoding: str) -> None:
    path = tmp_path / "t.csv"
    path.write_bytes("T (°C);ee (%)\n25;92,3\n".encode(encoding))

    table = read_table(path)

    assert table.headers == ("T (°C)", "ee (%)")
    assert table.rows == (("25", "92,3"),)


def test_metadata_lines_before_the_header_can_be_skipped(tmp_path: Path) -> None:
    path = tmp_path / "hplc.txt"
    path.write_text("Instrument: HPLC-2\nOperator: X\nt\tarea\n1.2\t450\n", encoding="utf-8")

    assert read_table(path, skip=2).headers == ("t", "area")


def test_a_file_that_is_not_a_text_table_asks_for_a_csv(tmp_path: Path) -> None:
    path = tmp_path / "results.xlsx"
    path.write_bytes(b"PK")

    with pytest.raises(LabHarnessError, match="Export it to CSV"):
        read_table(path)


# --- changed on request ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "figures", "rule", "expected"),
    [
        ("2.345", 2, ROUND_HALF_UP, "2.3"),
        ("2.35", 2, ROUND_HALF_UP, "2.4"),
        ("2.45", 2, ROUND_HALF_UP, "2.5"),
        ("2.45", 2, ROUND_HALF_EVEN, "2.4"),
        ("2.675", 3, ROUND_HALF_UP, "2.68"),  # binary floating point would give 2.67
        ("0.0996", 2, ROUND_HALF_UP, "0.10"),  # the trailing zero is significant
        ("0.0012345", 2, ROUND_HALF_UP, "0.0012"),
        ("-0.012345", 3, ROUND_HALF_UP, "-0.0123"),
        ("96.4", 2, ROUND_HALF_UP, "96"),
        ("1234", 2, ROUND_HALF_UP, "1.2e3"),  # 1200 would claim four figures
    ],
)
def test_significant_figures_follow_the_rounding_rules(
    number: str, figures: int, rule: str, expected: str
) -> None:
    assert round_significant(Decimal(number), figures, rule) == expected


def test_rounding_touches_only_the_columns_asked_for(csv_file: Path) -> None:
    table = read_table(csv_file).round(significant=2, columns=["ee (%)"])

    assert table.column("ee (%)") == ["92", "85", "97", "96"]
    assert table.column("T (°C)") == ["25", "25", "0", "-20"]  # untouched
    assert table.column("catalyst") == ["L1", "L1", "L2", "L2"]


def test_decimals_can_be_fixed_and_text_is_never_rounded(csv_file: Path) -> None:
    table = read_table(csv_file).round(decimals=1)

    assert table.column("ee (%)") == ["92.3", "85.0", "97.0", "96.4"]
    assert table.column("solvent") == ["toluene", "THF", "toluene", "toluene"]
    assert table.column("conversion (%)")[3] == ""  # an empty cell stays empty


def test_a_value_and_its_uncertainty_are_rounded_together(csv_file: Path, tmp_path: Path) -> None:
    table = read_table(csv_file).with_uncertainty("ee (%)", "ee_err")

    assert table.column("ee (%)") == ["92 +- 1", "85.0 +- 0.5", "97", "96.4 +- 0.3"]
    assert "ee_err" not in table.headers
    text = write_table(table, tmp_path / "t.tex").read_text(encoding="utf-8")
    assert "S[table-format=2.1(1)]" in text


def test_two_significant_figures_on_the_uncertainty_if_asked(csv_file: Path) -> None:
    table = read_table(csv_file).with_uncertainty("ee (%)", "ee_err", significant=2)

    assert table.column("ee (%)")[0] == "92.3 +- 1.2"
    assert table.column("ee (%)")[3] == "96.40 +- 0.31"


def test_columns_can_be_chosen_renamed_grouped_and_noted(csv_file: Path, tmp_path: Path) -> None:
    table = (
        read_table(csv_file)
        .footnotes("note")
        .select("entry", "catalyst", "ee (%)")
        .rename({"ee (%)": "$ee$ (%)"})
        .rule_between("catalyst")
    )

    text = write_table(table, tmp_path / "t.tex").read_text(encoding="utf-8")
    assert "{$ee$ (\\%)}" in text
    assert text.count("\\tnote{a}") == 2 and "\\item[a] at 0 °C for 48 h" in text
    assert text.count("\\midrule") == 2  # under the header, and between L1 and L2


def test_a_missing_column_says_which_ones_there_are(csv_file: Path) -> None:
    with pytest.raises(LabHarnessError, match="has no column 'yield'"):
        read_table(csv_file).select("entry", "yield")


def test_the_original_table_is_never_changed(csv_file: Path) -> None:
    original = read_table(csv_file)
    original.round(significant=1)

    assert original.column("ee (%)")[0] == "92,347"


@pytest.mark.latex
@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="needs a LaTeX distribution")
def test_the_table_compiles_in_a_real_workspace(csv_file: Path, tmp_path: Path) -> None:
    root = create_workspace(tmp_path / "paper")
    table = (
        read_table(csv_file)
        .with_uncertainty("ee (%)", "ee_err")
        .footnotes("note")
        .rule_between("catalyst")
    )
    write_table(table, root / "tables" / "optimisation.tex")
    paper = root / "paper.tex"
    paper.write_text(
        paper.read_text(encoding="utf-8").replace(
            "\\end{document}",
            "\\begin{table}\n\\caption{Optimisation.}\n\\labtable{tables/optimisation.tex}\n"
            "\\end{table}\n\\end{document}",
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "paper.tex"],
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
    )

    errors = [line for line in result.stdout.splitlines() if line.startswith("!")]
    assert result.returncode == 0 and not errors, errors
