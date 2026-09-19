"""`autopilot merged`: merge detection by content, recorded merges, cleanup and stacked dependents (T031)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import BASE_CONFIG, git

from taskrail import branches, claims
from taskrail.autopilot import merged as merged_module
from taskrail.autopilot import runs
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
| ⬜ | T004 | chore   | 1   | —          | Another one     | —           |
"""

ENABLED = "\n[autopilot]\nenabled = true\n"
BRANCHES = {
    "T001": "T001-base-task",
    "T002": "T002-depends-on-base",
    "T003": "T003-independent",
    "T004": "T004-another-one",
}
CHECKS = ("ancestor", "tree", "patch-id", "merge-tree")


def run(root, *argv, capsys, cwd_root=True):
    capsys.readouterr()
    code = main((["--root", str(root)] if cwd_root else []) + list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys, code=0):
    got, out, err = run(root, *argv, "--json", capsys=capsys)
    assert got == code, err
    return json.loads(out)


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def sha(root, ref):
    return git(root, "rev-parse", ref)


def ref_exists(root, ref):
    return subprocess.run(["git", "show-ref", "--verify", "--quiet", ref], cwd=root).returncode == 0


class Host:
    """A second clone of the bare origin that merges the way a hosting service would."""

    def __init__(self, path: Path):
        self.path = path

    def sync(self):
        git(self.path, "fetch", "-q", "--prune", "origin")
        git(self.path, "reset", "-q", "--hard", "origin/main")

    def push(self):
        git(self.path, "push", "-q", "origin", "HEAD:main")

    def commit(self, files: dict, message: str):
        self.sync()
        for name, content in files.items():
            (self.path / name).write_text(content, encoding="utf-8")
        commit_all(self.path, message)
        self.push()
        return sha(self.path, "HEAD")

    def squash(self, branch, message="feat: squash"):
        self.sync()
        git(self.path, "merge", "-q", "--squash", f"origin/{branch}")
        git(self.path, "commit", "-q", "-m", message)
        self.push()
        return sha(self.path, "HEAD")

    def merge(self, branch, ff=False):
        self.sync()
        if ff:
            git(self.path, "merge", "-q", "--ff-only", f"origin/{branch}")
        else:
            git(self.path, "merge", "-q", "--no-ff", "-m", f"Merge {branch}", f"origin/{branch}")
        self.push()
        return sha(self.path, "HEAD")

    def delete(self, branch):
        git(self.path, "push", "-q", "origin", "--delete", branch)

    def unmark(self, task_id):
        self.sync()
        todo = self.path / "TODO.md"
        text = todo.read_text(encoding="utf-8")
        for closed in ("✅", "❌"):
            text = text.replace(f"| {closed} | {task_id} |", f"| ⬜ | {task_id} |")
        todo.write_text(text, encoding="utf-8")
        commit_all(self.path, f"docs: reopen {task_id} by hand")
        self.push()


@pytest.fixture
def pilot(git_repo, tmp_path_factory):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG + ENABLED)
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git(git_repo.root, "fetch", "-q", "origin")
    host_path = tmp_path_factory.mktemp("host") / "host"
    git(git_repo.root, "clone", "-q", str(bare), str(host_path))
    git_repo.host = Host(host_path)
    git_repo.bare = bare

    def lane(task_id, run_id=None, base="origin/main"):
        path = tmp_path_factory.mktemp("lanes") / BRANCHES[task_id]
        git(git_repo.root, "worktree", "add", "-q", str(path), "-b", BRANCHES[task_id], base)
        argv = ["--root", str(path), "claim", task_id, "--owner", "lane"]
        if run_id:
            argv += ["--run", run_id]
        assert main(argv) == 0
        return path

    def work(path, name, content="work\n"):
        (path / name).write_text(content, encoding="utf-8")
        commit_all(path, f"work on {name}")

    def finish(path, task_id, publish=True):
        assert main(["--root", str(path), "done", task_id, "--owner", "lane"]) == 0
        commit_all(path, f"chore({task_id}): mark done")
        if publish:
            git(path, "push", "-q", "origin", git(path, "branch", "--show-current"))

    def discard(path, task_id, publish=True):
        assert main(["--root", str(path), "discard", task_id, "--owner", "lane"]) == 0
        commit_all(path, f"chore({task_id}): discard")
        if publish:
            git(path, "push", "-q", "origin", git(path, "branch", "--show-current"))

    git_repo.lane = lane
    git_repo.work = work
    git_repo.finish = finish
    git_repo.discard = discard
    return git_repo


def start(pilot, capsys):
    return data(pilot.root, "autopilot", "start", "--count", "2", capsys=capsys)["run"]["id"]


def merged(pilot, *argv, capsys, code=0, root=None):
    return data(root or pilot.root, "autopilot", "merged", *argv, capsys=capsys, code=code)


