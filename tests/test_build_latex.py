"""The full LaTeX build LabHarness runs itself, without latexmk and without Perl."""

import shutil
from pathlib import Path

import pytest

from labharness.core import LabHarnessError, load_workspace
from labharness.core import latex as latex_module
from labharness.core.latex import run_full_build
from labharness.watch.latex import compile_document

needs_latex = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("bibtex") is None,
    reason="needs a LaTeX distribution",
)

BIBLIOGRAPHY = """@article{first,
  author = {Doe, Jane}, title = {A first study}, journal = {J. Test.}, year = {2024}
}
@article{second,
  author = {Roe, Richard}, title = {A second study}, journal = {J. Test.}, year = {2025}
}
"""


def paper(folder: Path, body: str) -> Path:
    document = folder / "paper.tex"
    document.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        f"{body}\n\\bibliographystyle{{plain}}\n\\bibliography{{refs}}\n\\end{{document}}\n",
        encoding="utf-8",
    )
    (folder / "refs.bib").write_text(BIBLIOGRAPHY, encoding="utf-8")
    return document


@pytest.mark.latex
@needs_latex
def test_a_first_build_runs_the_bibliography_and_resolves_every_citation(tmp_path: Path) -> None:
    document = paper(tmp_path, "See \\cite{first}. \\label{here}Section~\\ref{here}.")

    result = run_full_build(document)

    assert result.ok, result.errors
    assert result.bibliography
    assert "first" in (tmp_path / "paper.bbl").read_text(encoding="utf-8")
    assert "undefined" not in (tmp_path / "paper.log").read_text(encoding="utf-8").lower()


@pytest.mark.latex
@needs_latex
def test_the_bibliography_only_runs_again_when_the_citations_change(tmp_path: Path) -> None:
    document = paper(tmp_path, "See \\cite{first}.")
    run_full_build(document)

    unchanged = run_full_build(document)
    assert unchanged.ok and not unchanged.bibliography
    assert unchanged.passes == 1

    paper(tmp_path, "See \\cite{first} and \\cite{second}.")
    cited = run_full_build(document)
    assert cited.ok and cited.bibliography
    assert "second" in (tmp_path / "paper.bbl").read_text(encoding="utf-8")


@pytest.mark.latex
@needs_latex
def test_editing_the_bibliography_file_runs_it_again(tmp_path: Path) -> None:
    document = paper(tmp_path, "See \\cite{first}.")
    run_full_build(document)

    bib = tmp_path / "refs.bib"
    bib.write_text(bib.read_text(encoding="utf-8").replace("A first", "A renamed"), "utf-8")
    result = run_full_build(document)

    assert result.bibliography
    assert "renamed" in (tmp_path / "paper.bbl").read_text(encoding="utf-8")


@pytest.mark.latex
@needs_latex
def test_a_document_without_a_bibliography_never_calls_bibtex(tmp_path: Path) -> None:
    document = tmp_path / "note.tex"
    document.write_text("\\documentclass{article}\\begin{document}Hi\\end{document}", "utf-8")

    result = run_full_build(document)

    assert result.ok and not result.bibliography
    assert result.passes == 1


@pytest.mark.latex
@needs_latex
def test_a_latex_error_fails_the_build_and_says_why(tmp_path: Path) -> None:
    document = tmp_path / "broken.tex"
    document.write_text("\\documentclass{article}\\begin{document}\\nope\\end{document}", "utf-8")

    result = run_full_build(document)

    assert not result.ok
    assert any("Undefined control sequence" in line for line in result.errors)


@pytest.mark.latex
@needs_latex
def test_a_missing_bibliography_entry_is_reported(tmp_path: Path) -> None:
    document = paper(tmp_path, "See \\cite{first}.")
    (tmp_path / "refs.bib").unlink()

    result = run_full_build(document)

    assert not result.ok
    assert any(line.startswith("bibtex:") for line in result.errors)


def test_the_build_never_needs_latexmk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def run(command: list[str], **kwargs: object) -> Done:
        calls.append(command)
        (tmp_path / "paper.pdf").write_bytes(b"%PDF")
        return Done()

    monkeypatch.setattr(
        "labharness.core.latex.shutil.which", lambda name: None if name == "latexmk" else name
    )
    monkeypatch.setattr("labharness.core.latex.subprocess.run", run)
    document = tmp_path / "paper.tex"
    document.write_text("x", encoding="utf-8")

    result = run_full_build(document)

    assert result.ok
    assert all(command[0] != "latexmk" for command in calls)


def test_the_manifest_can_ask_for_latexmk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "labharness.toml").write_text('builder = "latexmk"\n', encoding="utf-8")
    used: list[str] = []
    monkeypatch.setattr(
        "labharness.watch.latex.run_latexmk", lambda d, engine: used.append("latexmk")
    )
    monkeypatch.setattr(
        "labharness.watch.latex.run_full_build", lambda d, engine: used.append("own")
    )

    workspace = load_workspace(tmp_path)
    compile_document(workspace.document, workspace.builder)
    compile_document(workspace.document)

    assert used == ["latexmk", "own"]


def test_an_unknown_builder_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text('builder = "make"\n', encoding="utf-8")

    with pytest.raises(LabHarnessError, match="labharness, latexmk"):
        load_workspace(tmp_path)


def test_biblatex_documents_use_biber(tmp_path: Path) -> None:
    document = tmp_path / "paper.tex"
    document.with_suffix(".bcf").write_text("<bcf/>", encoding="utf-8")

    assert latex_module._bibliography_tool(document) == "biber"


ENGINES = ["pdflatex", "xelatex", "lualatex"]


@pytest.mark.latex
@pytest.mark.parametrize("engine", ENGINES)
def test_every_engine_builds_the_document_and_its_bibliography(tmp_path: Path, engine: str) -> None:
    if shutil.which(engine) is None or shutil.which("bibtex") is None:
        pytest.skip(f"needs {engine}")
    document = paper(tmp_path, r"See \cite{first}.")

    result = run_full_build(document, engine=engine)

    assert result.ok, result.errors
    assert result.bibliography
    assert (tmp_path / "paper.pdf").read_bytes().startswith(b"%PDF")


@pytest.mark.latex
@pytest.mark.parametrize("engine", ["xelatex", "lualatex"])
def test_diagrams_compile_with_the_workspace_engine(tmp_path: Path, engine: str) -> None:
    if shutil.which(engine) is None:
        pytest.skip(f"needs {engine}")
    from labharness.modules.diagrams import render_diagram

    source = tmp_path / "scheme.tex"
    source.write_text(r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}", "utf-8")

    output = render_diagram(source, tmp_path / "scheme.pdf", engine=engine)

    assert output.read_bytes().startswith(b"%PDF")


def test_the_manifest_engine_reaches_every_compilation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "labharness.toml").write_text('engine = "lualatex"\n', encoding="utf-8")
    seen: list[str] = []
    monkeypatch.setattr(
        "labharness.watch.latex.run_full_build",
        lambda document, engine: seen.append(engine),
    )

    workspace = load_workspace(tmp_path)
    compile_document(workspace.document, workspace.builder, workspace.engine)

    assert workspace.engine == "lualatex"
    assert seen == ["lualatex"]


def test_an_unknown_engine_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text('engine = "context"\n', encoding="utf-8")

    with pytest.raises(LabHarnessError, match="pdflatex, xelatex, lualatex"):
        load_workspace(tmp_path)
