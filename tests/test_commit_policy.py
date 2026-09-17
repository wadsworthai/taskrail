"""The commit policy: `[git].commit` and a kind's top-level `commit` (DESIGN.md §4, §5.1; T081)."""

import json

import pytest
from conftest import BASE_CONFIG
from test_autopilot_next import CONFIG, run
from test_autopilot_next import pilot  # noqa: F401  (the fixture)

from taskrail.cli import main
from taskrail.config import load_config
from taskrail.issues import ConfigError
from taskrail.kinds import load_kinds

ON_DONE_LINE = "commit everything {id} changed now, the status change included"


def set_git(repo, git_table: str, base: str = BASE_CONFIG, tail: str = "") -> None:
    repo.write(".taskrail/config.toml", base + "\n[git]\n" + git_table + "\n" + tail)


def override(repo, kind: str, policy: str | None, stage_commit: bool = True) -> None:
    top = f"commit = {policy}\n" if policy is not None else ""
    repo.write(
        f".taskrail/overrides/{kind}/kind.toml",
        f'name = "{kind}"\nsummary = "Local {kind} flow."\nskill = "taskrail-{kind}"\n{top}'
        f'[[stage]]\nname = "work"\ngate = "always"\ncommit = {"true" if stage_commit else "false"}\n',
    )


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


# Criterion 1


@pytest.mark.parametrize("value", ['"stages"', '"on-done"'])
def test_config_commit_accepts_both_policies(repo, value):
    set_git(repo, f"commit = {value}")
    assert load_config(repo.root).commit == value.strip('"')


def test_config_commit_is_unset_by_default(repo):
    assert load_config(repo.root).commit is None


@pytest.mark.parametrize("value", ['"sometimes"', "true", '"on_done"'])
def test_config_commit_rejects_other_values(repo, value, capsys):
    set_git(repo, f"commit = {value}")
    with pytest.raises(ConfigError, match="git.commit"):
        load_config(repo.root)
    code, _, err = run(repo.root, "validate", capsys=capsys)
    assert code == 2
    assert "git.commit" in err


# Criterion 2


@pytest.mark.parametrize("value", ['"stages"', '"on-done"'])
def test_kind_commit_accepts_both_policies(repo, value):
    override(repo, "bug", value)
    kinds, issues = load_kinds(load_config(repo.root))
    assert issues == []
    assert kinds["bug"].commit == value.strip('"')
    assert kinds["bug"].commit_source == "kind"


@pytest.mark.parametrize("value", ["true", '"sometimes"'])
def test_kind_commit_rejects_other_values(repo, value, capsys):
    override(repo, "bug", value)
    invalid = [i for i in repo.load()[1] if i.code == "kind-invalid"]
    assert len(invalid) == 1
    assert invalid[0].file == ".taskrail/overrides/bug/kind.toml"
    assert "commit" in invalid[0].message
    assert run(repo.root, "validate", capsys=capsys)[0] == 1


# Criterion 3


def test_show_reports_the_default_policy(git_repo, capsys):
    shown = data(git_repo.root, "show", "T002", capsys=capsys)
    descriptor = shown["kind_descriptor"]
    assert (descriptor["commit"], descriptor["commit_source"]) == ("stages", "default")
    assert [stage["commit"] for stage in descriptor["stages"]] == [True, True, False]
    assert shown["close"] == {"commit": "stages"}
    code, out, _ = run(git_repo.root, "show", "T002", capsys=capsys)
    assert "commit on-done" not in out
    assert "(gate: always, commit)" in out


# Criterion 4


def test_config_on_done_turns_every_stage_commit_off_in_show_and_kind_list(git_repo, capsys):
    set_git(git_repo, 'commit = "on-done"')
    shown = data(git_repo.root, "show", "T002", capsys=capsys)
    descriptor = shown["kind_descriptor"]
    assert (descriptor["commit"], descriptor["commit_source"]) == ("on-done", "config")
    assert [stage["commit"] for stage in descriptor["stages"]] == [False, False, False]
    assert shown["close"] == {"commit": "on-done"}

    listed = data(git_repo.root, "kind", "list", capsys=capsys)
    assert {k["name"]: (k["commit"], k["commit_source"]) for k in listed} == {
        name: ("on-done", "config") for name in ("bug", "chore", "feature", "spike")
    }
    assert all(stage["commit"] is False for k in listed for stage in k["stages"])

    code, out, _ = run(git_repo.root, "show", "T002", capsys=capsys)
    assert code == 0
    assert ", commit)" not in out
    assert "  commit on-done ([git].commit)" in out.splitlines()


