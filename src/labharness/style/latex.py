"""Translating a style into LaTeX: the document preamble and the TikZ figure preamble."""

from labharness.style.tokens import Style

GENERATED_MARK = "% LabHarness document style -- generated"

DOCUMENT_PREAMBLE = r"""% LabHarness document style -- generated from the {name} journal style.
%
% One typeface for the whole document, text and figures alike: {family}.
% Do not set fonts anywhere else; change them in the journal style file instead.
\usepackage[T1]{{fontenc}}
{packages}
\usepackage{{graphicx}}
% Editorial tables: rules, numbers aligned on the decimal mark, and notes under the table.
\usepackage{{booktabs}}
\usepackage{{siunitx}}
\usepackage{{threeparttable}}
\sisetup{{separate-uncertainty = true}}
{journal_preamble}
% \labfigure{{path}}: include a generated figure at its natural (final) size.
% If the figure does not exist yet, show a placeholder so the document still compiles.
\newcommand{{\labfigure}}[1]{{%
  \IfFileExists{{#1}}%
    {{\includegraphics{{#1}}}}%
    {{\fbox{{\parbox{{0.9\linewidth}}{{%
      \centering\ttfamily Figure not generated yet:\\\detokenize{{#1}}%
    }}}}}}%
}}

% \labtable{{path}}: include a generated table. Put it inside a table environment, which
% carries the caption and the label. If it does not exist yet, show a placeholder.
\newcommand{{\labtable}}[1]{{%
  \IfFileExists{{#1}}%
    {{\input{{#1}}}}%
    {{\fbox{{\ttfamily Table not generated yet: \detokenize{{#1}}}}}}%
}}

% \labresults{{path}}: load the macros written next to a fitted plot
% (e.g. figures/calibration.fit.tex) so the text can cite fitted values that update with the data.
\newcommand{{\labresults}}[1]{{\InputIfFileExists{{#1}}{{}}{{}}}}
"""

TIKZ_PREAMBLE = r"""% LabHarness figure style -- generated from the {name} journal style.
%
% Shared by every standalone diagram, so mechanisms, flowcharts and structures match the
% document and each other.
\usepackage[T1]{{fontenc}}
{packages}
\usepackage{{tikz}}
\usepackage{{chemfig}}
% arrows.meta for the arrowheads used below, positioning for "right=of", calc for coordinates.
\usetikzlibrary{{arrows.meta, positioning, calc}}

\setchemfig{{
  atom sep = {bond_length}pt,
  bond style = {{line width = {line_width}pt}},
  cram width = {wedge_width}pt,
  double bond sep = {double_bond_sep}pt,
}}

\tikzset{{
  every picture/.style = {{line width = {line_width}pt}},
  % Arrow pushing: a full head moves an electron pair, a half head a single electron.
  electron pair/.style = {{-stealth, line width = {line_width}pt}},
  single electron/.style = {{-{{Stealth[left]}}, line width = {line_width}pt}},
  node label/.style = {{font = \small, inner sep = 2pt}},
}}
"""


def document_preamble(style: Style) -> str:
    """The contents of ``labharness-style.tex`` in a workspace."""
    journal = style.latex.preamble.strip()
    return DOCUMENT_PREAMBLE.format(
        name=style.name.upper(),
        family=style.typography.family,
        packages=_packages(style),
        journal_preamble=f"\n{journal}\n" if journal else "",
    )


def tikz_preamble(style: Style) -> str:
    """The preamble injected into every standalone diagram."""
    structures = style.structures
    return TIKZ_PREAMBLE.format(
        name=style.name.upper(),
        packages=_packages(style),
        bond_length=_number(structures.bond_length_pt),
        line_width=_number(structures.line_width_pt),
        wedge_width=_number(structures.wedge_width_pt),
        double_bond_sep=_number(structures.bond_length_pt * structures.double_bond_offset),
    )


def _packages(style: Style) -> str:
    return "\n".join(f"\\usepackage{{{package}}}" for package in style.typography.latex_packages)


def _number(value: float) -> str:
    """Format a number for LaTeX: no trailing zeros, no exponents."""
    return f"{value:.3f}".rstrip("0").rstrip(".")
