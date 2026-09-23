"""Finding the document typeface inside the installed LaTeX distribution.

Fonts are never bundled with LabHarness: the same file the document uses is the one the
figures use, so text and figures cannot drift apart.
"""

import shutil
import subprocess
from functools import cache
from pathlib import Path

from labharness.core.errors import LabHarnessError


@cache
def find_font_file(file_name: str, package: str = "lm") -> Path:
    """Locate a font shipped with the LaTeX distribution, e.g. ``lmroman10-regular.otf``.

    ``package`` is the distribution package that contains it, named in the error.
    """
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        raise LabHarnessError(
            "cannot find 'kpsewhich', so the document fonts cannot be located. "
            "Install a LaTeX distribution (MiKTeX or TeX Live) and make sure it is on PATH."
        )

    result = subprocess.run([kpsewhich, file_name], capture_output=True, text=True, check=False)
    path = Path(result.stdout.strip().splitlines()[0]) if result.stdout.strip() else None
    if path is None or not path.is_file():
        raise LabHarnessError(
            f"the font '{file_name}' is not installed in your LaTeX distribution. Install the "
            f"'{package}' package (MiKTeX console, or 'tlmgr install {package}' in TeX Live)."
        )
    return path
