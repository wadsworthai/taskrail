"""`taskrail checks <ID>`: a task's configured checks in its worktree, with its lane's resources (T052).

Checks here are short POSIX shell commands; nothing leaves the machine.
"""

import json

from conftest import BASE_CONFIG, git
from test_autopilot import ENABLED, commit_all, data, pilot, run, start  # noqa: F401

from taskrail.cli import main

CHECKS = """[checks]
test = "echo test-ran; pwd"
lint = "echo lint-ran 1>&2"
smoke = "echo smoke-ran"
broken = "echo broken-ran; exit 3"
"""

# A local `feature` kind with checks in two stages, one of them repeated and one not configured.
FEATURE_KIND = """
name = "feature"
summary = "A feature."
skill = "taskrail-feature"
branch = "{id}-{slug}"
artifact = "{artifacts}/features/{id}-{slug}.md"
artifact_index = "{artifacts}/features/README.md"

[[stage]]
name = "plan"
gate = "always"

[[stage]]
name = "implement"
gate = "always"
checks = ["test", "lint"]

[[stage]]
name = "verify"
gate = "conditional"
checks = ["smoke", "test", "missing"]
"""


def config_with(checks: str = CHECKS, extra: str = "") -> str:
    head, _ = BASE_CONFIG.split("[checks]")
    return head + checks + ENABLED + extra


def publish(pilot, checks: str = CHECKS, extra: str = "", kind: str | None = FEATURE_KIND) -> None:
    """Commit the configuration on main and push it, so lane worktrees branch from it."""
    pilot.write(".taskrail/config.toml", config_with(checks, extra))
    if kind is not None:
        pilot.write(".taskrail/types/feature/kind.toml", kind)
    commit_all(pilot.root, "checks")
    git(pilot.root, "push", "-q", "origin", "main")


def checks(root, capsys, *argv):
    code, out, err = run(root, "checks", *argv, "--json", capsys=capsys)
    return code, (json.loads(out) if out.strip() else None), err


def by_name(result) -> dict:
    return {check["name"]: check for check in result["checks"]}


# 1


def test_runs_every_stage_check_in_the_worktree_from_the_main_checkout(pilot, capsys):
    publish(pilot, CHECKS.replace('broken = "echo broken-ran; exit 3"\n', ""))
    worktree = pilot.lane("T001")

    code, result, err = checks(pilot.root, capsys, "T001")

    assert code == 0, err
    assert [c["name"] for c in result["checks"]] == ["test", "lint", "smoke", "missing"]
    found = by_name(result)
    assert found["test"]["status"] == "passed" and found["test"]["exit"] == 0
    assert found["test"]["command"] == "echo test-ran; pwd"
    assert found["test"]["output"].splitlines() == ["test-ran", str(worktree.resolve())]
    assert found["lint"]["output"].strip() == "lint-ran"  # stderr is captured too
    assert found["smoke"]["status"] == "passed"
    assert found["missing"] == {"name": "missing", "command": None, "status": "not-configured", "exit": None, "output": None}
    assert result["passed"] is True
    assert result["id"] == "T001" and result["worktree"] == str(worktree.resolve())
    assert (result["run"], result["resources"], result["environment"], result["stage"]) == (None, {}, {}, None)


# 2


def test_a_failing_check_exits_6_and_the_later_checks_still_run(pilot, capsys):
    kind = FEATURE_KIND.replace('checks = ["test", "lint"]', 'checks = ["broken", "lint"]')
    publish(pilot, kind=kind)
    pilot.lane("T001")

    code, result, _ = checks(pilot.root, capsys, "T001")

    assert code == 6
    assert result["passed"] is False
    found = by_name(result)
    assert (found["broken"]["status"], found["broken"]["exit"], found["broken"]["output"].strip()) == ("failed", 3, "broken-ran")
    assert found["lint"]["status"] == "passed" and found["smoke"]["status"] == "passed"


# 3


