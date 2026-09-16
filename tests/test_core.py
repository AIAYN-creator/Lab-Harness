import os
import subprocess
import sys
from pathlib import Path

import pytest

from labharness.core import LabHarnessError, MissingExtraError, require

SRC = Path(__file__).resolve().parents[1] / "src"

SUBPACKAGES = [
    "labharness",
    "labharness.core",
    "labharness.style",
    "labharness.watch",
    "labharness.cli",
    "labharness.modules",
    "labharness.modules.chem",
    "labharness.modules.diagrams",
    "labharness.modules.plots",
]

HEAVY_DEPENDENCIES = ["rdkit", "scipy", "matplotlib", "numpy", "reportlab", "svglib", "py2opsin"]


def test_core_imports_without_loading_any_extra() -> None:
    # A fresh interpreter, so nothing imported by pytest or other tests can hide a leak.
    code = (
        "import importlib, sys\n"
        f"for name in {SUBPACKAGES!r}:\n"
        "    importlib.import_module(name)\n"
        f"leaked = sorted(d for d in {HEAVY_DEPENDENCIES!r} if d in sys.modules)\n"
        "print(','.join(leaked))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
    )
    assert result.stdout.strip() == ""


def test_require_returns_installed_module() -> None:
    assert require("json", extra="none").__name__ == "json"


def test_require_explains_which_extra_is_missing() -> None:
    with pytest.raises(MissingExtraError) as info:
        require("labharness_package_that_does_not_exist", extra="chem")

    error = info.value
    assert isinstance(error, LabHarnessError)
    assert isinstance(error, ImportError)
    assert error.extra == "chem"
    assert "labharness[chem]" in str(error)
