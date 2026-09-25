"""The workspace manifest: which script builds which figure, from which data.

``labharness.toml`` is plain text the researcher can read and edit. It is also what lets the
watcher rebuild only what changed, and what a future graphical interface will read.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.templates import DEFAULT_JOURNAL

MANIFEST_NAME = "labharness.toml"
DOCUMENT_NAME = "paper.tex"
STYLE_NAME = "labharness-style.tex"
# How the document is compiled: LabHarness's own passes, or latexmk for those who want it.
BUILDERS = ("labharness", "latexmk")
DEFAULT_BUILDER = "labharness"
# The LaTeX engine. Every typeface in the catalogue works with pdflatex, the fastest; the
# others are for fontspec and packages that only exist for them.
ENGINES = ("pdflatex", "xelatex", "lualatex")
DEFAULT_ENGINE = "pdflatex"


@dataclass(frozen=True)
class Figure:
    """One generated figure or table, with the script that builds it and the files it uses.

    Both are built the same way; ``kind`` only says which section of the manifest declared it.
    """

    output: Path
    script: Path
    inputs: tuple[Path, ...]
    kind: str = "figure"

    @property
    def name(self) -> str:
        return self.output.stem

    def depends_on(self, path: Path) -> bool:
        return path == self.script or path in self.inputs


@dataclass(frozen=True)
class LibrarySettings:
    """Where the lab's compound inventory is, from [library] in the manifest."""

    file: Path
    sheet: str | int | None = None
    # Field (smiles, name, formula, code, aliases) -> the header that holds it.
    columns: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Workspace:
    """A folder with a manifest in it."""

    root: Path
    journal: str
    # Every generated output: the [[figure]] entries, then the [[table]] entries.
    figures: tuple[Figure, ...]
    builder: str = DEFAULT_BUILDER
    engine: str = DEFAULT_ENGINE
    # The typeface chosen for this workspace; None uses the journal's default.
    font: str | None = None
    library: LibrarySettings | None = None

    @property
    def document(self) -> Path:
        return self.root / DOCUMENT_NAME

    @property
    def watched_paths(self) -> list[Path]:
        return [self.root / name for name in ("data", "scripts", DOCUMENT_NAME, MANIFEST_NAME)]

    def figures_affected_by(self, path: Path) -> list[Figure]:
        """Figures to rebuild after ``path`` changed.

        A change to the manifest or the style rebuilds everything, because either can change
        how every figure looks.
        """
        relative = _relative_to(path, self.root)
        if relative is None:
            return []
        if relative.name in (MANIFEST_NAME, STYLE_NAME):
            return list(self.figures)
        return [figure for figure in self.figures if figure.depends_on(relative)]


def find_workspace(start: Path | None = None) -> Path:
    """Walk up from ``start`` looking for a manifest, the way git looks for ``.git``."""
    current = (start or Path.cwd()).resolve()
    for folder in [current, *current.parents]:
        if (folder / MANIFEST_NAME).is_file():
            return folder
    raise LabHarnessError(
        f"no '{MANIFEST_NAME}' found here or in any parent folder. "
        "Run this inside a workspace, or create one with: labharness init"
    )


def load_workspace(root: Path | None = None) -> Workspace:
    """Read the manifest of a workspace."""
    root = find_workspace(root) if root is None or not (root / MANIFEST_NAME).is_file() else root
    manifest = root / MANIFEST_NAME

    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise LabHarnessError(f"{manifest} is not valid TOML: {error}") from error

    figures = tuple(
        _figure(entry, manifest, kind)
        for kind in ("figure", "table")
        for entry in data.get(kind, [])
    )
    _reject_duplicates(figures, manifest)
    builder = str(data.get("builder", DEFAULT_BUILDER))
    if builder not in BUILDERS:
        raise LabHarnessError(
            f"{manifest}: builder must be one of {', '.join(BUILDERS)}, not '{builder}'"
        )
    engine = str(data.get("engine", DEFAULT_ENGINE))
    if engine not in ENGINES:
        raise LabHarnessError(
            f"{manifest}: engine must be one of {', '.join(ENGINES)}, not '{engine}'"
        )
    journal = str(data.get("journal", DEFAULT_JOURNAL))
    font = _font(data.get("font"), manifest)
    return Workspace(
        root=root,
        journal=journal,
        figures=figures,
        builder=builder,
        engine=engine,
        font=font,
        library=_library(data.get("library"), manifest),
    )


def _library(value: object, manifest: Path) -> LibrarySettings | None:
    if value is None:
        return None
    if not isinstance(value, dict) or "file" not in value:
        raise LabHarnessError(f'{manifest}: [library] needs file = "data/..."')
    columns = value.get("columns", {})
    if not isinstance(columns, dict):
        raise LabHarnessError(
            f'{manifest}: [library] columns must be a table, like {{ smiles = "..." }}'
        )
    sheet = value.get("sheet")
    return LibrarySettings(
        file=Path(str(value["file"])),
        sheet=sheet if isinstance(sheet, int) or sheet is None else str(sheet),
        columns=tuple((str(key), str(header)) for key, header in columns.items()),
    )


def _font(value: object, manifest: Path) -> str | None:
    if value is None:
        return None
    from labharness.style.typefaces import load_typeface

    try:
        return load_typeface(str(value)).id
    except LabHarnessError as error:
        raise LabHarnessError(f"{manifest}: {error}") from None


def _figure(entry: dict[str, object], manifest: Path, kind: str) -> Figure:
    for key in ("output", "script"):
        if key not in entry:
            raise LabHarnessError(f"{manifest}: a [[{kind}]] entry has no '{key}'")

    inputs = entry.get("inputs", [])
    if not isinstance(inputs, list):
        raise LabHarnessError(f"{manifest}: 'inputs' must be a list of paths")

    return Figure(
        output=Path(str(entry["output"])),
        script=Path(str(entry["script"])),
        inputs=tuple(Path(str(item)) for item in inputs),
        kind=kind,
    )


def _reject_duplicates(figures: tuple[Figure, ...], manifest: Path) -> None:
    seen: set[Path] = set()
    for figure in figures:
        if figure.output in seen:
            raise LabHarnessError(f"{manifest}: two entries write to '{figure.output}'")
        seen.add(figure.output)


def _relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
