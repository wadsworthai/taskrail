"""`autopilot approve-governing` and the approved governing files in `autopilot status` (T059)."""

import json

import pytest
from conftest import git
from test_autopilot import ENABLED, commit_all, configure, data, pilot, row, run, start, status_of  # noqa: F401

from taskrail.autopilot import runs
from taskrail.config import AutopilotConfig, load_config

GOVERNING = ENABLED + 'governing = ["docs/adr"]\nescalate_gates = ["bug:fix"]\n'


def write(lane, path, text):
    (lane / path).parent.mkdir(parents=True, exist_ok=True)
    (lane / path).write_text(text)


def blob(lane, path):
    return git(lane, "hash-object", "--", path)


def approve(pilot, capsys, run_id, *argv, task="T003"):
    return data(pilot.root, "autopilot", "approve-governing", task, "--run", run_id, *argv, capsys=capsys)


def stored(pilot, run_id, task="T003"):
    return runs.read(load_config(pilot.root), run_id)["tasks"][task].get("governing_approved")


def flags(pilot, capsys, run_id, task="T003"):
    found = row(status_of(pilot.root, capsys, run_id), task)
    return found["governing_touched"], found["governing_approved"], found["escalation"]


def text_line(pilot, capsys, task="T003"):
    code, out, _ = run(pilot.root, "autopilot", "status", capsys=capsys)
    assert code == 0
    return next(line for line in out.splitlines() if line.startswith(f"  {task}"))


@pytest.fixture
def governed(pilot, capsys):
    """A bug lane in a run with a committed and an uncommitted governing file, and a file outside."""
    configure(pilot, GOVERNING)
    run_id = start(pilot.root, capsys)
    lane = pilot.lane("T003", run_id)
    write(lane, "docs/adr/0001.md", "one")
    write(lane, "notes.md", "not governing")
    commit_all(lane, "adr")
    write(lane, "docs/adr/0002.md", "two, uncommitted")
    return run_id, lane


# 1


def test_approve_records_every_governing_path_with_its_blob(pilot, capsys, governed):
    run_id, lane = governed
    expected = {"docs/adr/0001.md": blob(lane, "docs/adr/0001.md"), "docs/adr/0002.md": blob(lane, "docs/adr/0002.md")}
    result = approve(pilot, capsys, run_id)
    assert result["approved"] == expected
    assert result["governing_approved"] == expected
    assert (result["run"], result["task"]) == (run_id, "T003")
    assert stored(pilot, run_id) == expected


# 2


def test_status_drops_the_governing_reason_for_approved_files_before_done_branch(pilot, capsys, governed):
    run_id, _ = governed
    touched = ["docs/adr/0001.md", "docs/adr/0002.md"]
    assert flags(pilot, capsys, run_id) == (touched, [], ["governing"])
    approve(pilot, capsys, run_id)

    def lane(*argv):
        data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, *argv, capsys=capsys)

    assert flags(pilot, capsys, run_id) == (touched, touched, [])
    assert "ESCALATE" not in text_line(pilot, capsys)
    lane("--state", "gate", "--gate", "fix")
    assert flags(pilot, capsys, run_id) == (touched, touched, ["escalate-gate"])
    assert text_line(pilot, capsys).endswith("ESCALATE: gate bug:fix")
    lane("--state", "escalated", "--reason", "asked")
    assert flags(pilot, capsys, run_id) == (touched, touched, ["escalate-gate"])
    lane("--state", "failed", "--reason", "stuck")
    assert flags(pilot, capsys, run_id) == (touched, touched, [])


# 3


