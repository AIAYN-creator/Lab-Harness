# The LabHarness brand

![LabHarness](logo.svg)

**Everything LabHarness shows, LabHarness makes.** The logo is a TikZ diagram compiled by
LabHarness, the demo GIF is a real build, and every number on this page was measured. That is the
whole brand: the results speak, not the marketing.

## What we say

**From lab data to PDF in 1.3 seconds.**
*Change a number: the figure, the fit and the text follow.*

For posters at a Spanish-speaking faculty: **De los datos del laboratorio al PDF en 1,3 segundos.**
*Cambias un número: la figura, el ajuste y el texto se actualizan solos.*

The 1.3 s is measured, not promised: a changed measurement in a CSV, from saving the file to the
updated PDF, with the watcher running, on the author's laptop (see *How fast is it* in the
[README](../../README.md)). If the number changes, the tagline changes with it.

**Who it is for:** PhD students and science students who already write in LaTeX and redo their
figures by hand every time a measurement changes. Chemistry first. **Not yet** for anyone who
does not want to open a terminal, and we say so.

## How we say it

- **Show, do not promise.** Every claim comes with something to see: the GIF, a PDF, a measured
  time. Never *revolutionary*, *powerful*, *AI-powered*.
- **Short, plain, no exclamation marks.** Like a colleague at the next bench showing a trick.
- **Honest about what is missing.** It is alpha, and we say it.

## What we never do

- Stock photos, people smiling at laptops, purple gradients, glossy 3D icons.
- AI-generated images of "science", glowing flasks included.
- Numbers that were not measured, testimonials that were not given, university logos we have no
  permission to use.

## Colours

Two colours and black, taken from the palette the figures already use (Okabe-Ito), readable with
any colour vision deficiency. Everything must also work printed in black and white.

| Role | Colour | Hex |
|---|---|---|
| Brand, and the logo | Blue | `#0072B2` |
| Accent: what changed | Orange | `#E69F00` |
| Text | Black | `#000000` |
| Background | White | `#FFFFFF` |

## Typefaces

The ones LaTeX and LabHarness already use, free under the GUST Font License, with every TeX
distribution.

| Use | Typeface |
|---|---|
| Headings and the name | Latin Modern Sans, bold |
| Text | Latin Modern Roman |
| Commands and code | Latin Modern Mono |

## The logo

Three measurements and the curve that follows them; the one that just changed is orange.

| File | For |
|---|---|
| `logo.svg`, `logo.pdf`, `logo.png` | The mark and the name, on white |
| `logo-mono.*` | One colour: photocopies, stamps |
| `logo-negative.*` | White on the brand blue |
| `mark.*`, `mark-mono.*` | The mark alone |
| `mark-negative.png` | Avatars and social previews |
| `favicon.png` | 32 px |

Leave around it at least the width of one dot of the mark, and never stretch, recolour, outline
or put it on a photograph. To change it, edit and rerun the script that draws it:

```bash
uv run python tools/make_brand.py
```
