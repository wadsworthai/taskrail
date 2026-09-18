"""T105: an escalated lane frees its lane, and the human's answer parks the task until `next` takes it again.

DESIGN.md §12.1, §12.4, §12.6 and §12.7.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from conftest import git
from test_autopilot_next import backdate, commit_all, configure, data, dispatch, ids, pilot, row, run, start, stored  # noqa: F401

from taskrail import install
from taskrail.autopilot import runs
from taskrail.cli import main
from taskrail.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def parked(result) -> dict:
    """The `parked` entries of a `next` report, by task ID."""
    return {entry["id"]: entry for entry in result["parked"]}


def lane(root, capsys, run_id, task_id, *argv):
    return data(root, "autopilot", "lane", task_id, "--run", run_id, *argv, capsys=capsys)


def set_updated(root, run_id, task_id, minutes):
    """Move a lane's last update into the past, so answers can be ordered within one second."""
    moment = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    with runs.update(load_config(root), run_id) as record:
        record["tasks"][task_id]["updated"] = moment


# --- 1. An escalated lane frees its lane and keeps everything else (criteria 1, 2) ----------------


def test_an_escalated_lane_frees_its_lane_and_keeps_its_claim_and_its_place(pilot, capsys):
    configure(pilot, "max_lanes = 3\n")
    run_id = start(pilot.root, capsys, count=6)
    for task_id in ("T001", "T002", "T003"):
        pilot.lane(task_id, run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "governing", "--gate", "plan")
    lane(pilot.root, capsys, run_id, "T002", "--state", "escalated", "--reason", "a premise", "--gate", "fix")

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T005", "T006"]  # the two freed lanes are filled
    assert [entry["id"] for entry in result["lanes"]["occupied"]] == ["T003", "T005", "T006"]
    assert result["limited_by"] is None

    found = row(pilot.root, capsys, run_id, "T001")
    assert found["state"] == "escalated"
    assert found["claim"]["owner"] == "lane"
    assert (found["branch"], found["gate"], found["reason"]) == ("T001-first-ui", "plan", "governing")
    assert found["worktree"] and Path(found["worktree"]).is_dir()
    assert result["remaining"] == 1  # 6 − T001, T002, T003 (all counted) − the two just dispatched


def test_an_escalated_lane_gives_its_resource_values_back(pilot, capsys):
    configure(pilot, 'max_lanes = 2\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433", "5434"]\n')
    run_id = start(pilot.root, capsys, count=6)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002"]
    pilot.lane("T001", run_id)
    pilot.lane("T002", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked")

    result = dispatch(pilot.root, capsys, run_id)
    assert result["released"] == [{"id": "T001", "run": run_id, "resources": {"PORT": "5433"}}]
    assert ids(result) == ["T003"]
    assert result["dispatch"][0]["resources"] == {"PORT": "5433"}
    assert stored(pilot.root, run_id)["tasks"]["T001"]["resources"] == {}


# --- 2. Recording the answer (criteria 4, 5) -----------------------------------------------------


def test_lane_state_parked_records_the_answer_and_keeps_the_gate(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    run_id = start(pilot.root, capsys, count=6)
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "governing", "--gate", "plan")

    result = lane(pilot.root, capsys, run_id, "T001", "--state", "parked", "--reason", "the human approved the edit")
    assert (result["task"]["state"], result["task"]["gate"]) == ("parked", "plan")
    entry = stored(pilot.root, run_id)["tasks"]["T001"]
    assert (entry["state"], entry["gate"], entry["reason"]) == ("parked", "plan", "the human approved the edit")
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "parked"

    code, out, _ = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "parked", capsys=capsys)
    assert code == 0 and "parked" in out  # --reason is optional
    assert stored(pilot.root, run_id)["tasks"]["T001"]["gate"] == "plan"


