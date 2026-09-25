# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The lab compound library (the `library` extra): an inventory exported to CSV or `.xlsx`,
  named by `[library]` in the manifest. `resolve` looks in it first, by name, code or alias,
  `render_structure(compound=..., library=...)` draws from it, and `labharness library check`
  reviews it: unreadable SMILES, unspecified stereochemistry and formulas that do not match.
- The `excel` extra: tables and plots read `.xlsx` workbooks through the same reader as CSV,
  with `sheet=` and `cells=`, each cell as Excel shows it and formulas by their saved value.
  An ejected workspace that reads one pins openpyxl in `requirements.txt`.
- A GIF at the top of the README, from a CSV to a figure in the PDF and a changed measurement
  that moves its point and the number in the text. `tools/make_readme_gif.py` makes it by
  running every step for real.
- Plot axis labels can come from the column header: `t (min)`, `t [min]` or `t / min`. A
  header without a unit is refused rather than drawn without one.
- `[[table]]` entries in the manifest: the watcher rebuilds a table when its data changes, like
  a figure.
- `labharness init --font NAME` chooses the typeface when the workspace is created.
- A gallery, `docs/gallery/`, of pages LabHarness built: the demo and the first page of every
  template, regenerated with `tools/make_gallery.py`. The demo gains a second scheme, the
  acid-catalysed iodination of acetone.
- `labharness add <kind> <name>`: writes a figure script from a template and declares it in the
  manifest; `--insert` also places the figure block in `paper.tex`.
- `labharness preview`: renders figures, and with `--document` the pages of the PDF, as PNG images
  to review them by eye. `doctor` reports the tool it uses.
- `engine` in the manifest: `pdflatex` (default), `xelatex` or `lualatex`, used for the
  document and for every diagram.
- A catalogue of five typefaces (Latin Modern, TeX Gyre Termes, TeX Gyre Pagella, STIX Two,
  Libertinus), chosen with `font = "..."` in the manifest. The document style, plots, structures
  and diagrams all follow, and `labharness-style.tex` is regenerated when the choice changes.
- `labharness.lock` and `labharness accept`: every file in `data/` is fingerprinted, and a change
  to a registered file is reported on every build until a person accepts it, with who, when and
  what it replaced recorded. The build still runs.
- A git pre-commit hook, installed by `init` in a git repository or with `labharness hook
  install`, refuses to commit a change to raw data that was not accepted.
- `python -m labharness` runs the command line.
- `labharness eject TARGET`: a copy of the workspace whose scripts import a local, frozen
  `_labharness` with only the modules they use, and whose diagrams are standalone documents, so
  the figures regenerate without LabHarness installed. It writes `build.py`, pinned
  `requirements.txt` and an `EJECTED.md` explaining how to rebuild.

- `tables` module: `read_table` reads any delimited table, every cell as text, in UTF-8,
  UTF-16 or the Windows encodings old instruments write; `write_table` writes it in LaTeX exactly
  as it is, with booktabs rules and siunitx columns; and explicit operations change it on
  request: correct rounding to significant figures or decimals, value ± uncertainty, footnotes,
  groups, column choice. `\labtable` includes it in the manuscript.
- Templates for Elsevier (`elsarticle`), an RSC working layout (`rsc-draft`, not the official
  template), and a short `article` and a long `report` for lab work on A4:
  `labharness init --journal elsevier`.

### Changed

- A cell that is not a number stops a plot with its file, line and column (`'decay.csv', line 6,
  column 'c': 'n.d.' is not a number`), and the watcher prints that message alone instead of a
  traceback, then keeps watching. A traceback is still shown when a script itself is broken.
- macOS is a tier-1 platform: its CI job is part of `ci-pass`. `doctor` asks for `luatex85`
  when a workspace compiles with LuaLaTeX and the distribution lacks it, as BasicTeX does.
- **Perl is no longer needed.** LabHarness runs the full LaTeX build itself: pdflatex, BibTeX or
  Biber only when the citations or the bibliography changed, and more passes only when LaTeX asks.
  A change to the manuscript text now compiles in about 0.9 s instead of 4.1 s. latexmk stays
  available with `builder = "latexmk"` in the manifest, and `doctor` reports it as optional.
- New workspaces ship `.claude/settings.json`, which stops Claude Code from writing anything in
  `data/`, editing `labharness.lock` or running `labharness accept`, and their `AGENTS.md` states
  the same rule for every other agent.
- `doctor` prints the exact command that installs what is missing on the system it runs on, and
  for a missing extra the command that matches how LabHarness was installed, instead of
  `uv sync`, which only works in a clone of the repository.

- The agent rules are split: `AGENTS.md` holds the rules for every field and
  `AGENTS.chemistry.md` those only chemistry needs; `CLAUDE.md` imports both.
- A journal is now one folder under `templates/workspace/journals/`, holding its style, manuscript
  and bibliography. `init` records the journal in the manifest and generates
  `labharness-style.tex` from the style.

### Fixed

- A fitted value and its uncertainty could keep a digit too many when rounding carried (1.2345 ± 0.0996
  was written 1.234 ± 0.100, not 1.23 ± 0.10), and every digit of an uncertainty above the units
  (12346 ± 1234, not 12300 ± 1200); tables had the second problem too. Fits and tables now share one
  decimal rounding.
- `labharness add --insert` put the figure block between `\bibliographystyle` and
  `\bibliography` in the templates that have both. It now goes before them.
- The figure block `add` writes had no placement, so a figure added after the text of a page
  always moved to the next one. It is now `[htbp]`, as in the templates.
- Chemical structures were drawn on a fixed 4:3 canvas, leaving blank space around a long
  molecule. They are now cropped to the molecule and drawn as large as the layout allows: the
  column width, or the text width of a single-column document, with bonds up to 1.3 times the
  journal's. One that does not fit shrinks, with a warning.
- Warnings from figure modules (a structure that does not fit, error bars inferred from the
  decimals) never reached the terminal when the watcher ran the script. They are now printed
  under the figure on every rebuild.
- In a CSV separated by semicolons, a plot read `1.5` as fifteen, taking the point for a
  thousands separator. Plots and tables now share one reader: a point or a comma is always the
  decimal mark, it reads UTF-16 and the Windows encoding, skips metadata above the header with a
  warning, and stops at a summary row at the end instead of misreading it.

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
