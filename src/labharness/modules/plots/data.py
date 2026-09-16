"""Reading measurements out of a CSV, with their uncertainty.

Lab data arrives as it arrives: replicates in columns, replicates in repeated rows, an error
column already computed, or nothing but the digits the instrument printed. All four are
handled here, and nothing is ever invented.
"""

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.extras import require

DELIMITERS = [",", ";", "\t"]
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
    if not path.is_file():
        raise LabHarnessError(f"'{path}' does not exist")

    rows, delimiter = _read_rows(path)
    y_columns = [series.y] if isinstance(series.y, str) else list(series.y)
    _check_columns(rows, [series.x, *y_columns], path, series.error_column)

    x_raw = [row[series.x] for row in rows]
    x = numpy.array([_number(value, delimiter, series.x, path) for value in x_raw])
    warnings: list[str] = []

    if len(y_columns) > 1:
        values = numpy.array(
            [
                [_number(row[column], delimiter, column, path) for column in y_columns]
                for row in rows
            ]
        )
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
        y = numpy.array([_number(row[column], delimiter, column, path) for row in rows])
        error, source, replicates = None, "none", 1

    if series.error_column is not None:
        error = numpy.array(
            [
                _number(row[series.error_column], delimiter, series.error_column, path)
                for row in rows
            ]
        )
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
            resolution, mixed = _resolution_from_digits([row[y_columns[0]] for row in rows])
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


def _read_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    text = path.read_text(encoding="utf-8-sig")
    delimiter = _sniff(text)
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    if not rows:
        raise LabHarnessError(f"'{path}' has no data rows")
    return rows, delimiter


def _sniff(text: str) -> str:
    """Pick the delimiter by counting them in the header.

    Spreadsheets in languages that use the comma as the decimal mark export with semicolons,
    which is what most of this data looks like.
    """
    header = text.splitlines()[0] if text.splitlines() else ""
    counts = {delimiter: header.count(delimiter) for delimiter in DELIMITERS}
    best = max(counts, key=lambda delimiter: counts[delimiter])
    return best if counts[best] else ","


def _check_columns(
    rows: list[dict[str, str]], needed: list[str], path: Path, error_column: str | None
) -> None:
    available = set(rows[0])
    for column in [*needed, *([error_column] if error_column else [])]:
        if column not in available:
            raise LabHarnessError(
                f"'{path.name}' has no column '{column}'. It has: {', '.join(sorted(available))}"
            )


def _number(value: str, delimiter: str, column: str, path: Path) -> float:
    """Read a number written either as 1.23 or as 1,23."""
    text = (value or "").strip()
    if delimiter == ";" or ("," in text and "." not in text):
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError as error:
        raise LabHarnessError(
            f"'{path.name}', column '{column}': '{value}' is not a number"
        ) from error


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
