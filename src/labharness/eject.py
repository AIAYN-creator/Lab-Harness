"""Ejecting a workspace: a copy that regenerates its figures without LabHarness installed.

A paper has to outlive the tool that built it. ``labharness eject`` copies a workspace into a
new folder, never touching the original, where:

- each Python script imports ``_labharness``, a local copy of only the modules it uses, with
  the journal style frozen as it was, so the scripts stay as short as they were;
- each diagram is a complete standalone LaTeX document that compiles with plain pdflatex;
- the data, the manuscript and the figures already built are copied as they are.

There is no way back and no updates: what is ejected is frozen, which is the point.
"""

import ast
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from labharness.core.domains import Module, installed_modules
from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME, Workspace
from labharness.core.templates import JOURNALS, STYLE_FILE, journal_template
from labharness.eject_build import write_build_files

VENDOR = "_labharness"
PACKAGE = Path(__file__).resolve().parent
# Always needed: what every module stands on.
FOUNDATION = ("core", "style")
# LabHarness's own files, which mean nothing once it is gone.
LEFT_BEHIND = (
    MANIFEST_NAME,
    "labharness.lock",
    "AGENTS.md",
    "AGENTS.chemistry.md",
    "CLAUDE.md",
    "compile.sh",
    "compile.ps1",
    ".claude",
    ".labharness",
    ".git",
)
BUILD_ARTEFACTS = (
    "*.aux",
    "*.log",
    "*.out",
    "*.fls",
    "*.fdb_latexmk",
    "*.synctex.gz",
    "*.toc",
    "*.blg",
    ".*.labharness-bib",
    "__pycache__",
    "*.tmp",
)
_IMPORT = re.compile(r"\b(from|import)(\s+)labharness(\.|\b)")


@dataclass(frozen=True)
class Ejected:
    target: Path
    modules: tuple[str, ...]
    scripts: tuple[str, ...]
    diagrams: tuple[str, ...]
    notes: list[str] = field(default_factory=list)


def eject(workspace: Workspace, target: Path, force: bool = False) -> Ejected:
    """Copy ``workspace`` into ``target`` so that it no longer needs LabHarness."""
    target = target.expanduser().resolve()
    source = workspace.root.resolve()
    if target == source or source in target.parents:
        raise LabHarnessError("eject into a folder outside the workspace, not inside it")
    if target.exists() and any(target.iterdir()) and not force:
        raise LabHarnessError(f"'{target}' is not empty. Use --force to write into it anyway.")

    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*LEFT_BEHIND, *BUILD_ARTEFACTS),
    )

    used = _modules_used(workspace)
    _vendor(target / VENDOR, used, workspace.journal)
    modules = [module.name for module in used]

    scripts, diagrams = [], []
    for figure in workspace.figures:
        script = target / figure.script
        if script.suffix == ".py" and script.is_file():
            script.write_text(
                _rewrite_imports(script.read_text(encoding="utf-8")),
                encoding="utf-8",
                newline="\n",
            )
            scripts.append(figure.script.as_posix())
        elif script.suffix == ".tex" and script.is_file():
            script.write_text(_standalone(workspace, script), encoding="utf-8", newline="\n")
            diagrams.append(figure.script.as_posix())

    domains = sorted({m.distribution for m in used if not m.built_in and m.distribution})
    write_build_files(workspace, target, modules, domains)
    return Ejected(target, tuple(modules), tuple(scripts), tuple(diagrams))


def _modules_used(workspace: Workspace) -> list[Module]:
    """The registered modules the workspace's Python scripts import, LabHarness's or a domain's."""
    installed = installed_modules()
    used: list[Module] = []
    for figure in workspace.figures:
        script = workspace.root / figure.script
        if script.suffix != ".py" or not script.is_file():
            continue
        tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            for name in names:
                for module in installed:
                    if module.provides(name) and module not in used:
                        used.append(module)
    return used


def _vendor(folder: Path, modules: list[Module], journal: str) -> None:
    """Copy the foundation and the used modules, renamed, with the style frozen.

    LabHarness's own modules go inside ``_labharness``. A domain's package is copied next to
    the scripts under its own name, so their imports stay as they are, with its imports of
    LabHarness pointed at the frozen copy.
    """
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "__init__.py").write_text(
        '"""LabHarness, frozen: only what this paper\'s scripts use. See EJECTED.md."""\n',
        encoding="utf-8",
    )
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for part in FOUNDATION:
        shutil.copytree(PACKAGE / part, folder / part, ignore=ignore)
    (folder / "modules").mkdir()
    shutil.copy(PACKAGE / "modules" / "__init__.py", folder / "modules" / "__init__.py")
    copied = [folder]
    for module in modules:
        if module.built_in:
            shutil.copytree(module.location(), folder / "modules" / module.name, ignore=ignore)
            continue
        destination = folder.parent.joinpath(*module.package.split("."))
        shutil.copytree(module.location(), destination, ignore=ignore, dirs_exist_ok=True)
        copied.append(destination)

    for path in (file for place in copied for file in place.rglob("*.py")):
        path.write_text(
            _rewrite_imports(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n"
        )

    # The journal style, frozen: only this journal's file, and it becomes the default.
    style = folder / "templates" / "workspace" / JOURNALS / journal / STYLE_FILE
    style.parent.mkdir(parents=True)
    shutil.copy(journal_template(journal) / STYLE_FILE, style)
    templates = folder / "core" / "templates.py"
    text = templates.read_text(encoding="utf-8")
    text = re.sub(r'DEFAULT_JOURNAL = "[^"]*"', f'DEFAULT_JOURNAL = "{journal}"', text)
    templates.write_text(text, encoding="utf-8", newline="\n")


def _rewrite_imports(text: str) -> str:
    return _IMPORT.sub(lambda match: f"{match[1]}{match[2]}{VENDOR}{match[3]}", text)


def _standalone(workspace: Workspace, script: Path) -> str:
    """A diagram as a complete document, with the journal style it was drawn with."""
    from labharness.modules.diagrams import build_document
    from labharness.style import load_style

    document = build_document(script.read_text(encoding="utf-8"), load_style(workspace.journal))
    return (
        "% Ejected from LabHarness: a complete standalone document, with the journal style\n"
        "% it was drawn with. Compile it with pdflatex (twice if it has curved arrows).\n"
        + document
    )
