"""In a bare repository, task worktrees are read against and created in the directory holding it (T075).

An ordinary clone keeps its main checkout as that base; `worktree_base` reports it, absolute, the same
from every checkout.
"""

import json
from pathlib import Path

import pytest
from conftest import git

from taskrail import gitutil
from taskrail.cli import main

BARE_RUNNERS = ["sibling", "next to it", "inside the bare directory"]


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


@pytest.fixture
def bare(git_repo, tmp_path_factory):
    """A bare clone `layout/repo.git` with worktrees `layout/main`, `layout/T002-repricing` and `repo.git/T003-rounding-error`."""
    git_repo.write(".gitignore", ".worktrees/\n")
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "ignore worktrees")
    layout = tmp_path_factory.mktemp("layout").resolve()
    repository = layout / "repo.git"
    git(layout, "clone", "-q", "--bare", str(git_repo.root), str(repository))
    git(repository, "worktree", "add", "-q", str(layout / "main"), "main")
    git(repository, "worktree", "add", "-q", str(layout / "T002-repricing"), "-b", "T002-repricing", "main")
    git(repository, "worktree", "add", "-q", str(repository / "T003-rounding-error"), "-b", "T003-rounding-error", "main")
    runners = {
        "sibling": layout / "main",
        "next to it": layout / "T002-repricing",
        "inside the bare directory": repository / "T003-rounding-error",
    }
    return layout, runners


@pytest.fixture
def ordinary(git_repo):
    """An ordinary clone and a lane under its `.worktrees/`."""
    git_repo.write(".gitignore", ".worktrees/\n")
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "ignore worktrees")
    lane = git_repo.root / ".worktrees" / "T002-repricing"
    git(git_repo.root, "worktree", "add", "-q", str(lane), "-b", "T002-repricing")
    return git_repo.root.resolve(), {"main checkout": git_repo.root, "lane": lane}


@pytest.mark.parametrize("runner", BARE_RUNNERS)
def test_the_base_of_a_bare_repository_is_the_directory_holding_it(bare, runner):
    layout, runners = bare
    assert gitutil.main_worktree(runners[runner]) == layout


@pytest.mark.parametrize("runner", BARE_RUNNERS)
def test_show_and_list_read_worktrees_against_the_directory_holding_the_bare_repository(bare, runner, capsys):
    layout, runners = bare
    expected = {
        "T002": "T002-repricing",
        "T003": "repo.git/T003-rounding-error",
    }
    shown = {task: data(runners[runner], "show", task, capsys=capsys) for task in expected}
    assert {task: entry["worktree"] for task, entry in shown.items()} == expected
    assert {entry["worktree_base"] for entry in shown.values()} == {str(layout)}
    listed = data(runners[runner], "list", capsys=capsys)
    assert {entry["id"]: entry["worktree"] for entry in listed if entry["id"] in expected} == expected
    assert {entry["worktree_base"] for entry in listed} == {str(layout)}


@pytest.mark.parametrize("runner", BARE_RUNNERS)
def test_new_workspace_creates_the_worktree_outside_the_bare_directory(bare, runner, capsys):
    layout, runners = bare
    result = data(runners[runner], "new", "--epic", "E01", "--kind", "bug", "--title", "Placed", "--workspace", capsys=capsys)
    workspace = Path(result["workspace"])
    assert workspace == layout / ".worktrees" / result["branch"]
    shown = data(workspace, "show", result["id"], capsys=capsys)
    assert shown["worktree"] == f".worktrees/{result['branch']}"
    assert Path(shown["worktree_base"]) / shown["worktree"] == workspace


@pytest.mark.parametrize("runner", BARE_RUNNERS)
def test_workspace_refuses_a_path_taken_in_the_directory_holding_the_bare_repository(bare, runner, capsys):
    layout, runners = bare
    task = data(runners[runner], "new", "--epic", "E01", "--kind", "bug", "--title", "Taken", capsys=capsys)["id"]
    shown = data(runners[runner], "show", task, capsys=capsys)
    (layout / ".worktrees" / shown["branch"]).mkdir(parents=True)
    code, _, err = run(runners[runner], "workspace", task, "--json", capsys=capsys)
    assert code == 5, err
    assert "already exists" in err
    assert not git(runners[runner], "branch", "--list", shown["branch"])


@pytest.mark.parametrize("runner", ["main checkout", "lane"])
def test_an_ordinary_clone_reports_its_main_checkout_as_the_base(ordinary, runner, capsys):
    main_checkout, runners = ordinary
    shown = data(runners[runner], "show", "T002", capsys=capsys)
    assert (shown["worktree"], shown["worktree_base"]) == (".worktrees/T002-repricing", str(main_checkout))
    assert {entry["worktree_base"] for entry in data(runners[runner], "list", capsys=capsys)} == {str(main_checkout)}
    assert {entry["worktree_base"] for entry in data(runners[runner], "next", capsys=capsys)} == {str(main_checkout)}


def test_worktree_base_is_null_without_worktrees(ordinary, capsys):
    main_checkout, runners = ordinary
    config = main_checkout / ".taskrail" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + '\n[git]\nworktree = "never"\n', encoding="utf-8")
    shown = data(main_checkout, "show", "T002", capsys=capsys)
    assert (shown["worktree"], shown["worktree_base"]) == (None, None)
