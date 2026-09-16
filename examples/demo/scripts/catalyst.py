# figures/catalyst.pdf -- the organocatalyst, drawn from data/catalyst.smi
from labharness.modules.chem import render_structure

render_structure(output="figures/catalyst.pdf", smiles_file="data/catalyst.smi")
