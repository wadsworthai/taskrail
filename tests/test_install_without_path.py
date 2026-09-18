"""The documented default install route, run with `taskrail` absent from PATH.

README's *Install* and DESIGN.md §9 make the no-global-install route the default: `uvx` runs a
release once to bootstrap a repository, and the wrapper `init` commits runs taskrail from then on,
with `uv` as the only prerequisite. Proving that needs a PATH that holds `uv` but no `taskrail` —
a machine usually keeps both in the same directory — so this test builds one.

It covers the wrapper's `local:` pin, not its `uvx` fallback: that branch runs
`uvx --from git+<url>@<pin>`, which fetches the repository over the network on every call, and a
test must not reach the network. What is left uncovered is that transport alone; everything the
route needs before it — `init` run as its own process without `taskrail` on PATH, and the wrapper
resolving the pin and running taskrail on that same PATH — is exercised here.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import git

from taskrail import install

PROJECT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")


def path_with_uv_but_no_taskrail(tmp_path: Path) -> str:
    """A PATH with `uv`, the system directories the wrapper's shell needs, and no `taskrail`."""
    bin_dir = tmp_path / "path-bin"
    bin_dir.mkdir()
    (bin_dir / "uv").symlink_to(shutil.which("uv"))
    path = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
    if shutil.which("taskrail", path=path) is not None:
        pytest.skip("taskrail is installed in /usr/bin or /bin")
    return path


def test_init_and_the_wrapper_run_with_taskrail_absent_from_path(tmp_path, monkeypatch):
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("TASKRAIL_BIN", raising=False)  # it would bypass the wrapper entirely
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    env = {**os.environ, "PATH": path_with_uv_but_no_taskrail(tmp_path)}
    # The suite itself runs inside this project's virtual environment, which has a taskrail entry
    # point; uv would run that one whatever the pin says, and the route would prove nothing.
    env.pop("VIRTUAL_ENV", None)

    # Bootstrap: what `uvx --from git+<url>@<tag> taskrail init` does, from this checkout instead.
    bootstrap = subprocess.run(
        ["uv", "run", "--quiet", "--directory", str(PROJECT), "taskrail", "--root", str(repo), "init"],
        capture_output=True, text=True, env=env, timeout=120,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr
    wrapper = repo / install.WRAPPER
    assert os.access(wrapper, os.X_OK)

    # Pin this checkout's source, the one resolution that needs no network, and call the wrapper.
    (repo / "vendor-taskrail").symlink_to(PROJECT)
    config = repo / ".taskrail/config.toml"
    config.write_text(config.read_text().replace(f'"{install.release_tag()}"', '"local:vendor-taskrail"'))
    result = subprocess.run(
        [str(wrapper), "validate"], cwd=repo, capture_output=True, text=True, env=env, timeout=120
    )

    assert result.returncode == 0, result.stderr
    assert "0 error(s)" in result.stdout
