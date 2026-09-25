"""Reading a delimited text file the way instruments and spreadsheets actually write them.

One reader for every module, so a file that works in a plot also works in a table. Every cell
comes back as text: how a number was written is data too. What the reader has to put up with is
what old software writes: cp1252 or UTF-16, a semicolon and a decimal comma, and lines of
metadata above the header. It never guesses in silence: skipped metadata is reported, and rows
at the end that do not fit the table stop the read until the person says to drop them.
"""

import csv
import warnings
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from labharness.core.errors import LabHarnessError, LabHarnessWarning

# In order of preference. The comma goes last: it is also the decimal mark in half the world.
DELIMITERS = (";", "\t", "|", ",")
# Tried in order. UTF-16 carries a byte-order mark; cp1252 is what Windows software of any
# age writes, including the old machines instruments are still attached to.
ENCODINGS = ("utf-8-sig", "utf-16", "cp1252", "latin-1")
TEXT_FORMATS = {".csv", ".tsv", ".txt", ".dat", ".asc"}
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
) -> Rows:
    """Read a delimited text file into a header and rows of text.

    ``skip`` is the number of lines above the header. Left out, lines of metadata that do not
    have the table's shape are skipped, with a warning saying so; a metadata line that happens
    to have it cannot be told from a header, so pass ``skip`` for those files. ``skip_footer``
    drops that many lines at the end, such as a row of totals.
    """
    path = Path(path)
    if not path.is_file():
        raise LabHarnessError(f"'{path}' does not exist")
    if path.suffix.lower() not in TEXT_FORMATS:
        raise LabHarnessError(
            f"'{path.name}' is not a delimited text file. Export it to CSV (every spreadsheet, "
            "database and instrument can) and read that instead."
        )

    numbered = [
        (number, line)
        for number, line in enumerate(decode(path).splitlines(), start=1)
        if line.strip()
    ]
    if skip_footer:
        numbered = numbered[:-skip_footer]
    if skip is not None:
        numbered = [(number, line) for number, line in numbered if number > skip]
    if not numbered:
        raise LabHarnessError(f"'{path.name}' has no rows")

    lines = [line for _, line in numbered]
    delimiter = delimiter or sniff(lines)
    parsed = list(csv.reader(lines, delimiter=delimiter))

    start = 0
    if skip is None:
        start = _header_index(parsed)
        if start:
            warnings.warn(
                f"{path.name}: skipped {start} line(s) above the header, starting with "
                f"'{lines[0][:40]}'. Pass skip={numbered[start][0] - 1} to say so and "
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
