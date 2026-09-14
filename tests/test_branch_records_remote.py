"""Mirroring branch records to a remote ref, so another clone resolves a renamed branch (T036)."""

import json
from pathlib import Path

import pytest
from conftest import BASE_CONFIG, git

from taskrail import branches
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
NAME = "feature/base"
REF = "refs/taskrail/branches/T001"
COPY = "refs/taskrail/remotes/origin/branches/T001"
MIRRORED = BASE_CONFIG + '\n[git]\nbranch_record_remote = "origin"\n'


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


def refs(root, pattern):
    return git(root, "for-each-ref", "--format=%(refname)", pattern)


def local_record(root, task_id):
    return branches.read(load_config(root), task_id)


def at(monkeypatch, timestamp):
    """Make every record written from now on carry `timestamp` as `recorded`."""
    monkeypatch.setattr(branches, "_now", lambda: timestamp)


def setup_origin(git_repo, tmp_path_factory, config):
    git_repo.write(".taskrail/config.toml", config)
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git(git_repo.root, "fetch", "-q", "origin")
    git_repo.bare = bare

    def open_lane(root, branch, base="origin/main"):
        path = tmp_path_factory.mktemp("lanes") / "lane"
        git(root, "worktree", "add", "-q", str(path), "-b", branch, base)
        return path

    def clone():
        path = tmp_path_factory.mktemp("clones") / "clone"
        git(bare.parent, "clone", "-q", str(bare), str(path))
        return path

    git_repo.open_lane = open_lane
    git_repo.clone = clone
    return git_repo


@pytest.fixture
def mirrored(git_repo, tmp_path_factory):
    """Clone A of a bare origin, with branch records mirrored to it; `clone()` makes more clones."""
    return setup_origin(git_repo, tmp_path_factory, MIRRORED)


@pytest.fixture
def unmirrored(git_repo, tmp_path_factory):
    return setup_origin(git_repo, tmp_path_factory, BASE_CONFIG)


