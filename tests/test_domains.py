"""Modules are found through their entry points, LabHarness's own and a domain's alike."""

import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from labharness.cli import app
from labharness.cli.app import add_domain_commands
from labharness.core import create_workspace, load_workspace
from labharness.core.add import add_figure
from labharness.core.domains import FIGURES, figure_kinds, installed_modules
from labharness.core.errors import LabHarnessError
from labharness.core.newdomain import create_domain
from labharness.eject import VENDOR, eject

# A domain package as someone else would start it: with labharness new-domain toy.
SCRIPT = 'from labharness_toy import render\n\nrender("figures/note.txt", "made by a domain")\n'
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
    """labharness_toy, importable and declared as its pyproject declares it, as if installed."""
    toy = create_domain("toy", tmp_path / "labharness-toy")
    declared = tomllib.loads((toy / "pyproject.toml").read_text(encoding="utf-8"))
    monkeypatch.syspath_prepend(str(toy))
    real = metadata.entry_points

    def with_toy(**selection: Any) -> list[metadata.EntryPoint]:
        found = list(real(**selection))
        group = selection.get("group", "")
        for name, value in declared["project"]["entry-points"].get(group, {}).items():
            found.append(metadata.EntryPoint(name, value, group))
        if group == FIGURES:
            found.append(metadata.EntryPoint("plot", "labharness_toy", FIGURES))  # a clash
        return found

    monkeypatch.setattr(metadata, "entry_points", with_toy)


@pytest.mark.usefixtures("toy_domain")
def test_a_domain_package_is_found_by_its_entry_point() -> None:
    toy = next(module for module in installed_modules() if module.name == "toy")

    assert toy.package == "labharness_toy"
    assert not toy.built_in
    assert toy.provides("labharness_toy") and not toy.provides("labharness_toy_more")


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

    added = add_figure(load_workspace(workspace), "toy", "greeting")

    script = (workspace / added.script).read_text(encoding="utf-8")
    assert script.startswith("# figures/greeting.pdf -- an example for toy")


@pytest.mark.usefixtures("toy_domain")
def test_two_packages_with_the_same_kind_are_told_apart_not_chosen() -> None:
    kinds = figure_kinds()

    assert "plot" not in kinds
    assert kinds["labharness.modules.plots:plot"].package == "labharness.modules.plots"
    assert kinds["labharness_toy:plot"].package == "labharness_toy"


@pytest.mark.usefixtures("toy_domain")
def test_a_workspace_stacks_the_rules_of_several_fields(tmp_path: Path) -> None:
    root = create_workspace(tmp_path / "paper", fields=["chemistry", "toy", "chemistry"])

    assert (root / "AGENTS.chemistry.md").is_file()
    assert (root / "AGENTS.toy.md").read_text(encoding="utf-8").startswith("# Rules for toy\n")
    assert (root / "CLAUDE.md").read_text(encoding="utf-8").split() == [
        "@AGENTS.md",
        "@AGENTS.chemistry.md",
        "@AGENTS.toy.md",
    ]


def test_an_unknown_field_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="unknown field 'alchemy'. Installed: chemistry"):
        create_workspace(tmp_path / "paper", fields=["alchemy"])

    assert not (tmp_path / "paper").exists()


@pytest.mark.usefixtures("toy_domain")
def test_a_domain_works_from_init_to_eject_without_touching_the_core(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    root = tmp_path / "paper"

    assert runner.invoke(app, ["init", str(root), "--field", "toy"]).exit_code == 0
    assert (root / "AGENTS.toy.md").is_file()
    monkeypatch.chdir(root)
    with_domains = typer.Typer()
    add_domain_commands(with_domains)  # a fresh one: the real command line is not changed
    assert "hello from toy" in runner.invoke(with_domains, ["toy-hello"]).stdout
    added = runner.invoke(app, ["add", "toy", "greeting"])
    assert added.exit_code == 0, added.stdout
    built = runner.invoke(app, ["build", "--no-latex"])
    assert built.exit_code == 0, built.stdout
    assert (root / "figures" / "greeting.pdf").read_text(encoding="utf-8") == "hello from toy"
    ejected = runner.invoke(app, ["eject", str(tmp_path / "standalone")])
    assert ejected.exit_code == 0, ejected.stdout
    assert "toy" in ejected.stdout
