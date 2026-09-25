"""The unit written in a column header: ``t (min)``, ``t [min]`` or ``t / min``."""

import re

# A unit in brackets at the end, or after a slash with a space on each side (ISO 80000-1:
# quantity / unit). A slash without spaces, as in "A/B ratio", is part of the name.
_UNIT = re.compile(
    r"^(?P<quantity>.+?)\s*(?:\((?P<p>[^()]+)\)|\[(?P<b>[^\[\]]+)\]|\s/\s(?P<s>.+))$"
)


def split_unit(header: str) -> tuple[str, str | None]:
    """``("t", "min")`` for ``t (min)``, ``t [min]`` or ``t / min``; else ``(header, None)``."""
    match = _UNIT.match(header.strip())
    if match is None:
        return header.strip(), None
    unit = match["p"] or match["b"] or match["s"]
    return match["quantity"].strip(), unit.strip()
