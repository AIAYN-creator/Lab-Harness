"""labharness cite: a DOI in, an entry in the bibliography and a key to cite it with."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core import LabHarnessError
from labharness.core import cite as cite_module
from labharness.core.cite import cite, normalise_doi

runner = CliRunner()

# What doi.org answers for this DOI, from Crossref: one line, with its own key.
CROSSREF = (
    " @article{Mora_G_mez_2020, title={Influence of the reactor configuration}, volume={241}, "
    "ISSN={1383-5866}, url={http://dx.doi.org/10.1016/j.seppur.2020.116684}, "
    "DOI={10.1016/j.seppur.2020.116684}, journal={Separation and Purification Technology}, "
    "publisher={Elsevier BV}, author={Mora-Gómez, J. and García-Gabaldón, M.}, year={2020}, "
    "pages={116684} }\n"
)
DOI = "10.1016/j.seppur.2020.116684"


@pytest.fixture
def doi_org(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    asked: list[str] = []

    def answer(doi: str) -> str:
        asked.append(doi)
        return CROSSREF

    monkeypatch.setattr(cite_module, "fetch_bibtex", answer)
    return asked


@pytest.mark.parametrize(
    "written", [DOI, f"doi:{DOI}", f"https://doi.org/{DOI}", f"https://doi.org/{DOI}."]
)
def test_a_doi_is_read_however_it_is_pasted(written: str) -> None:
    assert normalise_doi(written) == DOI


def test_something_that_is_not_a_doi_says_what_one_looks_like() -> None:
    with pytest.raises(LabHarnessError, match="looks like 10."):
        normalise_doi("Mora-Gómez 2020")


def test_the_work_is_added_under_a_short_key(tmp_path: Path, doi_org: list[str]) -> None:
    bib = tmp_path / "references.bib"
    bib.write_text("% the bibliography\n", encoding="utf-8")

    citation = cite(DOI, bib)

    assert (citation.key, citation.added) == ("moragomez2020", True)
    text = bib.read_text(encoding="utf-8")
    assert text.startswith("% the bibliography\n\n@article{moragomez2020,")
    assert "Mora_G_mez_2020" not in text


def test_a_doi_already_there_is_not_added_twice_nor_fetched(
    tmp_path: Path, doi_org: list[str]
) -> None:
    bib = tmp_path / "references.bib"
    bib.write_text("@article{mine, title = {X}, doi = {10.1016/J.SEPPUR.2020.116684}}\n", "utf-8")

    citation = cite(f"https://doi.org/{DOI}", bib)

    assert (citation.key, citation.added) == ("mine", False)
    assert doi_org == []


def test_a_taken_key_gets_a_letter(tmp_path: Path, doi_org: list[str]) -> None:
    bib = tmp_path / "references.bib"
    bib.write_text("@article{moragomez2020, doi = {10.1/other}}\n", encoding="utf-8")

    assert cite(DOI, bib).key == "moragomez2020a"


def test_the_command_says_how_to_cite_it(
    tmp_path: Path, doi_org: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "labharness.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["cite", DOI])

    assert result.exit_code == 0, result.stdout
    assert "Added moragomez2020 to references.bib" in result.stdout
    assert "\\cite{moragomez2020}" in result.stdout
    assert (tmp_path / "references.bib").is_file()
