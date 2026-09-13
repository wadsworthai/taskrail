"""The autopilot configuration, runs, and the start, lane, decision and status commands (T029)."""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import pytest
from conftest import BASE_CONFIG, git

from taskrail import claims
from taskrail.autopilot import runs
from taskrail.autopilot.status import status as compute_status
from taskrail.cli import main
from taskrail.config import AutopilotConfig, load_config
from taskrail.issues import ConfigError
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
| ⬜ | T004 | chore   | 1   | —          | Another one     | —           |
| ❌ | T005 | chore   | 1   | —          | Dropped         | —           |
"""

ENABLED = '\n[autopilot]\nenabled = true\n'
BRANCHES = {
    "T001": "T001-base-task",
    "T002": "T002-depends-on-base",
    "T003": "T003-independent",
    "T004": "T004-another-one",
}


def run(root, *argv, capsys):
    capsys.readouterr()  # drop what setup steps printed
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def commit_all(root, message, date=None):
    git(root, "add", "-A")
    env = {"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else {}
    import subprocess

    result = subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, capture_output=True, text=True, env={**os.environ, **env})
    assert result.returncode == 0, result.stderr


def configure(repo, extra=ENABLED):
    repo.write(".taskrail/config.toml", BASE_CONFIG + extra)


@pytest.fixture
def pilot(git_repo, tmp_path_factory):
    """A repository with the autopilot enabled, a bare origin, and a helper to open lanes."""
    configure(git_repo)
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare

    def lane(task_id, run_id=None, base="origin/main"):
        path = tmp_path_factory.mktemp("lanes") / BRANCHES[task_id]
        git(git_repo.root, "worktree", "add", "-q", str(path), "-b", BRANCHES[task_id], base)
        argv = ["--root", str(path), "claim", task_id, "--owner", "lane"]
        if run_id:
            argv += ["--run", run_id]
        assert main(argv) == 0
        return path

    def finish(path, task_id):
        assert main(["--root", str(path), "done", task_id, "--owner", "lane"]) == 0
        commit_all(path, f"chore({task_id}): mark done")

    git_repo.lane = lane
    git_repo.finish = finish
    return git_repo


def start(root, capsys, *argv):
    return data(root, "autopilot", "start", "--count", "2", *argv, capsys=capsys)["run"]["id"]


def status_of(root, capsys, run_id=None):
    argv = ["autopilot", "status"] + (["--run", run_id] if run_id else [])
    return data(root, *argv, capsys=capsys)


def row(report, task_id, run_index=0):
    return next(r for r in report["runs"][run_index]["tasks"] if r["id"] == task_id)


def mark_merged(pilot, task_id):
    """Put the task's ✅ on main, as a squash merge would."""
    todo = (pilot.root / "TODO.md").read_text(encoding="utf-8")
    (pilot.root / "TODO.md").write_text(todo.replace(f"| ⬜ | {task_id} |", f"| ✅ | {task_id} |"), encoding="utf-8")
    commit_all(pilot.root, f"feat: {task_id} ({task_id})")


# 1


def test_autopilot_configuration_defaults(repo):
    assert load_config(repo.root).autopilot == AutopilotConfig()
    defaults = AutopilotConfig()
    assert (defaults.enabled, defaults.max_lanes, defaults.silent_minutes, defaults.handoff) == (False, 3, 20, "sequential")
    assert defaults.decisions == "{artifacts}/autopilot/decisions/{id}-{slug}.md"
    assert defaults.decisions_index == "{artifacts}/autopilot/decisions/README.md"
    assert (defaults.kinds, defaults.governing, defaults.escalate_gates, defaults.notify) == ((), (), (), "")
    assert defaults.notify_on == ("escalation", "lane-done")


