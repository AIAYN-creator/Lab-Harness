"""LabHarness: a local-first Data-to-Paper harness.

The package is organised as a thin core plus independent modules:

- ``labharness.core``: module contract, registry, manifest and errors.
- ``labharness.style``: the shared style (one typeface for the whole document).
- ``labharness.watch``: the event-driven orchestrator.
- ``labharness.cli``: the command-line interface, a thin layer over the above.
- ``labharness.modules``: one subpackage per domain, each behind an optional extra.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("labharness")
except PackageNotFoundError:  # running from a source checkout that is not installed
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
