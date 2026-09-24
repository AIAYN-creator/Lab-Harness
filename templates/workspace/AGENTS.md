# Instructions for AI agents working in this LabHarness workspace

This folder is a scientific writing workspace managed with LabHarness: raw data in `data/`,
transparent scripts in `scripts/`, generated figures and tables in `figures/` and `tables/`, and
the manuscript in `paper.tex`. The human stays in the loop: you write readable scripts, they
decide.

These are the rules for every field. The rules of a field are in their own file, next to this
one: **read `AGENTS.<field>.md` for every field this workspace uses** (`AGENTS.chemistry.md` for
chemistry). Where the two disagree, the field's file wins.

## Raw data is not yours

1. **`data/` holds raw data: never create, modify, move or delete anything in it.** If a value
   looks wrong, say so and let the human decide; do not correct it. Every file there is
   fingerprinted in `labharness.lock`, and the build reports any change.
   **Never run `labharness accept`**: accepting a change to raw data is the human's decision,
   not yours. Do not edit `labharness.lock` either.
2. **Never invent or "adjust" data.** Do not interpolate, smooth, fill in, or drop a point, a
   replicate or an experiment without an explicit request, even when it looks like an outlier.
   If you think it is one, say so and leave the decision to the human. If data is missing, ask.
3. **If a result does not support what the text claims, say so.** Never fit the text to the
   data, nor the data to the text.

## Numbers

4. **Never report more digits than the uncertainty justifies.** The uncertainty gets one or two
   significant figures and the value is rounded to the same decimal place: 92.347 ± 1.2 is
   written 92 ± 1. For a table, use `round()` and `with_uncertainty()` rather than retyping.
5. **Quote fitted values through their macros** (`\FitKineticsK`), never by copying the number:
   when the data changes, the text follows.
6. **Report a fit with its model, its parameters with their uncertainties, R² and the number of
   points.** If R² is poor or there are few points, say so.
7. **Do not linearise to fit** (logarithms, reciprocals) unless asked: fit the model as it is.
   Linearising distorts the error bars and biases the parameters.
8. **Units are SI or accepted in the field**, always through siunitx, and **never invent a unit
   that is not in the data.** If a column has no unit, ask. Quantities in italic, units upright:
   the style does it, do not force it by hand.

## How the workspace works

9. **Never edit `figures/` or `tables/` by hand.** They are produced by the scripts in
   `scripts/` and declared in `labharness.toml`.
10. A new figure means a script in `scripts/` plus its entry in `labharness.toml`. Create both
    with `labharness add <kind> <name> --input data/...` (kinds: `structure`, `plot`,
    `mechanism`, `flow`, `network`), then edit the script it writes. Add `--insert` only when
    the human asked for the figure to go into `paper.tex`.
11. **A table is written as it was given.** Read it with `read_table` and write it with
    `write_table`; apply only the operations the human asked for (rounding, uncertainties,
    columns), each as its own line, so the script shows what was done to the table.
12. **Never set fonts, sizes or colours** in a script or in a figure's `.tex` file. Everything
    comes from the shared style: one typeface for the whole document.
13. Keep scripts short, readable and runnable on their own. Start each one with a comment saying
    which figure or table it produces.
14. Do not rewrite the scientific text of `paper.tex` unless explicitly asked. Insert and update
    figures and tables; do not write the discussion.
15. **Look at a figure before calling it done.** A figure that builds can still read wrong.
    Run `labharness preview --only <name>` and open the PNG it writes; use `--document` to see
    it in place on the page.
