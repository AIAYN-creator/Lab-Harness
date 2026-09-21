# LabHarness

Turn raw lab data into publication-ready LaTeX figures, and keep the PDF in sync while you work.

> **Status: alpha, v0.1.0.** Everything below runs today except what is marked
> **[not implemented yet]**, which is specification: it describes what is being built
> (README-driven development), not what runs.

LabHarness is a local-first, open-source (MIT) harness for scientific writing and lab-data
automation — *Data-to-Paper*. Change a data point or a SMILES string, save, and the figure and the
PDF update on their own. The pipeline is always short, readable Python you can open and edit,
never a black box.

## How fast is it

From saving a file to seeing the PDF, measured on the author's laptop (Windows 11, MiKTeX)
with the watcher running, on a document using the ACS template:

| You change | Figure | LaTeX | **Total** |
|---|---|---|---|
| A measurement in a CSV | 0.20 s | 1.1 s | **1.3 s** |
| A SMILES string | 0.05 s | 1.05 s | **1.1 s** |
| A reaction mechanism | 3.1 s | 1.0 s | **4.1 s** |
| The text of the manuscript | — | 4.1 s | **4.1 s** |

Two things make that possible. Figure scripts run inside the watcher process, so a rebuild
never pays again for starting Python and importing RDKit or Matplotlib: the same figure takes
1.8 s from a cold start and 0.2 s once the watcher is up. And when only a figure changed,
LaTeX needs a single pass, which is what it gets — latexmk costs about a second before it runs
anything, so it is kept for the cases that need it, such as a changed bibliography.

What is left is LaTeX itself, and mechanisms drawn with chemfig, which are slow to compile.

## Who it is for

Researchers, PhD students and science students who already write in LaTeX or Overleaf and are
comfortable with a terminal and an editor such as VS Code or Zed.

## How it works

```
 data/                     scripts/                  figures/            paper.pdf
 raw measurements   ---->  transparent scripts ----> vector figures ---> your manuscript
 .csv .smi .mol            .py and .tex              .pdf

              labharness.toml says which script uses which data
              labharness watch reacts to every save and rebuilds only what changed
```

## Principles

- **Local-first.** Everything runs on your machine; nothing needs the network by default.
- **Human-in-the-loop.** Figures come from scripts you can read, tweak or take over entirely.
- **Zero layout friction.** One typeface for the whole document, figures included, generated at
  their final printed size so nothing is ever rescaled.
- **Save and see.** No manual regeneration step.
- **Modular.** Install only the domains you use.

## Requirements

