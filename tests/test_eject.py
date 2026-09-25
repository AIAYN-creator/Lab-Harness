"""labharness eject: a copy whose figures regenerate with LabHarness out of the picture."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from labharness.core import LabHarnessError, load_workspace
from labharness.eject import VENDOR, eject

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo"

# Runs a script in the ejected folder with the real package made unimportable: any import of
# labharness left behind fails loudly instead of quietly using the installed copy.
WITHOUT_LABHARNESS = """
import runpy, sys
sys.modules["labharness"] = None
sys.path.insert(0, ".")
runpy.run_path(sys.argv[1], run_name="__main__")
"""


def needs(*modules: str) -> pytest.MarkDecorator:
    missing = [module for module in modules if importlib.util.find_spec(module) is None]
    return pytest.mark.skipif(bool(missing), reason=f"needs {', '.join(missing)}")


@pytest.fixture
def ejected(tmp_path: Path) -> Path:
    workspace = tmp_path / "demo"
    shutil.copytree(DEMO, workspace)
    eject(load_workspace(workspace), tmp_path / "standalone")
    return tmp_path / "standalone"


def test_only_the_modules_the_scripts_use_are_copied(ejected: Path) -> None:
    modules = sorted(
        path.name for path in (ejected / VENDOR / "modules").iterdir() if path.is_dir()
    )

    assert modules == ["chem", "plots"]  # the demo draws no table and uses no diagrams module
    assert (ejected / VENDOR / "core").is_dir() and (ejected / VENDOR / "style").is_dir()


def test_nothing_imports_labharness_any_more(ejected: Path) -> None:
    offenders = [
        path.relative_to(ejected).as_posix()
        for path in ejected.rglob("*.py")
        if "import labharness" in (text := path.read_text(encoding="utf-8"))
        or "from labharness" in text
    ]

    assert offenders == []


def test_labharness_files_are_left_behind_and_the_original_is_untouched(
    ejected: Path, tmp_path: Path
) -> None:
    for name in ("labharness.toml", "AGENTS.md", "AGENTS.chemistry.md", "CLAUDE.md"):
        assert not (ejected / name).exists(), name
    # The compile shortcuts are rewritten: they call build.py, not labharness watch.
    assert "labharness" not in (ejected / "compile.sh").read_text(encoding="utf-8")
    assert (tmp_path / "demo" / "labharness.toml").is_file()
    assert (tmp_path / "demo" / "scripts" / "decay.py").read_text(encoding="utf-8") == (
        DEMO / "scripts" / "decay.py"
    ).read_text(encoding="utf-8")


def test_the_journal_is_frozen(ejected: Path) -> None:
    templates = (ejected / VENDOR / "core" / "templates.py").read_text(encoding="utf-8")
    styles = list((ejected / VENDOR / "templates" / "workspace" / "journals").iterdir())

    assert 'DEFAULT_JOURNAL = "acs"' in templates
    assert [style.name for style in styles] == ["acs"]


@pytest.mark.latex
@needs("rdkit", "scipy", "matplotlib")
@pytest.mark.skipif(shutil.which("kpsewhich") is None, reason="needs a LaTeX distribution")
def test_every_script_runs_with_labharness_unimportable(ejected: Path) -> None:
    for script in ("scripts/atenolol.py", "scripts/decay.py", "scripts/kapp.py"):
        result = subprocess.run(
            [sys.executable, "-c", WITHOUT_LABHARNESS, script],
            cwd=ejected,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr[-2000:]

    for figure in ("atenolol.pdf", "decay.pdf", "kapp.pdf"):
        assert (ejected / "figures" / figure).read_bytes().startswith(b"%PDF"), figure
    # The fitted values the text cites are written too.
    assert "FitDecayB" in (ejected / "figures" / "decay.fit.tex").read_text(encoding="utf-8")


@pytest.mark.latex
@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="needs a LaTeX distribution")
def test_a_diagram_compiles_with_plain_pdflatex(ejected: Path) -> None:
    mechanism = ejected / "scripts" / "mechanism.tex"
    assert "\\documentclass" in mechanism.read_text(encoding="utf-8")

    for _ in range(2):  # chemfig arrows need the second pass
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", mechanism.name],
            cwd=mechanism.parent,
            capture_output=True,
            text=True,
            errors="replace",
        )
    assert result.returncode == 0, result.stdout[-2000:]
    assert (mechanism.with_suffix(".pdf")).is_file()


def test_ejecting_inside_the_workspace_is_refused(tmp_path: Path) -> None:
    workspace = tmp_path / "demo"
    shutil.copytree(DEMO, workspace)

    with pytest.raises(LabHarnessError, match="outside the workspace"):
        eject(load_workspace(workspace), workspace / "copy")


def test_a_folder_with_something_in_it_needs_force(tmp_path: Path) -> None:
    workspace = tmp_path / "demo"
    shutil.copytree(DEMO, workspace)
    (tmp_path / "busy").mkdir()
    (tmp_path / "busy" / "notes.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="--force"):
        eject(load_workspace(workspace), tmp_path / "busy")


def test_the_ejected_folder_says_how_to_rebuild_it(ejected: Path) -> None:
    for name in ("build.py", "requirements.txt", "EJECTED.md", "compile.sh", "compile.ps1"):
        assert (ejected / name).is_file(), name
    assert "python build.py" in (ejected / "compile.sh").read_text(encoding="utf-8")
    assert "pip install -r requirements.txt" in (ejected / "EJECTED.md").read_text("utf-8")


@needs("rdkit", "scipy", "matplotlib")
def test_requirements_pin_the_versions_that_drew_the_figures(ejected: Path) -> None:
    from importlib import metadata

    pins = (ejected / "requirements.txt").read_text(encoding="utf-8").splitlines()

    for name in ("rdkit", "svglib", "reportlab", "numpy", "scipy", "matplotlib"):
        assert f"{name}=={metadata.version(name)}" in pins, name


def test_build_py_lists_every_figure_in_manifest_order(ejected: Path) -> None:
    text = (ejected / "build.py").read_text(encoding="utf-8")

    positions = [text.index(f"'figures/{name}.pdf'") for name in ("atenolol", "decay", "kapp")]
    assert positions == sorted(positions)
    assert "'scripts/mechanism.tex'" in text
    compile(text, "build.py", "exec")  # it is valid Python


@pytest.mark.latex
@needs("rdkit", "scipy", "matplotlib")
@pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("bibtex") is None,
    reason="needs a LaTeX distribution",
)
def test_build_py_regenerates_the_whole_paper_without_labharness(ejected: Path) -> None:
    for stale in [*(ejected / "figures").glob("*.pdf"), ejected / "paper.pdf"]:
        stale.unlink(missing_ok=True)

    result = subprocess.run(
        [sys.executable, "-c", WITHOUT_LABHARNESS, "build.py"],
        cwd=ejected,
        capture_output=True,
        text=True,
        errors="replace",
    )

    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    for figure in ("atenolol", "decay", "kapp", "mechanism"):
        assert (ejected / "figures" / f"{figure}.pdf").read_bytes().startswith(b"%PDF"), figure
    assert (ejected / "paper.pdf").read_bytes().startswith(b"%PDF")
    # The citation of the demo was resolved: BibTeX ran.
    assert "moragomez2020" in (ejected / "paper.bbl").read_text(encoding="utf-8")


TABLE_SCRIPT = """\
# tables/rates.tex -- apparent rate constants
from labharness.modules.tables import read_table, write_table

