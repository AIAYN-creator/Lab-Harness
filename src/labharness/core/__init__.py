"""Core of LabHarness: module contract, manifest, workspace and errors.

Modules may only depend on the public API exported here and in ``labharness.style``.
That rule is what makes ``labharness eject`` possible later on.
"""

from labharness.core.errors import LabHarnessError, LabHarnessWarning, MissingExtraError
from labharness.core.extras import require
from labharness.core.manifest import Figure, Workspace, find_workspace, load_workspace
from labharness.core.workspace import create_workspace

__all__ = [
    "Figure",
    "LabHarnessError",
    "LabHarnessWarning",
    "MissingExtraError",
    "Workspace",
    "create_workspace",
    "find_workspace",
    "load_workspace",
    "require",
]
