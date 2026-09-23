"""``python -m labharness``: the same command line, for when ``labharness`` is not on PATH.

The git hook uses it, so it runs with the Python that installed LabHarness.
"""

from labharness.cli.app import main

main()