write_table(read_table("data/kapp.csv"), "tables/rates.tex")
"""

TABLE_ENTRY = """
[[table]]
output = "tables/rates.tex"
script = "scripts/rates.py"
inputs = ["data/kapp.csv"]
"""


@pytest.mark.latex
@needs("rdkit", "scipy", "matplotlib")
@pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("bibtex") is None,
    reason="needs a LaTeX distribution",
)
def test_a_table_regenerates_in_the_ejected_copy_and_reaches_the_pdf(tmp_path: Path) -> None:
    workspace = tmp_path / "demo"
    shutil.copytree(DEMO, workspace)
    (workspace / "scripts" / "rates.py").write_text(TABLE_SCRIPT, encoding="utf-8")
    with (workspace / "labharness.toml").open("a", encoding="utf-8") as manifest:
        manifest.write(TABLE_ENTRY)
    paper = workspace / "paper.tex"
    paper.write_text(
        paper.read_text(encoding="utf-8").replace(
            "\\end{document}",
            "\\begin{table}\\labtable{tables/rates.tex}\\end{table}\n\\end{document}",
        ),
        encoding="utf-8",
    )
    target = tmp_path / "standalone"
    eject(load_workspace(workspace), target)

    result = subprocess.run(
        [sys.executable, "-c", WITHOUT_LABHARNESS, "build.py"],
        cwd=target,
        capture_output=True,
        text=True,
        errors="replace",
    )

    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert (target / VENDOR / "modules" / "tables").is_dir()
    assert "0.0150" in (target / "tables" / "rates.tex").read_text(encoding="utf-8")
    assert (target / "paper.pdf").read_bytes().startswith(b"%PDF")
    # The generated table reached the page, not the placeholder shown when it is missing.
    pages = PdfReader(target / "paper.pdf").pages
    assert "0.0150" in "".join(page.extract_text() for page in pages)
