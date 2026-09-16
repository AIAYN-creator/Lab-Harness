"""Core of LabHarness: module contract, registry, manifest and errors.

Modules may only depend on the public API exported here and in ``labharness.style``.
That rule is what makes ``labharness eject`` possible later on.
"""

from labharness.core.errors import LabHarnessError, MissingExtraError
from labharness.core.extras import require

__all__ = ["LabHarnessError", "MissingExtraError", "require"]
