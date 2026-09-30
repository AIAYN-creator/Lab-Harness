"""Every link in the documentation to a file of this repository points at a file that exists."""

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


def broken(document: Path) -> list[str]:
    missing = []
    for markdown, html in LINK.findall(document.read_text(encoding="utf-8")):
        target = (markdown or html).split("#")[0]
        if not target or re.match(r"[a-z]+:", target):  # an anchor, or http:, mailto:...
            continue
        if not (document.parent / target).exists():
            missing.append(f"{document.relative_to(ROOT).as_posix()} -> {target}")
    return missing


@pytest.mark.skipif(not documents(), reason="not a git checkout")
def test_no_link_in_the_documentation_is_broken() -> None:
    assert [problem for document in documents() for problem in broken(document)] == []
