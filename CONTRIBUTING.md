# Contributing to LabHarness

Thanks for your interest! Issues, questions and pull requests are welcome. LabHarness has a single
maintainer, so the guide below is mostly about making a contribution easy to review.

## Before you start

- **A bug, a question, an idea:** open an issue. For a bug, paste the output of
  `labharness doctor`: most problems are an environment one, and it shows which.
- **A small fix** (a typo, a clearer error message, a missing test): open a pull request directly.
- **Anything larger** — a new journal, a new figure kind, a change in behaviour: open an issue
  first so we agree on the approach before you spend time on it. There are issue templates for a
  new journal and for a new module.

Expect a first answer within about a week. That is a goal, not a promise.

## Development setup

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/) and a LaTeX distribution
(MiKTeX or TeX Live). Use a PDF viewer that does not lock files: SumatraPDF on Windows,
Skim on macOS.

```bash
git clone https://github.com/<you>/Lab-Harness.git     # your fork
cd Lab-Harness
uv sync --all-extras
uv run labharness doctor
uv run pytest
```

## Running the checks

The same four commands CI runs. A pull request is only merged with all of them green.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest                   # everything
uv run pytest -m "not latex"    # without a LaTeX distribution
```

Tests that need LaTeX are marked `latex` and skip themselves when it is missing, so the suite runs
anywhere; CI runs them on TeX Live (Linux) and MiKTeX (Windows).

## How a pull request gets in

1. Fork the repository and work on a short-lived branch.
2. Open a pull request against `main`, filling in the template.
3. **The first time you contribute, GitHub waits for the maintainer to approve running CI** on your
   pull request. That is a repository setting, not a judgement about your change.
4. The pull request needs the `ci-pass` check green, the review conversations resolved, and an
   approval from the maintainer. New commits after an approval need a new one.
5. It is merged with squash: your pull request becomes one commit, titled after it.

There is no CLA and no sign-off: contributions are accepted under the project's MIT licence.

## Commit messages and pull request titles

[Conventional Commits](https://www.conventionalcommits.org/), because the squash commit takes the
title of the pull request:

```
feat(plots): add power-law fits
fix(watch): debounce double saves from VS Code on Windows
docs: explain the manifest format
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`, `build`.

## Adding a journal

A journal is one folder, `templates/workspace/journals/<journal>/`, with its `style.toml`,
`paper.tex` and `references.bib`. [`docs/onboarding.md`](docs/onboarding.md) explains each file.
No module should need changing; `tests/test_journal_contract.py` fails if one does.

**Only journals whose LaTeX class has a free licence can be added**, because the template is
copied into every user's workspace. Check the class on CTAN before starting.

## Adding a figure kind or a module

See *Adding a module* in [`docs/onboarding.md`](docs/onboarding.md). In short:

- modules are plain functions with no terminal I/O;
- heavy dependencies go behind an extra, and the core must import without any;
- no hard-coded fonts, sizes or colours: everything comes from the style;
- outputs are written atomically.

## Design rules

Please read [`AGENTS.md`](AGENTS.md): it applies to humans too. Larger design decisions are
recorded in [`docs/adr/`](docs/adr/). If a change contradicts one, say so in the issue before
working around it.

## Code of conduct

This project follows its [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to
uphold it.