def finished_lane(pilot, task_id="T001", run_id=None, files=("base.py",)):
    path = pilot.lane(task_id, run_id)
    for name in files:
        pilot.work(path, name)
    pilot.finish(path, task_id)
    return path


def checks(result):
    return tuple(result["checks"][name] for name in CHECKS)


# 1


def test_ancestor_with_a_merge_commit_names_the_merge(pilot, capsys):
    finished_lane(pilot)
    pilot.host.commit({"other.txt": "x"}, "unrelated")
    merge = pilot.host.merge(BRANCHES["T001"])
    pilot.host.commit({"later.txt": "y"}, "later")
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "ancestor", merge)
    assert checks(result) == (True, None, None, None)
    assert result["mainline"]["ref"] == "origin/main"


def test_ancestor_after_a_fast_forward_names_the_head(pilot, capsys):
    lane = finished_lane(pilot)
    pilot.host.merge(BRANCHES["T001"], ff=True)
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "ancestor", sha(lane, "HEAD"))


# 2


def test_tree_match_after_a_squash_on_an_unchanged_mainline(pilot, capsys):
    finished_lane(pilot)
    squash = pilot.host.squash(BRANCHES["T001"])
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "tree", squash)
    assert checks(result) == (False, True, None, None)


# 3


def test_patch_id_after_an_unrelated_commit_landed_first(pilot, capsys):
    finished_lane(pilot)
    pilot.host.commit({"other.txt": "x"}, "unrelated")
    squash = pilot.host.squash(BRANCHES["T001"])
    pilot.host.commit({"later.txt": "y"}, "later")
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "patch-id", squash)
    assert checks(result) == (False, False, True, None)


# 4


def test_merge_tree_when_the_changes_arrived_in_separate_commits(pilot, capsys):
    finished_lane(pilot, files=("one.py", "two.py"))
    host = pilot.host
    host.commit({"other.txt": "x"}, "unrelated")
    git(host.path, "checkout", f"origin/{BRANCHES['T001']}", "--", "one.py", "TODO.md")
    commit_all(host.path, "first half")
    git(host.path, "checkout", f"origin/{BRANCHES['T001']}", "--", "two.py")
    commit_all(host.path, "second half")
    host.push()
    tip = sha(host.path, "HEAD")
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "merge-tree", tip)
    assert checks(result) == (False, False, False, True)


# 5


def test_an_unmerged_finished_branch_is_not_merged(pilot, capsys):
    finished_lane(pilot)
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (False, None, None)
    assert checks(result) == (False, False, False, False)
    assert result["done_at_head"] is True


def test_a_local_commit_after_the_squash_is_not_merged(pilot, capsys):
    lane = finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    pilot.work(lane, "late.py")  # never pushed
    result = merged(pilot, "T001", capsys=capsys)
    assert result["merged"] is False
    assert checks(result) == (False, False, False, False)
    assert result["head"]["ref"] == BRANCHES["T001"]
    assert result["head"]["local"] == sha(lane, "HEAD") != result["head"]["remote"]