def test_config_stages_keeps_the_declared_booleans(git_repo, capsys):
    set_git(git_repo, 'commit = "stages"')
    descriptor = data(git_repo.root, "show", "T002", capsys=capsys)["kind_descriptor"]
    assert (descriptor["commit"], descriptor["commit_source"]) == ("stages", "config")
    assert [stage["commit"] for stage in descriptor["stages"]] == [True, True, False]


# Criterion 5


def test_kind_stages_wins_over_config_on_done(git_repo, capsys):
    set_git(git_repo, 'commit = "on-done"')
    override(git_repo, "feature", '"stages"')
    shown = data(git_repo.root, "show", "T002", capsys=capsys)
    descriptor = shown["kind_descriptor"]
    assert (descriptor["commit"], descriptor["commit_source"]) == ("stages", "kind")
    assert [stage["commit"] for stage in descriptor["stages"]] == [True]
    assert shown["close"] == {"commit": "stages"}
    bug = next(k for k in data(git_repo.root, "kind", "list", capsys=capsys) if k["name"] == "bug")
    assert (bug["commit"], bug["commit_source"]) == ("on-done", "config")


def test_kind_on_done_without_config(git_repo, capsys):
    override(git_repo, "feature", '"on-done"')
    shown = data(git_repo.root, "show", "T002", capsys=capsys)
    descriptor = shown["kind_descriptor"]
    assert (descriptor["commit"], descriptor["commit_source"]) == ("on-done", "kind")
    assert [stage["commit"] for stage in descriptor["stages"]] == [False]
    assert shown["close"] == {"commit": "on-done"}
    listed = {k["name"]: (k["commit"], k["commit_source"]) for k in data(git_repo.root, "kind", "list", capsys=capsys)}
    assert listed["feature"] == ("on-done", "kind")
    assert listed["bug"] == ("stages", "default")
    out = run(git_repo.root, "show", "T002", capsys=capsys)[1]
    assert "  commit on-done (.taskrail/overrides/feature/kind.toml)" in out.splitlines()


# Criterion 6


def test_on_done_kind_with_committing_stages_is_not_an_issue(repo):
    override(repo, "feature", '"on-done"', stage_commit=True)
    assert repo.codes("error") == []
    assert repo.codes("warning") == []


# Criterion 7


@pytest.mark.parametrize("command", ["done", "discard"])
def test_done_and_discard_report_the_policy(git_repo, capsys, command):
    set_git(git_repo, 'commit = "on-done"')
    assert main(["--root", str(git_repo.root), "claim", "T002"]) == 0
    result = data(git_repo.root, command, "T002", "--force", capsys=capsys)
    assert result["commit"] == "on-done"


@pytest.mark.parametrize("command", ["done", "discard"])
def test_done_and_discard_text_under_on_done(git_repo, capsys, command):
    override(git_repo, "feature", '"on-done"')
    code, out, err = run(git_repo.root, command, "T002", "--force", capsys=capsys)
    assert code == 0, err
    assert ON_DONE_LINE.format(id="T002") in out


@pytest.mark.parametrize("command", ["done", "discard"])
def test_done_and_discard_under_stages(git_repo, capsys, command):
    result = data(git_repo.root, command, "T002", "--force", capsys=capsys)
    assert result["commit"] == "stages"
    set_git(git_repo, 'commit = "stages"')
    code, out, _ = run(git_repo.root, command, "T003", "--force", capsys=capsys)
    assert code == 0
    assert "commit everything" not in out


# Criteria 8 and 9


def pilot_config(repo, git_table: str = "", autopilot: str = "max_lanes = 10\n", enabled: bool = True) -> None:
    head = f"\n[autopilot]\nenabled = {'true' if enabled else 'false'}\n" + autopilot
    repo.write(".taskrail/config.toml", CONFIG + ("\n[git]\n" + git_table + "\n" if git_table else "") + head)


def refused(root, capsys, *argv):
    code, _, err = run(root, *argv, capsys=capsys)
    assert code == 5, err
    return err


CONFIG_SOURCE = "([git].commit in .taskrail/config.toml)"


