"""A task finished only on its own branch, and dependents branched from it (T017)."""

import json

import pytest
from conftest import git

from taskrail import claims, stack
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.project import load_project

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
| ⬜ | T004 | chore   | 1   | T001, T003 | Two deps        | —           |
"""

T001 = "T001-base-task"
T002 = "T002-depends-on-base"
T003 = "T003-independent"


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


def mark_done(text, task_id):
    return text.replace(f"| ⬜ | {task_id} |", f"| ✅ | {task_id} |")


@pytest.fixture
def lanes(git_repo, tmp_path_factory):
    """E1's repository: a bare origin, and lanes that finish tasks in their own worktrees."""
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare
    git_repo.worktrees = {}

    def open_lane(task_id, branch, base="origin/main"):
        path = tmp_path_factory.mktemp("lanes") / branch
        git(git_repo.root, "worktree", "add", "-q", str(path), "-b", branch, base)
        git_repo.worktrees[task_id] = path
        return path

    def finish(task_id, branch, base="origin/main", capsys=None):
        path = open_lane(task_id, branch, base)
        assert main(["--root", str(path), "claim", task_id, "--owner", "lane"]) == 0
        assert main(["--root", str(path), "done", task_id, "--owner", "lane"]) == 0
        commit_all(path, f"chore({task_id}): mark done")
        return path

    git_repo.open_lane = open_lane
    git_repo.finish = finish
    return git_repo


def ids(rows):
    return [row["id"] for row in rows]


def sha(root, ref):
    return git(root, "rev-parse", ref)


# 1


def test_a_task_done_on_its_branch_is_done_branch_and_never_offered(lanes, capsys):
    assert ids(data(lanes.root, "next", capsys=capsys)) == ["T001", "T003"]
    lanes.finish("T001", T001)
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    assert "T001" not in ids(data(lanes.root, "next", capsys=capsys))
    assert ids(data(lanes.root, "list", "--state", "done-branch", capsys=capsys)) == ["T001"]
    assert "done-branch" in run(lanes.root, "list", capsys=capsys)[1]
    code, _, err = run(lanes.root, "claim", "T001", capsys=capsys)
    assert code == 5
    assert T001 in err


def test_done_branch_wins_over_a_live_claim(lanes, capsys):
    path = lanes.finish("T001", T001)
    assert main(["--root", str(path), "claim", "T001", "--owner", "lane", "--ignore-deps"]) == 5  # ✅ there
    claims.claim(load_config(lanes.root), "T001", owner="other", branch=T001, worktree=str(path))
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"


# 2


def test_a_single_unmerged_dependency_sets_the_base(lanes, capsys):
    lanes.finish("T001", T001)
    capsys.readouterr()
    task = data(lanes.root, "show", "T002", capsys=capsys)
    assert (task["state"], task["blocked_by"]) == ("pending", [])
    assert "T002" in ids(data(lanes.root, "next", capsys=capsys))
    base = task["base"]
    assert (base["onto"], base["dependency"], base["diverged"]) == (T001, "T001", False)
    assert base["commit"] == sha(lanes.root, T001)
    assert "T001 is done on T001-base-task but not merged into main" in base["reason"]
    assert (base["remote"], base["remote_source"]) == ("origin", "[review].remote")
    assert f"base {T001}" in run(lanes.root, "show", "T002", capsys=capsys)[1]


# 3


def test_two_unmerged_dependencies_block_the_task(lanes, capsys):
    lanes.finish("T001", T001)
    lanes.finish("T003", T003)
    capsys.readouterr()
    task = data(lanes.root, "show", "T004", capsys=capsys)
    assert (task["state"], task["blocked_by"]) == ("blocked", ["T001", "T003"])
    assert "T004" not in ids(data(lanes.root, "next", capsys=capsys))
    assert task["base"]["onto"] is None and task["base"]["commit"] is None and task["base"]["dependency"] is None
    assert "T001" in task["base"]["reason"] and "T003" in task["base"]["reason"]
    code, _, err = run(lanes.root, "claim", "T004", capsys=capsys)
    assert code == 5
    assert "blocked by T001, T003" in err


# 4


