"""Turning a systematic IUPAC name into a SMILES string, offline, with OPSIN.

A separate step on purpose: the SMILES lands in a file you can check before it becomes a
figure, and the watcher never pays for starting a JVM.
"""

from pathlib import Path

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError
from labharness.core.extras import require


def resolve_name(name: str, output: Path | str | None = None) -> str:
    """Resolve ``name`` to a SMILES string, optionally writing it to ``output``."""
    if not name.strip():
        raise LabHarnessError("give resolve_name a chemical name")

    py2opsin = require("py2opsin", extra="iupac")
    try:
        smiles = str(py2opsin.py2opsin(name)).strip()
    except FileNotFoundError as error:  # no Java on this machine
        raise LabHarnessError(
            "OPSIN needs Java, and there is no 'java' on PATH. Install a JDK (for example "
            "Eclipse Temurin), or write the SMILES by hand."
        ) from error

    if not smiles:
        raise LabHarnessError(
            f"OPSIN could not read '{name}'. It understands systematic IUPAC names, not trade "
            "names or in-house codes: check the spelling, or use the SMILES directly."
        )

    smiles = _canonical(smiles)

    if output is not None:
        output = Path(output)
        with atomic_output(output) as temporary:
            temporary.write_text(f"{smiles}\n# resolved from: {name}\n", encoding="utf-8")
    return smiles


def _canonical(smiles: str) -> str:
    """Canonicalise with RDKit when it is installed, so files are comparable."""
    try:
        chem = require("rdkit.Chem", extra="chem")
    except LabHarnessError:
        return smiles

    molecule = chem.MolFromSmiles(smiles)
    if molecule is None:
        raise LabHarnessError(f"OPSIN returned a SMILES RDKit cannot read: {smiles}")
    return str(chem.MolToSmiles(molecule))
