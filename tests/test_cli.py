from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness import __version__
from labharness.cli import app

runner = CliRunner()

SCRIPT = """
from pathlib import Path

Path("figures").mkdir(exist_ok=True)
Path("figures/value.pdf").write_text("%PDF-1.4", encoding="utf-8")
"""


def make_workspace(root: Path) -> Path:
    (root / "labharness.toml").write_text(
        """
[[figure]]
output = "figures/value.pdf"
script = "scripts/value.py"
inputs = ["data/value.txt"]
""",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "data").mkdir()
    (root / "scripts" / "value.py").write_text(SCRIPT, encoding="utf-8")
    (root / "data" / "value.txt").write_text("42\n", encoding="utf-8")
    return root


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_init_creates_a_workspace_ready_to_watch(tmp_path: Path) -> None:
    target = tmp_path / "my-paper"

    result = runner.invoke(app, ["init", str(target)])

    assert result.exit_code == 0, result.stdout
    for name in (
        "paper.tex",
        "labharness-style.tex",
        "labharness.toml",
        "references.bib",
        "AGENTS.md",
        "compile.sh",
    ):
        assert (target / name).is_file(), name
    for folder in ("data", "figures", "scripts"):
        assert (target / folder).is_dir(), folder
    # The journals folder belongs to the template, not to a workspace.
    assert not (target / "journals").exists()


def test_init_refuses_to_overwrite_unless_forced(tmp_path: Path) -> None:
    (tmp_path / "something.txt").write_text("mine", encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "--force" in result.stdout

    forced = runner.invoke(app, ["init", str(tmp_path), "--force"])
    assert forced.exit_code == 0
    assert (tmp_path / "something.txt").is_file()


def test_init_rejects_an_unknown_journal(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path / "paper"), "--journal", "nature"])

    assert result.exit_code == 1
    assert "acs" in result.stdout


def test_build_reports_each_figure_and_its_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(make_workspace(tmp_path))

    result = runner.invoke(app, ["build", "--no-latex"])

    assert result.exit_code == 0, result.stdout
    assert "figures" in result.stdout and "ms" in result.stdout
    assert (tmp_path / "figures" / "value.pdf").is_file()


def test_build_can_rebuild_a_single_figure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(make_workspace(tmp_path))

    result = runner.invoke(app, ["build", "--only", "value", "--no-latex"])

    assert result.exit_code == 0, result.stdout


def test_build_says_which_figures_exist_when_the_name_is_wrong(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(make_workspace(tmp_path))

    result = runner.invoke(app, ["build", "--only", "nope"])

    assert result.exit_code == 1
    assert "value" in result.stdout


def test_build_outside_a_workspace_explains_how_to_make_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "labharness init" in result.stdout


def test_doctor_reports_the_environment() -> None:
    result = runner.invoke(app, ["doctor"])

    # 0 when everything required is there, 3 when something is missing: both are valid answers.
    assert result.exit_code in (0, 3)
    assert "pdflatex" in result.stdout
    assert "PDF viewer" in result.stdout
