"""Command-line interface: a thin layer over the core, the watcher and the modules.

No figure logic lives here, so the same functions can be driven from anywhere else.
"""

from labharness.cli.app import app, main

__all__ = ["app", "main"]