def finish_renamed_t001(repo, capsys):
    """In clone A: T001 claimed, renamed to NAME, marked done there and its branch pushed."""
    lane = repo.open_lane(repo.root, T001)
    assert run(lane, "claim", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    assert data(lane, "branch", "T001", NAME, "--owner", "lane", capsys=capsys)["record_remote"]["pushed"] is True
    assert run(lane, "done", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    commit_all(lane, "chore(T001): mark done")
    git(lane, "push", "-q", "origin", NAME)
    return lane


# 1


def test_nothing_is_mirrored_when_the_setting_is_off(unmirrored, capsys):
    repo = unmirrored
    assert data(repo.root, "branch", "T003", "bug/three", capsys=capsys)["record_remote"] is None
    lane = repo.open_lane(repo.root, T001)
    claimed = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (claimed["branch_recorded"], claimed["record_remote"]) == (True, None)
    code, out, err = run(repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Fresh", "--workspace",
                         "--branch", "feature/new", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["record_remote"] is None
    for argv in (("show", "T001"), ("list",), ("next",)):
        code, _, err = run(repo.root, *argv, "--fetch", capsys=capsys)
        assert (code, err) == (0, "")
    assert refs(repo.bare, "refs/taskrail/branches") == ""
    assert refs(repo.root, "refs/taskrail") == ""


def test_a_non_string_setting_is_a_configuration_error(unmirrored, capsys):
    unmirrored.write(".taskrail/config.toml", BASE_CONFIG + "\n[git]\nbranch_record_remote = 1\n")
    code, _, err = run(unmirrored.root, "validate", capsys=capsys)
    assert code == 2
    assert "branch_record_remote" in err


# 2 and 10


def test_branch_pushes_a_public_parentless_record(mirrored, capsys):
    repo = mirrored
    result = data(repo.root, "branch", "T001", NAME, capsys=capsys)
    pushed = result["record_remote"]
    commit = git(repo.bare, "rev-parse", REF)
    assert pushed == {"name": "origin", "ref": REF, "commit": commit, "pushed": True, "error": None}
    assert git(repo.root, "rev-parse", COPY) == commit

    raw = git(repo.bare, "cat-file", "-p", commit)
    assert "\nparent " not in raw and not raw.startswith("parent ")
    assert git(repo.bare, "log", "-1", "--format=%an <%ae>|%cn <%ce>|%s", commit) == (
        "taskrail <taskrail@localhost>|taskrail <taskrail@localhost>|taskrail branch T001"
    )
    assert git(repo.bare, "ls-tree", "--name-only", commit) == "branch.json"
    published = json.loads(git(repo.bare, "show", f"{commit}:branch.json"))
    stored = local_record(repo.root, "T001")
    assert published == {"id": "T001", "branch": NAME, "recorded": stored.recorded}

    assert data(repo.root, "show", "T001", capsys=capsys)["prior_work"]["commits"] == []


# 3


def test_claim_pushes_only_the_record_it_freezes(mirrored, capsys):
    repo = mirrored
    lane = repo.open_lane(repo.root, T001)
    frozen = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert frozen["branch_recorded"] is True
    assert frozen["record_remote"]["pushed"] is True
    assert json.loads(git(repo.bare, "show", f"{REF}:branch.json"))["branch"] == T001

    elsewhere = repo.open_lane(repo.root, "elsewhere")
    other = data(elsewhere, "claim", "T003", "--owner", "lane", capsys=capsys)
    assert (other["branch_recorded"], other["record_remote"]) == (False, None)

    assert run(lane, "release", "T001", "--owner", "lane", capsys=capsys)[0] == 0
    again = data(lane, "claim", "T001", "--owner", "lane", capsys=capsys)
    assert (again["branch_recorded"], again["record_remote"]) == (False, None)
    assert refs(repo.bare, "refs/taskrail/branches") == REF


def test_new_workspace_with_a_branch_pushes_its_record(mirrored, capsys):
    repo = mirrored
    code, out, err = run(repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Fresh", "--workspace",
                         "--branch", "feature/new", "--json", capsys=capsys)
    assert code == 0, err
    result = json.loads(out)
    assert result["record_remote"]["pushed"] is True
    assert json.loads(git(repo.bare, "show", "refs/taskrail/branches/T004:branch.json"))["branch"] == "feature/new"


# 4


def test_local_only_neither_fetches_nor_pushes_records(mirrored, capsys):
    repo = mirrored
    other = repo.clone()
    assert data(other, "branch", "T003", "bug/three", capsys=capsys)["record_remote"]["pushed"] is True

    lane = repo.open_lane(repo.root, T001)
    claimed = data(lane, "claim", "T001", "--owner", "lane", "--local-only", capsys=capsys)
    assert (claimed["branch_recorded"], claimed["record_remote"]) == (True, None)
    renamed = data(lane, "branch", "T001", NAME, "--owner", "lane", "--local-only", capsys=capsys)
    assert renamed["record_remote"] is None
    assert refs(repo.bare, "refs/taskrail/branches") == "refs/taskrail/branches/T003"
    assert refs(repo.root, "refs/taskrail/remotes") == ""
    assert local_record(repo.root, "T003") is None


# 5


def test_each_push_leases_on_the_previous_commit(mirrored, capsys, monkeypatch):
    repo = mirrored
    at(monkeypatch, "2026-01-01T00:00:01+00:00")
    first = data(repo.root, "branch", "T001", NAME, capsys=capsys)["record_remote"]["commit"]
    at(monkeypatch, "2026-01-01T00:00:02+00:00")
    second = data(repo.root, "branch", "T001", NAME, capsys=capsys)["record_remote"]
    assert second["pushed"] is True and second["commit"] != first
    assert git(repo.bare, "rev-parse", REF) == second["commit"] == git(repo.root, "rev-parse", COPY)


def test_a_record_changed_by_another_clone_meanwhile_is_not_overwritten(mirrored, capsys, monkeypatch):
    repo = mirrored
    at(monkeypatch, "2026-01-01T00:00:01+00:00")
    assert data(repo.root, "branch", "T001", NAME, capsys=capsys)["record_remote"]["pushed"] is True
    other = repo.clone()
    at(monkeypatch, "2026-01-01T00:00:02+00:00")
    theirs = data(other, "branch", "T001", "their/name", capsys=capsys)["record_remote"]
    assert theirs["pushed"] is True

    # Clone A pushes before it has seen that change: the fetch happens, but the race is simulated.
    monkeypatch.setattr(branches, "fetch", lambda config: ([], None))
    at(monkeypatch, "2026-01-01T00:00:03+00:00")
    code, out, err = run(repo.root, "branch", "T001", "our/name", "--json", capsys=capsys)
    assert code == 0
    mine = json.loads(out)["record_remote"]
    assert (mine["pushed"], mine["commit"]) == (False, None)
    assert mine["error"]
    assert "warning" in err and REF in err
    assert local_record(repo.root, "T001").branch == "our/name"
    assert git(repo.bare, "rev-parse", REF) == theirs["commit"]


# 6


def test_show_fetch_resolves_a_branch_renamed_in_another_clone(mirrored, capsys):
    repo = mirrored
    finish_renamed_t001(repo, capsys)
    other = repo.clone()

    plain = data(other, "show", "T001", capsys=capsys)
    assert (plain["branch"], plain["branch_source"], plain["state"]) == (T001, "template", "pending")
    assert refs(other, "refs/taskrail") == ""

    fetched = data(other, "show", "T001", "--fetch", capsys=capsys)
    assert (fetched["branch"], fetched["branch_source"], fetched["state"]) == (NAME, "recorded", "done-branch")
    base = data(other, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["dependency"]) == (f"origin/{NAME}", "T001")


def test_list_and_next_fetch_agree(mirrored, capsys):
    repo = mirrored
    finish_renamed_t001(repo, capsys)

    listed = {t["id"]: t for t in data(repo.clone(), "list", "--fetch", capsys=capsys)}
    assert (listed["T001"]["branch"], listed["T001"]["state"], listed["T002"]["state"]) == (NAME, "done-branch", "pending")

    unfetched = [t["id"] for t in data(repo.clone(), "next", capsys=capsys)]
    assert "T002" not in unfetched
    eligible = [t["id"] for t in data(repo.clone(), "next", "--fetch", capsys=capsys)]
    assert "T002" in eligible and "T001" not in eligible


# 7


def test_review_fetches_records_before_resolving_the_task_branch(mirrored, capsys):
    repo = mirrored
    finish_renamed_t001(repo, capsys)

    other = repo.clone()
    git(other, "switch", "-q", NAME)
    assert data(other, "review", "T001", capsys=capsys)["head"] == NAME

    unfetched = repo.clone()
    git(unfetched, "switch", "-q", NAME)
    code, _, err = run(unfetched, "review", "T001", "--no-fetch", capsys=capsys)
    assert code == 5
    assert f"task branch {T001}" in err
    assert refs(unfetched, "refs/taskrail") == ""


def test_claim_fetches_records_first(mirrored, capsys):
    repo = mirrored
    finish_renamed_t001(repo, capsys)
    other = repo.clone()
    git(other, "switch", "-q", "-c", "T002-depends-on-base", f"origin/{NAME}")
    claimed = data(other, "claim", "T002", "--owner", "b", capsys=capsys)
    assert claimed["claim"]["base"]["dependency"] == "T001"


def test_branch_fetches_records_first(mirrored, capsys):
    repo = mirrored
    assert data(repo.root, "branch", "T001", NAME, capsys=capsys)["record_remote"]["pushed"] is True
    other = repo.clone()
    code, _, err = run(other, "branch", "T003", NAME, capsys=capsys)
    assert code == 5
    assert f"{NAME} is the branch of T001" in err


def test_new_workspace_fetches_records_first(mirrored, capsys):
    repo = mirrored
    finish_renamed_t001(repo, capsys)
    other = repo.clone()
    code, out, err = run(other, "new", "--epic", "E01", "--kind", "feature", "--title", "Stacked", "--depends-on", "T001",
                         "--workspace", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["base"] == f"origin/{NAME}"


# 8


def test_the_later_record_wins_and_a_fetch_never_deletes_one(mirrored, capsys, monkeypatch):
    repo = mirrored
    other = repo.clone()
    at(monkeypatch, "2026-01-01T00:00:01+00:00")
    assert data(repo.root, "branch", "T003", "a/early", capsys=capsys)["record_remote"]["pushed"] is True

    at(monkeypatch, "2026-01-01T00:00:02+00:00")
    assert data(other, "branch", "T003", "b/later", "--local-only", capsys=capsys)["record_remote"] is None
    assert data(other, "show", "T003", "--fetch", capsys=capsys)["branch"] == "b/later"

    at(monkeypatch, "2026-01-01T00:00:01+00:00")
    assert data(other, "branch", "T003", "b/tie", "--local-only", capsys=capsys)["record_remote"] is None
    assert data(other, "show", "T003", "--fetch", capsys=capsys)["branch"] == "b/tie"

    at(monkeypatch, "2026-01-01T00:00:03+00:00")
    assert data(repo.root, "branch", "T003", "a/latest", capsys=capsys)["record_remote"]["pushed"] is True
    assert data(other, "show", "T003", "--fetch", capsys=capsys)["branch"] == "a/latest"
    adopted = local_record(other, "T003")
    assert (adopted.branch, adopted.recorded) == ("a/latest", "2026-01-01T00:00:03+00:00")

    git(repo.root, "push", "-q", "origin", ":refs/taskrail/branches/T003")
    assert data(other, "show", "T003", "--fetch", capsys=capsys)["branch"] == "a/latest"
    assert refs(other, "refs/taskrail/remotes") == ""
    assert local_record(other, "T003").branch == "a/latest"


# 9


def test_an_unreachable_remote_only_warns(mirrored, capsys, tmp_path):
    repo = mirrored
    git(repo.root, "remote", "set-url", "origin", str(tmp_path / "missing.git"))

    code, out, err = run(repo.root, "show", "T001", "--fetch", "--json", capsys=capsys)
    assert code == 0
    assert json.loads(out)["branch"] == T001
    assert "warning" in err

    code, out, err = run(repo.root, "branch", "T001", NAME, "--json", capsys=capsys)
    assert code == 0
    pushed = json.loads(out)["record_remote"]
    assert (pushed["pushed"], pushed["commit"]) == (False, None) and pushed["error"]
    assert "warning" in err
    assert local_record(repo.root, "T001").branch == NAME

    code, out, err = run(repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Offline", "--workspace",
                         "--branch", "feature/offline", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["record_remote"]["pushed"] is False
    assert "warning" in err
    assert Path(json.loads(out)["workspace"]).is_dir()
