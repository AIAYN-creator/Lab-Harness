# Instructions for AI agents working on the LabHarness repository

LabHarness is a local-first Data-to-Paper harness: raw lab data in, publication-ready LaTeX
figures out. This file is for agents that **develop LabHarness itself**. The rules for agents
that write papers *with* LabHarness live in `templates/workspace/AGENTS.md`.

## Non-negotiable

1. **Never commit or push without explicit authorization from the maintainer (@AIAYN-creator),
   every single time.** Prepare the change, show what would be committed, and wait.
2. When an agent took part in a commit, add the trailer `Supervised-by: <agent name>`.
   **Never** use `Co-Authored-By` for an agent.
3. Design decisions are recorded as ADRs (`docs/adr/`). Do not contradict an accepted ADR;
   if a change seems to require it, raise it with the maintainer instead.

## Architecture rules

- `src/labharness/` holds the package: `core`, `style`, `watch`, `cli` and `modules/<domain>`.
- **The CLI and the watcher are thin consumers.** No figure logic lives in them.
- **The core must import without any extra installed.** Heavy dependencies (RDKit, SciPy,
  Matplotlib, OPSIN, …) are imported lazily inside functions through `labharness.core.require`.
  `tests/test_core.py` enforces it.
- Every module follows the contract described in `src/labharness/modules/__init__.py`:
  - no printing and no `sys.argv` or `exit()`;
  - no global state;
  - atomic writes and deterministic output;
  - no imports between modules, and only the public API of `core` and `style`.
- **Never hard-code fonts, sizes or colours in a module.** Everything comes from the shared
  style: one typeface for the whole document.
- `templates/workspace/` is the researcher's workspace template, shipped inside the package.

## Conventions

- Code, CLI messages and repository docs are in English.
- Commits follow Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `ci`,
  `chore`, `build`), optionally scoped by area, e.g. `feat(chem): …`.
- Paths with spaces and Windows are first-class: the maintainer develops on Windows.

## Commands

```
uv sync --all-extras
uv run pytest
```

Linting, formatting and type checking are added with the CI setup.
