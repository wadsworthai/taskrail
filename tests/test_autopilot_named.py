"""Named autopilot runs, rows that only their task's branch holds, and `autopilot extend` (T071)."""

import json
import shutil

import pytest
from conftest import git
from test_autopilot_next import CONFIG, commit_all, data, dispatch, ids, run, skipped, start, stored  # noqa: F401
from test_autopilot_next import pilot  # noqa: F401  (the fixture)

from taskrail import branches
from taskrail.autopilot import runs
from taskrail.cli import main
from taskrail.config import load_config

QUIET_CHECKS = CONFIG.replace('test = "pytest"', 'test = "true"').replace('lint = "ruff check"', 'lint = "true"')


def configure(repo, autopilot="max_lanes = 10\n", enabled=True):
    repo.write(".taskrail/config.toml", QUIET_CHECKS + f"\n[autopilot]\nenabled = {'true' if enabled else 'false'}\n" + autopilot)


@pytest.fixture
def named(pilot):  # noqa: F811
    """The `pilot` repository with checks that pass quietly and task worktrees ignored, pushed to origin."""
    configure(pilot)
    pilot.write(".gitignore", ".worktrees/\n")
    commit_all(pilot.root, "quiet checks")
    git(pilot.root, "push", "-q", "origin", "main")
    return pilot


def code_of(root, *argv, capsys):
    code, _, err = run(root, *argv, capsys=capsys)
    return code, err


