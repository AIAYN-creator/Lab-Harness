"""A problem in the data names its file, line and column, and never stops the watcher."""

from pathlib import Path

import pytest

from labharness.core import load_workspace
from labharness.core.errors import LabHarnessError
from labharness.watch.runner import build_figure

numpy = pytest.importorskip("numpy")

from labharness.modules.plots import Series, read_series  # noqa: E402

# Line 1 is metadata, line 2 is blank, line 3 is the header: the bad cell is on line 6.
EXPORT = "Instrument: UV-1800\n\nt;c\n0;1,00\n30;0,64\n60;n.d.\n90;0,26\n"


def test_a_cell_that_is_not_a_number_is_located_by_file_line_and_column(tmp_path: Path) -> None:
    source = tmp_path / "decay.csv"
    source.write_text(EXPORT, encoding="utf-8")

    with pytest.warns(match="skipped"), pytest.raises(LabHarnessError) as error:
        read_series(Series(csv=source, x="t", y="c"))

    assert str(error.value) == "'decay.csv', line 6, column 'c': 'n.d.' is not a number"


def test_an_empty_cell_says_it_is_empty(tmp_path: Path) -> None:
    source = tmp_path / "decay.csv"
    source.write_text("t;c\n0;1,00\n30;\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="line 3, column 'c': an empty cell"):
        read_series(Series(csv=source, x="t", y="c"))


def test_the_watcher_shows_the_message_not_a_traceback(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        '[[figure]]\noutput = "figures/decay.pdf"\nscript = "scripts/decay.py"\n'
        'inputs = ["data/decay.csv"]\n',
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "data" / "decay.csv").write_text("t;c\n0;1,00\n30;x\n", encoding="utf-8")
    (tmp_path / "scripts" / "decay.py").write_text(
        "from labharness.modules.plots import Series, read_series\n"
        'read_series(Series(csv="data/decay.csv", x="t", y="c"))\n',
        encoding="utf-8",
    )
    workspace = load_workspace(tmp_path)

    result = build_figure(workspace, workspace.figures[0])

    assert not result.ok
    assert result.error == "'decay.csv', line 3, column 'c': 'x' is not a number"
