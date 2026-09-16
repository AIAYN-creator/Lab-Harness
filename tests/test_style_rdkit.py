"""The RDKit translator must match the drawing options RDKit actually exposes."""

import pytest

from labharness.style import load_style
from labharness.style.rdkit import apply_to_draw_options

rdMolDraw2D = pytest.importorskip("rdkit.Chem.Draw.rdMolDraw2D", reason="needs the chem extra")
Chem = pytest.importorskip("rdkit.Chem", reason="needs the chem extra")


def test_draw_options_take_the_journal_geometry_and_font() -> None:
    style = load_style("acs")
    drawer = rdMolDraw2D.MolDraw2DSVG(200, 200)

    apply_to_draw_options(drawer.drawOptions(), style)

    options = drawer.drawOptions()
    assert options.fixedBondLength == style.structures.bond_length_pt
    assert options.bondLineWidth == style.structures.line_width_pt
    assert options.fontFile.endswith(".otf")


def test_a_molecule_still_draws_with_the_style_applied() -> None:
    style = load_style("acs")
    drawer = rdMolDraw2D.MolDraw2DSVG(200, 200)
    apply_to_draw_options(drawer.drawOptions(), style)

    molecule = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, molecule)
    drawer.FinishDrawing()

    assert drawer.GetDrawingText().startswith("<?xml")
