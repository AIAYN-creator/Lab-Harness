"""A table as it was written: headers and cells kept as text, never reinterpreted.

A table in LabHarness is whatever the person hands over: a CSV exported from an instrument,
a spreadsheet, a database dump. It is read as text, because how a number was written is
data too (0.120 is not 0.12), and written to LaTeX exactly as it was. Anything else is an
explicit operation the person, or an agent on their behalf, asks for: keep two significant
figures, pair a value with its uncertainty, rename a column. Each one returns a new table,
so the original is never lost and the script reads as the list of what was done to it.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from labharness.core.errors import LabHarnessError
from labharness.core.numbers import round_together
from labharness.core.tabular import parse_decimal

# How a half is rounded. Half up is what most chemistry courses teach (2.45 -> 2.5); half to
# even is the ISO 80000-1 rule, which does not bias a long column of results upwards.
ROUNDING = {"half-up": ROUND_HALF_UP, "half-even": ROUND_HALF_EVEN}


@dataclass(frozen=True)
class Table:
    """Headers and rows, every cell a string exactly as read."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    source: str = ""
    # Row indices a horizontal rule goes before, and footnotes: (row, column) -> letter.
    rules: tuple[int, ...] = ()
    notes: tuple[tuple[str, str], ...] = ()
    marks: tuple[tuple[int, int, str], ...] = ()
    uncertainties: Mapping[str, str] = field(default_factory=dict)

    # --- looking inside ---------------------------------------------------------------------

    def column(self, name: str) -> list[str]:
        return [row[self._index(name)] for row in self.rows]

    def _index(self, name: str) -> int:
        try:
            return self.headers.index(name)
        except ValueError:
            known = ", ".join(repr(header) for header in self.headers)
            raise LabHarnessError(f"the table has no column {name!r}. It has: {known}") from None

    # --- choosing what to show --------------------------------------------------------------

    def select(self, *names: str) -> "Table":
        """Keep these columns, in this order."""
        indices = [self._index(name) for name in names]
        return replace(
            self,
            headers=tuple(self.headers[i] for i in indices),
            rows=tuple(tuple(row[i] for i in indices) for row in self.rows),
            marks=tuple((r, indices.index(c), m) for r, c, m in self.marks if c in indices),
        )

    def drop(self, *names: str) -> "Table":
        for name in names:
            self._index(name)
        return self.select(*(header for header in self.headers if header not in names))

    def rename(self, names: Mapping[str, str]) -> "Table":
        """Give columns new headers, e.g. {"ee": "ee (%)"}."""
        for name in names:
            self._index(name)
        uncertainties = {names.get(k, k): names.get(v, v) for k, v in self.uncertainties.items()}
        return replace(
            self,
            headers=tuple(names.get(header, header) for header in self.headers),
            uncertainties=uncertainties,
        )

    # --- numbers ----------------------------------------------------------------------------

    def round(
        self,
        significant: int | None = None,
        decimals: int | None = None,
        columns: Iterable[str] | None = None,
        rule: str = "half-up",
    ) -> "Table":
        """Round numeric cells to ``significant`` figures or to ``decimals`` places.

        Only numbers change; text, empty cells and dashes are left alone. Rounding works on the
        number as written, in decimal, so 2.675 rounds to 2.68 and not to the 2.67 that binary
        floating point would give. A value whose rounding falls above the units, such as 1234
        to two figures, is written as 1.2e3, because 1200 would claim four.
        """
        if (significant is None) == (decimals is None):
            raise LabHarnessError("round needs either significant= or decimals=, not both")
        if rule not in ROUNDING:
            raise LabHarnessError(f"unknown rounding rule {rule!r}. Use: {', '.join(ROUNDING)}")
        if significant is not None and significant < 1:
            raise LabHarnessError("significant= must be at least 1")

        def one(text: str) -> str:
            number = parse_decimal(text)
            if number is None:
                return text
            if significant is not None:
                return round_significant(number, significant, ROUNDING[rule])
            return round_places(number, decimals or 0, ROUNDING[rule])

        return self._map(one, columns)

    def with_uncertainty(
        self, value: str, error: str, significant: int = 1, rule: str = "half-up"
    ) -> "Table":
        """Show ``value`` as value ± error, the error dropped as a column of its own.

        The error is rounded to ``significant`` figures (one, or two when its first digit is
        1, is the usual convention, so pass significant=2 for that) and the value to the same
        decimal place. A row with no error keeps its value as written.
        """
        values, errors = self._index(value), self._index(error)
        rounding = ROUNDING.get(rule)
        if rounding is None:
            raise LabHarnessError(f"unknown rounding rule {rule!r}. Use: {', '.join(ROUNDING)}")

        rows = []
        for row in self.rows:
            cells = list(row)
            number, spread = parse_decimal(row[values]), parse_decimal(row[errors])
            if number is not None and spread is not None and spread > 0:
                shown_value, shown_error = round_together(number, spread, significant, rounding)
                cells[values] = f"{shown_value} +- {shown_error}"
            rows.append(tuple(cells))
        paired = replace(self, rows=tuple(rows), uncertainties={**self.uncertainties, value: error})
        return paired.drop(error)

    # --- layout -----------------------------------------------------------------------------

    def rule_between(self, column: str) -> "Table":
        """Draw a rule wherever ``column`` changes value, to separate groups of rows."""
        cells, rules = self.column(column), []
        for index in range(1, len(cells)):
            if cells[index] != cells[index - 1]:
                rules.append(index)
        return replace(self, rules=tuple(rules))

    def footnotes(self, column: str, on: str | None = None) -> "Table":
        """Turn a column of footnote texts into table notes, marked on column ``on``.

        Rows with the same text share a letter. The notes column is dropped.
        """
        target = on or self.headers[0]
        letters: dict[str, str] = {}
        marks = list(self.marks)
        for row, text in enumerate(self.column(column)):
            text = text.strip()
            if not text:
                continue
            if text not in letters:
                if len(letters) == 26:
                    raise LabHarnessError("a table cannot have more than 26 different notes")
                letters[text] = "abcdefghijklmnopqrstuvwxyz"[len(letters)]
            marks.append((row, self._index(target), letters[text]))
        noted = replace(
            self,
            marks=tuple(marks),
            notes=(*self.notes, *((letter, text) for text, letter in letters.items())),
        )
        return noted.drop(column)

    # ----------------------------------------------------------------------------------------

    def _map(self, change: Callable[[str], str], columns: Iterable[str] | None) -> "Table":
        chosen = set(range(len(self.headers)))
        if columns is not None:
            chosen = {self._index(name) for name in columns}
        rows = tuple(
            tuple(change(cell) if i in chosen else cell for i, cell in enumerate(row))
            for row in self.rows
        )
        return replace(self, rows=rows)


