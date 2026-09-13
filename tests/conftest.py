from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from taskrail.config import load_config
from taskrail.project import load_project

BASE_CONFIG = """
version = "v0.1.0"

[[backlog]]
name = "main"
prefix = "T"
file = "TODO.md"

[columns]
custom = []

[checks]
test = "pytest"
lint = "ruff check"
"""

BASE_TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |

## E01 — Billing

Done when: every session has a cost.

| ✓  | ID   | Kind    | Pts | Depends On | Title          | Description |
|----|------|---------|-----|------------|----------------|-------------|
| ✅ | T001 | chore   | 2   | —          | Price table    | Base prices |
| ⬜ | T002 | feature | 3   | T001       | Repricing      | Recompute   |
| ⬜ | T003 | bug     | 1   | T002       | Rounding error | Off by one  |
"""


class Repo:
    def __init__(self, root: Path):
        self.root = root

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
        return path

    def load(self):
        return load_project(load_config(self.root))

    def codes(self, severity: str = "error") -> list[str]:
        _, issues = self.load()
        return [i.code for i in issues if i.severity == severity]


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    r.write(".taskrail/config.toml", BASE_CONFIG)
    r.write("TODO.md", BASE_TODO)
    return r


def git(root: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def git_repo(repo: Repo, monkeypatch) -> Repo:
    for key, value in {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    git(repo.root, "init", "-q", "-b", "main")
    git(repo.root, "add", "-A")
    git(repo.root, "commit", "-q", "-m", "init")
    return repo
