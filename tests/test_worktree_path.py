"""A task's `worktree` is one path, relative to the main checkout, whichever checkout runs the command (T072)."""

import json
import os

import pytest
from conftest import git

from taskrail.cli import main

TODO = """
# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | Demo | Try paths | —    |

## E01 — Demo

| ✓  | ID   | Kind    | Pts | Depends On | Title   | Description |
|----|------|---------|-----|------------|---------|-------------|
| ⬜ | T001 | feature | 1   | —          | Wanted  | —           |
| ⬜ | T002 | feature | 1   | —          | Nested  | —           |
| ⬜ | T003 | feature | 1   | —          | Outside | —           |
"""


def data(root, *argv, capsys):
    code = main(["--root", str(root), *argv, "--json"])
    out, err = capsys.readouterr()
    assert code == 0, err
    return json.loads(out)


@pytest.fixture
def checkouts(git_repo, tmp_path_factory):
    """The main checkout, a worktree under `.worktrees/` and one outside the repository."""
    git_repo.write("TODO.md", TODO)
    git_repo.write(".gitignore", ".worktrees/\n")
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "backlog")
    nested = git_repo.root / ".worktrees" / "T002-nested"
    outside = tmp_path_factory.mktemp("elsewhere") / "T003-outside"
    git(git_repo.root, "worktree", "add", "-q", str(nested), "-b", "T002-nested")
    git(git_repo.root, "worktree", "add", "-q", str(outside), "-b", "T003-outside")
    expected = {
        "T001": ".worktrees/T001-wanted",  # not created yet
        "T002": ".worktrees/T002-nested",
        "T003": os.path.relpath(outside.resolve(), git_repo.root.resolve()),
    }
    assert expected["T003"].startswith("..")
    return {"main checkout": git_repo.root, "nested worktree": nested, "outside worktree": outside}, expected


@pytest.mark.parametrize("runner", ["main checkout", "nested worktree", "outside worktree"])
def test_show_reports_the_same_worktree_from_every_checkout(checkouts, runner, capsys):
    roots, expected = checkouts
    got = {task: data(roots[runner], "show", task, capsys=capsys)["worktree"] for task in expected}
    assert got == expected


@pytest.mark.parametrize("runner", ["main checkout", "nested worktree", "outside worktree"])
def test_list_reports_the_same_worktree_from_every_checkout(checkouts, runner, capsys):
    roots, expected = checkouts
    got = {entry["id"]: entry["worktree"] for entry in data(roots[runner], "list", capsys=capsys)}
    assert got == expected
