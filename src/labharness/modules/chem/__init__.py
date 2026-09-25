"""Chemical structures: SMILES to vector PDF (RDKit), and names to SMILES (OPSIN).

Structures need the ``chem`` extra; resolving names needs ``iupac`` and Java. The lab's own
compound inventory, looked up before OPSIN and usable in figures, needs ``library``.

    from labharness.modules.chem import render_structure

    render_structure(smiles_file="data/catalyst.smi", output="figures/catalyst.pdf")
"""

from labharness.modules.chem.library import Compound, Library, check, load_library
from labharness.modules.chem.resolve import resolve_name, write_smiles
from labharness.modules.chem.structures import read_smiles, render_structure

__all__ = [
    "Compound",
    "Library",
    "check",
    "load_library",
    "read_smiles",
    "render_structure",
    "resolve_name",
    "write_smiles",
]
