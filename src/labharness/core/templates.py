"""Locating the workspace template, which ships inside the installed package.

A journal is one folder under ``journals/``: its style (``style.toml``), its manuscript
(``paper.tex``) and its bibliography. Adding a journal is adding a folder. No code names a
journal, except :data:`DEFAULT_JOURNAL`, the one used when nobody asked for another.
"""

from pathlib import Path

from labharness.core.errors import LabHarnessError

WORKSPACE = "workspace"
JOURNALS = "journals"
STYLE_FILE = "style.toml"
DEFAULT_JOURNAL = "acs"


def template_root() -> Path:
    """The folder holding the workspace template.

    Installed, it lives inside the package. Running from a source checkout it is the
    ``templates/`` folder of the repository.
    """
    packaged = Path(__file__).resolve().parents[1] / "templates" / WORKSPACE
    if packaged.is_dir():
        return packaged

    from_source = Path(__file__).resolve().parents[3] / "templates" / WORKSPACE
    if from_source.is_dir():
        return from_source

    raise LabHarnessError("the workspace template is missing from this installation")


def available_journals() -> list[str]:
    """Every journal folder that carries a style."""
    return sorted(
        folder.name
        for folder in (template_root() / JOURNALS).iterdir()
        if (folder / STYLE_FILE).is_file()
    )


def journal_template(journal: str) -> Path:
    """The folder of a journal, or a clear error listing the ones that exist."""
    folder = template_root() / JOURNALS / journal
    if not (folder / STYLE_FILE).is_file():
        raise LabHarnessError(
            f"unknown journal '{journal}'. Available: {', '.join(available_journals())}"
        )
    return folder
