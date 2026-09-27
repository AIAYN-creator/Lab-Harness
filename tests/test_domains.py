"""Modules are found through their entry points, LabHarness's own and a domain's alike."""

import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

from labharness.core import create_workspace, load_workspace
from labharness.core.add import add_figure
from labharness.core.domains import FIGURES, GROUP, figure_kinds, installed_modules
from labharness.eject import VENDOR, eject

# A domain package as someone else would write it: its own name, importing LabHarness's core.
TOY = '''"""A toy domain: writes a file, and uses LabHarness's core to do it."""

from pathlib import Path

from labharness.core.atomic import atomic_output


def note(output: str, text: str) -> None:
    with atomic_output(Path(output)) as temporary:
        temporary.write_text(text, encoding="utf-8")
'''
SCRIPT = 'from labharness_toy import note\n\nnote("figures/note.txt", "made by a domain")\n'
WITHOUT_LABHARNESS = (
    "import runpy, sys; sys.modules['labharness'] = None; sys.path.insert(0, '.'); "
    "runpy.run_path('scripts/note.py', run_name='__main__')"
)


def test_labharness_registers_its_own_modules_like_any_domain() -> None:
    modules = {module.name: module for module in installed_modules()}

    assert set(modules) >= {"chem", "diagrams", "plots", "tables"}
    assert modules["chem"].package == "labharness.modules.chem"
    assert modules["chem"].built_in and modules["chem"].distribution == "labharness"


@pytest.fixture
def toy_domain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """labharness_toy, importable and declared under the entry point group, as if installed."""
    package = tmp_path / "site" / "labharness_toy"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(TOY, encoding="utf-8")
    (package / "templates").mkdir()
    (package / "templates" / "note.py.template").write_text(
        '# $output -- a note\nfrom labharness_toy import note\n\nnote("$output", "hello")\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path / "site"))
    real = metadata.entry_points

    def with_toy(**selection: Any) -> list[metadata.EntryPoint]:
        found = list(real(**selection))
        if selection.get("group") == GROUP:
            found.append(metadata.EntryPoint("toy", "labharness_toy", GROUP))
        if selection.get("group") == FIGURES:
            found.append(metadata.EntryPoint("note", "labharness_toy", FIGURES))
            found.append(metadata.EntryPoint("plot", "labharness_toy", FIGURES))  # a clash
        return found

    monkeypatch.setattr(metadata, "entry_points", with_toy)


@pytest.mark.usefixtures("toy_domain")
def test_a_domain_package_is_found_by_its_entry_point() -> None:
    toy = next(module for module in installed_modules() if module.name == "toy")

    assert toy.package == "labharness_toy"
    assert not toy.built_in
    assert toy.provides("labharness_toy") and not toy.provides("labharness_toys")


@pytest.mark.usefixtures("toy_domain")
def test_an_ejected_workspace_carries_the_domain_it_uses(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "paper", journal="article")
    (workspace / "scripts" / "note.py").write_text(SCRIPT, encoding="utf-8")
    with (workspace / "labharness.toml").open("a", encoding="utf-8") as manifest:
        manifest.write('\n[[figure]]\noutput = "figures/note.txt"\nscript = "scripts/note.py"\n')
    target = tmp_path / "standalone"

    ejected = eject(load_workspace(workspace), target)

    assert ejected.modules == ("toy",)
    copied = (target / "labharness_toy" / "__init__.py").read_text(encoding="utf-8")
    assert f"from {VENDOR}.core.atomic import atomic_output" in copied
    subprocess.run([sys.executable, "-c", WITHOUT_LABHARNESS], cwd=target, check=True)
    assert (target / "figures" / "note.txt").read_text(encoding="utf-8") == "made by a domain"


@pytest.mark.usefixtures("toy_domain")
def test_add_offers_the_kinds_a_domain_registers(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path / "paper", journal="article")

    added = add_figure(load_workspace(workspace), "note", "greeting")

    script = (workspace / added.script).read_text(encoding="utf-8")
    assert script.startswith("# figures/greeting.pdf -- a note")


@pytest.mark.usefixtures("toy_domain")
def test_two_packages_with_the_same_kind_are_told_apart_not_chosen() -> None:
    kinds = figure_kinds()

    assert "plot" not in kinds
    assert kinds["labharness.modules.plots:plot"].package == "labharness.modules.plots"
    assert kinds["labharness_toy:plot"].package == "labharness_toy"
