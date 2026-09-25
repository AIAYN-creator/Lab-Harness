"""Chemical structures: SMILES to a vector PDF, drawn with RDKit."""

import io
import re
import warnings
from pathlib import Path
from typing import Any

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError, LabHarnessWarning
from labharness.core.extras import require
from labharness.style.rdkit import apply_to_draw_options
from labharness.style.tokens import Style, load_style

COMMENT = "#"


def read_smiles(path: Path | str) -> str:
    """Read a SMILES string from a ``.smi`` file, ignoring comments and blank lines."""
    path = Path(path)
    if not path.is_file():
        raise LabHarnessError(f"'{path}' does not exist")

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(COMMENT):
            # A .smi line may carry a name after the SMILES, separated by whitespace.
            return stripped.split()[0]

    raise LabHarnessError(f"'{path}' has no SMILES in it")


def render_structure(
    output: Path | str,
    smiles: str | None = None,
    smiles_file: Path | str | None = None,
    style: Style | None = None,
    width_in: float | None = None,
    compound: str | None = None,
    library: Path | str | None = None,
) -> Path:
    """Draw a molecule and write it as a vector PDF.

    Give it a SMILES string, a file containing one, or a ``compound`` of the lab's
    ``library`` by its name, code or alias; list the library in the figure's inputs so the
    figure is redrawn when the inventory changes. The geometry and the typeface
    come from the journal style, so every structure in a document matches.

    The structure is drawn as large as the layout allows, with no blank canvas around it.
    The room is ``width_in``, by default the journal's column width, which for a single-column
    document is the text width; its height is at most ``max_height_ratio`` of that. Within that
    box the molecule grows until it fills it, with bonds at most ``max_bond_scale`` times the
    journal's and atom labels kept at the document's text size. A molecule too large for the
    box is shrunk to fit instead, with a warning: its bonds are then shorter than the
    journal asks for.
    """
    if sum(given is not None for given in (smiles, smiles_file, compound)) != 1:
        raise LabHarnessError(
            "give render_structure one of 'smiles', 'smiles_file' or 'compound' (with 'library')"
        )

    if smiles_file is not None:
        smiles = read_smiles(smiles_file)
    if compound is not None:
        smiles = _from_library(compound, library)
    assert smiles is not None  # for type checkers; the check above guarantees it

    style = style or load_style()
    box_width = (width_in or style.dimensions.single_column_in) * 72
    box_height = box_width * style.structures.max_height_ratio
    svg, width_pt = _draw_svg(smiles, style, box_width, box_height, name=Path(output).name)

    output = Path(output)
    with atomic_output(output) as temporary:
        _svg_to_pdf(svg, temporary, width_pt)
    return output


def _from_library(compound: str, library: Path | str | None) -> str:
    """The SMILES of ``compound`` in the library, with every check on it reported."""
    from labharness.modules.chem.library import check, load_library, settings_for

    if library is None:
        raise LabHarnessError("compound= needs library=, the inventory file it is in")
    inventory = load_library(library, **settings_for(Path(library)))
    found = inventory.find(compound)
    if found is None:
        raise LabHarnessError(f"'{compound}' is not in {Path(library).name}")
    for finding in check(found):
        warnings.warn(f"{compound}: {finding}", LabHarnessWarning, stacklevel=3)
    return found.smiles


