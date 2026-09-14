"""`autopilot notify`, `lane --gate` and the escalation flags in `autopilot status` (T032).

Notify commands here are local shell commands writing to temporary files; nothing leaves the machine.
"""

import json
import os
import time
from pathlib import Path

import pytest
from test_autopilot import ENABLED, TODO, commit_all, configure, data, pilot, row, run, start, status_of  # noqa: F401

from taskrail.autopilot import runs
from taskrail.config import load_config


def escalation_module():
    from taskrail.autopilot import escalation

    return escalation


def toml_string(value) -> str:
    return "'" + str(value) + "'"  # a TOML literal string: no escapes to worry about in paths


def notify_config(command: str, extra: str = "") -> str:
    return ENABLED + f"notify = {toml_string(command)}\n" + extra


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat = Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().split(") ", 1)[1][0] != "Z"  # a zombie is dead, only not yet reaped
    except (OSError, IndexError):
        return True


# 1


def test_lane_records_the_gate_a_lane_is_stopped_at(pilot, capsys):
    run_id = start(pilot.root, capsys)
    config = load_config(pilot.root)
    pilot.lane("T001", run_id)

    result = data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "plan", "--reason", "plan gate", capsys=capsys)
    assert result["task"]["gate"] == "plan"
    assert runs.read(config, run_id)["tasks"]["T001"]["gate"] == "plan"

    before = (pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json").read_text()
    code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "nope", capsys=capsys)
    assert code == 2 and "plan, implement, verify" in err
    assert (pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json").read_text() == before

    for extra in (["--state", "running"], ["--state", "failed", "--reason", "stuck"]):
        code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, *extra, "--gate", "plan", capsys=capsys)
        assert code == 2 and "--gate" in err

    # without --state on a lane recorded at a gate, --gate replaces the stage
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--gate", "implement", capsys=capsys)
    assert runs.read(config, run_id)["tasks"]["T001"]["gate"] == "implement"

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "escalated", "--reason", "needs a human", capsys=capsys)
    stored = runs.read(config, run_id)["tasks"]["T001"]
    assert (stored["state"], stored["gate"]) == ("escalated", "implement")

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "running", capsys=capsys)
    assert runs.read(config, run_id)["tasks"]["T001"]["gate"] is None

    code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--gate", "plan", capsys=capsys)
    assert code == 2 and "--gate" in err  # recorded running, no --state

    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "verify", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "failed", "--reason", "stuck", capsys=capsys)
    assert runs.read(config, run_id)["tasks"]["T001"]["gate"] is None

    with runs.update(config, run_id) as stored:
        runs.lane(stored, "T003")  # a lane record written without `gate`
    assert "gate" not in json.loads((pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json").read_text())["tasks"]["T003"]
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert found["gate"] is None and found["escalation"] == []


def test_lane_records_close_for_the_stop_after_done_in_every_kind(pilot, capsys):
    """T050: `close` names the stop after `taskrail done`, which no kind has as a stage."""
    configure(pilot, ENABLED + 'escalate_gates = ["feature:close"]\n')
    run_id = start(pilot.root, capsys)
    config = load_config(pilot.root)
    feature = pilot.lane("T001", run_id)
    pilot.lane("T003", run_id)

    # a bug task, whose stages (diagnose, fix, impact) differ from a feature's
    result = data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "gate", "--gate", "close", capsys=capsys)
    assert result["task"]["gate"] == "close"
    assert runs.read(config, run_id)["tasks"]["T003"]["gate"] == "close"

    # the F10 scenario: the feature task is done and committed on its branch, then the stop is recorded
    pilot.finish(feature, "T001")
    result = data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "close", capsys=capsys)
    assert result["task"]["gate"] == "close"
    stored = runs.read(config, run_id)["tasks"]["T001"]
    assert (stored["state"], stored["gate"]) == ("gate", "close")
    found = row(status_of(pilot.root, capsys, run_id), "T001")
    assert (found["state"], found["gate"], found["escalate_gate"], found["escalation"]) == ("done-branch", "close", None, [])

    # the state rules of --gate still hold for close, and a refusal writes nothing
    runs_file = pilot.root / ".git" / "taskrail" / "runs" / f"{run_id}.json"
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "running", capsys=capsys)
    before = runs_file.read_text()
    for extra in (["--state", "running"], ["--state", "failed", "--reason", "stuck"], []):
        code, _, err = run(pilot.root, "autopilot", "lane", "T003", "--run", run_id, *extra, "--gate", "close", capsys=capsys)
        assert code == 2 and "--gate needs --state gate or escalated" in err, extra
    assert runs_file.read_text() == before

    # an unknown name still exits 2, naming the kind's stages and close
    code, _, err = run(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "gate", "--gate", "nope", capsys=capsys)
    assert code == 2 and "(diagnose, fix, impact) or `close`" in err
    assert runs_file.read_text() == before


