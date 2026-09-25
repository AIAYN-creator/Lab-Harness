"""Draw the LabHarness logo with LabHarness, into docs/brand.

Everything LabHarness shows, LabHarness makes: the logo is a TikZ diagram compiled by the
diagrams module, like any figure, and exported to PDF, SVG and PNG. The mark is the program in
one picture: three measurements and the curve that follows them, the one that just changed in
the accent colour.

    uv run python tools/make_brand.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from labharness.modules.diagrams import render_diagram

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "docs" / "brand"

# dec-identidad-visual: black, the brand blue, and the orange that marks what changed.
BLUE, ORANGE, INK, PAPER = "0072B2", "E69F00", "000000", "FFFFFF"

# The mark on a 10 x 10 grid: an axis, a decay through three points, the middle one moved.
MARK = r"""\begin{{tikzpicture}}[x=1mm, y=1mm, line cap=round, line join=round]
  \definecolor{{line}}{{HTML}}{{{line}}}
  \definecolor{{accent}}{{HTML}}{{{accent}}}
  {background}
  \draw[line, line width=1.3mm] (0.6,10) -- (0.6,0.6) -- (10,0.6);
  \draw[line, line width=1.1mm] (2.6,8.8) .. controls (4.2,4.2) and (6,3.1) .. (9.4,2.6);
  \fill[line] (2.6,8.8) circle (1.2mm);
  \fill[accent] (4.75,4.95) circle (1.5mm);
  \fill[line] (9.4,2.6) circle (1.2mm);
  {wordmark}
\end{{tikzpicture}}"""
WORDMARK = (
    r"\node[anchor=west, text=line, inner sep=0] at (12.5,5)"
    r" {\sffamily\bfseries\fontsize{26}{26}\selectfont LabHarness};"
)
BACKGROUND = r"\fill[{colour}] (-2,-2) rectangle ({right},12);"

VARIANTS = {
    # name: (line, accent, background, with the wordmark)
    "logo": (BLUE, ORANGE, None, True),
    "logo-mono": (INK, INK, None, True),
    "logo-negative": (PAPER, ORANGE, BLUE, True),
    "mark": (BLUE, ORANGE, None, False),
    "mark-mono": (INK, INK, None, False),
    "mark-negative": (PAPER, ORANGE, BLUE, False),
}


def draw(name: str, line: str, accent: str, background: str | None, wordmark: bool) -> None:
    fill = ""
    if background is not None:
        fill = (
            r"\definecolor{bg}{HTML}{"
            + background
            + "}"
            + BACKGROUND.format(colour="bg", right=58 if wordmark else 12)
        )
    source = MARK.format(
        line=line, accent=accent, background=fill, wordmark=WORDMARK if wordmark else ""
    )
    with tempfile.TemporaryDirectory() as scratch:
        tex = Path(scratch) / f"{name}.tex"
        tex.write_text(source, encoding="utf-8")
        pdf = BRAND / f"{name}.pdf"
        render_diagram(tex, pdf, border_pt=0)
    _convert(pdf, name)
    print(f"docs/brand/{name}.pdf, .svg, .png")


def _convert(pdf: Path, name: str) -> None:
    """SVG for the web, and PNG: 512 px wide for avatars, and the mark at 16 px to check it."""
    pdftocairo = shutil.which("pdftocairo")
    if pdftocairo is None:
        raise SystemExit("needs pdftocairo, from poppler (it comes with MiKTeX and TeX Live)")
    subprocess.run([pdftocairo, "-svg", pdf, BRAND / f"{name}.svg"], check=True)
    subprocess.run(
        [
            pdftocairo,
            "-png",
            "-singlefile",
            "-scale-to-x",
            "512",
            "-scale-to-y",
            "-1",
            "-transp",
            pdf,
            BRAND / name,
        ],
        check=True,
    )
    if name == "mark":
        subprocess.run(
            [
                pdftocairo,
                "-png",
                "-singlefile",
                "-scale-to-x",
                "32",
                "-scale-to-y",
                "32",
                "-transp",
                pdf,
                BRAND / "favicon",
            ],
            check=True,
        )


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    for name, (line, accent, background, wordmark) in VARIANTS.items():
        draw(name, line, accent, background, wordmark)


if __name__ == "__main__":
    main()