@pytest.mark.parametrize("change", ["commit", "uncommitted", "delete"])
def test_a_change_to_an_approved_file_flags_it_again(pilot, capsys, governed, change):
    run_id, lane = governed
    commit_all(lane, "second adr")
    approve(pilot, capsys, run_id)
    if change == "delete":
        (lane / "docs/adr/0001.md").unlink()
    else:
        write(lane, "docs/adr/0001.md", "one, changed")
        if change == "commit":
            commit_all(lane, "change adr")
    touched, approved, escalation = flags(pilot, capsys, run_id)
    assert "docs/adr/0001.md" in touched
    assert approved == ["docs/adr/0002.md"]
    assert escalation == ["governing"]
    assert text_line(pilot, capsys).endswith("ESCALATE: governing docs/adr/0001.md")


def test_a_recreated_deleted_file_flags_again(pilot, capsys, governed):
    run_id, lane = governed
    (lane / "docs/adr/0002.md").unlink()
    git(lane, "rm", "-q", "docs/adr/0001.md")
    commit_all(lane, "drop adr")
    assert flags(pilot, capsys, run_id)[0] == []  # a file created and deleted on the branch is no change
    write(lane, "docs/adr/0003.md", "three")
    commit_all(lane, "adr three")
    (lane / "docs/adr/0003.md").unlink()
    result = approve(pilot, capsys, run_id)
    assert result["approved"] == {"docs/adr/0003.md": None}  # an approved deletion
    assert flags(pilot, capsys, run_id) == (["docs/adr/0003.md"], ["docs/adr/0003.md"], [])
    write(lane, "docs/adr/0003.md", "back")
    assert flags(pilot, capsys, run_id) == (["docs/adr/0003.md"], [], ["governing"])


# 4


def test_a_governing_path_touched_after_the_approval_is_named_alone(pilot, capsys, governed):
    run_id, lane = governed
    approve(pilot, capsys, run_id)
    write(lane, "docs/adr/0004.md", "new")
    touched, approved, escalation = flags(pilot, capsys, run_id)
    assert touched == ["docs/adr/0001.md", "docs/adr/0002.md", "docs/adr/0004.md"]
    assert approved == ["docs/adr/0001.md", "docs/adr/0002.md"]
    assert escalation == ["governing"]
    assert text_line(pilot, capsys).endswith("ESCALATE: governing docs/adr/0004.md")


# 5


def test_path_approves_only_the_named_files(pilot, capsys, governed):
    run_id, lane = governed
    result = approve(pilot, capsys, run_id, "--path", "docs/adr/0002.md")
    assert result["approved"] == {"docs/adr/0002.md": blob(lane, "docs/adr/0002.md")}
    assert flags(pilot, capsys, run_id) == (["docs/adr/0001.md", "docs/adr/0002.md"], ["docs/adr/0002.md"], ["governing"])
    assert text_line(pilot, capsys).endswith("ESCALATE: governing docs/adr/0001.md")


@pytest.mark.parametrize("path", ["notes.md", "docs/adr/0009.md"])
def test_a_path_outside_governing_touched_is_refused(pilot, capsys, governed, path):
    run_id, _ = governed
    before = stored(pilot, run_id)
    code, _, err = run(pilot.root, "autopilot", "approve-governing", "T003", "--run", run_id, "--path", "docs/adr/0001.md", "--path", path, capsys=capsys)
    assert code == 2
    assert path in err and "docs/adr/0001.md, docs/adr/0002.md" in err
    assert stored(pilot, run_id) == before


# 6


def test_approving_again_records_the_new_blob(pilot, capsys, governed):
    run_id, lane = governed
    approve(pilot, capsys, run_id, "--path", "docs/adr/0001.md")
    approve(pilot, capsys, run_id, "--path", "docs/adr/0002.md")
    write(lane, "docs/adr/0001.md", "one, changed")
    assert flags(pilot, capsys, run_id)[2] == ["governing"]
    result = approve(pilot, capsys, run_id, "--path", "docs/adr/0001.md")
    changed = blob(lane, "docs/adr/0001.md")
    assert result["approved"] == {"docs/adr/0001.md": changed}
    assert result["governing_approved"] == {"docs/adr/0001.md": changed, "docs/adr/0002.md": blob(lane, "docs/adr/0002.md")}
    assert flags(pilot, capsys, run_id)[1:] == (["docs/adr/0001.md", "docs/adr/0002.md"], [])


