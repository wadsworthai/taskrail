"""`autopilot next`: dispatch within lanes, kinds, groups, the run's count and resource pools (T030)."""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from conftest import BASE_CONFIG, git

from taskrail.autopilot import runs
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.issues import ConfigError
from taskrail.predicates import ColumnPredicate

CONFIG = BASE_CONFIG.replace("custom = []", 'custom = ["Area"]')

TODO = """
# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | Demo | Try lanes | —    |

## E01 — Demo

| ✓  | ID   | Kind    | Pts | Depends On | Title       | Description | Area |
|----|------|---------|-----|------------|-------------|-------------|------|
| ⬜ | T001 | feature | 1   | —          | First ui    | —           | ui   |
| ⬜ | T002 | bug     | 1   | —          | Second ui   | —           | UI   |
| ⬜ | T003 | chore   | 2   | —          | Api work    | —           | api  |
| ⬜ | T004 | feature | 2   | T001       | After first | —           | api  |
| ⬜ | T005 | bug     | 3   | —          | Late bug    | —           | —    |
| ⬜ | T006 | chore   | 3   | —          | Late chore  | —           | —    |
| ⬜ | T007 | chore   | 5   | T003, T005 | Needs two   | —           | —    |
"""


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


def configure(repo, autopilot="", enabled=True):
    head = "\n[autopilot]\nenabled = true\n" if enabled else "\n[autopilot]\nenabled = false\n"
    repo.write(".taskrail/config.toml", CONFIG + head + autopilot)


@pytest.fixture
def pilot(git_repo, tmp_path_factory):
    """A repository with the autopilot enabled, a bare origin, and helpers to claim and finish lanes."""
    configure(git_repo, "max_lanes = 10\n")
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare
    git_repo.worktrees = {}

    def lane(task_id, run_id=None):
        shown = json.loads(_quiet(git_repo.root, "show", task_id, "--json"))
        path = tmp_path_factory.mktemp("lanes") / shown["branch"]
        git(git_repo.root, "worktree", "add", "-q", str(path), "-b", shown["branch"], shown["base"]["onto"])
        argv = ["--root", str(path), "claim", task_id, "--owner", "lane"] + (["--run", run_id] if run_id else [])
        assert main(argv) == 0
        git_repo.worktrees[task_id] = path
        return path

    def finish(task_id):
        path = git_repo.worktrees[task_id]
        assert main(["--root", str(path), "done", task_id, "--owner", "lane"]) == 0
        commit_all(path, f"chore({task_id}): mark done")

    git_repo.lane = lane
    git_repo.finish = finish
    return git_repo


