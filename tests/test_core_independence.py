"""The core does not know any domain: nothing outside a module imports a module.

That is what lets someone add a package for their field without anyone touching the core
(ADR 31). The exceptions are listed, each with what it needs, and the list may only shrink: a
listed file that no longer imports a module fails the test until it is taken off.
"""

import ast
from pathlib import Path

SOURCE = Path(__file__).parent.parent / "src" / "labharness"

# file -> why it still names a module. Retiring one needs a way for a domain to bring its own
# kind of source file (today a .tex diagram is built by the diagrams module).
EXCEPTIONS = {
    "watch/runner.py": "builds a .tex source through the diagrams module",
    "eject.py": "turns a .tex diagram into a standalone document through the diagrams module",
}


def importers() -> set[str]:
    found = set()
    for path in SOURCE.rglob("*.py"):
        relative = path.relative_to(SOURCE).as_posix()
        if relative.startswith("modules/"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "labharness.modules"
            ):
                found.add(relative)
            if isinstance(node, ast.Import) and any(
                alias.name.startswith("labharness.modules") for alias in node.names
            ):
                found.add(relative)
    return found


def test_nothing_outside_a_module_imports_one_but_the_listed_exceptions() -> None:
    assert importers() - set(EXCEPTIONS) == set()


def test_every_exception_is_still_needed() -> None:
    assert set(EXCEPTIONS) - importers() == set()
