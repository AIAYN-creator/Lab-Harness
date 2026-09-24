"""Make docs/assets/demo.gif, the loop at the top of the README.

The story, from raw data to a paper that follows it: the data is there, ``labharness add``
writes the figure script, the script is adjusted, ``labharness watch`` builds the figure into
the PDF, the text cites the fitted rate constant, and a changed measurement moves its point and
the number in the text.

Nothing in the page is mocked. Every step runs for real in a new workspace, the terminal shows
what LabHarness printed and the times it measured, and each page is rasterised from the PDF it
built. Only the editor and the terminal around the page are drawn.

    uv run python tools/make_readme_gif.py
"""

import contextlib
import io
import os
import shutil
import tempfile
import textwrap
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from typer.testing import CliRunner

from labharness.cli import app
from labharness.cli.app import _print_result
from labharness.core import load_workspace
from labharness.preview import preview_document
from labharness.style.fonts import find_font_file
from labharness.watch.runner import BuildResult, build

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "demo.gif"
WORKSPACE = "atenolol"

WIDTH, HEIGHT, BAR = 960, 540, 34
LEFT = 430  # width of the editor and terminal column
EDITOR_ROWS, EDITOR_COLUMNS = 11, 42
TERMINAL_ROWS, TERMINAL_COLUMNS = 10, 56

INK, PAPER, MUTED = (34, 34, 34), (255, 255, 255), (120, 120, 120)
EDITOR_BG, LINE_NO, CURRENT = (250, 250, 250), (170, 170, 170), (255, 243, 205)
TERMINAL_BG, TERMINAL_INK = (30, 30, 30), (220, 220, 220)
GREEN, RED, DESK, MARK = (120, 200, 120), (235, 110, 100), (225, 228, 232), (230, 120, 20)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(find_font_file(name)), size)


MONO, MONO_SMALL = font("lmmono10-regular.otf", 15), font("lmmono10-regular.otf", 12)
SANS, SANS_BOLD = font("lmsans10-regular.otf", 15), font("lmsans10-bold.otf", 16)
CHAR = MONO.getlength("m")

# What the person has before starting, and what they type along the way.
RESULTS = "\\section{Results}\n\nThe concentration of atenolol decays exponentially with time.\n\n"
SCRIPT_EDITS = [
    ('model="linear"', 'model="exp"'),
    ('x_label=("t", None),  # e.g. ("Time", "min")', 'x_label=("Time", "min"),'),
    ('y_label=("c", None)', 'y_label=("$C/C_0$", None)'),
]
PAPER_EDITS = [
    (
        "The concentration of atenolol decays exponentially with time.",
        "The concentration of atenolol decays exponentially with time, "
        "with $b = \\FitDecayB \\pm \\FitDecayBError$ min$^{-1}$.",
    ),
    (r"\caption{TODO: write the caption.}", r"\caption{Atenolol against time, exponential fit.}"),
]
DATA_EDIT = ("120;0,165", "120;0,265")


# --- running the story ---------------------------------------------------------------------


@dataclass
class Step:
    """One state of the story: the page as built, what was printed, how long the build took."""

    page: Image.Image
    printed: list[str]
    seconds: float = 0.0


@dataclass
class Story:
    steps: dict[str, Step]
    csv: list[str]  # the data file before the change
    script: list[str]  # the script as labharness add wrote it
    paper: list[str]  # the manuscript before the text cites the fit


