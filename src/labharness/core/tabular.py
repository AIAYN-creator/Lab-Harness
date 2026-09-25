"""Reading a delimited text file the way instruments and spreadsheets actually write them.

One reader for every module, so a file that works in a plot also works in a table. Every cell
comes back as text: how a number was written is data too. What the reader has to put up with is
what old software writes: cp1252 or UTF-16, a semicolon and a decimal comma, and lines of
metadata above the header. It never guesses in silence: skipped metadata is reported, and rows
at the end that do not fit the table stop the read until the person says to drop them.

An Excel workbook (.xlsx, with the excel extra) goes through the same path, each cell as Excel
shows it.
"""

import csv
import re
import warnings
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from labharness.core.errors import LabHarnessError, LabHarnessWarning
from labharness.core.extras import require

# In order of preference. The comma goes last: it is also the decimal mark in half the world.
DELIMITERS = (";", "\t", "|", ",")
# Tried in order. UTF-16 carries a byte-order mark; cp1252 is what Windows software of any
# age writes, including the old machines instruments are still attached to.
ENCODINGS = ("utf-8-sig", "utf-16", "cp1252", "latin-1")
TEXT_FORMATS = {".csv", ".tsv", ".txt", ".dat", ".asc"}
# A number format that shows a fixed number of decimals, such as 0.000 or #,##0.00.
_FIXED = re.compile(r"^(?:#,##)?0(?:\.(0+))?$")
# What a cell holds when there is no value: shown as a dash, never read as a number.
DASHES = {"-", "--", "---", "—", "–"}


@dataclass(frozen=True)
class Rows:
    """The header and the rows of a file, every cell as written."""

    headers: list[str]
    rows: list[list[str]]
    delimiter: str
    # The line number of the header in the file, counting from 1, for error messages.
    header_line: int


def read_rows(
    path: Path | str,
    delimiter: str | None = None,
    skip: int | None = None,
    skip_footer: int = 0,
    sheet: str | int | None = None,
    cells: str | None = None,
) -> Rows:
    """Read a delimited text file, or an Excel workbook, into a header and rows of text.

    ``skip`` is the number of lines above the header. Left out, lines of metadata that do not
    have the table's shape are skipped, with a warning saying so; a metadata line that happens
    to have it cannot be told from a header, so pass ``skip`` for those files. ``skip_footer``
    drops that many lines at the end, such as a row of totals. For a workbook, ``sheet`` is
    the sheet's name or its number from 0 (the first by default) and ``cells`` a range such as
    ``"A3:D20"`` (by default, every cell with something in it).
    """
    path = Path(path)
    if not path.is_file():
        raise LabHarnessError(f"'{path}' does not exist")
    if path.suffix.lower() == ".xlsx":
        delimiter = ""
        numbered = [(n, row) for n, row in _workbook_rows(path, sheet, cells) if any(row)]
    elif path.suffix.lower() in TEXT_FORMATS:
        lines = [
            (number, line)
            for number, line in enumerate(decode(path).splitlines(), start=1)
            if line.strip()
        ]
        delimiter = delimiter or (sniff([line for _, line in lines]) if lines else ",")
        numbered = [
            (number, next(csv.reader([line], delimiter=delimiter))) for number, line in lines
        ]
    else:
        raise LabHarnessError(
            f"'{path.name}' is not a table LabHarness reads. Export it to CSV (every spreadsheet, "
            "database and instrument can) or save it as .xlsx, and read that instead."
        )

    if skip_footer:
        numbered = numbered[:-skip_footer]
    if skip is not None:
        numbered = [(number, row) for number, row in numbered if number > skip]
    if not numbered:
        raise LabHarnessError(f"'{path.name}' has no rows")
    parsed = [row for _, row in numbered]

    start = 0
    if skip is None:
        start = _header_index(parsed)
        if start:
            warnings.warn(
                f"{path.name}: skipped {start} line(s) above the header, starting with "
                f"'{' '.join(parsed[0])[:40]}'. Pass skip={numbered[start][0] - 1} to say so and "
                "silence this.",
                LabHarnessWarning,
                stacklevel=2,
            )

    headers, body = parsed[start], parsed[start + 1 :]
    for offset, row in enumerate(body, start=start + 1):
        if len(row) > len(headers) and any(cell.strip() for cell in row[len(headers) :]):
            line = numbered[offset][0]
            remaining = len(body) - (offset - start - 1)
            raise LabHarnessError(
                f"{path.name}, line {line}: {len(row)} cells for {len(headers)} columns. If it "
                f"is a summary at the end of the file, pass skip_footer={remaining}."
            )
    rows = [(row + [""] * len(headers))[: len(headers)] for row in body]
    return Rows(
        headers=[header.strip() for header in headers],
        rows=rows,
        delimiter=delimiter,
        header_line=numbered[start][0],
    )