def test_lane_records_close_for_a_task_whose_kind_is_not_defined(pilot, capsys):
    """T050 D2: close does not depend on the kind's stages, so an undefined kind does not refuse it."""
    run_id = start(pilot.root, capsys)
    pilot.lane("T004", run_id)
    todo = pilot.root / "TODO.md"
    todo.write_text(todo.read_text().replace("| T004 | chore   |", "| T004 | mystery |"))
    commit_all(pilot.root, "an undefined kind")

    result = data(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--state", "gate", "--gate", "close", capsys=capsys)
    assert result["task"]["gate"] == "close"
    code, _, err = run(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--gate", "scope", capsys=capsys)
    assert code == 2 and "kind `mystery` is not defined" in err


# 2


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("docs/adr", "docs/adr/0001.md", True),
        ("docs/adr/", "docs/adr/0001.md", True),
        ("docs/adr", "docs/adr", True),
        ("docs/adr", "docs/adrx.md", False),
        ("docs/adr", "other/docs/adr/0001.md", False),
        ("CONSTITUTION.md", "CONSTITUTION.md", True),
        ("CONSTITUTION.md", "docs/CONSTITUTION.md", False),
        ("*.md", "README.md", True),
        ("*.md", "docs/README.md", False),
        ("docs/*.md", "docs/a/b.md", False),
        ("docs/*", "docs/a/b.md", True),  # matches the leading directory docs/a
        ("docs/**/x.md", "docs/x.md", True),
        ("docs/**/x.md", "docs/a/b/x.md", True),
        ("**/policy.md", "policy.md", True),
        ("**/policy.md", "a/b/policy.md", True),
        ("docs/**", "docs/a/b.md", True),
        ("src/**/policy-*.py", "src/policy-y.py", True),
        ("src/**/policy-*.py", "src/policy.py", False),
        ("file?.txt", "file1.txt", True),
        ("file?.txt", "file10.txt", False),
        ("a?b", "a/b", False),
        ("[ab].md", "a.md", True),
        ("[ab].md", "c.md", False),
        ("[!ab].md", "c.md", True),
        ("[!ab].md", "a.md", False),
        ("Docs/ADR", "docs/adr/0001.md", False),
        ("./ops/x.toml", "ops/x.toml", True),
        ("a.b", "aXb", False),
        ("a+b(c)", "a+b(c)", True),
    ],
)
def test_governing_patterns(pattern, path, expected):
    assert escalation_module().matches(pattern, path) is expected


def test_status_flags_governing_paths_a_lane_touched(pilot, capsys):
    configure(pilot, ENABLED + 'governing = ["docs/adr", "CONSTITUTION.md", "src/**/policy-*.py", "./ops/*.toml"]\n')
    run_id = start(pilot.root, capsys)
    lane = pilot.lane("T003", run_id)
    for path in ("docs/adr/0001.md", "src/a/b/policy-x.py", "ops/deploy.toml", "docs/adrx.md", "ops/sub/deploy.toml", "src/policy.py"):
        (lane / path).parent.mkdir(parents=True, exist_ok=True)
        (lane / path).write_text("x")
    commit_all(lane, "work")
    (lane / "CONSTITUTION.md").write_text("uncommitted")
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert found["governing_touched"] == ["CONSTITUTION.md", "docs/adr/0001.md", "ops/deploy.toml", "src/a/b/policy-x.py"]
    assert found["escalation"] == ["governing"]
    assert found["escalate_gate"] is None


