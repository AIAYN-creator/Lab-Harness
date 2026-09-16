import shutil
from pathlib import Path

import pytest

from labharness.core import LabHarnessError
from labharness.style import available_journals, find_font_file, load_style
from labharness.style.latex import document_preamble, tikz_preamble
from labharness.style.mpl import palette, rcparams

TEMPLATE_STYLE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "workspace"
    / "journals"
    / "acs"
    / "labharness-style.tex"
)


def test_acs_style_loads_with_the_acs_1996_geometry() -> None:
    style = load_style("acs")

    assert style.name == "acs"
    assert style.structures.bond_length_pt == 14.4
    assert style.structures.line_width_pt == 0.6
    assert style.dimensions.single_column_in == 3.25
    assert style.typography.latex_package == "lmodern"


def test_acs_is_the_default_and_the_only_journal_in_v0_1() -> None:
    assert load_style() == load_style("acs")
    assert available_journals() == ["acs"]


def test_an_unknown_journal_says_which_ones_exist() -> None:
    with pytest.raises(LabHarnessError, match="acs"):
        load_style("nature")


def test_axis_labels_follow_the_journal_format() -> None:
    style = load_style()

    assert style.axis_label("Concentration", "mM") == "Concentration (mM)"
    assert style.axis_label("Absorbance") == "Absorbance"
    assert style.axis_label("Absorbance", None) == "Absorbance"


def test_the_workspace_template_is_what_the_style_generates() -> None:
    # The template shipped to users must not drift from the style: it is generated from it.
    generated = document_preamble(load_style("acs"))
    on_disk = TEMPLATE_STYLE.read_text(encoding="utf-8")

    assert generated.splitlines() == on_disk.splitlines()


def test_the_tikz_preamble_carries_the_same_typeface_and_geometry() -> None:
    style = load_style()
    preamble = tikz_preamble(style)

    assert r"\usepackage{lmodern}" in preamble
    assert "atom sep = 14.4pt" in preamble
    assert "line width = 0.6pt" in preamble
    # Arrow pushing styles, which is why diagrams use TikZ and chemfig instead of RDKit.
    assert "electron pair/.style" in preamble
    assert "single electron/.style" in preamble


def test_matplotlib_settings_come_from_the_style() -> None:
    style = load_style()
    params = rcparams(style)

    assert params["font.serif"] == ["Latin Modern Roman"]
    assert params["font.size"] == style.typography.base_size_pt
    assert params["axes.grid"] is False
    assert params["pdf.fonttype"] == 42
    # Final printed size: one ACS column wide.
    assert params["figure.figsize"][0] == style.dimensions.single_column_in
    assert rcparams(style, width_in=7.0)["figure.figsize"][0] == 7.0


def test_the_palette_starts_in_black_and_is_colour_blind_safe() -> None:
    colours = palette(load_style())

    assert colours[0] == "#000000"
    assert "#E69F00" in colours  # Okabe-Ito orange
    assert len(colours) == len(set(colours))


@pytest.mark.skipif(shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution")
def test_the_document_font_is_found_in_the_latex_installation() -> None:
    font = find_font_file(load_style().typography.font_file)

    assert font.is_file()
    assert font.suffix == ".otf"


@pytest.mark.skipif(shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution")
def test_a_missing_font_explains_how_to_install_it() -> None:
    with pytest.raises(LabHarnessError, match="Latin Modern"):
        find_font_file("labharness-no-such-font.otf")


def test_without_latex_the_error_says_to_install_a_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("labharness.style.fonts.shutil.which", lambda name: None)

    with pytest.raises(LabHarnessError, match="LaTeX distribution"):
        find_font_file("labharness-font-without-kpsewhich.otf")


@pytest.mark.skipif(shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution")
def test_matplotlib_gets_the_font_registered_not_just_named() -> None:
    matplotlib = pytest.importorskip("matplotlib", reason="needs the plots extra")
    pytest.importorskip("matplotlib.font_manager")  # the registry lives in this submodule

    from labharness.style.mpl import apply

    apply(matplotlib, load_style())

    known = {font.name for font in matplotlib.font_manager.fontManager.ttflist}
    assert matplotlib.rcParams["font.serif"][0] in known
