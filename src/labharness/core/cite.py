"""Adding a reference to the bibliography from its DOI.

The one place LabHarness goes online, and only when asked: ``labharness cite DOI`` asks doi.org
for the BibTeX of the work, the registry every DOI belongs to, and appends it to the workspace's
bibliography under a short key, so the text can cite it with ``\\cite{key}``. A DOI already in
the bibliography is never added twice.
"""

import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError

_DOI = re.compile(r"10\.\d{4,9}/\S+")
_KEY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")
TIMEOUT_S = 20


@dataclass(frozen=True)
class Citation:
    key: str
    added: bool  # False when the DOI was already in the bibliography


def cite(doi: str, bibliography: Path) -> Citation:
    """Add the work with this DOI to ``bibliography``, unless it is already there."""
    doi = normalise_doi(doi)
    text = bibliography.read_text(encoding="utf-8") if bibliography.is_file() else ""
    existing = _entry_with_doi(text, doi)
    if existing is not None:
        return Citation(existing, added=False)

    entry = fetch_bibtex(doi)
    key = _new_key(entry, set(_KEY.findall(text)))
    entry = _KEY.sub(lambda match: match.group(0).replace(match.group(1), key), entry.strip(), 1)
    kept = text.rstrip()
    with atomic_output(bibliography) as temporary:
        temporary.write_text(f"{kept}\n\n{entry}\n" if kept else f"{entry}\n", encoding="utf-8")
    return Citation(key, added=True)


def normalise_doi(text: str) -> str:
    """The DOI in ``10.1021/...``, ``doi:10.1021/...`` or ``https://doi.org/10.1021/...``."""
    found = _DOI.search(urllib.parse.unquote(text.strip()))
    if found is None:
        raise LabHarnessError(f"'{text}' is not a DOI: a DOI looks like 10.1021/ja00001a001")
    return found.group(0).rstrip(".,;")


def fetch_bibtex(doi: str) -> str:
    """The BibTeX doi.org gives for ``doi``."""
    request = urllib.request.Request(
        f"https://doi.org/{urllib.parse.quote(doi, safe='/')}",
        headers={"Accept": "application/x-bibtex; charset=utf-8", "User-Agent": "LabHarness"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            entry = str(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise LabHarnessError(f"doi.org does not know the DOI {doi}: check it") from None
        raise LabHarnessError(f"doi.org answered {error.code} for {doi}") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise LabHarnessError(
            f"could not reach doi.org ({error}). labharness cite needs the network."
        ) from None
    if not _KEY.search(entry):
        raise LabHarnessError(f"doi.org gave no BibTeX for {doi}")
    return entry


def _entry_with_doi(text: str, doi: str) -> str | None:
    """The key of the entry whose doi field is ``doi``, compared without case."""
    for start in _KEY.finditer(text):
        end = text.find("\n@", start.end())
        body = text[start.end() : end if end != -1 else len(text)]
        if (_field(body, "doi") or "").strip().lower() == doi.lower():
            return start.group(1)
    return None


def _new_key(entry: str, taken: set[str]) -> str:
    """The first author's surname and the year, as the demo writes them: moragomez2020."""
    authors = _field(entry, "author") or ""
    first = authors.split(" and ")[0]
    surname = first.split(",")[0] if "," in first else (first.split() or [""])[-1]
    year = (_field(entry, "year") or "").strip()
    base = (_ascii_letters(surname) or "ref") + year
    key, suffix = base, ord("a")
    while key in taken:
        key, suffix = f"{base}{chr(suffix)}", suffix + 1
    return key


def _field(entry: str, name: str) -> str | None:
    """The value of a BibTeX field, with nested braces, or None."""
    match = re.search(rf"\b{name}\s*=\s*", entry, flags=re.IGNORECASE)
    if match is None:
        return None
    rest = entry[match.end() :]
    if not rest.startswith("{"):
        return re.split(r"[,}\n]", rest, maxsplit=1)[0].strip().strip('"')
    depth = 0
    for index, character in enumerate(rest):
        depth += {"{": 1, "}": -1}.get(character, 0)
        if depth == 0:
            return rest[1:index]
    return None


def _ascii_letters(text: str) -> str:
    """Letters only, accents dropped, LaTeX accent commands too: Mora-G{\\'o}mez -> moragomez."""
    text = re.sub(r"\\[^A-Za-z]|\\[A-Za-z]+\s*", "", text)
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(character for character in plain.lower() if character.isalpha())
