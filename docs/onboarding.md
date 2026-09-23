# Onboarding

How LabHarness is built, and how to work on it. If you only want to *use* it, read the
[README](../README.md) and [usage.md](usage.md) instead.

- [Set up your machine](#set-up-your-machine)
- [A tour of the repository](#a-tour-of-the-repository)
- [The module contract](#the-module-contract)
- [Adding a module](#adding-a-module)
- [Adding a journal](#adding-a-journal)
- [Running the checks](#running-the-checks)
- [Windows notes](#windows-notes)
- [Decisions](#decisions)

## Set up your machine

```bash
git clone https://github.com/AIAYN-creator/Lab-Harness.git
cd Lab-Harness
uv sync --all-extras
uv run pre-commit install --install-hooks --hook-type commit-msg
uv run labharness doctor
```

`labharness doctor` is the fastest way to find out what your machine is missing. Every check
in it exists because it bit someone during development.

| You need | Why | Notes |
|---|---|---|
| Python ≥ 3.11 | The package | `uv` installs it for you if needed |
| A LaTeX distribution | Compiling documents and diagrams | MiKTeX or TeX Live/MacTeX |
| SumatraPDF or Skim | A viewer that reloads and does not lock the PDF | Adobe Acrobat locks the file and breaks the rebuild |
| Java *(optional)* | OPSIN, for the `iupac` extra | Eclipse Temurin |

## A tour of the repository

```
src/labharness/
├── core/        Manifest, workspace creation, errors, lazy extras
├── style/       The journal style (data) and one translator per engine
├── watch/       The orchestrator: run scripts, compile LaTeX, open the viewer
├── cli/         Typer commands: a thin layer over everything above
└── modules/     One subpackage per domain: chem, diagrams, plots
templates/workspace/   What `labharness init` copies, journals included
docs/adr/              Why things are the way they are
tests/                 Unit, contract and LaTeX tests
```

Two rules shape all of it:

1. **The core imports with no extras installed.** RDKit, SciPy and Matplotlib are imported
   lazily, inside functions, through `labharness.core.require`. `tests/test_core.py` runs a
   fresh interpreter and fails if any of them leaks in.
2. **Style is data.** No font, size or colour is written in a module: it comes from the
   journal style file. `tests/test_style.py` even checks that the template shipped to users
   is exactly what the style generates.

## The module contract

A module is plain Python functions. They:

1. never print, read `sys.argv` or call `exit()` — errors are typed exceptions;
2. take style and paths as arguments, and keep no global state;
3. write outputs atomically, so nothing ever reads a half-written PDF;
4. are deterministic: same input, same output;
5. do not import each other, and only use the public API of `core` and `style`;
6. import their heavy dependencies lazily.

Rule 5 is what will let `labharness eject` copy a module into a workspace and have it keep
working. Rule 1 is what lets the same function serve the CLI today and a graphical interface
later.

## Adding a module

1. Create `src/labharness/modules/<name>/` with an `__init__.py` that documents what it does
   and which extra it needs.
2. Add the extra to `pyproject.toml` under `[project.optional-dependencies]`, and register
   the module in `[project.entry-points."labharness.modules"]`.
3. Import heavy dependencies inside the function:

   ```python
   from labharness.core import require

   def render(...):
       rdkit = require("rdkit", extra="chem")
   ```

   If the extra is missing the user gets the exact command to install it, not a traceback.
4. Take every visual decision from the style, never from a literal in your code.
5. Write the figure to a temporary file and rename it into place.
6. Add tests: the numbers your code computes, and what the module does when the input is
   wrong. Mark anything that needs LaTeX with `@pytest.mark.latex`.

## Adding a journal

A journal is one folder, `templates/workspace/journals/<journal>/`:

| File | What it is |
|---|---|
| `style.toml` | Typeface, sizes, column widths, structure geometry and plot defaults. Copy the ACS one and adjust the values. LaTeX that only concerns this journal's document class goes under `[latex] preamble` |
| `paper.tex` | The manuscript skeleton, loading `labharness-style.tex` |
| `references.bib` | An empty or example bibliography |

That is all. `labharness init --journal <journal>` records the journal in the manifest and
generates `labharness-style.tex` from `style.toml`; figure scripts draw for the journal of their
workspace without naming it. No module should need changing: if one does, that is a bug in the
module, and `tests/test_journal_contract.py` is there to catch it.

## Running the checks

```bash
uv run pytest                 # everything, including the LaTeX tests
uv run pytest -m "not latex"  # skip the LaTeX tests
uv run ruff check .
uv run ruff format .
uv run mypy
```

CI runs the same things on Ubuntu and Windows, plus a LaTeX job on Ubuntu. The single
required check is `ci-pass`, which is green only when all the others are.

Tests that need a LaTeX distribution are marked `latex` and skip themselves when `pdflatex`
is not installed, so the suite still passes on a machine without TeX.

## Windows notes

Windows is where LabHarness is developed and demoed, so these are first-class concerns:

- **Paths with spaces** are normal here. Never build a command by pasting strings together.
- **Some editors save in two steps**, which shows up as two rebuilds for one save. That is
  what `--debounce` is for.
- **MiKTeX can report a package as missing when it is installed**: its file database is
  stale. `initexmf --update-fndb` fixes it.
- **Adobe Acrobat locks the PDF** and LaTeX then cannot write it. Use SumatraPDF.

## Decisions

Every architectural decision is written down as an ADR in [`docs/adr/`](adr/): what was
decided, which alternatives were rejected and why. If a change seems to contradict one,
that is a conversation to have first, not something to work around.
