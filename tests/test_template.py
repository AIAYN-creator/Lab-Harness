"""Every workspace template must compile, and everything in it must use one typeface."""

import io
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import create_workspace
from labharness.core.lock import check_data
from labharness.core.templates import available_journals
from labharness.doctor import _tex_file
from labharness.style.typefaces import available_typefaces, load_typeface
from labharness.watch.latex import compile_document

pytestmark = [
    pytest.mark.latex,
    pytest.mark.skipif(shutil.which("pdflatex") is None, reason="needs a LaTeX distribution"),
]


@pytest.fixture(scope="module", params=available_journals())
def compiled_pdf(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> bytes:
    """A new workspace for each journal, built the way labharness build does it."""
    # Through init, as a user would get it: the style file is generated, not shipped.
    journal = str(request.param)
    workspace = create_workspace(tmp_path_factory.mktemp(journal), journal=journal, force=True)
    check_data(workspace)

    result = compile_document(workspace / "paper.tex")

    assert result.ok and result.pdf is not None, (journal, result.errors)
    return result.pdf.read_bytes()


def embedded_fonts(pdf: bytes) -> set[str]:
    """Base font names used by the document, read through a real PDF parser.

    Reading the raw bytes is not enough: pdfTeX stores these entries inside compressed
    object streams, and whether they end up in the clear depends on the distribution.
    """
    names: set[str] = set()
    for page in PdfReader(io.BytesIO(pdf)).pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        fonts = resources.get_object().get("/Font")
        if fonts is None:
            continue
        for font in fonts.get_object().values():
            base_font = font.get_object().get("/BaseFont")
            if base_font is not None:
                # Subset fonts are named like ABCDEF+LMRoman10-Regular.
                names.add(str(base_font).lstrip("/").split("+")[-1])
    return names


def test_every_embedded_font_is_latin_modern(compiled_pdf: bytes) -> None:
    fonts = embedded_fonts(compiled_pdf)
    assert fonts, "no fonts found in the compiled PDF"
    assert all(font.startswith("LM") for font in fonts), fonts


def test_missing_figures_do_not_break_the_build(compiled_pdf: bytes) -> None:
    # The template references figures/example.pdf, which does not exist: \labfigure must
    # fall back to a placeholder instead of failing the compilation.
    assert compiled_pdf.startswith(b"%PDF")


@pytest.mark.parametrize("typeface", available_typefaces())
@pytest.mark.parametrize("journal", available_journals())
def test_every_template_in_every_typeface_embeds_only_that_typeface(
    tmp_path: Path, journal: str, typeface: str
) -> None:
    face = load_typeface(typeface)
    if not all(_tex_file(f"{package}.sty") for package in face.latex_packages):
        pytest.skip(f"needs {', '.join(face.latex_packages)}")
    workspace = create_workspace(tmp_path / journal, journal=journal, font=typeface)
    check_data(workspace)

    result = compile_document(workspace / "paper.tex")

    assert result.ok and result.pdf is not None, (journal, typeface, result.errors)
    fonts = embedded_fonts(result.pdf.read_bytes())
    assert fonts
    assert all(face.owns_pdf_font(font) for font in fonts), (journal, typeface, sorted(fonts))