def test_an_unstarted_branch_is_not_merged_although_it_is_an_ancestor(pilot, capsys):
    pilot.lane("T003")
    result = merged(pilot, "T003", capsys=capsys)
    assert (result["merged"], result["done_at_head"], result["closed"]) == (False, False, None)
    assert "not done or discarded" in result["reason"]
    assert checks(result) == (None, None, None, None)
    code, _, err = run(pilot.root, "autopilot", "merged", "T003", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 5 and "not merged" in err


def test_a_merged_branch_whose_row_is_not_done_at_its_head_is_not_merged(pilot, capsys):
    lane = pilot.lane("T004")
    pilot.work(lane, "four.py")
    git(lane, "push", "-q", "origin", BRANCHES["T004"])
    pilot.host.merge(BRANCHES["T004"])
    result = merged(pilot, "T004", capsys=capsys)
    assert (result["merged"], result["done_at_head"]) == (False, False)


# 6


def test_confirmations_are_reported_and_never_prove(pilot, capsys):
    finished_lane(pilot)
    squash = pilot.host.squash(BRANCHES["T001"], "feat(demo): base task (T001) (#3)")
    result = merged(pilot, "T001", capsys=capsys)
    assert result["confirmations"] == {"row_done_on_mainline": True, "row_discarded_on_mainline": False, "title_commit": squash}

    finished_lane(pilot, "T003", files=("three.py",))
    pilot.host.sync()
    todo = pilot.host.path / "TODO.md"
    todo.write_text(todo.read_text(encoding="utf-8").replace("| ⬜ | T003 |", "| ✅ | T003 |"), encoding="utf-8")
    commit_all(pilot.host.path, "docs: mark T003 by hand (T003)")
    pilot.host.push()
    result = merged(pilot, "T003", capsys=capsys)
    assert result["merged"] is False
    assert result["confirmations"]["row_done_on_mainline"] is True
    assert result["confirmations"]["title_commit"] is not None


# 7


def test_fetch_prunes_and_no_fetch_leaves_refs_alone(pilot, capsys):
    finished_lane(pilot)
    remote_ref = f"refs/remotes/origin/{BRANCHES['T001']}"
    assert ref_exists(pilot.root, remote_ref)
    before = sha(pilot.root, "origin/main")
    pilot.host.squash(BRANCHES["T001"])
    pilot.host.delete(BRANCHES["T001"])

    result = merged(pilot, "T001", "--no-fetch", capsys=capsys)
    assert (result["fetched"], result["merged"]) == (False, False)
    assert sha(pilot.root, "origin/main") == before and ref_exists(pilot.root, remote_ref)

    result = merged(pilot, "T001", capsys=capsys)
    assert (result["fetched"], result["merged"], result["remote"]) == (True, True, "origin")
    assert not ref_exists(pilot.root, remote_ref)


def test_a_repository_without_the_remote_skips_the_fetch(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG)
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    git(git_repo.root, "switch", "-q", "-c", BRANCHES["T001"])
    (git_repo.root / "base.py").write_text("work\n")
    commit_all(git_repo.root, "work")
    assert main(["--root", str(git_repo.root), "claim", "T001", "--owner", "me"]) == 0
    assert main(["--root", str(git_repo.root), "done", "T001", "--owner", "me"]) == 0
    commit_all(git_repo.root, "done")
    git(git_repo.root, "switch", "-q", "main")
    git(git_repo.root, "merge", "-q", "--squash", BRANCHES["T001"])
    git(git_repo.root, "commit", "-q", "-m", "squash")
    result = merged(git_repo, "T001", capsys=capsys)
    assert (result["fetched"], result["merged"], result["via"], result["mainline"]["ref"]) == (False, True, "tree", "main")


def test_an_unreachable_remote_exits_2(pilot, capsys):
    finished_lane(pilot)
    git(pilot.root, "remote", "set-url", "origin", str(pilot.root / "missing.git"))
    code, _, err = run(pilot.root, "autopilot", "merged", "T001", capsys=capsys)
    assert code == 2 and "fetch" in err


# 8


def test_the_remote_copy_is_checked_when_the_local_branch_is_gone(pilot, capsys):
    lane = finished_lane(pilot)
    head = sha(lane, "HEAD")
    git(pilot.root, "worktree", "remove", str(lane))
    git(pilot.root, "branch", "-q", "-D", BRANCHES["T001"])
    pilot.host.squash(BRANCHES["T001"])
    result = merged(pilot, "T001", capsys=capsys)
    assert result["merged"] is True
    assert result["head"] == {"ref": f"origin/{BRANCHES['T001']}", "commit": head, "local": None, "remote": head}


def test_the_local_branch_is_checked_when_the_remote_was_pruned(pilot, capsys):
    lane = finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    pilot.host.delete(BRANCHES["T001"])
    result = merged(pilot, "T001", capsys=capsys)
    assert result["merged"] is True
    assert result["head"] == {"ref": BRANCHES["T001"], "commit": sha(lane, "HEAD"), "local": sha(lane, "HEAD"), "remote": None}


def test_no_branch_no_record_and_unknown_task_exit_3(pilot, capsys):
    code, _, err = run(pilot.root, "autopilot", "merged", "T003", capsys=capsys)
    assert code == 3 and BRANCHES["T003"] in err
    code, _, err = run(pilot.root, "autopilot", "merged", "T999", capsys=capsys)
    assert code == 3 and "T999" in err


def test_a_renamed_branch_is_found_after_done(pilot, capsys):
    lane = pilot.lane("T001")
    assert main(["--root", str(lane), "branch", "T001", "renamed-base", "--owner", "lane"]) == 0
    pilot.work(lane, "base.py")
    pilot.finish(lane, "T001")
    pilot.host.squash("renamed-base")
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["branch"], result["merged"]) == ("renamed-base", True)


# 9


def test_the_merge_is_recorded_in_the_run(pilot, capsys):
    run_id = start(pilot, capsys)
    lane = finished_lane(pilot, run_id=run_id)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--reason", "plan", capsys=capsys)
    path = runs.runs_dir(load_config(pilot.root)) / f"{run_id}.json"
    stored = json.loads(path.read_text())
    stored["future"] = {"kept": True}
    stored["tasks"]["T001"]["later"] = 1
    path.write_text(json.dumps(stored))
    squash = pilot.host.squash(BRANCHES["T001"])

    result = merged(pilot, "T001", "--run", run_id, capsys=capsys)
    assert result["runs"] == [run_id]
    stored = json.loads(path.read_text())
    entry = stored["tasks"]["T001"]
    assert entry["merged"]["via"] == "tree" and entry["merged"]["commit"] == squash
    assert entry["merged"]["head"] == sha(lane, "HEAD") and entry["merged"]["mainline"] == "origin/main"
    assert entry["merged"]["detected"]
    assert (entry["state"], entry["reason"], entry["later"], stored["future"]) == ("gate", "plan", 1, {"kept": True})


