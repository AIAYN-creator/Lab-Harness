# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `labharness add <kind> <name>`: writes a figure script from a template and declares it in the
  manifest; `--insert` also places the figure block in `paper.tex`.
- `labharness preview`: renders figures, and with `--document` the pages of the PDF, as PNG images
  to review them by eye. `doctor` reports the tool it uses.
- `engine` in the manifest: `pdflatex` (default), `xelatex` or `lualatex`, used for the
  document and for every diagram.
- A catalogue of five typefaces (Latin Modern, TeX Gyre Termes, TeX Gyre Pagella, STIX Two,
  Libertinus), chosen with `font = "..."` in the manifest. The document style, plots, structures
  and diagrams all follow, and `labharness-style.tex` is regenerated when the choice changes.

### Changed

- **Perl is no longer needed.** LabHarness runs the full LaTeX build itself: pdflatex, BibTeX or
  Biber only when the citations or the bibliography changed, and more passes only when LaTeX asks.
  A change to the manuscript text now compiles in about 0.9 s instead of 4.1 s. latexmk stays
  available with `builder = "latexmk"` in the manifest, and `doctor` reports it as optional.
- A journal is now one folder under `templates/workspace/journals/`, holding its style, manuscript
  and bibliography. `init` records the journal in the manifest and generates
  `labharness-style.tex` from the style.

### Fixed

- Python figure scripts always used the ACS style, whatever journal the workspace had.

## [0.1.0] - 2026-09-21

The demo-ready MVP: change a data point, a SMILES string or a mechanism, save, and the figure and
the PDF follow.

### Added

- `labharness init`: a workspace with manuscript, data, scripts, figures and a
  `labharness.toml` manifest saying which script builds which figure from which data.
- `labharness build` and `labharness watch`: an event-driven watcher that rebuilds only the
  figures affected by a save, runs Python figure scripts in its own process, takes a single
  pdflatex pass when only figures changed, and prints the time spent in each phase.
- `labharness resolve`: IUPAC name to SMILES, offline, with OPSIN (`iupac` extra, needs Java).
- `labharness doctor`: checks Python, the extras, LaTeX, latexmk and Perl, the fonts, Java and
  the PDF viewer, and says how to fix what is missing.
- `chem` module: chemical structures drawn by RDKit at their final size, with ACS 1996
  geometry.
- `diagrams` module: TikZ and chemfig mechanisms and diagrams compiled standalone, with curved
  electron-pushing arrows and three commented templates (mechanism, flow, network).
- `plots` module: linear, polynomial and exponential fits drawn with error bars taken from
  replicates, an error column or the instrument resolution, and fitted values written as LaTeX
  macros so the text quotes numbers that follow the data.
- Shared style as data: one file per journal translated for RDKit, LaTeX/TikZ and Matplotlib,
  with one typeface (Latin Modern) for the whole document.
- ACS manuscript template (achemso), including a fix for an empty bibliography.
- Modular installation: `chem`, `iupac`, `plots` and `all` extras over a core that imports
  without any of them.
- A demo workspace in `examples/demo` built around the electrochemical oxidation of atenolol.
- Instructions for AI agents, for the repository and for workspaces (`AGENTS.md` and a
  one-line `CLAUDE.md`).
- Continuous integration on Ubuntu (Python 3.11 to 3.13) and Windows, with LaTeX tests on
  TeX Live and MiKTeX behind a single required check, `ci-pass`.
- Governance: MIT license, contributing guide, code of conduct, security policy, issue and pull
  request templates, code owners and a versioned branch ruleset.

[Unreleased]: https://github.com/AIAYN-creator/Lab-Harness/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AIAYN-creator/Lab-Harness/releases/tag/v0.1.0