def _workbook_rows(
    path: Path, sheet: str | int | None, cells: str | None
) -> list[tuple[int, list[str]]]:
    """The rows of one sheet, numbered as Excel numbers them, every cell as Excel shows it.

    Formulas are read by the value Excel last calculated and saved; LabHarness never
    recalculates. A formula with no saved value stops the read rather than reading as empty.
    """
    openpyxl = require("openpyxl", extra="excel")
    try:
        values = openpyxl.load_workbook(path, data_only=True)
    except (zipfile.BadZipFile, KeyError, ValueError) as error:
        raise LabHarnessError(
            f"'{path.name}' is not a workbook Excel could open: {error}. Save it again from "
            "Excel as .xlsx, or export it to CSV."
        ) from None
    names = values.sheetnames
    if isinstance(sheet, int):
        if not 0 <= sheet < len(names):
            raise LabHarnessError(f"'{path.name}' has {len(names)} sheet(s): {', '.join(names)}")
        sheet = names[sheet]
    elif sheet is None:
        sheet = names[0]
    elif sheet not in names:
        raise LabHarnessError(f"'{path.name}' has no sheet '{sheet}'. It has: {', '.join(names)}")

    worksheet = values[sheet]
    bounds = {}
    if cells:
        left, top, right, bottom = openpyxl.utils.range_boundaries(cells)
        bounds = {"min_col": left, "min_row": top, "max_col": right, "max_row": bottom}
    formulas = None
    rows = []
    general = False
    for row in worksheet.iter_rows(**bounds):
        texts = []
        for cell in row:
            if cell.value is None:
                formulas = formulas or openpyxl.load_workbook(path)[sheet]
                formula = formulas[cell.coordinate].value
                if isinstance(formula, str) and formula.startswith("="):
                    raise LabHarnessError(
                        f"'{path.name}', cell {cell.coordinate}: a formula Excel never "
                        "calculated. Open the file in Excel and save it, then read it again."
                    )
            text, lost_zeros = _cell_text(cell.value, cell.number_format)
            general = general or lost_zeros
            texts.append(text)
        while texts and not texts[-1]:  # a sheet is rectangular; a row ends at its last value
            texts.pop()
        rows.append((row[0].row, texts))
    if general:
        warnings.warn(
            f"{path.name}: some numbers have no fixed number of decimals in Excel, so trailing "
            "zeros may be lost (0.120 reads as 0.12). Give the column a number format with its "
            "decimals, or pass resolution= to a plot.",
            LabHarnessWarning,
            stacklevel=3,
        )
    return rows


def _cell_text(value: object, number_format: str) -> tuple[str, bool]:
    """A cell as Excel shows it, and whether a number may have lost trailing zeros."""
    if value is None:
        return "", False
    if isinstance(value, bool):
        return str(value).upper(), False
    if isinstance(value, int):
        return str(value), False
    if isinstance(value, float):
        fixed = _FIXED.match(number_format)
        if fixed:
            return f"{value:.{len(fixed.group(1) or '')}f}", False
        text = repr(value)
        return (text[:-2] if text.endswith(".0") else text), True
    if hasattr(value, "isoformat"):
        return value.isoformat(), False
    return str(value), False


def decode(path: Path) -> str:
    """The text of ``path``, in the first of ENCODINGS that reads it."""
    data = path.read_bytes()
    for encoding in ENCODINGS:
        if encoding == "utf-16" and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
            continue
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise LabHarnessError(f"'{path.name}' is in an encoding LabHarness cannot read")


def sniff(lines: list[str]) -> str:
    """The first delimiter, in order of preference, that the last line of the file uses.

    The end of the file is the data: metadata above the header has no reason to use it.
    """
    return next((d for d in DELIMITERS if d in lines[-1]), ",")


def _header_index(rows: list[list[str]]) -> int:
    """The first row with as many cells as the row after it: above it, lines of metadata."""
    wide = any(len(row) > 1 for row in rows)
    for index, (row, following) in enumerate(zip(rows, rows[1:], strict=False)):
        if len(row) == len(following) and (len(row) > 1 or not wide):
            return index
    return 0


def parse_decimal(text: str) -> Decimal | None:
    """The number written in a cell, or None for text, blanks and dashes.

    Accepts a decimal comma (1,23), a leading plus, exponents (1.2e-3) and the Unicode minus
    sign that spreadsheets and some instruments write. A number with both a comma and a point,
    such as 1.234,5, is not read: whether the point groups thousands is a guess.
    """
    cleaned = text.strip().replace("−", "-").replace(" ", "")
    if not cleaned or cleaned in DASHES:
        return None
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None
