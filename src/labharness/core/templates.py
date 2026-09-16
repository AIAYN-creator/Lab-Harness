"""Locating the workspace template, which ships inside the installed package."""

from pathlib import Path

from labharness.core.errors import LabHarnessError

WORKSPACE = "workspace"
JOURNALS = "journals"


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


def journal_template(journal: str) -> Path:
    folder = template_root() / JOURNALS / journal
    if not folder.is_dir():
        available = sorted(item.name for item in (template_root() / JOURNALS).iterdir())
        raise LabHarnessError(f"unknown journal '{journal}'. Available: {', '.join(available)}")
    return folder