# 3


def test_no_governing_flag_without_a_match_or_a_branch(pilot, capsys):
    run_id = start(pilot.root, capsys)
    lane = pilot.lane("T003", run_id)
    (lane / "docs").mkdir()
    (lane / "docs" / "notes.md").write_text("x")
    with runs.update(load_config(pilot.root), run_id) as stored:
        runs.lane(stored, "T002")  # pending
    report = status_of(pilot.root, capsys, run_id)
    assert (row(report, "T003")["governing_touched"], row(report, "T003")["escalation"]) == ([], [])

    configure(pilot, ENABLED + 'governing = ["docs"]\n')
    report = status_of(pilot.root, capsys, run_id)
    assert row(report, "T003")["governing_touched"] == ["docs/notes.md"]
    assert (row(report, "T002")["state"], row(report, "T002")["governing_touched"]) == ("pending", [])

    commit_all(lane, "notes")
    pilot.finish(lane, "T003")
    todo = (pilot.root / "TODO.md").read_text(encoding="utf-8")
    (pilot.root / "TODO.md").write_text(todo.replace("| ⬜ | T003 |", "| ✅ | T003 |"), encoding="utf-8")
    commit_all(pilot.root, "feat: T003 (T003)")
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert (found["state"], found["governing_touched"], found["escalation"]) == ("done-merged", [], [])


# 4


def test_status_flags_a_gate_listed_in_escalate_gates(pilot, capsys):
    configure(pilot, ENABLED + 'governing = ["docs/adr"]\nescalate_gates = ["feature:plan", "chore:scope"]\n')
    run_id = start(pilot.root, capsys)
    feature = pilot.lane("T001", run_id)
    pilot.lane("T003", run_id)
    chore = pilot.lane("T004", run_id)

    def lane(task_id, *argv):
        data(pilot.root, "autopilot", "lane", task_id, "--run", run_id, *argv, capsys=capsys)

    def flags(task_id):
        found = row(status_of(pilot.root, capsys, run_id), task_id)
        return found["gate"], found["escalate_gate"], found["escalation"]

    assert flags("T001") == (None, None, [])  # running
    lane("T001", "--state", "gate", "--gate", "plan")
    assert flags("T001") == ("plan", "feature:plan", ["escalate-gate"])
    lane("T001", "--gate", "implement")
    assert flags("T001") == ("implement", None, [])
    lane("T001", "--state", "escalated", "--reason", "asked", "--gate", "plan")
    assert flags("T001") == ("plan", "feature:plan", ["escalate-gate"])

    (feature / "docs" / "adr").mkdir(parents=True)
    (feature / "docs" / "adr" / "0002.md").write_text("x")
    commit_all(feature, "adr")
    assert flags("T001") == ("plan", "feature:plan", ["governing", "escalate-gate"])

    lane("T003", "--state", "gate", "--gate", "diagnose")
    assert flags("T003") == ("diagnose", None, [])

    lane("T004", "--state", "gate", "--gate", "scope")
    assert flags("T004") == ("scope", "chore:scope", ["escalate-gate"])
    pilot.finish(chore, "T004")
    capsys.readouterr()
    found = row(status_of(pilot.root, capsys, run_id), "T004")
    assert (found["state"], found["escalate_gate"], found["escalation"]) == ("done-branch", None, [])

    lane("T001", "--state", "running")
    assert flags("T001") == (None, None, ["governing"])


# 5


def test_status_text_marks_flagged_lanes(pilot, capsys):
    configure(pilot, ENABLED + 'governing = ["docs/adr"]\nescalate_gates = ["feature:plan", "bug:fix"]\n')
    run_id = start(pilot.root, capsys)
    feature = pilot.lane("T001", run_id)
    bug = pilot.lane("T003", run_id)
    pilot.lane("T004", run_id)
    for lane_path, name in ((feature, "0001.md"), (bug, "0002.md")):
        (lane_path / "docs" / "adr").mkdir(parents=True)
        (lane_path / "docs" / "adr" / name).write_text("x")
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "plan", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--state", "gate", "--gate", "scope", capsys=capsys)
    code, out, _ = run(pilot.root, "autopilot", "status", capsys=capsys)
    assert code == 0
    lines = {line.split()[0]: line for line in out.splitlines() if line.startswith("  T")}
    assert lines["T001"].endswith("ESCALATE: governing docs/adr/0001.md; gate feature:plan")
    assert lines["T003"].endswith("ESCALATE: governing docs/adr/0002.md")
    assert "ESCALATE" not in lines["T004"]
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "gate", "--gate", "fix", capsys=capsys)
    (bug / "docs" / "adr" / "0002.md").unlink()
    out = run(pilot.root, "autopilot", "status", capsys=capsys)[1]
    t003 = next(line for line in out.splitlines() if line.startswith("  T003"))
    assert t003.endswith("ESCALATE: gate bug:fix")


