"""Modules are found through their entry points, LabHarness's own and a domain's alike."""

import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest

from labharness.core import create_workspace, load_workspace
from labharness.core.domains import GROUP, installed_modules
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
    monkeypatch.syspath_prepend(str(tmp_path / "site"))
    real = metadata.entry_points

    def with_toy(**selection: Any) -> list[metadata.EntryPoint]:
        found = list(real(**selection))
        if selection.get("group") == GROUP:
            found.append(metadata.EntryPoint("toy", "labharness_toy", GROUP))
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
