"""labharness.lock: raw data is fingerprinted, and a change has to be accepted by a person."""

import tomllib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core import LabHarnessError, load_workspace
from labharness.core.lock import LOCK_NAME, accept, check_data
from labharness.watch.runner import build

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "labharness.toml").write_text("", encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    (data / "kinetics.csv").write_text("t;c\n0;1,00\n5;0,61\n10;0,37\n", encoding="utf-8")
    (data / "catalyst.smi").write_text("CCO\n", encoding="utf-8")
    return tmp_path


def lock(root: Path) -> Any:
    return tomllib.loads((root / LOCK_NAME).read_text(encoding="utf-8"))


def test_new_files_are_registered_without_complaint(root: Path) -> None:
    report = check_data(root)

    assert report.registered == ("data/catalyst.smi", "data/kinetics.csv")
    assert report.clean
    assert set(lock(root)["files"]) == {"data/catalyst.smi", "data/kinetics.csv"}


def test_a_changed_file_is_reported_with_what_changed(root: Path) -> None:
    check_data(root)
    (root / "data" / "kinetics.csv").write_text("t;c\n0;1,00\n5;0,61\n", encoding="utf-8")

    report = check_data(root)

    assert not report.clean
    assert report.changes[0].message == (
        "data/kinetics.csv changed since it was accepted (4 lines -> 3 lines)"
    )


def test_it_keeps_being_reported_until_accepted(root: Path) -> None:
    check_data(root)
    (root / "data" / "catalyst.smi").write_text("CCN\n", encoding="utf-8")

    assert not check_data(root).clean
    assert not check_data(root).clean  # not forgotten after being said once
    assert "same size, different content" in check_data(root).changes[0].message


def test_accepting_records_who_when_and_what_it_replaced(root: Path) -> None:
    check_data(root)
    before = lock(root)["files"]["data/kinetics.csv"]["sha256"]
    (root / "data" / "kinetics.csv").write_text("t;c\n0;1,00\n", encoding="utf-8")

    accepted = accept(root, ["data/kinetics.csv"], by="Ana")

    assert [change.path for change in accepted] == ["data/kinetics.csv"]
    assert check_data(root).clean
    record = lock(root)["history"][0]
    assert record["by"] == "Ana"
    assert record["previous"] == before
    assert record["accepted"]


def test_a_removed_file_is_reported_and_can_be_accepted(root: Path) -> None:
    check_data(root)
    (root / "data" / "catalyst.smi").unlink()

    assert "was removed" in check_data(root).changes[0].message
    accept(root, ["data/catalyst.smi"])
    assert check_data(root).clean
    assert "data/catalyst.smi" not in lock(root)["files"]


def test_accepting_a_file_that_did_not_change_is_an_error(root: Path) -> None:
    check_data(root)

    with pytest.raises(LabHarnessError, match="no change to accept"):
        accept(root, ["data/kinetics.csv"])


def test_line_endings_changed_by_git_are_not_a_change(root: Path) -> None:
    kinetics = root / "data" / "kinetics.csv"
    unix = kinetics.read_bytes().replace(b"\r\n", b"\n")
    kinetics.write_bytes(unix)
    check_data(root)
    kinetics.write_bytes(unix.replace(b"\n", b"\r\n"))

    assert check_data(root).clean


def test_office_lock_files_and_hidden_files_are_not_data(root: Path) -> None:
    (root / "data" / "~$results.xlsx").write_bytes(b"lock")
    (root / "data" / ".DS_Store").write_bytes(b"x")

    assert all("~$" not in name and ".DS" not in name for name in check_data(root).registered)


def test_the_build_reports_it_and_still_builds(root: Path) -> None:
    check_data(root)
    (root / "data" / "kinetics.csv").write_text("t;c\n0;2,00\n", encoding="utf-8")

    result = build(load_workspace(root), compile_latex=False)

    assert result.ok  # a correction must be possible: nothing is blocked
    assert result.data.changes[0].path == "data/kinetics.csv"


def test_the_command_line_accepts_and_reports(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(root)
    runner.invoke(app, ["build", "--no-latex"])
    (root / "data" / "kinetics.csv").write_text("t;c\n0;2,00\n", encoding="utf-8")

    built = runner.invoke(app, ["build", "--no-latex"])
    accepted = runner.invoke(app, ["accept", "data/kinetics.csv"])
    again = runner.invoke(app, ["build", "--no-latex"])

    assert "changed since it was accepted" in built.stdout
    assert "labharness accept" in built.stdout
    assert accepted.exit_code == 0 and "Accepted" in accepted.stdout
    assert "changed since" not in again.stdout
