"""The typeface catalogue: one choice, carried to LaTeX, Matplotlib, RDKit and TikZ."""

import io
import shutil
import subprocess
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import LabHarnessError, create_workspace, load_workspace
from labharness.style import available_typefaces, load_style, load_typeface, using_journal
from labharness.style.latex import document_preamble, tikz_preamble
from labharness.style.mpl import rcparams
from labharness.watch.runner import refresh_document_style

CATALOGUE = ["latin-modern", "termes", "pagella", "stix", "libertinus"]


def has_latex_package(name: str) -> bool:
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        return False
    found = subprocess.run([kpsewhich, f"{name}.sty"], capture_output=True, text=True)
    return bool(found.stdout.strip())


def pdf_fonts(pdf: bytes) -> set[str]:
    names: set[str] = set()
    for page in PdfReader(io.BytesIO(pdf)).pages:
        resources = page.get("/Resources")
        fonts = resources.get_object().get("/Font") if resources is not None else None
        for font in fonts.get_object().values() if fonts is not None else []:
            base = font.get_object().get("/BaseFont")
            if base is not None:
                names.add(str(base))
    return names


def test_the_catalogue_is_the_five_decided_typefaces() -> None:
    assert available_typefaces() == CATALOGUE


def test_an_unknown_typeface_lists_the_catalogue() -> None:
    with pytest.raises(LabHarnessError, match="latin-modern, termes"):
        load_typeface("comic-sans")


def test_the_journal_default_is_latin_modern() -> None:
    assert load_style("acs").typography.typeface == "latin-modern"


@pytest.mark.parametrize("typeface", CATALOGUE)
def test_a_typeface_reaches_every_engine(typeface: str) -> None:
    face = load_typeface(typeface)
    style = load_style("acs", typeface)

    for preamble in (document_preamble(style), tikz_preamble(style)):
        for package in face.latex_packages:
            assert f"\\usepackage{{{package}}}" in preamble
    params = rcparams(style)
    assert params["font.serif"] == [face.family]
    assert params["mathtext.fontset"] == face.mathtext
    # The sizes are the journal's, whatever the typeface.
    assert style.typography.base_size_pt == load_style("acs").typography.base_size_pt


def test_the_manifest_chooses_the_typeface(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_workspace(tmp_path / "paper")
    manifest = root / "labharness.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + 'font = "pagella"\n', "utf-8")
    monkeypatch.chdir(root / "scripts")

    assert load_workspace(root).font == "pagella"
    assert load_style().typography.family == "TeX Gyre Pagella"


def test_an_unknown_font_in_the_manifest_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text('font = "arial"\n', encoding="utf-8")

    with pytest.raises(LabHarnessError, match="unknown typeface 'arial'"):
        load_workspace(tmp_path)


def test_the_watcher_typeface_wins() -> None:
    with using_journal("acs", "stix"):
        assert load_style().typography.typeface == "stix"
    assert load_style().typography.typeface == "latin-modern"


def test_the_document_style_follows_a_new_typeface(tmp_path: Path) -> None:
    root = create_workspace(tmp_path / "paper")
    manifest = root / "labharness.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + 'font = "termes"\n', "utf-8")

    assert refresh_document_style(load_workspace(root))
    assert "\\usepackage{tgtermes}" in (root / "labharness-style.tex").read_text("utf-8")
    # Once it matches, nothing is rewritten.
    assert not refresh_document_style(load_workspace(root))


def test_a_style_file_written_by_hand_is_left_alone(tmp_path: Path) -> None:
    root = create_workspace(tmp_path / "paper")
    handmade = "% my own preamble\n\\usepackage{mathptmx}\n"
    (root / "labharness-style.tex").write_text(handmade, encoding="utf-8")

    assert not refresh_document_style(load_workspace(root))
    assert (root / "labharness-style.tex").read_text(encoding="utf-8") == handmade


@pytest.mark.latex
@pytest.mark.parametrize("typeface", CATALOGUE)
def test_a_document_in_each_typeface_uses_only_that_typeface(tmp_path: Path, typeface: str) -> None:
    face = load_typeface(typeface)
    if shutil.which("pdflatex") is None or not all(map(has_latex_package, face.latex_packages)):
        pytest.skip(f"needs pdflatex and {', '.join(face.latex_packages)}")
    document = tmp_path / "paper.tex"
    document.write_text(
        "\\documentclass{article}\n"
        + document_preamble(load_style("acs", typeface))
        + "\\begin{document}\nText, \\emph{italic}, $k_\\mathrm{obs} = \\alpha x^2$.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", document.name],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    fonts = pdf_fonts((tmp_path / "paper.pdf").read_bytes())
    assert fonts
    assert all(face.owns_pdf_font(font) for font in fonts), sorted(fonts)


@pytest.mark.latex
@pytest.mark.parametrize("typeface", CATALOGUE)
def test_a_plot_in_each_typeface_embeds_that_typeface(tmp_path: Path, typeface: str) -> None:
    matplotlib = pytest.importorskip("matplotlib", reason="needs the plots extra")
    matplotlib.use("Agg")
    pyplot = pytest.importorskip("matplotlib.pyplot")
    pytest.importorskip("matplotlib.font_manager")
    from labharness.style.mpl import apply

    style = load_style("acs", typeface)
    try:
        apply(matplotlib, style)
    except LabHarnessError as error:
        pytest.skip(str(error))

    figure, axes = pyplot.subplots()
    axes.set_xlabel("Time (min)")
    axes.set_ylabel("$C/C_0$")
    figure.savefig(tmp_path / "plot.pdf")
    pyplot.close(figure)

    fonts = {font.split("+")[-1] for font in pdf_fonts((tmp_path / "plot.pdf").read_bytes())}
    face = load_typeface(typeface)
    text_fonts = [font for font in fonts if face.owns_pdf_font(font)]
    assert text_fonts, sorted(fonts)
