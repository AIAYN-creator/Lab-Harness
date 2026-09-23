"""A git pre-commit hook that refuses to commit an unaccepted change to raw data.

The third layer protecting ``data/``: the lock reports a change on every build, and this makes
sure one cannot slip into the history unnoticed. New data files always pass; a file that was
modified or deleted passes only once ``labharness accept`` has recorded the change in the lock
that is committed with it. ``git commit --no-verify`` still gets past it: a net, not a cage.

The hook is a short shell script, so it needs no ``pre-commit`` tool, and it calls the same
Python that installed it, so it works whether LabHarness came from uv, pipx or pip.
"""

import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.lock import DATA_FOLDER, LOCK_NAME, TEXT_SUFFIXES, fingerprint_bytes
from labharness.core.manifest import MANIFEST_NAME

MARKER = "# Installed by LabHarness"
HOOK = """#!/bin/sh
{marker}: refuse commits that change accepted raw data without accepting it.
# Remove this file to disable it, or commit with --no-verify to skip it once.
exec "{python}" -m labharness hook check
"""


@dataclass(frozen=True)
class Refusal:
    path: str
    reason: str


def git_root(start: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=start, capture_output=True, text=True
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def install_hook(workspace: Path, force: bool = False) -> Path:
    """Write the pre-commit hook of the repository ``workspace`` belongs to."""
    root = git_root(workspace)
    if root is None:
        raise LabHarnessError(
            f"'{workspace}' is not in a git repository. Run 'git init' first, then "
            "'labharness hook install'."
        )
    hooks = _hooks_folder(root)
    hook = hooks / "pre-commit"
    foreign = hook.exists() and MARKER not in hook.read_text(encoding="utf-8", errors="replace")
    if foreign and not force:
        raise LabHarnessError(
            f"{hook} already exists and was not written by LabHarness. Add this line to it "
            f'instead: "{Path(sys.executable).as_posix()}" -m labharness hook check   '
            "(or use --force to replace it)"
        )
    hooks.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        HOOK.format(marker=MARKER, python=Path(sys.executable).as_posix()),
        encoding="utf-8",
        newline="\n",
    )
    hook.chmod(0o755)
    return hook


def workspaces_with_staged_data(root: Path) -> list[Path]:
    """Every workspace in the repository with a staged change under its ``data/``.

    Git runs hooks from the top of the repository, which is not necessarily a workspace: the
    workspaces are found from the staged files, walking up to the nearest manifest.
    """
    found: list[Path] = []
    for path in _git(root, "diff", "--cached", "--name-only", "--no-renames").splitlines():
        parts = Path(path).parts
        if DATA_FOLDER not in parts:
            continue
        folder = root.joinpath(*parts[: parts.index(DATA_FOLDER)])
        if (folder / MANIFEST_NAME).is_file() and folder not in found:
            found.append(folder)
    return found


def check_staged(workspace: Path) -> list[Refusal]:
    """The staged changes to data files that the staged lock does not accept."""
    root = git_root(workspace)
    if root is None:
        return []
    prefix = workspace.resolve().relative_to(root.resolve()).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    data = f"{prefix}{DATA_FOLDER}/"

    staged = _git(root, "diff", "--cached", "--name-status", "--no-renames", "--", data)
    accepted = _staged_lock(root, prefix + LOCK_NAME)
    refusals = []
    for line in staged.splitlines():
        status, _, path = line.partition("\t")
        name = path[len(prefix) :]
        if status == "A":
            continue  # new data is always welcome
        entry = accepted.get(name)
        if status == "D":
            if entry is not None:
                refusals.append(Refusal(name, "deleted, but still in labharness.lock"))
            continue
        text = Path(path).suffix.lower() in TEXT_SUFFIXES
        digest = fingerprint_bytes(_staged_bytes(root, path), text=text).sha256
        if entry is None or entry.get("sha256") != digest:
            refusals.append(Refusal(name, "changed, and the change was not accepted"))
    return refusals


def main_check(start: Path) -> int:
    """Entry point of the hook: print what is refused and return the exit code."""
    root = git_root(start)
    if root is None:
        return 0
    refusals = [
        refusal
        for workspace in workspaces_with_staged_data(root)
        for refusal in check_staged(workspace)
    ]
    if not refusals:
        return 0
    print("LabHarness: this commit changes raw data that was not accepted.", file=sys.stderr)
    for refusal in refusals:
        print(f"  {refusal.path}: {refusal.reason}", file=sys.stderr)
    print(
        "If the change is intended, run 'labharness accept <file>', stage labharness.lock "
        "with it, and commit again.",
        file=sys.stderr,
    )
    return 1


def _hooks_folder(root: Path) -> Path:
    configured = _git(root, "rev-parse", "--git-path", "hooks").strip()
    folder = Path(configured)
    return folder if folder.is_absolute() else root / folder


def _staged_lock(root: Path, lock_path: str) -> dict[str, dict[str, object]]:
    """The lock as it will be committed: the staged one, or the last committed one."""
    result = subprocess.run(
        ["git", "show", f":{lock_path}"], cwd=root, capture_output=True, check=False
    )
    if result.returncode != 0:
        return {}
    files: dict[str, dict[str, object]] = tomllib.loads(result.stdout.decode("utf-8")).get(
        "files", {}
    )
    return files


def _staged_bytes(root: Path, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f":{path}"], cwd=root, capture_output=True, check=True
    ).stdout


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout
