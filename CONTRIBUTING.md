# Contributing to LabHarness

Thanks for your interest! **LabHarness is pre-alpha and the repository is private.** External
contributions open with the public v1.0 release. This guide already describes how they will work.

## Development setup

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/) and a LaTeX distribution
(MiKTeX or TeX Live). On Windows with MiKTeX, `latexmk` also needs Perl
(e.g. Strawberry Perl). Use a PDF viewer that does not lock files: SumatraPDF on Windows,
Skim on macOS.

```
git clone https://github.com/AIAYN-creator/Lab-Harness.git
cd Lab-Harness
uv sync --all-extras
uv run pytest
```

## How changes get in

- **Before v1.0:** the maintainer commits directly to `main`.
- **From v1.0 on:**
  1. Open an issue first for anything beyond a small fix, so we can agree on the approach.
  2. Work on a short-lived branch and open a pull request against `main`.
  3. The pull request needs the `ci-pass` check to be green and an approval from the
     maintainer (code owner). It is merged with squash.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(plots): add power-law fits
fix(watch): debounce double saves from VS Code on Windows
docs: explain the manifest format
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`, `build`.

## Design rules

Please read [`AGENTS.md`](AGENTS.md). It applies to humans too. In short:

- modules are plain functions with no terminal I/O;
- the core imports without any extra;
- no hard-coded fonts, sizes or colours;
- larger design decisions are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Code of conduct

This project follows its [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to
uphold it.
