"""`labharness add`: one call writes the script, the manifest entry and, if asked, the LaTeX."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from labharness.cli import app
from labharness.core import LabHarnessError, create_workspace, load_workspace
from labharness.core.add import KINDS, add_figure

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    workspace = create_workspace(tmp_path / "paper")
    (workspace / "data" / "kinetics.csv").write_text(
        "t;c\n0;1,00\n5;0,61\n10;0,37\n", encoding="utf-8"
    )
    return workspace


def test_a_plot_reads_its_columns_from_the_csv(root: Path) -> None:
    added = add_figure(load_workspace(root), "plot", "kinetics", [Path("data/kinetics.csv")])

    script = (root / added.script).read_text(encoding="utf-8")
    assert added.script == Path("scripts/kinetics.py")
    assert 'Series(csv="data/kinetics.csv", x="t", y="c")' in script
    assert script.startswith("# figures/kinetics.pdf --")
    assert added.notes == []


def test_the_new_figure_is_in_the_manifest_and_the_comments_survive(root: Path) -> None:
    add_figure(load_workspace(root), "plot", "kinetics", [Path("data/kinetics.csv")])

    manifest = (root / "labharness.toml").read_text(encoding="utf-8")
    figure = load_workspace(root).figures[0]
    assert "# LabHarness manifest" in manifest
    assert figure.output == Path("figures/kinetics.pdf")
    assert figure.script == Path("scripts/kinetics.py")
    assert figure.inputs == (Path("data/kinetics.csv"),)


def test_a_structure_reads_its_smiles_from_data_by_default(root: Path) -> None:
    added = add_figure(load_workspace(root), "structure", "catalyst")

    assert added.inputs == (Path("data/catalyst.smi"),)
    assert 'smiles_file="data/catalyst.smi"' in (root / added.script).read_text("utf-8")
    # data/ belongs to the human: add never creates the SMILES, it says it is missing.
    assert not (root / "data" / "catalyst.smi").exists()
    assert any("does not exist yet" in note for note in added.notes)


@pytest.mark.parametrize("kind", ["mechanism", "flow", "network"])
def test_diagrams_start_from_their_commented_template(root: Path, kind: str) -> None:
    added = add_figure(load_workspace(root), kind, "scheme")

    text = (root / added.script).read_text(encoding="utf-8")
    assert added.script == Path("scripts/scheme.tex")
    assert text.startswith("% figures/scheme.pdf --")
    assert r"\begin{tikzpicture}" in text


def test_every_kind_has_a_template(root: Path) -> None:
    for number, kind in enumerate(KINDS):
        add_figure(load_workspace(root), kind, f"figure{number}")

    assert len(load_workspace(root).figures) == len(KINDS)


def test_insert_puts_the_figure_before_the_references(root: Path) -> None:
    added = add_figure(load_workspace(root), "structure", "catalyst", insert=True)

    document = (root / "paper.tex").read_text(encoding="utf-8")
    assert added.inserted
    assert r"\label{fig:catalyst}" in document
    assert document.index(r"\labfigure{figures/catalyst.pdf}") < document.index(r"\bibliography")


@pytest.mark.parametrize("journal", ["article", "report", "elsevier", "rsc-draft"])
def test_insert_goes_before_the_bibliography_style_too(tmp_path: Path, journal: str) -> None:
    workspace = create_workspace(tmp_path / "paper", journal=journal)

    add_figure(load_workspace(workspace), "structure", "catalyst", insert=True)

    document = (workspace / "paper.tex").read_text(encoding="utf-8")
    figure = document.index(r"\labfigure{figures/catalyst.pdf}")
    assert figure < document.index(r"\bibliographystyle")
    assert r"\begin{figure}[htbp]" in document


def test_without_insert_the_document_is_not_touched(root: Path) -> None:
    before = (root / "paper.tex").read_text(encoding="utf-8")

    added = add_figure(load_workspace(root), "structure", "catalyst")

    assert not added.inserted
    assert (root / "paper.tex").read_text(encoding="utf-8") == before
    assert r"\labfigure{figures/catalyst.pdf}" in added.latex


def test_an_existing_script_is_never_overwritten_silently(root: Path) -> None:
    add_figure(load_workspace(root), "mechanism", "scheme")
    (root / "scripts" / "scheme.tex").write_text("% my work", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="--force"):
        add_figure(load_workspace(root), "mechanism", "scheme")
    assert (root / "scripts" / "scheme.tex").read_text(encoding="utf-8") == "% my work"


def test_force_replaces_the_script_without_duplicating_the_entry(root: Path) -> None:
    add_figure(load_workspace(root), "mechanism", "scheme")
    add_figure(load_workspace(root), "mechanism", "scheme", force=True)

    assert len(load_workspace(root).figures) == 1


@pytest.mark.parametrize("name", ["bad name", "-dash", "../escape", "a/b", ""])
def test_a_name_that_is_not_a_file_name_is_refused(root: Path, name: str) -> None:
    with pytest.raises(LabHarnessError, match="cannot be a figure name"):
        add_figure(load_workspace(root), "plot", name)


def test_an_unknown_kind_lists_the_known_ones(root: Path) -> None:
    with pytest.raises(LabHarnessError, match="structure"):
        add_figure(load_workspace(root), "photo", "cat")


def test_an_input_outside_the_workspace_is_refused(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere.csv"
    outside.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="outside the workspace"):
        add_figure(load_workspace(root), "plot", "stray", [outside])


def test_the_command_line_adds_and_prints_the_latex(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["add", "plot", "kinetics", "--input", "data/kinetics.csv"])

    assert result.exit_code == 0, result.stdout
    assert "Added figures/kinetics.pdf" in result.stdout
    assert r"\labfigure{figures/kinetics.pdf}" in result.stdout
    assert (root / "scripts" / "kinetics.py").is_file()


def test_the_command_line_reports_a_clash_as_an_error(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(root)
    runner.invoke(app, ["add", "flow", "pipeline"])

    result = runner.invoke(app, ["add", "flow", "pipeline"])

    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_a_table_is_added_like_a_figure(root: Path) -> None:
    (root / "data" / "screening.csv").write_text("entry;ee (%)\n1;92\n2;88\n", encoding="utf-8")

    added = add_figure(
        load_workspace(root), "table", "screening", [Path("data/screening.csv")], insert=True
    )

    script = (root / added.script).read_text(encoding="utf-8")
    assert added.output == Path("tables/screening.tex")
    assert 'read_table("data/screening.csv")' in script
    assert 'write_table(table, "tables/screening.tex")' in script
    workspace = load_workspace(root)
    assert [(item.name, item.kind) for item in workspace.figures] == [("screening", "table")]
    document = (root / "paper.tex").read_text(encoding="utf-8")
    assert r"\labtable{tables/screening.tex}" in document
    assert document.index(r"\caption{TODO") < document.index(r"\labtable")  # caption above


def test_an_added_table_builds_and_reaches_the_document(root: Path) -> None:
    from labharness.watch.runner import build_figure

    (root / "data" / "screening.csv").write_text("entry;ee (%)\n1;92\n", encoding="utf-8")
    add_figure(load_workspace(root), "table", "screening", [Path("data/screening.csv")])
    workspace = load_workspace(root)

    result = build_figure(workspace, workspace.figures[0])

    assert result.ok, result.error
    assert "92" in (root / "tables" / "screening.tex").read_text(encoding="utf-8")
