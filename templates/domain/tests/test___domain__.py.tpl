from pathlib import Path

import {{package}}
from {{package}} import render

HERE = Path({{package}}.__file__).parent


def test_render_writes_the_file(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"

    render(str(output), "hi")

    assert output.read_text(encoding="utf-8") == "hi"


def test_the_package_brings_the_template_and_the_rules_it_registers() -> None:
    assert (HERE / "templates" / "{{domain}}.py.template").is_file()
    assert (HERE / "AGENTS.{{domain}}.md").is_file()
