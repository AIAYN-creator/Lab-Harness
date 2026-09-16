"""Checking that this machine has everything LabHarness needs.

Every problem found on the author's laptop during development is a check here: Perl missing
for latexmk, no Sumatra installed, Adobe Acrobat locking the PDF, a stale MiKTeX file
database.
"""

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from labharness.style import load_style
from labharness.style.fonts import find_font_file
from labharness.watch.viewer import find_viewer


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True
    hint: str = ""


def run_checks() -> list[Check]:
    return [
        _python(),
        *_extras(),
        _latex(),
        _latexmk(),
        _fonts(),
        _java(),
        _viewer(),
    ]


def everything_required_passes(checks: list[Check]) -> bool:
    return all(check.ok for check in checks if check.required)


def _python() -> Check:
    version = platform.python_version()
    ok = sys.version_info >= (3, 11)
    return Check(
        "Python",
        ok,
        version,
        hint="" if ok else "LabHarness needs Python 3.11 or newer",
    )


def _extras() -> list[Check]:
    extras = {
        "chem": ("rdkit", "chemical structures"),
        "plots": ("matplotlib", "plots and regressions"),
        "iupac": ("py2opsin", "IUPAC name resolution"),
    }
    checks = []
    for extra, (module, purpose) in extras.items():
        installed = importlib.util.find_spec(module) is not None
        checks.append(
            Check(
                f"extra '{extra}'",
                installed,
                "installed" if installed else f"not installed ({purpose} unavailable)",
                required=False,
                hint="" if installed else f"uv sync --extra {extra}",
            )
        )
    return checks


def _latex() -> Check:
    pdflatex = shutil.which("pdflatex")
    return Check(
        "pdflatex",
        pdflatex is not None,
        pdflatex or "not found",
        hint="" if pdflatex else "Install MiKTeX or TeX Live",
    )


def _latexmk() -> Check:
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        return Check("latexmk", False, "not found", hint="Install MiKTeX or TeX Live")

    result = subprocess.run([latexmk, "-v"], capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode != 0 or "perl" in output.lower():
        return Check(
            "latexmk",
            False,
            "found, but it does not run",
            hint=(
                "latexmk is a Perl script. On Windows with MiKTeX install Perl: "
                "winget install StrawberryPerl.StrawberryPerl"
            ),
        )
    return Check("latexmk", True, output.strip().splitlines()[0] if output.strip() else latexmk)


def _fonts() -> Check:
    font_file = load_style().typography.font_file
    try:
        return Check("document font", True, str(find_font_file(font_file)))
    except Exception as error:  # noqa: BLE001 - the message is the whole point
        return Check(
            "document font",
            False,
            str(error),
            hint="Install the Latin Modern fonts ('lm' in TeX Live, 'lmodern' on Debian)",
        )


def _java() -> Check:
    needed = importlib.util.find_spec("py2opsin") is not None
    java = shutil.which("java")
    return Check(
        "Java",
        java is not None or not needed,
        java or "not found",
        required=needed,
        hint="" if java or not needed else "Needed by the 'iupac' extra. Install Eclipse Temurin",
    )


def _viewer() -> Check:
    viewer = find_viewer()
    return Check(
        "PDF viewer",
        viewer is not None,
        str(viewer) if viewer else "not found",
        required=False,
        hint=(
            ""
            if viewer
            else "Install SumatraPDF (Windows) or Skim (macOS). Adobe Acrobat locks the PDF "
            "and stops the rebuild"
        ),
    )
