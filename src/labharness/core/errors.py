"""Exception hierarchy shared by every part of LabHarness."""


class LabHarnessError(Exception):
    """Base class for every error raised by LabHarness."""


class LabHarnessWarning(UserWarning):
    """Something a person should know about a figure that still built.

    Modules emit these with :func:`warnings.warn`; the watcher collects them and prints them
    next to the figure, so they are seen even when the script ignores its return value.
    """


class MissingExtraError(LabHarnessError, ImportError):
    """A feature needs an optional extra that is not installed."""

    def __init__(self, extra: str, package: str) -> None:
        super().__init__(
            f"This feature needs the '{extra}' extra (missing package: {package}). "
            f'Install it with: uv sync --extra {extra}   or   pip install "labharness[{extra}]"'
        )
        self.extra = extra
        self.package = package
