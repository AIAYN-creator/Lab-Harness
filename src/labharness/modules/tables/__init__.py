"""Tables: whatever table you have, written in LaTeX as it is, then changed only on request.

Needs no extra: a table is text.

    from labharness.modules.tables import read_table, write_table

    table = read_table("data/optimisation.csv")          # every cell exactly as written
    table = table.with_uncertainty("ee (%)", "ee_err")    # only what was asked for
    write_table(table, "tables/optimisation.tex")

Place it in the manuscript with ``\\labtable{tables/optimisation.tex}`` inside a ``table``
environment that carries the caption and the label.
"""

from labharness.core.tabular import parse_decimal
from labharness.modules.tables.io import read_table, write_table
from labharness.modules.tables.table import (
    ROUNDING,
    Table,
    from_rows,
    round_places,
    round_significant,
)

__all__ = [
    "ROUNDING",
    "Table",
    "from_rows",
    "parse_decimal",
    "read_table",
    "round_places",
    "round_significant",
    "write_table",
]
