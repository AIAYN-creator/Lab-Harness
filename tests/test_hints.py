"""doctor says exactly what to type, on this system and for this kind of install."""

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness import hints
from labharness.cli import app
from labharness.hints import COMMANDS, System, command_for, extra_command, tex_package_command

runner = CliRunner()
SYSTEMS = ["windows", "macos", "debian", "fedora", "arch", "linux"]


@pytest.mark.parametrize("tool", sorted(COMMANDS))
@pytest.mark.parametrize("system", SYSTEMS)
def test_every_tool_has_an_answer_on_every_system(tool: str, system: str) -> None:
    assert command_for(tool, System(system, system))


def test_each_system_gets_its_own_package_manager() -> None:
    assert command_for("latex", System("windows", "")).startswith("winget install MiKTeX")
    assert command_for("latex", System("macos", "")).startswith("brew install")
    assert command_for("java", System("debian", "")).startswith("sudo apt install")
    assert command_for("java", System("fedora", "")).startswith("sudo dnf install")
    assert command_for("viewer", System("arch", "")).startswith("sudo pacman -S")


def test_a_tex_package_is_installed_with_the_distribution_of_the_system() -> None:
    assert "miktex packages install lm" in tex_package_command("lm", System("windows", ""))
    assert tex_package_command("lm", System("debian", "")) == "sudo tlmgr install lm"


@pytest.mark.parametrize(
    ("prefix", "expected"),
    [
        (
            "/home/ana/.local/share/uv/tools/labharness",
            'uv tool install --force "labharness[chem]"',
        ),
        ("/home/ana/.local/share/pipx/venvs/labharness", 'pipx install --force "labharness[chem]"'),
        ("/home/ana/venvs/paper", 'pip install "labharness[chem]"'),
    ],
)
def test_an_extra_is_added_the_way_labharness_was_installed(
    prefix: str, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hints, "_running_from_a_checkout", lambda: False)
    monkeypatch.setattr(sys, "prefix", prefix)

    assert extra_command("chem") == expected


def test_a_clone_of_the_repository_uses_uv_sync() -> None:
    # This test suite runs from a checkout.
    assert extra_command("plots") == "uv sync --extra plots"


def test_linux_distributions_are_recognised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = tmp_path / "os-release"
    release.write_text('ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04 LTS"\n', "utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(hints, "_os_release", lambda: hints_values(release))

    system = hints.detect_system()

    assert system == System("debian", "Ubuntu 24.04 LTS")


def hints_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        values[key] = value.strip('"')
    return values


def test_doctor_prints_the_system_and_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    debian = System("debian", "Debian 12")
    monkeypatch.setattr("labharness.doctor.shutil.which", lambda name: None)
    # labharness.cli.app is also the name of the Typer app, so reach the module itself.
    monkeypatch.setattr(sys.modules["labharness.cli.app"], "detect_system", lambda: debian)
    monkeypatch.setattr(hints, "detect_system", lambda: debian)

    result = runner.invoke(app, ["doctor"])

    assert "Debian 12" in result.stdout
    assert "sudo apt install texlive-latex-extra" in result.stdout
