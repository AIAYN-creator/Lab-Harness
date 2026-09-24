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
| 3 | A dependency is missing: an extra, or a system tool such as LaTeX or Java |

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
| `--journal` | `acs` | The template: `acs` (achemso), `elsevier` (elsarticle), `rsc-draft`, `article` (a short lab report) or `report` (a long report or a thesis chapter) |
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

### `labharness accept`

```
labharness accept FILE...
```

Raw data in `data/` is fingerprinted in `labharness.lock`. A new file is registered on the next
build without fuss. A registered file that changes or disappears is reported in red on **every**
build until you accept it:

```
  data/kinetics.csv changed since it was accepted (12 lines -> 11 lines)
      If the change is intended: labharness accept <file>
```

The figures are rebuilt with the new data all the same: a correction must be possible. What it
must not be is silent. `accept` records the file, who accepted it, when, and the fingerprint it
replaced, in the history at the end of `labharness.lock`. Keep that file in version control.

Spreadsheet lock files (`~$...`) and hidden files are not data and are ignored.

### `labharness hook`

```
labharness hook install [--force]
```

Installs a git pre-commit hook that refuses a commit changing or deleting a data file whose
change was not accepted. New files always pass. After `labharness accept`, stage `labharness.lock`
with the data and the commit goes through. `init` installs it on its own when the workspace is
inside a git repository; it never replaces a hook it did not write. `git commit --no-verify`
skips it once.

### `labharness eject`

```
labharness eject TARGET [--force]
```

Copies the workspace into `TARGET` so that its figures regenerate **without LabHarness
installed**: for a reviewer, for whoever inherits the project, or for you in five years. The
original workspace is not touched.

- Each Python script imports `_labharness`, a local copy of only the modules it uses, with the
  journal style frozen as it was. The scripts stay as short as they were.
- Each diagram becomes a complete standalone LaTeX document that compiles with plain pdflatex.
- Data, manuscript, bibliography and the figures already built are copied as they are.

There is no `un-eject` and no updates: the copy is frozen on purpose. Keep working in the
original.

The copy rebuilds with `python build.py` (or `compile.sh` / `compile.ps1`), which runs the
scripts in order, compiles the diagrams and the paper with pdflatex and BibTeX. `requirements.txt`
pins the exact versions of the packages that drew the figures, and `EJECTED.md` explains all of it
to whoever opens the folder.

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

Checks Python and the installed extras, the LaTeX distribution and BibTeX, the Latin
Modern fonts, Java when the `iupac` extra is installed, and your PDF viewer — warning you if the
default viewer is Adobe Acrobat, which locks the file — and the tool `preview` uses to turn PDFs
into images. `latexmk` is reported but optional. Exits non-zero if something required is
missing. Run it first whenever something does not work.

Every problem comes with the command that fixes it **on your system**: `winget` on Windows,
Homebrew on macOS, and `apt`, `dnf` or `pacman` on Linux, and for a missing extra the command
that matches how you installed LabHarness (`uv tool`, `pipx`, `pip`, or a clone of the
repository). `doctor` never installs anything itself.

### Templates

| `--journal` | Class | Figures drawn at |
|---|---|---|
| `acs` | achemso | 3.25 in (one column), 7 in (two) |
| `elsevier` | elsarticle | 90 mm (one column), 190 mm (full width) |
| `rsc-draft` | article, two columns | 8.3 cm (one column), 17.1 cm (two) |
| `article` | article, A4, 2.5 cm and 3.25 cm margins | 14.5 cm, the text width |
| `report` | report, same page | 14.5 cm, the text width |

**`rsc-draft` is not the official RSC template.** That one has no free licence, so it cannot be
copied into workspaces. Write and review in `rsc-draft`, then paste the body into the official
template to submit: the figures are already at RSC's widths and go in unchanged.

`article` and `report` map a Unicode minus sign, as pasted from a spreadsheet, to a hyphen, so
it does not stop pdfLaTeX.

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

Optional keys go at the top of the file:

