"""Creating a workspace from the template."""

import shutil
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.manifest import MANIFEST_NAME, STYLE_NAME
from labharness.core.templates import (
    DEFAULT_JOURNAL,
    JOURNALS,
    STYLE_FILE,
    journal_template,
    template_root,
)


def create_workspace(target: Path, journal: str = DEFAULT_JOURNAL, force: bool = False) -> Path:
    """Copy the template into ``target`` and drop in the chosen journal files.

    The workspace records its journal in the manifest, and its LaTeX style is generated from
    the journal style, so figures and document can never disagree about how they look.
    """
    from labharness.style.latex import document_preamble
    from labharness.style.tokens import load_style

    folder = journal_template(journal)
    target = target.expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise LabHarnessError(f"'{target}' is not empty. Use --force to write into it anyway.")

    # The journals folder is not part of a workspace: only the chosen journal is copied,
    # flattened into the root. Its style.toml stays in the package: it is read, not edited.
    shutil.copytree(
        template_root(),
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(JOURNALS),
    )
    for source in folder.iterdir():
        if source.name != STYLE_FILE:
            shutil.copy(source, target / source.name)

    manifest = target / MANIFEST_NAME
    if not manifest.is_file():  # pragma: no cover - template would be broken
        raise LabHarnessError(f"the template produced no {MANIFEST_NAME}")

    text = _with_journal(manifest.read_text(encoding="utf-8"), journal)
    manifest.write_text(text, encoding="utf-8", newline="\n")
    preamble = document_preamble(load_style(journal))
    (target / STYLE_NAME).write_text(preamble, encoding="utf-8", newline="\n")
    return target


def _with_journal(manifest: str, journal: str) -> str:
    """Put the journal at the top of the manifest, after its opening comments."""
    lines = manifest.splitlines()
    header = 0
    while header < len(lines) and lines[header].startswith("#"):
        header += 1
    entry = [f'journal = "{journal}"']
    return "\n".join([*lines[:header], "", *entry, *lines[header:]]) + "\n"
