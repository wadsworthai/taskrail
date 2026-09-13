import tomllib
from pathlib import Path

from taskrail import __version__
from taskrail.install import release_tag


def test_the_package_version_comes_from_pyproject():
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert __version__ == pyproject["project"]["version"]


def test_the_release_tag_matches_the_version():
    assert release_tag() == f"v{__version__}"
