"""The ACS workspace template must compile, and everything in it must use one typeface."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "workspace" / "journals" / "acs"

pytestmark = [
    pytest.mark.latex,
    pytest.mark.skipif(shutil.which("pdflatex") is None, reason="needs a LaTeX distribution"),
]


@pytest.fixture(scope="module")
def compiled_pdf(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    workspace = tmp_path_factory.mktemp("acs")
    for source in TEMPLATE.iterdir():
        shutil.copy(source, workspace / source.name)

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    pdf = workspace / "paper.pdf"
    assert result.returncode == 0 and pdf.exists(), result.stdout[-3000:]
    return pdf.read_bytes()


def test_every_embedded_font_is_latin_modern(compiled_pdf: bytes) -> None:
    # Subset fonts are named like ABCDEF+LMRoman10-Regular.
    fonts = set(re.findall(rb"/BaseFont\s*/(?:[A-Z]{6}\+)?([A-Za-z0-9\-]+)", compiled_pdf))
    assert fonts, "no embedded fonts found in the compiled PDF"
    assert all(font.startswith(b"LM") for font in fonts), fonts


def test_missing_figures_do_not_break_the_build(compiled_pdf: bytes) -> None:
    # The template references figures/example.pdf, which does not exist: \labfigure must
    # fall back to a placeholder instead of failing the compilation.
    assert compiled_pdf.startswith(b"%PDF")
