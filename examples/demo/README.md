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

## Raw data is protected

`data/` is the part of a paper that must never change by accident, and the demo shows the three
layers that guard it:

| Try this | What happens |
|---|---|
| Change a value in `data/decay.csv` and save | The figure follows, and the build says in red that `data/decay.csv` changed since it was accepted, on every rebuild, until you run `labharness accept data/decay.csv` |
| Ask an AI agent (Claude Code) to "fix" a value in `data/` | It cannot: `.claude/settings.json` denies it any write to `data/`, and denies it `labharness accept` too. `AGENTS.md` gives every other agent the same rule |
| Commit a changed data file without accepting it | The git hook installed by `labharness hook install` refuses the commit |

The first time you change a data point in a rehearsal, the red line is the point: the tool noticed
that raw data was touched.

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
