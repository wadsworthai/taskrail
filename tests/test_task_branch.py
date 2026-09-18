"""Naming and renaming a task's branch, and finding it everywhere afterwards (T019)."""

import json
import re
from pathlib import Path

import pytest
from conftest import BASE_CONFIG, git

from taskrail import branches, claims
from taskrail.cli import main
from taskrail.config import load_config

TODO = """
# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | Demo | Try lanes | —    |

## E01 — Demo

| ✓  | ID   | Kind    | Pts | Depends On | Title           | Description |
|----|------|---------|-----|------------|-----------------|-------------|
| ⬜ | T001 | feature | 2   | —          | Base task       | —           |
| ⬜ | T002 | feature | 1   | T001       | Depends on base | —           |
| ⬜ | T003 | bug     | 3   | —          | Independent     | —           |
"""

T001 = "T001-base-task"
T003 = "T003-independent"
NAME = "feature/base"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def exists(root, branch):
    return git(root, "branch", "--list", branch) != ""


def record(root, task_id):
    return branches.read(load_config(root), task_id)


@pytest.fixture
def lanes(git_repo, tmp_path_factory):
    """A bare origin, and lanes that work tasks in worktrees outside the repository."""
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git(git_repo.root, "fetch", "-q", "origin")
    git_repo.bare = bare

    def open_lane(branch, base="origin/main"):
        path = tmp_path_factory.mktemp("lanes") / "lane"
        git(git_repo.root, "worktree", "add", "-q", str(path), "-b", branch, base)
        return path

    git_repo.open_lane = open_lane
    return git_repo


def rename_in_lane(lanes, capsys):
    """T001 claimed on its template branch, then renamed to NAME inside its worktree."""
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    result = data(lane, "branch", "T001", NAME, "--owner", "lane", capsys=capsys)
    return lane, result


# 1


def test_naming_a_task_before_its_workspace_exists(lanes, capsys):
    before = data(lanes.root, "show", "T001", capsys=capsys)
    assert (before["branch"], before["branch_source"], before["worktree"]) == (T001, "template", f".worktrees/{T001}")
    result = data(lanes.root, "branch", "T001", NAME, capsys=capsys)
    assert result == {
        "id": "T001", "branch": NAME, "previous": T001, "renamed": False, "claim_updated": False,
        "worktree": None, "remote_copies": [], "record_remote": None,
    }
    after = data(lanes.root, "show", "T001", capsys=capsys)
    assert (after["branch"], after["branch_source"], after["worktree"]) == (NAME, "recorded", f".worktrees/{NAME}")
    assert {k: v for k, v in after.items() if k not in ("branch", "branch_source", "worktree")} == {
        k: v for k, v in before.items() if k not in ("branch", "branch_source", "worktree")
    }
    assert record(lanes.root, "T001").branch == NAME
    stored = json.loads((branches.records_dir(load_config(lanes.root)) / "T001.json").read_text())
    assert sorted(stored) == ["branch", "id", "recorded"]


# 2


def test_renaming_inside_the_worktree_renames_the_branch_and_follows_the_claim(lanes, capsys):
    lane, result = rename_in_lane(lanes, capsys)
    assert (result["previous"], result["renamed"], result["claim_updated"]) == (T001, True, True)
    assert Path(result["worktree"]) == lane.resolve()
    assert git(lane, "branch", "--show-current") == NAME
    assert not exists(lanes.root, T001)
    assert git(lanes.root, "config", f"branch.{NAME}.merge") == "refs/heads/main"
    assert claims.read(load_config(lanes.root), "T001").branch == NAME
    [row] = data(lanes.root, "claims", capsys=capsys)["local"]
    assert row["stale"] is None
    shown = data(lanes.root, "show", "T001", capsys=capsys)
    assert (shown["branch"], (lanes.root / shown["worktree"]).resolve()) == (NAME, lane.resolve())  # relative to the main checkout (T072)
    assert shown["worktree"].startswith("../")
    assert shown["claim"]["branch"] == NAME
    # claiming again from the renamed branch is the same claim
    again = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (again["created"], again["warning"]) == (False, None)


