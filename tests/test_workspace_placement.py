"""`new --workspace` and `workspace` create a task's worktree under the main checkout, from any checkout (T073)."""

import json
from pathlib import Path

import pytest
from conftest import git

from taskrail.cli import main

RUNNERS = ["main checkout", "lane"]


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


@pytest.fixture
def checkouts(git_repo):
    """The main checkout and a lane: a task worktree under its `.worktrees/`."""
    git_repo.write(".gitignore", ".worktrees/\n")
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "ignore worktrees")
    lane = git_repo.root / ".worktrees" / "T002-lane"
    git(git_repo.root, "worktree", "add", "-q", str(lane), "-b", "T002-lane")
    return {"main checkout": git_repo.root, "lane": lane}


def expected_path(checkouts, branch):
    return (checkouts["main checkout"] / ".worktrees" / branch).resolve()


def add_row_here(root, title, capsys):
    """A row written only in this checkout, uncommitted: its base does not have it."""
    return data(root, "new", "--epic", "E01", "--kind", "bug", "--title", title, capsys=capsys)["id"]


@pytest.mark.parametrize("runner", RUNNERS)
def test_new_workspace_creates_the_worktree_under_the_main_checkout(checkouts, runner, capsys):
    result = data(checkouts[runner], "new", "--epic", "E01", "--kind", "bug", "--title", "Placed", "--workspace", capsys=capsys)
    workspace = Path(result["workspace"])
    assert workspace == expected_path(checkouts, result["branch"])
    assert git(workspace, "branch", "--show-current") == result["branch"]
    assert data(workspace, "show", result["id"], capsys=capsys)["worktree"] == f".worktrees/{result['branch']}"


@pytest.mark.parametrize("runner", RUNNERS)
def test_workspace_creates_the_worktree_under_the_main_checkout(checkouts, runner, capsys):
    task = add_row_here(checkouts[runner], "Moved", capsys)
    before = data(checkouts[runner], "show", task, capsys=capsys)
    result = data(checkouts[runner], "workspace", task, capsys=capsys)
    workspace = Path(result["workspace"])
    assert workspace == expected_path(checkouts, result["branch"])
    assert workspace == (checkouts["main checkout"] / before["worktree"]).resolve()
    assert data(workspace, "show", task, capsys=capsys)["worktree"] == before["worktree"]


@pytest.mark.parametrize("runner", RUNNERS)
def test_new_workspace_refuses_a_path_taken_under_the_main_checkout(checkouts, runner, capsys):
    expected_path(checkouts, "T004-taken").mkdir(parents=True)
    argv = ["new", "--epic", "E01", "--kind", "bug", "--title", "Taken", "--workspace", "--branch", "T004-taken", "--json"]
    code, _, err = run(checkouts[runner], *argv, capsys=capsys)
    assert code == 5, err
    assert "already exists" in err
    assert not git(checkouts["main checkout"], "branch", "--list", "T004-taken")


@pytest.mark.parametrize("runner", RUNNERS)
def test_workspace_refuses_a_path_taken_under_the_main_checkout(checkouts, runner, capsys):
    task = add_row_here(checkouts[runner], "Taken", capsys)
    branch = data(checkouts[runner], "show", task, capsys=capsys)["branch"]
    expected_path(checkouts, branch).mkdir(parents=True)
    code, _, err = run(checkouts[runner], "workspace", task, "--json", capsys=capsys)
    assert code == 5, err
    assert "already exists" in err
    assert not git(checkouts["main checkout"], "branch", "--list", branch)