def test_inside_the_dependency_worktree_the_base_is_still_its_branch(lanes, capsys):
    path = lanes.finish("T001", T001)
    capsys.readouterr()
    assert data(path, "show", "T001", capsys=capsys)["state"] == "done"
    base = data(path, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"], base["commit"]) == (T001, "T001", sha(path, T001))


# 5


def test_a_dependency_merged_into_the_local_mainline_is_merged(lanes, capsys):
    lanes.finish("T001", T001)
    (lanes.root / "TODO.md").write_text(mark_done(TODO.lstrip("\n"), "T001"))
    commit_all(lanes.root, "merge T001")
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done"
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == ("main", None)
    assert base["commit"] == sha(lanes.root, "main")


def test_a_dependency_merged_only_on_the_remote_mainline_is_merged(lanes, tmp_path_factory, capsys):
    lanes.finish("T001", T001)
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(lanes.root, "clone", "-q", str(lanes.bare), str(clone))
    (clone / "TODO.md").write_text(mark_done((clone / "TODO.md").read_text(), "T001"))
    commit_all(clone, "squash T001")
    git(clone, "push", "-q", "origin", "main")
    git(lanes.root, "fetch", "-q", "origin")
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] != "done-branch"
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == ("origin/main", None)


# 6


def push_lane(lanes, branch):
    git(lanes.root, "push", "-q", "origin", branch)
    git(lanes.root, "fetch", "-q", "origin")


def test_a_dependency_branch_only_on_the_remote(lanes, capsys):
    path = lanes.finish("T001", T001)
    push_lane(lanes, T001)
    git(lanes.root, "worktree", "remove", "--force", str(path))
    git(lanes.root, "branch", "-D", T001)
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == (f"origin/{T001}", "T001")
    assert base["commit"] == sha(lanes.root, f"origin/{T001}")


def test_the_further_ahead_copy_of_the_dependency_branch_wins_and_divergence_stops(lanes, tmp_path_factory, capsys):
    path = lanes.finish("T001", T001)
    push_lane(lanes, T001)
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(lanes.root, "clone", "-q", "-b", T001, str(lanes.bare), str(clone))
    (clone / "NOTES.md").write_text("remote lane\n")
    commit_all(clone, "docs: remote note")
    git(clone, "push", "-q", "origin", T001)
    git(lanes.root, "fetch", "-q", "origin")
    capsys.readouterr()
    assert data(lanes.root, "show", "T002", capsys=capsys)["base"]["onto"] == f"origin/{T001}"

    (path / "LOCAL.md").write_text("local lane\n")
    commit_all(path, "docs: local note")
    base = data(lanes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["diverged"], base["commit"], base["dependency"]) == (None, True, None, "T001")


# 7


def test_new_workspace_branches_from_the_single_unmerged_dependency(lanes, capsys):
    lanes.finish("T001", T001)
    capsys.readouterr()
    result = data(
        lanes.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Stacked", "--depends-on", "T001", "--workspace",
        capsys=capsys,
    )
    assert (result["branch"], result["base"]) == ("T005-stacked", T001)
    assert sha(lanes.root, "T005-stacked") == sha(lanes.root, T001)


def test_new_workspace_refuses_two_unmerged_dependencies_and_frees_the_id(lanes, capsys):
    lanes.finish("T001", T001)
    lanes.finish("T003", T003)
    capsys.readouterr()
    code, _, err = run(
        lanes.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Stacked", "--depends-on", "T001,T003", "--workspace",
        capsys=capsys,
    )
    assert code == 5
    assert "T001" in err and "T003" in err
    assert git(lanes.root, "branch", "--list", "T005-*") == ""
    assert not (lanes.root / ".worktrees" / "T005-stacked").exists()
    assert run(lanes.root, "reserve-id", capsys=capsys)[1].strip() == "T005"


# 8


def test_claim_records_the_fork_point_of_a_stacked_branch(lanes, capsys):
    t001 = lanes.finish("T001", T001)
    fork = sha(lanes.root, T001)
    lane = lanes.open_lane("T002", T002, base=T001)
    (t001 / "LATER.md").write_text("more work on the dependency\n")
    commit_all(t001, "docs: later")
    capsys.readouterr()
    claim = data(lane, "claim", "T002", "--owner", "lane", capsys=capsys)["claim"]
    assert claim["base"] == {"onto": T001, "commit": fork, "dependency": "T001"}
    assert claims.read(load_config(lane), "T002").base == claim["base"]


