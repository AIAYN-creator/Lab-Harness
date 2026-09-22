"""`labharness preview`: figures as images, so a person or an agent can look at them."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

import pytest
from pypdf import PdfWriter
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core import LabHarnessError, create_workspace, load_workspace
from labharness.preview import (
    GHOSTSCRIPT,
    PREVIEW_FOLDER,
    find_rasteriser,
    preview_document,
    preview_figures,
)

runner = CliRunner()
PNG = b"\x89PNG\r\n\x1a\n"
Test = TypeVar("Test", bound=Callable[..., None])


def needs_a_rasteriser(test: Test) -> Test:
    """Runs in the LaTeX CI jobs, which install pdftoppm; skipped where there is none."""
    skip = pytest.mark.skipif(find_rasteriser() is None, reason="needs pdftoppm or Ghostscript")
    return cast(Test, pytest.mark.latex(skip(test)))


def blank_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    workspace = create_workspace(tmp_path / "paper")
    manifest = workspace / "labharness.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + '\n[[figure]]\noutput = "figures/kapp.pdf"\nscript = "scripts/kapp.py"\n'
        + '\n[[figure]]\noutput = "figures/kapp2.pdf"\nscript = "scripts/kapp2.py"\n',
        encoding="utf-8",
    )
    blank_pdf(workspace / "figures" / "kapp.pdf")
    blank_pdf(workspace / "figures" / "kapp2.pdf")
    return workspace


@needs_a_rasteriser
def test_every_figure_becomes_an_image(root: Path) -> None:
    results = preview_figures(load_workspace(root))

    assert [result.ok for result in results] == [True, True]
    images = [image for result in results for image in result.images]
    assert [image.name for image in images] == ["kapp.png", "kapp2.png"]
    assert all(image.parent == root / PREVIEW_FOLDER for image in images)
    assert all(image.read_bytes().startswith(PNG) for image in images)


@needs_a_rasteriser
def test_previewing_one_figure_leaves_a_similar_name_alone(root: Path) -> None:
    workspace = load_workspace(root)
    preview_figures(workspace)
    kapp2 = root / PREVIEW_FOLDER / "kapp2.png"
    before = kapp2.stat().st_mtime_ns

    preview_figures(workspace, [workspace.figures[0]])

    assert kapp2.is_file()
    assert kapp2.stat().st_mtime_ns == before


@needs_a_rasteriser
def test_the_document_gives_one_image_per_page_in_order(root: Path) -> None:
    blank_pdf(root / "paper.pdf", pages=11)

    result = preview_document(load_workspace(root))

    assert result.ok, result.error
    assert len(result.images) == 11
    numbers = [int(image.stem.rsplit("-", 1)[-1]) for image in result.images]
    assert numbers == list(range(1, 12))


@pytest.mark.latex
@pytest.mark.skipif(not any(shutil.which(name) for name in GHOSTSCRIPT), reason="needs Ghostscript")
def test_ghostscript_works_when_there_is_no_pdftoppm(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ghostscript = next(Path(found) for name in GHOSTSCRIPT if (found := shutil.which(name)))
    monkeypatch.setattr("labharness.preview.find_rasteriser", lambda: ("ghostscript", ghostscript))
    blank_pdf(root / "paper.pdf", pages=2)
    workspace = load_workspace(root)

    figures = preview_figures(workspace)
    document = preview_document(workspace)

    assert all(result.ok for result in figures), [result.error for result in figures]
    assert [image.name for image in document.images] == ["paper-1.png", "paper-2.png"]


@needs_a_rasteriser
def test_a_figure_not_built_yet_is_reported_not_raised(root: Path) -> None:
    (root / "figures" / "kapp2.pdf").unlink()

    results = preview_figures(load_workspace(root))

    assert results[0].ok
    assert not results[1].ok
    assert "not been built" in (results[1].error or "")


def test_without_a_rasteriser_the_error_says_what_to_install(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("labharness.preview.shutil.which", lambda name: None)

    assert find_rasteriser() is None
    with pytest.raises(LabHarnessError, match="poppler"):
        preview_figures(load_workspace(root))


@needs_a_rasteriser
def test_the_command_line_prints_where_each_image_is(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["preview", "--only", "kapp"])

    assert result.exit_code == 0, result.stdout
    assert "figures/kapp.pdf  ->  .labharness/preview/kapp.png" in result.stdout


def test_the_command_line_fails_clearly_without_a_rasteriser(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(root)
    monkeypatch.setattr("labharness.preview.shutil.which", lambda name: None)

    result = runner.invoke(app, ["preview"])

    assert result.exit_code == 1
    assert "pdftoppm" in result.stdout


def test_doctor_reports_the_preview_tool() -> None:
    result = runner.invoke(app, ["doctor"])

    assert "figure previews" in result.stdout
