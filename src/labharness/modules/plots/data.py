"""Reading measurements out of a CSV, with their uncertainty.

Lab data arrives as it arrives: replicates in columns, replicates in repeated rows, an error
column already computed, or nothing but the digits the instrument printed. All four are
handled here, and nothing is ever invented.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.extras import require
from labharness.core.tabular import Rows, parse_decimal, read_rows

DECIMAL_DIGITS = re.compile(r"[.,](\d+)")


@dataclass(frozen=True)
class Series:
    """One curve: where the numbers are and which columns to use.

    ``y`` may be a single column, or several when each replicate has its own column.
    """

    csv: Path | str
    x: str
    y: str | Sequence[str]
    label: str | None = None
    error_column: str | None = None
    resolution: float | None = None
    # Lines above the header and at the end of the file; see core.tabular.read_rows.
    skip: int | None = None
    skip_footer: int = 0
    # In an .xlsx workbook: the sheet, by name or number, and a range such as "A3:D20".
    sheet: str | int | None = None
    cells: str | None = None


@dataclass
class Points:
    """The measurements of a series, ready to plot: x, y and the error bar on y."""

    x: Any
    y: Any
    error: Any
    label: str | None = None
    error_source: str = "none"
    replicates: int = 1
    warnings: list[str] = field(default_factory=list)


def read_series(series: Series) -> Points:
    """Read a series and work out the uncertainty on each point."""
    numpy = require("numpy", extra="plots")

    path = Path(series.csv)
    read = _read(path, series)
    y_columns = [series.y] if isinstance(series.y, str) else list(series.y)

    x = numpy.array(_numbers(read, series.x, path))
    warnings: list[str] = []

    if len(y_columns) > 1:
        values = numpy.column_stack([_numbers(read, column, path) for column in y_columns])
        y = values.mean(axis=1)
        error = values.std(axis=1, ddof=1)
        source, replicates = "replicates", len(y_columns)
        if replicates < 3:
            warnings.append(
                f"{path.name}: {replicates} replicates per point. A standard deviation from two "
                "measurements is a weak estimate."
            )
    else:
        column = y_columns[0]
        y = numpy.array(_numbers(read, column, path))
        error, source, replicates = None, "none", 1

    if series.error_column is not None:
        error = numpy.array(_numbers(read, series.error_column, path))
        source = "error column"
    elif source == "none" and _has_repeated(x):
        x, y, error, replicates = _group_repeats(numpy, x, y)
        source = "replicates"
        if replicates < 3:
            warnings.append(
                f"{path.name}: some points have fewer than three replicates, so their standard "
                "deviation is a weak estimate."
            )
    elif source == "none":
        resolution = series.resolution
        if resolution is None:
            resolution, mixed = _resolution_from_digits(read.column(y_columns[0]))
            if mixed:
                warnings.append(
                    f"{path.name}: column '{y_columns[0]}' does not use the same number of "
                    "decimals everywhere, so the instrument resolution is a guess. Pass "
                    "resolution= to state it."
                )
        error = numpy.full(y.shape, resolution)
        source = "resolution"

    return Points(
        x=x,
        y=y,
        error=error,
        label=series.label,
        error_source=source,
        replicates=replicates,
        warnings=warnings,
    )


def _read(path: Path, series: Series) -> Rows:
    read = read_rows(
        path,
        skip=series.skip,
        skip_footer=series.skip_footer,
        sheet=series.sheet,
        cells=series.cells,
    )
    if not read.rows:
        raise LabHarnessError(f"'{path}' has no data rows")
    return read


def _numbers(read: Rows, column: str, path: Path) -> list[float]:
    """A column as numbers, written either as 1.23 or as 1,23.

    A cell that is not a number stops the plot with the file, the line and the column, so it
    can be found and fixed in the data rather than guessed around.
    """
    try:
        cells = read.column(column)
    except LabHarnessError as error:
        raise LabHarnessError(f"'{path.name}' {error}") from None
    numbers = []
    for line, cell in zip(read.lines, cells, strict=True):
        number = parse_decimal(cell)
        if number is None:
            shown = f"'{cell}'" if cell.strip() else "an empty cell"
            raise LabHarnessError(
                f"'{path.name}', line {line}, column '{column}': {shown} is not a number"
            )
        numbers.append(float(number))
    return numbers


def _resolution_from_digits(values: Sequence[str]) -> tuple[float, bool]:
    """Infer the instrument resolution from how many decimals were written down.

    The file is read as text precisely for this: 0.120 and 0.12 are the same number but not
    the same measurement.
    """
    decimals = {len(match.group(1)) for value in values if (match := DECIMAL_DIGITS.search(value))}
    if not decimals:
        return 1.0, False
    return 10.0 ** -max(decimals), len(decimals) > 1


def _has_repeated(x: Any) -> bool:
    return len(set(x.tolist())) < len(x)


def _group_repeats(numpy: Any, x: Any, y: Any) -> tuple[Any, Any, Any, int]:
    """Average rows that share the same x, keeping their standard deviation."""
    unique = sorted(set(x.tolist()))
    means, deviations, counts = [], [], []
    for value in unique:
        group = y[x == value]
        means.append(group.mean())
        deviations.append(group.std(ddof=1) if len(group) > 1 else 0.0)
        counts.append(len(group))
    return (
        numpy.array(unique),
        numpy.array(means),
        numpy.array(deviations),
        min(counts),
    )