def test_stage_and_check_narrow_the_selection(pilot, capsys):
    publish(pilot)
    pilot.lane("T001")

    code, result, _ = checks(pilot.root, capsys, "T001", "--stage", "implement")
    assert code == 0 and result["stage"] == "implement"
    assert [c["name"] for c in result["checks"]] == ["test", "lint"]

    code, result, _ = checks(pilot.root, capsys, "T001", "--check", "smoke", "--check", "test")
    assert code == 0
    assert [c["name"] for c in result["checks"]] == ["test", "smoke"]  # in stage order

    code, result, _ = checks(pilot.root, capsys, "T001", "--stage", "plan")
    assert code == 0 and result["checks"] == [] and result["passed"] is True

    code, result, err = checks(pilot.root, capsys, "T001", "--stage", "nope")
    assert code == 2 and result is None and "plan, implement, verify" in err

    code, result, err = checks(pilot.root, capsys, "T001", "--stage", "implement", "--check", "smoke")
    assert code == 2 and result is None and "smoke" in err


# 4


def test_the_lane_resources_reach_the_checks_before_and_after_done(pilot, capsys):
    port = 'test = "echo port=$TASKRAIL_RESOURCE_PORT"\nlint = "true"\n'
    publish(pilot, "[checks]\n" + port, 'max_lanes = 1\n[[autopilot.resource]]\nname = "PORT"\nvalues = ["5433"]\n', kind=None)
    run_id = start(pilot.root, capsys)
    dispatched = data(pilot.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert [t["id"] for t in dispatched["dispatch"]] == ["T004"]
    worktree = pilot.lane("T004", run_id)

    code, result, err = checks(pilot.root, capsys, "T004")
    assert code == 0, err
    assert (result["run"], result["resources"], result["environment"]) == (run_id, {"PORT": "5433"}, {"TASKRAIL_RESOURCE_PORT": "5433"})
    assert by_name(result)["test"]["output"].strip() == "port=5433"

    pilot.finish(worktree, "T004")  # `done` releases the claim; the run still lists the lane
    code, result, err = checks(pilot.root, capsys, "T004")
    assert code == 0, err
    assert result["run"] == run_id and by_name(result)["test"]["output"].strip() == "port=5433"
    assert result["worktree"] == str(worktree.resolve())


# 5


def test_the_worktree_configuration_decides_the_commands(pilot, capsys):
    publish(pilot)
    worktree = pilot.lane("T001")
    (worktree / ".taskrail/config.toml").write_text(config_with(CHECKS.replace("echo smoke-ran", "echo smoke-from-branch")), encoding="utf-8")

    code, result, _ = checks(pilot.root, capsys, "T001", "--check", "smoke")

    assert code == 0
    assert by_name(result)["smoke"]["command"] == "echo smoke-from-branch"
    assert by_name(result)["smoke"]["output"].strip() == "smoke-from-branch"


# 6


def test_no_worktree_exits_5_and_an_unknown_task_exits_3(pilot, capsys):
    publish(pilot, '[checks]\ntest = "touch ran-anyway"\n', kind=None)

    code, result, err = checks(pilot.root, capsys, "T003")
    assert code == 5 and result is None
    assert "T003" in err and "T003-independent" in err
    assert not (pilot.root / "ran-anyway").exists()

    code, _, err = checks(pilot.root, capsys, "T999")
    assert code == 3 and "T999" in err


# 7


def test_text_mode_streams_each_check_and_summarises(pilot, capfd):
    publish(pilot)
    worktree = pilot.lane("T001")
    capfd.readouterr()

    code = main(["--root", str(pilot.root), "checks", "T001", "--stage", "verify"])
    out, err = capfd.readouterr()

    assert code == 0
    text = out + err
    assert "smoke: echo smoke-ran" in text and "smoke-ran" in text and "test-ran" in text
    assert "missing: not configured" in text
    assert "passed smoke" in text and "passed test" in text

    kind = FEATURE_KIND.replace('checks = ["smoke", "test", "missing"]', 'checks = ["broken"]')
    (worktree / ".taskrail/types/feature/kind.toml").write_text(kind, encoding="utf-8")  # the worktree's kind decides
    capfd.readouterr()
    code = main(["--root", str(pilot.root), "checks", "T001", "--stage", "verify"])
    out, err = capfd.readouterr()
    assert code == 6 and "failed broken (exit 3)" in out + err