# 7


def test_an_approval_holds_without_the_worktree_and_at_done_branch(pilot, capsys, governed):
    run_id, lane = governed
    commit_all(lane, "second adr")
    approve(pilot, capsys, run_id)
    touched = ["docs/adr/0001.md", "docs/adr/0002.md"]
    pilot.finish(lane, "T003")
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert (found["state"], found["governing_touched"], found["governing_approved"], found["escalation"]) == ("done-branch", touched, touched, [])
    git(pilot.root, "worktree", "remove", str(lane))
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert (found["worktree"], found["governing_touched"], found["governing_approved"]) == (None, touched, touched)


def test_an_approval_from_the_branch_tip_matches_the_worktree_file(pilot, capsys, governed):
    run_id, lane = governed
    commit_all(lane, "second adr")
    git(pilot.root, "worktree", "remove", str(lane))  # the claim still names the removed worktree
    result = approve(pilot, capsys, run_id)
    assert set(result["approved"]) == {"docs/adr/0001.md", "docs/adr/0002.md"}
    git(pilot.root, "worktree", "add", "-q", str(lane), "T003-independent")
    assert flags(pilot, capsys, run_id)[1:] == (["docs/adr/0001.md", "docs/adr/0002.md"], [])


# 8


def test_unknown_run_task_or_member_exits_3_and_nothing_to_approve_exits_5(pilot, capsys, governed):
    run_id, _ = governed
    path = runs.runs_dir(load_config(pilot.root)) / f"{run_id}.json"
    before = path.read_text()
    assert run(pilot.root, "autopilot", "approve-governing", "T003", "--run", "20000101-9", capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "approve-governing", "T999", "--run", run_id, capsys=capsys)[0] == 3
    code, _, err = run(pilot.root, "autopilot", "approve-governing", "T004", "--run", run_id, capsys=capsys)
    assert code == 3 and "T004" in err
    pilot.lane("T001", run_id)
    code, _, err = run(pilot.root, "autopilot", "approve-governing", "T001", "--run", run_id, capsys=capsys)
    assert code == 5 and "governing" in err
    after = json.loads(path.read_text())
    assert "governing_approved" not in after["tasks"]["T001"]
    assert json.loads(before)["tasks"]["T003"] == after["tasks"]["T003"]


def test_approve_text_names_the_files(pilot, capsys, governed):
    run_id, lane = governed
    code, out, _ = run(pilot.root, "autopilot", "approve-governing", "T003", "--run", run_id, capsys=capsys)
    assert code == 0
    assert f"T003 in run {run_id}: approved docs/adr/0001.md ({blob(lane, 'docs/adr/0001.md')[:12]})" in out
    assert "docs/adr/0002.md" in out


# 9


@pytest.mark.parametrize("state", ["running", "gate", "escalated", "failed"])
def test_flags_drop_governing_only_when_every_governing_file_is_approved(state):
    from taskrail.autopilot import escalation

    config = AutopilotConfig(governing=("docs/adr",))
    touched = ["TODO.md", "docs/adr/0001.md", "docs/adr/0002.md"]
    found = escalation.flags("bug", state, None, touched, config, approved=["docs/adr/0001.md"])
    assert (found["governing_touched"], found["governing_approved"], found["escalation"]) == (touched[1:], ["docs/adr/0001.md"], ["governing"])
    found = escalation.flags("bug", state, None, touched, config, approved=["docs/adr/0001.md", "docs/adr/0002.md", "TODO.md"])
    assert (found["governing_approved"], found["escalation"]) == (touched[1:], [])
    assert escalation.flags("bug", state, None, touched, config)["governing_approved"] == []
