"""The working environment: VS Code with the manuscript, the watcher and the PDF beside it.

LabHarness does not build an editor. It writes the two files VS Code reads from ``.vscode/``
and opens the folder: a task that starts the watcher when the folder opens, and the settings
that make the LaTeX Workshop extension show the PDF in a tab, on the side the person chose,
and leave compiling to LabHarness. What was already in those files is kept.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.manifest import Workspace

FOLDER = ".vscode"
EXTENSION = "James-Yu.latex-workshop"
TASK_LABEL = "LabHarness: watch"
SIDES = ("left", "right")
DEFAULT_SIDE = "right"

SIDE_KEY = "latex-workshop.view.pdf.tab.editorGroup"
# What LabHarness owns in settings.json: the rest of the file is the person's.
SETTINGS = {
    "latex-workshop.latex.autoBuild.run": "never",
    "latex-workshop.view.pdf.viewer": "tab",
}
TASK = {
    "label": TASK_LABEL,
    "type": "shell",
    "command": "labharness watch --no-open",
    "isBackground": True,
    "problemMatcher": [],
    "presentation": {"reveal": "always", "panel": "dedicated", "clear": True},
    "runOptions": {"runOn": "folderOpen"},
}


def find_code() -> str | None:
    """The ``code`` command of VS Code, if it is on the PATH."""
    return shutil.which("code")


def extension_installed(code: str) -> bool:
    """Whether LaTeX Workshop is installed. Unknown counts as installed: it only warns."""
    try:
        listed = subprocess.run(
            [code, "--list-extensions"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return True
    return listed.returncode != 0 or EXTENSION.lower() in listed.stdout.lower().split()


def configure(workspace: Workspace, side: str | None = None) -> list[Path]:
    """Write the task and the settings, keeping whatever else the person had. Returns the files."""
    if side is not None and side not in SIDES:
        raise LabHarnessError(f"--pdf must be one of {', '.join(SIDES)}, not '{side}'")
    folder = workspace.root / FOLDER
    settings = _read(folder / "settings.json")
    settings.update(SETTINGS)
    settings[SIDE_KEY] = side or settings.get(SIDE_KEY) or DEFAULT_SIDE

    tasks = _read(folder / "tasks.json")
    tasks.setdefault("version", "2.0.0")
    others = [task for task in tasks.get("tasks", []) if task.get("label") != TASK_LABEL]
    tasks["tasks"] = [*others, TASK]

    folder.mkdir(exist_ok=True)
    written = []
    for name, content in (("settings.json", settings), ("tasks.json", tasks)):
        (folder / name).write_text(json.dumps(content, indent=4) + "\n", encoding="utf-8")
        written.append(folder / name)
    return written


def launch(code: str, workspace: Workspace) -> None:
    """Open the folder, and the manuscript in it, in VS Code."""
    subprocess.Popen(
        [code, str(workspace.root), str(workspace.document)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
    except json.JSONDecodeError as error:
        # VS Code allows comments in these files; rewriting one would lose them.
        raise LabHarnessError(
            f"{path.name} in {FOLDER}/ has comments or a syntax error ({error.msg}, line "
            f"{error.lineno}). LabHarness would have to rewrite it and lose them: fix it, or "
            "move it aside, and run 'labharness open' again."
        ) from error
    if not isinstance(content, dict):
        raise LabHarnessError(f"{path.name} in {FOLDER}/ is not a JSON object.")
    return content
