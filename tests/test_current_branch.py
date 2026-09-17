"""Working tasks on the checked-out branch with `[git] task_branch = "current"` (T080, DESIGN.md §13.2)."""

import json

import pytest
from conftest import BASE_CONFIG, git

from taskrail import branches, claims
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.issues import ConfigError

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
"""

CHECKS = '[checks]\ntest = "echo test-ran"\nlint = "echo lint-ran"\n'
CURRENT = '\n[git]\nworktree = "never"\ntask_branch = "current"\n'
ENABLED = '\n[autopilot]\nenabled = true\n'
REFUSAL = '[git].task_branch is "current"'
AUTOPILOT_REFUSAL = 'taskrail: the autopilot needs a branch per task; [git].task_branch is "current" in .taskrail/config.toml'


def config(git_table: str = CURRENT, extra: str = "") -> str:
    head, _ = BASE_CONFIG.split("[checks]")
    return head + CHECKS + git_table + extra


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


@pytest.fixture
def current(git_repo, tmp_path_factory):
    """A current-branch repository with the autopilot enabled and a bare origin whose main it tracks."""
    git_repo.write(".taskrail/config.toml", config(extra=ENABLED))
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "-u", "origin", "main")
    return git_repo


def use_task_branches(repo, extra: str = ENABLED) -> None:
    repo.write(".taskrail/config.toml", config("", extra))


def use_current(repo, extra: str = ENABLED) -> None:
    repo.write(".taskrail/config.toml", config(CURRENT, extra))


# Criteria 1 and 2: configuration


def test_task_branch_defaults_to_task(repo):
    assert load_config(repo.root).task_branch == "task"


def test_current_with_worktree_never_loads(repo):
    repo.write(".taskrail/config.toml", config())
    assert load_config(repo.root).task_branch == "current"


@pytest.mark.parametrize("value", ['"branch"', '""', "true"])
def test_an_unknown_task_branch_exits_2_naming_the_key(git_repo, capsys, value):
    git_repo.write(".taskrail/config.toml", config(f'\n[git]\nworktree = "never"\ntask_branch = {value}\n'))
    with pytest.raises(ConfigError, match="task_branch"):
        load_config(git_repo.root)
    for argv in (["validate"], ["show", "T001"]):
        code, _, err = run(git_repo.root, *argv, capsys=capsys)
        assert code == 2
        assert "task_branch" in err


@pytest.mark.parametrize("worktree", ["", 'worktree = "required"\n'])
def test_current_requires_worktree_never(git_repo, capsys, worktree):
    git_repo.write(".taskrail/config.toml", config(f'\n[git]\n{worktree}task_branch = "current"\n'))
    code, _, err = run(git_repo.root, "validate", capsys=capsys)
    assert code == 2
    assert 'git.task_branch = "current" requires git.worktree = "never"' in err


# Criterion 3: the task_branch field


def test_show_list_and_next_report_task_branch(current, capsys):
    for expected, configure in (("current", use_current), ("task", use_task_branches)):
        configure(current)
        assert data(current.root, "show", "T001", capsys=capsys)["task_branch"] == expected
        assert {entry["task_branch"] for entry in data(current.root, "list", capsys=capsys)} == {expected}
        assert {entry["task_branch"] for entry in data(current.root, "next", capsys=capsys)} == {expected}


# Criteria 4 and 5: branch, base and worktree


def test_branch_is_the_checked_out_branch_with_no_base_or_worktree(current, capsys):
    shown = data(current.root, "show", "T001", capsys=capsys)
    assert shown["branch"] == "main"
    assert shown["branch_source"] == "current"
    assert shown["base"] is None
    assert shown["worktree"] is None
    assert shown["worktree_base"] is None
    for entry in data(current.root, "list", capsys=capsys):
        assert (entry["branch"], entry["branch_source"], entry["base"], entry["worktree"]) == ("main", "current", None, None)

    git(current.root, "switch", "-q", "-c", "topic")
    assert data(current.root, "show", "T003", capsys=capsys)["branch"] == "topic"


def test_branch_follows_the_checkout_while_the_claim_names_another(current, capsys):
    assert data(current.root, "claim", "T001", capsys=capsys)["claim"]["branch"] == "main"
    git(current.root, "switch", "-q", "-c", "elsewhere")
    shown = data(current.root, "show", "T001", capsys=capsys)
    assert shown["branch"] == "elsewhere"
    assert shown["branch_source"] == "current"
    assert shown["claim"]["branch"] == "main"


def test_branch_is_null_on_a_detached_head(current, capsys):
    git(current.root, "switch", "-q", "--detach")
    shown = data(current.root, "show", "T001", capsys=capsys)
    assert shown["branch"] is None
    assert shown["branch_source"] == "current"


def test_show_text_has_no_base_line(current, capsys):
    code, out, err = run(current.root, "show", "T001", capsys=capsys)
    assert code == 0, err
    assert "\n  base " not in out
    use_task_branches(current)
    code, out, err = run(current.root, "show", "T001", capsys=capsys)
    assert "\n  base origin/main" in out or "\n  base main" in out


# Criterion 6: prior work


def test_prior_work_reports_no_branches_and_no_prepared_workspace(current, capsys):
    current.write("docs/features/T001-base-task.md", "# T001\n")
    commit_all(current.root, "feat(cli): start the base task (T001)")
    git(current.root, "branch", "T001-base-task")  # the template name exists, and is not evidence here
    # Names T001 only in passing and contains the checked-out branch's name: the `branch` form would match it.
    git(current.root, "commit", "-q", "--allow-empty", "-m", "Merge main into the work before T001 lands")

    prior = data(current.root, "show", "T001", capsys=capsys)["prior_work"]
    assert prior["branches"] == []
    assert prior["prepared"] is None
    assert "working tree" in prior["artifact"]
    assert [(commit["subject"], commit["match"]) for commit in prior["commits"]] == [("feat(cli): start the base task (T001)", "suffix")]
    assert prior["commits_total"] == 1


# Criterion 7: no done-branch, discarded-branch or stacking


def _close_on_template_branch(repo, task_id, branch, mark):
    git(repo.root, "switch", "-q", "-c", branch)
    todo = (repo.root / "TODO.md").read_text(encoding="utf-8")
    (repo.root / "TODO.md").write_text(todo.replace(f"| ⬜ | {task_id} |", f"| {mark} | {task_id} |"), encoding="utf-8")
    commit_all(repo.root, f"chore({task_id}): close")
    git(repo.root, "switch", "-q", "main")


def test_a_task_closed_on_another_branch_is_not_done_branch(current, capsys):
    _close_on_template_branch(current, "T001", "T001-base-task", "✅")
    _close_on_template_branch(current, "T003", "T003-independent", "❌")

    use_task_branches(current)  # the same refs make them done-branch and discarded-branch per task
    assert data(current.root, "show", "T001", capsys=capsys)["state"] == "done-branch"
    assert data(current.root, "show", "T003", capsys=capsys)["state"] == "discarded-branch"
    assert data(current.root, "show", "T002", capsys=capsys)["base"]["dependency"] == "T001"

    use_current(current)
    assert data(current.root, "show", "T001", capsys=capsys)["state"] == "pending"
    assert data(current.root, "show", "T003", capsys=capsys)["state"] == "pending"
    dependent = data(current.root, "show", "T002", capsys=capsys)
    assert dependent["state"] == "blocked"
    assert dependent["blocked_by"] == ["T001"]
    assert "T002" not in [entry["id"] for entry in data(current.root, "next", capsys=capsys)]
    code, _, err = run(current.root, "claim", "T002", capsys=capsys)
    assert code == 5
    assert "blocked by T001" in err


def test_a_dependency_done_in_the_checkout_unblocks(current, capsys):
    assert data(current.root, "claim", "T001", capsys=capsys)["claimed"]
    data(current.root, "done", "T001", capsys=capsys)
    assert data(current.root, "show", "T002", capsys=capsys)["state"] == "pending"


# Criterion 8: claim


def test_claim_records_the_checked_out_branch_without_a_warning_or_record(current, capsys):
    result = data(current.root, "claim", "T001", capsys=capsys)
    assert result["warning"] is None
    assert result["branch_recorded"] is False
    assert result["claim"]["branch"] == "main"
    assert result["claim"]["base"] is None
    assert branches.read(load_config(current.root), "T001") is None
    assert claims.read(load_config(current.root), "T001").branch == "main"
    _, _, err = run(current.root, "show", "T001", capsys=capsys)
    assert "warning" not in err


def test_claim_on_a_detached_head_warns_to_check_out_a_branch(current, capsys):
    git(current.root, "switch", "-q", "--detach")
    code, out, err = run(current.root, "claim", "T001", "--json", capsys=capsys)
    assert code == 0, err
    result = json.loads(out)
    assert result["claim"]["branch"] is None
    assert "detached HEAD" in result["warning"]
    assert "check out a branch to work the task on" in result["warning"]
    assert "taskrail branch" not in result["warning"]
    assert result["warning"] in err
    assert branches.read(load_config(current.root), "T001") is None


# Criterion 9: commands that assume a task branch


def test_new_workspace_is_refused_before_reserving_an_id(current, capsys):
    before = git(current.root, "branch", "--list")
    code, out, err = run(current.root, "new", "--epic", "E01", "--kind", "chore", "--title", "Refused", "--workspace", capsys=capsys)
    assert code == 5
    assert out == ""
    assert REFUSAL in err
    assert git(current.root, "branch", "--list") == before
    assert data(current.root, "new", "--epic", "E01", "--kind", "chore", "--title", "Next one", capsys=capsys)["id"] == "T004"


def test_new_workspace_with_branch_is_refused_the_same_way(current, capsys):
    code, _, err = run(current.root, "new", "--epic", "E01", "--kind", "chore", "--title", "X", "--workspace", "--branch", "main", capsys=capsys)
    assert code == 5
    assert REFUSAL in err


def test_new_workspace_with_an_unknown_epic_still_exits_3(current, capsys):
    code, _, _ = run(current.root, "new", "--epic", "E09", "--kind", "chore", "--title", "X", "--workspace", capsys=capsys)
    assert code == 3


@pytest.mark.parametrize("argv", [["workspace", "T001"], ["branch", "T001", "feature/base"]])
def test_workspace_and_branch_are_refused(current, capsys, argv):
    todo = (current.root / "TODO.md").read_text(encoding="utf-8")
    code, out, err = run(current.root, *argv, capsys=capsys)
    assert code == 5
    assert out == ""
    assert REFUSAL in err
    assert (current.root / "TODO.md").read_text(encoding="utf-8") == todo
    assert branches.read(load_config(current.root), "T001") is None
    assert git(current.root, "branch", "--list", "feature/base") == ""


@pytest.mark.parametrize("argv", [["workspace", "T099"], ["branch", "T099", "feature/base"]])
def test_workspace_and_branch_of_an_unknown_task_still_exit_3(current, capsys, argv):
    code, _, _ = run(current.root, *argv, capsys=capsys)
    assert code == 3


# Criterion 10: no mainline warning


def test_new_on_the_mainline_does_not_warn(current, capsys):
    code, out, err = run(current.root, "new", "--epic", "E01", "--kind", "chore", "--title", "On main", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["warning"] is None
    assert "warning" not in err

    use_task_branches(current)
    result = data(current.root, "new", "--epic", "E01", "--kind", "chore", "--title", "Warned", capsys=capsys)
    assert result["warning"] is not None


# Criterion 11: edit


def test_edit_never_records_the_old_branch(current, capsys):
    git(current.root, "branch", "T003-independent")  # would be kept by a record under task branches
    result = data(current.root, "edit", "T003", "--title", "Renamed task", capsys=capsys)
    assert result["branch"]["recorded"] is False
    assert result["branch"]["source"] == "current"
    assert branches.read(load_config(current.root), "T003") is None


# Criterion 12: checks


def test_checks_run_in_the_checkout_without_a_claim(current, capsys):
    code, out, err = run(current.root, "checks", "T001", "--json", capsys=capsys)
    assert code == 0, err
    result = json.loads(out)
    assert result["worktree"] == str(current.root.resolve())
    assert [check["status"] for check in result["checks"]] == ["passed", "passed"]


def test_checks_run_in_the_checkout_on_a_detached_head(current, capsys):
    git(current.root, "switch", "-q", "--detach")
    code, out, err = run(current.root, "checks", "T001", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["worktree"] == str(current.root.resolve())


def test_checks_run_in_the_claims_worktree_when_it_exists(current, capsys, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("elsewhere")
    data(current.root, "claim", "T001", "--worktree", str(elsewhere), capsys=capsys)
    code, out, err = run(current.root, "checks", "T001", "--json", capsys=capsys)
    assert code == 0, err
    assert json.loads(out)["worktree"] == str(elsewhere.resolve())


# Criterion 13: the autopilot


def test_autopilot_start_extend_and_next_are_refused(current, capsys):
    use_task_branches(current)
    run_id = data(current.root, "autopilot", "start", "--count", "1", capsys=capsys)["run"]["id"]
    use_current(current)

    for argv in (
        ["autopilot", "start", "--count", "1"],
        ["autopilot", "start", "--tasks", "T001"],
        ["autopilot", "extend", run_id, "--count", "2"],
        ["autopilot", "next"],
        ["autopilot", "next", "--run", run_id],
    ):
        code, out, err = run(current.root, *argv, capsys=capsys)
        assert code == 5, argv
        assert out == ""
        assert err.strip() == AUTOPILOT_REFUSAL

    code, _, err = run(current.root, "autopilot", "status", "--run", run_id, capsys=capsys)
    assert code == 0, err


def test_the_enabled_check_comes_first(current, capsys):
    use_current(current, extra="")
    code, _, err = run(current.root, "autopilot", "start", "--count", "1", capsys=capsys)
    assert code == 5
    assert "the autopilot is disabled" in err
