"""taskrail: an agent-agnostic backlog tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    # pyproject.toml is the only place the version is written.
    __version__ = version("taskrail")
except PackageNotFoundError:  # a source tree that was never installed
    __version__ = "0.0.0+unknown"
