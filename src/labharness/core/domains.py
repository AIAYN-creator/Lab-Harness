"""The modules LabHarness knows about: its own, and those a domain package brings.

Every module is registered the same way, under the ``labharness.modules`` entry point group:
the four that ship with LabHarness, and any a package for another field declares in its own
``pyproject.toml``. Nothing in the core names a module; it asks here (ADR 31).

A package also registers the kinds of figure ``labharness add`` offers, under
``labharness.figures``: the name of the kind points at a package, and its template is the file
``templates/<kind>.*`` inside it. And the fields whose agent rules ``labharness init`` copies,
under ``labharness.fields``: the rules of a field are ``AGENTS.<field>.md`` inside its package.
And the commands it adds to the command line, under ``labharness.commands``: a module with a
``register(app)`` function.
"""

from dataclasses import dataclass
from importlib import metadata, util
from pathlib import Path

from labharness.core.errors import LabHarnessError

GROUP = "labharness.modules"
FIGURES = "labharness.figures"
FIELDS = "labharness.fields"
COMMANDS = "labharness.commands"
# The modules that ship with LabHarness, for when it runs without its package metadata.
BUILT_IN = {
    "chem": "labharness.modules.chem",
    "diagrams": "labharness.modules.diagrams",
    "plots": "labharness.modules.plots",
    "tables": "labharness.modules.tables",
}
BUILT_IN_FIGURES = {
    "structure": BUILT_IN["chem"],
    "plot": BUILT_IN["plots"],
    "table": BUILT_IN["tables"],
    "mechanism": BUILT_IN["diagrams"],
    "flow": BUILT_IN["diagrams"],
    "network": BUILT_IN["diagrams"],
}
BUILT_IN_FIELDS = {"chemistry": BUILT_IN["chem"]}
BUILT_IN_COMMANDS = {"chemistry": f"{BUILT_IN['chem']}.commands"}


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
        return _folder(self.package)

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


@dataclass(frozen=True)
class FigureKind:
    """A kind of figure or table ``labharness add`` can start, and where its template is."""

    name: str
    package: str
    distribution: str

    def template(self) -> Path:
        found = sorted((_folder(self.package) / "templates").glob(f"{self.name}.*"))
        if not found:
            raise LabHarnessError(
                f"{self.package} registers the kind '{self.name}' but has no "
                f"templates/{self.name}.* to start it from"
            )
        return found[0]


def figure_kinds() -> dict[str, FigureKind]:
    """Every kind installed, by name. Two packages with the same kind are told apart as
    ``package:kind``, and neither is chosen by its plain name."""
    found = [
        FigureKind(point.name, point.value, point.dist.name if point.dist else "")
        for point in metadata.entry_points(group=FIGURES)
    ]
    if not found:
        found = [
            FigureKind(name, package, "labharness") for name, package in BUILT_IN_FIGURES.items()
        ]
    kinds: dict[str, FigureKind] = {}
    for kind in found:
        clashing = [other for other in found if other.name == kind.name]
        key = kind.name if len(clashing) == 1 else f"{kind.package}:{kind.name}"
        kinds[key] = kind
    return dict(sorted(kinds.items()))


@dataclass(frozen=True)
class Field:
    """A field whose rules for AI agents a workspace can carry, next to the general ones."""

    name: str
    package: str
    distribution: str

    def rules(self) -> Path:
        rules = _folder(self.package) / f"AGENTS.{self.name}.md"
        if not rules.is_file():
            raise LabHarnessError(
                f"{self.package} registers the field '{self.name}' but has no {rules.name}"
            )
        return rules


def fields() -> dict[str, Field]:
    """Every field installed, by name."""
    found = [
        Field(point.name, point.value, point.dist.name if point.dist else "")
        for point in metadata.entry_points(group=FIELDS)
    ]
    if not found:
        found = [Field(name, package, "labharness") for name, package in BUILT_IN_FIELDS.items()]
    return {field.name: field for field in sorted(found, key=lambda field: field.name)}


def command_modules() -> list[str]:
    """The modules that add commands to the command line, each with a ``register(app)``."""
    found = [point.value for point in metadata.entry_points(group=COMMANDS)]
    return sorted(found or BUILT_IN_COMMANDS.values())


def _folder(package: str) -> Path:
    spec = util.find_spec(package)
    if spec is None or not spec.submodule_search_locations:
        raise LabHarnessError(f"'{package}' is not installed")
    return Path(next(iter(spec.submodule_search_locations)))