def test_autopilot_configuration_reads_every_single_value_key(repo):
    configure(
        repo,
        """
[autopilot]
enabled = true
max_lanes = 2
kinds = ["bug", "chore"]
governing = ["docs/constitution.md"]
escalate_gates = ["spike:decide"]
decisions = "{artifacts}/records/{id}.md"
decisions_index = "{artifacts}/records/README.md"
silent_minutes = 5
handoff = "sequential"
notify = "notify-send taskrail"
notify_on = ["lane-failed"]
""",
    )
    loaded = load_config(repo.root).autopilot
    assert loaded == AutopilotConfig(
        enabled=True, max_lanes=2, kinds=("bug", "chore"), governing=("docs/constitution.md",), escalate_gates=("spike:decide",),
        decisions="{artifacts}/records/{id}.md", decisions_index="{artifacts}/records/README.md", silent_minutes=5,
        handoff="sequential", notify="notify-send taskrail", notify_on=("lane-failed",),
    )


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('autopilot = "on"', "[autopilot] must be a table"),
        ('[autopilot]\nenabled = "yes"', "autopilot.enabled must be bool"),
        ("[autopilot]\nmax_lanes = 0", "autopilot.max_lanes must be at least 1"),
        ("[autopilot]\nmax_lanes = true", "autopilot.max_lanes must be int"),
        ("[autopilot]\nsilent_minutes = -1", "autopilot.silent_minutes must not be negative"),
        ('[autopilot]\nhandoff = "batch"', "autopilot.handoff must be one of sequential"),
        ('[autopilot]\nkinds = ["Bug"]', "autopilot.kinds: `Bug` is not a kind name"),
        ('[autopilot]\nkinds = "bug"', "autopilot.kinds must be a list of non-empty strings"),
        ('[autopilot]\nescalate_gates = ["decide"]', "autopilot.escalate_gates: `decide` must be shaped kind:stage"),
        ('[autopilot]\nnotify_on = ["always"]', "autopilot.notify_on: `always` is not one of escalation, lane-done, lane-failed"),
        ('[autopilot]\ndecisions = "{nope}.md"', "autopilot.decisions: invalid template"),
        ("[autopilot]\nnotify = 1", "autopilot.notify must be str"),
    ],
)
def test_autopilot_configuration_errors_name_the_key(repo, capsys, toml, message):
    if toml.startswith("autopilot"):
        repo.write(".taskrail/config.toml", toml + "\n" + BASE_CONFIG)  # a top-level key, not one of [checks]
    else:
        configure(repo, "\n" + toml + "\n")
    with pytest.raises(ConfigError, match=re.escape(message)):
        load_config(repo.root)
    code, _, err = run(repo.root, "list", capsys=capsys)
    assert code == 2 and message in err


# 2, 3


def test_start_is_refused_until_the_autopilot_is_enabled(git_repo, capsys):
    common = git_repo.root / ".git" / "taskrail" / "runs"
    for extra in ("", "\n[autopilot]\nenabled = false\n"):
        configure(git_repo, extra)
        for argv in (["--count", "2"], []):
            code, out, err = run(git_repo.root, "autopilot", "start", *argv, capsys=capsys)
            assert code == 5
            assert "[autopilot].enabled" in err
    assert not common.exists()


def test_start_needs_a_positive_count(git_repo, capsys):
    configure(git_repo)
    for argv in ([], ["--count", "0"], ["--count", "-1"]):
        code, _, err = run(git_repo.root, "autopilot", "start", *argv, capsys=capsys)
        assert code == 2, err
        assert "count" in err
    assert not (git_repo.root / ".git" / "taskrail" / "runs").exists()


# 4


def test_start_creates_a_run_file_in_the_common_directory(pilot, capsys, tmp_path):
    result = data(pilot.root, "autopilot", "start", "--count", "2", capsys=capsys)
    run_id = result["run"]["id"]
    assert re.fullmatch(datetime.now(timezone.utc).strftime("%Y%m%d") + r"-1", run_id)
    path = pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json"
    assert result["path"] == str(path)
    stored = json.loads(path.read_text())
    assert stored["id"] == run_id and stored["count"] == 2 and stored["kinds"] == []
    assert stored["tasks"] == {} and stored["handed_off"] == [] and stored["decisions"] == []
    assert stored["owner"] and datetime.fromisoformat(stored["started"])

    code, out, _ = run(pilot.root, "autopilot", "start", "--count", "1", capsys=capsys)
    assert code == 0 and out.strip() != run_id and out.strip().endswith("-2")

    worktree = tmp_path / "wt"
    git(pilot.root, "worktree", "add", "-q", str(worktree), "-b", "other", "main")
    third = data(worktree, "autopilot", "start", "--count", "1", capsys=capsys)["run"]["id"]
    assert third.endswith("-3") and (pilot.root / ".git" / "taskrail" / "runs" / f"{third}.json").is_file()


