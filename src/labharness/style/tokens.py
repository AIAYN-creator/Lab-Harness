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
_active_typeface: ContextVar[str | None] = ContextVar("labharness_typeface", default=None)


@dataclass(frozen=True)
class Typography:
    typeface: str
    family: str
    latex_packages: tuple[str, ...]
    font_file: str
    mathtext: str
    tex_package: str
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
    # How a structure fills the room the layout gives it (one column, or the text width of a
    # single-column document): as large as fits, but with bonds at most this many times the
    # journal's, so a small molecule does not turn into a poster; and no taller than this
    # fraction of its width, so a tall one does not take the page.
    max_bond_scale: float = 1.3
    max_height_ratio: float = 1.0


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
def using_journal(journal: str, typeface: str | None = None) -> Iterator[None]:
    """Make ``journal`` (and ``typeface``) what :func:`load_style` uses when not told."""
    journal_token = _active_journal.set(journal)
    typeface_token = _active_typeface.set(typeface)
    try:
        yield
    finally:
        _active_typeface.reset(typeface_token)
        _active_journal.reset(journal_token)


def current_typeface() -> str | None:
    """The typeface the workspace chose, or None to use the journal's default."""
    active = _active_typeface.get()
    if active is not None or _active_journal.get() is not None:
        return active

    from labharness.core.manifest import find_workspace, load_workspace

    try:
        return load_workspace(find_workspace()).font
    except LabHarnessError:
        return None


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


def load_style(journal: str | None = None, typeface: str | None = None) -> Style:
    """Load the style of a journal: the workspace's own journal and typeface when not named.

    Naming a journal without a typeface gives that journal's default typeface.
    """
    from labharness.style.typefaces import load_typeface

    if journal is None:
        typeface = typeface or current_typeface()
    source = journal_template(journal or current_journal()) / STYLE_FILE
    try:
        data: dict[str, Any] = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise LabHarnessError(f"{source} is not valid TOML: {error}") from error

    plots = data["plots"]
    sizes = data["typography"]
    face = load_typeface(typeface or sizes["typeface"])
    return Style(
        name=data["name"],
        description=data["description"],
        typography=Typography(
            typeface=face.id,
            family=face.family,
            latex_packages=face.latex_packages,
            font_file=face.font_file,
            mathtext=face.mathtext,
            tex_package=face.tex_package,
            base_size_pt=sizes["base_size_pt"],
            small_size_pt=sizes["small_size_pt"],
        ),
        dimensions=Dimensions(**data["dimensions"]),
        structures=Structures(**data["structures"]),
        plots=Plots(**{**plots, "palette": tuple(plots["palette"])}),
        latex=Latex(**data.get("latex", {})),
    )
