# LabHarness usage

Complete reference for the v0.1 command line, file formats and troubleshooting.

> **Alpha, v0.1.0.** Every command below works today. Anything marked **[not implemented yet]**
> is specification (README-driven development).

- [Concepts](#concepts)
- [Global options](#global-options)
- [Commands](#commands)
- [The manifest](#the-manifest)
- [Figure kinds](#figure-kinds)
- [Data formats](#data-formats)
- [Style and typography](#style-and-typography)
- [Troubleshooting](#troubleshooting)

## Concepts

A **workspace** is a folder with a `labharness.toml` in it: your manuscript, your raw data, your
scripts and the figures they produce. Commands can be run from anywhere inside it — LabHarness
walks up the folder tree looking for `labharness.toml`, the way git looks for `.git`.

A **figure** is one entry in the manifest: an output PDF, the script that builds it, and the input
files it depends on. A **module** is the Python function a script calls: `chem` for structures,
`diagrams` for TikZ and mechanisms, `plots` for regressions.

## Global options

| Option | Effect |
|---|---|
| `--help` | Help for any command |
| `--version` | Print the LabHarness version |
| `--verbose` | Show every command run and every file touched |
| `--quiet` | Only errors |

Output is coloured when the terminal supports it; `NO_COLOR` is honoured.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime error: LaTeX failed, a fit did not converge, an input file is invalid |
| 2 | Usage error: unknown command or bad options |
| 3 | A dependency is missing: an extra, or a system tool such as LaTeX, Perl or Java |

Every error says what failed, why, and how to fix it.

## Commands

### `labharness init`

```
labharness init [PATH] [--journal acs] [--force]
```

Creates a workspace from the template: `paper.tex`, `labharness-style.tex`, `references.bib`,
`labharness.toml`, `data/`, `figures/`, `scripts/`, `AGENTS.md`, `CLAUDE.md`, `compile.sh`,
`compile.ps1` and a `.gitignore` for LaTeX artefacts.

| Option | Default | Meaning |
|---|---|---|
| `PATH` | `.` | Where to create the workspace |
| `--journal` | `acs` | Journal template. v0.1 ships ACS only |
| `--force` | off | Write into a folder that is not empty |

### `labharness add`

```
labharness add <kind> <name> [--input FILE...] [--insert] [--edit] [--force]
```

Writes `scripts/<name>.py` (or `.tex` for diagrams) from a commented template **and** adds the
matching `[[figure]]` entry to the manifest, so the watcher picks it up immediately. It then
prints the LaTeX block that places the figure in the manuscript, or adds it with `--insert`.

| Argument | Meaning |
|---|---|
| `kind` | `structure`, `plot`, `mechanism`, `flow` or `network` |
| `name` | Used for the script and for `figures/<name>.pdf`: letters, digits, `-` and `_` |
| `--input` | Input files the figure depends on. Repeatable. A `structure` without one reads `data/<name>.smi`; a `plot` fills in its column names from the CSV header |
| `--insert` | Also add the figure block to `paper.tex`, just before the bibliography |
| `--edit` | Open the new script in `$VISUAL`, `$EDITOR` or VS Code |
| `--force` | Replace a script that already exists (the manifest entry is not duplicated) |

`add` never writes into `data/`: if an input does not exist yet, it says so, and the figure builds
as soon as the file appears. An existing script is never replaced without `--force`.

### `labharness build`

```
labharness build [--only NAME] [--no-latex]
```

Rebuilds figures and compiles the PDF once, printing the time each phase took. Useful in CI, and
before a live demo so LaTeX installs anything it is missing ahead of time.

| Option | Meaning |
|---|---|
| `--only NAME` | Rebuild a single figure |
| `--no-latex` | Rebuild figures but do not compile the document |

### `labharness watch`

```
labharness watch [--no-open] [--debounce MS]
```

The main loop. Watches `data/`, `scripts/`, `paper.tex`, the manifest and the style file. On every
save it rebuilds only the affected figures and recompiles the document, then prints the latency of
each phase. It opens the PDF in your viewer on start (SumatraPDF on Windows, Skim on macOS).

| Option | Default | Meaning |
|---|---|---|
| `--no-open` | off | Do not open the PDF viewer on start |
| `--debounce` | 100 ms | Wait this long to group rapid saves. Raise it if your editor saves in two steps |

If LaTeX fails, the error is summarised, the last good PDF stays on screen, and the watcher keeps
running: fix the file, save, and it recovers.

### `labharness preview`

```
labharness preview [--only NAME] [--document] [--dpi 200]
```

Renders each figure as a PNG in `.labharness/preview/`, and with `--document` every page of the
compiled `paper.pdf` as well, so you can see the figures where they sit. The folder is ignored by
git.

A test can tell that a figure was built, not that it reads well: a label in the wrong place, a
group that reads as a radical, a figure with half its area blank. The images are for looking at,
by you or by an agent that can open images; the workspace `AGENTS.md` asks agents to do it before
calling a figure done.

| Option | Default | Meaning |
|---|---|---|
| `--only NAME` | all | Preview a single figure |
| `--document` | off | Also render the pages of `paper.pdf` |
| `--dpi` | 200 | Resolution of the images |

Uses `pdftoppm` (included in MiKTeX; `poppler-utils` on Debian and Ubuntu, `poppler` in Homebrew)
or, failing that, Ghostscript. `labharness doctor` says which one it found.

### `labharness resolve`

```
labharness resolve "NAME" -o FILE
```

Turns a systematic IUPAC name into a SMILES string with OPSIN, offline, and writes it to `FILE`
with the original name kept as a comment. Needs the `iupac` extra and Java.

Resolution is a separate step on purpose: the SMILES lands in a file you can check before it
becomes a figure, and the watcher never pays the cost of starting a JVM.

Reserved for later versions: `--library FILE.csv` (your lab's compound inventory, v0.5) and
`--online` (PubChem, v1.5).

### `labharness doctor`

```
labharness doctor
```

Checks Python and the installed extras, the LaTeX distribution, `latexmk` and Perl, the Latin
Modern fonts, Java when the `iupac` extra is installed, and your PDF viewer — warning you if the
default viewer is Adobe Acrobat, which locks the file — and the tool `preview` uses to turn PDFs
into images. Exits non-zero if something required is
missing. Run it first whenever something does not work.

## The manifest

`labharness.toml`, at the root of the workspace. One entry per figure:

```toml
[[figure]]
output = "figures/catalyst.pdf"
script = "scripts/catalyst.py"
inputs = ["data/catalyst.smi"]

[[figure]]
output = "figures/kinetics.pdf"
script = "scripts/kinetics.py"
inputs = ["data/kinetics_25C.csv", "data/kinetics_40C.csv"]

[[figure]]
output = "figures/mechanism.pdf"
script = "scripts/mechanism.tex"
```

Editing the manifest or the style file rebuilds every figure. `labharness add` keeps the file up to
date for you, but it is plain text you can edit by hand.

## Figure kinds

Each kind is a short script that calls one helper. The watcher runs Python scripts in its own
process and compiles `.tex` diagrams on their own, so a rebuild costs milliseconds.

### `structure` — chemical structures

```python
# figures/catalyst.pdf -- structure of the catalyst
from labharness.modules.chem import render_structure

render_structure(smiles_file="data/catalyst.smi", output="figures/catalyst.pdf")
```

Drawn with RDKit using the journal's geometry (bond length, line widths) and the document typeface.

### `mechanism` and `flow` — diagrams

A commented standalone LaTeX file in `scripts/`, compiled to a PDF in `figures/`. Mechanisms use
chemfig with arrow pushing; flowcharts and frameworks use plain TikZ nodes and paths. RDKit is
never used for mechanisms: it cannot draw electron-pushing arrows reliably.

### `plot` — regressions and plots

```python
# figures/calibration.pdf -- calibration curve, triplicates
from labharness.modules.plots import Series, regression_plot

regression_plot(
    output="figures/calibration.pdf",
    series=[Series(csv="data/calibration.csv", x="conc", y=["abs_1", "abs_2", "abs_3"])],
    model="linear",
    x_label=("Concentration", "mM"),
    y_label=("Absorbance", None),
)
```

Models: `linear`, `polynomial`, `log`, `exp`, `power`, or your own function (Arrhenius, Eyring,
Michaelis-Menten…). Axis labels are mandatory: a plot without them fails loudly instead of
producing an unlabelled figure.

Fitted parameters, their uncertainties and R² are written next to the figure as LaTeX macros
(`figures/calibration.fit.tex`). Load them with `\labresults{figures/calibration.fit.tex}` and cite
a fitted value in your text: it updates when the data does.

## Data formats

### CSV

Files with a header row. Columns are chosen by name in the script. CSV exported by Excel in
languages that use `;` as the separator and `,` as the decimal mark is detected automatically.

### Error bars, in priority order

1. **An explicit error column** in the CSV, e.g. `abs_sd`.
2. **Replicates** — either several columns (`abs_1`, `abs_2`, `abs_3`) or repeated rows with the
   same x — giving mean ± sample standard deviation. Fewer than three replicates gets a warning.
3. **Instrument resolution**, inferred from the number of decimals written in the file
   (`0.123` → ± 0.001). Files are read as text so trailing zeros are not lost; set `resolution=`
   in the script if your export trimmed them.

Fits are weighted whenever real uncertainties are available. Errors in x are not handled in v0.1.

### SMILES

`.smi` files with one SMILES string, optionally with the source name as a comment. Write them by
hand or with `labharness resolve`.

## Style and typography

The journal style file defines, in one place: the typeface, figure text sizes, column widths,
structure geometry and plot defaults. Modules never hard-code any of it, so switching journals is
switching style files.

| What | v0.1 |
|---|---|
| Typeface | The LaTeX default (Computer Modern / Latin Modern), for text and figures alike |
| Figure width | One ACS column, 3.25 in |
| Figure text | 8 pt at final size |
| Structures | ACS 1996 geometry: 14.4 pt bonds, 0.6 pt lines |
| Plots | No grid, Okabe-Ito colours, fit line drawn only over the data range |

Figures are generated at their final size and included without scaling.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `latexmk` fails saying the script engine `perl` was not found | MiKTeX on Windows has no Perl. Install Strawberry Perl |
| A package is reported missing although it is installed | The MiKTeX file database is stale: run `initexmf --update-fndb` |
| The PDF does not refresh, or LaTeX cannot write it | The viewer is locking the file. Use SumatraPDF or Skim, not Adobe Acrobat |
| Nothing rebuilds when you save | The file is not listed in any `inputs` in the manifest |
| A figure rebuilds twice per save | Your editor saves in two steps: raise `--debounce` |
| Decimal numbers read as text, or wrong error bars | Check the CSV separator and decimal mark, or set `resolution=` explicitly |

Still stuck? Run `labharness doctor` and include its output when you open an issue.

## Appendix: ACS journal codes

`paper.tex` selects the journal with the `journal=` option of the `achemso` class:

| Code | Journal |
|---|---|
| `jacsat` | Journal of the American Chemical Society |
| `joceah` | The Journal of Organic Chemistry |
| `orlef7` | Organic Letters |
| `accacs` | ACS Catalysis |

The achemso documentation lists every supported code.
