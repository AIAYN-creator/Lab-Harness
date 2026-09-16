"""Chemical structures: SMILES to vector PDF (RDKit), and names to SMILES (OPSIN).

Structures need the ``chem`` extra; resolving names needs ``iupac`` and Java.

    from labharness.modules.chem import render_structure

    render_structure(smiles_file="data/catalyst.smi", output="figures/catalyst.pdf")
"""

from labharness.modules.chem.resolve import resolve_name
from labharness.modules.chem.structures import read_smiles, render_structure

__all__ = ["read_smiles", "render_structure", "resolve_name"]