def test_concurrent_starts_take_the_next_free_number(pilot):
    config = load_config(pilot.root)
    moment = datetime(2026, 9, 13, 23, 59, tzinfo=timezone.utc)
    created = [runs.create(config, 1, [], "x", now=moment)["id"] for _ in range(3)]
    assert created == ["20260913-1", "20260913-2", "20260913-3"]
    assert runs.create(config, 1, [], "x", now=moment + timedelta(minutes=2))["id"] == "20260914-1"
    assert [r["id"] for r in runs.read_all(config)] == ["20260914-1", "20260913-3", "20260913-2", "20260913-1"]


# 5


def test_start_stores_and_checks_kinds(pilot, capsys):
    run_id = data(pilot.root, "autopilot", "start", "--count", "1", "--kinds", "bug,chore", capsys=capsys)["run"]["id"]
    assert runs.read(load_config(pilot.root), run_id)["kinds"] == ["bug", "chore"]

    code, _, err = run(pilot.root, "autopilot", "start", "--count", "1", "--kinds", "nope", capsys=capsys)
    assert code == 2 and "--kinds: kind `nope` is not defined" in err

    configure(pilot, ENABLED + 'kinds = ["spike"]\n[kinds]\nallowed = ["bug", "chore", "feature"]\n')
    code, _, err = run(pilot.root, "autopilot", "start", "--count", "1", capsys=capsys)
    assert code == 2 and "[autopilot].kinds: kind `spike` is not allowed" in err
    configure(pilot, ENABLED + 'kinds = ["feature"]\n')
    run_id = data(pilot.root, "autopilot", "start", "--count", "1", capsys=capsys)["run"]["id"]
    assert runs.read(load_config(pilot.root), run_id)["kinds"] == ["feature"]
    assert len(runs.read_all(load_config(pilot.root))) == 2


def test_start_refuses_an_invalid_backlog(pilot, capsys):
    pilot.write("TODO.md", TODO.replace("| T004 | chore   |", "| T004 | nokind  |"))
    code, _, err = run(pilot.root, "autopilot", "start", "--count", "1", capsys=capsys)
    assert code == 1 and "validation error" in err
    assert runs.read_all(load_config(pilot.root)) == []


# 6


