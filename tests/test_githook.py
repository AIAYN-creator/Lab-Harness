"""The git hook: an unaccepted change to raw data cannot be committed."""

import shutil
import subprocess
from pathlib import Path

import pytest

from labharness.core import LabHarnessError, create_workspace
from labharness.core.githook import MARKER, check_staged, install_hook, main_check
from labharness.core.lock import accept, check_data

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def git(folder: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.org")
    git(tmp_path, "config", "user.name", "Test")
    return tmp_path


@pytest.fixture
def workspace(repo: Path) -> Path:
    """A workspace in a subfolder, committed with one accepted data file."""
    root = create_workspace(repo / "paper")
    (root / "data" / "k.csv").write_text("t;c\n0;1\n", encoding="utf-8")
    check_data(root)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "start")
    return root


def change(root: Path) -> None:
    (root / "data" / "k.csv").write_text("t;c\n0;2\n", encoding="utf-8")
    git(root, "add", "-A")


def test_an_unaccepted_change_is_refused(workspace: Path) -> None:
    change(workspace)

    refusals = check_staged(workspace)

    assert [refusal.path for refusal in refusals] == ["data/k.csv"]
    assert main_check(workspace.parent) == 1  # from the repository root, as git runs it


def test_an_accepted_change_committed_with_its_lock_passes(workspace: Path) -> None:
    change(workspace)
    accept(workspace, ["data/k.csv"])
    git(workspace, "add", "-A")

    assert check_staged(workspace) == []


def test_accepting_without_staging_the_lock_is_not_enough(workspace: Path) -> None:
    change(workspace)
    accept(workspace, ["data/k.csv"])  # the lock changed, but it is not staged

    assert check_staged(workspace)


def test_new_data_always_passes(workspace: Path) -> None:
    (workspace / "data" / "more.csv").write_text("t;c\n0;3\n", encoding="utf-8")
    git(workspace, "add", "-A")

    assert check_staged(workspace) == []


def test_deleting_an_accepted_file_is_refused(workspace: Path) -> None:
    git(workspace, "rm", "-q", "data/k.csv")

    assert "deleted" in check_staged(workspace)[0].reason


def test_the_hook_blocks_a_real_commit(workspace: Path, repo: Path) -> None:
    install_hook(workspace)
    change(workspace)

    commit = git(repo, "commit", "-m", "sneaky")

    assert commit.returncode != 0
    assert "not accepted" in commit.stderr


def test_init_does_not_replace_a_hook_it_did_not_write(repo: Path) -> None:
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="was not written by LabHarness"):
        install_hook(repo)
    assert hook.read_text(encoding="utf-8") == "#!/bin/sh\necho mine\n"
    assert MARKER in install_hook(repo, force=True).read_text(encoding="utf-8")


def test_outside_a_repository_it_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="git init"):
        install_hook(tmp_path)
