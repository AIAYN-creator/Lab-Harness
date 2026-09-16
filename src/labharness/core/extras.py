"""Lazy imports of optional dependencies, with an actionable error when they are missing."""

import importlib
from types import ModuleType

from labharness.core.errors import MissingExtraError


def require(package: str, extra: str) -> ModuleType:
    """Import ``package`` or explain which extra installs it.

    Modules call this inside their functions, never at import time, so that
    ``import labharness`` works with no extras installed.
    """
    try:
        return importlib.import_module(package)
    except ImportError as exc:
        raise MissingExtraError(extra, package) from exc
