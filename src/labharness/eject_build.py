"""The files that let an ejected workspace rebuild itself: build.py, requirements, EJECTED.md.

``build.py`` is written into the ejected folder as plain Python with no dependency but the
standard library and what the scripts import: it runs every figure script in order, compiles
the diagrams and then the paper with pdflatex and BibTeX. It does what ``labharness build``
does, minus the watcher, and it is short enough to read.
"""

import pprint
import re
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

from labharness.core.manifest import Workspace

BUILD_PY = '''"""Regenerate every figure of this paper and compile it, without LabHarness.

Written by labharness eject ({version}, {date}). Run it from this folder:

    python build.py

It needs the Python packages in requirements.txt and a LaTeX distribution with pdflatex and
BibTeX. See EJECTED.md.
"""

import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCUMENT = "{document}"
# In the order of the manifest they came from: script, and the figure it writes.
FIGURES = {figures}
MAX_PASSES = 5


def run_script(script: str) -> None:
    sys.path.insert(0, str(ROOT))
    try:
        runpy.run_path(str(ROOT / script), run_name="__main__")
    finally:
        sys.path.remove(str(ROOT))


def pdflatex(document: Path) -> str:
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", document.name],
        cwd=document.parent, capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0:
        errors = [line for line in result.stdout.splitlines() if line.startswith("!")]
        raise RuntimeError(f"{{document.name}} did not compile: {{errors[:3] or 'see the log'}}")
    return result.stdout


def compile_diagram(script: str, output: str) -> None:
    """Compile a standalone diagram away from scripts/, and keep only its PDF."""
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / Path(script).name
        shutil.copy(ROOT / script, source)
        for _ in range(3):  # chemfig arrows need a second pass
            if "Rerun" not in pdflatex(source):
                break
        (ROOT / output).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source.with_suffix(".pdf"), ROOT / output)


def compile_document() -> None:
    document = ROOT / DOCUMENT
    output = pdflatex(document)
    aux = document.with_suffix(".aux").read_text(encoding="utf-8", errors="replace")
    if "\\\\bibdata" in aux:
        subprocess.run(["bibtex", document.stem], cwd=ROOT, capture_output=True)
        output = pdflatex(document)
    passes = 1
    while "Rerun" in output and passes < MAX_PASSES:
        output = pdflatex(document)
        passes += 1


def main() -> int:
    failed = []
    for script, output in FIGURES:
        try:
            if script.endswith(".tex"):
                compile_diagram(script, output)
            else:
                run_script(script)
            print(f"  {{output}}")
        except Exception as error:  # a broken figure must not hide the others
            failed.append(output)
            print(f"  {{output}}  FAILED: {{error}}")
    try:
        compile_document()
        print(f"  {{Path(DOCUMENT).with_suffix('.pdf')}}")
    except (RuntimeError, FileNotFoundError) as error:
        failed.append(DOCUMENT)
        print(f"  {{DOCUMENT}}  FAILED: {{error}}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
'''

EJECTED_MD = """# This paper was ejected from LabHarness

Written by `labharness eject` ({version}) on {date}, from a workspace for the **{journal}**
journal style. Everything here regenerates **without LabHarness installed**.

## Regenerate everything

```bash
pip install -r requirements.txt
python build.py
```

It also needs a LaTeX distribution with `pdflatex` and `bibtex` (MiKTeX or TeX Live).
`compile.sh` and `compile.ps1` are shortcuts for the same command.

## What is here

| Path | What it is |
|---|---|
| `data/` | The raw data, as it was |
| `scripts/*.py` | One script per figure. They import `_labharness`, not LabHarness |
| `scripts/*.tex` | Diagrams, each a complete standalone document |
| `_labharness/` | The part of LabHarness these scripts use, frozen: no updates, on purpose |
| `figures/` | The figures as they were when ejected, so the paper compiles straight away |
| `build.py` | Runs the scripts in order, compiles the diagrams, then the paper |
| `requirements.txt` | The exact versions of the Python packages that drew the figures |

## What is guaranteed, and what is not

- With the versions in `requirements.txt`, the figures regenerate with the same data, the same
  fits and the same style. The PDF files will not be identical byte for byte: Matplotlib and
  LaTeX write dates into them.
- There is no watcher here: rebuilding is `python build.py`.
- This copy does not follow LabHarness any more. To keep working with LabHarness, use the
  workspace this was ejected from.
"""


def write_build_files(workspace: Workspace, target: Path, modules: list[str]) -> list[str]:
    """Write build.py, requirements.txt, EJECTED.md and the compile shortcuts into ``target``."""
    from labharness import __version__

    date = datetime.now(UTC).date().isoformat()
    figures = [(figure.script.as_posix(), figure.output.as_posix()) for figure in workspace.figures]
    files = {
        "build.py": BUILD_PY.format(
            version=__version__,
            date=date,
            document=workspace.document.name,
            figures=pprint.pformat(figures, width=90),
        ),
        "requirements.txt": requirements([*modules, *_data_extras(workspace)]),
        "EJECTED.md": EJECTED_MD.format(version=__version__, date=date, journal=workspace.journal),
        "compile.sh": "#!/usr/bin/env sh\n# Regenerate the figures and the paper.\n"
        'exec python build.py "$@"\n',
        "compile.ps1": "# Regenerate the figures and the paper.\npython build.py @args\n",
    }
    for name, text in files.items():
        (target / name).write_text(text, encoding="utf-8", newline="\n")
    return list(files)


def _data_extras(workspace: Workspace) -> list[str]:
    """Extras the data needs to be read, whatever module reads it: excel for a workbook."""
    inputs = [path for figure in workspace.figures for path in figure.inputs]
    return ["excel"] if any(path.suffix.lower() == ".xlsx" for path in inputs) else []


def requirements(modules: list[str]) -> str:
    """Exact versions of the packages the used modules need, as installed right now."""
    lines = ["# The exact versions that drew these figures, written by labharness eject."]
    for name in _distributions(modules):
        try:
            lines.append(f"{name}=={metadata.version(name)}")
        except metadata.PackageNotFoundError:
            lines.append(f"# {name}: not installed when this was ejected")
    return "\n".join(lines) + "\n"


def _distributions(modules: list[str]) -> list[str]:
    """The requirements of the extras named like the modules (chem, plots...), plus theirs."""
    try:
        requires = metadata.requires("labharness") or []
    except metadata.PackageNotFoundError:  # pragma: no cover - running uninstalled
        return []
    names: list[str] = []
    for requirement in requires:
        spec, _, marker = requirement.partition(";")
        extra = re.search(r"extra\s*==\s*['\"]([^'\"]+)['\"]", marker)
        if extra and extra.group(1) in modules:
            name = re.match(r"[A-Za-z0-9_.\-]+", spec.strip())
            if name and name.group(0) not in names:
                names.append(name.group(0))
    # svglib draws the structures through reportlab: pin it too, it decides the geometry.
    if "svglib" in names and "reportlab" not in names:
        names.append("reportlab")
    return names
