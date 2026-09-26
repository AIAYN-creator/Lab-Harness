"""The watcher's work as events: what changed, what was rebuilt, how long it took."""

import json
from pathlib import Path

import pytest

from labharness.core.manifest import Figure, load_workspace
from labharness.watch import events, session
from labharness.watch.runner import BuildResult, build

SCRIPT = (
    "from pathlib import Path\n"
    'value = Path("data/value.txt").read_text(encoding="utf-8").strip()\n'
    'Path("figures").mkdir(exist_ok=True)\n'
    'Path("figures/value.pdf").write_text(f"%PDF-1.4 {value}", encoding="utf-8")\n'
)


def workspace_in(root: Path) -> Path:
    (root / "labharness.toml").write_text(
        '[[figure]]\noutput = "figures/value.pdf"\nscript = "scripts/value.py"\n'
        'inputs = ["data/value.txt"]\n',
        encoding="utf-8",
    )
    (root / "data").mkdir()
    (root / "scripts").mkdir()
    (root / "data" / "value.txt").write_text("42\n", encoding="utf-8")
    (root / "scripts" / "value.py").write_text(SCRIPT, encoding="utf-8")
    return root


def test_a_rebuild_is_announced_before_it_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session, "build", lambda *args, **kwargs: BuildResult())  # no LaTeX
    workspace = load_workspace(workspace_in(tmp_path))
    announced: list[tuple[tuple[Path, ...], tuple[Figure, ...]]] = []
    saved = tmp_path / "data" / "value.txt"

    list(session.changes_to_cycles(workspace, [{saved}], lambda *args: announced.append(args)))

    assert announced == [((saved,), workspace.figures)]
    assert events.starting(tmp_path, *announced[0]) == [
        {"event": "changed", "path": "data/value.txt"},
        {"event": "building", "outputs": ["figures/value.pdf"]},
    ]


def test_a_finished_rebuild_says_what_was_built_and_what_data_changed(tmp_path: Path) -> None:
    workspace = load_workspace(workspace_in(tmp_path))
    build(workspace, compile_latex=False)  # registers the data in the lock
    (tmp_path / "data" / "value.txt").write_text("43\n", encoding="utf-8")

    told = events.finished(build(workspace, compile_latex=False))

    assert [event["event"] for event in told] == ["data", "built"]
    assert told[0]["path"] == "data/value.txt"
    assert told[1]["output"] == "figures/value.pdf" and told[1]["ok"] is True
    assert json.loads(json.dumps(told)) == told  # plain JSON, nothing else
