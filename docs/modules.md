# Build a module for your field

LabHarness draws figures and tables from raw data, and the same core serves any field. What
changes from one field to another is the module that reads the data and draws: chemistry is one
(structures, mechanisms, the lab compound library), plots and tables are others. **Yours is a
package of its own**: you never change LabHarness, and nobody has to accept a change to it for
your module to work.

Not everyone has to write one. You can also [ask for one, and put a bounty on it](bounties.md).

## What a domain is

An ordinary Python package that tells LabHarness what it brings through *entry points*, four
groups in its `pyproject.toml` ([ADR 31](adr/README.md)):

| Group | What it adds | How a person uses it |
|---|---|---|
| `labharness.modules` | The code your scripts import | `from labharness_architecture import render` |
| `labharness.figures` | A kind of figure or table, started from `templates/<kind>.py.template` | `labharness add architecture floor` |
| `labharness.fields` | The rules for AI agents, `AGENTS.<field>.md` | `labharness init --field architecture` |
| `labharness.commands` | Commands on the command line, from a module with `register(app)` | `labharness architecture-hello` |

LabHarness's own chemistry, plots, tables and diagrams are registered the same way: no domain is
special. A test fails if anything in the core imports a module.

## Start one

```bash
labharness new-domain architecture      # writes labharness-architecture/
cd labharness-architecture
uv pip install -e .
labharness doctor                       # lists it under "modules"
pytest                                  # the tests that came with it pass
```

It works as it comes: one example of each of the four things above. Its `README.md` has the five
steps to make it yours. Then, in any workspace, `labharness init --field architecture`,
`labharness add architecture floor` and `labharness build`.

## What LabHarness gives your module

Take it from the core instead of writing it again; it is what makes a module behave like the
others.

| You need | Use |
|---|---|
| Write a file so a half-written one is never seen | `labharness.core.atomic.atomic_output` |
| Read a table: CSV, TSV, TXT, `.xlsx`; encodings, decimal commas, metadata rows, errors with file, line and column | `labharness.core.tabular.read_rows` |
| A value and its uncertainty rounded together | `labharness.core.numbers.round_together` |
| Fonts, sizes and widths of the journal | `labharness.style.load_style` |
| A heavy dependency behind an extra, with the command to install it if it is missing | `labharness.core.require` |

## Rules a module follows

1. **Do not touch LabHarness's core.** Everything you need is behind the entry points.
2. **Never write to `data/`.** It belongs to the person; changing it is a decision they take with
   `labharness accept`.
3. **Every visual decision comes from the journal's style**, never from a literal in your code.
   One typeface for the whole document, figures generated at their final size.
4. **Import heavy libraries inside the function**, with `require`, so the package installs and
   `labharness doctor` runs without them.
5. **A test for everything you add**, and for what happens when the input is wrong.
6. **Rules for AI agents that say what to check**, not what the agent already knows: units,
   conventions and what must never be invented.

A domain that follows them also survives `labharness eject`: the script's copy carries your module
with it. The libraries it needs, such as `ezdxf` or `statsmodels`, are yours to install.

## Publish it

Name it `labharness-<field>`, as `new-domain` does, and publish it to PyPI like any package:
`pip install labharness-architecture`. To be paid a [bounty](bounties.md) it has to be MIT, like LabHarness.

## Three ways to contribute

- **Write a module** for your field, as above.
- **[Ask for one](../.github/ISSUE_TEMPLATE/new_module.yml)**, and, if you want, put a
  [bounty](bounties.md) on it. Anyone can claim it.
- **Improve LabHarness itself**: issues and pull requests are welcome, see
  [`CONTRIBUTING.md`](../.github/CONTRIBUTING.md).
