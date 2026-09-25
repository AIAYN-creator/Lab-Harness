"""Reporting a value with its uncertainty, the same way everywhere LabHarness writes one.

Fitted parameters in the text and uncertainties in a table go through here, so a number never
has more digits than its uncertainty justifies, whichever route it takes to the page.
"""

from decimal import ROUND_HALF_UP, Decimal


def round_together(
    value: Decimal, error: Decimal, significant: int = 2, rounding: str = ROUND_HALF_UP
) -> tuple[str, str]:
    """``value`` and ``error``, the error to ``significant`` figures and the value to match.

    Decimal arithmetic on the numbers as written: 1.2345 +- 0.0996 is 1.23 +- 0.10, the
    rounding of 0.0996 carrying into one digit fewer, and 12345.6 +- 1234 is 12300 +- 1200.
    ``error`` must be positive.
    """
    first = error.adjusted()  # the position of its first significant digit
    quantum = Decimal(1).scaleb(first - significant + 1)
    shown = error.quantize(quantum, rounding=rounding)
    if shown.adjusted() != first:  # 0.0996 became 0.100: the carry added a digit
        quantum = quantum.scaleb(1)
        shown = error.quantize(quantum, rounding=rounding)
    return f"{value.quantize(quantum, rounding=rounding):f}", f"{shown:f}"
