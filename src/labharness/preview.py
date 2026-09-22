"""Turning figures into images someone -- or an agent -- can look at.

Tests check that a figure builds; they cannot check that it reads well. The first live
rehearsal showed why that matters: an iodomethyl group came out as ``CH2·I``, which a
chemist reads as a radical, and only looking at the page caught it. A PNG is something an
agent can open and inspect, so reviewing a figure becomes part of the loop, not an
afterthought.

Rasterising uses what a LaTeX installation already ships: ``pdftoppm`` (MiKTeX, and Poppler
on Linux and macOS), or Ghostscript. No Python dependency is added for it.
"""

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from labharness.core.errors import LabHarnessError
from labharness.core.manifest import Figure, Workspace

PREVIEW_FOLDER = Path(".labharness") / "preview"
DEFAULT_DPI = 200
# MiKTeX ships Ghostscript as mgs; Windows installers call it gswin64c.
GHOSTSCRIPT = ("gs", "gswin64c", "gswin32c", "mgs")
INSTALL_HINT = (
    "Install Poppler (pdftoppm) or Ghostscript: MiKTeX already includes pdftoppm; "
    "on Debian or Ubuntu 'apt install poppler-utils', on macOS 'brew install poppler'"
)


@dataclass(frozen=True)
class Preview:
    source: Path
    images: tuple[Path, ...]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def find_rasteriser() -> tuple[str, Path] | None:
    """The tool used to rasterise PDFs, and where it is, or None if there is none."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        return "pdftoppm", Path(pdftoppm)
    for name in GHOSTSCRIPT:
        found = shutil.which(name)
        if found:
            return "ghostscript", Path(found)
    return None


def preview_figures(
    workspace: Workspace, figures: Sequence[Figure] | None = None, dpi: int = DEFAULT_DPI
) -> list[Preview]:
    """Rasterise the given figures (all of them by default) into ``.labharness/preview``."""
    tool = _require_rasteriser()
    folder = workspace.root / PREVIEW_FOLDER
    results = []
    for figure in workspace.figures if figures is None else figures:
        pdf = workspace.root / figure.output
        results.append(_rasterise(tool, pdf, folder / figure.name, dpi, first_page_only=True))
    return results


def preview_document(workspace: Workspace, dpi: int = DEFAULT_DPI) -> Preview:
    """Rasterise every page of the compiled manuscript, to check figures in place."""
    tool = _require_rasteriser()
    pdf = workspace.document.with_suffix(".pdf")
    stem = workspace.root / PREVIEW_FOLDER / pdf.stem
    return _rasterise(tool, pdf, stem, dpi, first_page_only=False)


def _require_rasteriser() -> tuple[str, Path]:
    tool = find_rasteriser()
    if tool is None:
        raise LabHarnessError(f"no tool to turn PDFs into images. {INSTALL_HINT}")
    return tool


def _rasterise(
    tool: tuple[str, Path], pdf: Path, stem: Path, dpi: int, first_page_only: bool
) -> Preview:
    if not pdf.is_file():
        return Preview(pdf, (), error=f"{pdf.name} has not been built yet")

    stem.parent.mkdir(parents=True, exist_ok=True)
    for stale in _images(stem, first_page_only):
        stale.unlink()

    kind, executable = tool
    if kind == "pdftoppm":
        command = [str(executable), "-png", "-r", str(dpi)]
        command += ["-singlefile"] if first_page_only else []
        command += [str(pdf), str(stem)]
    else:
        pattern = f"{stem}.png" if first_page_only else f"{stem}-%d.png"
        command = [
            str(executable),
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-dQUIET",
            "-sDEVICE=png16m",
            "-dTextAlphaBits=4",
            "-dGraphicsAlphaBits=4",
            f"-r{dpi}",
        ]
        command += ["-dFirstPage=1", "-dLastPage=1"] if first_page_only else []
        command += [f"-sOutputFile={pattern}", str(pdf)]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    images = _images(stem, first_page_only)
    if completed.returncode != 0 or not images:
        message = (completed.stderr or completed.stdout).strip().splitlines()
        return Preview(pdf, (), error=message[-1] if message else f"{kind} produced no image")
    return Preview(pdf, images)


def _images(stem: Path, first_page_only: bool) -> tuple[Path, ...]:
    """The images written for ``stem``: ``name.png``, or ``name-1.png``, ``name-2.png``...

    Matched exactly, so previewing ``kapp`` never touches the images of ``kapp2``.
    """
    if first_page_only:
        single = stem.with_name(f"{stem.name}.png")
        return (single,) if single.is_file() else ()
    pages = [
        image
        for image in stem.parent.glob(f"{stem.name}-*.png")
        if image.stem.removeprefix(f"{stem.name}-").isdigit()
    ]
    # pdftoppm pads page numbers (paper-01.png), Ghostscript does not: sort by the number.
    return tuple(sorted(pages, key=lambda image: int(image.stem.rsplit("-", 1)[-1])))
