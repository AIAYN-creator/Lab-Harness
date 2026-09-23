"""Compiling LaTeX, and turning its output into something a person can read.

Shared by the watcher, which compiles the document, and by the diagrams module, which
compiles each figure on its own.

LabHarness drives the passes itself instead of handing them to latexmk: pdflatex, then
BibTeX (or Biber) only when the citations or the bibliography changed, then pdflatex again
until LaTeX stops asking for a rerun. That is all latexmk does for a paper, and latexmk is a
Perl script, which MiKTeX on Windows does not ship. latexmk is still used when a workspace asks
for it (``builder = "latexmk"`` in the manifest).
"""

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from labharness.core.errors import LabHarnessError

# A paper settles in three passes; five leaves room for a table of contents or cross-references
# that move page numbers, without looping forever on a document that never settles.
MAX_PASSES = 5
# Written next to the document: which citations and bibliography files the last BibTeX run saw.
BIBLIOGRAPHY_STATE = ".{stem}.labharness-bib"
LATEXMK_ENGINE_FLAGS = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}


@dataclass(frozen=True)
class LatexResult:
    ok: bool
    pdf: Path | None
    errors: tuple[str, ...]
    log: str
    passes: int = 0
    bibliography: bool = False

    @property
    def summary(self) -> str:
        return "\n".join(self.errors) if self.errors else "LaTeX failed, see the log"


def run_full_build(document: Path, engine: str = "pdflatex") -> LatexResult:
    """Compile ``document`` completely: bibliography and cross-references included.

    Incremental where it pays: the bibliography tool only runs when the citations in the
    ``.aux`` file, the bibliography files or the ``.bbl`` changed since it last ran.
    """
    compiler = _tool(engine, f"cannot find '{engine}'. Install MiKTeX or TeX Live.")

    output, code = _run(compiler, document)
    passes = 1
    ran_bibliography = False
    errors: list[str] = []

    tool = _bibliography_tool(document)
    if tool is not None and _bibliography_is_stale(document):
        bibliography_errors = _run_bibliography(tool, document)
        errors += bibliography_errors
        ran_bibliography = True
        if not bibliography_errors:
            _remember_bibliography(document)
        # The citations need two more passes: one to read the .bbl, one to settle the labels.
        output, code = _run(compiler, document)
        passes += 1

    while _asks_for_rerun(output) and passes < MAX_PASSES:
        output, code = _run(compiler, document)
        passes += 1

    pdf = document.with_suffix(".pdf")
    ok = code == 0 and pdf.is_file() and not errors
    latex_errors = summarise_errors(output) or (() if ok else summarise_errors(read_log(document)))
    return LatexResult(
        ok=ok,
        pdf=pdf if pdf.is_file() else None,
        errors=tuple(dict.fromkeys([*latex_errors, *errors])),
        log=output,
        passes=passes,
        bibliography=ran_bibliography,
    )


def run_pdflatex(document: Path, passes: int = 2, engine: str = "pdflatex") -> LatexResult:
    """Compile with the engine directly, for when only a figure changed.

    Redrawing a figure needs one pass, and LaTeX itself says when it needs another, so the
    quick path listens for that instead of assuming.
    """
    compiler = _tool(engine, f"cannot find '{engine}'. Install MiKTeX or TeX Live.")

    output, code = "", 1
    done = 0
    for attempt in range(passes):
        output, code = _run(compiler, document)
        done += 1
        if not _asks_for_rerun(output) or attempt == passes - 1:
            break

    pdf = document.with_suffix(".pdf")
    ok = code == 0 and pdf.is_file()
    errors = summarise_errors(output) or (() if ok else summarise_errors(read_log(document)))
    return LatexResult(
        ok=ok, pdf=pdf if pdf.is_file() else None, errors=errors, log=output, passes=done
    )


