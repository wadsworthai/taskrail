"""`autopilot close`: abandon a run, releasing its dispatches and resources and hiding it (T048)."""

import json
from datetime import datetime, timezone

from conftest import git
from test_autopilot_next import TODO, configure, data, dispatch, ids, pilot, run, start, stored  # noqa: F401

from taskrail import claims
from taskrail.autopilot import runs
from taskrail.cli import main
from taskrail.config import load_config

RESOURCES = '[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433", "5434"]\n'


def close(root, capsys, run_id, reason="the orchestrator session was lost"):
    return data(root, "autopilot", "close", run_id, "--reason", reason, capsys=capsys)


def preview(root, capsys):
    return dispatch(root, capsys)


def occupied(result):
    """Lanes held by a run, leaving out the ones this `next` itself just chose."""
    return sorted(lane["id"] for lane in result["lanes"]["occupied"] if lane["run"] is not None)


# 1


def test_close_records_who_when_and_why_and_keeps_every_other_key(pilot, capsys):
    run_id = start(pilot.root, capsys)
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--handle", "agent-1", capsys=capsys)
    data(pilot.root, "autopilot", "decision", "--run", run_id, "--question", "q", "--decision", "d", "--reason", "r", capsys=capsys)
    with runs.update(load_config(pilot.root), run_id) as record:
        record["future_key"] = {"kept": True}
        record["tasks"]["T003"]["future_lane_key"] = 7
    before = stored(pilot.root, run_id)

    result = close(pilot.root, capsys, run_id, reason="  rewound session  ")
    assert set(result) == {"run", "closed", "released", "claims"}
    assert result["run"] == run_id
    closed = result["closed"]
    assert closed["reason"] == "rewound session" and closed["by"] == claims.default_owner()
    assert datetime.fromisoformat(closed["at"]).tzinfo is not None

    after = stored(pilot.root, run_id)
    assert after["closed"] == closed
    assert {key: value for key, value in after.items() if key != "closed"} == {key: value for key, value in before.items() if key != "closed"}
    assert after["future_key"] == {"kept": True} and after["tasks"]["T003"]["future_lane_key"] == 7
    assert after["tasks"]["T003"]["handle"] == "agent-1" and len(after["decisions"]) == 1

    text = run(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)[1]
    assert f"closed {closed['at']} by {closed['by']} — rewound session" in text


# 2


def test_close_releases_every_dispatch_and_resource_of_the_run(pilot, capsys):
    configure(pilot, "max_lanes = 2\n" + RESOURCES)
    run_id = start(pilot.root, capsys)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001", "T002"]
    lanes = stored(pilot.root, run_id)["tasks"]

    result = close(pilot.root, capsys, run_id)
    assert result["released"] == [
        {"id": "T001", "dispatched": lanes["T001"]["dispatched"], "resources": {"PORT": "5433"}},
        {"id": "T002", "dispatched": lanes["T002"]["dispatched"], "resources": {"PORT": "5434"}},
    ]
    for lane in stored(pilot.root, run_id)["tasks"].values():
        assert lane["dispatched"] is None and lane["resources"] == {}
    assert data(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)["runs"][0]["tasks"][0]["state"] == "pending"


# 3


def test_close_keeps_and_reports_the_claims_naming_the_run(pilot, capsys):
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T003", run_id)

    result = close(pilot.root, capsys, run_id)
    held = claims.read_all(load_config(pilot.root))
    assert "T003" in held and held["T003"].run == run_id
    assert result["claims"] == [{"id": "T003", "owner": "lane", "branch": held["T003"].branch, "worktree": str(path)}]


def test_close_text_names_what_it_released_and_the_kept_claims(pilot, capsys):
    configure(pilot, "max_lanes = 2\n" + RESOURCES)
    run_id = start(pilot.root, capsys)
    path = pilot.lane("T003", run_id)
    assert ids(dispatch(pilot.root, capsys, run_id)) == ["T001"]
    dispatched = stored(pilot.root, run_id)["tasks"]["T001"]["dispatched"]

    code, out, _ = run(pilot.root, "autopilot", "close", run_id, "--reason", "gone", capsys=capsys)
    assert code == 0
    assert out.splitlines() == [
        f"closed run {run_id}: gone",
        f"  released dispatch of {dispatched} and PORT=5433 from T001",
        f"  kept claim T003 by lane in {path}; release it with `taskrail release T003`",
    ]


# 4


def test_a_closed_run_frees_its_lanes_and_resources_for_other_runs(pilot, capsys):
    configure(pilot, "max_lanes = 2\n" + RESOURCES)
    first = start(pilot.root, capsys)
    second = start(pilot.root, capsys)
    assert ids(dispatch(pilot.root, capsys, first)) == ["T001", "T002"]
    assert ids(dispatch(pilot.root, capsys, second)) == []
    assert ids(preview(pilot.root, capsys)) == []

    close(pilot.root, capsys, first)
    closed_record = stored(pilot.root, first)
    shown = preview(pilot.root, capsys)
    assert ids(shown) == ["T001", "T002"] and occupied(shown) == [] and shown["skipped"] == []

    result = dispatch(pilot.root, capsys, second)
    assert ids(result) == ["T001", "T002"]
    assert [task["resources"] for task in result["dispatch"]] == [{"PORT": "5433"}, {"PORT": "5434"}]
    assert result["released"] == [] and result["skipped"] == []
    assert stored(pilot.root, first) == closed_record  # nothing in a closed run is written


# 5


