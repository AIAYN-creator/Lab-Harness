"""Every link in the documentation to a file of this repository, and to a section of one, exists."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
LINK = re.compile(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)|(?:src|href)="([^"]+)"')


def documents() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return [ROOT / name for name in listed.stdout.split() if (ROOT / name).is_file()]


def sections(document: Path) -> set[str]:
    """The anchors GitHub gives the headings of a Markdown file."""
    found = set()
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", document.read_text(encoding="utf-8"), re.M):
        plain = re.sub(r"[^\w\- ]", "", heading.replace("`", "").lower())
        found.add(plain.replace(" ", "-"))
    return found


def broken(document: Path) -> list[str]:
    missing = []
    for markdown, html in LINK.findall(document.read_text(encoding="utf-8")):
        link = markdown or html
        if re.match(r"[a-z]+:", link):  # http:, mailto:...
            continue
        target, _, anchor = link.partition("#")
        found = document if not target else document.parent / target
        where = f"{document.relative_to(ROOT).as_posix()} -> {link}"
        if not found.exists() or (
            anchor and found.suffix == ".md" and anchor not in sections(found)
        ):
            missing.append(where)
    return missing


@pytest.mark.skipif(not documents(), reason="not a git checkout")
def test_no_link_in_the_documentation_is_broken() -> None:
    assert [problem for document in documents() for problem in broken(document)] == []