# 6


def test_notify_runs_the_command_with_the_message_and_environment(pilot, capsys, tmp_path):
    out_dir = tmp_path / "notified"
    out_dir.mkdir()
    command = f"cat > {out_dir}/message.txt; env | grep ^TASKRAIL_ | sort > {out_dir}/env.txt; pwd > {out_dir}/cwd.txt"
    configure(pilot, notify_config(command))
    run_id = start(pilot.root, capsys)
    pilot.lane("T001", run_id)
    data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "plan", "--reason", "plan gate", capsys=capsys)

    result = data(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, "--task", "T001", "--message", "Approve?", capsys=capsys)
    message = f"taskrail autopilot: escalation in run {run_id}\nT001 Base task\nlane: gate at plan — plan gate\n\nApprove?\n"
    assert (result["sent"], result["exit_code"], result["timed_out"], result["error"], result["skipped"]) == (True, 0, False, None, None)
    assert (result["event"], result["run"], result["task"], result["command"], result["message"]) == ("escalation", run_id, "T001", command, message)
    assert (out_dir / "message.txt").read_text(encoding="utf-8") == message
    assert (out_dir / "env.txt").read_text().splitlines() == ["TASKRAIL_EVENT=escalation", f"TASKRAIL_RUN={run_id}", "TASKRAIL_TASK=T001"]
    assert Path((out_dir / "cwd.txt").read_text().strip()).resolve() == pilot.root.resolve()

    result = data(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, capsys=capsys)
    assert result["sent"] is True and result["task"] is None
    assert (out_dir / "message.txt").read_text(encoding="utf-8") == f"taskrail autopilot: escalation in run {run_id}\n"
    assert (out_dir / "env.txt").read_text().splitlines() == ["TASKRAIL_EVENT=escalation", f"TASKRAIL_RUN={run_id}", "TASKRAIL_TASK="]

    code, out, err = run(pilot.root, "autopilot", "notify", "--event", "lane-done", "--run", run_id, "--task", "T001", capsys=capsys)
    assert (code, out.strip(), err) == (0, "notified: lane-done", "")
    assert (out_dir / "message.txt").read_text(encoding="utf-8") == f"taskrail autopilot: lane-done in run {run_id}\nT001 Base task\nlane: gate at plan — plan gate\n"


# 7


def test_notify_skips_events_not_configured_and_an_empty_command(pilot, capsys, tmp_path):
    marker = tmp_path / "sent.txt"
    configure(pilot, notify_config(f"cat > {marker}"))
    run_id = start(pilot.root, capsys)
    pilot.lane("T003", run_id)

    result = data(pilot.root, "autopilot", "notify", "--event", "lane-failed", "--run", run_id, "--task", "T003", capsys=capsys)
    assert result["sent"] is False and "notify_on" in result["skipped"]
    code, out, _ = run(pilot.root, "autopilot", "notify", "--event", "lane-failed", "--run", run_id, "--task", "T003", capsys=capsys)
    assert code == 0 and out.startswith("not sent: ")
    assert not marker.exists()

    configure(pilot, ENABLED)
    result = data(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, capsys=capsys)
    assert result["sent"] is False and "[autopilot].notify" in result["skipped"]
    assert not marker.exists()


# 8


