# Instructions for AI agents working in this LabHarness workspace

This folder is a scientific writing workspace managed with LabHarness: raw data in `data/`,
transparent scripts in `scripts/`, generated figures in `figures/`, and the manuscript in
`paper.tex`. The human stays in the loop: you write readable scripts, they decide.

> v0.1 placeholder: domain-specific scientific rules will be added in a later version.

## Rules

1. **`data/` holds raw data: never modify it.**
2. **Never edit files in `figures/` by hand.** Figures are produced by the scripts in `scripts/`
   and declared in `labharness.toml`.
3. A new figure means a script in `scripts/` plus its entry in `labharness.toml`
   (`labharness add` does both).
4. Use the right module for each kind of figure:
   - chemical structures → the `chem` module (RDKit);
   - reaction mechanisms with arrows, flowcharts and diagrams → the `diagrams` module
     (TikZ/chemfig), **never RDKit**;
   - plots and regressions → the `plots` module.
5. **Never set fonts, sizes or colours** in a script or in a figure's `.tex` file. Everything
   comes from the shared style: one typeface for the whole document.
6. Keep scripts short, readable and runnable on their own. Start each one with a comment saying
   which figure it produces.
7. **Never invent or "adjust" experimental data.** Do not interpolate, drop outliers or fill in
   values without an explicit request. If data is missing, ask.
8. **Never write SMILES from memory.** When starting from a name, run `labharness resolve` and
   leave the SMILES in `data/` so the human can check it.
9. Do not rewrite the scientific text of `paper.tex` unless explicitly asked. Insert and update
   figures; do not write the discussion.
