"""Chemical structures: SMILES to a vector PDF, drawn with RDKit."""

import io
from pathlib import Path

from labharness.core.atomic import atomic_output
from labharness.core.errors import LabHarnessError
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
) -> Path:
    """Draw a molecule and write it as a vector PDF.

    Give it either a SMILES string or a file containing one. The geometry and the typeface
    come from the journal style, so every structure in a document matches.
    """
    if (smiles is None) == (smiles_file is None):
        raise LabHarnessError("give render_structure either 'smiles' or 'smiles_file'")

    if smiles_file is not None:
        smiles = read_smiles(smiles_file)
    assert smiles is not None  # for type checkers; the check above guarantees it

    style = style or load_style()
    width_pt = (width_in or style.dimensions.single_column_in) * 72
    svg = _draw_svg(smiles, style, width_pt)

    output = Path(output)
    with atomic_output(output) as temporary:
        _svg_to_pdf(svg, temporary, width_pt)
    return output


def _draw_svg(smiles: str, style: Style, width_pt: float) -> str:
    chem = require("rdkit.Chem", extra="chem")
    draw = require("rdkit.Chem.Draw.rdMolDraw2D", extra="chem")

    molecule = chem.MolFromSmiles(smiles)
    if molecule is None:
        raise LabHarnessError(f"'{smiles}' is not a valid SMILES string")

    # RDKit works in canvas units; the conversion below maps one of them to one point,
    # so the bond length asked for in points is the bond length on paper.
    width = int(width_pt)
    height = int(width / style.dimensions.aspect_ratio)
    drawer = draw.MolDraw2DSVG(width, height)
    apply_to_draw_options(drawer.drawOptions(), style)

    draw.PrepareAndDrawMolecule(drawer, molecule)
    drawer.FinishDrawing()
    return str(drawer.GetDrawingText())


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