def _draw_svg(
    smiles: str, style: Style, box_width: float, box_height: float, name: str
) -> tuple[str, float]:
    """The molecule as SVG, as large as fits the box, and its width in points on paper."""
    chem = require("rdkit.Chem", extra="chem")
    draw = require("rdkit.Chem.Draw.rdMolDraw2D", extra="chem")

    molecule = chem.MolFromSmiles(smiles)
    if molecule is None:
        raise LabHarnessError(f"'{smiles}' is not a valid SMILES string")

    # A canvas of -1 x -1 lets RDKit size it to the molecule: its outline, with no blank area
    # to waste space. On such a canvas RDKit ignores fixedBondLength and scales by
    # scalingFactor, in canvas units per depiction unit, so the scale is set from the bond
    # length of the depiction itself. One canvas unit becomes one point on paper below.
    depictor = require("rdkit.Chem.rdDepictor", extra="chem")
    depictor.Compute2DCoords(molecule)
    per_unit = style.structures.bond_length_pt / _mean_bond_length(molecule)

    natural_width, natural_height = _canvas_size(_draw(draw, molecule, style, per_unit))
    fits = min(box_width / natural_width, box_height / natural_height)
    scale = min(fits, style.structures.max_bond_scale)

    if scale < 1:
        warnings.warn(
            f"{name}: the molecule is {natural_width / 72:.2f} x {natural_height / 72:.2f} in "
            f"at the journal's bond length and does not fit in {box_width / 72:.2f} x "
            f"{box_height / 72:.2f} in, so it is drawn at {scale:.0%} of that bond length. "
            "Give it more room with width_in=, or split the scheme.",
            LabHarnessWarning,
            stacklevel=3,
        )

    svg = _draw(draw, molecule, style, per_unit * scale, shrunk=scale < 1)
    width, height = _canvas_size(svg)
    # Labels and padding do not scale exactly with the bonds: never exceed the box.
    return svg, min(width, box_width, box_height * width / height)


def _mean_bond_length(molecule: Any) -> float:
    """The bond length of the 2D depiction, in its own units (1.5 for RDKit's coordinates)."""
    conformer = molecule.GetConformer()
    lengths = [
        (
            conformer.GetAtomPosition(bond.GetBeginAtomIdx())
            - conformer.GetAtomPosition(bond.GetEndAtomIdx())
        ).Length()
        for bond in molecule.GetBonds()
    ]
    return sum(lengths) / len(lengths) if lengths else 1.5


def _draw(draw: Any, molecule: Any, style: Style, per_unit: float, shrunk: bool = False) -> str:
    """Draw on a canvas sized to the molecule, ``per_unit`` points per depiction unit.

    Atom labels grow and shrink with the bonds, as they do in ChemDraw; when a molecule has
    to shrink to fit they are kept at no less than the document's small text size.
    """
    drawer = draw.MolDraw2DSVG(-1, -1)
    options = drawer.drawOptions()
    apply_to_draw_options(options, style)
    options.scalingFactor = per_unit
    # No padding: the canvas is already the molecule's outline, and padding on a flexible
    # canvas shrinks the bonds instead of adding a margin.
    options.padding = 0.0
    if shrunk:
        options.minFontSize = round(style.typography.small_size_pt)
    draw.PrepareAndDrawMolecule(drawer, molecule)
    drawer.FinishDrawing()
    return str(drawer.GetDrawingText())


def _canvas_size(svg: str) -> tuple[float, float]:
    match = re.search(r"width='([0-9.]+)px' height='([0-9.]+)px'", svg)
    if match is None:  # pragma: no cover - RDKit always writes the canvas size
        raise LabHarnessError("RDKit wrote an SVG without a size")
    return float(match.group(1)), float(match.group(2))


def _svg_to_pdf(svg: str, output: Path, width_pt: float) -> None:
    """Convert RDKit's SVG into PDF, at exactly the width asked for.

    RDKit draws atom labels as outlines rather than text, so the conversion never has to
    resolve a font: the PDF holds the same shapes the SVG had.

    The rescaling matters. svglib reads the SVG pixels as CSS pixels at 96 dpi, so a
    234-unit canvas would become a 175 pt figure: three quarters of the requested size, with
    bonds three quarters as long as the journal asks for. Scaling the drawing so its width is
    the requested number of points maps one canvas unit to one point and puts the geometry
    back where it belongs.
    """
    svglib = require("svglib.svglib", extra="chem")
    render_pdf = require("reportlab.graphics.renderPDF", extra="chem")

    drawing = svglib.svg2rlg(io.BytesIO(svg.encode("utf-8")))
    if drawing is None:
        raise LabHarnessError("the structure could not be converted to PDF")

    factor = width_pt / drawing.width
    drawing.scale(factor, factor)
    drawing.width *= factor
    drawing.height *= factor

    render_pdf.drawToFile(drawing, str(output))
