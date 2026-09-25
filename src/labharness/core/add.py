"""Adding a figure or a table to a workspace: the script, the manifest entry and the LaTeX.

This is what a person or an agent would otherwise do by hand in three files, and where the
mistakes happen: a figure missing from the manifest never rebuilds, a manifest entry with a
typo points at nothing. Doing it in one call keeps the three consistent.
"""

import re
import string
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME, Workspace
from labharness.core.tabular import TEXT_FORMATS, read_rows
from labharness.core.templates import template_root

FIGURES_FOLDER = "figures"
TABLES_FOLDER = "tables"
SCRIPTS_FOLDER = "scripts"

# Each kind: the template it starts from and the suffix of the script it writes.
KINDS: dict[str, str] = {
    "structure": "structure.py.template",
    "plot": "plot.py.template",
    "mechanism": "mechanism.tex",
    "flow": "flow.tex",
    "network": "network.tex",
    "table": "table.py.template",
}
# What a table can be read from.
READABLE = TEXT_FORMATS | {".xlsx"}

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
# Where a new figure block goes: before the bibliography, or before the end of the document.
_DOCUMENT_ENDS = (
    r"\bibliographystyle{",
    r"\bibliography{",
    r"\printbibliography",
    r"\end{document}",
)


@dataclass(frozen=True)
class AddedFigure:
    """What ``add_figure`` wrote, and what the person still has to do."""

    name: str
    script: Path
    output: Path
    inputs: tuple[Path, ...]
    latex: str
    inserted: bool
    notes: list[str] = field(default_factory=list)


def add_figure(
    workspace: Workspace,
    kind: str,
    name: str,
    inputs: list[Path] | None = None,
    insert: bool = False,
    force: bool = False,
) -> AddedFigure:
    """Write the script of a new figure and declare it in the manifest.

    ``inputs`` are paths relative to the workspace. With ``insert``, the figure block is
    also added to the manuscript, before the bibliography.
    """
    if kind not in KINDS:
        raise LabHarnessError(f"unknown figure kind '{kind}'. Available: {', '.join(KINDS)}")
    if not _NAME.match(name):
        raise LabHarnessError(
            f"'{name}' cannot be a figure name: use letters, digits, '-' and '_', "
            "starting with a letter or a digit"
        )

    template = template_root().parent / "figures" / KINDS[kind]
    suffix = ".tex" if template.suffix == ".tex" else ".py"
    script = Path(SCRIPTS_FOLDER) / f"{name}{suffix}"
    if kind == "table":
        output = Path(TABLES_FOLDER) / f"{name}.tex"
    else:
        output = Path(FIGURES_FOLDER) / f"{name}.pdf"
    declared = [_relative(workspace.root, path) for path in inputs or []]
    notes: list[str] = []

    if kind == "structure" and not declared:
        declared = [Path("data") / f"{name}.smi"]
    _refuse_to_overwrite(workspace, script, output, force)

    fields = {"output": output.as_posix(), **_fields_for(kind, workspace.root, declared, notes)}
    for path in declared:
        if not (workspace.root / path).is_file():
            notes.append(f"{path.as_posix()} does not exist yet: the figure builds once it does.")

    source = template.read_text(encoding="utf-8")
    if suffix == ".py":
        text = string.Template(source).safe_substitute(fields)
    else:
        # Every script opens by saying which figure it produces.
        text = f"% {output.as_posix()} -- say here what this figure shows.\n%\n{source}"
    _write(workspace.root / script, text)

    if not any(figure.output == output for figure in workspace.figures):
        section = "table" if kind == "table" else "figure"
        _append_to_manifest(workspace.root / MANIFEST_NAME, section, output, script, declared)

    latex = table_block(output, name) if kind == "table" else figure_block(output, name)
    inserted = insert and _insert_into_document(workspace.document, latex, notes)
    return AddedFigure(name, script, output, tuple(declared), latex, inserted, notes)


