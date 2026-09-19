"""A run whose finished tasks `taskrail archive` moved out of the backlog still resolves them (T121)."""

import json

import pytest
from conftest import BASE_CONFIG, git

from taskrail.autopilot import runs
from taskrail.autopilot import status as status_module
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.model import Status

TODO = """
# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | Demo | Try lanes | —    |

## E01 — Demo

| ✓  | ID   | Kind    | Pts | Depends On | Title        | Description |
|----|------|---------|-----|------------|--------------|-------------|
| ⬜ | T001 | feature | 1   | —          | First lane   | —           |
| ⬜ | T002 | bug     | 1   | —          | Second lane  | —           |
| ⬜ | T003 | chore   | 1   | —          | Dropped lane | —           |
| ⬜ | T004 | chore   | 1   | —          | Still to do  | —           |
"""

LANES = {"T001": ("✅", "done-merged"), "T002": ("✅", "done-merged"), "T003": ("❌", "discarded")}


def data(root, *argv, capsys):
    capsys.readouterr()
    code = main(["--root", str(root), *argv, "--json"])
    out, err = capsys.readouterr()
    assert code == 0, err
    return json.loads(out)


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def finished_run(repo, capsys, record: bool) -> str:
    """A count-2 run whose three lanes were closed and merged on `main`, with or without `autopilot merged` records."""
    repo.write(".taskrail/config.toml", BASE_CONFIG + "\n[autopilot]\nenabled = true\nmax_lanes = 10\n")
    repo.write("TODO.md", TODO)
    commit_all(repo.root, "backlog")
    run_id = data(repo.root, "autopilot", "start", "--count", "2", capsys=capsys)["run"]["id"]

    todo = (repo.root / "TODO.md").read_text(encoding="utf-8")
    for task_id, (cell, _) in LANES.items():
        todo = todo.replace(f"| ⬜ | {task_id} |", f"| {cell} | {task_id} |")
    (repo.root / "TODO.md").write_text(todo, encoding="utf-8")
    commit_all(repo.root, "merge the lanes")
    merge = git(repo.root, "rev-parse", "HEAD")

    with runs.update(load_config(repo.root), run_id) as run:
        for task_id, (cell, _) in LANES.items():
            lane = runs.lane(run, task_id)
            if record:
                closed = "done" if cell == "✅" else "discarded"
                lane["merged"] = {"via": "tree", "commit": merge, "head": merge, "mainline": "main", "detected": "2026-01-01T00:00:00+00:00", "status": closed}
    return run_id


def archive(repo, capsys):
    result = data(repo.root, "archive", capsys=capsys)
    assert result["backlogs"][0]["archived"] == ["T001", "T002", "T003"]
    commit_all(repo.root, "archive")


def report(repo, capsys, run_id):
    found = data(repo.root, "autopilot", "status", "--run", run_id, capsys=capsys)["runs"][0]
    return found, {row["id"]: row for row in found["tasks"]}


@pytest.mark.parametrize("record", [False, True], ids=["without-merge-record", "with-merge-record"])
def test_status_resolves_a_run_whose_tasks_are_archived(git_repo, capsys, record):
    run_id = finished_run(git_repo, capsys, record)
    before, before_rows = report(git_repo, capsys, run_id)
    archive(git_repo, capsys)
    after, rows = report(git_repo, capsys, run_id)

    assert (before["complete"], before["done_merged"]) == (True, 2)
    assert (after["complete"], after["done_merged"]) == (True, 2)
    for task_id, (_, state) in LANES.items():
        assert rows[task_id]["state"] == state
        assert rows[task_id]["title"] == before_rows[task_id]["title"]
        assert rows[task_id]["kind"] == before_rows[task_id]["kind"]
        assert "problem" not in rows[task_id]
    assert set(rows[task_id]) == set(before_rows[task_id])  # an archived member is a normal task row


def test_a_recorded_merge_still_counts_for_an_archived_task(git_repo, capsys):
    finished_run(git_repo, capsys, record=True)
    archive(git_repo, capsys)
    project, _ = git_repo.load()

    assert status_module._recorded(project, Status.DONE) == {"T001", "T002"}
    assert status_module._recorded(project, Status.DISCARDED) == {"T003"}


@pytest.mark.parametrize("record", [False, True], ids=["without-merge-record", "with-merge-record"])
def test_next_does_not_dispatch_past_the_count_of_a_run_whose_tasks_are_archived(git_repo, capsys, record):
    run_id = finished_run(git_repo, capsys, record)
    archive(git_repo, capsys)

    result = data(git_repo.root, "autopilot", "next", "--run", run_id, capsys=capsys)

    assert result["dispatch"] == []
    assert result["limited_by"] == "count"


def test_the_backlog_commands_stay_blind_to_the_archive(git_repo, capsys):
    finished_run(git_repo, capsys, record=False)
    archive(git_repo, capsys)

    listed = data(git_repo.root, "list", capsys=capsys)
    assert [task["id"] for task in listed] == ["T004"]
    assert main(["--root", str(git_repo.root), "show", "T001", "--json"]) == 3