def test_a_failing_notify_command_is_reported_and_never_blocks(pilot, capsys):
    configure(pilot, notify_config("echo out; echo boom >&2; exit 3"))
    run_id = start(pilot.root, capsys)
    code, out, err = run(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, "--json", capsys=capsys)
    result = json.loads(out)  # the command's own stdout is not mixed into taskrail's
    assert code == 0
    assert (result["sent"], result["exit_code"], result["timed_out"]) == (False, 3, False)
    assert (result["stdout"], result["stderr"]) == ("out\n", "boom\n")
    assert "3" in result["error"]
    assert err.startswith("taskrail: warning: ") and "boom" in err

    configure(pilot, notify_config("taskrail-t032-no-such-command"))
    code, out, err = run(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, "--json", capsys=capsys)
    result = json.loads(out)
    assert code == 0 and result["sent"] is False and result["exit_code"] == 127
    assert result["stderr"] and "taskrail: warning: " in err


def test_a_notify_command_past_the_timeout_is_killed_with_its_children(pilot, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("taskrail.autopilot.notify.TIMEOUT_SECONDS", 1)
    pids = tmp_path / "pids"
    configure(pilot, notify_config(f"echo $$ > {pids}.shell; sleep 60 & echo $! > {pids}.child; wait"))
    run_id = start(pilot.root, capsys)
    began = time.monotonic()
    code, out, err = run(pilot.root, "autopilot", "notify", "--event", "escalation", "--run", run_id, "--json", capsys=capsys)
    elapsed = time.monotonic() - began
    result = json.loads(out)
    assert code == 0 and elapsed < 10
    assert (result["sent"], result["timed_out"], result["exit_code"]) == (False, True, None)
    assert "timed out" in result["error"] and "taskrail: warning: " in err
    for suffix in ("shell", "child"):
        pid = int(Path(f"{pids}.{suffix}").read_text())
        deadline = time.monotonic() + 5
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not alive(pid), suffix


# 9


def test_notify_checks_its_arguments_before_running_anything(pilot, capsys, tmp_path):
    marker = tmp_path / "sent.txt"
    configure(pilot, notify_config(f"cat >> {marker}", 'notify_on = ["escalation", "lane-done", "lane-failed"]\n'))
    run_id = start(pilot.root, capsys)
    pilot.lane("T001", run_id)

    def code_of(*argv):
        return run(pilot.root, "autopilot", "notify", *argv, capsys=capsys)[0]

    assert code_of("--event", "escalation", "--run", "20000101-1") == 3
    assert code_of("--event", "escalation", "--run", run_id, "--task", "T999") == 3
    assert code_of("--event", "escalation", "--run", run_id, "--task", "T003") == 3  # not in the run
    assert code_of("--event", "lane-done", "--run", run_id) == 2
    assert code_of("--event", "lane-failed", "--run", run_id) == 2
    with pytest.raises(SystemExit) as exited:
        code_of("--event", "bogus", "--run", run_id)
    assert exited.value.code == 2
    assert not marker.exists()

    configure(pilot, f"\n[autopilot]\nnotify = {toml_string(f'cat >> {marker}')}\n")  # enabled is absent
    pilot.write("TODO.md", TODO.replace("| T004 | chore   |", "| T004 | nokind  |"))
    assert code_of("--event", "escalation", "--run", run_id, "--task", "T001") == 0  # disabled, invalid backlog
    assert marker.read_text(encoding="utf-8").startswith(f"taskrail autopilot: escalation in run {run_id}\nT001 Base task\n")


# 10


def test_status_never_runs_the_notify_command(pilot, capsys, tmp_path):
    marker = tmp_path / "sent.txt"
    configure(pilot, notify_config(f"cat > {marker}", 'governing = ["docs"]\nescalate_gates = ["bug:diagnose"]\nnotify_on = ["escalation", "lane-done", "lane-failed"]\n'))
    run_id = start(pilot.root, capsys)
    lane = pilot.lane("T003", run_id)
    (lane / "docs").mkdir()
    (lane / "docs" / "x.md").write_text("x")
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--state", "escalated", "--reason", "governing", "--gate", "diagnose", capsys=capsys)
    assert row(status_of(pilot.root, capsys, run_id), "T003")["escalation"] == ["governing", "escalate-gate"]
    assert run(pilot.root, "autopilot", "status", capsys=capsys)[0] == 0
    assert not marker.exists()
