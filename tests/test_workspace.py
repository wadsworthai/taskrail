import json
from pathlib import Path

import pytest
from conftest import BASE_TODO, git

from taskrail.cli import main
from taskrail.config import load_config
from taskrail.kinds import load_kinds

BRANCH = "T004-negative-totals"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def new_in_workspace(root, *extra, capsys, expect=0):
    code, out, err = run(
        root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals", "--workspace", "--json", *extra, capsys=capsys
    )
    assert code == expect, err
    return (json.loads(out) if out.strip() else None), err


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


@pytest.fixture
def remote_repo(git_repo, tmp_path_factory):
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare
    return git_repo


def advance_remote(repo, tmp_path_factory, todo=None):
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(repo.root, "clone", "-q", str(repo.bare), str(clone))
    if todo is not None:
        (clone / "TODO.md").write_text(todo)
    else:
        (clone / "NOTES.md").write_text("elsewhere\n")
    commit_all(clone, "remote change")
    git(clone, "push", "-q", "origin", "main")
    git(repo.root, "fetch", "-q", "origin")


def test_show_reports_the_base(remote_repo, tmp_path_factory, capsys):
    data = json.loads(run(remote_repo.root, "show", "T002", "--json", capsys=capsys)[1])
    assert data["base"] == {"onto": "origin/main", "diverged": False, "reason": "origin/main is up to date with or ahead of main"}
    advance_remote(remote_repo, tmp_path_factory)
    assert json.loads(run(remote_repo.root, "show", "T002", "--json", capsys=capsys)[1])["base"]["onto"] == "origin/main"
    assert "base origin/main" in run(remote_repo.root, "show", "T002", capsys=capsys)[1]


def test_show_base_without_a_remote_or_git(git_repo, repo, capsys):
    data = json.loads(run(git_repo.root, "show", "T002", "--json", capsys=capsys)[1])
    assert data["base"]["onto"] == "main"


def test_show_base_outside_git_is_null(repo, capsys):
    assert json.loads(run(repo.root, "show", "T002", "--json", capsys=capsys)[1])["base"] is None


def test_workspace_creates_the_worktree_and_writes_the_row_there(remote_repo, capsys):
    before = (remote_repo.root / "TODO.md").read_text()
    data, _ = new_in_workspace(remote_repo.root, capsys=capsys)
    workspace = Path(data["workspace"])
    assert (data["id"], data["branch"], data["base"]) == ("T004", BRANCH, "origin/main")
    assert workspace == (remote_repo.root / ".worktrees" / BRANCH).resolve()
    assert git(workspace, "branch", "--show-current") == BRANCH
    assert "| ⬜ | T004 | bug" in (workspace / "TODO.md").read_text()
    assert (remote_repo.root / "TODO.md").read_text() == before
    assert git(remote_repo.root, "status", "--porcelain", "--", "TODO.md") == ""
    assert run(workspace, "claim", "T004", "--owner", "alice", capsys=capsys)[0] == 0


def test_workspace_branches_from_the_remote_when_it_is_ahead(remote_repo, tmp_path_factory, capsys):
    advance_remote(remote_repo, tmp_path_factory, todo=BASE_TODO.replace("| Off by one  |", "| Off by two  |"))
    data, _ = new_in_workspace(remote_repo.root, capsys=capsys)
    text = (Path(data["workspace"]) / "TODO.md").read_text()
    assert "Off by two" in text and "| T004 |" in text


def test_workspace_in_this_checkout_when_worktrees_are_off(git_repo, capsys):
    config = git_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + '\n[git]\nworktree = "never"\n')
    commit_all(git_repo.root, "no worktrees")
    data, _ = new_in_workspace(git_repo.root, capsys=capsys)
    assert Path(data["workspace"]) == git_repo.root
    assert git(git_repo.root, "branch", "--show-current") == BRANCH
    assert "| T004 |" in (git_repo.root / "TODO.md").read_text()


def test_workspace_refuses_a_dirty_checkout_when_worktrees_are_off(git_repo, capsys):
    config = git_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + '\n[git]\nworktree = "never"\n')
    _, err = new_in_workspace(git_repo.root, capsys=capsys, expect=5)
    assert "uncommitted changes" in err
    assert git(git_repo.root, "branch", "--show-current") == "main"


def test_workspace_refuses_an_existing_branch_and_frees_the_id(git_repo, capsys):
    git(git_repo.root, "branch", BRANCH)
    _, err = new_in_workspace(git_repo.root, capsys=capsys, expect=5)
    assert f"branch {BRANCH} already exists" in err
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_workspace_refuses_diverged_mainlines(remote_repo, tmp_path_factory, capsys):
    advance_remote(remote_repo, tmp_path_factory)
    (remote_repo.root / "LOCAL.md").write_text("local\n")
    commit_all(remote_repo.root, "local change")
    _, err = new_in_workspace(remote_repo.root, capsys=capsys, expect=5)
    assert "have diverged" in err
    assert not (remote_repo.root / ".worktrees").exists()


def test_a_failed_write_removes_the_new_workspace(git_repo, capsys):
    _, err = new_in_workspace(git_repo.root, "--column", "Owner=api", capsys=capsys, expect=2)
    assert "no column(s): Owner" in err
    assert not (git_repo.root / ".worktrees" / BRANCH).exists()
    assert not git(git_repo.root, "branch", "--list", BRANCH)
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_without_workspace_new_still_writes_here(git_repo, capsys):
    assert run(git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals", capsys=capsys)[0] == 0
    assert "| T004 |" in (git_repo.root / "TODO.md").read_text()
    assert not (git_repo.root / ".worktrees").exists()


def test_spike_frame_commits_its_draft(repo):
    stages = {s.name: s for s in load_kinds(load_config(repo.root))[0]["spike"].stages}
    assert stages["frame"].commit is True
