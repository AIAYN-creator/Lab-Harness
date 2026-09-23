"""The exact command that installs what is missing, on this machine.

``doctor`` never installs anything itself: installing software is the person's decision. What
it can do is print the one line to type, for the package manager this system actually has,
instead of a generic "install LaTeX".
"""

import platform
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class System:
    """Where LabHarness runs: the family of package managers that applies."""

    name: str  # windows, macos, debian, fedora, arch, linux
    label: str


def detect_system() -> System:
    if sys.platform == "win32":
        return System("windows", f"Windows {platform.release()}")
    if sys.platform == "darwin":
        return System("macos", f"macOS {platform.mac_ver()[0]}")
    release = _os_release()
    family = {release.get("ID", "")} | set(release.get("ID_LIKE", "").split())
    label = release.get("PRETTY_NAME", "Linux")
    for name in ("debian", "fedora", "arch"):
        if name in family or (name == "debian" and "ubuntu" in family):
            return System(name, label)
    return System("linux", label)


# What to type, per tool and per system. Missing entries fall back to "linux".
COMMANDS: dict[str, dict[str, str]] = {
    "latex": {
        "windows": "winget install MiKTeX.MiKTeX",
        "macos": "brew install --cask basictex   (then: sudo tlmgr install achemso chemfig "
        "standalone lm siunitx)",
        "debian": "sudo apt install texlive-latex-extra texlive-science "
        "texlive-fonts-recommended lmodern",
        "fedora": "sudo dnf install texlive-scheme-medium",
        "arch": "sudo pacman -S texlive-latexextra texlive-science texlive-fontsrecommended",
        "linux": "install TeX Live from your distribution, or from https://tug.org/texlive/",
    },
    "java": {
        "windows": "winget install EclipseAdoptium.Temurin.21.JRE",
        "macos": "brew install --cask temurin",
        "debian": "sudo apt install default-jre",
        "fedora": "sudo dnf install java-21-openjdk",
        "arch": "sudo pacman -S jre-openjdk",
        "linux": "install a Java runtime (Eclipse Temurin, OpenJDK) from your distribution",
    },
    "viewer": {
        "windows": "winget install SumatraPDF.SumatraPDF",
        "macos": "brew install --cask skim",
        "debian": "sudo apt install zathura zathura-pdf-poppler",
        "fedora": "sudo dnf install zathura-pdf-poppler",
        "arch": "sudo pacman -S zathura zathura-pdf-poppler",
        "linux": "any viewer that reloads on change: Zathura, Okular, Evince",
    },
    "rasteriser": {
        "windows": "it comes with MiKTeX: reinstall or update MiKTeX",
        "macos": "brew install poppler",
        "debian": "sudo apt install poppler-utils",
        "fedora": "sudo dnf install poppler-utils",
        "arch": "sudo pacman -S poppler",
        "linux": "install poppler-utils (pdftoppm) or Ghostscript",
    },
    "perl": {
        "windows": "winget install StrawberryPerl.StrawberryPerl",
        "linux": "perl comes with your distribution: install the 'perl' package",
    },
}


def command_for(tool: str, system: System | None = None) -> str:
    """The command that installs ``tool`` here."""
    system = system or detect_system()
    options = COMMANDS[tool]
    return options.get(system.name) or options.get("linux", "")


def tex_package_command(package: str, system: System | None = None) -> str:
    """How to add one package to the LaTeX distribution: MiKTeX on Windows, TeX Live elsewhere."""
    system = system or detect_system()
    if system.name == "windows":
        return f"miktex packages install {package}   (or the MiKTeX Console)"
    return f"sudo tlmgr install {package}"


def extra_command(extra: str) -> str:
    """How to add an extra, for the way this copy of LabHarness was installed."""
    prefix = Path(sys.prefix).as_posix().lower()
    if _running_from_a_checkout():
        return f"uv sync --extra {extra}"
    if "/uv/tools/" in prefix:
        return f'uv tool install --force "labharness[{extra}]"'
    if "/pipx/venvs/" in prefix:
        return f'pipx install --force "labharness[{extra}]"'
    return f'pip install "labharness[{extra}]"'


def _running_from_a_checkout() -> bool:
    """A source checkout has the repository's pyproject.toml three levels above the package."""
    here = Path(__file__).resolve()
    return (here.parents[2] / "pyproject.toml").is_file() and here.parents[1].name == "src"


def _os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        if key:
            values[key.strip()] = value.strip().strip('"')
    return values