def printed_by(result: BuildResult) -> list[str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        _print_result(result)
    return output.getvalue().splitlines()


def page_of(root: Path) -> Image.Image:
    preview = preview_document(load_workspace(root), dpi=150)
    assert preview.ok, preview.error
    return Image.open(preview.images[0]).convert("RGB")


def rebuilt(root: Path, changed: str) -> Step:
    """What the watcher does after a save of ``changed``, and what it prints."""
    workspace = load_workspace(root)
    figures = workspace.figures_affected_by(root / changed)
    result = build(workspace, figures=figures, quick=changed.startswith("data/"))
    assert result.ok, [figure.error for figure in result.figures]
    lines = ["", f"{time.strftime('%H:%M:%S')}  {Path(changed).name}", *printed_by(result)]
    return Step(page_of(root), lines, result.total_seconds)


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def run_story(root: Path) -> Story:
    runner = CliRunner()
    runner.invoke(app, ["init", str(root), "--journal", "article"])
    os.chdir(root)  # the commands run inside the workspace, as a person would run them
    shutil.copy(ROOT / "examples" / "demo" / "data" / "decay.csv", root / "data" / "decay.csv")
    paper = root / "paper.tex"
    text = paper.read_text(encoding="utf-8")
    # A short manuscript that cites nothing yet: a title and one sentence of results.
    text = text[: text.index(r"\section{Aim}")] + RESULTS + text[text.index(r"\end{document}") :]
    text = text.replace(r"\title{Title of the report}", r"\title{Anodic oxidation of atenolol}")
    text = text.replace(
        r"\begin{document}", "\\labresults{figures/decay.fit.tex}\n\n\\begin{document}"
    )
    paper.write_text(text, encoding="utf-8")
    csv = (root / "data" / "decay.csv").read_text(encoding="utf-8").splitlines()

    steps: dict[str, Step] = {}
    build(load_workspace(root))
    steps["data"] = Step(page_of(root), [])

    added = runner.invoke(app, ["add", "plot", "decay", "--input", "data/decay.csv", "--insert"])
    steps["add"] = Step(steps["data"].page, added.stdout.splitlines())
    script = (root / "scripts" / "decay.py").read_text(encoding="utf-8").splitlines()
    for old, new in SCRIPT_EDITS:
        replace(root / "scripts" / "decay.py", old, new)

    first = build(load_workspace(root))
    assert first.ok, [figure.error for figure in first.figures]
    watching = [*printed_by(first), "Waiting for changes."]
    steps["watch"] = Step(page_of(root), watching, first.total_seconds)

    manuscript = paper.read_text(encoding="utf-8").splitlines()
    for old, new in PAPER_EDITS:
        replace(paper, old, new)
    steps["cite"] = rebuilt(root, "paper.tex")

    replace(root / "data" / "decay.csv", *DATA_EDIT)
    steps["change"] = rebuilt(root, "data/decay.csv")
    return Story(steps, csv, script, manuscript)


# --- drawing -------------------------------------------------------------------------------


@dataclass
class Screen:
    """Everything on screen at one moment."""

    file: str
    lines: list[str]
    first: int  # the first line of the file the editor shows
    page: Image.Image
    step: str
    terminal: list[tuple[str, bool]] = field(default_factory=list)
    cursor: tuple[int, int] | None = None  # (line, column)
    saved: bool = True
    marks: list[tuple[int, int, int, int]] = field(default_factory=list)


def wrapped(line: str) -> list[str]:
    return [line[i : i + EDITOR_COLUMNS] for i in range(0, len(line), EDITOR_COLUMNS)] or [""]


def draw(screen: Screen, crop: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), DESK)
    pen = ImageDraw.Draw(image)

    pen.rectangle((0, 0, WIDTH, BAR), fill=INK)
    pen.text((14, 8), "LabHarness", font=SANS_BOLD, fill=PAPER)
    pen.text((112, 9), "raw data in, a paper that follows it out", font=SANS, fill=(170, 170, 170))
    width = pen.textlength(screen.step, font=SANS_BOLD)
    pen.text((WIDTH - 14 - width, 8), screen.step, font=SANS_BOLD, fill=(255, 196, 120))

    # Editor, with long lines wrapped the way an editor wraps them.
    top, bottom = BAR + 10, BAR + 10 + 30 + EDITOR_ROWS * 20
    pen.rectangle((10, top, LEFT, bottom), fill=EDITOR_BG, outline=(210, 210, 210))
    title = screen.file + ("" if screen.saved else "  ●")
    pen.text((22, top + 7), title, font=MONO_SMALL, fill=MUTED)
    row = 0
    for number in range(screen.first, len(screen.lines)):
        parts = wrapped(screen.lines[number])
        if row + len(parts) > EDITOR_ROWS:
            break
        y = top + 30 + row * 20
        if screen.cursor is not None and screen.cursor[0] == number:
            pen.rectangle((12, y - 2, LEFT - 2, y + 20 * len(parts) - 3), fill=CURRENT)
            column = screen.cursor[1]
            x = 50 + (column % EDITOR_COLUMNS) * CHAR
            cursor_y = y + (column // EDITOR_COLUMNS) * 20
            pen.line((x + 1, cursor_y, x + 1, cursor_y + 17), fill=INK, width=2)
        pen.text((20, y + 2), f"{number + 1:>2}", font=MONO_SMALL, fill=LINE_NO)
        for offset, part in enumerate(parts):
            pen.text((50, y + offset * 20), part, font=MONO, fill=INK)
        row += len(parts)

    # Terminal: the last lines that fit.
    top = bottom + 10
    pen.rectangle((10, top, LEFT, HEIGHT - 10), fill=TERMINAL_BG)
    for number, (line, warning) in enumerate(screen.terminal[-TERMINAL_ROWS:]):
        colour = RED if warning else GREEN if line.startswith("$") else TERMINAL_INK
        pen.text((20, top + 8 + number * 16), line, font=MONO_SMALL, fill=colour)

    # The page, as large as the column allows, with what changed marked on it.
    page = screen.page.crop(crop)
    area = (LEFT + 14, BAR + 10, WIDTH - 10, HEIGHT - 26)
    scale = min((area[2] - area[0]) / page.width, (area[3] - area[1]) / page.height)
    shown = page.resize((round(page.width * scale), round(page.height * scale)), Image.LANCZOS)
    x = area[0] + (area[2] - area[0] - shown.width) // 2
    image.paste(shown, (x, area[1]))
    pen.rectangle((x - 1, area[1] - 1, x + shown.width, area[1] + shown.height), outline=MUTED)
    for left, upper, right, lower in screen.marks:
        box = (
            x + (left - crop[0]) * scale - 5,
            area[1] + (upper - crop[1]) * scale - 4,
            x + (right - crop[0]) * scale + 5,
            area[1] + (lower - crop[1]) * scale + 4,
        )
        pen.rounded_rectangle(box, radius=6, outline=MARK, width=3)
    pen.text((x, area[1] + shown.height + 4), "paper.pdf", font=MONO_SMALL, fill=MUTED)
    return image


def terminal(lines: list[str]) -> list[tuple[str, bool]]:
    """Lines wrapped to the terminal, each with whether LabHarness prints it in red."""
    out = []
    for line in lines:
        warning = "changed since it was accepted" in line
        indent = " " * (len(line) - len(line.lstrip()) + 2)
        for part in textwrap.wrap(line, TERMINAL_COLUMNS, subsequent_indent=indent) or [""]:
            out.append((part.replace("\\", "/"), warning))
    return out


def content_box(start: Image.Image, end: Image.Image) -> tuple[int, int, int, int]:
    """The part of the page the story happens in: from the Results heading to the figure.

    The heading is the last block of text but one on the page the story starts from, whose
    last block is the sentence of results. The title above it is left out, so the text the
    story changes is shown as large as it can be.
    """
    margin = 24
    rows = _ink_rows(start)
    blocks = numpy.split(rows, numpy.nonzero(numpy.diff(rows) > 8)[0] + 1)
    top = int(blocks[-2][0]) - margin
    ink = numpy.asarray(end.convert("L")) < 200
    ink[int(ink.shape[0] * 0.9) :] = False  # the page number
    columns, bottom = numpy.nonzero(ink.any(axis=0))[0], int(_ink_rows(end)[-1])
    return int(columns[0]) - margin, top, int(columns[-1]) + margin, bottom + margin


def _ink_rows(page: Image.Image) -> numpy.ndarray:
    ink = numpy.asarray(page.convert("L")) < 200
    ink[int(ink.shape[0] * 0.9) :] = False
    return numpy.nonzero(ink.any(axis=1))[0]


def changes(before: Image.Image, after: Image.Image) -> list[tuple[int, int, int, int]]:
    """Where the page changed in a way a reader notices: a moved point, a new number.

    New ink is sorted by how solid it is. A plotted point is a solid dot. Digits are less
    solid, and each patch of them is widened to the whole number it belongs to. The thin
    slivers of a curve that moved by a pixel are hardly solid at all, and are left out.
    """
    ink = numpy.asarray(after.convert("L")) < 128
    new_ink = ink & (numpy.asarray(before.convert("L")) > 200)
    labels, _ = ndimage.label(ndimage.binary_dilation(new_ink, iterations=6))
    boxes: list[tuple[int, int, int, int]] = []
    for region in ndimage.find_objects(labels):
        rows, columns = numpy.nonzero(new_ink[region])
        if len(rows) < 15:
            continue
        top, bottom = region[0].start + rows.min(), region[0].start + rows.max() + 1
        left, right = region[1].start + columns.min(), region[1].start + columns.max() + 1
        solid = len(rows) / ((bottom - top) * (right - left))
        if solid < 0.1:
            continue  # a sliver of the curve
        if solid < 0.5:  # digits
            left, right = _word(ink[top:bottom], left, right)
        boxes.append((left, top, right, bottom))
    return _merged(boxes)


def _merged(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Boxes that overlap, such as two changed digits of one number, become one."""
    merged: list[tuple[int, int, int, int]] = []
    for box in sorted(boxes):
        if (
            merged
            and box[0] <= merged[-1][2]
            and box[1] <= merged[-1][3]
            and box[3] >= merged[-1][1]
        ):
            last = merged.pop()
            box = (last[0], min(last[1], box[1]), max(last[2], box[2]), max(last[3], box[3]))
        merged.append(box)
    return merged


def _word(band: numpy.ndarray, left: int, right: int, gap: int = 5) -> tuple[int, int]:
    """Widen [left, right) along a line of text until a space as wide as ``gap`` pixels."""
    inked = band.any(axis=0)
    while left > 0 and inked[max(0, left - gap) : left].any():
        left -= 1
    while right < len(inked) and inked[right : right + gap].any():
        right += 1
    return left, right


# --- the animation -------------------------------------------------------------------------


def typing(old: str, new: str) -> Iterator[tuple[str, int]]:
    """The line as it is edited from ``old`` to ``new``, a key at a time, and the cursor."""
    start = 0
    while start < min(len(old), len(new)) and old[start] == new[start]:
        start += 1
    end = 0
    while end < min(len(old), len(new)) - start and old[-1 - end] == new[-1 - end]:
        end += 1
    tail = old[len(old) - end :]
    for cut in range(len(old) - end, start - 1, -1):
        yield old[:cut] + tail, cut
    for count in range(1, len(new) - end - start + 1):
        yield new[: start + count] + tail, start + count


class Film:
    def __init__(self, crop: tuple[int, int, int, int]) -> None:
        self.crop = crop
        self.frames: list[tuple[Image.Image, int]] = []
        self.shell: list[str] = []

    def show(self, screen: Screen, milliseconds: int) -> None:
        self.frames.append((draw(screen, self.crop), milliseconds))

    def command(self, screen: Screen, text: str) -> None:
        for count in range(0, len(text) + 1, 2):
            screen.terminal = terminal([*self.shell, f"$ {text[:count]}"])
            self.show(screen, 50)
        self.shell.append(f"$ {text}")

    def edit(self, screen: Screen, edits: list[tuple[str, str]], milliseconds: int) -> None:
        for old, new in edits:
            number = next(i for i, line in enumerate(screen.lines) if old in line)
            line = screen.lines[number]
            for typed, column in typing(line, line.replace(old, new)):
                screen.lines[number], screen.cursor, screen.saved = typed, (number, column), False
                self.show(screen, milliseconds)
        screen.saved = True

    def rebuild(self, screen: Screen, step: Step) -> None:
        """The watcher's pause while it rebuilds, then its output and the new page together."""
        self.show(screen, round(step.seconds * 1000))
        self.shell.extend(step.printed)
        screen.page, screen.terminal, screen.cursor = step.page, terminal(self.shell), None


def main() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        here = Path.cwd()
        try:
            os.chdir(scratch)
            story = run_story(Path(scratch) / WORKSPACE)
        finally:
            os.chdir(here)
    steps = story.steps
    film = Film(content_box(steps["data"].page, steps["change"].page))

    # 1. The data is there.
    screen = Screen("data/decay.csv", list(story.csv), 0, steps["data"].page, "1  your data")
    film.show(screen, 1800)

    # 2. labharness add writes the script, its manifest entry and the figure block.
    screen.step = "2  labharness add"
    film.command(screen, "labharness add plot decay --input data/decay.csv --insert")
    film.shell.extend(steps["add"].printed)
    screen.terminal = terminal(film.shell)
    film.show(screen, 1500)

    # 3. The script is adjusted: an exponential model, and the axis labels.
    screen = Screen(
        "scripts/decay.py",
        list(story.script),
        6,
        screen.page,
        "3  adjust the script",
        screen.terminal,
    )
    film.show(screen, 900)
    film.edit(screen, SCRIPT_EDITS, 45)
    film.show(screen, 600)

    # 4. labharness watch builds the figure into the PDF.
    screen.step, screen.cursor = "4  labharness watch", None
    film.shell.clear()
    film.command(screen, "labharness watch")
    film.shell.append(f"Watching {WORKSPACE}")  # printed before the first build starts
    screen.terminal = terminal(film.shell)
    film.rebuild(screen, steps["watch"])
    film.show(screen, 2500)

    # 5. The text cites the fitted rate constant, and the caption is written.
    first = next(i for i, line in enumerate(story.paper) if line.startswith(r"\section{Results}"))
    screen = Screen(
        "paper.tex", list(story.paper), first, screen.page, "5  cite the fit", screen.terminal
    )
    film.show(screen, 700)
    film.edit(screen, PAPER_EDITS, 30)
    film.rebuild(screen, steps["cite"])
    film.show(screen, 2500)

    # 6. A measurement changes: its point moves, and so does the number in the text.
    screen = Screen(
        "data/decay.csv", list(story.csv), 0, screen.page, "6  change a number", screen.terminal
    )
    film.show(screen, 700)
    film.edit(screen, [DATA_EDIT], 140)
    film.rebuild(screen, steps["change"])
    film.show(screen, 700)
    screen.marks = changes(steps["cite"].page, steps["change"].page)
    film.show(screen, 4500)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    images = [
        image.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for image, _ in film.frames
    ]
    images[0].save(
        OUTPUT,
        save_all=True,
        append_images=images[1:],
        duration=[milliseconds for _, milliseconds in film.frames],
        loop=0,
        optimize=True,
    )
    seconds = sum(milliseconds for _, milliseconds in film.frames) / 1000
    print(
        f"{OUTPUT.relative_to(ROOT).as_posix()}: {len(film.frames)} frames, {seconds:.0f} s, "
        f"{OUTPUT.stat().st_size / 1e6:.1f} MB, {len(screen.marks)} marks"
    )


if __name__ == "__main__":
    main()
