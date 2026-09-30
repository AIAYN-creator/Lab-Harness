# {{distribution}}

LabHarness for {{domain}}: figures, tables and agent rules, as a package of its own. It was
started with `labharness new-domain {{domain}}`, and it works as it is: it draws one example.

## Make it yours

1. **Install it** next to LabHarness: `uv pip install -e .` (or `pip install -e .`).
2. **See that LabHarness finds it**: `labharness doctor` lists it under *modules*.
3. **Try the example** in a workspace: `labharness add {{domain}} first`, then `labharness build`.
4. **Replace it** with what your field draws: the code in `{{package}}/__init__.py`, and the
   script it starts from in `{{package}}/templates/{{domain}}.py.template`.
5. **Write the rules** an AI agent should follow in `{{package}}/AGENTS.{{domain}}.md`. A
   workspace gets them with `labharness init --field {{domain}}`.

`pytest` runs the tests that came with it. Add one for everything you add.

## What this package must not do

Touch LabHarness's core. Everything it needs is behind the entry points in `pyproject.toml`, and
that is what lets anyone add a field without asking. Data files are read with
`labharness.core.tabular.read_rows`, and never written to: `data/` belongs to the person.

Licence: MIT, like LabHarness.
