# LabHarness

> **Status: pre-alpha — under active design.** Nothing here is usable yet. This README is a placeholder; the full README (written before the code, README-driven development) lands with v0.1.

**LabHarness** is an open-source, local-first harness for scientific writing and lab-data automation — *Data-to-Paper*. It turns raw lab files (`.csv`, `.smi`, `.mol`, …) into publication-ready vector figures for LaTeX, and keeps the PDF in sync as the data changes.

AI helps write the pipeline, but the pipeline is always **short, readable Python you can open and edit** — never a black box.

## Who it is for

Researchers, PhD students and science students who already write in LaTeX/Overleaf and are comfortable in a terminal and an editor like VS Code or Zed.

## Principles

- **Local-first.** Everything runs on your machine; nothing needs the network by default.
- **Human-in-the-loop.** Figures come from transparent scripts you can read, tweak or take over entirely.
- **Zero layout friction.** One typeface for the whole document — figures included — and figures generated at their final printed size, so labels, axes and structures always match the text.
- **Save and see.** Change a data point or a SMILES string, save, and the figure and the PDF update on their own.
- **Modular.** Install only the domains you use.

## Planned for v0.1

| Module | What it does |
|---|---|
| **Chemical structures** | SMILES (or an IUPAC name, resolved offline) → vector PDF, via RDKit |
| **Diagrams** | Reaction mechanisms with arrow-pushing, flowcharts and technical frameworks, via TikZ/chemfig |
| **Regressions & plots** | Linear, polynomial, logarithmic, exponential and custom fits with error bars, labelled axes and units, via SciPy/Matplotlib |
| **Watcher** | Event-driven orchestrator: regenerates only the affected figures and recompiles the PDF |

v0.1 ships with the ACS journal template only and is operated entirely from the command line.

## Roadmap

| Version | Focus |
|---|---|
| **v0.1** | Demo-ready MVP: structures, diagrams, regressions, watcher, ACS template |
| **v0.5** | Daily use: editorial LaTeX tables (booktabs/siunitx), real agent rules, lab compound libraries |
| **v1.0** | Public release: more journal templates (RSC, Elsevier), selectable typeface |
| **v1.5+** | New domains: economics, mathematics, architecture/engineering |
| **v2.0** | A graphical interface for people who don't use a terminal |

## License

[MIT](LICENSE) © 2026 AIAYN-creator
