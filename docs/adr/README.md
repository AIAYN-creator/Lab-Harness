# Architecture Decision Records

Why LabHarness is the way it is. Each entry states the decision and the reason it beat the
alternatives; the long-form records, with every option that was considered, live on the
maintainer's project board and are being written up here as they settle.

If a change contradicts one of these, raise it before working around it.

| # | Decision | Why |
|---|---|---|
| 1 | **v0.1 is a demo-ready MVP**, done when the live demo runs end to end on the maintainer's laptop. Regressions and plots are in; a graphical interface, editorial tables and other journals are out. | Plots are where the friction is: Excel, axis titles, units, redoing it whenever the data changes. |
| 2 | **Latency reference: 0.5 s** from saving a file to seeing the PDF update, measured per phase and reported, but not a release gate. | Ambitious on purpose. Figures already meet it; LaTeX does not, and pretending otherwise would hide the real bottleneck. |
| 3 | **Python, managed with uv**, supporting 3.11 to 3.13. | RDKit, SciPy and Matplotlib are Python, and the pipeline has to be readable by the researcher using it. |
| 4 | **A package plus short scripts in the workspace**, with an `eject` command planned for v0.5. | One tested implementation instead of copies that drift, while the scripts a user reads stay three lines long. |
| 5 | **Modular install: one extra per domain**, and a core that imports without any of them. | Somebody doing chemistry should not download the economics stack. |
| 6 | **Style is data**: one file per journal, translated for RDKit, LaTeX and Matplotlib. | Adding a journal must not mean touching modules. |
| 7 | **One typeface for the whole document** — the LaTeX default in v0.1 — and figures generated at their final printed size. | The point of the project: no layout friction, and no figure whose text is a different size from the text around it. |
| 8 | **Event-driven watcher in Python** that rebuilds only affected figures and calls latexmk, with a `labharness.toml` manifest saying which script uses which data. | `latexmk -pvc` watches neither the data nor the scripts, and polls on a timer. A manifest is also what a graphical interface will read. |
| 9 | **Scripts run inside the watcher process.** | A rebuild costs milliseconds instead of the second a fresh interpreter needs to import Matplotlib. Measured: 1826 ms cold, around 300 ms warm. |
| 10 | **Mechanisms and diagrams use TikZ and chemfig**, compiled standalone to PDF; never RDKit. | RDKit cannot draw electron-pushing arrows reliably, and compiling diagrams separately keeps the document fast. |
| 11 | **IUPAC names are resolved offline with OPSIN, as a separate step** that writes a SMILES file into `data/`. | Local-first, and a wrong name becomes a file you can check instead of a silently wrong structure. |
| 12 | **Errors on plotted points come from replicates when they exist**, then an explicit error column, then the instrument resolution inferred from the decimals in the file. | It matches how lab data actually arrives, and never invents an uncertainty. |
| 13 | **pytest, ruff and mypy, with a single required CI check named `ci-pass`.** | The branch ruleset references one stable name, so the test matrix can change freely. |
| 14 | **No third-party GitHub Actions.** | The repository policy blocks them, so the CI installs what it needs itself. |
| 15 | **Conventional Commits, squash merges, and a protected `main` with an administrator bypass.** | A readable history, and review for everyone who is not the maintainer. |
| 16 | **Agent instructions live in `AGENTS.md`, with a one-line `CLAUDE.md` importing it.** | Whatever agent someone uses, the rules are the same ones. |

## Decided for v0.5 and v1.0

| # | Decision | Why |
|---|---|---|
| 17 | **A journal is one folder** (`style.toml`, `paper.tex`, bibliography), and figure scripts draw for the journal of their workspace without naming it. | Adding a journal must never mean touching a module; a test fails if any module spells one out. |
| 18 | **Editorial tables follow the figure pattern**: a CSV or a fit, a short script, a generated `tabular` with booktabs and siunitx, and a `\labtable` in the manuscript. Uncertainties are written with ±, units go in the header, and significant figures come from the data, never from the tool. An enantiomeric excess can be a percentage or a fraction, as the CSV gives it. | Tables are where asymmetric catalysis reports its results, and a number retyped by hand is a number that drifts from the data. |
| 19 | **`data/` is protected in three independent layers**: checksums in `labharness.lock` that flag any change to a registered file until `labharness accept` (the build still runs), a deny rule that stops agents writing to `data/` or running `accept`, and a git hook that refuses unaccepted changes. New files are always welcome. | A raw data point changed without trace can invalidate a paper; corrections still have to be possible, visibly. |
| 20 | **`labharness eject`** copies a workspace into a folder that regenerates without LabHarness: each script imports a local `_labharness/` holding only the modules it uses, with the style frozen as constants, plus `build.py` and pinned requirements. | A paper must outlive the tool that built it, and ejected scripts should stay as short as the originals. |
| 21 | **The lab compound library is an optional extra.** Without one, nothing changes; with one, `resolve` looks it up before OPSIN. | Every lab already keeps a compound inventory, and none should need one to use LabHarness. |
| 22 | **Journals for v1.0: ACS, Elsevier (`elsarticle`) and RSC as a working format.** RSC's official template has no free licence, so LabHarness ships its own layout with RSC widths and the free `rsc` bibliography style, and says the official template is for submission. Wiley is out of v1.0. | Only freely licensed classes can be copied into every workspace. |
| 23 | **A closed catalogue of five typefaces** (Latin Modern, TeX Gyre Termes, TeX Gyre Pagella, STIX Two, Libertinus), chosen at `init`. Latin Modern stays the default in every journal. All five run on pdflatex, and the LaTeX engine becomes configurable for anything outside the catalogue. | Each entry is tested across text, maths, plots and structures, which an arbitrary font cannot promise. |
| 24 | **Distribution on PyPI as `labharness`**, published from a tag with trusted publishing and no stored token; installed with `uv tool install "labharness[all]"`. Windows and Linux are tier 1, macOS tier 2 until its CI job is green. | One command to install is what the v1.0 exit criterion asks for. |
| 25 | **No Perl.** LabHarness runs the full LaTeX build itself (pdflatex, then BibTeX when needed, then pdflatex until references settle) and uses latexmk only if it is installed. | Perl was the least expected requirement on Windows; without it, a Windows install is uv and MiKTeX. |
| 26 | **Governance for external contributors**: the versioned ruleset is the source of truth and the live one is re-imported from it; the administrator bypass stays in `always` mode; release tags `v*` get their own ruleset; Dependabot security alerts, secret scanning and private vulnerability reporting are on; signed commits are not required. | CI runs on every push anyway, and the maintainer does not need more friction than that. |
