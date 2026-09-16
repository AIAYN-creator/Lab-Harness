"""The style of a journal, loaded from data.

A style is plain data: one file per journal under ``journals/``. Every engine translates
these values, so switching journals is switching files and no module ever hard-codes a
font, a size or a colour.
"""

import tomllib
from dataclasses import dataclass
from importlib import resources
from typing import Any

from labharness.core.errors import LabHarnessError

JOURNALS = "labharness.style.journals"


@dataclass(frozen=True)
class Typography:
    family: str
    latex_package: str
    font_file: str
    base_size_pt: float
    small_size_pt: float


@dataclass(frozen=True)
class Dimensions:
    single_column_in: float
    double_column_in: float
    aspect_ratio: float


@dataclass(frozen=True)
class Structures:
    bond_length_pt: float
    line_width_pt: float
    wedge_width_pt: float
    double_bond_offset: float
    hash_spacing_pt: float


@dataclass(frozen=True)
class Plots:
    grid: bool
    line_width_pt: float
    marker_size_pt: float
    error_capsize_pt: float
    axis_label_format: str
    palette: tuple[str, ...]


@dataclass(frozen=True)
class Style:
    name: str
    description: str
    typography: Typography
    dimensions: Dimensions
    structures: Structures
    plots: Plots

    def axis_label(self, quantity: str, unit: str | None = None) -> str:
        """Format an axis label, e.g. "Concentration (mM)" or "Absorbance"."""
        if not unit:
            return quantity
        return self.plots.axis_label_format.format(quantity=quantity, unit=unit)


def available_journals() -> list[str]:
    return sorted(
        entry.name.removesuffix(".toml")
        for entry in resources.files(JOURNALS).iterdir()
        if entry.name.endswith(".toml")
    )


def load_style(journal: str = "acs") -> Style:
    """Load the style of a journal. v0.1 ships ACS only."""
    source = resources.files(JOURNALS).joinpath(f"{journal}.toml")
    if not source.is_file():
        raise LabHarnessError(
            f"unknown journal '{journal}'. Available: {', '.join(available_journals())}"
        )

    data: dict[str, Any] = tomllib.loads(source.read_text(encoding="utf-8"))
    plots = data["plots"]
    return Style(
        name=data["name"],
        description=data["description"],
        typography=Typography(**data["typography"]),
        dimensions=Dimensions(**data["dimensions"]),
        structures=Structures(**data["structures"]),
        plots=Plots(**{**plots, "palette": tuple(plots["palette"])}),
    )
