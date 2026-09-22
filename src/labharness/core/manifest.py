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


@dataclass(frozen=True)
class Figure:
    """One generated figure, with the script that builds it and the files it depends on."""

    output: Path
    script: Path
    inputs: tuple[Path, ...]

    @property
    def name(self) -> str:
        return self.output.stem

    def depends_on(self, path: Path) -> bool:
        return path == self.script or path in self.inputs


@dataclass(frozen=True)
class Workspace:
    """A folder with a manifest in it."""

    root: Path
    journal: str
    figures: tuple[Figure, ...]

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

    figures = tuple(_figure(entry, manifest) for entry in data.get("figure", []))
    _reject_duplicates(figures, manifest)
    return Workspace(root=root, journal=str(data.get("journal", DEFAULT_JOURNAL)), figures=figures)


def _figure(entry: dict[str, object], manifest: Path) -> Figure:
    for key in ("output", "script"):
        if key not in entry:
            raise LabHarnessError(f"{manifest}: a [[figure]] entry has no '{key}'")

    inputs = entry.get("inputs", [])
    if not isinstance(inputs, list):
        raise LabHarnessError(f"{manifest}: 'inputs' must be a list of paths")

    return Figure(
        output=Path(str(entry["output"])),
        script=Path(str(entry["script"])),
        inputs=tuple(Path(str(item)) for item in inputs),
    )


def _reject_duplicates(figures: tuple[Figure, ...], manifest: Path) -> None:
    seen: set[Path] = set()
    for figure in figures:
        if figure.output in seen:
            raise LabHarnessError(f"{manifest}: two [[figure]] entries write to '{figure.output}'")
        seen.add(figure.output)


def _relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
