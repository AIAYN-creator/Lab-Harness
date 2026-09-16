import shutil
from collections.abc import Sequence
from pathlib import Path

import pytest

from labharness.core.latex import summarise_errors
from labharness.core.manifest import Figure, Workspace, load_workspace
from labharness.watch import session
from labharness.watch.runner import BuildResult, build_figure

SCRIPT = """
from pathlib import Path

value = Path("data/value.txt").read_text(encoding="utf-8").strip()
Path("figures").mkdir(exist_ok=True)
Path("figures/value.pdf").write_text(f"%PDF-1.4 {value}", encoding="utf-8")
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    (tmp_path / "labharness.toml").write_text(
        """
[[figure]]
output = "figures/value.pdf"
script = "scripts/value.py"
inputs = ["data/value.txt"]
""",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "data" / "value.txt").write_text("42\n", encoding="utf-8")
    (tmp_path / "scripts" / "value.py").write_text(SCRIPT, encoding="utf-8")
    return load_workspace(tmp_path)


def test_a_script_runs_with_the_workspace_as_its_working_directory(workspace: Workspace) -> None:
    result = build_figure(workspace, workspace.figures[0])

    assert result.ok, result.error
    assert (workspace.root / "figures" / "value.pdf").read_text(encoding="utf-8").endswith("42")
    assert result.seconds >= 0


def test_the_working_directory_is_restored_afterwards(workspace: Workspace) -> None:
    before = Path.cwd()

    build_figure(workspace, workspace.figures[0])

    assert Path.cwd() == before


def test_a_script_that_raises_does_not_stop_the_watcher(workspace: Workspace) -> None:
    (workspace.root / "scripts" / "value.py").write_text("raise ValueError('boom')", "utf-8")

    result = build_figure(workspace, workspace.figures[0])

    assert not result.ok
    assert "ValueError" in (result.error or "")


def test_a_script_that_writes_nothing_is_reported(workspace: Workspace) -> None:
    (workspace.root / "scripts" / "value.py").write_text("pass", encoding="utf-8")

    result = build_figure(workspace, workspace.figures[0])

    assert not result.ok
    assert "produced no" in (result.error or "")


def test_a_missing_script_is_reported(workspace: Workspace) -> None:
    (workspace.root / "scripts" / "value.py").unlink()

    result = build_figure(workspace, workspace.figures[0])

    assert not result.ok
    assert "does not exist" in (result.error or "")


@pytest.mark.latex
@pytest.mark.skipif(shutil.which("latexmk") is None, reason="needs a LaTeX distribution")
def test_a_tex_figure_is_built_through_the_diagrams_module(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        '[[figure]]\noutput = "figures/m.pdf"\nscript = "scripts/m.tex"\n', encoding="utf-8"
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "m.tex").write_text(
        r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}", encoding="utf-8"
    )
    workspace = load_workspace(tmp_path)

    result = build_figure(workspace, workspace.figures[0])

    assert result.ok, result.error
    assert (tmp_path / "figures" / "m.pdf").read_bytes().startswith(b"%PDF")


def test_a_broken_tex_figure_is_reported_without_stopping_the_watcher(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        '[[figure]]\noutput = "figures/m.pdf"\nscript = "scripts/m.tex"\n', encoding="utf-8"
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "m.tex").write_text(r"\begin{tikzpicture}", encoding="utf-8")
    workspace = load_workspace(tmp_path)

    result = build_figure(workspace, workspace.figures[0])

    assert not result.ok
    assert result.error


def test_a_save_rebuilds_only_the_affected_figures(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    rebuilt: list[list[str]] = []
    quick_calls: list[bool] = []

    def fake_build(
        ws: Workspace,
        figures: Sequence[Figure] | None = None,
        compile_latex: bool = True,
        quick: bool = False,
    ) -> BuildResult:
        chosen = ws.figures if figures is None else figures
        rebuilt.append([figure.name for figure in chosen])
        quick_calls.append(quick)
        return BuildResult()

    monkeypatch.setattr(session, "build", fake_build)

    batches = [
        {workspace.root / "data" / "value.txt"},
        {workspace.root / "data" / "unrelated.txt"},
        {workspace.root / "paper.tex"},
    ]
    cycles = list(session.changes_to_cycles(workspace, batches))

    # The unrelated file produced no cycle at all; the document change compiles with no figures.
    assert rebuilt == [["value"], []]
    assert [cycle.changed[0].name for cycle in cycles] == ["value.txt", "paper.tex"]
    # A data change needs one LaTeX pass; a change to the document itself needs latexmk.
    assert quick_calls == [True, False]


def test_latex_errors_are_summarised_for_a_person() -> None:
    summary = summarise_errors(
        "This is pdfTeX\n! LaTeX Error: File `nope.sty' not found.\nl.8 \\usepackage\nblah\n"
    )

    assert summary[0].startswith("! LaTeX Error")
    assert any(line.startswith("l.8") for line in summary)


def test_a_latex_failure_is_explained_from_the_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # latexmk prints a summary, not the LaTeX error: the message must come from the log.
    from labharness.core import latex

    document = tmp_path / "paper.tex"
    document.write_text("broken", encoding="utf-8")
    document.with_suffix(".log").write_text(
        "! Undefined control sequence.\nl.34 The fitted slope is \\FitSlope\n", encoding="utf-8"
    )

    class Result:
        returncode = 1
        stdout = "latexmk: Errors, so I did not complete making targets\n"
        stderr = ""

    monkeypatch.setattr("labharness.core.latex.shutil.which", lambda name: "latexmk")
    monkeypatch.setattr("labharness.core.latex.subprocess.run", lambda *args, **kwargs: Result())

    result = latex.run_latexmk(document)

    assert not result.ok
    assert result.errors[0].startswith("! Undefined control sequence")
