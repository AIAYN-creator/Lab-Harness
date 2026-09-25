"""Regenerate the images in docs/gallery: the demo, and the first page of every template.

Each image is what LabHarness builds from the repository as it is, so the gallery cannot
drift from the code. Run it after changing a template or the demo:

    uv run python tools/make_gallery.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

from labharness.core import create_workspace, load_workspace
from labharness.core.templates import available_journals
from labharness.preview import preview_document
from labharness.watch.runner import build

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / "docs" / "gallery"
DPI = 90


def render(workspace_root: Path, name: str, pages: int | None = None) -> None:
    """Build a workspace and copy its first ``pages`` pages (all by default) as name-<n>.png."""
    workspace = load_workspace(workspace_root)
    result = build(workspace)
    if not result.ok:
        errors = [figure.error for figure in result.figures if not figure.ok]
        sys.exit(f"{name} did not build: {errors or result.compilation}")
    preview = preview_document(workspace, dpi=DPI)
    if not preview.ok:
        sys.exit(f"{name}: {preview.error}")
    for page, image in enumerate(preview.images[:pages], start=1):
        target = GALLERY / f"{name}-{page}.png"
        shutil.copy(image, target)
        print(target.relative_to(ROOT).as_posix())


def main() -> None:
    GALLERY.mkdir(parents=True, exist_ok=True)
    for stale in GALLERY.glob("*.png"):
        stale.unlink()
    with tempfile.TemporaryDirectory() as scratch:
        demo = Path(scratch) / "demo"
        shutil.copytree(ROOT / "examples" / "demo", demo)
        render(demo, "demo")
        # A template is shown by its first page: the rest is empty sections.
        for journal in available_journals():
            render(create_workspace(Path(scratch) / journal, journal=journal), journal, pages=1)


if __name__ == "__main__":
    main()
