"""A journal is a folder: adding one must not mean touching a module.

These tests add a journal nobody ships -- different axis labels, different text size -- and
check that every path through LabHarness picks it up: init, the style, the watcher and a
script run by hand.
"""

import re
import shutil
from pathlib import Path

import pytest

from labharness.core import LabHarnessError, create_workspace, load_workspace
from labharness.core import templates as templates_module
from labharness.style import available_journals, load_style, using_journal
from labharness.watch.runner import build_figure

SOURCE = Path(__file__).resolve().parents[1] / "src" / "labharness"
PROBE = """\
from pathlib import Path
from labharness.style import load_style

Path("figures/probe.txt").write_text(load_style().axis_label("Time", "min"), encoding="utf-8")
"""


@pytest.fixture
def fictional_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A copy of the template with one extra journal, used instead of the shipped one."""
    template = tmp_path / "template"
    shutil.copytree(templates_module.template_root(), template)

    acs = template / "journals" / "acs"
    journal = template / "journals" / "fictional"
    shutil.copytree(acs, journal)
    style = (journal / "style.toml").read_text(encoding="utf-8")
    style = style.replace('name = "acs"', 'name = "fictional"')
    style = style.replace('"{quantity} ({unit})"', '"{quantity} / {unit}"')
    style = style.replace("base_size_pt = 8.0", "base_size_pt = 9.0")
    (journal / "style.toml").write_text(style, encoding="utf-8")

    monkeypatch.setattr(templates_module, "template_root", lambda: template)
    return "fictional"


def test_a_journal_folder_is_all_it_takes_to_add_a_journal(fictional_journal: str) -> None:
    assert fictional_journal in available_journals()

    style = load_style(fictional_journal)

    assert style.name == "fictional"
    assert style.typography.base_size_pt == 9.0
    assert style.axis_label("Time", "min") == "Time / min"


def test_init_records_the_journal_and_generates_its_style(
    fictional_journal: str, tmp_path: Path
) -> None:
    workspace = create_workspace(tmp_path / "paper", journal=fictional_journal)

    assert load_workspace(workspace).journal == "fictional"
    assert "FICTIONAL journal style" in (workspace / "labharness-style.tex").read_text("utf-8")
    # The style is read from the package, never copied into the workspace to drift.
    assert not (workspace / "style.toml").exists()


def test_a_script_run_by_the_watcher_draws_for_the_workspace_journal(
    fictional_journal: str, tmp_path: Path
) -> None:
    root = create_workspace(tmp_path / "paper", journal=fictional_journal)
    (root / "scripts" / "probe.py").write_text(PROBE, encoding="utf-8")
    manifest = root / "labharness.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + '\n[[figure]]\noutput = "figures/probe.txt"\nscript = "scripts/probe.py"\n',
        encoding="utf-8",
    )
    workspace = load_workspace(root)

    result = build_figure(workspace, workspace.figures[0])

    assert result.ok, result.error
    assert (root / "figures" / "probe.txt").read_text(encoding="utf-8") == "Time / min"


def test_a_script_run_by_hand_finds_its_journal_in_the_manifest(
    fictional_journal: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = create_workspace(tmp_path / "paper", journal=fictional_journal)
    monkeypatch.chdir(root / "scripts")

    assert load_style().name == "fictional"


def test_the_watcher_journal_wins_over_the_folder(fictional_journal: str) -> None:
    with using_journal(fictional_journal):
        assert load_style().name == "fictional"
    assert load_style().name == "acs"


def test_an_unknown_journal_lists_the_ones_that_exist(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="acs"):
        create_workspace(tmp_path / "paper", journal="nature")
    # Nothing was written before the journal was checked.
    assert not (tmp_path / "paper").exists()


def test_no_module_names_a_journal() -> None:
    """Only the default journal may be spelled out, and only in one place."""
    naming = re.compile(r"""["']acs["']""")
    offenders = [
        str(path.relative_to(SOURCE))
        for path in SOURCE.rglob("*.py")
        if naming.search(path.read_text(encoding="utf-8"))
        and path != SOURCE / "core" / "templates.py"
    ]

    assert offenders == []
