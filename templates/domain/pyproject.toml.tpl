# {{distribution}}: LabHarness for {{domain}}. This file is what tells LabHarness what the package
# brings; nothing else is needed for it to be found once it is installed.
[project]
name = "{{distribution}}"
version = "0.1.0"
description = "Figures, tables and agent rules for {{domain}}, for LabHarness."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
dependencies = ["labharness"]

# A module: the code your scripts import.
[project.entry-points."labharness.modules"]
{{domain}} = "{{package}}"

# A kind of figure `labharness add` offers: the file templates/{{domain}}.py.template starts it.
[project.entry-points."labharness.figures"]
{{domain}} = "{{package}}"

# A field: the file AGENTS.{{domain}}.md is copied by `labharness init --field {{domain}}`.
[project.entry-points."labharness.fields"]
{{domain}} = "{{package}}"

# Commands added to the command line: a module with a register(app) function.
[project.entry-points."labharness.commands"]
{{domain}} = "{{package}}.commands"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = ["."]
