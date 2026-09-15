"""The `--json` contract, exercised the way agents run the CLI from this checkout.

Procedures and the autopilot parse `taskrail … --json` from stdout and act on the exit code.
An output wrapper around `uv run` once truncated that stdout into invalid JSON while keeping the
exit code, so these tests run the real `uv run taskrail` command in a subprocess and check the
bytes an agent would receive.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")


def uv_run(repo, *argv):
    return subprocess.run(
        ["uv", "run", "--quiet", "--directory", str(PROJECT), "taskrail", "--root", str(repo.root), *argv],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["show", "T002", "--json"], dict),
        (["list", "--json"], list),
        (["next", "--json"], list),
    ],
)
def test_json_stdout_is_complete_json_and_exit_code_is_zero(repo, argv, expected):
    result = uv_run(repo, *argv)

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert isinstance(data, expected)


def test_show_json_is_long_enough_to_catch_a_line_cap(repo):
    # A wrapper that keeps only the first and last lines of long output breaks JSON of this size.
    result = uv_run(repo, "show", "T002", "--json")

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("\n") > 60
    assert json.loads(result.stdout)["id"] == "T002"


def test_error_keeps_its_exit_code_and_stays_off_stdout(repo):
    result = uv_run(repo, "show", "T999", "--json")

    assert result.returncode == 3
    assert result.stdout == ""
    assert "T999" in result.stderr
