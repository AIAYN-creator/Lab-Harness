"""The modules LabHarness knows about: its own, and those a domain package brings.

Every module is registered the same way, under the ``labharness.modules`` entry point group:
the four that ship with LabHarness, and any a package for another field declares in its own
``pyproject.toml``. Nothing in the core names a module; it asks here (ADR 31).
"""

from dataclasses import dataclass
from importlib import metadata, util
from pathlib import Path

from labharness.core.errors import LabHarnessError

GROUP = "labharness.modules"
# The modules that ship with LabHarness, for when it runs without its package metadata.
BUILT_IN = {
    "chem": "labharness.modules.chem",
    "diagrams": "labharness.modules.diagrams",
    "plots": "labharness.modules.plots",
    "tables": "labharness.modules.tables",
}


@dataclass(frozen=True)
class Module:
    name: str  # "chem"
    package: str  # what a script imports: "labharness.modules.chem"
    distribution: str  # the package that installed it: "labharness"

    @property
    def built_in(self) -> bool:
        return self.package.startswith("labharness.modules.")

    def location(self) -> Path:
        """The folder the module's code is installed in."""
        spec = util.find_spec(self.package)
        if spec is None or not spec.submodule_search_locations:
            raise LabHarnessError(f"the module '{self.name}' ({self.package}) is not installed")
        return Path(next(iter(spec.submodule_search_locations)))

    def provides(self, imported: str) -> bool:
        """Whether an import of ``imported`` is an import of this module."""
        return imported == self.package or imported.startswith(f"{self.package}.")


def installed_modules() -> list[Module]:
    """Every module installed, LabHarness's own and those of domain packages, by name."""
    found = [
        Module(point.name, point.value, point.dist.name if point.dist else "")
        for point in metadata.entry_points(group=GROUP)
    ]
    if not found:
        found = [Module(name, package, "labharness") for name, package in BUILT_IN.items()]
    return sorted(found, key=lambda module: module.name)
