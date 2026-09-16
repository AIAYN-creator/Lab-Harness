"""Compiling the document with latexmk."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from labharness.core.errors import LabHarnessError


@dataclass(frozen=True)
class CompileResult:
    ok: bool
    pdf: Path | None
    errors: tuple[str, ...]
    log: str

    @property
    def summary(self) -> str:
        return "\n".join(self.errors) if self.errors else "LaTeX failed, see the log"


def compile_document(document: Path) -> CompileResult:
    """Run latexmk once over ``document``. Incremental: it only redoes what changed."""
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        raise LabHarnessError(
            "cannot find 'latexmk'. Install a LaTeX distribution, and on Windows with MiKTeX "
            "install Perl as well (for example Strawberry Perl)."
        )

    result = subprocess.run(
        # No -halt-on-error: latexmk needs extra passes for bibliographies and cross-references,
        # and nonstopmode already stops it from waiting for input.
        [latexmk, "-pdf", "-interaction=nonstopmode", document.name],
        cwd=document.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    pdf = document.with_suffix(".pdf")
    ok = result.returncode == 0 and pdf.is_file()

    errors = _errors(output)
    if not ok and not errors:
        # latexmk summarises instead of repeating what LaTeX said, so the real message is
        # in the log. Without this the terminal says "LaTeX failed" and nothing else.
        errors = _errors(_read_log(document))

    return CompileResult(ok=ok, pdf=pdf if pdf.is_file() else None, errors=errors, log=output)


def _read_log(document: Path) -> str:
    log = document.with_suffix(".log")
    if not log.is_file():
        return ""
    return log.read_text(encoding="utf-8", errors="replace")


def _errors(output: str) -> tuple[str, ...]:
    """The lines a person needs: LaTeX errors and the line they happened on."""
    interesting = [
        line.rstrip()
        for line in output.splitlines()
        if line.startswith("!") or line.startswith("l.") or "not found" in line
    ]
    return tuple(dict.fromkeys(interesting))