def test_claims_groups_and_gates_of_a_closed_run_hold_no_lane(pilot, capsys):
    configure(pilot, 'max_lanes = 3\n[[autopilot.group]]\nname = "db"\nlimit = 1\n')
    run_id = start(pilot.root, capsys)
    pilot.lane("T003", run_id)
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--group", "db", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T006", "--run", run_id, "--state", "gate", capsys=capsys)
    before = preview(pilot.root, capsys)
    assert occupied(before) == ["T003", "T006"]
    assert before["groups"][0]["members"] == ["T003"]

    close(pilot.root, capsys, run_id)
    after = preview(pilot.root, capsys)
    assert occupied(after) == [] and ids(after) == ["T001", "T002", "T005"]
    assert after["groups"][0]["members"] == [] and after["groups"][0]["free"] == 1


# 6


def test_status_lists_a_closed_run_only_when_named(pilot, capsys):
    first = start(pilot.root, capsys)
    second = start(pilot.root, capsys)
    for task_id, run_id in (("T001", first), ("T003", second)):
        (pilot.lane(task_id, run_id) / "shared.txt").write_text(task_id, encoding="utf-8")
    report = data(pilot.root, "autopilot", "status", capsys=capsys)
    assert [r["id"] for r in report["runs"]] == [second, first]
    assert report["overlaps"] == {"shared.txt": ["T001", "T003"]}
    assert all(r["closed"] is None for r in report["runs"])

    closed = close(pilot.root, capsys, first)["closed"]
    report = data(pilot.root, "autopilot", "status", capsys=capsys)
    assert [r["id"] for r in report["runs"]] == [second] and report["overlaps"] == {}
    named = data(pilot.root, "autopilot", "status", "--run", first, capsys=capsys)
    assert [r["id"] for r in named["runs"]] == [first] and named["runs"][0]["closed"] == closed
    assert f"run {first}" not in run(pilot.root, "autopilot", "status", capsys=capsys)[1]


# 7


def test_a_closed_run_refuses_new_work_and_writes_nothing(pilot, capsys, tmp_path):
    run_id = start(pilot.root, capsys)
    data(pilot.root, "autopilot", "lane", "T003", "--run", run_id, "--handle", "agent-1", capsys=capsys)
    close(pilot.root, capsys, run_id)
    before = stored(pilot.root, run_id)

    for argv in (
        ["autopilot", "next", "--run", run_id],
        ["autopilot", "lane", "T002", "--run", run_id, "--handle", "agent-2"],
        ["autopilot", "lane", "T003", "--run", run_id, "--state", "failed", "--reason", "x"],
        ["autopilot", "decision", "--run", run_id, "--question", "q", "--decision", "d", "--reason", "r"],
    ):
        code, _, err = run(pilot.root, *argv, capsys=capsys)
        assert code == 5 and f"run `{run_id}` is closed" in err, argv

    shown = json.loads(run(pilot.root, "show", "T002", "--json", capsys=capsys)[1])
    path = tmp_path / "lane-T002"
    git(pilot.root, "worktree", "add", "-q", str(path), "-b", shown["branch"], "origin/main")
    code, _, err = run(path, "claim", "T002", "--owner", "lane", "--run", run_id, capsys=capsys)
    assert code == 5 and f"run `{run_id}` is closed" in err
    assert "T002" not in claims.read_all(load_config(pilot.root))
    assert stored(pilot.root, run_id) == before


# 8


def test_close_exit_codes(pilot, capsys):
    run_id = start(pilot.root, capsys)
    assert run(pilot.root, "autopilot", "close", "20000101-1", "--reason", "x", capsys=capsys)[0] == 3
    assert run(pilot.root, "autopilot", "close", "../claims/x", "--reason", "x", capsys=capsys)[0] == 3
    for reason in ("", "   "):
        code, _, err = run(pilot.root, "autopilot", "close", run_id, "--reason", reason, capsys=capsys)
        assert code == 2 and "--reason" in err
    assert stored(pilot.root, run_id)["closed"] is None

    first = close(pilot.root, capsys, run_id, reason="first")["closed"]
    code, _, err = run(pilot.root, "autopilot", "close", run_id, "--reason", "second", capsys=capsys)
    assert code == 5 and "already closed" in err
    assert stored(pilot.root, run_id)["closed"] == first


# 9


def test_close_works_while_disabled_and_with_an_invalid_backlog(pilot, capsys):
    run_id = start(pilot.root, capsys)
    configure(pilot, enabled=False)
    pilot.write("TODO.md", TODO.replace("| T004 | feature |", "| T004 | nope    |"))
    assert close(pilot.root, capsys, run_id)["closed"]["reason"]
    assert runs.is_closed(stored(pilot.root, run_id))


# 10


def test_a_merge_recorded_in_a_closed_run_still_counts(pilot, capsys):
    first = start(pilot.root, capsys)
    second = start(pilot.root, capsys)
    data(pilot.root, "autopilot", "lane", "T003", "--run", first, "--handle", "a", capsys=capsys)
    data(pilot.root, "autopilot", "lane", "T003", "--run", second, "--handle", "b", capsys=capsys)
    commit = git(pilot.root, "rev-parse", "main")
    with runs.update(load_config(pilot.root), first) as record:
        record["tasks"]["T003"]["merged"] = {
            "via": "tree",
            "commit": commit,
            "head": commit,
            "mainline": "main",
            "detected": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    close(pilot.root, capsys, first)
    report = data(pilot.root, "autopilot", "status", "--run", second, capsys=capsys)
    assert report["runs"][0]["tasks"][0]["state"] == "done-merged"
    assert main(["--root", str(pilot.root), "autopilot", "status", "--json"]) == 0