def test_claim_records_the_run(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T001", run_id)
    config = load_config(pilot.root)
    assert claims.read(config, "T001").run == run_id
    assert list(runs.read(config, run_id)["tasks"]) == ["T001"]  # still a member once `done` releases the claim

    code, _, err = run(pilot.root, "claim", "T003", "--run", "20000101-9", capsys=capsys)
    assert code == 3 and "no autopilot run `20000101-9`" in err
    assert claims.read(config, "T003") is None

    assert run(pilot.root, "claim", "T004", capsys=capsys)[0] == 0
    assert claims.read(config, "T004").run is None
    assert json.loads((pilot.root / ".git" / "taskrail" / "claims" / "T004.json").read_text())["run"] is None
    assert path.is_dir()


def test_claim_run_on_the_template_branch_still_records_the_branch(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.root.parent / "t003-lane"
    git(pilot.root, "worktree", "add", "-q", str(path), "-b", BRANCHES["T003"], "origin/main")
    result = data(path, "claim", "T003", "--run", run_id, capsys=capsys)
    assert (result["branch_recorded"], result["warning"], result["claim"]["run"]) == (True, None, run_id)
    assert data(pilot.root, "show", "T003", capsys=capsys)["branch_source"] == "recorded"
    assert list(runs.read(load_config(pilot.root), run_id)["tasks"]) == ["T003"]


def test_status_follows_a_renamed_task_branch(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T003", run_id)
    pilot.finish(path, "T003")  # releases the claim, so status resolves the branch itself
    assert run(pilot.root, "branch", "T003", "T003-renamed", capsys=capsys)[0] == 0
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert (found["state"], found["branch"]) == ("done-branch", "T003-renamed")
    assert found["worktree"] == str(path.resolve())
    assert found["touched"] == ["TODO.md"]


def test_the_remote_claim_carries_the_run(pilot, capsys):
    configure(pilot, ENABLED + '[git]\nclaim_remote = "origin"\n')
    run_id = start(pilot.root, capsys)
    assert run(pilot.root, "claim", "T003", "--run", run_id, capsys=capsys)[0] == 0
    published = json.loads(git(pilot.bare, "show", "refs/taskrail/claims/T003:claim.json"))
    assert published["run"] == run_id


def test_claim_files_without_a_run_still_load(pilot):
    config = load_config(pilot.root)
    directory = claims.claims_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "T003.json").write_text(json.dumps({"id": "T003", "owner": "old", "branch": "b", "created": "2026-01-01T00:00:00+00:00"}))
    assert claims.read(config, "T003").run is None


# 7


def test_lane_records_handle_state_reason_and_group(pilot, capsys):
    run_id = start(pilot.root, capsys)
    config = load_config(pilot.root)
    claim_file = pilot.lane("T001", run_id) and (pilot.root / ".git" / "taskrail" / "claims" / "T001.json")
    before = claim_file.read_text()

    result = data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--handle", "H1", "--state", "gate", "--reason", "plan gate", capsys=capsys)
    assert result["task"]["id"] == "T001"
    stored = runs.read(config, run_id)["tasks"]["T001"]
    assert (stored["handle"], stored["state"], stored["reason"]) == ("H1", "gate", "plan gate")
    assert datetime.fromisoformat(stored["updated"])

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "running", "--group", "ui", capsys=capsys)
    stored = runs.read(config, run_id)["tasks"]["T001"]
    assert (stored["handle"], stored["state"], stored["reason"], stored["group"]) == ("H1", "running", None, "ui")

    code, out, _ = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", capsys=capsys)
    assert code == 0 and "T001 in run" in out and "gate" in out

    for state in ("failed", "escalated"):
        code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", state, capsys=capsys)
        assert code == 2 and "needs --reason" in err
    code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "running", "--reason", "x", capsys=capsys)
    assert code == 2

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "failed", "--reason", "tests hang", capsys=capsys)
    assert runs.read(config, run_id)["tasks"]["T001"]["state"] == "failed"
    assert claim_file.read_text() == before

    assert run(pilot.root, "autopilot", "lane", "T001", "--run", "20000101-1", capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "lane", "T999", "--run", run_id, capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "lane", "T001", "--run", "../claims/T001", capsys=capsys)[0] == 3