def test_claim_records_the_mainline_base(lanes, capsys):
    lane = lanes.open_lane("T003", T003)
    capsys.readouterr()
    claim = data(lane, "claim", "T003", "--owner", "lane", capsys=capsys)["claim"]
    assert claim["base"] == {"onto": "origin/main", "commit": sha(lanes.root, "origin/main"), "dependency": None}


def test_claim_files_without_a_base_or_with_unknown_keys_still_load(lanes):
    config = load_config(lanes.root)
    directory = claims.claims_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    old = {"id": "T003", "owner": "old", "branch": T003, "created": "2026-01-01T00:00:00+00:00", "worktree": None, "host": "h"}
    (directory / "T003.json").write_text(json.dumps(old))
    (directory / "T001.json").write_text(json.dumps({**old, "id": "T001", "future": {"x": 1}}))
    loaded = claims.read_all(config)
    assert loaded["T003"].base is None and loaded["T003"].owner == "old"
    assert loaded["T001"].owner == "old"


# 9, 10


def test_review_rebases_a_stacked_branch_onto_its_dependency(lanes, capsys):
    t001 = lanes.finish("T001", T001)
    lane = lanes.open_lane("T002", T002, base=T001)
    capsys.readouterr()
    assert run(lane, "claim", "T002", "--owner", "lane", capsys=capsys)[0] == 0
    code, _, err = run(lane, "done", "T002", "--owner", "lane", capsys=capsys)
    assert code == 0, err
    commit_all(lane, "chore(T002): mark done")

    result = data(lane, "review", "T002", capsys=capsys)
    assert (result["target"], result["rebase"]["onto"], result["rebase"]["dependency"]) == ("main", T001, "T001")
    assert result["rebase"]["needed"] is False

    (t001 / "LATER.md").write_text("more work on the dependency\n")
    commit_all(t001, "docs: later")
    assert data(lane, "review", "T002", capsys=capsys)["rebase"]["needed"] is True


def test_review_on_a_mainline_based_branch_has_no_dependency(lanes, capsys):
    lane = lanes.finish("T003", T003)
    capsys.readouterr()
    rebase = data(lane, "review", "T003", capsys=capsys)["rebase"]
    assert (rebase["onto"], rebase["dependency"]) == ("origin/main", None)


# A task reopened on its mainline while its old branch still says ✅ (T034)


def squash_merge(lanes, task_id):
    """What a squash merge of the task's pull request leaves on the mainline: its row ✅."""
    todo = lanes.root / "TODO.md"
    todo.write_text(mark_done(todo.read_text(), task_id))
    commit_all(lanes.root, f"feat: merge ({task_id})")


def reopen_on_mainline(lanes, task_id, capsys, trailer=None):
    capsys.readouterr()
    result = data(lanes.root, "reopen", task_id, "--reason", "Not finished after all", capsys=capsys)
    message = result["commit_message"]
    if trailer is not None:
        message = message.replace(f"Reopens: {task_id}\n", f"{trailer}\n")
    git(lanes.root, "commit", "-q", "-a", "--cleanup=verbatim", "-m", message)


def drop_lane(lanes, task_id, branch):
    git(lanes.root, "worktree", "remove", "--force", str(lanes.worktrees[task_id]))
    git(lanes.root, "branch", "-D", branch)


@pytest.mark.parametrize("trailer", [None, "Reopens:  T001 \r"], ids=["trailer", "trailer-with-whitespace"])
def test_a_task_reopened_on_the_mainline_is_pending_despite_its_stale_branch(lanes, capsys, trailer):
    lanes.finish("T001", T001)
    push_lane(lanes, T001)
    squash_merge(lanes, "T001")
    reopen_on_mainline(lanes, "T001", capsys, trailer)
    git(lanes.root, "push", "-q", "origin", "main")
    git(lanes.root, "fetch", "-q", "origin")
    capsys.readouterr()

    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "pending"
    assert "T001" in ids(data(lanes.root, "next", capsys=capsys))
    dependent = data(lanes.root, "show", "T002", capsys=capsys)
    assert (dependent["state"], dependent["blocked_by"], dependent["base"]["dependency"]) == ("blocked", ["T001"], None)
    code, _, err = run(lanes.root, "claim", "T001", "--owner", "other", capsys=capsys)
    assert code == 0, err