| What | Why | Notes |
|---|---|---|
| Python ≥ 3.11 | The harness | Developed on 3.12 |
| [uv](https://docs.astral.sh/uv/) | Environment and lockfile | `pip install .` also works |
| A LaTeX distribution | Compiling the document and the diagrams | MiKTeX or TeX Live/MacTeX |
| Perl | `latexmk` needs it | Ships with TeX Live; on Windows with MiKTeX install Strawberry Perl |
| A PDF viewer that does not lock files | Live reload | SumatraPDF (Windows), Skim (macOS). **Adobe Acrobat will not work**: it locks the PDF |
| Java *(optional)* | IUPAC name resolution with OPSIN | Only for the `iupac` extra |

## Install

### 1. The requirements

<details>
<summary>Windows</summary>

```powershell
winget install astral-sh.uv
winget install StrawberryPerl.StrawberryPerl   # latexmk needs Perl; skip it if you use TeX Live
winget install SumatraPDF.SumatraPDF
winget install MiKTeX.MiKTeX                   # or TeX Live
winget install EclipseAdoptium.Temurin.21.JDK  # optional, only for the iupac extra
```

</details>

<details>
<summary>macOS</summary>

```bash
brew install uv
brew install --cask mactex          # or basictex for a smaller install
brew install --cask skim
brew install --cask temurin         # optional, only for the iupac extra
```

</details>

<details>
<summary>Linux</summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt install texlive-full       # or a smaller scheme plus achemso, chemfig and standalone
sudo apt install default-jre        # optional, only for the iupac extra
```

Any PDF viewer that reloads on change works: Okular and Zathura both do.

</details>

### 2. LabHarness

```bash
git clone https://github.com/AIAYN-creator/Lab-Harness.git
cd Lab-Harness
uv sync --all-extras
uv run labharness doctor
```

`labharness doctor` checks the requirements above and tells you exactly what is missing and
how to install it.

Install only what you need:

| Extra | Brings | For |
|---|---|---|
| *(core)* | CLI, watcher, style, TikZ diagrams | Always |
| `chem` | RDKit, SVG to PDF conversion | Chemical structures |
| `plots` | NumPy, SciPy, Matplotlib | Regressions and plots |
| `iupac` | OPSIN (needs Java) | Names to SMILES |
| `all` | Everything above | — |

## Quickstart

```bash
labharness init my-paper --journal acs
cd my-paper
labharness add structure catalyst --input data/catalyst.smi   # [not implemented yet]
labharness watch
```

Now open `data/catalyst.smi`, change the SMILES string and save. The structure is redrawn and the
PDF reloads in your viewer, with the timings printed in the terminal.

## Commands

`add` is still specification; the rest work today.

| Command | What it does |
|---|---|
| `labharness init [PATH] [--journal acs]` | Create a workspace from the template |
| `labharness add <kind> <name> [--input FILE...]` | Add a figure: writes the script and the manifest entry **[not implemented yet]** |
| `labharness build [--only NAME] [--no-latex]` | Rebuild figures and compile the PDF once |
| `labharness watch [--no-open] [--debounce MS]` | Watch, rebuild and recompile on every save |
| `labharness resolve NAME -o FILE` | IUPAC name to SMILES, offline |
| `labharness doctor` | Check the environment and report what is missing |

**[Full command reference, options and file formats: `docs/usage.md`](docs/usage.md)**

## The workspace

```
my-paper/
├── paper.tex              # Your manuscript (ACS template in v0.1)
├── labharness-style.tex   # Typography and figure helpers: the only place fonts are set
├── labharness.toml        # Manifest: which script builds which figure, from which data
├── data/                  # Raw measurements. Never modified by the tool
├── figures/               # Generated vector PDFs. Never edited by hand
├── scripts/               # Transparent scripts, one per figure
├── references.bib
├── AGENTS.md  CLAUDE.md   # Rules for AI agents working in this workspace
└── compile.sh  compile.ps1
```

A script is short enough to read at a glance:

```python
# figures/catalyst.pdf -- structure of the catalyst
from labharness.modules.chem import render_structure

render_structure(smiles_file="data/catalyst.smi", output="figures/catalyst.pdf")
```

And the manifest says what depends on what:

```toml
[[figure]]
output = "figures/catalyst.pdf"
script = "scripts/catalyst.py"
inputs = ["data/catalyst.smi"]
```

## Typography

One typeface for the entire document — text, axis labels, atom labels, mechanisms — defined once
in `labharness-style.tex`. v0.1 uses the LaTeX default (Computer Modern / Latin Modern). Figures
are generated at their final printed size and included without scaling, so 8 pt in a figure is
8 pt on paper.

## In v0.1

**Included:** chemical structures (RDKit), reaction mechanisms and diagrams (TikZ/chemfig),
regressions and plots with error bars (SciPy/Matplotlib), the watcher, the ACS template and
IUPAC name resolution.

**Not included:** any graphical interface, editorial LaTeX tables, journals other than ACS, and
publishing to PyPI.

## Roadmap

| Version | Focus |
|---|---|
| **v0.1** | Demo-ready MVP |
| **v0.5** | Daily use: editorial tables, real agent rules, lab compound libraries |
| **v1.0** | Public release: more journal templates, selectable typeface |
| **v1.5+** | New domains: economics, mathematics, architecture and engineering |
| **v2.0** | A graphical interface for people who do not use a terminal |

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the detail.

## Contributing

External contributions open with v1.0. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). If you want to work on LabHarness itself, start with
[`docs/onboarding.md`](docs/onboarding.md); the decisions behind the design are in
[`docs/adr/`](docs/adr/).

## License

[MIT](LICENSE) © 2026 AIAYN-creator
