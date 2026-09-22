"""The style of a journal, loaded from data.

A style is plain data: the ``style.toml`` of each journal folder in the workspace template.
Every engine translates these values, so switching journals is switching files and no module
ever hard-codes a journal, a font, a size or a colour.

A figure script does not say which journal it is drawn for: it takes the journal of the
workspace it belongs to. The watcher tells it (:func:`using_journal`); a script run by hand
finds the manifest the way git finds ``.git``.
"""

import contextlib
import tomllib
from collections.abc import Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.templates import DEFAULT_JOURNAL, STYLE_FILE, journal_template

_active_journal: ContextVar[str | None] = ContextVar("labharness_journal", default=None)


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
class Latex:
    # Journal-specific LaTeX appended to the document preamble, for workarounds that belong
    # to one document class and must not leak into the others.
    preamble: str = ""


@dataclass(frozen=True)
class Style:
    name: str
    description: str
    typography: Typography
    dimensions: Dimensions
    structures: Structures
    plots: Plots
    latex: Latex = Latex()

    def axis_label(self, quantity: str, unit: str | None = None) -> str:
        """Format an axis label, e.g. "Concentration (mM)" or "Absorbance"."""
        if not unit:
            return quantity
        return self.plots.axis_label_format.format(quantity=quantity, unit=unit)


@contextlib.contextmanager
def using_journal(journal: str) -> Iterator[None]:
    """Make ``journal`` the one :func:`load_style` returns when it is not given one."""
    token = _active_journal.set(journal)
    try:
        yield
    finally:
        _active_journal.reset(token)


def current_journal() -> str:
    """The journal a figure is being drawn for.

    Set by the watcher; otherwise read from the manifest of the workspace the script runs
    in; otherwise the default, for a script run outside any workspace.
    """
    active = _active_journal.get()
    if active is not None:
        return active

    from labharness.core.manifest import find_workspace, load_workspace

    try:
        return load_workspace(find_workspace()).journal
    except LabHarnessError:
        return DEFAULT_JOURNAL


def load_style(journal: str | None = None) -> Style:
    """Load the style of a journal: the workspace's own when none is named."""
    source = journal_template(journal or current_journal()) / STYLE_FILE
    try:
        data: dict[str, Any] = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise LabHarnessError(f"{source} is not valid TOML: {error}") from error

    plots = data["plots"]
    return Style(
        name=data["name"],
        description=data["description"],
        typography=Typography(**data["typography"]),
        dimensions=Dimensions(**data["dimensions"]),
        structures=Structures(**data["structures"]),
        plots=Plots(**{**plots, "palette": tuple(plots["palette"])}),
        latex=Latex(**data.get("latex", {})),
    )