def test_parked_is_refused_for_a_task_that_holds_no_lane(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    run_id = start(pilot.root, capsys, count=6)
    code, _, err = run(pilot.root, "autopilot", "lane", "T006", "--run", run_id, "--state", "parked", capsys=capsys)
    assert code == 5 and "T006 is pending" in err
    assert "running, gate, escalated, failed or parked" in err

    pilot.lane("T001", run_id)
    pilot.finish("T001")
    code, _, err = run(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "parked", capsys=capsys)
    assert code == 5 and "T001 is done-branch" in err


# --- 3. `next` takes parked tasks first (criteria 6, 7, 8) ---------------------------------------


def test_next_redispatches_a_parked_task_before_a_task_never_started(pilot, capsys):
    configure(pilot, 'max_lanes = 1\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433"]\n')
    run_id = start(pilot.root, capsys, count=6)
    first = dispatch(pilot.root, capsys, run_id)
    assert ids(first) == ["T001"] and first["dispatch"][0]["restart"] is False
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked", "--gate", "plan")
    lane(pilot.root, capsys, run_id, "T001", "--state", "parked", "--reason", "answered")

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001"]  # not T002, which has never started
    entry = result["dispatch"][0]
    assert entry["restart"] is True
    assert (entry["branch"], entry["resources"]) == ("T001-first-ui", {"PORT": "5433"})
    assert parked(result)["T001"] == {"id": "T001", "run": run_id, "gate": "plan", "reason": "answered", "dispatched": True, "why": None}

    entry = stored(pilot.root, run_id)["tasks"]["T001"]
    assert (entry["state"], entry["gate"], entry["reason"]) == ("running", None, None)
    assert runs.dispatch_live(entry, 15)
    assert row(pilot.root, capsys, run_id, "T001")["state"] == "running"
    assert parked(dispatch(pilot.root, capsys, run_id)) == {}  # it is no longer parked


def test_a_parked_task_returns_even_when_the_run_s_count_is_used_up(pilot, capsys):
    configure(pilot, "max_lanes = 2\n")
    run_id = start(pilot.root, capsys, count=1)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001"]
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked")
    lane(pilot.root, capsys, run_id, "T001", "--state", "parked")

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T001"]
    assert result["remaining"] == 0  # the task was already counted; the redispatch does not lower it
    assert result["limited_by"] == "count"


def test_parked_tasks_return_oldest_answer_first(pilot, capsys):
    configure(pilot, "max_lanes = 1\n")
    run_id = start(pilot.root, capsys, count=6)
    for task_id in ("T001", "T002"):
        pilot.lane(task_id, run_id)
        lane(pilot.root, capsys, run_id, task_id, "--state", "escalated", "--reason", "asked")
        lane(pilot.root, capsys, run_id, task_id, "--state", "parked")
    set_updated(pilot.root, run_id, "T002", 30)  # answered half an hour before T001

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == ["T002"]
    assert parked(result)["T001"]["dispatched"] is False


def test_a_parked_task_whose_claim_was_released_is_dispatched_once(pilot, capsys):
    configure(pilot, "max_lanes = 3\n")
    run_id = start(pilot.root, capsys, count=6)
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked")
    lane(pilot.root, capsys, run_id, "T001", "--state", "parked")
    assert main(["--root", str(pilot.root), "release", "T001", "--owner", "lane"]) == 0

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result).count("T001") == 1  # the parked pass, not the candidate list, sends it back
    assert ids(result)[0] == "T001" and result["dispatch"][0]["restart"] is True
    # It is eligible again without its claim, so the candidate list sees it — and skips the lane it now holds.
    assert {entry["id"]: entry["reason"] for entry in result["skipped"]}["T001"] == f"dispatched in run {run_id}"


# --- 4. Nowhere to go: the answer waits (criteria 9, 10) -----------------------------------------


def test_a_parked_task_waits_while_every_lane_is_busy(pilot, capsys):
    configure(pilot, "max_lanes = 1\n")
    run_id = start(pilot.root, capsys, count=6)
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked", "--gate", "plan")
    lane(pilot.root, capsys, run_id, "T001", "--state", "parked", "--reason", "answered")
    pilot.lane("T003", run_id)  # the freed lane went to another task

    result = dispatch(pilot.root, capsys, run_id)
    assert ids(result) == []
    assert parked(result)["T001"]["dispatched"] is False
    assert parked(result)["T001"]["why"] == "no free lane"
    assert result["limited_by"] == "max_lanes"
    assert stored(pilot.root, run_id)["tasks"]["T001"]["state"] == "parked"

    code, out, _ = run(pilot.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert code == 0 and re.search(r"^\s+parked T001.*no free lane", out, re.M)


def test_the_preview_lists_parked_tasks_and_dispatches_none(pilot, capsys):
    configure(pilot, "max_lanes = 3\n")
    run_id = start(pilot.root, capsys, count=6)
    pilot.lane("T001", run_id)
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "asked")
    lane(pilot.root, capsys, run_id, "T001", "--state", "parked")

    result = dispatch(pilot.root, capsys)  # no --run: a preview
    assert result["preview"] is True
    assert "T001" not in ids(result)
    assert parked(result)["T001"]["dispatched"] is False
    assert parked(result)["T001"]["why"] == f"needs --run {run_id}"
    assert stored(pilot.root, run_id)["tasks"]["T001"]["state"] == "parked"