def figure_block(output: Path, name: str) -> str:
    """The LaTeX that places a generated figure in the manuscript.

    ``[htbp]`` lets LaTeX put it where it is written when it fits there, as the templates do;
    without it, a figure placed after the text of a page always moves to the next one.
    """
    return "\n".join(
        [
            r"\begin{figure}[htbp]",
            r"  \centering",
            rf"  \labfigure{{{output.as_posix()}}}",
            r"  \caption{TODO: write the caption.}",
            rf"  \label{{fig:{name}}}",
            r"\end{figure}",
        ]
    )


def table_block(output: Path, name: str) -> str:
    """The LaTeX that places a generated table: the caption goes above a table."""
    return "\n".join(
        [
            r"\begin{table}[htbp]",
            r"  \centering",
            r"  \caption{TODO: write the caption.}",
            rf"  \label{{tab:{name}}}",
            rf"  \labtable{{{output.as_posix()}}}",
            r"\end{table}",
        ]
    )


def _fields_for(kind: str, root: Path, inputs: list[Path], notes: list[str]) -> dict[str, str]:
    if kind == "structure":
        return {"smiles_file": inputs[0].as_posix()}
    if kind not in ("plot", "table"):
        return {}

    table = next((path for path in inputs if path.suffix.lower() in READABLE), None)
    if table is None:
        notes.append("No CSV given: fill in the file and the column names in the script.")
        return {"csv": "data/FILE.csv", "x": "x", "y": "y"}
    if kind == "table":
        return {"csv": table.as_posix()}

    columns = _columns(root / table)
    if len(columns) < 2:
        notes.append(f"Could not read two columns from {table.as_posix()}: check x and y.")
        columns = [*columns, "x", "y"][:2]
    return {"csv": table.as_posix(), "x": columns[0], "y": columns[1]}


def _columns(path: Path) -> list[str]:
    """The header of a table, read the way the plot will read it."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # the plot reports skipped metadata when it runs
            return read_rows(path).headers
    except LabHarnessError:
        return []


def _relative(root: Path, path: Path) -> Path:
    absolute = (path if path.is_absolute() else root / path).resolve()
    try:
        return absolute.relative_to(root.resolve())
    except ValueError:
        raise LabHarnessError(
            f"'{path}' is outside the workspace: copy it into data/ first"
        ) from None


def _refuse_to_overwrite(workspace: Workspace, script: Path, output: Path, force: bool) -> None:
    if force:
        return
    if (workspace.root / script).exists():
        raise LabHarnessError(f"{script.as_posix()} already exists. Use --force to replace it.")
    if any(figure.output == output for figure in workspace.figures):
        raise LabHarnessError(
            f"the manifest already has an entry writing {output.as_posix()}. "
            "Pick another name, or use --force."
        )


def _append_to_manifest(
    manifest: Path, section: str, output: Path, script: Path, inputs: list[Path]
) -> None:
    """Append an entry as text, so the comments and layout of the file survive."""
    lines = [
        "",
        f"[[{section}]]",
        f'output = "{output.as_posix()}"',
        f'script = "{script.as_posix()}"',
    ]
    if inputs:
        listed = ", ".join(f'"{path.as_posix()}"' for path in inputs)
        lines.append(f"inputs = [{listed}]")
    current = manifest.read_text(encoding="utf-8")
    _write(manifest, current.rstrip("\n") + "\n" + "\n".join(lines) + "\n")


def _insert_into_document(document: Path, latex: str, notes: list[str]) -> bool:
    if not document.is_file():
        notes.append(f"No {document.name} here: paste the figure block where it belongs.")
        return False

    lines = document.read_text(encoding="utf-8").splitlines()
    position = next(
        (
            index
            for marker in _DOCUMENT_ENDS
            for index, line in enumerate(lines)
            if line.lstrip().startswith(marker)
        ),
        None,
    )
    if position is None:
        notes.append(f"Could not find where {document.name} ends: paste the block by hand.")
        return False

    lines[position:position] = [*latex.splitlines(), ""]
    _write(document, "\n".join(lines) + "\n")
    return True


def _write(path: Path, text: str) -> None:
    with atomic_output(path) as temporary:
        temporary.write_text(text, encoding="utf-8", newline="\n")