def test_run_selection_and_standalone_use(pilot, capsys):
    first = start(pilot, capsys)
    second = start(pilot, capsys)
    finished_lane(pilot, run_id=first)
    config = load_config(pilot.root)
    assert run(pilot.root, "autopilot", "merged", "T001", "--run", "20000101-1", capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "merged", "T001", "--run", second, capsys=capsys)[0] == 3

    before = (runs.runs_dir(config) / f"{first}.json").read_text()
    assert merged(pilot, "T001", capsys=capsys)["runs"] == []  # not merged: nothing written
    assert (runs.runs_dir(config) / f"{first}.json").read_text() == before

    with runs.update(config, second) as stored:
        runs.lane(stored, "T001")
    pilot.host.squash(BRANCHES["T001"])
    pilot.write(".taskrail/config.toml", BASE_CONFIG)  # autopilot disabled
    assert sorted(merged(pilot, "T001", capsys=capsys)["runs"]) == sorted([first, second])


def test_standalone_use_writes_no_run_file(pilot, capsys):
    finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    result = merged(pilot, "T001", capsys=capsys)
    assert (result["merged"], result["runs"]) == (True, [])
    assert not runs.runs_dir(load_config(pilot.root)).exists()


# 10


def test_status_counts_a_recorded_merge_after_the_row_was_edited_by_hand(pilot, capsys):
    run_id = start(pilot, capsys)
    finished_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T001"])
    pilot.host.unmark("T001")

    def state(task_id):
        report = data(pilot.root, "autopilot", "status", "--run", run_id, "--fetch", capsys=capsys)
        return next(row["state"] for row in report["runs"][0]["tasks"] if row["id"] == task_id)

    assert state("T001") == "done-branch"
    assert merged(pilot, "T001", "--run", run_id, capsys=capsys)["merged"] is True
    assert state("T001") == "done-merged"

    stray = pilot.lane("T003", run_id)
    pilot.work(stray, "stray.py")
    config = load_config(pilot.root)
    with runs.update(config, run_id) as stored:
        runs.lane(stored, "T003")["merged"] = {"via": "tree", "commit": sha(stray, "HEAD"), "head": sha(stray, "HEAD"), "mainline": "origin/main", "detected": "x"}
    assert state("T003") != "done-merged"

    first = merged(pilot, "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert first["cleanup"]["branch_deleted"] is True
    pilot.host.delete(BRANCHES["T001"])  # no copy of the branch is left: only the run knows the merge
    again = merged(pilot, "T001", capsys=capsys)
    assert (again["merged"], again["recorded"], again["via"], again["commit"]) == (True, True, first["via"], first["commit"])


# 11


def test_cleanup_removes_the_worktree_and_local_branch_only(pilot, capsys):
    run_id = start(pilot, capsys)
    lane = finished_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T001"])
    config = load_config(pilot.root)
    claims.claim(config, "T001", owner="lane", branch=BRANCHES["T001"], worktree=str(lane))  # a claim left behind

    result = merged(pilot, "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    cleanup = result["cleanup"]
    assert cleanup == {
        "worktree": str(lane.resolve()),
        "worktree_removed": True,
        "branch_deleted": True,
        "claim_released": True,
        "remote_branch": f"origin/{BRANCHES['T001']}",
        "refused": None,
    }
    assert not lane.exists()
    assert str(lane.resolve()) not in git(pilot.root, "worktree", "list", "--porcelain")
    assert not ref_exists(pilot.root, f"refs/heads/{BRANCHES['T001']}")
    assert ref_exists(pilot.root, f"refs/remotes/origin/{BRANCHES['T001']}")
    assert subprocess.run(["git", "config", "--get", f"branch.{BRANCHES['T001']}.merge"], cwd=pilot.root).returncode != 0
    assert branches.read(config, "T001") is not None
    assert claims.read(config, "T001") is None
    assert merged(pilot, "T001", "--cleanup", "--owner", "lane", capsys=capsys)["merged"] is True  # nothing left to remove


# 12


def test_cleanup_refusals_change_nothing(pilot, capsys, monkeypatch):
    config = load_config(pilot.root)
    unmerged = finished_lane(pilot, "T003", files=("three.py",))
    code, out, err = run(pilot.root, "autopilot", "merged", "T003", "--cleanup", "--json", capsys=capsys)
    assert code == 5 and "not merged" in err and json.loads(out)["cleanup"]["refused"]
    assert unmerged.exists()

    lane = finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    branch_ref = f"refs/heads/{BRANCHES['T001']}"

    def refused(*extra, root=None, expect=5, text=None):
        code, _, err = run(root or pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", *extra, capsys=capsys)
        assert code == expect, err
        if text:
            assert text in err
        assert lane.exists() and ref_exists(pilot.root, branch_ref)

    (lane / "base.py").write_text("changed\n")
    refused(text="uncommitted")
    git(lane, "checkout", "--", "base.py")
    (lane / "scratch.txt").write_text("untracked\n")
    refused(text="uncommitted")
    (lane / "scratch.txt").unlink()

    refused(root=lane, text="inside")
    monkeypatch.chdir(lane / "")
    refused(text="inside")
    monkeypatch.chdir(pilot.root)

    git(pilot.root, "worktree", "lock", str(lane))
    refused(text="locked")
    git(pilot.root, "worktree", "unlock", str(lane))

    claims.claim(config, "T001", owner="someone-else", branch=BRANCHES["T001"], worktree=str(lane))
    refused(expect=4, text="someone-else")
    claims.release(config, "T001", "someone-else")

    exclude = Path(git(pilot.root, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("*.log\n")
    (lane / "debug.log").write_text("ignored\n")
    code, _, err = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 0, err
    assert not lane.exists()


def test_cleanup_refuses_the_main_worktree(pilot, capsys):
    git(pilot.root, "switch", "-q", "-c", BRANCHES["T004"])
    assert main(["--root", str(pilot.root), "claim", "T004", "--owner", "lane"]) == 0
    pilot.work(pilot.root, "four.py")
    pilot.finish(pilot.root, "T004")
    pilot.host.squash(BRANCHES["T004"])
    code, _, err = run(pilot.root, "autopilot", "merged", "T004", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 5 and "main worktree" in err
    assert ref_exists(pilot.root, f"refs/heads/{BRANCHES['T004']}")


def test_cleanup_refuses_a_worktree_that_contains_other_worktrees(pilot, capsys, tmp_path):
    """A worktree nested in the lane's ignored directory is invisible to its status, and git worktree remove deletes it (T074)."""
    lane = finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    branch_ref = f"refs/heads/{BRANCHES['T001']}"
    exclude = Path(git(pilot.root, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(".worktrees/\n")
    nested = lane / ".worktrees" / "T003-nested"
    git(lane, "worktree", "add", "-q", str(nested), "-b", "T003-nested")
    (nested / "WORK.md").write_text("uncommitted work\n")
    git(lane, "worktree", "lock", str(nested))
    gone = lane / ".worktrees" / "gone"
    git(lane, "worktree", "add", "-q", str(gone), "-b", "gone")
    shutil.rmtree(gone)  # still registered, but its directory is gone: nothing of it can be lost
    assert git(lane, "status", "--porcelain", "--untracked-files=all") == ""

    def refused_naming(*inside):
        code, out, err = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", "--json", capsys=capsys)
        assert code == 5, err
        refused = json.loads(out)["cleanup"]["refused"]
        assert refused.startswith(f"the worktree {lane.resolve()} contains other worktrees: "), refused
        assert all(str(path.resolve()) in refused for path in inside) and str(gone.resolve()) not in refused
        assert refused in err
        assert (nested / "WORK.md").read_text() == "uncommitted work\n"
        assert lane.exists() and ref_exists(pilot.root, branch_ref)

    refused_naming(nested)
    visible = lane / "sub" / "T004-nested"  # not ignored: named as a worktree, not as untracked changes
    git(lane, "worktree", "add", "-q", str(visible), "-b", "T004-nested")
    refused_naming(nested, visible)

    git(pilot.root, "worktree", "unlock", str(nested))
    git(pilot.root, "worktree", "move", str(nested), str(tmp_path / "T003-nested"))
    git(pilot.root, "worktree", "move", str(visible), str(tmp_path / "T004-nested"))
    code, _, err = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 0, err
    assert not lane.exists() and not ref_exists(pilot.root, branch_ref)
    assert (tmp_path / "T003-nested" / "WORK.md").read_text() == "uncommitted work\n"


def test_cleanup_keeps_a_branch_that_moved_after_the_check(pilot, capsys, monkeypatch):
    from taskrail.autopilot import merged as merged_module

    finished_lane(pilot)
    pilot.host.squash(BRANCHES["T001"])
    original = merged_module._remove_worktree
    moved = {}

    def remove_then_commit(root, path):
        original(root, path)
        head = git(pilot.root, "rev-parse", BRANCHES["T001"])
        tree = git(pilot.root, "rev-parse", f"{head}^{{tree}}")
        moved["sha"] = git(pilot.root, "commit-tree", tree, "-p", head, "-m", "concurrent")
        git(pilot.root, "update-ref", f"refs/heads/{BRANCHES['T001']}", moved["sha"])

    monkeypatch.setattr(merged_module, "_remove_worktree", remove_then_commit)
    code, _, err = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 2, err
    assert sha(pilot.root, f"refs/heads/{BRANCHES['T001']}") == moved["sha"]


# 13


def test_a_claimed_stacked_dependent_gets_its_rebase_command(pilot, capsys):
    run_id = start(pilot, capsys)
    finished_lane(pilot, run_id=run_id)
    stacked = pilot.lane("T002", run_id, base=BRANCHES["T001"])
    pilot.work(stacked, "stacked.py")
    fork = claims.read(load_config(pilot.root), "T002").base["commit"]
    pilot.host.commit({"other.txt": "x"}, "unrelated")
    pilot.host.squash(BRANCHES["T001"])

    result = merged(pilot, "T001", "--run", run_id, capsys=capsys)
    assert result["dependents"] == [
        {
            "id": "T002",
            "branch": BRANCHES["T002"],
            "worktree": str(stacked.resolve()),
            "head": sha(stacked, "HEAD"),
            "stacked": True,
            "fork": fork,
            "fork_source": "claim",
            "onto": "origin/main",
            "command": f"git rebase --onto origin/main {fork}",
            "reason": None,
        }
    ]
    git(stacked, *result["dependents"][0]["command"].split()[1:])
    assert git(stacked, "log", "--format=%s", "origin/main..HEAD").splitlines() == ["work on stacked.py"]

    # Once rebased, the claim's fork point is no longer in the branch: no second rebase is offered.
    dependent = merged(pilot, "T001", "--run", run_id, capsys=capsys)["dependents"][0]
    assert (dependent["stacked"], dependent["fork_source"], dependent["command"]) == (False, "merge-base", None)


def test_a_finished_dependent_forks_from_the_dependency_head_even_after_cleanup(pilot, capsys):
    run_id = start(pilot, capsys)
    base = finished_lane(pilot, run_id=run_id)
    dependency_head = sha(base, "HEAD")
    stacked = pilot.lane("T002", base=BRANCHES["T001"])  # without --run, so no run keeps its base
    pilot.work(stacked, "stacked.py")
    pilot.finish(stacked, "T002")  # releases the claim and its recorded base
    pilot.host.squash(BRANCHES["T001"])
    pilot.host.delete(BRANCHES["T001"])

    result = merged(pilot, "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert result["cleanup"]["branch_deleted"] is True and result["cleanup"]["remote_branch"] is None
    dependent = result["dependents"][0]
    assert (dependent["fork"], dependent["fork_source"], dependent["stacked"]) == (dependency_head, "merge-base", True)

    again = merged(pilot, "T001", "--run", run_id, capsys=capsys)
    assert again["recorded"] is True
    dependent = again["dependents"][0]
    assert (dependent["fork"], dependent["fork_source"], dependent["command"]) == (
        dependency_head,
        "run",
        f"git rebase --onto origin/main {dependency_head}",
    )


def released_dependent_of_a_rebased_dependency(pilot, capsys):
    """The T033 F1 scenario: T002 stacked on T001 and marked done, then T001 rebased at hand-off and squash-merged."""
    run_id = start(pilot, capsys)
    base = finished_lane(pilot, run_id=run_id)
    fork = sha(base, "HEAD")
    stacked = pilot.lane("T002", run_id, base=BRANCHES["T001"])
    pilot.work(stacked, "stacked.py")
    pilot.finish(stacked, "T002")  # releases the claim and its recorded base
    pilot.host.commit({"other.txt": "x"}, "unrelated")
    git(base, "fetch", "-q", "origin")
    git(base, "rebase", "-q", "origin/main")
    git(base, "push", "-q", "--force-with-lease", "origin", BRANCHES["T001"])
    assert sha(base, "HEAD") != fork
    pilot.host.squash(BRANCHES["T001"])
    return run_id, fork, stacked


def fork_of(dependent):
    return {key: dependent[key] for key in ("stacked", "fork", "fork_source", "onto", "command", "reason")}


def test_a_released_dependent_keeps_its_fork_point_after_its_dependency_is_rebased(pilot, capsys):
    run_id, fork, stacked = released_dependent_of_a_rebased_dependency(pilot, capsys)

    result = merged(pilot, "T001", "--run", run_id, capsys=capsys)
    assert result["merged"] is True
    [dependent] = result["dependents"]
    assert fork_of(dependent) == {
        "stacked": True,
        "fork": fork,
        "fork_source": "run-base",
        "onto": "origin/main",
        "command": f"git rebase --onto origin/main {fork}",
        "reason": None,
    }
    git(stacked, *dependent["command"].split()[1:])
    assert git(stacked, "log", "--format=%s", "origin/main..HEAD").splitlines() == ["chore(T002): mark done", "work on stacked.py"]

    # Once rebased, the kept fork point is no longer in the branch: no second rebase is offered.
    again = merged(pilot, "T001", "--run", run_id, capsys=capsys)["dependents"][0]
    assert (again["stacked"], again["fork_source"], again["command"]) == (False, "merge-base", None)


def test_a_kept_base_counts_only_for_the_merged_dependency_and_an_existing_commit(pilot, capsys):
    run_id, fork, _ = released_dependent_of_a_rebased_dependency(pilot, capsys)
    config = load_config(pilot.root)
    dependent = merged(pilot, "T001", "--run", run_id, capsys=capsys)["dependents"][0]
    assert (dependent["fork"], dependent["fork_source"], dependent["stacked"]) == (fork, "run-base", True)
    kept = runs.read(config, run_id)["tasks"]["T002"]["base"]

    for label, changed in (
        ("another dependency", {**kept, "dependency": "T003"}),
        ("a missing commit", {**kept, "commit": "0" * 40}),
        ("no base, as in a run file older than T047", None),
    ):
        with runs.update(config, run_id) as stored:
            if changed is None:
                del stored["tasks"]["T002"]["base"]
            else:
                stored["tasks"]["T002"]["base"] = changed
        dependent = merged(pilot, "T001", "--run", run_id, capsys=capsys)["dependents"][0]
        assert (dependent["fork_source"], dependent["stacked"], dependent["command"]) == ("merge-base", False, None), label


def test_the_newest_run_keeping_a_base_wins(pilot, capsys):
    run_id, fork, _ = released_dependent_of_a_rebased_dependency(pilot, capsys)
    config = load_config(pilot.root)
    newer = start(pilot, capsys)
    kept = runs.read(config, run_id)["tasks"]["T002"]["base"]
    with runs.update(config, run_id) as stored:  # an older commit T002's head also contains
        stored["tasks"]["T002"]["base"] = {**kept, "commit": sha(pilot.root, f"{fork}~1")}
    with runs.update(config, newer) as stored:
        runs.lane(stored, "T002")["base"] = kept
    assert [run["id"] for run in runs.read_all(config)] == [newer, run_id]
    dependent = merged(pilot, "T001", capsys=capsys)["dependents"][0]
    assert (dependent["fork"], dependent["fork_source"]) == (fork, "run-base")


def test_a_dependent_branched_from_the_mainline_is_not_stacked(pilot, capsys):
    finished_lane(pilot)
    beside = pilot.lane("T002", base="origin/main")
    pilot.work(beside, "beside.py")
    pilot.host.squash(BRANCHES["T001"])
    dependent = merged(pilot, "T001", capsys=capsys)["dependents"][0]
    assert (dependent["id"], dependent["stacked"], dependent["command"]) == ("T002", False, None)


# 14


def test_text_and_json_forms(pilot, capsys):
    finished_lane(pilot)
    stacked = pilot.lane("T002", base=BRANCHES["T001"])
    pilot.work(stacked, "stacked.py")
    squash = pilot.host.squash(BRANCHES["T001"])
    result = merged(pilot, "T001", "--no-fetch", capsys=capsys)
    assert set(result) == {
        "id", "branch", "remote", "fetched", "mainline", "head", "done_at_head", "closed", "merged", "via", "commit",
        "recorded", "reason", "checks", "confirmations", "runs", "cleanup", "dependents",
    }
    assert set(result["mainline"]) == {"ref", "commit", "diverged"}
    assert result["cleanup"] is None

    code, out, _ = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", capsys=capsys)
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == f"T001 merged into origin/main via tree at {squash[:7]}"
    assert any(line.startswith("removed worktree ") for line in lines)
    assert f"deleted branch {BRANCHES['T001']}" in lines
    assert any(line.startswith("T002: git rebase --onto origin/main ") for line in lines)

    code, out, _ = run(pilot.root, "autopilot", "merged", "T002", capsys=capsys)
    assert code == 0 and out.startswith("T002 not merged into origin/main: ")


# 15 A branch whose task was discarded on it (T067)


def discarded_lane(pilot, task_id="T003", run_id=None, files=("three.py",)):
    path = pilot.lane(task_id, run_id)
    for name in files:
        pilot.work(path, name)
    pilot.discard(path, task_id)
    return path


def run_report(pilot, run_id, capsys):
    return data(pilot.root, "autopilot", "status", "--run", run_id, "--fetch", capsys=capsys)["runs"][0]


def state_of(report, task_id):
    return next(row["state"] for row in report["tasks"] if row["id"] == task_id)


def test_a_merged_discarded_branch_is_detected_and_reported(pilot, capsys):
    discarded_lane(pilot)
    squash = pilot.host.squash(BRANCHES["T003"])
    result = merged(pilot, "T003", capsys=capsys)
    assert (result["merged"], result["via"], result["commit"]) == (True, "tree", squash)
    assert (result["closed"], result["done_at_head"], result["reason"]) == ("discarded", False, None)
    assert (result["confirmations"]["row_discarded_on_mainline"], result["confirmations"]["row_done_on_mainline"]) == (True, False)


def test_a_recorded_discard_merge_reads_discarded_and_never_done_merged(pilot, capsys):
    run_id = start(pilot, capsys)
    discarded_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T003"])
    pilot.host.unmark("T003")  # the ❌ row edited back by hand: only the record knows the discard merged

    assert state_of(run_report(pilot, run_id, capsys), "T003") == "discarded-branch"
    result = merged(pilot, "T003", "--run", run_id, capsys=capsys)
    assert (result["merged"], result["runs"]) == (True, [run_id])
    assert runs.read(load_config(pilot.root), run_id)["tasks"]["T003"]["merged"]["status"] == "discarded"

    report = run_report(pilot, run_id, capsys)
    assert (state_of(report, "T003"), report["done_merged"], report["complete"]) == ("discarded", 0, False)


def test_cleanup_removes_a_merged_discarded_branch(pilot, capsys):
    run_id = start(pilot, capsys)
    lane = discarded_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T003"])
    config = load_config(pilot.root)
    claims.claim(config, "T003", owner="lane", branch=BRANCHES["T003"], worktree=str(lane))  # a claim left behind

    result = merged(pilot, "T003", "--cleanup", "--owner", "lane", capsys=capsys)
    assert result["cleanup"] == {
        "worktree": str(lane.resolve()),
        "worktree_removed": True,
        "branch_deleted": True,
        "claim_released": True,
        "remote_branch": f"origin/{BRANCHES['T003']}",
        "refused": None,
    }
    assert not lane.exists()
    assert not ref_exists(pilot.root, f"refs/heads/{BRANCHES['T003']}")
    assert ref_exists(pilot.root, f"refs/remotes/origin/{BRANCHES['T003']}")
    assert claims.read(config, "T003") is None

    pilot.host.delete(BRANCHES["T003"])  # no copy of the branch is left: only the run knows the merge
    again = merged(pilot, "T003", capsys=capsys)
    assert (again["merged"], again["recorded"], again["closed"], again["commit"]) == (True, True, "discarded", result["commit"])


def test_a_done_merge_records_done_and_a_record_without_status_counts_as_done(pilot, capsys):
    run_id = start(pilot, capsys)
    finished_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T001"])
    pilot.host.unmark("T001")
    result = merged(pilot, "T001", "--run", run_id, capsys=capsys)
    assert (result["merged"], result["closed"], result["done_at_head"]) == (True, "done", True)
    config = load_config(pilot.root)
    assert runs.read(config, run_id)["tasks"]["T001"]["merged"]["status"] == "done"
    assert state_of(run_report(pilot, run_id, capsys), "T001") == "done-merged"

    with runs.update(config, run_id) as stored:
        del stored["tasks"]["T001"]["merged"]["status"]  # as written before T067
    assert state_of(run_report(pilot, run_id, capsys), "T001") == "done-merged"


def test_the_newest_recorded_merge_decides_the_status(pilot, capsys):
    run_id = start(pilot, capsys)
    other = start(pilot, capsys)
    discarded_lane(pilot, run_id=run_id)
    pilot.host.squash(BRANCHES["T003"])
    pilot.host.unmark("T003")
    merged(pilot, "T003", "--run", run_id, capsys=capsys)
    config = load_config(pilot.root)
    record = runs.read(config, run_id)["tasks"]["T003"]["merged"]

    for detected, expected in (("2000-01-01T00:00:00+00:00", "discarded"), ("2999-01-01T00:00:00+00:00", "done-merged")):
        with runs.update(config, other) as stored:
            runs.lane(stored, "T003")["merged"] = {**record, "status": "done", "detected": detected}
        assert state_of(run_report(pilot, run_id, capsys), "T003") == expected, detected


def test_the_text_form_names_a_discarded_merge(pilot, capsys):
    discarded_lane(pilot)
    squash = pilot.host.squash(BRANCHES["T003"])
    code, out, _ = run(pilot.root, "autopilot", "merged", "T003", capsys=capsys)
    assert code == 0
    assert out.splitlines()[0] == f"T003 merged into origin/main via tree at {squash[:7]} (discarded)"


def test_recorded_merges_resolve_the_mainline_refs_once_per_backlog(pilot, capsys, monkeypatch):
    run_id = start(pilot, capsys)
    on_main = sha(pilot.root, "main")
    stray = pilot.lane("T003", run_id)
    pilot.work(stray, "stray.py")
    records = {"T001": (on_main, "done"), "T002": (on_main, "done"), "T003": (sha(stray, "HEAD"), "done"), "T004": (on_main, "discarded")}
    with runs.update(load_config(pilot.root), run_id) as stored:
        for task_id, (commit, closed) in records.items():
            runs.lane(stored, task_id)["merged"] = {"via": "tree", "commit": commit, "head": commit, "mainline": "main", "detected": "x", "status": closed}
    project, _ = pilot.load()
    resolved = []
    original = merged_module.resolve_remote
    monkeypatch.setattr(merged_module, "resolve_remote", lambda *args: resolved.append(args) or original(*args))

    found = merged_module.recorded_merges(project)

    assert found == {"T001": "done", "T002": "done", "T004": "discarded"}  # T003's commit is on no mainline
    assert len(resolved) == 1  # one backlog, four records (T126)
