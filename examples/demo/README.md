# Demo workspace

The workspace used in the v0.1 live demo, and the end-to-end test of the whole pipeline: a
chemical structure, a reaction mechanism and a calibration curve, all generated from the files
in `data/`.

```bash
uv run labharness build     # build everything once
uv run labharness watch     # then change a file in data/ and save
```

Three things to try, each exercising a different module:

| Change this | And watch |
|---|---|
| The SMILES in `data/catalyst.smi` | The structure is redrawn |
| A number in `data/calibration.csv` | The point, its error bar, the fit **and the slope quoted in the text** all follow |
| A label in `scripts/mechanism.tex` | The mechanism is recompiled |

> **The numbers in `data/` are demonstration data, not measurements.** The catalyst is real:
> `data/catalyst.smi` was produced by `labharness resolve "(2S)-pyrrolidine-2-carboxylic acid"`.
> The reference in `references.bib` is a placeholder.
