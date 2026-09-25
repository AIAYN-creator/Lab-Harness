"""The lab compound inventory: read as it is exported, checked, never corrected."""

import shutil
import warnings
from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core import LabHarnessError, load_workspace

pytest.importorskip("rdkit")

from labharness.modules.chem import check, load_library, render_structure  # noqa: E402
from labharness.modules.chem.library import workspace_library  # noqa: E402

runner = CliRunner()

# As Access exports it: Spanish headers with accents, a broken row, a chiral compound without
# stereochemistry and a formula that belongs to another row.
INVENTORY = """\
Código;Nombre común;SMILES;Fórmula;Alias
CAT-7B;(S)-t-Bu-PyOx;CC(C)(C)[C@@H]1COC(=N1)c1ccccn1;C12H16N2O;PyOx
LAC-1;ácido láctico;CC(O)C(=O)O;C3H6O3;
IPA;isopropanol;CC(C)O;C3H8O;
BAD-3;roto;C1CC(;C3H6;
ACE;acetona;CC(C)=O;C3H6O3;
"""


@pytest.fixture
def inventory(tmp_path: Path) -> Path:
    path = tmp_path / "inventario.csv"
    path.write_text(INVENTORY, encoding="utf-8")
    return path


def test_an_access_export_is_read_as_it_is(inventory: Path) -> None:
    library = load_library(inventory)

    assert [compound.code for compound in library.compounds] == ["CAT-7B", "LAC-1", "IPA", "ACE"]
    assert library.compounds[0].aliases == ("PyOx",)


def test_a_compound_is_found_by_name_code_or_alias_but_never_by_likeness(inventory: Path) -> None:
    library = load_library(inventory)

    assert library.find("cat-7b") is library.compounds[0]
    assert library.find("PYOX") is library.compounds[0]
    assert library.find("Acido Lactico") is library.compounds[1]  # no case, no accents
    assert library.find("CAT-7") is None
    assert library.find("ácido") is None


def test_a_broken_row_is_left_out_with_its_row_and_the_rest_is_used(inventory: Path) -> None:
    library = load_library(inventory)

    assert library.rejected == ("row 5 (roto): RDKit cannot read the SMILES 'C1CC('",)


def test_a_chiral_compound_without_stereochemistry_is_flagged(inventory: Path) -> None:
    library = load_library(inventory)
    lactic, isopropanol, pyox = (library.find(key) for key in ("LAC-1", "IPA", "CAT-7B"))
    assert lactic and isopropanol and pyox

    assert any("stereocentre at C2 is not specified" in text for text in check(lactic))
    assert check(isopropanol) == []  # achiral: nothing to specify
    assert check(pyox) == []  # specified


def test_a_double_bond_without_e_or_z_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "i.csv"
    path.write_text("name;smiles\nbut-2-ene;CC=CC\n(E)-but-2-ene;C/C=C/C\n", encoding="utf-8")
    library = load_library(path)

    assert check(library.compounds[0]) == ["double bond 2 has no E/Z in the SMILES"]
    assert check(library.compounds[1]) == []


def test_a_formula_that_does_not_match_its_smiles_is_flagged(inventory: Path) -> None:
    library = load_library(inventory)

    assert library.findings[-1] == (
        "row 6 (ACE): the formula C3H6O3 does not match the SMILES, which is C3H6O"
    )


def test_headers_it_does_not_know_are_mapped_in_the_manifest(tmp_path: Path) -> None:
    path = tmp_path / "i.csv"
    path.write_text("Ref;Producto;SMILES_canon\nX1;etanol;CCO\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match=r"no column for the smiles.*\[library\]"):
        load_library(path)
    library = load_library(path, columns={"smiles": "SMILES_canon", "name": "Producto"})
    assert library.find("etanol") is not None


def workspace_with(tmp_path: Path, inventory: Path, library: str) -> Path:
    root = tmp_path / "paper"
    (root / "data").mkdir(parents=True)
    shutil.copy(inventory, root / "data" / "inventario.csv")
    (root / "labharness.toml").write_text(library, encoding="utf-8")
    return root


def test_the_manifest_names_the_library(tmp_path: Path, inventory: Path) -> None:
    root = workspace_with(
        tmp_path,
        inventory,
        '[library]\nfile = "data/inventario.csv"\ncolumns = { name = "Nombre común" }\n',
    )

    settings = load_workspace(root).library

    assert settings is not None
    assert settings.file == Path("data/inventario.csv")
    assert settings.columns == (("name", "Nombre común"),)


def test_resolve_looks_in_the_library_first_and_says_so(
    tmp_path: Path, inventory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = workspace_with(tmp_path, inventory, '[library]\nfile = "data/inventario.csv"\n')
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["resolve", "LAC-1", "-o", "data/lactico.smi"])

    assert result.exit_code == 0, result.stdout
    assert "from the lab library" in result.stdout
    assert "stereocentre" in result.stdout
    written = (root / "data" / "lactico.smi").read_text(encoding="utf-8")
    assert written == "CC(O)C(=O)O\n# from library: inventario.csv, row 3 (LAC-1)\n"


def test_a_library_that_cannot_be_read_is_skipped_not_fatal(
    tmp_path: Path, inventory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = workspace_with(tmp_path, inventory, '[library]\nfile = "data/missing.csv"\n')
    monkeypatch.chdir(root)

    library, problem = workspace_library()

    assert library is None
    assert problem is not None and "missing.csv" in problem


def test_library_check_reports_every_row_to_review(
    tmp_path: Path, inventory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = workspace_with(tmp_path, inventory, '[library]\nfile = "data/inventario.csv"\n')
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["library", "check"])

    assert result.exit_code == 1
    assert "4 compounds read" in result.stdout
    assert "row 3 (LAC-1)" in result.stdout and "row 5 (roto)" in result.stdout
    assert "row 6 (ACE)" in result.stdout
    assert "Nothing in the inventory was changed" in result.stdout


@pytest.mark.skipif(
    shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution for the font"
)
def test_a_figure_draws_a_compound_by_its_code_and_warns_about_it(
    tmp_path: Path, inventory: Path
) -> None:
    output = tmp_path / "lactic.pdf"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        render_structure(output=output, compound="LAC-1", library=inventory)

    assert output.read_bytes().startswith(b"%PDF")
    assert any("LAC-1: the stereocentre" in str(warning.message) for warning in caught)
    with pytest.raises(LabHarnessError, match="'NOPE' is not in inventario.csv"):
        render_structure(output=output, compound="NOPE", library=inventory)