# --- 5. What holds a lane, in `status` (criterion 11) ---------------------------------------------


def test_status_reports_which_tasks_hold_a_lane(pilot, capsys):
    configure(pilot, "max_lanes = 6\n")
    run_id = start(pilot.root, capsys, count=6)
    with runs.update(load_config(pilot.root), run_id) as record:
        runs.lane(record, "T004")  # a member of the run that was never dispatched
    assert "T006" in ids(dispatch(pilot.root, capsys, run_id))  # T006 stays dispatched, never claimed
    for task_id in ("T001", "T002", "T003", "T005"):
        pilot.lane(task_id, run_id)
    lane(pilot.root, capsys, run_id, "T002", "--state", "gate", "--gate", "fix")
    lane(pilot.root, capsys, run_id, "T003", "--state", "escalated", "--reason", "asked")
    lane(pilot.root, capsys, run_id, "T005", "--state", "escalated", "--reason", "asked")
    lane(pilot.root, capsys, run_id, "T005", "--state", "parked")
    pilot.finish("T001")

    report = data(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)["runs"][0]
    found = {entry["id"]: (entry["state"], entry["holds_lane"]) for entry in report["tasks"]}
    assert found["T001"] == ("done-branch", False)
    assert found["T002"] == ("gate", True)
    assert found["T003"] == ("escalated", False)
    assert found["T005"] == ("parked", False)
    assert found["T006"] == ("dispatched", True)
    assert found["T004"] == ("pending", False)

    lane(pilot.root, capsys, run_id, "T001", "--state", "handed-off")
    lane(pilot.root, capsys, run_id, "T002", "--state", "failed", "--reason", "stuck")
    report = data(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)["runs"][0]
    found = {entry["id"]: (entry["state"], entry["holds_lane"]) for entry in report["tasks"]}
    assert found["T001"] == ("handed-off", False)
    assert found["T002"] == ("failed", False)

    code, out, _ = run(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)
    assert code == 0
    assert re.search(r"^\s+T005\s+parked\s+.*no lane", out, re.M)
    assert re.search(r"^\s+T002\s+failed\s+.*no lane", out, re.M)
    assert not re.search(r"^\s+T001\s+handed-off.*no lane", out, re.M)  # a closed lane is not parked


# --- 6. A parked task keeps its escalation flags (criterion 12) -----------------------------------


def test_a_parked_task_still_flags_an_unapproved_governing_path(pilot, capsys):
    configure(pilot, 'max_lanes = 2\ngoverning = ["docs/adr"]\nescalate_gates = ["feature:plan"]\n')
    run_id = start(pilot.root, capsys, count=6)
    worktree = pilot.lane("T001", run_id)
    (worktree / "docs" / "adr").mkdir(parents=True)
    (worktree / "docs" / "adr" / "0001.md").write_text("decided", encoding="utf-8")
    commit_all(worktree, "adr")
    lane(pilot.root, capsys, run_id, "T001", "--state", "escalated", "--reason", "governing", "--gate", "plan")

    found = row(pilot.root, capsys, run_id, "T001")
    assert (found["governing_touched"], found["escalate_gate"], found["escalation"]) == (
        ["docs/adr/0001.md"],
        "feature:plan",
        ["governing", "escalate-gate"],
    )

    lane(pilot.root, capsys, run_id, "T001", "--state", "parked", "--reason", "answered")
    found = row(pilot.root, capsys, run_id, "T001")
    assert found["governing_touched"] == ["docs/adr/0001.md"]  # `parked` reports its touched files
    assert found["escalate_gate"] is None  # the lane is no longer stopped at a gate
    assert found["escalation"] == ["governing"]


# --- 7. The design and the skill say so (criterion 13) --------------------------------------------


def test_design_and_skill_describe_the_parked_state():
    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    section = design[design.index("### 12.7 Resources") : design.index("### 12.8 ")]
    assert "`running` (a claim, stale or not), `gate` or `dispatched`" in section
    assert "`escalated`, `parked`, `failed`" in section  # among the states that use no lane
    assert r"--state running\|gate\|escalated\|parked\|failed\|handed-off" in design
    assert "holds_lane" in design

    skill = (install.SKILLS_SOURCE / "taskrail-autopilot" / "SKILL.md").read_text(encoding="utf-8")
    escalate = skill[skill.index("## Escalate") : skill.index("## Close and hand off")]
    assert "--state parked" in escalate
    assert "next --run <R>" in escalate
    assert skill.count("--state parked") == 1  # one place tells the orchestrator what to do
