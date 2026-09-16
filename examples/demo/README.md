# Demo workspace

The workspace used in the v0.1 live demo, and the end-to-end test of the whole pipeline: a
molecule, a reaction scheme and two fits, all generated from the files in `data/`.

```bash
uv run labharness build     # build everything once
uv run labharness watch     # then change a file in data/ and save
```

Four things to try, each exercising a different module:

| Change this | And watch |
|---|---|
| The SMILES in `data/atenolol.smi` | The structure is redrawn |
| A concentration in `data/decay.csv` | The curve, the fit **and the rate constant quoted in the text** all follow |
| A value in `data/kapp.csv` | The straight line and its slope, quoted in the text, follow |
| A label in `scripts/mechanism.tex` | The scheme is recompiled |

## About the data

The subject follows a published study of the electrochemical oxidation of atenolol, cited in
`references.bib`. **Nothing from that work is reproduced here**: the numbers in `data/` are
demonstration values chosen to have a plausible shape, not measurements, and the captions say
so.

The molecule is real and was not typed by hand: `data/atenolol.smi` came from

```bash
labharness resolve "2-[4-[2-hydroxy-3-(propan-2-ylamino)propoxy]phenyl]acetamide" -o data/atenolol.smi
```

and RDKit confirms the formula, C14H22N2O3.
