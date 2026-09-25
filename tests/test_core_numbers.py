"""A value and its uncertainty are rounded the same way in a table and in the text."""

from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from labharness.core.numbers import round_together
from labharness.modules.tables import from_rows


@pytest.mark.parametrize(
    ("value", "error", "significant", "expected"),
    [
        ("0.012345", "0.00042", 2, ("0.01235", "0.00042")),
        ("1.2345", "0.0996", 2, ("1.23", "0.10")),  # the carry takes a digit away
        ("3.14159", "0.00996", 2, ("3.142", "0.010")),
        ("12345.6", "1234", 2, ("12300", "1200")),  # above the units: no false digits
        ("92.347", "1.2", 1, ("92", "1")),
        ("-0.0150172", "0.0000243", 2, ("-0.015017", "0.000024")),
        ("2.675", "0.01", 1, ("2.68", "0.01")),  # decimal, not the 2.67 of binary floats
    ],
)
def test_the_value_keeps_the_digits_its_uncertainty_justifies(
    value: str, error: str, significant: int, expected: tuple[str, str]
) -> None:
    assert round_together(Decimal(value), Decimal(error), significant) == expected


def test_half_to_even_is_available_for_long_columns() -> None:
    assert round_together(Decimal("2.45"), Decimal("0.1"), 1, ROUND_HALF_EVEN) == ("2.4", "0.1")


def test_a_fit_and_a_table_report_the_same_numbers() -> None:
    pytest.importorskip("numpy")
    from labharness.modules.plots.fits import Parameter

    table = from_rows(["k", "k_err"], [["12345.6", "1234"]]).with_uncertainty(
        "k", "k_err", significant=2
    )

    assert table.rows[0][0] == "12300 +- 1200"
    assert Parameter("k", 12345.6, 1234.0).rounded() == ("12300", "1200")