def _quiet(root, *argv):
    result = subprocess.run([sys.executable, "-m", "taskrail", "--root", str(root), *argv], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def start(root, capsys, count=5, kinds=None):
    argv = ["autopilot", "start", "--count", str(count)] + (["--kinds", kinds] if kinds is not None else [])
    return data(root, *argv, capsys=capsys)["run"]["id"]


def dispatch(root, capsys, run_id=None):
    return data(root, "autopilot", "next", *(["--run", run_id] if run_id else []), capsys=capsys)


def ids(result):
    return [task["id"] for task in result["dispatch"]]


def skipped(result):
    return {entry["id"]: entry["reason"] for entry in result["skipped"]}


def stored(root, run_id):
    return runs.read(load_config(root), run_id)


def backdate(root, run_id, task_id, minutes):
    """Move a task's dispatch into the past, as if its lane never claimed."""
    moment = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    with runs.update(load_config(root), run_id) as record:
        record["tasks"][task_id]["dispatched"] = moment


def row(root, capsys, run_id, task_id):
    report = data(root, "autopilot", "status", "--run", run_id, capsys=capsys)
    return next(r for r in report["runs"][0]["tasks"] if r["id"] == task_id)


# 1


def test_group_and_resource_configuration(repo):
    from taskrail.config import GroupConfig, ResourceConfig

    config = load_config(repo.root).autopilot
    assert (config.groups, config.resources) == ((), ())
    configure(
        repo,
        """
[[autopilot.group]]
name = "ui"
limit = 1
column = "area"
match = ["UI", "ux"]

[[autopilot.group]]
name = "db"
limit = 2

[[autopilot.resource]]
name = "PORT"
values = ["5433", "5434"]
""",
    )
    config = load_config(repo.root).autopilot
    assert config.groups == (
        GroupConfig(name="ui", limit=1, predicate=ColumnPredicate("Area", ("UI", "ux"))),
        GroupConfig(name="db", limit=2, predicate=None),
    )
    assert config.resources == (ResourceConfig(name="PORT", values=("5433", "5434")),)


GROUP = '[[autopilot.group]]\nname = "ui"\nlimit = 1\n'
RESOURCE = '[[autopilot.resource]]\nname = "PORT"\nvalues = ["1"]\n'


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('group = "ui"', "autopilot.group must be an array of tables"),
        ('resource = "PORT"', "autopilot.resource must be an array of tables"),
        ("[[autopilot.group]]\nlimit = 1", "autopilot.group #1: missing `name`"),
        ('[[autopilot.group]]\nname = "ui"', "autopilot.group `ui`: missing `limit`"),
        ('[[autopilot.group]]\nname = "UI"\nlimit = 1', "autopilot.group `UI`: name must be lowercase letters, digits and dashes"),
        (GROUP + GROUP, "autopilot.group: `ui` is used more than once"),
        ('[[autopilot.group]]\nname = "ui"\nlimit = "one"', "autopilot.group `ui`: `limit` must be int"),
        ('[[autopilot.group]]\nname = "ui"\nlimit = 0', "autopilot.group `ui`: `limit` must be at least 1"),
        (GROUP + 'column = "Area"', "autopilot.group `ui`: `column` needs `match`"),
        (GROUP + 'match = ["ui"]', "autopilot.group `ui`: `match` needs `column`"),
        (GROUP + 'column = "Nope"\nmatch = "x"', "autopilot.group `ui`: column `Nope` is not declared in [columns].custom"),
        (GROUP + 'column = "Kind"\nmatch = "bug"', "autopilot.group `ui`: column `Kind` is core column Kind"),
        ("[[autopilot.resource]]\nvalues = [\"1\"]", "autopilot.resource #1: missing `name`"),
        ('[[autopilot.resource]]\nname = "PORT"', "autopilot.resource `PORT`: missing `values`"),
        ('[[autopilot.resource]]\nname = "port"\nvalues = ["1"]', "autopilot.resource `port`: name must be uppercase letters, digits and underscores"),
        (RESOURCE + RESOURCE, "autopilot.resource: `PORT` is used more than once"),
        ('[[autopilot.resource]]\nname = "PORT"\nvalues = []', "autopilot.resource `PORT`: `values` must be a non-empty list of strings"),
        ('[[autopilot.resource]]\nname = "PORT"\nvalues = [5433]', "autopilot.resource `PORT`: `values` must be a non-empty list of strings"),
        ('[[autopilot.resource]]\nname = "PORT"\nvalues = [""]', "autopilot.resource `PORT`: `values` must be a non-empty list of strings"),
        ('[[autopilot.resource]]\nname = "PORT"\nvalues = ["1", "1"]', "autopilot.resource `PORT`: value `1` is listed more than once"),
    ],
)
def test_group_and_resource_errors_name_the_key(repo, capsys, toml, message):
    if toml.startswith(("group", "resource")):
        repo.write(".taskrail/config.toml", CONFIG + "\n[autopilot]\n" + toml + "\n")
    else:
        configure(repo, toml + "\n")
    with pytest.raises(ConfigError, match=re.escape(message)):
        load_config(repo.root)
    code, _, err = run(repo.root, "list", capsys=capsys)
    assert code == 2 and message in err


# 2


