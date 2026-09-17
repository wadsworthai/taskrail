"""Closing a task on the checked-out branch: `review` reports and never fetches, rebases or publishes (T083, DESIGN.md §7.1)."""

import json

import pytest
from conftest import BASE_CONFIG, git

from taskrail.cli import main

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
| ⬜ | T002 | bug     | 1   | —          | Independent     | —           |
"""

CURRENT = '\n[git]\nworktree = "never"\ntask_branch = "current"\n'
PUBLISH_REFUSAL = 'taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves'


def config(git_table: str = CURRENT) -> str:
    head, _ = BASE_CONFIG.split("[checks]")
    return head + '[checks]\ntest = "true"\n' + git_table


def run(root, *argv, capsys):
    capsys.readouterr()
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


def commit_file(repo, name, message):
    repo.write(name, message + "\n")
    commit_all(repo.root, message)


@pytest.fixture
def current(git_repo, tmp_path_factory):
    """A current-branch repository whose main tracks a bare origin."""
    git_repo.write(".taskrail/config.toml", config())
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "-u", "origin", "main")
    git_repo.bare = bare
    return git_repo


def close(repo, task_id, capsys, message=None):
    """Claim, commit a change naming the task, mark it done and commit that."""
    assert run(repo.root, "claim", task_id, capsys=capsys)[0] == 0
    commit_file(repo, f"{task_id}.txt", message or f"feat(demo): add a file ({task_id})")
    assert run(repo.root, "done", task_id, capsys=capsys)[0] == 0
    commit_all(repo.root, f"chore(backlog): mark {task_id} done")


# 1, 3, 5
def test_review_reports_on_the_mainline(current, capsys):
    close(current, "T001", capsys)
    result = data(current.root, "review", "T001", capsys=capsys)
    assert result["id"] == "T001"
    assert result["head"] == "main"
    assert result["target"] == "main"
    assert result["remote"] == "origin"
    assert result["fetched"] is False
    assert result["rebase"]["enabled"] is False
    assert result["rebase"]["needed"] is False
    assert result["rebase"]["onto"] is None
    assert result["rebase"]["reason"] == '[git].task_branch is "current": review does not rebase'
    assert result["push"] == {"enabled": False, "pushed": False, "command": None, "error": None}
    assert result["pull_request"]["title"] == "feat: base task (T001)"
    assert result["pull_request"]["body"].startswith("Task: T001 — Base task")
    assert result["pull_request"]["url"] is None
    assert result["published"] is False
    assert result["upstream"] == {"ref": "origin/main", "ahead": 2}


# 1: the title follows --type, --scope and --breaking as under "task"
def test_review_title_options(current, capsys):
    close(current, "T001", capsys)
    result = data(current.root, "review", "T001", "--type", "fix", "--scope", "cli", "--breaking", capsys=capsys)
    assert result["pull_request"]["title"] == "fix(cli)!: base task (T001)"


# 2
def test_review_fetches_and_pushes_nothing(current, tmp_path_factory, capsys):
    other = tmp_path_factory.mktemp("other") / "clone"
    git(current.root, "clone", "-q", str(current.bare), str(other))
    (other / "remote.txt").write_text("remote\n", encoding="utf-8")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "remote change")
    git(other, "push", "-q", "origin", "main")
    remote_main = git(other, "rev-parse", "HEAD")
    tracking_before = git(current.root, "rev-parse", "origin/main")

    close(current, "T001", capsys)
    result = data(current.root, "review", "T001", capsys=capsys)

    assert result["fetched"] is False
    assert git(current.root, "rev-parse", "origin/main") == tracking_before
    assert git(current.root, "--git-dir", str(current.bare), "rev-parse", "main") == remote_main


# 3
def test_review_runs_on_any_branch(current, capsys):
    git(current.root, "switch", "-q", "-c", "work")
    close(current, "T001", capsys)
    result = data(current.root, "review", "T001", capsys=capsys)
    assert result["head"] == "work"
    assert result["target"] == "main"
    assert result["upstream"] is None  # 5: no upstream


# 4
def test_commits_on_head_in_the_three_forms(current, capsys):
    commit_file(current, "a.txt", "T001 start")  # prefix
    commit_file(current, "b.txt", "feat(T001): scoped")  # scope
    commit_file(current, "c.txt", "mentions T001 in the middle")  # ignored
    git(current.root, "switch", "-q", "-c", "elsewhere")
    commit_file(current, "d.txt", "feat: on another branch (T001)")
    git(current.root, "switch", "-q", "main")
    close(current, "T001", capsys, "feat(demo): squashed title (T001) (#12)")  # suffix
    result = data(current.root, "review", "T001", capsys=capsys)
    assert [(c["subject"], c["match"]) for c in result["commits"]] == [
        ("feat(demo): squashed title (T001) (#12)", "suffix"),
        ("feat(T001): scoped", "scope"),
        ("T001 start", "prefix"),
    ]
    assert result["commits_total"] == 3
    assert all(len(c["sha"]) == 40 for c in result["commits"])


# 4
def test_commits_are_capped_at_ten(current, capsys):
    for number in range(12):
        commit_file(current, f"f{number}.txt", f"T001 step {number}")
    close(current, "T001", capsys, "T001 step 12")
    result = data(current.root, "review", "T001", capsys=capsys)
    assert len(result["commits"]) == 10
    assert result["commits_total"] == 13
    assert result["commits"][0]["subject"] == "T001 step 12"


# 4 (decision 4): a gone upstream reads as none
def test_upstream_gone_is_null(current, capsys):
    close(current, "T001", capsys)
    git(current.root, "update-ref", "-d", "refs/remotes/origin/main")
    result = data(current.root, "review", "T001", capsys=capsys)
    assert result["upstream"] is None


# 5: ahead counts only what the upstream lacks
def test_upstream_ahead_after_a_push(current, capsys):
    close(current, "T001", capsys)
    git(current.root, "push", "-q", "origin", "main")
    commit_file(current, "later.txt", "later work")
    result = data(current.root, "review", "T001", capsys=capsys)
    assert result["upstream"] == {"ref": "origin/main", "ahead": 1}


# decision 3: a detached HEAD is not refused
def test_detached_head_is_reported(current, capsys):
    close(current, "T001", capsys)
    git(current.root, "switch", "-q", "--detach", "HEAD")
    result = data(current.root, "review", "T001", capsys=capsys)
    assert result["head"] is None
    assert result["upstream"] is None
    assert result["commits_total"] == 1


# decision 2: Reopens trailers only from what a push would send
def test_reopens_since_the_upstream(current, capsys):
    git(current.root, "commit", "-q", "--allow-empty", "-m", "reopen T002\n\nReopens: T002")
    git(current.root, "push", "-q", "origin", "main")
    git(current.root, "commit", "-q", "--allow-empty", "-m", "reopen T001 before\n\nReopens: T001")
    close(current, "T001", capsys)
    body = data(current.root, "review", "T001", capsys=capsys)["pull_request"]["body"]
    assert "Reopens: T001" in body
    assert "Reopens: T002" not in body


def test_reopens_without_an_upstream_read_all_of_head(current, capsys):
    git(current.root, "commit", "-q", "--allow-empty", "-m", "reopen T002\n\nReopens: T002")
    git(current.root, "switch", "-q", "-c", "work")
    close(current, "T001", capsys)
    body = data(current.root, "review", "T001", capsys=capsys)["pull_request"]["body"]
    assert "Reopens: T002" in body


# 6
def test_publish_is_refused_before_anything_else(current, capsys):
    before = git(current.root, "--git-dir", str(current.bare), "rev-parse", "main")
    code, out, err = run(current.root, "review", "T001", "--publish", "--json", capsys=capsys)  # T001 is pending
    assert code == 5
    assert err.strip() == PUBLISH_REFUSAL
    assert out == ""
    close(current, "T001", capsys)
    code, _, err = run(current.root, "review", "T001", "--publish", capsys=capsys)
    assert code == 5
    assert err.strip() == PUBLISH_REFUSAL
    assert git(current.root, "--git-dir", str(current.bare), "rev-parse", "main") == before


# 7
def test_pending_and_unknown_tasks(current, capsys):
    code, _, err = run(current.root, "review", "T001", capsys=capsys)
    assert code == 5
    assert "run `taskrail done T001`" in err
    code, _, _ = run(current.root, "review", "T999", capsys=capsys)
    assert code == 3


# 1: a discarded task is reported too, with a chore title
def test_discarded_task_is_reported(current, capsys):
    assert run(current.root, "discard", "T002", capsys=capsys)[0] == 0
    commit_all(current.root, "chore(backlog): discard T002")
    result = data(current.root, "review", "T002", capsys=capsys)
    assert result["pull_request"]["title"] == "chore: independent (T002)"


# 8
def test_text_output(current, capsys):
    close(current, "T001", capsys)
    code, out, _ = run(current.root, "review", "T001", capsys=capsys)
    assert code == 0
    sha = git(current.root, "rev-parse", "--short=7", "HEAD~1")
    assert out.splitlines() == [
        'T001 done on main; review reports only ([git].task_branch is "current")',
        "1 commit(s) naming T001:",
        f"  {sha} feat(demo): add a file (T001)",
        "upstream origin/main: 2 commit(s) not pushed",
        "reference title: feat: base task (T001)",
        "push with git once the human approves",
    ]


# 9
def test_show_close_review(current, capsys):
    assert data(current.root, "show", "T001", capsys=capsys)["close"] == {"commit": "stages", "review": "report"}
    current.write(".taskrail/config.toml", config(""))
    assert data(current.root, "show", "T001", capsys=capsys)["close"] == {"commit": "stages", "review": "publish"}
