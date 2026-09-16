"""Opening the PDF in a viewer that reloads on change and does not lock the file."""

import platform
import shutil
import subprocess
from pathlib import Path

WINDOWS_VIEWER = "SumatraPDF.exe"
MACOS_VIEWER = "Skim"


def find_viewer() -> Path | None:
    """The PDF viewer to use on this machine, if one is installed."""
    system = platform.system()

    if system == "Windows":
        on_path = shutil.which(WINDOWS_VIEWER)
        if on_path:
            return Path(on_path)
        for folder in (
            Path.home() / "AppData/Local/SumatraPDF",
            Path("C:/Program Files/SumatraPDF"),
            Path("C:/Program Files (x86)/SumatraPDF"),
        ):
            candidate = folder / WINDOWS_VIEWER
            if candidate.is_file():
                return candidate
        return None

    if system == "Darwin":
        app = Path("/Applications") / f"{MACOS_VIEWER}.app"
        return app if app.exists() else None

    xdg = shutil.which("xdg-open")
    return Path(xdg) if xdg else None


def open_pdf(pdf: Path) -> bool:
    """Open ``pdf`` in that viewer. Returns False if there is nothing to open it with."""
    viewer = find_viewer()
    if viewer is None:
        return False

    system = platform.system()
    if system == "Windows":
        # -reuse-instance keeps a single window, which is what makes the live reload look
        # seamless during a demo.
        command = [str(viewer), "-reuse-instance", str(pdf)]
    elif system == "Darwin":
        command = ["open", "-a", MACOS_VIEWER, str(pdf)]
    else:
        command = [str(viewer), str(pdf)]

    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
