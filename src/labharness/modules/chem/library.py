"""The lab's own compound inventory: find a compound by its name or in-house code.

An optional extra, and optional in every way: without a library nothing changes, and a
library with broken rows only loses those rows, with a warning each. It is read with the
same reader as any table, so an export from Access, Excel or anything else works as it is,
with its columns recognised by name.

Each compound is checked when it is read, and nothing is ever corrected: the checks say what
they see, and the person decides. The two that ship are the ones that catch the costly
mistakes in a lab of asymmetric catalysis: a chiral compound with no stereochemistry, which
draws fine and is the wrong enantiomer, and a SMILES pasted into the wrong row, which the
molecular formula gives away.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from labharness.core.errors import LabHarnessError
from labharness.core.extras import require
from labharness.core.tabular import read_rows

# The names a column goes by in real inventories, compared without case, accents or spaces.
COLUMNS: dict[str, tuple[str, ...]] = {
    "smiles": ("smiles", "smile", "smiles code", "smiles_code"),
    "name": ("nombre", "nombre comun", "name", "common name"),
    "formula": ("formula", "formula molecular", "molecular formula", "fm"),
    "code": ("codigo", "id", "ref", "code"),
    "aliases": ("alias", "aliases", "sinonimos", "synonyms"),
}
_ELEMENT = re.compile(r"([A-Z][a-z]?)(\d*)")


@dataclass(frozen=True)
class Compound:
    """One row of the inventory."""

    row: int  # the line of the file, or the row of the sheet, it came from
    name: str
    smiles: str
    formula: str = ""
    code: str = ""
    aliases: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return self.code or self.name


@dataclass(frozen=True)
class Library:
    source: Path
    compounds: tuple[Compound, ...]
    # Rows that could not be used, each with its reason, and what the checks found.
    rejected: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()

    def find(self, key: str) -> Compound | None:
        """The compound whose name, code or alias is ``key``, never one that looks like it."""
        wanted = _normal(key)
        for compound in self.compounds:
            if wanted in {_normal(t) for t in (compound.name, compound.code, *compound.aliases)}:
                return compound
        return None


def load_library(
    path: Path | str, sheet: str | int | None = None, columns: Mapping[str, str] | None = None
) -> Library:
    """Read an inventory (CSV, or .xlsx with the excel extra) and check every compound.

    ``columns`` maps a field (smiles, name, formula, code, aliases) to the header that holds
    it, for an inventory whose headers are not recognised on their own.
    """
    chem = require("rdkit.Chem", extra="chem")
    rdlogger = require("rdkit.RDLogger", extra="chem")
    path = Path(path)
    read = read_rows(path, sheet=sheet)
    where = _locate(read.headers, columns or {}, path)

    compounds, rejected, findings = [], [], []
    rdlogger.DisableLog("rdApp.*")  # a broken row is reported below, once, in plain words
    try:
        for line, cells in zip(read.lines, read.rows, strict=True):
            field = {key: cells[index].strip() for key, index in where.items()}
            if not field["smiles"] and not field["name"]:
                continue
            molecule = chem.MolFromSmiles(field["smiles"]) if field["smiles"] else None
            if molecule is None:
                rejected.append(
                    f"row {line} ({field['name'] or '?'}): RDKit cannot read the SMILES "
                    f"'{field['smiles']}'"
                )
                continue
            compound = Compound(
                row=line,
                name=field["name"],
                smiles=str(chem.MolToSmiles(molecule)),
                formula=field.get("formula", ""),
                code=field.get("code", ""),
                aliases=tuple(a.strip() for a in field.get("aliases", "").split(";") if a.strip()),
            )
            compounds.append(compound)
            findings += [f"row {line} ({compound.label}): {text}" for text in check(compound)]
    finally:
        rdlogger.EnableLog("rdApp.*")
    return Library(path, tuple(compounds), tuple(rejected), tuple(findings))


def check(compound: Compound) -> list[str]:
    """What every check sees in ``compound``. None of them changes it."""
    chem = require("rdkit.Chem", extra="chem")
    molecule = chem.MolFromSmiles(compound.smiles)
    return [finding for run in CHECKS for finding in run(molecule, compound)]


def unspecified_stereo(molecule: Any, compound: Compound) -> list[str]:
    """Stereocentres and double bonds that could be either way, but the SMILES does not say."""
    chem = require("rdkit.Chem", extra="chem")
    found = []
    for stereo in chem.FindPotentialStereo(molecule):
        if stereo.specified != chem.StereoSpecified.Unspecified:
            continue
        if stereo.type == chem.StereoType.Atom_Tetrahedral:
            atom = molecule.GetAtomWithIdx(stereo.centeredOn)
            found.append(
                f"the stereocentre at {atom.GetSymbol()}{stereo.centeredOn + 1} is not "
                "specified: the SMILES stands for either enantiomer"
            )
        elif stereo.type == chem.StereoType.Bond_Double:
            found.append(f"double bond {stereo.centeredOn + 1} has no E/Z in the SMILES")
    return found


def formula_mismatch(molecule: Any, compound: Compound) -> list[str]:
    """The molecular formula in the inventory is not the one of its SMILES."""
    if not compound.formula:
        return []
    descriptors = require("rdkit.Chem.rdMolDescriptors", extra="chem")
    calculated = str(descriptors.CalcMolFormula(molecule))
    if _elements(compound.formula) == _elements(calculated):
        return []
    return [f"the formula {compound.formula} does not match the SMILES, which is {calculated}"]


# Each check takes the molecule and its row and returns what it found, in words. Adding one
# is adding a function here.
CHECKS: tuple[Callable[[Any, Compound], list[str]], ...] = (unspecified_stereo, formula_mismatch)


def workspace_library() -> tuple[Library | None, str | None]:
    """The inventory [library] in the manifest names, or None and why it could not be read.

    Never an error: a library that cannot be read only means resolving goes on without it.
    """
    from labharness.core.manifest import find_workspace, load_workspace

    try:
        workspace = load_workspace(find_workspace())
    except LabHarnessError:
        return None, None
    settings = workspace.library
    if settings is None:
        return None, None
    try:
        library = load_library(
            workspace.root / settings.file, settings.sheet, dict(settings.columns)
        )
    except LabHarnessError as error:  # the extra is missing, or the file is
        return None, f"the compound library was not used: {error}"
    return library, None


def settings_for(path: Path) -> dict[str, Any]:
    """The sheet and columns [library] in the manifest gives for ``path``, if it names it.

    A script only says which file its compound is in; how to read that file is said once, in
    the manifest. An ejected copy, with no manifest, reads it by the recognised headers.
    """
    from labharness.core.manifest import find_workspace, load_workspace

    try:
        workspace = load_workspace(find_workspace())
    except LabHarnessError:
        return {}
    settings = workspace.library
    if settings is None or (workspace.root / settings.file).resolve() != path.resolve():
        return {}
    return {"sheet": settings.sheet, "columns": dict(settings.columns)}


def _locate(headers: list[str], columns: Mapping[str, str], path: Path) -> dict[str, int]:
    """Which column holds each field: the mapping given, or a header it goes by."""
    where = {}
    normal = [_normal(header) for header in headers]
    for field, names in COLUMNS.items():
        if field in columns:
            if columns[field] not in headers:
                raise LabHarnessError(
                    f"'{path.name}' has no column '{columns[field]}' for {field}. "
                    f"It has: {', '.join(headers)}"
                )
            where[field] = headers.index(columns[field])
            continue
        index = next((i for i, header in enumerate(normal) if header in names), None)
        if index is not None:
            where[field] = index
    for field in ("smiles", "name"):
        if field not in where:
            raise LabHarnessError(
                f"'{path.name}' has no column for the {field}. Its columns are "
                f"{', '.join(headers)}: say which one it is with columns = {{ {field} = "
                '"..." } in [library] in labharness.toml.'
            )
    return where


def _normal(text: str) -> str:
    """Lower case, no accents, single spaces: 'Nombre  Común' and 'nombre comun' are equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(plain.lower().replace("_", " ").split())


def _elements(formula: str) -> Counter[str]:
    """Element counts of a formula written in any order, with or without spaces."""
    counts: Counter[str] = Counter()
    for element, number in _ELEMENT.findall(formula.replace(" ", "")):
        counts[element] += int(number or 1)
    return counts
