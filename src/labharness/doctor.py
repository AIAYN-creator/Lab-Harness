"""Checking that this machine has everything LabHarness needs.

Every problem found on the author's laptop during development is a check here: no Sumatra
installed, Adobe Acrobat locking the PDF, a stale MiKTeX file database. latexmk and Perl used
to be on that list; LabHarness now compiles without them, so they are only reported.
"""

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from labharness.hints import command_for, detect_system, extra_command, tex_package_command
from labharness.preview import find_rasteriser
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
        _modules(),
        _latex(),
        _bibtex(),
        *_engine(),
        _latexmk(),
        _fonts(),
        _java(),
        _viewer(),
        _rasteriser(),
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
        "excel": ("openpyxl", "reading .xlsx workbooks"),
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
                hint="" if installed else extra_command(extra),
            )
        )
    return checks


def _modules() -> Check:
    """The modules installed: LabHarness's own, and those of any domain package."""
    from labharness.core.domains import installed_modules

    names = [
        module.name if module.built_in else f"{module.name} ({module.distribution})"
        for module in installed_modules()
    ]
    return Check("modules", True, ", ".join(names), required=False)


def _latex() -> Check:
    pdflatex = shutil.which("pdflatex")
    return Check(
        "pdflatex",
        pdflatex is not None,
        pdflatex or "not found",
        hint="" if pdflatex else command_for("latex"),
    )


def _engine() -> list[Check]:
    """The engine of the workspace doctor runs in, when it is not pdflatex."""
    from labharness.core.errors import LabHarnessError
    from labharness.core.manifest import DEFAULT_ENGINE, load_workspace

    try:
        engine = load_workspace().engine
    except LabHarnessError:
        return []
    if engine == DEFAULT_ENGINE:
        return []
    found = shutil.which(engine)
    checks = [
        Check(
            f"{engine} (this workspace)",
            found is not None,
            found or "not found",
            hint="" if found else f"The manifest asks for {engine}: install it, or remove 'engine'",
        )
    ]
    # standalone, which every diagram uses, loads luatex85 under LuaLaTeX. Small distributions
    # such as BasicTeX leave it out; MiKTeX installs it the first time it is needed.
    if engine == "lualatex" and found and not _tex_file("luatex85.sty"):
        checks.append(
            Check(
                "luatex85 (diagrams with lualatex)",
                False,
                "not installed",
                required=detect_system().name != "windows",
                hint=tex_package_command("luatex85"),
            )
        )
    return checks


def _tex_file(name: str) -> bool:
    """Whether the LaTeX distribution has ``name``, as kpsewhich finds it."""
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        return False
    result = subprocess.run([kpsewhich, name], capture_output=True, text=True, check=False)
    return bool(result.stdout.strip())


def _bibtex() -> Check:
    bibtex = shutil.which("bibtex")
    return Check(
        "bibtex",
        bibtex is not None,
        bibtex or "not found",
        hint=""
        if bibtex
        else "It comes with every LaTeX distribution: reinstall MiKTeX or TeX Live",
    )


def _latexmk() -> Check:
    """Optional: only used by workspaces with builder = "latexmk" in their manifest."""
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        return Check("latexmk", True, "not installed (optional)", required=False)

    result = subprocess.run([latexmk, "-v"], capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode != 0 or "perl" in output.lower():
        return Check(
            "latexmk",
            False,
            "found, but it does not run (optional: LabHarness compiles without it)",
            required=False,
            hint=f'Only needed for builder = "latexmk". It is a Perl script: {command_for("perl")}',
        )
    return Check("latexmk", True, output.strip().splitlines()[0] if output.strip() else latexmk)


def _fonts() -> Check:
    typography = load_style().typography
    try:
        found = find_font_file(typography.font_file, typography.tex_package)
        return Check("document font", True, f"{typography.family}: {found}")
    except Exception as error:  # noqa: BLE001 - the message is the whole point
        return Check(
            "document font",
            False,
            str(error),
            hint=tex_package_command(typography.tex_package),
        )


def _java() -> Check:
    needed = importlib.util.find_spec("py2opsin") is not None
    java = shutil.which("java")
    return Check(
        "Java",
        java is not None or not needed,
        java or "not found",
        required=needed,
        hint="" if java or not needed else f"Needed by the 'iupac' extra: {command_for('java')}",
    )


def _rasteriser() -> Check:
    tool = find_rasteriser()
    return Check(
        "figure previews",
        tool is not None,
        f"{tool[0]} ({tool[1]})" if tool else "not found",
        required=False,
        hint="" if tool else f"'labharness preview' needs it: {command_for('rasteriser')}",
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
            else f"{command_for('viewer')}. Not Adobe Acrobat: it locks the PDF and stops "
            "the rebuild"
        ),
    )
