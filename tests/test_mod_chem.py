"""The chemistry module: SMILES in, vector PDF out."""

import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import LabHarnessError, LabHarnessWarning
from labharness.modules.chem import read_smiles, render_structure, resolve_name
from labharness.style import load_style

ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"


def _has(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


drawing = pytest.mark.skipif(
    not _has("rdkit") or shutil.which("kpsewhich") is None,
    reason="needs the chem extra and a LaTeX distribution for the font",
)


def test_reading_a_smi_file_ignores_comments_and_names(tmp_path: Path) -> None:
    path = tmp_path / "catalyst.smi"
    path.write_text(f"# resolved from: aspirin\n\n{ASPIRIN} aspirin\n", encoding="utf-8")

    assert read_smiles(path) == ASPIRIN


def test_reading_a_file_without_a_smiles_says_so(tmp_path: Path) -> None:
    path = tmp_path / "empty.smi"
    path.write_text("# only a comment\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="no SMILES"):
        read_smiles(path)


def test_asking_for_both_or_neither_input_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="one of .smiles., .smiles_file. or .compound."):
        render_structure(tmp_path / "out.pdf")

    with pytest.raises(LabHarnessError, match="one of .smiles., .smiles_file. or .compound."):
        render_structure(tmp_path / "out.pdf", smiles=ASPIRIN, smiles_file=tmp_path / "x.smi")


def page_size(pdf: Path) -> tuple[float, float]:
    box = PdfReader(str(pdf)).pages[0].mediabox
    return float(box.width), float(box.height)


@drawing
def test_a_structure_becomes_a_vector_pdf_cropped_to_the_molecule(tmp_path: Path) -> None:
    style = load_style()
    output = render_structure(tmp_path / "figures" / "aspirin.pdf", smiles=ASPIRIN)

    assert output.is_file()
    page = PdfReader(str(output)).pages[0]
    width_pt, height_pt = page_size(output)
    column_pt = style.dimensions.single_column_in * 72
    # Narrower than the column and shorter than the old 4:3 canvas: no blank area around it.
    assert width_pt < column_pt
    assert height_pt < column_pt / style.dimensions.aspect_ratio
    # Vector, not a bitmap: the page holds no image objects.
    xobjects = page.get("/Resources", {}).get("/XObject", {})
    subtypes = [xobjects[name].get_object().get("/Subtype") for name in xobjects]
    assert "/Image" not in subtypes


@drawing
def test_a_structure_can_be_drawn_from_a_file(tmp_path: Path) -> None:
    source = tmp_path / "aspirin.smi"
    source.write_text(f"{ASPIRIN}\n", encoding="utf-8")

    output = render_structure(tmp_path / "aspirin.pdf", smiles_file=source)

    assert output.read_bytes().startswith(b"%PDF")


@drawing
def test_an_invalid_smiles_leaves_the_previous_figure_alone(tmp_path: Path) -> None:
    output = tmp_path / "structure.pdf"
    render_structure(output, smiles=ASPIRIN)
    good = output.read_bytes()

    with pytest.raises(LabHarnessError, match="not a valid SMILES"):
        render_structure(output, smiles="this is not a molecule")

    assert output.read_bytes() == good
    assert not list(tmp_path.glob(".*.tmp")), "a temporary file was left behind"


@pytest.mark.skipif(
    not _has("py2opsin") or shutil.which("java") is None, reason="needs the iupac extra and Java"
)
def test_a_iupac_name_resolves_offline_to_a_canonical_smiles(tmp_path: Path) -> None:
    output = tmp_path / "ethanol.smi"

    smiles = resolve_name("ethanol", output=output)

    assert smiles == "CCO"
    written = output.read_text(encoding="utf-8")
    assert written.startswith("CCO")
    assert "resolved from: ethanol" in written


@pytest.mark.skipif(
    not _has("py2opsin") or shutil.which("java") is None, reason="needs the iupac extra and Java"
)
def test_a_name_opsin_cannot_read_explains_what_it_understands() -> None:
    with pytest.raises(LabHarnessError, match="systematic IUPAC names"):
        resolve_name("BINAP")


def test_an_empty_name_is_rejected() -> None:
    with pytest.raises(LabHarnessError, match="chemical name"):
        resolve_name("   ")


ATENOLOL = "CC(C)NCC(O)COc1ccc(CC(N)=O)cc1"
# A straight chain: its bonds are all C-C, so one SVG path is one whole bond.
LONG_CHAIN = "C" * 60


def bond_length(smiles: str, width_in: float | None = None) -> float:
    """The length on paper, in points, of the first bond RDKit draws."""
    import math
    import re

    from labharness.modules.chem.structures import _draw_svg

    style = load_style()
    box = (width_in or style.dimensions.single_column_in) * 72
    svg, _ = _draw_svg(smiles, style, box, box * style.structures.max_height_ratio, "test")
    match = re.search(r"class='bond-0[^']*' d='M ([0-9.]+),([0-9.]+) L ([0-9.]+),([0-9.]+)", svg)
    assert match is not None
    x1, y1, x2, y2 = map(float, match.groups())
    return math.hypot(x2 - x1, y2 - y1)


@drawing
def test_a_small_molecule_grows_to_fill_the_room_but_no_further_than_the_cap() -> None:
    style = load_style()
    most = style.structures.bond_length_pt * style.structures.max_bond_scale

    # Butane has room to spare in a column: its bonds grow, and stop at the cap.
    assert bond_length("CCCC") == pytest.approx(most, rel=0.05)


@drawing
def test_a_long_molecule_fills_the_width_it_is_given(tmp_path: Path) -> None:
    style = load_style()
    column = style.dimensions.single_column_in
    in_column = render_structure(tmp_path / "column.pdf", smiles=ATENOLOL)
    # A single-column report gives the text width, and the same molecule uses it.
    # 30 carbons fit 5.7 in at the journal bond length, but not at the cap: they fill it.
    in_text = render_structure(tmp_path / "text.pdf", smiles=LONG_CHAIN[:30], width_in=5.7)

    assert page_size(in_column)[0] <= column * 72 + 0.5
    assert page_size(in_text)[0] == pytest.approx(5.7 * 72, abs=2)


@drawing
def test_a_molecule_too_big_for_the_room_shrinks_to_fit_and_says_so(tmp_path: Path) -> None:
    column_pt = load_style().dimensions.single_column_in * 72

    with pytest.warns(LabHarnessWarning, match="does not fit"):
        output = render_structure(tmp_path / "chain.pdf", smiles=LONG_CHAIN)

    width_pt, height_pt = page_size(output)
    assert width_pt == pytest.approx(column_pt, abs=1)
    assert height_pt < width_pt / 3  # cropped in height too: no band of blank canvas
    assert bond_length(LONG_CHAIN) < load_style().structures.bond_length_pt


@drawing
def test_a_structure_is_never_taller_than_the_style_allows(tmp_path: Path) -> None:
    style = load_style()
    # Drawn vertically by RDKit's layout of a spiro stack, or simply a tall cage.
    output = render_structure(
        tmp_path / "tall.pdf", smiles="C1CC2(C1)CC1(C2)CC2(C1)CC1(C2)CC2(C1)CC2"
    )

    width_pt, height_pt = page_size(output)
    assert (
        height_pt <= style.dimensions.single_column_in * 72 * style.structures.max_height_ratio + 1
    )


@drawing
def test_the_atenolol_of_the_demo_fits_a_column_at_the_journal_bond_length() -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", LabHarnessWarning)
        assert bond_length(ATENOLOL) >= load_style().structures.bond_length_pt