def test_next_is_refused_while_disabled_and_checks_the_run_and_backlog(pilot, capsys):
    run_id = start(pilot.root, capsys)
    configure(pilot, enabled=False)
    for argv in ([], ["--run", run_id]):
        code, _, err = run(pilot.root, "autopilot", "next", *argv, capsys=capsys)
        assert code == 5 and "[autopilot].enabled" in err
    assert stored(pilot.root, run_id)["tasks"] == {}

    configure(pilot)
    assert run(pilot.root, "autopilot", "next", "--run", "20000101-1", capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "next", "--run", "../claims/x", capsys=capsys)[0] == 3

    pilot.write("TODO.md", TODO.replace("| T004 | feature |", "| T004 | nope    |"))
    code, _, err = run(pilot.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert code == 1 and "validation error" in err
    assert stored(pilot.root, run_id)["tasks"] == {}


# 3


def test_next_dispatches_within_max_lanes_in_next_order(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    run_id = start(pilot.root, capsys)
    result = dispatch(pilot.root, capsys, run_id)
    assert (result["run"], result["preview"]) == (run_id, False)
    assert ids(result) == ["T001", "T002"]
    assert result["limited_by"] == "max_lanes"
    assert result["lanes"]["max"] == 2 and result["lanes"]["free"] == 0
    assert [(lane["id"], lane["run"], lane["state"]) for lane in result["lanes"]["occupied"]] == [
        ("T001", run_id, "dispatched"),
        ("T002", run_id, "dispatched"),
    ]
    assert result["remaining"] == 3

    first = result["dispatch"][0]
    shown = data(pilot.root, "show", "T001", capsys=capsys)
    for key in ("id", "kind", "state", "branch", "worktree", "base", "artifact", "skill", "kind_descriptor", "prior_work"):
        assert first[key] == shown[key], key
    assert first["base"]["commit"]
    assert (first["decisions"], first["decisions_index"]) == (
        "docs/autopilot/decisions/T001-first-ui.md",
        "docs/autopilot/decisions/README.md",
    )
    assert (first["resources"], first["environment"], first["groups"]) == ({}, {}, [])

    record = stored(pilot.root, run_id)["tasks"]
    assert set(record) == {"T001", "T002"}
    assert all(datetime.fromisoformat(record[t]["dispatched"]) for t in ("T001", "T002"))

    code, out, _ = run(pilot.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert code == 0 and "nothing to dispatch" in out and "max_lanes" in out


def test_next_text_lists_each_dispatched_task(pilot, capsys):
    configure(pilot, 'max_lanes = 1\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433"]\n')
    run_id = start(pilot.root, capsys)
    code, out, _ = run(pilot.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert code == 0
    assert re.search(r"^T001\s+feature\s+T001-first-ui\s+.*PORT=5433", out, re.M)
    assert "1/1 lanes" in out


# 4


def test_a_dispatch_holds_its_lane_until_it_is_claimed_or_expires(pilot, capsys):
    configure(pilot, 'max_lanes = 2\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433", "5434", "5435"]\n')
    run_id = start(pilot.root, capsys)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002"]

    again = dispatch(pilot.root, capsys, run_id)
    assert ids(again) == [] and again["limited_by"] == "max_lanes" and again["released"] == []

    pilot.lane("T001", run_id)
    assert ids(dispatch(pilot.root, capsys, run_id)) == []

    backdate(pilot.root, run_id, "T002", 16)  # claim_grace_minutes is 15
    result = dispatch(pilot.root, capsys, run_id)
    assert result["released"] == [{"id": "T002", "run": run_id, "resources": {"PORT": "5434"}}]
    assert ids(result) == ["T002"]
    assert result["dispatch"][0]["resources"] == {"PORT": "5434"}
    assert stored(pilot.root, run_id)["tasks"]["T001"]["resources"] == {"PORT": "5433"}


# 5


def test_a_gate_occupies_a_lane_while_escalated_and_failed_do_not(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    run_id = start(pilot.root, capsys, count=4)
    pilot.lane("T001", run_id)
    pilot.lane("T003", run_id)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "escalated", "--reason", "governing", capsys=capsys)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T002"]  # the escalated lane waits for a human and holds no lane (T105)
    assert [lane["id"] for lane in result["lanes"]["occupied"]] == ["T001", "T002"]
    assert "T003" not in skipped(result) and "T007" not in skipped(result)  # claimed; blocked

    again = dispatch(pilot.root, capsys, run_id)  # a lane at a gate keeps its place
    assert ids(again) == [] and again["limited_by"] == "max_lanes"

    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "failed", "--reason", "hangs", capsys=capsys)
    configure(pilot, "max_lanes = 4\n")
    assert main(["--root", str(pilot.root), "release", "T003", "--owner", "lane"]) == 0
    result = dispatch(pilot.root, capsys, run_id)
    assert skipped(result)["T003"] == f"failed in run {run_id}"
    assert skipped(result)["T002"] == f"dispatched in run {run_id}"
    assert ids(result) == ["T005"]  # T004 is blocked by T001; count 4 = T001, T002, T003 (failed) and T005; T006 waits
    assert result["limited_by"] == "count"

    pilot.finish("T001")
    assert "T001" not in [lane["id"] for lane in dispatch(pilot.root, capsys, run_id)["lanes"]["occupied"]]


# 6


def test_lanes_and_dispatches_are_counted_across_runs(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    first = start(pilot.root, capsys)
    second = start(pilot.root, capsys)
    pilot.lane("T001", first)
    assert ids(dispatch(pilot.root, capsys, first)) == ["T002"]
    assert ids(dispatch(pilot.root, capsys, second)) == []

    configure(pilot, "max_lanes = 3\n")
    result = dispatch(pilot.root, capsys, second)
    assert skipped(result)["T002"] == f"dispatched in run {first}"
    assert ids(result) == ["T003"]
    assert {(lane["id"], lane["run"]) for lane in result["lanes"]["occupied"]} == {
        ("T001", first),
        ("T002", first),
        ("T003", second),
    }


# 7


def test_the_run_count_limits_dispatch(pilot, capsys):
    run_id = start(pilot.root, capsys, count=1)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001"] and result["limited_by"] == "count" and result["remaining"] == 0

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "failed", "--reason", "stuck", capsys=capsys)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == [] and result["limited_by"] == "count"

    assert main(["--root", str(pilot.root), "discard", "T001"]) == 0
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T002"] and result["remaining"] == 0


# 8


def test_kinds_come_from_the_run_and_the_configuration(pilot, capsys):
    runs_dir = pilot.root / ".git" / "taskrail" / "runs"

    def fresh(autopilot, kinds):
        shutil.rmtree(runs_dir, ignore_errors=True)
        configure(pilot, "max_lanes = 10\n" + autopilot)
        return dispatch(pilot.root, capsys, start(pilot.root, capsys, count=10, kinds=kinds))

    result = fresh("", "bug")
    assert ids(result) == ["T002", "T005"]
    assert result["skipped"] == [] and result["limited_by"] is None

    assert ids(fresh('kinds = ["chore"]\n', None)) == ["T003", "T006"]
    assert ids(fresh("", None)) == ["T001", "T002", "T003", "T005", "T006"]
    assert ids(fresh('kinds = ["chore", "feature"]\n', "bug,chore")) == ["T003", "T006"]
    assert ids(fresh('kinds = ["feature"]\n', "bug")) == []


# 9


def test_a_column_group_limits_its_lanes(pilot, capsys):
    group = '[[autopilot.group]]\nname = "ui"\nlimit = 1\ncolumn = "Area"\nmatch = "ui"\n'
    configure(pilot, "max_lanes = 2\n" + group)
    run_id = start(pilot.root, capsys, count=10)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001", "T003"]
    assert skipped(result) == {"T002": "group ui is full"}
    assert result["dispatch"][0]["groups"] == ["ui"] and result["dispatch"][1]["groups"] == []
    assert result["groups"] == [{"name": "ui", "limit": 1, "column": "Area", "match": ["ui"], "members": ["T001"], "free": 0}]

    configure(pilot, "max_lanes = 3\n" + group)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T005"]
    assert skipped(result) == {"T001": f"dispatched in run {run_id}", "T002": "group ui is full", "T003": f"dispatched in run {run_id}"}

    configure(pilot, "max_lanes = 4\n" + group)
    pilot.lane("T001", run_id)
    pilot.finish("T001")
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T002", "T004"]  # the ui lane ended; T004 is stacked on T001
    assert "T002" not in skipped(result)


# 10


def test_a_judgement_group_follows_lane_group_records(pilot, capsys):
    groups = '[[autopilot.group]]\nname = "db"\nlimit = 1\n[[autopilot.group]]\nname = "ui"\nlimit = 1\ncolumn = "Area"\nmatch = "ui"\n'
    configure(pilot, "max_lanes = 4\n" + groups)
    run_id = start(pilot.root, capsys, count=10)
    for task_id in ("T003", "T006"):
        data(pilot.root, "autopilot", "lane", task_id, "--run", run_id, "--group", "db", capsys=capsys)
    before = stored(pilot.root, run_id)

    code, _, err = run(pilot.root, "autopilot", "lane", "T005", "--run", run_id, "--group", "nope", capsys=capsys)
    assert code == 2 and "no judgement group `nope`" in err and "db" in err
    code, _, err = run(pilot.root, "autopilot", "lane", "T005", "--run", run_id, "--group", "ui", capsys=capsys)
    assert code == 2 and "column Area" in err
    assert stored(pilot.root, run_id) == before

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001", "T003", "T005"]
    assert skipped(result) == {"T002": "group ui is full", "T006": "group db is full"}
    assert [task["groups"] for task in result["dispatch"]] == [["ui"], ["db"], []]


# 11


def test_resources_are_allocated_per_lane_and_released_when_it_ends(pilot, capsys):
    configure(
        pilot,
        'max_lanes = 3\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433", "5434"]\n'
        '[[autopilot.resource]]\nname = "DB"\nvalues = ["a", "b", "c"]\n',
    )
    run_id = start(pilot.root, capsys, count=10)
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001", "T002"] and result["limited_by"] == "resource:PORT"
    assert [task["resources"] for task in result["dispatch"]] == [{"PORT": "5433", "DB": "a"}, {"PORT": "5434", "DB": "b"}]
    assert result["dispatch"][0]["environment"] == {"TASKRAIL_RESOURCE_PORT": "5433", "TASKRAIL_RESOURCE_DB": "a"}
    assert result["resources"] == [
        {"name": "PORT", "values": ["5433", "5434"], "held": {"5433": "T001", "5434": "T002"}, "free": []},
        {"name": "DB", "values": ["a", "b", "c"], "held": {"a": "T001", "b": "T002"}, "free": ["c"]},
    ]
    record = stored(pilot.root, run_id)["tasks"]
    assert record["T001"]["resources"] == {"PORT": "5433", "DB": "a"} and "T003" not in record

    pilot.lane("T001", run_id)
    pilot.finish("T001")
    result = dispatch(pilot.root, capsys, run_id)
    assert result["released"] == [{"id": "T001", "run": run_id, "resources": {"PORT": "5433", "DB": "a"}}]
    assert stored(pilot.root, run_id)["tasks"]["T001"]["resources"] == {}
    assert ids(result) == ["T003"] and result["dispatch"][0]["resources"] == {"PORT": "5433", "DB": "a"}

    data(pilot.root, "autopilot", "lane", "T002", "--run", run_id, "--state", "failed", "--reason", "broken", capsys=capsys)
    result = dispatch(pilot.root, capsys, run_id)
    assert result["released"] == [{"id": "T002", "run": run_id, "resources": {"PORT": "5434", "DB": "b"}}]
    assert ids(result) == ["T004"] and result["dispatch"][0]["resources"] == {"PORT": "5434", "DB": "b"}


# 12


def test_concurrent_dispatches_share_the_limits(pilot, capsys):
    configure(pilot, 'max_lanes = 3\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["1", "2", "3", "4"]\n')
    first = start(pilot.root, capsys, count=10)
    second = start(pilot.root, capsys, count=10)
    env = {**os.environ}
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "taskrail", "--root", str(pilot.root), "autopilot", "next", "--run", run_id, "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        for run_id in (first, second)
    ]
    results = []
    for process in processes:
        out, err = process.communicate(timeout=60)
        assert process.returncode == 0, err
        results.append(json.loads(out))
    dispatched = [task for result in results for task in result["dispatch"]]
    assert len(dispatched) == 3
    assert len({task["id"] for task in dispatched}) == 3
    assert len({task["resources"]["PORT"] for task in dispatched}) == 3


# 13


def test_stacked_bases_diverged_bases_and_blocked_tasks(pilot, capsys):
    configure(pilot, "max_lanes = 10\n")
    run_id = start(pilot.root, capsys, count=10)
    pilot.lane("T001", run_id)
    pilot.finish("T001")
    result = dispatch(pilot.root, capsys, run_id)
    stacked = next(task for task in result["dispatch"] if task["id"] == "T004")
    assert stacked["base"]["dependency"] == "T001" and stacked["base"]["onto"] == "T001-first-ui"
    assert "T007" not in ids(result) and "T007" not in skipped(result)

    shutil.rmtree(pilot.root / ".git" / "taskrail" / "runs")
    run_id = start(pilot.root, capsys, count=10)
    clone = pilot.root.parent / "diverging-clone"
    git(pilot.root, "clone", "-q", str(pilot.bare), str(clone))
    (clone / "remote.txt").write_text("remote\n")
    commit_all(clone, "remote change")
    git(clone, "push", "-q", "origin", "main")
    (pilot.root / "local.txt").write_text("local\n")
    commit_all(pilot.root, "local change")
    git(pilot.root, "fetch", "-q", "origin")
    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T004"]  # stacked on T001's branch, which has not diverged
    assert skipped(result)["T002"].startswith("base diverged")


# 14


def test_next_without_a_run_is_a_preview(pilot, capsys):
    configure(pilot, 'max_lanes = 2\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433", "5434"]\n')
    preview = dispatch(pilot.root, capsys)
    assert (preview["run"], preview["preview"], preview["remaining"]) == (None, True, None)
    assert ids(preview) == ["T001", "T002"]
    assert [task["resources"] for task in preview["dispatch"]] == [{"PORT": "5433"}, {"PORT": "5434"}]
    assert not (pilot.root / ".git" / "taskrail" / "runs").exists()

    run_id = start(pilot.root, capsys)
    path = pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json"
    before = (path.read_text(), path.stat().st_mtime_ns)
    assert ids(dispatch(pilot.root, capsys)) == ["T001", "T002"]
    assert (path.read_text(), path.stat().st_mtime_ns) == before
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002"]


# 15


def test_status_reports_a_dispatched_task(pilot, capsys):
    configure(pilot, 'max_lanes = 1\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433"]\n')
    run_id = start(pilot.root, capsys)
    dispatch(pilot.root, capsys, run_id)
    lane = row(pilot.root, capsys, run_id, "T001")
    assert (lane["state"], lane["resources"]) == ("dispatched", {"PORT": "5433"})

    backdate(pilot.root, run_id, "T001", 16)
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "pending"

    backdate(pilot.root, run_id, "T001", 0)
    pilot.lane("T001", run_id)
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "running"


# T054


def test_a_lane_between_done_and_its_commit_is_running_and_not_dispatched_again(pilot, capsys):
    configure(pilot, "max_lanes = 1\n")
    run_id = start(pilot.root, capsys)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001"]
    path = pilot.lane("T001", run_id)
    backdate(pilot.root, run_id, "T001", 16)  # claim_grace_minutes is 15
    assert main(["--root", str(path), "done", "T001", "--owner", "lane"]) == 0  # releases the claim; not committed yet

    lane = row(pilot.root, capsys, run_id, "T001")
    assert (lane["state"], lane["claim"], lane["touched"]) == ("running", None, ["TODO.md"])
    configure(pilot, "max_lanes = 2\n")
    result = dispatch(pilot.root, capsys, run_id)
    assert skipped(result)["T001"] == f"running in run {run_id}"
    assert ids(result) == ["T002"]  # T001 still holds one of the two lanes
    assert "T001" in [occupied["id"] for occupied in result["lanes"]["occupied"]]

    commit_all(path, "chore(T001): mark done")
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "done-branch"


def test_a_lane_at_a_gate_without_a_claim_is_not_dispatched_again(pilot, capsys):
    run_id = start(pilot.root, capsys, count=3)
    pilot.lane("T001", run_id)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", capsys=capsys)
    assert main(["--root", str(pilot.root), "release", "T001", "--owner", "lane"]) == 0

    result = dispatch(pilot.root, capsys, run_id)
    assert skipped(result)["T001"] == f"gate in run {run_id}"
    assert ids(result) == ["T002", "T003"]


def test_a_task_discarded_on_its_unmerged_branch_is_closed_and_not_dispatched_again(pilot, capsys):
    run_id = start(pilot.root, capsys, count=2)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002"]
    path = pilot.lane("T001", run_id)
    assert main(["--root", str(path), "discard", "T001", "--owner", "lane"]) == 0
    commit_all(path, "chore(T001): discard")
    backdate(pilot.root, run_id, "T001", 16)  # claim_grace_minutes is 15
    branch = data(pilot.root, "show", "T001", capsys=capsys)["branch"]

    lane = row(pilot.root, capsys, run_id, "T001")
    assert (lane["state"], lane["claim"], lane["branch"], lane["touched"]) == ("discarded-branch", None, branch, ["TODO.md"])
    report = data(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)
    assert report["runs"][0]["handoff"]["queue"] == ["T001"]  # its branch waits for hand-off (T065)
    assert "T001" not in [task["id"] for task in data(pilot.root, "next", capsys=capsys)]
    result = dispatch(pilot.root, capsys, run_id)
    assert "T001" not in skipped(result)
    assert ids(result) == ["T003"]  # T001 is no candidate, and its place in the run's count is free again
    assert result["remaining"] == 0

    git(pilot.root, "push", "-q", "origin", f"{branch}:main")  # merged, and the local mainline is not pulled
    git(pilot.root, "fetch", "-q", "origin")
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "discarded"


def test_a_lane_between_discard_and_its_commit_is_running(pilot, capsys):
    run_id = start(pilot.root, capsys)
    assert "T001" in ids(dispatch(pilot.root, capsys, run_id))
    path = pilot.lane("T001", run_id)
    backdate(pilot.root, run_id, "T001", 16)
    assert main(["--root", str(path), "discard", "T001", "--owner", "lane"]) == 0  # releases the claim; not committed yet

    lane = row(pilot.root, capsys, run_id, "T001")
    assert (lane["state"], lane["claim"], lane["touched"]) == ("running", None, ["TODO.md"])
    commit_all(path, "chore(T001): discard")
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "discarded-branch"


# T064


def merge_without_pull(pilot, capsys, task_id, closing):
    """Close a task in its lane, push its branch to origin/main and fetch, leaving the local main behind."""
    path = pilot.worktrees[task_id]
    assert main(["--root", str(path), closing, task_id, "--owner", "lane"]) == 0
    commit_all(path, f"chore({task_id}): {closing}")
    branch = data(pilot.root, "show", task_id, capsys=capsys)["branch"]
    git(pilot.root, "push", "-q", "origin", f"{branch}:main")
    git(pilot.root, "fetch", "-q", "origin")
    return path, branch


@pytest.mark.parametrize("closing, state", [("done", "done-merged"), ("discard", "discarded")])
def test_a_task_closed_on_the_remote_mainline_but_not_pulled_is_not_dispatched(pilot, capsys, closing, state):
    run_id = start(pilot.root, capsys, count=6)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002", "T003", "T005", "T006"]
    pilot.lane("T001", run_id)
    path, branch = merge_without_pull(pilot, capsys, "T001", closing)
    backdate(pilot.root, run_id, "T001", 16)  # claim_grace_minutes is 15
    dispatched = stored(pilot.root, run_id)["tasks"]["T001"]["dispatched"]
    reason = f"{state} on the mainline, not in this checkout"

    assert row(pilot.root, capsys, run_id, "T001")["state"] == state
    assert data(pilot.root, "show", "T001", capsys=capsys)["state"] == "pending"  # plain commands read the checkout (§7)
    preview = dispatch(pilot.root, capsys)
    assert (ids(preview), skipped(preview).get("T001")) == ([], reason)
    result = dispatch(pilot.root, capsys, run_id)
    assert (ids(result), skipped(result).get("T001")) == ([], reason)
    assert stored(pilot.root, run_id)["tasks"]["T001"]["dispatched"] == dispatched  # not recorded again

    git(pilot.root, "worktree", "remove", "--force", str(path))  # as `autopilot merged --cleanup` does
    git(pilot.root, "branch", "-D", branch)
    assert skipped(dispatch(pilot.root, capsys))["T001"] == reason

    git(pilot.root, "merge", "-q", "--ff-only", "origin/main")  # pulled: no longer a candidate at all
    preview = dispatch(pilot.root, capsys)
    assert "T001" not in ids(preview) and "T001" not in skipped(preview)


def test_a_task_reopened_on_the_local_mainline_is_offered_while_the_remote_is_still_closed(pilot, capsys):
    run_id = start(pilot.root, capsys, count=6)
    dispatch(pilot.root, capsys, run_id)
    pilot.lane("T001", run_id)
    path, branch = merge_without_pull(pilot, capsys, "T001", "done")
    git(pilot.root, "worktree", "remove", "--force", str(path))
    git(pilot.root, "branch", "-D", branch)
    git(pilot.root, "merge", "-q", "--ff-only", "origin/main")
    backdate(pilot.root, run_id, "T001", 16)

    reopened = data(pilot.root, "reopen", "T001", "--reason", "not finished", capsys=capsys)
    git(pilot.root, "commit", "-q", "-am", reopened["commit_message"])  # not pushed: origin/main still has ✅
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "pending"
    preview = dispatch(pilot.root, capsys)
    assert "T001" in ids(preview) and "T001" not in skipped(preview)

    git(pilot.root, "push", "-q", "origin", "main")  # the reopen reaches origin/main, and the local main falls behind
    git(pilot.root, "reset", "-q", "--hard", "HEAD~1")
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "pending"
