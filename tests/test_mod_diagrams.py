"""The diagrams module: a TikZ or chemfig source in, a vector PDF out."""

import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import LabHarnessError
from labharness.modules.diagrams import build_document, render_diagram
from labharness.style import load_style

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "figures"

needs_latex = pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="needs a LaTeX distribution"
)

SIMPLE = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"


def test_the_shared_style_is_always_wrapped_around_the_drawing() -> None:
    document = build_document(SIMPLE, load_style())

    assert document.startswith(r"\documentclass[border=2pt]{standalone}")
    assert r"\usepackage{lmodern}" in document  # the document typeface, not a choice of the figure
    assert "atom sep = 14.4pt" in document  # the journal geometry
    assert SIMPLE in document


def test_a_missing_source_says_so(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="does not exist"):
        render_diagram(tmp_path / "nope.tex", tmp_path / "out.pdf")


@pytest.mark.latex
@needs_latex
def test_a_drawing_becomes_a_vector_pdf(tmp_path: Path) -> None:
    source = tmp_path / "diagram.tex"
    source.write_text(SIMPLE, encoding="utf-8")

    output = render_diagram(source, tmp_path / "figures" / "diagram.pdf")

    assert output.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(str(output)).pages) == 1


@pytest.mark.latex
@needs_latex
@pytest.mark.parametrize("template", ["mechanism", "flow", "network"])
def test_every_shipped_template_compiles(template: str, tmp_path: Path) -> None:
    output = render_diagram(TEMPLATES / f"{template}.tex", tmp_path / f"{template}.pdf")

    assert output.is_file()


@pytest.mark.latex
@needs_latex
def test_a_mechanism_uses_the_document_typeface(tmp_path: Path) -> None:
    output = render_diagram(TEMPLATES / "mechanism.tex", tmp_path / "mechanism.pdf")

    fonts = set()
    for page in PdfReader(str(output)).pages:
        resources = page.get("/Resources")
        fonts_in_page = resources.get_object().get("/Font") if resources else None
        for font in fonts_in_page.get_object().values() if fonts_in_page else []:
            base = font.get_object().get("/BaseFont")
            if base is not None:
                fonts.add(str(base).lstrip("/").split("+")[-1])

    assert fonts, "the mechanism has no text in it"
    assert all(font.startswith("LM") for font in fonts), fonts


@pytest.mark.latex
@needs_latex
def test_a_broken_drawing_explains_what_latex_said(tmp_path: Path) -> None:
    source = tmp_path / "broken.tex"
    source.write_text(r"\begin{tikzpicture}\draw (0,0) -- (1,1);", encoding="utf-8")

    with pytest.raises(LabHarnessError) as error:
        render_diagram(source, tmp_path / "broken.pdf")

    assert "broken.tex" in str(error.value)
    assert "!" in str(error.value)