def test_run_files_keep_keys_this_version_does_not_know(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json"
    stored = json.loads(path.read_text())
    stored["future"] = {"x": 1}
    stored["tasks"] = {"T003": {"state": "gate", "later": True}}
    path.write_text(json.dumps(stored))
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--handle", "H", capsys=capsys)
    after = json.loads(path.read_text())
    assert after["future"] == {"x": 1} and after["tasks"]["T003"]["later"] is True
    assert after["tasks"]["T003"]["state"] == "gate"


# 8


def test_handed_off_needs_done_branch_and_keeps_the_order(pilot, capsys):
    run_id = start(pilot.root, capsys)
    first = pilot.lane("T003", run_id)
    second = pilot.lane("T004", run_id)
    code, _, err = run(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "handed-off", capsys=capsys)
    assert code == 5 and "done-branch" in err
    pilot.finish(first, "T003")
    pilot.finish(second, "T004")
    capsys.readouterr()
    for task_id in ("T004", "T003", "T004"):
        result = data(pilot.root, "autopilot", "lane", task_id, "--run", run_id, "--state", "handed-off", capsys=capsys)
    assert result["handed_off"] == ["T004", "T003"]
    assert runs.read(load_config(pilot.root), run_id)["handed_off"] == ["T004", "T003"]


# 9


def test_decision_appends_to_the_run(pilot, capsys):
    run_id = start(pilot.root, capsys)
    argv = ["autopilot", "decision", "--run", run_id]
    first = data(pilot.root, *argv, "--question", "Touch map", "--decision", "T001 owns cli.py", "--reason", "fewer conflicts", capsys=capsys)
    assert first["decision"]["number"] == 1
    code, out, _ = run(pilot.root, *argv, "--question", "Order", "--decision", "T003 first", "--reason", "smaller", capsys=capsys)
    assert code == 0 and "decision 2 recorded" in out
    stored = runs.read(load_config(pilot.root), run_id)["decisions"]
    assert [(d["number"], d["question"], d["decision"], d["reason"]) for d in stored] == [
        (1, "Touch map", "T001 owns cli.py", "fewer conflicts"),
        (2, "Order", "T003 first", "smaller"),
    ]
    assert all(datetime.fromisoformat(d["recorded"]) for d in stored)
    assert run(pilot.root, *argv, "--question", " ", "--decision", "x", "--reason", "y", capsys=capsys)[0] == 2
    assert run(pilot.root, "autopilot", "decision", "--run", "20000101-1", "--question", "q", "--decision", "d", "--reason", "r", capsys=capsys)[0] == 3
    with pytest.raises(SystemExit) as missing:
        main(["--root", str(pilot.root), *argv, "--question", "q"])
    assert missing.value.code == 2
    assert status_of(pilot.root, capsys, run_id)["runs"][0]["decisions"] == stored


# 10


def test_status_derives_every_state(pilot, capsys):
    run_id = start(pilot.root, capsys)
    config = load_config(pilot.root)
    with runs.update(config, run_id) as stored:
        for task_id in ("T002", "T005"):
            runs.lane(stored, task_id)
    t001 = pilot.lane("T001", run_id)
    t003 = pilot.lane("T003", run_id)
    t004 = pilot.lane("T004", run_id)
    report = status_of(pilot.root, capsys, run_id)
    states = {r["id"]: r["state"] for r in report["runs"][0]["tasks"]}
    assert states == {"T002": "pending", "T005": "discarded", "T001": "running", "T003": "running", "T004": "running"}
    assert row(report, "T002")["blocked_by"] == ["T001"]

    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "gate", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--state", "escalated", "--reason", "governing file", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "failed", "--reason", "stuck", capsys=capsys)
    report = status_of(pilot.root, capsys, run_id)
    assert [row(report, t)["state"] for t in ("T003", "T004", "T001")] == ["gate", "escalated", "failed"]
    assert row(report, "T004")["reason"] == "governing file"

    pilot.finish(t001, "T001")  # recorded failed, but done on its branch
    pilot.finish(t003, "T003")
    capsys.readouterr()
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "handed-off", capsys=capsys)
    report = status_of(pilot.root, capsys, run_id)
    assert (row(report, "T001")["state"], row(report, "T003")["state"]) == ("done-branch", "handed-off")

    mark_merged(pilot, "T003")
    assert row(status_of(pilot.root, capsys, run_id), "T003")["state"] == "done-merged"

    # merged only on origin/main: a clone pushes the ✅, and the orchestrator fetched it
    clone = pilot.root.parent / "clone"
    git(pilot.root, "clone", "-q", str(pilot.bare), str(clone))
    git(pilot.root, "push", "-q", "origin", "main")
    git(clone, "pull", "-q")
    (clone / "TODO.md").write_text((clone / "TODO.md").read_text().replace("| ⬜ | T001 |", "| ✅ | T001 |"))
    commit_all(clone, "feat: T001 (T001)")
    git(clone, "push", "-q", "origin", "main")
    git(pilot.root, "fetch", "-q", "origin")
    report = status_of(pilot.root, capsys, run_id)
    assert row(report, "T001")["state"] == "done-merged"
    assert report["runs"][0]["done_merged"] == 2 and report["runs"][0]["complete"] is True


