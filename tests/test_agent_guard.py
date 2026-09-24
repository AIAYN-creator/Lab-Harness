"""A new workspace stops agents from touching raw data, not only by asking them nicely."""

import json
from pathlib import Path

from labharness.core import create_workspace


def deny_rules(root: Path) -> list[str]:
    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return list(settings["permissions"]["deny"])


def test_a_new_workspace_denies_agents_any_write_to_data(tmp_path: Path) -> None:
    rules = deny_rules(create_workspace(tmp_path / "paper"))

    for tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        assert f"{tool}(data/**)" in rules


def test_agents_cannot_accept_a_change_to_the_data(tmp_path: Path) -> None:
    rules = deny_rules(create_workspace(tmp_path / "paper"))

    # Accepting a change to raw data is a human decision, whichever shell the agent uses.
    for shell in ("Bash", "PowerShell"):
        assert f"{shell}(labharness accept:*)" in rules
        assert f"{shell}(uv run labharness accept:*)" in rules
    assert "Edit(labharness.lock)" in rules and "Write(labharness.lock)" in rules


def test_the_rule_is_also_written_for_agents_that_read_agents_md(tmp_path: Path) -> None:
    rules = (create_workspace(tmp_path / "paper") / "AGENTS.md").read_text(encoding="utf-8")

    assert "never create, modify, move or delete anything in it" in rules
    assert "Never run `labharness accept`" in rules


def test_the_demo_shows_the_same_protection() -> None:
    demo = Path(__file__).resolve().parents[1] / "examples" / "demo"
    template = Path(__file__).resolve().parents[1] / "templates" / "workspace"

    assert deny_rules(demo) == deny_rules(template)
    for name in ("AGENTS.md", "AGENTS.chemistry.md", "CLAUDE.md"):
        assert (demo / name).read_text(encoding="utf-8") == (template / name).read_text(
            encoding="utf-8"
        )


def test_rules_are_modular_a_general_file_and_one_per_field(tmp_path: Path) -> None:
    root = create_workspace(tmp_path / "paper")
    general = (root / "AGENTS.md").read_text(encoding="utf-8")
    chemistry = (root / "AGENTS.chemistry.md").read_text(encoding="utf-8")

    # The general file points at the field files, and knows nothing about chemistry.
    assert "AGENTS.<field>.md" in general
    for word in ("SMILES", "enantiomer", "RDKit"):
        assert word not in general, word
    assert "SMILES" in chemistry and "enantiomer" in chemistry
    # Claude Code reads both through CLAUDE.md.
    assert (root / "CLAUDE.md").read_text(encoding="utf-8").split() == [
        "@AGENTS.md",
        "@AGENTS.chemistry.md",
    ]