def round_significant(number: Decimal, figures: int, rounding: str) -> str:
    """``number`` with ``figures`` significant figures, trailing zeros kept: 0.0996 -> 0.10."""
    if number == 0:
        return "0" if figures == 1 else "0." + "0" * (figures - 1)
    exponent = number.adjusted()  # position of the first significant digit
    quantum = Decimal(1).scaleb(exponent - figures + 1)
    rounded = number.quantize(quantum, rounding=rounding)
    if rounded.adjusted() != exponent:  # 9.96 -> 10.0 carried a digit: one fewer place
        quantum = quantum.scaleb(1)
        rounded = number.quantize(quantum, rounding=rounding)
    if quantum.as_tuple().exponent > 0:  # type: ignore[operator]
        # Rounding above the units: 1234 to two figures is 1.2e3, not 1200.
        mantissa = rounded.scaleb(-rounded.adjusted()).quantize(Decimal(1).scaleb(1 - figures))
        return f"{mantissa}e{rounded.adjusted()}"
    return f"{rounded:f}"


def round_places(number: Decimal, places: int, rounding: str) -> str:
    """``number`` with exactly ``places`` decimals."""
    return f"{number.quantize(Decimal(1).scaleb(-places), rounding=rounding):f}"


def from_rows(headers: Sequence[str], rows: Sequence[Sequence[str]], source: str = "") -> Table:
    width = len(headers)
    cleaned = []
    for number, row in enumerate(rows, start=2):
        cells = [str(cell) if cell is not None else "" for cell in row]
        if len(cells) > width and any(cell.strip() for cell in cells[width:]):
            raise LabHarnessError(
                f"{source or 'the table'}, row {number}: {len(cells)} cells for {width} columns"
            )
        cleaned.append(tuple((cells + [""] * width)[:width]))
    return Table(headers=tuple(str(h).strip() for h in headers), rows=tuple(cleaned), source=source)
