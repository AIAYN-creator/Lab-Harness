"""Creating a workspace from the template."""

import shutil
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME
from labharness.core.templates import JOURNALS, journal_template, template_root


def create_workspace(target: Path, journal: str = "acs", force: bool = False) -> Path:
    """Copy the template into ``target`` and drop in the chosen journal files."""
    target = target.expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise LabHarnessError(f"'{target}' is not empty. Use --force to write into it anyway.")

    # The journals folder is not part of a workspace: only the chosen journal is copied,
    # flattened into the root.
    shutil.copytree(
        template_root(),
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(JOURNALS),
    )
    for source in journal_template(journal).iterdir():
        shutil.copy(source, target / source.name)

    if not (target / MANIFEST_NAME).is_file():  # pragma: no cover - template would be broken
        raise LabHarnessError(f"the template produced no {MANIFEST_NAME}")
    return target