def test_a_stale_claim_stays_running_with_its_reason(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T004", run_id)
    git(pilot.root, "worktree", "remove", "--force", str(path))
    found = row(status_of(pilot.root, capsys, run_id), "T004")
    assert found["state"] == "running"
    assert "no longer exists" in found["claim"]["stale"]


# 11


def test_a_running_lane_idle_past_silent_minutes_is_silent(pilot, capsys):
    configure(pilot, ENABLED + "silent_minutes = 30\n")
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T003", run_id)
    (path / "work.txt").write_text("progress")
    config = load_config(pilot.root)

    def report(now):
        project, _ = load_project(config)
        return row(compute_status(project, runs.read_all(config), claims.read_all(config), now=now), "T003")

    now = datetime.now(timezone.utc)
    assert report(now)["silent"] is False
    later = now + timedelta(minutes=90)
    found = report(later)
    assert found["silent"] is True and found["idle_minutes"] >= 89

    moment = (later - timedelta(minutes=5)).timestamp()
    os.utime(path / "work.txt", (moment, moment))
    found = report(later)
    assert found["silent"] is False and found["idle_minutes"] == 5

    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "gate", capsys=capsys)
    assert report(now + timedelta(days=2))["silent"] is False


# 12


def test_touched_files_and_overlaps_between_lanes(pilot, capsys):
    run_id = start(pilot.root, capsys)
    first = pilot.lane("T003", run_id)
    second = pilot.lane("T004", run_id)
    (first / "shared.py").write_text("one")
    (first / "only-first.py").write_text("one")
    commit_all(first, "work")
    (second / "shared.py").write_text("two")
    report = status_of(pilot.root, capsys, run_id)
    assert row(report, "T003")["touched"] == ["only-first.py", "shared.py"]
    assert row(report, "T004")["touched"] == ["shared.py"]
    assert report["overlaps"] == {"shared.py": ["T003", "T004"]}


def test_a_stacked_lane_does_not_list_its_dependency_files(pilot, capsys):
    run_id = start(pilot.root, capsys)
    base = pilot.lane("T001", run_id)
    (base / "base.py").write_text("base")
    commit_all(base, "base work")
    pilot.finish(base, "T001")
    stacked = pilot.lane("T002", run_id, base=BRANCHES["T001"])
    (stacked / "stacked.py").write_text("stacked")
    commit_all(stacked, "stacked work")
    report = status_of(pilot.root, capsys, run_id)
    assert row(report, "T002")["touched"] == ["stacked.py"]
    assert row(report, "T001")["touched"] == ["TODO.md", "base.py"]
    assert report["overlaps"] == {}


# 13


def test_handoff_queue_puts_dependencies_first(pilot, capsys):
    run_id = start(pilot.root, capsys)
    base = pilot.lane("T001", run_id)
    pilot.finish(base, "T001")
    stacked = pilot.lane("T002", run_id, base=BRANCHES["T001"])
    commit_all_date = "2026-01-01T00:00:00+00:00"
    assert main(["--root", str(stacked), "done", "T002", "--owner", "lane"]) == 0
    commit_all(stacked, "chore(T002): mark done", date=commit_all_date)  # finished "earlier" than T001
    capsys.readouterr()
    handoff = status_of(pilot.root, capsys, run_id)["runs"][0]["handoff"]
    assert handoff == {"mode": "sequential", "in_review": None, "queue": ["T001", "T002"], "next": "T001"}

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "handed-off", capsys=capsys)
    handoff = status_of(pilot.root, capsys, run_id)["runs"][0]["handoff"]
    assert (handoff["in_review"], handoff["queue"], handoff["next"]) == ("T001", ["T002"], None)

    mark_merged(pilot, "T001")
    handoff = status_of(pilot.root, capsys, run_id)["runs"][0]["handoff"]
    assert (handoff["in_review"], handoff["queue"], handoff["next"]) == (None, ["T002"], "T002")


