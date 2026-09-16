# figures/atenolol.pdf -- the molecule being degraded, from data/atenolol.smi
#
# The SMILES was not typed by hand: it came from the IUPAC name through
# `labharness resolve`, and RDKit confirms the formula is C14H22N2O3.
from labharness.modules.chem import render_structure

render_structure(output="figures/atenolol.pdf", smiles_file="data/atenolol.smi")
