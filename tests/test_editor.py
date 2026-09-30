"""'labharness open': what it writes for VS Code, and what it leaves alone."""

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from labharness import editor
from labharness.cli import app
from labharness.core import create_workspace, load_workspace
from labharness.core.errors import LabHarnessError
from labharness.core.manifest import Workspace
from labharness.watch.session import Cycle, watch

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return load_workspace(create_workspace(tmp_path / "paper", journal="article"))


def read(root: Path, name: str) -> dict[str, Any]:
    content: dict[str, Any] = json.loads((root / ".vscode" / name).read_text(encoding="utf-8"))
    return content


def test_open_writes_the_task_and_the_settings(workspace: Workspace) -> None:
    editor.configure(workspace)

    (task,) = read(workspace.root, "tasks.json")["tasks"]
    assert task["command"] == "labharness watch --no-open"
    assert task["runOptions"] == {"runOn": "folderOpen"}
    settings = read(workspace.root, "settings.json")
    assert settings["latex-workshop.latex.autoBuild.run"] == "never"
    assert settings["latex-workshop.view.pdf.viewer"] == "tab"
    assert settings[editor.SIDE_KEY] == "right"


def test_raw_data_opens_read_only_and_the_paths_already_there_are_kept(
    workspace: Workspace,
) -> None:
    folder = workspace.root / ".vscode"
    folder.mkdir()
    (folder / "settings.json").write_text(
        json.dumps({editor.READONLY_KEY: {"dist/**": True}}), encoding="utf-8"
    )

    editor.configure(workspace)
    editor.configure(workspace)

    assert read(workspace.root, "settings.json")[editor.READONLY_KEY] == {
        "dist/**": True,
        "data/**": True,
    }


def test_what_the_person_already_had_is_kept(workspace: Workspace) -> None:
    folder = workspace.root / ".vscode"
    folder.mkdir()
    (folder / "settings.json").write_text(
        json.dumps({"editor.fontSize": 15, editor.SIDE_KEY: "left"}), encoding="utf-8"
    )
    (folder / "tasks.json").write_text(
        json.dumps({"version": "2.0.0", "tasks": [{"label": "mine", "type": "shell"}]}),
        encoding="utf-8",
    )

    editor.configure(workspace)
    editor.configure(workspace)  # twice: nothing is added twice

    settings = read(workspace.root, "settings.json")
    assert settings["editor.fontSize"] == 15
    assert settings[editor.SIDE_KEY] == "left"  # remembered, not reset to the default
    labels = [task["label"] for task in read(workspace.root, "tasks.json")["tasks"]]
    assert labels == ["mine", editor.TASK_LABEL]


def test_the_side_is_remembered_once_chosen(workspace: Workspace) -> None:
    editor.configure(workspace, "left")
    editor.configure(workspace)

    assert read(workspace.root, "settings.json")[editor.SIDE_KEY] == "left"


def test_a_side_that_is_not_one_is_refused(workspace: Workspace) -> None:
    with pytest.raises(LabHarnessError, match="left, right"):
        editor.configure(workspace, "above")

    assert not (workspace.root / ".vscode").exists()


def test_a_settings_file_with_comments_is_not_rewritten(workspace: Workspace) -> None:
    folder = workspace.root / ".vscode"
    folder.mkdir()
    original = '{\n  // my font\n  "editor.fontSize": 15\n}\n'
    (folder / "settings.json").write_text(original, encoding="utf-8")

    with pytest.raises(LabHarnessError, match="settings.json .* comments"):
        editor.configure(workspace)

    assert (folder / "settings.json").read_text(encoding="utf-8") == original
    assert not (folder / "tasks.json").exists()


def test_without_vs_code_open_says_how_to_install_it(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(editor, "find_code", lambda: None)
    monkeypatch.chdir(workspace.root)

    result = runner.invoke(app, ["open"])

    assert result.exit_code == 3
    assert "VS Code was not found" in result.stdout
    assert not (workspace.root / ".vscode").exists()


def test_open_configures_and_launches(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    launched = []
    monkeypatch.setattr(editor, "find_code", lambda: "code")
    monkeypatch.setattr(editor, "extension_installed", lambda code: False)
    monkeypatch.setattr(editor, "launch", lambda code, ws: launched.append((code, ws.root)))
    monkeypatch.chdir(workspace.root)

    result = runner.invoke(app, ["open", "--pdf", "left"])

    assert result.exit_code == 0, result.stdout
    assert launched == [("code", workspace.root)]
    assert "code --install-extension James-Yu.latex-workshop" in result.stdout
    assert read(workspace.root, "settings.json")[editor.SIDE_KEY] == "left"


def test_the_watcher_stops_when_asked_without_ctrl_c(workspace: Workspace) -> None:
    asked = threading.Event()
    cycles: list[Cycle] = []
    threading.Timer(0.5, asked.set).start()

    watch(workspace, on_cycle=cycles.append, stop_event=asked)  # returns, instead of blocking

    assert asked.is_set() and cycles == []