| Key | Default | Meaning |
|---|---|---|
| `journal` | `"acs"` | The journal the workspace was created for; `init` writes it |
| `font` | the journal's | The typeface, from the catalogue in *Typefaces* below |
| `engine` | `"pdflatex"` | The LaTeX engine: `"pdflatex"`, `"xelatex"` or `"lualatex"`. Every typeface LabHarness offers works with pdflatex, the fastest; the other two are for `fontspec` and packages that only exist for them. They take about twice as long per rebuild, and the very first build with them builds a font cache, which can take a minute |
| `builder` | `"labharness"` | How the document is compiled. `"labharness"`: pdflatex, BibTeX or Biber only when citations or the bibliography changed, and more passes only when LaTeX asks. `"latexmk"`: hand it to latexmk instead, which needs Perl |

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
A structure is drawn **as large as the layout allows**, with no blank canvas around it. The room
it gets is the journal's column width, which in a single-column document (an article or a report)
is the text width, or `width_in=` for a figure that spans more (`width_in=7.0` for a
double-column ACS figure); it is never taller than that width. Within that room the molecule grows
until it fills it, with bonds up to 1.3 times the journal's so a small molecule does not turn into
a poster (`max_bond_scale` in the style). A molecule too large for the room shrinks to fit, and the
build prints a warning saying by how much, because its bonds are then shorter than the journal
asks for.

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

## Tables

A table is **whatever table you have**: a CSV exported from an instrument, a spreadsheet, a
database. LabHarness reads it with every cell as text and writes it in LaTeX **exactly as it
is**: same columns, same headers, same decimals. There is no template and no expected column.
Anything else is an operation you ask for, one line each, and the script reads as the list of
what was done to the table:

```python
# tables/optimisation.tex -- optimisation of the reaction conditions
from labharness.modules.tables import read_table, write_table

table = read_table("data/optimisation.csv")  # as it is
table = table.with_uncertainty("ee (%)", "ee_err")  # value ± error, rounded together
table = table.round(significant=2, columns=["conversion (%)"])
table = table.footnotes("note").rule_between("catalyst")
write_table(table, "tables/optimisation.tex")
```

```latex
\begin{table}
  \caption{Optimisation of the reaction conditions.}
  \label{tab:optimisation}
  \labtable{tables/optimisation.tex}
\end{table}
```

| Operation | What it does |
|---|---|
| `round(significant=n)` / `round(decimals=n)` | Rounds numbers, only in `columns=` if given. Decimal arithmetic on the number as written (2.675 → 2.68), trailing zeros kept (0.0996 → 0.10), and 1234 to two figures written 1.2e3 rather than a misleading 1200. `rule="half-up"` (default) or `"half-even"` (ISO 80000-1) |
| `with_uncertainty(value, error, significant=1)` | Shows value ± error: the error to `significant` figures, the value to the same decimal place |
| `select(...)`, `drop(...)`, `rename({...})` | Chooses, orders and renames columns |
| `footnotes(column)` | Turns a column of notes into table footnotes; the same text shares a letter |
| `rule_between(column)` | A rule wherever that column changes, to separate groups |

Numbers go in siunitx columns aligned on the decimal mark; a decimal comma is read as a decimal;
text is escaped and `$...$` is kept as maths; an empty cell is a dash. The original table is never
modified: every operation returns a new one. Formats other than delimited text are exported to CSV
first.

## Data formats

**Good practice: export to a format that cannot be misread.** Tables go into `data/` as CSV,
which every instrument and database can export, however old. Spectra, chromatograms or anything
that is only an image of the data go in as PNG or PDF, and are placed in the manuscript as they
are. Proprietary instrument files are kept elsewhere, as the raw record; LabHarness reads what
was exported from them.

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

### Typefaces

One typeface per document, chosen from a tested catalogue. Add `font = "..."` at the top of
`labharness.toml` to change it; the document style and every figure follow on the next build.
Sizes stay the journal's.

| `font` | Typeface | Maths |
|---|---|---|
| `latin-modern` *(default)* | Latin Modern, the LaTeX default | Computer Modern |
| `termes` | TeX Gyre Termes, in the style of Times | newtxmath |
| `pagella` | TeX Gyre Pagella, in the style of Palatino | newpxmath |
| `stix` | STIX Two, designed for scientific publishing | STIX Two Math |
| `libertinus` | Libertinus Serif | Libertinus Math |

All five run on pdflatex and ship with TeX Live and MiKTeX. If a font file is missing, the error
names the package to install. Headings or addresses that a journal class sets in sans-serif or
monospace stay in Latin Modern Sans and Mono, so nothing falls back to bitmap fonts.

The catalogue is closed on purpose: every entry has maths designed to match and is checked to
leave no other font in the PDF. A font outside it can still be used by writing your own
`labharness-style.tex` without the first "generated" line, which LabHarness then leaves alone.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| With `builder = "latexmk"`, latexmk fails saying the script engine `perl` was not found | MiKTeX on Windows has no Perl. Install Strawberry Perl, or remove the line: LabHarness compiles without latexmk |
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
