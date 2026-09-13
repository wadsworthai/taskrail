import re
import tomllib
from pathlib import Path

from taskrail import __version__
from taskrail.install import release_tag


def test_the_package_version_comes_from_pyproject():
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert __version__ == pyproject["project"]["version"]


def test_the_release_tag_is_the_version_without_its_development_suffix():
    release = re.match(r"^\d+\.\d+\.\d+", __version__).group(0)
    assert release_tag() == f"v{release}"
