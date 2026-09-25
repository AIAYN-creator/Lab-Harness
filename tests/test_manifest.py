from pathlib import Path

import pytest

from labharness.core import LabHarnessError, find_workspace, load_workspace

MANIFEST = """
[[figure]]
output = "figures/catalyst.pdf"
script = "scripts/catalyst.py"
inputs = ["data/catalyst.smi"]

[[figure]]
output = "figures/kinetics.pdf"
script = "scripts/kinetics.py"
inputs = ["data/kinetics_25C.csv", "data/kinetics_40C.csv"]
"""


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    (tmp_path / "labharness.toml").write_text(MANIFEST, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "data").mkdir()
    return tmp_path


def test_a_workspace_is_found_from_any_folder_inside_it(workspace_root: Path) -> None:
    deep = workspace_root / "scripts"

    assert find_workspace(deep) == workspace_root.resolve()


def test_outside_a_workspace_the_error_says_how_to_make_one(tmp_path: Path) -> None:
    with pytest.raises(LabHarnessError, match="labharness init"):
        find_workspace(tmp_path)


def test_figures_are_read_from_the_manifest(workspace_root: Path) -> None:
    workspace = load_workspace(workspace_root)

    assert [figure.name for figure in workspace.figures] == ["catalyst", "kinetics"]
    assert workspace.journal == "acs"
    assert workspace.figures[1].inputs == (
        Path("data/kinetics_25C.csv"),
        Path("data/kinetics_40C.csv"),
    )


def test_changing_a_data_file_rebuilds_only_its_figure(workspace_root: Path) -> None:
    workspace = load_workspace(workspace_root)

    affected = workspace.figures_affected_by(workspace_root / "data" / "catalyst.smi")

    assert [figure.name for figure in affected] == ["catalyst"]


def test_changing_a_script_rebuilds_its_figure(workspace_root: Path) -> None:
    workspace = load_workspace(workspace_root)

    affected = workspace.figures_affected_by(workspace_root / "scripts" / "kinetics.py")

    assert [figure.name for figure in affected] == ["kinetics"]


def test_changing_the_manifest_or_the_style_rebuilds_everything(workspace_root: Path) -> None:
    workspace = load_workspace(workspace_root)

    for path in ("labharness.toml", "labharness-style.tex"):
        affected = workspace.figures_affected_by(workspace_root / path)
        assert len(affected) == 2, path


def test_an_unrelated_file_rebuilds_nothing(workspace_root: Path) -> None:
    workspace = load_workspace(workspace_root)

    assert workspace.figures_affected_by(workspace_root / "data" / "notes.txt") == []
    assert workspace.figures_affected_by(Path("/somewhere/else/catalyst.smi")) == []


def test_two_figures_writing_to_the_same_file_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        """
[[figure]]
output = "figures/a.pdf"
script = "scripts/a.py"

[[figure]]
output = "figures/a.pdf"
script = "scripts/b.py"
""",
        encoding="utf-8",
    )

    with pytest.raises(LabHarnessError, match="two"):
        load_workspace(tmp_path)


def test_a_figure_without_a_script_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        '[[figure]]\noutput = "figures/a.pdf"\n', encoding="utf-8"
    )

    with pytest.raises(LabHarnessError, match="script"):
        load_workspace(tmp_path)


def test_a_broken_manifest_says_so(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text("[[figure]\n", encoding="utf-8")

    with pytest.raises(LabHarnessError, match="not valid TOML"):
        load_workspace(tmp_path)


def test_tables_are_declared_like_figures_and_rebuilt_from_their_data(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        MANIFEST
        + """
[[table]]
output = "tables/optimisation.tex"
script = "scripts/optimisation.py"
inputs = ["data/optimisation.csv"]
""",
        encoding="utf-8",
    )

    workspace = load_workspace(tmp_path)
    affected = workspace.figures_affected_by(tmp_path / "data" / "optimisation.csv")

    assert [(item.name, item.kind) for item in affected] == [("optimisation", "table")]
    assert [item.kind for item in workspace.figures] == ["figure", "figure", "table"]


def test_a_table_and_a_figure_writing_to_the_same_file_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "labharness.toml").write_text(
        MANIFEST
        + """
[[table]]
output = "figures/catalyst.pdf"
script = "scripts/other.py"
""",
        encoding="utf-8",
    )

    with pytest.raises(LabHarnessError, match="two entries write to"):
        load_workspace(tmp_path)