def test_autopilot_refuses_a_config_on_done(pilot, capsys):  # noqa: F811
    pilot_config(pilot, 'commit = "on-done"')
    for argv in (
        ("autopilot", "start", "--count", "2"),
        ("autopilot", "start", "--count", "2", "--kinds", "bug"),
        ("autopilot", "start", "--tasks", "T001"),
        ("autopilot", "next"),
    ):
        err = refused(pilot.root, capsys, *argv)
        assert err.startswith("taskrail: the autopilot needs lanes that commit as each stage ends; ")
        assert CONFIG_SOURCE in err
    assert "kind `bug` commits on done ([git].commit in .taskrail/config.toml)" in refused(
        pilot.root, capsys, "autopilot", "start", "--count", "2", "--kinds", "bug"
    )


def test_autopilot_names_every_on_done_kind_with_its_source(pilot, capsys):  # noqa: F811
    pilot_config(pilot, 'commit = "on-done"')
    override(pilot, "feature", '"stages"')
    override(pilot, "chore", '"on-done"')
    err = refused(pilot.root, capsys, "autopilot", "next")
    assert "kind `feature`" not in err
    assert "kind `bug` commits on done ([git].commit in .taskrail/config.toml)" in err
    assert "kind `chore` commits on done (.taskrail/overrides/chore/kind.toml)" in err


def test_autopilot_refuses_existing_runs_after_the_switch(pilot, capsys):  # noqa: F811
    count_run = json.loads(run(pilot.root, "autopilot", "start", "--count", "2", "--json", capsys=capsys)[1])["run"]["id"]
    named_run = json.loads(run(pilot.root, "autopilot", "start", "--tasks", "T001", "--json", capsys=capsys)[1])["run"]["id"]
    pilot_config(pilot, 'commit = "on-done"')
    assert CONFIG_SOURCE in refused(pilot.root, capsys, "autopilot", "extend", count_run, "--count", "3")
    assert CONFIG_SOURCE in refused(pilot.root, capsys, "autopilot", "extend", named_run, "--tasks", "T002")
    assert CONFIG_SOURCE in refused(pilot.root, capsys, "autopilot", "next", "--run", count_run)
    assert CONFIG_SOURCE in refused(pilot.root, capsys, "autopilot", "next", "--run", named_run)
    # Criterion 9: inspection keeps working.
    code, _, err = run(pilot.root, "autopilot", "status", "--run", count_run, capsys=capsys)
    assert code == 0, err


def test_autopilot_checks_only_the_kinds_a_run_drives(pilot, capsys):  # noqa: F811
    override(pilot, "chore", '"on-done"')
    pilot_config(pilot, autopilot='max_lanes = 10\nkinds = ["bug", "feature"]\n')
    assert run(pilot.root, "autopilot", "next", capsys=capsys)[0] == 0
    count_run = json.loads(run(pilot.root, "autopilot", "start", "--count", "1", "--json", capsys=capsys)[1])["run"]["id"]
    assert run(pilot.root, "autopilot", "next", "--run", count_run, capsys=capsys)[0] == 0

    pilot_config(pilot)  # every allowed kind is driven again
    assert "kind `chore` commits on done" in refused(pilot.root, capsys, "autopilot", "next")
    named_run = json.loads(run(pilot.root, "autopilot", "start", "--tasks", "T001,T002", "--json", capsys=capsys)[1])["run"]["id"]
    assert run(pilot.root, "autopilot", "extend", named_run, "--tasks", "T005", capsys=capsys)[0] == 0
    assert run(pilot.root, "autopilot", "next", "--run", named_run, capsys=capsys)[0] == 0
    assert "kind `chore`" in refused(pilot.root, capsys, "autopilot", "extend", named_run, "--tasks", "T003")
    assert "kind `chore`" in refused(pilot.root, capsys, "autopilot", "start", "--tasks", "T003")
    assert "kind `chore`" in refused(pilot.root, capsys, "autopilot", "start", "--count", "1", "--kinds", "chore")
    assert run(pilot.root, "autopilot", "start", "--count", "1", "--kinds", "bug", capsys=capsys)[0] == 0


def test_a_disabled_autopilot_is_refused_first(pilot, capsys):  # noqa: F811
    pilot_config(pilot, 'commit = "on-done"', enabled=False)
    assert "[autopilot].enabled" in refused(pilot.root, capsys, "autopilot", "next")