# 14


def test_status_renders_decision_record_paths(pilot, capsys):
    run_id = start(pilot.root, capsys)
    pilot.lane("T003", run_id)
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert found["decisions"] == "docs/autopilot/decisions/T003-independent.md"
    assert found["decisions_index"] == "docs/autopilot/decisions/README.md"
    configure(pilot, ENABLED + 'decisions = "{artifacts}/records/{epic}/{id}.md"\ndecisions_index = "{artifacts}/records/index.md"\n')
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert (found["decisions"], found["decisions_index"]) == ("docs/records/E01/T003.md", "docs/records/index.md")


# 15


def test_status_without_runs_and_for_an_unknown_run(pilot, capsys):
    assert status_of(pilot.root, capsys) == {"runs": [], "overlaps": {}, "fetched": []}
    code, out, _ = run(pilot.root, "autopilot", "status", capsys=capsys)
    assert code == 0 and "no autopilot runs" in out
    code, _, err = run(pilot.root, "autopilot", "status", "--run", "20000101-1", capsys=capsys)
    assert code == 3 and "no autopilot run" in err


def test_status_lists_every_run_newest_first(pilot, capsys):
    config = load_config(pilot.root)
    older = runs.create(config, 1, [], "x", now=datetime(2026, 1, 1, tzinfo=timezone.utc))["id"]
    newer = start(pilot.root, capsys)
    report = status_of(pilot.root, capsys)
    assert [r["id"] for r in report["runs"]] == [newer, older]
    assert [r["complete"] for r in report["runs"]] == [False, False]
    text = run(pilot.root, "autopilot", "status", capsys=capsys)[1]
    assert text.index(newer) < text.index(older)


def test_status_fetches_only_when_asked(pilot, capsys):
    run_id = start(pilot.root, capsys)
    with runs.update(load_config(pilot.root), run_id) as stored:
        runs.lane(stored, "T004")
    clone = pilot.root.parent / "fetch-clone"
    git(pilot.root, "clone", "-q", str(pilot.bare), str(clone))
    (clone / "TODO.md").write_text((clone / "TODO.md").read_text().replace("| ⬜ | T004 |", "| ✅ | T004 |"))
    commit_all(clone, "feat: T004 (T004)")
    git(clone, "push", "-q", "origin", "main")
    before = git(pilot.root, "rev-parse", "origin/main")
    report = status_of(pilot.root, capsys, run_id)
    assert (row(report, "T004")["state"], report["fetched"]) == ("pending", [])
    assert git(pilot.root, "rev-parse", "origin/main") == before
    report = data(pilot.root, "autopilot", "status", "--run", run_id, "--fetch", capsys=capsys)
    assert (row(report, "T004")["state"], report["fetched"]) == ("done-merged", ["origin"])


def test_status_lane_and_decision_work_while_disabled(pilot, capsys):
    run_id = start(pilot.root, capsys)
    configure(pilot, "")
    assert run(pilot.root, "autopilot", "start", "--count", "1", capsys=capsys)[0] == 5
    assert data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--handle", "H", capsys=capsys)["task"]["handle"] == "H"
    assert run(pilot.root, "autopilot", "decision", "--run", run_id, "--question", "q", "--decision", "d", "--reason", "r", capsys=capsys)[0] == 0
    assert [r["id"] for r in status_of(pilot.root, capsys)["runs"]] == [run_id]
    text = run(pilot.root, "autopilot", "status", capsys=capsys)[1]
    assert f"run {run_id}" in text and "T003" in text and "hand-off: next —" in text


def test_status_refuses_an_invalid_backlog_unless_allowed(pilot, capsys):
    start(pilot.root, capsys)
    pilot.write("TODO.md", TODO.replace("| T004 | chore   |", "| T004 | nokind  |"))
    assert run(pilot.root, "autopilot", "status", capsys=capsys)[0] == 1
    assert run(pilot.root, "autopilot", "status", "--allow-invalid", capsys=capsys)[0] == 0
