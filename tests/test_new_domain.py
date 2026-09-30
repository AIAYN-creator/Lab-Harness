"""'labharness new-domain': a package that works as it comes, and refuses what would clash."""

import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core.errors import LabHarnessError
from labharness.core.newdomain import create_domain, domain_name

runner = CliRunner()


def test_a_name_becomes_what_a_python_package_can_be_called() -> None:
    assert domain_name("Arquitectura y obra") == "arquitectura_y_obra"
    assert domain_name("  Física -- óptica ") == "fisica_optica"


@pytest.mark.parametrize("bad", ["", "   ", "123", "+++"])
def test_a_name_that_cannot_be_a_package_is_refused(bad: str) -> None:
    with pytest.raises(LabHarnessError, match="cannot be the name of a domain"):
        domain_name(bad)


def test_the_package_is_written_with_its_name_in_every_file(tmp_path: Path) -> None:
    folder = create_domain("Architecture", tmp_path / "out")

    files = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    assert files == {
        "README.md",
        "pyproject.toml",
        "labharness_architecture/__init__.py",
        "labharness_architecture/commands.py",
        "labharness_architecture/AGENTS.architecture.md",
        "labharness_architecture/templates/architecture.py.template",
        "tests/test_architecture.py",
    }
    text = "".join(path.read_text(encoding="utf-8") for path in folder.rglob("*") if path.is_file())
    assert "{{" not in text and "__domain__" not in text and "__package__" not in text
    assert 'name = "labharness-architecture"' in (folder / "pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_the_tests_that_come_with_the_package_pass(tmp_path: Path) -> None:
    folder = create_domain("architecture", tmp_path / "out")

    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=folder,
        capture_output=True,
        text=True,
        check=False,
    )

    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.parametrize("taken", ["chem", "plots", "structure", "mechanism", "chemistry"])
def test_a_name_already_used_by_a_module_a_kind_or_a_field_is_refused(
    tmp_path: Path, taken: str
) -> None:
    with pytest.raises(LabHarnessError, match="already a module, a kind of figure or a field"):
        create_domain(taken, tmp_path / "out")

    assert not (tmp_path / "out").exists()


def test_a_folder_that_is_not_empty_is_not_written_into_unless_forced(tmp_path: Path) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "mine.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="not empty"):
        create_domain("architecture", target)
    create_domain("architecture", target, force=True)

    assert (target / "mine.txt").read_text(encoding="utf-8") == "mine"
    assert (target / "pyproject.toml").is_file()


def test_the_command_says_what_to_do_next(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new-domain", "architecture", "--path", str(tmp_path / "out")])

    assert result.exit_code == 0, result.stdout
    assert "uv pip install -e ." in result.stdout
