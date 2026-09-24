# Rules for chemistry

Read together with `AGENTS.md`, whose rules still apply. Where they disagree, this file wins.

## Which module draws what

1. Chemical structures → the `chem` module (RDKit). Reaction mechanisms with arrows, schemes and
   diagrams → the `diagrams` module (TikZ and chemfig), **never RDKit**: it cannot draw
   electron-pushing arrows.

## Molecules

2. **Never write a SMILES from memory.** Look the compound up in the lab inventory first, then
   run `labharness resolve` on its systematic name, and leave the SMILES in `data/` so the human
   can check it. If neither finds it, ask.
3. **Stereochemistry:** a chiral compound's SMILES must carry it. If `resolve` or the inventory
   warns that a stereocentre is unspecified, **stop and ask**; never pick an enantiomer.
4. **Names:** IUPAC for systematic names; common names only where the group uses them, and the
   inventory decides which.

## Results

5. **ee and er:** use the one the data gives, and say which enantiomer is the major one when it
   is known. Never convert between them unless asked.
6. **Yield and conversion are different things.** If the data does not say which it is, ask.

## Mechanisms

7. Every curved arrow starts at an electron pair, or at a single electron with a half-headed
   arrow, and ends where the new bond forms. **If you are not sure of the mechanism, draw the
   reaction scheme, not an invented mechanism.**