def run_latexmk(document: Path, engine: str = "pdflatex") -> LatexResult:
    """Compile ``document`` with latexmk, for workspaces that ask for it.

    No -halt-on-error: latexmk needs its extra passes for bibliographies and
    cross-references, and nonstopmode already stops it from waiting for input.
    """
    latexmk = _tool(
        "latexmk",
        "cannot find 'latexmk'. It is optional: remove 'builder = \"latexmk\"' from the "
        "manifest, or install it (on Windows with MiKTeX it also needs Perl).",
    )

    result = subprocess.run(
        [latexmk, LATEXMK_ENGINE_FLAGS[engine], "-interaction=nonstopmode", document.name],
        cwd=document.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    pdf = document.with_suffix(".pdf")
    ok = result.returncode == 0 and pdf.is_file()

    errors = summarise_errors(output)
    if not ok and not errors:
        # latexmk summarises instead of repeating what LaTeX said, so the real message is
        # in the log. Without this the terminal says "LaTeX failed" and nothing else.
        errors = summarise_errors(read_log(document))

    return LatexResult(ok=ok, pdf=pdf if pdf.is_file() else None, errors=errors, log=output)


def read_log(document: Path) -> str:
    log = document.with_suffix(".log")
    if not log.is_file():
        return ""
    return log.read_text(encoding="utf-8", errors="replace")


def summarise_errors(output: str) -> tuple[str, ...]:
    """The lines a person needs: LaTeX errors and the line they happened on."""
    interesting = [
        line.rstrip()
        for line in output.splitlines()
        if line.startswith("!") or line.startswith("l.") or "not found" in line
    ]
    return tuple(dict.fromkeys(interesting))


def _tool(name: str, missing: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise LabHarnessError(missing)
    return found


def _run(compiler: str, document: Path) -> tuple[str, int]:
    result = subprocess.run(
        [compiler, "-interaction=nonstopmode", document.name],
        cwd=document.parent,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    return result.stdout + result.stderr, result.returncode


def _asks_for_rerun(output: str) -> bool:
    # "Rerun to get cross-references right", "Label(s) may have changed. Rerun...",
    # and the same request from natbib, mciteplus, biblatex and hyperref.
    return "Rerun" in output


def _bibliography_tool(document: Path) -> str | None:
    """Biber for biblatex, BibTeX for \\bibliography, nothing for a document without one."""
    if document.with_suffix(".bcf").is_file():
        return "biber"
    aux = document.with_suffix(".aux")
    if aux.is_file() and "\\bibdata" in aux.read_text(encoding="utf-8", errors="replace"):
        return "bibtex"
    return None


def _bibliography_fingerprint(document: Path) -> str:
    """What the bibliography depends on: the citations and the bibliography files."""
    aux = document.with_suffix(".aux")
    lines = [
        line
        for line in aux.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith(("\\citation", "\\bibdata", "\\bibstyle", "\\abx@aux"))
    ]
    digest = hashlib.sha256("\n".join(lines).encode("utf-8"))
    for bib in sorted(document.parent.glob("*.bib")):
        digest.update(bib.name.encode("utf-8"))
        digest.update(bib.read_bytes())
    bcf = document.with_suffix(".bcf")
    if bcf.is_file():
        digest.update(bcf.read_bytes())
    return digest.hexdigest()


def _state_file(document: Path) -> Path:
    return document.with_name(BIBLIOGRAPHY_STATE.format(stem=document.stem))


def _bibliography_is_stale(document: Path) -> bool:
    if not document.with_suffix(".bbl").is_file():
        return True
    state = _state_file(document)
    remembered = state.read_text(encoding="utf-8").strip() if state.is_file() else ""
    return remembered != _bibliography_fingerprint(document)


def _remember_bibliography(document: Path) -> None:
    _state_file(document).write_text(_bibliography_fingerprint(document) + "\n", encoding="utf-8")


def _run_bibliography(tool: str, document: Path) -> list[str]:
    executable = _tool(tool, f"the document needs '{tool}', which is not installed.")
    result = subprocess.run(
        [executable, document.stem],
        cwd=document.parent,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    output = result.stdout + result.stderr
    # The exit code cannot be trusted: MiKTeX's BibTeX exits 1 both for a warning and for a
    # missing database. What BibTeX always prints is its count of error messages.
    failed = result.returncode >= 2 or "error message" in output
    if tool == "biber":
        failed = result.returncode != 0 or "ERROR -" in output
    if not failed:
        return []

    messages = [
        line.strip()
        for line in output.splitlines()
        if line.startswith(("I couldn't", "I found no", "ERROR -"))
    ]
    return [f"{tool}: {message}" for message in dict.fromkeys(messages)] or [f"{tool} failed"]
