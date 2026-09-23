# Security policy

## Supported versions

LabHarness is pre-1.0: only the latest release and `main` receive fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report it privately, whichever way
suits you:

- through GitHub: the **Security** tab of the repository, then **Report a vulnerability**;
- by email to labharness.project@gmail.com, with the details and, if you can, a way to reproduce
  the problem.

We aim to acknowledge reports within a week, and to agree with you on when a fix is disclosed.

## What is in scope

LabHarness runs locally and makes no network requests by default. The most relevant risks are
input files processed on your machine:

- **Figure scripts are Python and run with your permissions.** The watcher runs every script
  listed in `labharness.toml`, so only open workspaces you trust, as with any code you run.
- **LaTeX sources** are compiled without ever asking for `-shell-escape`. A way to make
  LabHarness run shell commands through LaTeX is in scope.
- **Data files** (CSV, SMILES, spreadsheets) must never execute anything: if one can, that is a
  vulnerability.

## What the repository does

- **Dependabot security alerts** are on: the maintainer is told when a dependency in `uv.lock` has
  a published vulnerability.
- **Secret scanning with push protection** is on: a push containing a credential is blocked.
- There are no automatic dependency update pull requests: upgrades are deliberate.