def prepare(repo, capsys, title="Prepared one", commit=True):
    """A task created with `new --workspace`: its row only on its own branch. Returns (ID, worktree)."""
    result = data(repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", title, "--workspace", capsys=capsys)
    worktree = repo.root / ".worktrees" / result["branch"]
    if commit:
        commit_all(worktree, f"chore(backlog): add {result['id']}")
    return result["id"], worktree


def start_named(root, capsys, tasks):
    return data(root, "autopilot", "start", "--tasks", tasks, capsys=capsys)["run"]["id"]


def claim(worktree, task_id, run_id=None):
    argv = ["--root", str(worktree), "claim", task_id, "--owner", "lane"] + (["--run", run_id] if run_id else [])
    assert main(argv) == 0


def close_on_branch(worktree, task_id, command="done"):
    assert main(["--root", str(worktree), command, task_id, "--owner", "lane"]) == 0
    commit_all(worktree, f"chore({task_id}): mark {command}")


def status_row(root, capsys, run_id, task_id):
    report = data(root, "autopilot", "status", "--run", run_id, capsys=capsys)
    return report["runs"][0], next(row for row in report["runs"][0]["tasks"] if row["id"] == task_id)


def run_files(root):
    directory = runs.runs_dir(load_config(root))
    return sorted(path.name for path in directory.glob("*.json")) if directory.is_dir() else []


# Criterion 1


def test_start_names_tasks_in_the_order_given_once(named, capsys):
    result = data(named.root, "autopilot", "start", "--tasks", "T005,T002,T005", capsys=capsys)["run"]
    assert (result["named"], result["count"], result["kinds"]) == (["T005", "T002"], 2, [])
    assert stored(named.root, result["id"])["named"] == ["T005", "T002"]
    again = data(named.root, "autopilot", "start", "--tasks", "T005,T002", "--count", "2", capsys=capsys)["run"]
    assert (again["named"], again["count"]) == (["T005", "T002"], 2)


def test_a_count_only_run_names_nothing(named, capsys):
    run_id = start(named.root, capsys, count=2)
    assert stored(named.root, run_id)["named"] == []


# Criterion 2


@pytest.mark.parametrize(
    ("argv", "code", "message"),
    [
        ([], 2, "--tasks"),
        (["--tasks", " , "], 2, "at least one task ID"),
        (["--tasks", "T001,T002", "--count", "3"], 2, "does not match"),
        (["--tasks", "T001", "--kinds", "feature"], 2, "--kinds does not apply"),
        (["--tasks", "T001,T099"], 3, "no task `T099`"),
    ],
)
def test_start_refuses_bad_task_lists_and_writes_nothing(named, capsys, argv, code, message):
    got, err = code_of(named.root, "autopilot", "start", *argv, capsys=capsys)
    assert got == code and message in err
    assert run_files(named.root) == []


def test_start_refuses_while_disabled_before_anything_else(named, capsys):
    configure(named, enabled=False)
    got, err = code_of(named.root, "autopilot", "start", "--tasks", "T099", "--kinds", "x", capsys=capsys)
    assert got == 5 and "[autopilot].enabled" in err


def test_start_refuses_a_closed_task_or_a_kind_not_driven(named, capsys):
    named.lane("T001")
    named.finish("T001")  # done-branch
    got, err = code_of(named.root, "autopilot", "start", "--tasks", "T002,T001", capsys=capsys)
    assert got == 5 and "T001 is done-branch" in err

    named.lane("T003")
    close_on_branch(named.worktrees["T003"], "T003", "discard")
    got, err = code_of(named.root, "autopilot", "start", "--tasks", "T003", capsys=capsys)
    assert got == 5 and "T003 is discarded-branch" in err

    assert main(["--root", str(named.root), "done", "T006", "--force"]) == 0
    commit_all(named.root, "done T006")
    got, err = code_of(named.root, "autopilot", "start", "--tasks", "T006", capsys=capsys)
    assert got == 5 and "T006 is done" in err

    configure(named, 'kinds = ["bug"]\n')
    got, err = code_of(named.root, "autopilot", "start", "--tasks", "T002,T005,T004", capsys=capsys)
    assert got == 5 and "T004's kind `feature` is not in [autopilot].kinds" in err
    assert run_files(named.root) == []


# Criterion 3


def test_a_named_run_dispatches_only_its_tasks_in_the_order_given(named, capsys):
    run_id = start_named(named.root, capsys, "T005,T002")
    result = dispatch(named.root, capsys, run_id)
    assert ids(result) == ["T005", "T002"]  # T001 is cheaper and eligible, but not named
    assert result["skipped"] == [] and result["remaining"] == 0


def test_a_named_run_takes_the_next_named_task_when_a_lane_frees(named, capsys):
    configure(named, "max_lanes = 1\n")
    run_id = start_named(named.root, capsys, "T005,T002")
    result = dispatch(named.root, capsys, run_id)
    assert ids(result) == ["T005"] and result["limited_by"] == "max_lanes"
    named.lane("T005", run_id)
    assert ids(dispatch(named.root, capsys, run_id)) == []
    named.finish("T005")
    assert ids(dispatch(named.root, capsys, run_id)) == ["T002"]


# Criterion 4


def test_a_named_task_that_cannot_start_says_why(named, capsys):
    run_id = start_named(named.root, capsys, "T004,T003,T001,T005")
    named.lane("T003")  # claimed outside the run
    configure(named, 'max_lanes = 10\nkinds = ["bug", "chore"]\n')
    result = dispatch(named.root, capsys, run_id)
    assert ids(result) == ["T005"]
    assert skipped(result) == {
        "T004": "blocked by T001",
        "T003": "claimed by lane",
        "T001": f"kind feature is not driven by run {run_id}",
    }


# Criterion 5


def test_new_workspace_records_its_branch(named, capsys):
    task_id, worktree = prepare(named, capsys)
    record = branches.read(load_config(named.root), task_id)
    assert record is not None and record.branch == worktree.name
    assert data(worktree, "show", task_id, capsys=capsys)["branch_source"] == "recorded"


# Criterion 6


def test_a_row_only_on_its_branch_is_found_from_the_main_checkout(named, capsys):
    task_id, worktree = prepare(named, capsys)
    assert run(named.root, "show", task_id, capsys=capsys)[0] == 3  # the checkout lacks the row
    run_id = start_named(named.root, capsys, task_id)

    result = dispatch(named.root, capsys, run_id)
    assert ids(result) == [task_id]
    entry = result["dispatch"][0]
    assert entry["branch"] == worktree.name
    assert entry["worktree"] == f".worktrees/{worktree.name}"  # relative under the root, as for any task (see T072)
    assert entry["prior_work"]["prepared"]["row"] == "committed"

    assert code_of(named.root, "autopilot", "lane", task_id, "--run", run_id, "--state", "running", capsys=capsys)[0] == 0
    assert code_of(named.root, "autopilot", "notify", "--event", "lane-done", "--run", run_id, "--task", task_id, capsys=capsys)[0] == 0
    got, err = code_of(named.root, "autopilot", "approve-governing", task_id, "--run", run_id, capsys=capsys)
    assert got == 5 and "touches no governing path" in err

    claim(worktree, task_id, run_id)
    assert status_row(named.root, capsys, run_id, task_id)[1]["state"] == "running"
    checks = data(named.root, "checks", task_id, capsys=capsys)
    assert checks["passed"] and checks["worktree"] == str(worktree.resolve())

    close_on_branch(worktree, task_id)
    report, row = status_row(named.root, capsys, run_id, task_id)
    assert row["state"] == "done-branch" and report["handoff"]["queue"] == [task_id]
    merged = data(named.root, "autopilot", "merged", task_id, "--no-fetch", capsys=capsys)
    assert merged["merged"] is False


# Criterion 7


def test_a_branch_only_task_discarded_on_its_branch_reads_discarded_branch(named, capsys):
    task_id, worktree = prepare(named, capsys)
    run_id = start_named(named.root, capsys, task_id)
    claim(worktree, task_id, run_id)
    close_on_branch(worktree, task_id, "discard")
    assert status_row(named.root, capsys, run_id, task_id)[1]["state"] == "discarded-branch"


def test_a_row_not_committed_yet_is_found_in_its_worktree(named, capsys):
    task_id, _ = prepare(named, capsys, commit=False)
    run_id = start_named(named.root, capsys, task_id)
    result = dispatch(named.root, capsys, run_id)
    assert ids(result) == [task_id]
    prepared = result["dispatch"][0]["prior_work"]["prepared"]
    assert (prepared["row"], prepared["commits"]) == ("uncommitted", 0)


# Criterion 8


def occupancy(root, capsys, *argv):
    result = dispatch(root, capsys, *argv)
    return {lane["id"]: lane["state"] for lane in result["lanes"]["occupied"]}, result["lanes"]["free"]


def test_a_lane_counts_from_a_checkout_that_lacks_its_row(named, capsys):
    task_id, worktree = prepare(named, capsys)
    run_id = start(named.root, capsys, count=1)
    claim(worktree, task_id, run_id)
    from_main = occupancy(named.root, capsys)
    assert from_main[0].get(task_id) == "running"
    assert from_main[1] == occupancy(worktree, capsys)[1]
    assert occupancy(named.root, capsys, run_id)[0].get(task_id) == "running"


def test_a_claimed_lane_whose_row_is_gone_still_counts(named, capsys):
    task_id, worktree = prepare(named, capsys)
    run_id = start(named.root, capsys, count=1)
    claim(worktree, task_id, run_id)
    git(named.root, "worktree", "remove", "--force", str(worktree))
    git(named.root, "branch", "-D", worktree.name)
    shutil.rmtree(worktree, ignore_errors=True)
    assert occupancy(named.root, capsys)[0].get(task_id) == "running"


# Criterion 9 is the unchanged count-only suite in test_autopilot_next.py.


# Criteria 13–16: autopilot extend


def test_extend_appends_named_tasks_and_raises_the_count(named, capsys):
    run_id = start_named(named.root, capsys, "T005,T002")
    result = data(named.root, "autopilot", "extend", run_id, "--tasks", "T006,T005", capsys=capsys)
    assert result["added"] == ["T006"] and result["previous_count"] == 2
    assert (result["run"]["named"], result["run"]["count"]) == (["T005", "T002", "T006"], 3)
    assert ids(dispatch(named.root, capsys, run_id)) == ["T005", "T002", "T006"]
    report, row = status_row(named.root, capsys, run_id, "T006")
    assert report["count"] == 3 and report["named"] == ["T005", "T002", "T006"] and row["state"] == "dispatched"

    again = data(named.root, "autopilot", "extend", run_id, "--tasks", "T005", capsys=capsys)
    assert again["added"] == [] and again["run"]["count"] == 3


def test_extend_refuses_tasks_like_start_and_finds_branch_only_rows(named, capsys):
    run_id = start_named(named.root, capsys, "T005")
    before = stored(named.root, run_id)
    assert code_of(named.root, "autopilot", "extend", run_id, "--tasks", "T099", capsys=capsys)[0] == 3
    named.lane("T001")
    named.finish("T001")
    assert code_of(named.root, "autopilot", "extend", run_id, "--tasks", "T002,T001", capsys=capsys)[0] == 5
    configure(named, 'max_lanes = 10\nkinds = ["bug"]\n')
    assert code_of(named.root, "autopilot", "extend", run_id, "--tasks", "T004", capsys=capsys)[0] == 5
    assert stored(named.root, run_id) == before

    configure(named)
    task_id, _ = prepare(named, capsys)
    assert data(named.root, "autopilot", "extend", run_id, "--tasks", task_id, capsys=capsys)["added"] == [task_id]


def test_extend_sets_the_count_of_a_count_only_run(named, capsys):
    run_id = start(named.root, capsys, count=1)
    assert ids(dispatch(named.root, capsys, run_id)) == ["T001"]
    named.lane("T001", run_id)
    result = data(named.root, "autopilot", "extend", run_id, "--count", "4", capsys=capsys)
    assert (result["run"]["count"], result["previous_count"], result["added"]) == (4, 1, [])
    assert len(ids(dispatch(named.root, capsys, run_id))) == 3
    assert code_of(named.root, "autopilot", "extend", run_id, "--count", "0", capsys=capsys)[0] == 2


def test_extend_refuses_a_count_below_the_tasks_already_counted(named, capsys):
    run_id = start(named.root, capsys, count=2)
    assert len(ids(dispatch(named.root, capsys, run_id))) == 2
    got, err = code_of(named.root, "autopilot", "extend", run_id, "--count", "1", capsys=capsys)
    assert got == 5 and "already counted" in err
    assert data(named.root, "autopilot", "extend", run_id, "--count", "2", capsys=capsys)["run"]["count"] == 2


def test_extend_refuses_the_wrong_flag_an_unknown_or_closed_run_and_a_disabled_autopilot(named, capsys):
    named_run = start_named(named.root, capsys, "T005")
    count_run = start(named.root, capsys, count=1)
    for argv in ([named_run, "--count", "3"], [count_run, "--tasks", "T002"], [count_run]):
        assert code_of(named.root, "autopilot", "extend", *argv, capsys=capsys)[0] == 2, argv
    assert code_of(named.root, "autopilot", "extend", "20000101-1", "--count", "2", capsys=capsys)[0] == 3
    assert main(["--root", str(named.root), "autopilot", "close", count_run, "--reason", "abandoned"]) == 0
    assert code_of(named.root, "autopilot", "extend", count_run, "--count", "2", capsys=capsys)[0] == 5
    configure(named, enabled=False)
    got, err = code_of(named.root, "autopilot", "extend", named_run, "--tasks", "T002", capsys=capsys)
    assert got == 5 and "[autopilot].enabled" in err
    assert json.loads(json.dumps(stored(named.root, named_run)))["named"] == ["T005"]