def test_a_second_done_on_a_branch_containing_the_reopen_is_done_branch_again(lanes, capsys):
    lanes.finish("T001", T001)
    push_lane(lanes, T001)
    squash_merge(lanes, "T001")
    reopen_on_mainline(lanes, "T001", capsys)
    drop_lane(lanes, "T001", T001)  # origin/T001-base-task stays behind, still ✅ and without the reopen

    capsys.readouterr()
    lanes.finish("T001", T001, base="main")
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    project, _ = load_project(load_config(lanes.root))
    assert stack.done_on_branch(project)["T001"].refs == (T001,)


def test_a_second_reopen_clears_a_branch_that_contains_only_the_first(lanes, capsys):
    lanes.finish("T001", T001)
    squash_merge(lanes, "T001")
    reopen_on_mainline(lanes, "T001", capsys)
    drop_lane(lanes, "T001", T001)
    lanes.finish("T001", T001, base="main")  # contains the first reopen
    squash_merge(lanes, "T001")
    reopen_on_mainline(lanes, "T001", capsys)  # the stale tip lacks this one
    capsys.readouterr()

    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "pending"
    assert "T001" in ids(data(lanes.root, "next", capsys=capsys))


# A task discarded on its own branch and not merged (T062)


def discard_on_branch(lanes, task_id, branch, base="origin/main"):
    path = lanes.open_lane(task_id, branch, base)
    assert main(["--root", str(path), "claim", task_id, "--owner", "lane"]) == 0
    assert main(["--root", str(path), "discard", task_id, "--owner", "lane"]) == 0
    commit_all(path, f"chore({task_id}): discard")
    return path


def test_a_task_discarded_on_its_branch_is_discarded_branch_and_never_offered(lanes, capsys):
    discard_on_branch(lanes, "T001", T001)
    capsys.readouterr()

    shown = data(lanes.root, "show", "T001", capsys=capsys)
    assert (shown["status"], shown["state"]) == ("pending", "discarded-branch")
    assert ids(data(lanes.root, "next", capsys=capsys)) == ["T003"]
    assert ids(data(lanes.root, "list", "--state", "discarded-branch", capsys=capsys)) == ["T001"]
    code, _, err = run(lanes.root, "claim", "T001", "--owner", "other", capsys=capsys)
    assert code == 5
    assert f"T001 is discarded on branch {T001}" in err
    dependent = data(lanes.root, "show", "T002", capsys=capsys)  # a discarded dependency still blocks, unstacked
    assert (dependent["state"], dependent["blocked_by"], dependent["base"]["dependency"]) == ("blocked", ["T001"], None)


def test_a_discard_only_on_the_remote_branch_is_discarded_branch(lanes, capsys):
    path = discard_on_branch(lanes, "T001", T001)
    push_lane(lanes, T001)
    git(lanes.root, "worktree", "remove", "--force", str(path))
    git(lanes.root, "branch", "-D", T001)
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "discarded-branch"
    project, _ = load_project(load_config(lanes.root))
    assert stack.discarded_on_branch(project)["T001"].refs == (f"origin/{T001}",)
    assert "T001" not in stack.done_on_branch(project)


def test_a_done_tip_wins_over_a_discarded_one(lanes, capsys):
    path = discard_on_branch(lanes, "T001", T001)
    push_lane(lanes, T001)  # origin keeps the ❌
    git(path, "reset", "-q", "--hard", "origin/main")
    assert main(["--root", str(path), "done", "T001", "--owner", "lane", "--force"]) == 0  # claim refuses it now
    commit_all(path, "chore(T001): mark done")
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    project, _ = load_project(load_config(lanes.root))
    assert "T001" not in stack.discarded_on_branch(project)


def test_a_discard_older_than_a_reopen_on_the_mainline_does_not_count(lanes, capsys):
    discard_on_branch(lanes, "T001", T001)
    todo = lanes.root / "TODO.md"
    todo.write_text(todo.read_text().replace("| ⬜ | T001 |", "| ❌ | T001 |"))
    commit_all(lanes.root, "chore: merge (T001)")
    reopen_on_mainline(lanes, "T001", capsys)  # the branch tip lacks the reopen
    capsys.readouterr()
    assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "pending"
    assert "T001" in ids(data(lanes.root, "next", capsys=capsys))
