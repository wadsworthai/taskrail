"""The `decisions` gate: a stop for each decision instead of each stage (T082, DESIGN.md §5.6, §12.6)."""

import json

from test_autopilot import ENABLED, TODO, commit_all, configure, data, pilot, row, run, start, status_of  # noqa: F401

from conftest import git
from taskrail.config import load_config
from taskrail.kinds import CORE_DIR, load_kinds

LOCAL_KIND = """
name = "research"
summary = "A local kind that stops only for decisions."
skill = "research"

[[stage]]
name = "scope"
gate = "decisions"
commit = true

[[stage]]
name = "write-up"
gate = "always"
"""


def decisions_override(kind: str, stage: str) -> str:
    """The core descriptor of `kind` with `stage`'s gate turned into `decisions`."""
    text = (CORE_DIR / kind / "kind.toml").read_text(encoding="utf-8")
    head, marker, tail = text.partition(f'name = "{stage}"')
    assert marker, f"core kind {kind} has no stage {stage}"
    before, gate, after = tail.partition('gate = "always"')
    assert gate, f"stage {stage} of {kind} is not an always gate"
    return head + marker + before + 'gate = "decisions"' + after


def cli(root, capsys, *argv):
    from taskrail.cli import main

    capsys.readouterr()
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


# 1. A local kind loads a decisions gate.


def test_local_kind_loads_a_decisions_gate(repo):
    repo.write(".taskrail/types/research/kind.toml", LOCAL_KIND)
    project, issues = repo.load()
    assert issues == []
    assert [(s.name, s.gate) for s in project.kinds["research"].stages] == [("scope", "decisions"), ("write-up", "always")]


# 2. An override of a core kind loads one, and validate passes.


def test_override_of_a_core_kind_loads_a_decisions_gate(repo, capsys):
    repo.write(".taskrail/overrides/feature/kind.toml", decisions_override("feature", "plan"))
    kinds, issues = load_kinds(load_config(repo.root))
    assert issues == []
    assert kinds["feature"].source == "override"
    assert {s.name: s.gate for s in kinds["feature"].stages} == {"plan": "decisions", "implement": "always", "verify": "conditional"}
    code, out, err = cli(repo.root, capsys, "validate")
    assert code == 0, out + err


# 3. Any other gate is still kind-invalid, and the message names all four values.


def test_an_unknown_gate_names_the_four_values(repo, capsys):
    repo.write(".taskrail/types/research/kind.toml", LOCAL_KIND.replace('"decisions"', '"decision"'))
    messages = [i.message for i in repo.load()[1] if i.code == "kind-invalid"]
    assert messages == ["stage `scope`: gate must be one of always, conditional, decisions, none"]
    code, _, _ = cli(repo.root, capsys, "validate")
    assert code == 1


# 4. show reports the gate, in JSON and text.


def test_show_reports_a_decisions_gate(repo, capsys):
    repo.write(".taskrail/overrides/feature/kind.toml", decisions_override("feature", "plan"))
    code, out, err = cli(repo.root, capsys, "show", "T002", "--json")
    assert code == 0, err
    stages = json.loads(out)["kind_descriptor"]["stages"]
    assert [(s["name"], s["gate"]) for s in stages] == [("plan", "decisions"), ("implement", "always"), ("verify", "conditional")]
    code, out, err = cli(repo.root, capsys, "show", "T002")
    assert code == 0, err
    assert "  · plan (gate: decisions, commit)\n" in out


# 5. kind list reports it.


def test_kind_list_reports_a_decisions_gate(repo, capsys):
    repo.write(".taskrail/types/research/kind.toml", LOCAL_KIND)
    code, out, err = cli(repo.root, capsys, "kind", "list", "--json")
    assert code == 0, err
    research = next(k for k in json.loads(out) if k["name"] == "research")
    assert [(s["name"], s["gate"]) for s in research["stages"]] == [("scope", "decisions"), ("write-up", "always")]


# 6–8. The autopilot records, flags and dispatches decisions gates like any gate.


def spike_pilot(pilot, extra=""):
    """Make T004 a spike whose decide stage is a decisions gate, committed and pushed."""
    configure(pilot, ENABLED + extra)
    pilot.write("TODO.md", TODO.replace("| T004 | chore   |", "| T004 | spike   |"))
    pilot.write(".taskrail/overrides/spike/kind.toml", decisions_override("spike", "decide"))
    pilot.write(".taskrail/overrides/feature/kind.toml", decisions_override("feature", "plan"))
    commit_all(pilot.root, "decisions gates")
    git(pilot.root, "push", "-q", "origin", "main")


def test_lane_records_a_decisions_gate_and_status_reports_it(pilot, capsys):
    spike_pilot(pilot)
    run_id = start(pilot.root, capsys)
    pilot.lane("T001", run_id)
    result = data(pilot.root, "autopilot", "lane", "T001", "--run", run_id, "--state", "gate", "--gate", "plan", capsys=capsys)
    assert result["task"]["gate"] == "plan"
    found = row(status_of(pilot.root, capsys, run_id), "T001")
    assert (found["state"], found["gate"], found["escalate_gate"], found["escalation"]) == ("gate", "plan", None, [])


def test_escalate_gates_flags_a_decisions_gate(pilot, capsys):
    spike_pilot(pilot, 'escalate_gates = ["spike:decide"]\n')
    run_id = data(pilot.root, "autopilot", "start", "--count", "1", "--tasks", "T004", capsys=capsys)["run"]["id"]
    pilot.lane("T004", run_id)
    data(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--state", "gate", "--gate", "decide", capsys=capsys)
    found = row(status_of(pilot.root, capsys, run_id), "T004")
    assert (found["gate"], found["escalate_gate"], found["escalation"]) == ("decide", "spike:decide", ["escalate-gate"])
    data(pilot.root, "autopilot", "lane", "T004", "--run", run_id, "--state", "escalated", "--reason", "asked", capsys=capsys)
    found = row(status_of(pilot.root, capsys, run_id), "T004")
    assert (found["state"], found["escalate_gate"]) == ("escalated", "spike:decide")


def test_start_and_next_accept_kinds_with_decisions_gates(pilot, capsys):
    spike_pilot(pilot, 'kinds = ["feature", "spike"]\n')
    code, out, err = run(pilot.root, "autopilot", "next", "--json", capsys=capsys)
    assert code == 0, err
    code, out, err = run(pilot.root, "autopilot", "start", "--count", "2", "--json", capsys=capsys)
    assert code == 0, err
    run_id = json.loads(out)["run"]["id"]
    code, out, err = run(pilot.root, "autopilot", "next", "--run", run_id, "--json", capsys=capsys)
    assert code == 0, err
    assert {entry["id"] for entry in json.loads(out)["dispatch"]} <= {"T001", "T004"}