# 3


def test_a_renamed_task_done_on_its_branch_is_still_found(lanes, capsys):
    lane, _ = rename_in_lane(lanes, capsys)
    assert run(lane, "done", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    commit_all(lane, "chore(T001): mark done")
    assert claims.read(load_config(lanes.root), "T001") is None
    shown = data(lanes.root, "show", "T001", capsys=capsys)
    assert shown["state"] == "done-branch"
    assert shown["prior_work"]["branches"] == [NAME]
    assert "T001" not in [t["id"] for t in data(lanes.root, "next", capsys=capsys)]
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == (NAME, "T001")

    git(lane, "push", "-q", "origin", NAME)
    git(lanes.root, "fetch", "-q", "origin")
    git(lanes.root, "worktree", "remove", "--force", str(lane))
    git(lanes.root, "branch", "-D", NAME)
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == (f"origin/{NAME}", "T001")


# 4


def test_review_runs_on_the_renamed_branch(lanes, capsys):
    lane, _ = rename_in_lane(lanes, capsys)
    assert run(lane, "done", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    commit_all(lane, "chore(T001): mark done")
    review = data(lane, "review", "T001", "--no-fetch", capsys=capsys)
    assert review["head"] == NAME
    published = data(lane, "review", "T001", "--no-fetch", "--publish", "--no-push", capsys=capsys)
    assert published["push"]["command"].endswith(f"origin HEAD:refs/heads/{NAME}")

    other = lanes.open_lane(T001, base=NAME)
    code, _, err = run(other, "review", "T001", "--no-fetch", capsys=capsys)
    assert code == 5
    assert f"task branch {NAME}" in err


def test_the_pull_request_link_names_the_renamed_branch(lanes, capsys):
    git(lanes.root, "remote", "set-url", "origin", "git@github.com:example/demo.git")
    lane, _ = rename_in_lane(lanes, capsys)
    assert run(lane, "done", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    commit_all(lane, "chore(T001): mark done")
    review = data(lane, "review", "T001", "--no-fetch", capsys=capsys)
    assert "compare/main...feature%2Fbase?" in review["pull_request"]["url"]


# 5


def test_a_manual_git_rename_is_adopted(lanes, capsys):
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    git(lane, "branch", "-m", T001, "by-hand")
    result = data(lane, "branch", "T001", "by-hand", "--owner", "lane", capsys=capsys)
    assert (result["renamed"], result["claim_updated"], result["previous"]) == (False, True, T001)
    assert data(lanes.root, "show", "T001", capsys=capsys)["branch"] == "by-hand"
    assert claims.read(load_config(lanes.root), "T001").branch == "by-hand"


# 6


def new_workspace(root, *extra, capsys):
    return run(root, "new", "--epic", "E01", "--kind", "feature", "--title", "Fresh work", "--workspace", *extra, "--json", capsys=capsys)


def test_new_workspace_with_a_chosen_branch(lanes, capsys):
    code, out, err = new_workspace(lanes.root, "--branch", "feature/new", capsys=capsys)
    assert code == 0, err
    result = json.loads(out)
    assert (result["id"], result["branch"]) == ("T004", "feature/new")
    path = lanes.root / ".worktrees" / "feature" / "new"
    assert Path(result["workspace"]) == path.resolve()
    assert git(path, "branch", "--show-current") == "feature/new"
    assert "| T004 |" in (path / "TODO.md").read_text()
    assert record(lanes.root, "T004").branch == "feature/new"
    assert not exists(lanes.root, "T004-fresh-work")


@pytest.mark.parametrize(
    ("name", "code"),
    [("bad name", 2), ("main", 2), (T003, 5), ("taken", 5)],
)
def test_new_workspace_refuses_a_bad_branch_and_frees_the_id(lanes, name, code, capsys):
    git(lanes.root, "branch", "taken")
    result, _, err = new_workspace(lanes.root, "--branch", name, capsys=capsys)
    assert result == code, err
    assert not (lanes.root / ".worktrees").exists()
    assert record(lanes.root, "T004") is None
    assert git(lanes.root, "branch", "--list", "T004-*") == ""
    assert run(lanes.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_new_branch_needs_workspace(lanes, capsys):
    code, _, err = run(lanes.root, "new", "--epic", "E01", "--kind", "feature", "--title", "X", "--branch", "x", capsys=capsys)
    assert code == 2
    assert "--workspace" in err
    assert "T004" not in (lanes.root / "TODO.md").read_text()


# 7


@pytest.mark.parametrize("name", ["-x", "HEAD", "a..b", "with space", "@{-1}", "main"])
def test_branch_refuses_invalid_names_and_mainlines(lanes, name, capsys):
    code, _, err = run(lanes.root, "branch", "T001", "--", name, capsys=capsys)
    assert code == 2, err
    assert record(lanes.root, "T001") is None


def test_branch_refuses_another_tasks_branch(lanes, capsys):
    assert run(lanes.root, "branch", "T001", T003, capsys=capsys)[0] == 5
    assert data(lanes.root, "branch", "T003", "feature/three", capsys=capsys)["branch"] == "feature/three"
    code, _, err = run(lanes.root, "branch", "T001", "feature/three", capsys=capsys)
    assert code == 5
    assert "T003" in err
    assert record(lanes.root, "T001") is None


def test_branch_refuses_the_recorded_branch_of_a_task_created_in_its_own_workspace(lanes, capsys):
    code, _, err = new_workspace(lanes.root, "--branch", "feature/fresh", capsys=capsys)
    assert code == 0, err
    assert "| T004 |" not in (lanes.root / "TODO.md").read_text()  # the row lives in T004's workspace
    code, _, err = run(lanes.root, "branch", "T002", "feature/fresh", capsys=capsys)
    assert code == 5
    assert "T004" in err
    code, _, err = new_workspace(lanes.root, "--branch", "feature/fresh", capsys=capsys)
    assert code == 5
    assert "T004" in err


def test_branch_refuses_an_existing_target_while_the_old_branch_exists(lanes, capsys):
    lanes.open_lane(T001)
    git(lanes.root, "branch", "other")
    code, _, err = run(lanes.root, "branch", "T001", "other", capsys=capsys)
    assert code == 5
    assert "other already exists" in err
    assert exists(lanes.root, T001) and record(lanes.root, "T001") is None


def test_branch_refuses_a_pushed_branch_unless_forced(lanes, capsys):
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    git(lane, "push", "-q", "origin", T001)
    git(lanes.root, "fetch", "-q", "origin")
    before = claims.read(load_config(lanes.root), "T001")
    code, _, err = run(lane, "branch", "T001", NAME, "--owner", "lane", capsys=capsys)
    assert code == 5
    assert f"origin/{T001}" in err and "--force" in err
    assert exists(lanes.root, T001) and record(lanes.root, "T001").branch == T001  # frozen by claim, unchanged
    assert claims.read(load_config(lanes.root), "T001") == before

    result = data(lane, "branch", "T001", NAME, "--owner", "lane", "--force", capsys=capsys)
    assert (result["renamed"], result["remote_copies"]) == (True, [f"origin/{T001}"])
    assert git(lanes.bare, "branch", "--list", T001) != ""  # the remote is never touched
    assert git(lanes.bare, "branch", "--list", NAME) == ""


def test_branch_refuses_a_name_taken_on_the_remote_unless_forced(lanes, capsys):
    git(lanes.root, "push", "-q", "origin", f"main:refs/heads/{NAME}")
    git(lanes.root, "fetch", "-q", "origin")
    code, _, err = run(lanes.root, "branch", "T001", NAME, capsys=capsys)
    assert code == 5
    assert f"origin/{NAME}" in err
    assert record(lanes.root, "T001") is None
    assert data(lanes.root, "branch", "T001", NAME, "--force", capsys=capsys)["branch"] == NAME


def test_branch_refuses_a_task_claimed_by_someone_else_unless_forced(lanes, capsys):
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "alice", capsys=capsys)[0] == 0
    code, _, err = run(lane, "branch", "T001", NAME, "--owner", "bob", capsys=capsys)
    assert code == 4
    assert "alice" in err
    assert exists(lanes.root, T001) and record(lanes.root, "T001").branch == T001
    result = data(lane, "branch", "T001", NAME, "--owner", "bob", "--force", capsys=capsys)
    assert (result["renamed"], result["claim_updated"]) == (True, True)


def test_branch_on_an_unknown_task(lanes, capsys):
    assert run(lanes.root, "branch", "T999", NAME, capsys=capsys)[0] == 3


def test_branch_to_the_same_name_only_records_it(lanes, capsys):
    lanes.open_lane(T001)
    result = data(lanes.root, "branch", "T001", T001, capsys=capsys)
    assert (result["renamed"], result["previous"], result["branch"]) == (False, T001, T001)
    assert record(lanes.root, "T001").branch == T001


# 8


@pytest.fixture
def remote_claims(lanes):
    lanes.write(".taskrail/config.toml", BASE_CONFIG + '\n[git]\nclaim_remote = "origin"\n')
    commit_all(lanes.root, "claim remote")
    git(lanes.root, "push", "-q", "origin", "main")
    git(lanes.root, "fetch", "-q", "origin")
    return lanes


def test_a_rename_re_pushes_the_remote_claim(remote_claims, capsys):
    lanes = remote_claims
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    first = claims.read(load_config(lanes.root), "T001").remote["commit"]
    assert data(lane, "branch", "T001", NAME, "--owner", "lane", capsys=capsys)["claim_updated"] is True
    local = claims.read(load_config(lanes.root), "T001")
    assert local.remote["commit"] != first
    published = json.loads(git(lanes.bare, "show", "refs/taskrail/claims/T001:claim.json"))
    assert published["branch"] == NAME
    assert git(lanes.bare, "rev-parse", "refs/taskrail/claims/T001") == local.remote["commit"]
    assert run(lane, "release", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    assert git(lanes.bare, "for-each-ref", "refs/taskrail/claims") == ""


def test_local_only_rename_leaves_the_remote_claim(remote_claims, capsys):
    lanes = remote_claims
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    assert data(lane, "branch", "T001", NAME, "--owner", "lane", "--local-only", capsys=capsys)["claim_updated"] is True
    assert json.loads(git(lanes.bare, "show", "refs/taskrail/claims/T001:claim.json"))["branch"] == T001


# 9


def edit_title(root):
    path = Path(root) / "TODO.md"
    path.write_text(path.read_text().replace("| Base task       |", "| Base task v2    |"))


def test_a_recorded_branch_survives_a_title_edit(lanes, capsys):
    data(lanes.root, "branch", "T001", NAME, capsys=capsys)
    edit_title(lanes.root)
    assert data(lanes.root, "show", "T001", capsys=capsys)["branch"] == NAME


# 10


def test_claim_freezes_the_template_name(lanes, capsys):
    lane = lanes.open_lane(T001)
    result = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (result["branch_recorded"], result["warning"]) == (True, None)
    assert data(lanes.root, "show", "T001", capsys=capsys)["branch_source"] == "recorded"
    again = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (again["created"], again["branch_recorded"], again["warning"]) == (False, False, None)

    edit_title(lanes.root)
    edit_title(lane)
    shown = data(lanes.root, "show", "T001", capsys=capsys)
    assert (shown["branch"], shown["branch_source"]) == (T001, "recorded")
    assert run(lane, "done", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    commit_all(lane, "chore(T001): mark done")
    assert data(lane, "review", "T001", "--no-fetch", capsys=capsys)["head"] == T001
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"


def test_claim_on_a_recorded_branch_writes_nothing(lanes, capsys):
    data(lanes.root, "branch", "T001", NAME, capsys=capsys)
    recorded = record(lanes.root, "T001")
    lane = lanes.open_lane(NAME)
    result = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (result["branch_recorded"], result["warning"]) == (False, None)
    assert record(lanes.root, "T001") == recorded


# 11


def test_claim_on_another_branch_warns_and_records_nothing(lanes, capsys):
    lane = lanes.open_lane("feature/other")
    code, out, err = run(lane, "claim", "T001", "--owner", "lane", "--json", capsys=capsys)
    assert code == 0
    result = json.loads(out)
    assert result["branch_recorded"] is False
    assert "taskrail branch" in result["warning"]
    assert re.search(r"^taskrail: warning: .*taskrail branch", err, re.MULTILINE)
    assert result["warning"] in err
    assert record(lanes.root, "T001") is None
    assert data(lanes.root, "show", "T001", capsys=capsys)["branch_source"] == "template"


def test_claim_on_the_mainline_warns(lanes, capsys):
    code, _, err = run(lanes.root, "claim", "T003", capsys=capsys)
    assert code == 0
    assert "warning" in err and "taskrail branch" in err
    assert record(lanes.root, "T003") is None


def test_claim_on_the_template_branch_of_a_renamed_task_warns_and_keeps_the_record(lanes, capsys):
    data(lanes.root, "branch", "T001", NAME, capsys=capsys)
    lane = lanes.open_lane(T001)
    result = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert NAME in result["warning"]
    assert record(lanes.root, "T001").branch == NAME


# 12


def test_outside_git_the_template_applies(repo, capsys):
    shown = data(repo.root, "show", "T002", capsys=capsys)
    assert (shown["branch"], shown["branch_source"]) == ("T002-repricing", "template")
    assert run(repo.root, "branch", "T002", "x", capsys=capsys)[0] == 2


# T119


def close_from_the_mainline(lanes, command, task_id, branch, capsys):
    """Claim `task_id` inside its own worktree, then close it with the cwd in the mainline checkout."""
    lane = lanes.open_lane(branch)
    assert run(lane, "claim", task_id, "--owner", "lane", capsys=capsys)[0] == 0
    code, out, err = run(lanes.root, command, task_id, "--owner", "lane", "--json", capsys=capsys)
    return lane, code, json.loads(out), err


def test_done_on_another_branch_warns(lanes, capsys):
    lane, code, result, err = close_from_the_mainline(lanes, "done", "T001", T001, capsys=capsys)
    assert code == 0
    assert result["status"] == "done"
    assert "main" in result["warning"] and T001 in result["warning"]
    assert "taskrail branch" in result["warning"]
    assert str(lanes.root) in result["warning"]
    assert re.search(r"^taskrail: warning: .*taskrail branch", err, re.MULTILINE)
    assert result["warning"] in err
    # The damage the warning is about: the row is ticked here and untouched on the task's branch.
    assert "| ✅ | T001 " in (lanes.root / "TODO.md").read_text()
    assert "| ⬜ | T001 " in (lane / "TODO.md").read_text()


def test_discard_on_another_branch_warns(lanes, capsys):
    _, code, result, err = close_from_the_mainline(lanes, "discard", "T003", T003, capsys=capsys)
    assert code == 0
    assert result["status"] == "discarded"
    assert "discarded" in result["warning"] and T003 in result["warning"]
    assert result["warning"] in err


def test_done_on_the_task_branch_warns_about_nothing(lanes, capsys):
    lane = lanes.open_lane(T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    code, out, err = run(lane, "done", "T001", "--owner", "lane", "--json", capsys=capsys)
    assert (code, json.loads(out)["warning"]) == (0, None)
    assert "warning" not in err


def test_outside_git_closing_a_task_warns_about_nothing(repo, capsys):
    code, out, err = run(repo.root, "done", "T003", "--owner", "solo", "--force", "--json", capsys=capsys)
    assert (code, json.loads(out)["warning"]) == (0, None)
    assert "warning" not in err


def test_only_the_resolver_renders_the_branch_template():
    source = Path(branches.__file__).parent
    renders = [
        path.name
        for path in sorted(source.glob("*.py"))
        if re.search(r"render\([^)]*\.branch\b", path.read_text())
    ]
    assert renders == ["branches.py"]
