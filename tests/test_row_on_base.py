"""T070: a task whose row is missing from its base — `base.row`, `taskrail workspace`, and `new`'s warning."""

import json
import re
import subprocess
from pathlib import Path

import pytest
from conftest import BASE_CONFIG, git
from test_install import empty_repo, init  # noqa: F401

from taskrail import ids, install
from taskrail.autopilot import runs
from taskrail.cli import build_parser, main
from taskrail.config import load_config
from taskrail.project import load_project

BRANCH = "T004-negative-totals"

CONFIG = BASE_CONFIG.replace("custom = []", 'custom = ["Area"]')

TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |

## E01 — Billing

| ✓  | ID   | Kind    | Pts | Depends On | Title          | Description | Area |
|----|------|---------|-----|------------|----------------|-------------|------|
| ✅ | T001 | chore   | 2   | —          | Price table    | Base prices | api  |
| ⬜ | T002 | feature | 3   | T001       | Repricing      | Recompute   | api  |
| ⬜ | T003 | bug     | 1   | T002       | Rounding error | Off by one  | ui   |
"""


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


def configure(repo, extra=""):
    repo.write(".taskrail/config.toml", CONFIG + extra)


@pytest.fixture
def remote_repo(git_repo, tmp_path_factory):
    """`main` with three tasks and an Area column, pushed to a bare `origin` it tracks."""
    configure(git_repo)
    git_repo.write("TODO.md", TODO)
    commit_all(git_repo.root, "backlog")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "-u", "origin", "main")
    git_repo.bare = bare
    return git_repo


def add_row(repo, capsys, *extra, title="Negative totals"):
    """`new` without `--workspace`: the row is written, uncommitted, in this checkout."""
    code, out, err = run(repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", title, "--json", *extra, capsys=capsys)
    assert code == 0, err
    return json.loads(out), err


def advance_remote(repo, tmp_path_factory):
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(repo.root, "clone", "-q", str(repo.bare), str(clone))
    (clone / "NOTES.md").write_text("elsewhere\n")
    commit_all(clone, "remote change")
    git(clone, "push", "-q", "origin", "main")
    git(repo.root, "fetch", "-q", "origin")


def todo(root) -> str:
    return (Path(root) / "TODO.md").read_text(encoding="utf-8")


def reserved(root) -> list[str]:
    config = load_config(Path(root))
    return [r["id"] for r in ids.reservations(config, config.backlogs[0])]


def nothing_created(repo, branch=BRANCH):
    assert not git(repo.root, "branch", "--list", branch)
    worktrees = repo.root / ".worktrees"
    assert not worktrees.exists() or not any(worktrees.iterdir())


# --- 1. base.row -----------------------------------------------------------------------------------


def test_base_row_is_on_base_for_a_committed_task_and_missing_for_one_only_this_checkout_has(remote_repo, capsys):
    assert data(remote_repo.root, "show", "T002", capsys=capsys)["base"]["row"] == "on-base"
    add_row(remote_repo, capsys)
    assert git(remote_repo.root, "status", "--porcelain") == "M TODO.md"
    base = data(remote_repo.root, "show", "T004", capsys=capsys)["base"]
    assert (base["onto"], base["row"]) == ("origin/main", "missing")


def test_a_row_committed_on_a_branch_that_is_not_the_base_is_missing(remote_repo, capsys):
    git(remote_repo.root, "switch", "-q", "-c", "topic")
    add_row(remote_repo, capsys)
    commit_all(remote_repo.root, "a task on a topic branch")
    base = data(remote_repo.root, "show", "T004", capsys=capsys)["base"]
    assert (base["onto"], base["row"]) == ("origin/main", "missing")


def test_base_row_is_on_branch_in_the_workspace_new_created(remote_repo, capsys):
    created = data(remote_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals", "--workspace", capsys=capsys)
    workspace = Path(created["workspace"])
    assert data(workspace, "show", "T004", capsys=capsys)["base"]["row"] == "on-branch"
    commit_all(workspace, "add T004")
    assert data(workspace, "show", "T004", capsys=capsys)["base"]["row"] == "on-branch"


def test_base_row_is_null_when_the_mainlines_have_diverged(remote_repo, tmp_path_factory, capsys):
    advance_remote(remote_repo, tmp_path_factory)
    (remote_repo.root / "LOCAL.md").write_text("local\n")
    commit_all(remote_repo.root, "local change")
    base = data(remote_repo.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["diverged"], base["row"]) == (None, True, None)


# --- 2. show text ----------------------------------------------------------------------------------


def test_show_text_names_the_missing_row_and_the_command(remote_repo, capsys):
    add_row(remote_repo, capsys)
    out = run(remote_repo.root, "show", "T004", capsys=capsys)[1]
    assert "  row not on origin/main: only this checkout has it; run `taskrail workspace T004`" in out
    assert "row not on" not in run(remote_repo.root, "show", "T002", capsys=capsys)[1]


# --- 3. next ---------------------------------------------------------------------------------------


def test_next_keeps_a_missing_row_and_marks_it(remote_repo, capsys):
    before = run(remote_repo.root, "next", capsys=capsys)[1].splitlines()
    add_row(remote_repo, capsys)
    listed = {entry["id"]: entry for entry in data(remote_repo.root, "next", capsys=capsys)}
    assert listed["T004"]["base"]["row"] == "missing"
    assert listed["T002"]["base"]["row"] == "on-base"
    lines = run(remote_repo.root, "next", capsys=capsys)[1].splitlines()
    marked = [line for line in lines if line.startswith("T004")]
    assert len(marked) == 1 and marked[0].endswith("  (row not on origin/main)")
    assert [line for line in lines if not line.startswith("T004")] == before


# --- 4. autopilot next -----------------------------------------------------------------------------


def test_autopilot_next_skips_a_missing_row_and_dispatches_the_rest(remote_repo, capsys):
    configure(remote_repo, "\n[autopilot]\nenabled = true\nmax_lanes = 10\n")
    commit_all(remote_repo.root, "autopilot")
    git(remote_repo.root, "push", "-q", "origin", "main")
    add_row(remote_repo, capsys)
    reason = {"id": "T004", "reason": "row not on origin/main: run taskrail workspace T004"}

    preview = data(remote_repo.root, "autopilot", "next", capsys=capsys)
    assert reason in preview["skipped"]
    assert [task["id"] for task in preview["dispatch"]] == ["T002"]

    run_id = data(remote_repo.root, "autopilot", "start", "--count", "5", capsys=capsys)["run"]["id"]
    report = data(remote_repo.root, "autopilot", "next", "--run", run_id, capsys=capsys)
    assert reason in report["skipped"]
    assert [task["id"] for task in report["dispatch"]] == ["T002"]
    assert "T004" not in runs.read(load_config(remote_repo.root), run_id)["tasks"]


# --- 5. taskrail workspace with worktrees ----------------------------------------------------------


def test_workspace_carries_the_row_with_its_id_and_cells(remote_repo, capsys):
    committed = git(remote_repo.root, "show", "HEAD:TODO.md")
    add_row(remote_repo, capsys, "--pts", "2", "--depends-on", "T001", "--description", "Refunds | credits", "--column", "Area=billing")
    # Any reservation while the row sits in this checkout drops T004's own (§6.3).
    assert run(remote_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T005"
    assert run(remote_repo.root, "unreserve-id", "T005", capsys=capsys)[0] == 0
    assert "T004" not in reserved(remote_repo.root)

    result = data(remote_repo.root, "workspace", "T004", capsys=capsys)
    workspace = (remote_repo.root / ".worktrees" / BRANCH).resolve()
    assert result == {
        "id": "T004", "backlog": "main", "epic": "E01", "branch": BRANCH, "workspace": str(workspace), "base": "origin/main",
        "files": ["TODO.md"], "removed_from": {"path": str(remote_repo.root), "files": ["TODO.md"], "uncommitted": False},
        "reservation_added": True, "record_remote": None,
    }
    assert git(workspace, "branch", "--show-current") == BRANCH
    assert git(workspace, "merge-base", "HEAD", "origin/main") == git(remote_repo.root, "rev-parse", "origin/main")
    upstream = subprocess.run(["git", "config", "--get-regexp", rf"^branch\.{BRANCH}\."], cwd=remote_repo.root, capture_output=True, text=True)
    assert upstream.stdout == ""

    project, _ = load_project(load_config(workspace))
    task = project.task("T004")
    assert (task.status_raw, task.kind, task.points, task.depends_on, task.title, task.description, task.columns) == (
        "⬜", "bug", 2, ["T001"], "Negative totals", "Refunds | credits", {"Area": "billing"},
    )
    assert "Refunds \\| credits" in todo(workspace)

    assert todo(remote_repo.root) == committed + "\n"
    assert git(remote_repo.root, "status", "--porcelain", "--", "TODO.md") == ""
    assert "T004" in reserved(remote_repo.root)
    assert run(remote_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T005"

    shown = data(workspace, "show", "T004", capsys=capsys)
    assert (shown["branch"], shown["branch_source"], shown["base"]["row"]) == (BRANCH, "recorded", "on-branch")
    assert run(workspace, "claim", "T004", capsys=capsys)[0] == 0


def test_workspace_text_output(remote_repo, capsys):
    add_row(remote_repo, capsys)
    code, out, _ = run(remote_repo.root, "workspace", "T004", capsys=capsys)
    assert code == 0
    workspace = (remote_repo.root / ".worktrees" / BRANCH).resolve()
    assert out.splitlines() == ["T004", f"workspace {workspace} on branch {BRANCH} from origin/main", f"removed from {remote_repo.root}: TODO.md"]


# --- 6. worktree = "never" -------------------------------------------------------------------------


def never(repo):
    configure(repo, '\n[git]\nworktree = "never"\n')
    commit_all(repo.root, "no worktrees")
    git(repo.root, "push", "-q", "origin", "main")


def test_workspace_switches_this_checkout_when_worktrees_are_off(remote_repo, capsys):
    never(remote_repo)
    add_row(remote_repo, capsys)
    result = data(remote_repo.root, "workspace", "T004", capsys=capsys)
    assert (result["workspace"], result["branch"], result["removed_from"]["uncommitted"]) == (str(remote_repo.root), BRANCH, False)
    assert git(remote_repo.root, "branch", "--show-current") == BRANCH
    assert "| T004 |" in todo(remote_repo.root)
    assert git(remote_repo.root, "status", "--porcelain") == "M TODO.md"
    assert "| T004 |" not in git(remote_repo.root, "show", "main:TODO.md")


def test_workspace_refuses_other_uncommitted_changes_when_worktrees_are_off(remote_repo, capsys):
    never(remote_repo)
    add_row(remote_repo, capsys)
    (remote_repo.root / "NOTES.md").write_text("draft\n")
    code, _, err = run(remote_repo.root, "workspace", "T004", capsys=capsys)
    assert code == 5 and "uncommitted changes" in err
    assert git(remote_repo.root, "branch", "--show-current") == "main"
    assert "| T004 |" in todo(remote_repo.root)
    nothing_created(remote_repo)


# --- 7. Refusals change nothing --------------------------------------------------------------------


def refused(repo, capsys, *argv, code):
    before = (todo(repo.root), reserved(repo.root))
    status, _, err = run(repo.root, "workspace", *argv, capsys=capsys)
    assert status == code, err
    assert (todo(repo.root), reserved(repo.root)) == before
    return err


def test_workspace_refuses_an_unknown_task(remote_repo, capsys):
    assert "no task `T999`" in refused(remote_repo, capsys, "T999", code=3)


def test_workspace_refuses_a_row_already_on_its_base(remote_repo, capsys):
    err = refused(remote_repo, capsys, "T002", code=5)
    assert "T002 is already on origin/main" in err
    nothing_created(remote_repo, "T002-repricing")


def test_workspace_refuses_a_task_whose_branch_exists(remote_repo, capsys):
    add_row(remote_repo, capsys)
    git(remote_repo.root, "branch", BRANCH)
    assert f"branch {BRANCH} already exists" in refused(remote_repo, capsys, "T004", code=5)
    assert not (remote_repo.root / ".worktrees").exists()


def test_workspace_refuses_a_task_that_is_not_pending(remote_repo, capsys):
    assert "T001 is done, not pending" in refused(remote_repo, capsys, "T001", code=5)


def test_workspace_refuses_a_claimed_task(remote_repo, capsys):
    add_row(remote_repo, capsys)
    assert run(remote_repo.root, "claim", "T004", "--owner", "alice", capsys=capsys)[0] == 0
    assert "claimed by alice" in refused(remote_repo, capsys, "T004", "--owner", "bob", code=4)
    assert "release it first" in refused(remote_repo, capsys, "T004", "--owner", "alice", code=5)
    nothing_created(remote_repo)


def test_workspace_refuses_diverged_mainlines(remote_repo, tmp_path_factory, capsys):
    advance_remote(remote_repo, tmp_path_factory)
    (remote_repo.root / "LOCAL.md").write_text("local\n")
    commit_all(remote_repo.root, "local change")
    add_row(remote_repo, capsys)
    assert "have diverged" in refused(remote_repo, capsys, "T004", code=5)
    nothing_created(remote_repo)


def test_workspace_refuses_an_epic_missing_on_the_base(remote_repo, capsys):
    assert run(remote_repo.root, "epic", "add", "--name", "Auth", "--objective", "Sign in", capsys=capsys)[0] == 0
    code, out, err = run(remote_repo.root, "new", "--epic", "E02", "--kind", "bug", "--title", "Lockout", "--json", capsys=capsys)
    assert code == 0, err
    assert "epic `E02` does not exist on origin/main" in refused(remote_repo, capsys, "T004", code=3)
    nothing_created(remote_repo, "T004-lockout")


def test_workspace_refuses_a_row_whose_dependency_only_this_checkout_has(remote_repo, capsys):
    add_row(remote_repo, capsys)
    add_row(remote_repo, capsys, "--depends-on", "T004", title="After negatives")
    err = refused(remote_repo, capsys, "T005", code=1)
    assert "nothing was written" in err
    nothing_created(remote_repo, "T005-after-negatives")


def test_workspace_refuses_a_row_another_row_here_depends_on(remote_repo, capsys):
    add_row(remote_repo, capsys)
    add_row(remote_repo, capsys, "--depends-on", "T004", title="After negatives")
    assert "nothing was written" in refused(remote_repo, capsys, "T004", code=1)
    nothing_created(remote_repo)


# --- 8. --branch ------------------------------------------------------------------------------------


def test_workspace_branch_names_and_records_the_branch(remote_repo, capsys):
    add_row(remote_repo, capsys)
    result = data(remote_repo.root, "workspace", "T004", "--branch", "fix/negative", capsys=capsys)
    assert result["branch"] == "fix/negative"
    shown = data(Path(result["workspace"]), "show", "T004", capsys=capsys)
    assert (shown["branch"], shown["branch_source"]) == ("fix/negative", "recorded")


def test_workspace_refuses_an_invalid_branch_name(remote_repo, capsys):
    add_row(remote_repo, capsys)
    assert "is not a valid branch name" in refused(remote_repo, capsys, "T004", "--branch", "bad name", code=2)
    nothing_created(remote_repo)


# --- 9. new's warning on a mainline -----------------------------------------------------------------


def test_new_without_workspace_warns_on_the_mainline(remote_repo, capsys):
    result, err = add_row(remote_repo, capsys)
    message = "T004 was written to this checkout of main, uncommitted; commit it to main, or run `taskrail workspace T004` to move it into its own branch"
    assert f"taskrail: warning: {message}" in err
    assert result["warning"] == message


def test_new_on_another_branch_or_with_a_workspace_does_not_warn(remote_repo, capsys):
    created = data(remote_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals", "--workspace", capsys=capsys)
    assert created["warning"] is None
    git(remote_repo.root, "switch", "-q", "-c", "topic")
    result, err = add_row(remote_repo, capsys, title="Follow-up")
    assert result["warning"] is None
    assert "warning" not in err


# --- 10. The skill ---------------------------------------------------------------------------------


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


PHRASES = (
    "if `base.row` is `missing`, the task's row exists only in this checkout",
    "run `taskrail workspace <id> --json` instead of the git commands below",
    "on a mainline checkout `new` warns",
    "move such a row into its own workspace with `taskrail workspace <id>`, which keeps its id",
)


@pytest.mark.parametrize(("integration", "skills_dir"), [(None, None), ("claude", ".claude/skills"), ("opencode", ".opencode/skills")])
def test_the_core_skill_names_base_row_and_the_workspace_command(empty_repo, capsys, integration, skills_dir):
    if integration is None:
        text = (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")
    else:
        init(empty_repo, "--integration", integration, capsys=capsys)
        text = (empty_repo / skills_dir / "taskrail/SKILL.md").read_text(encoding="utf-8")
    for phrase in PHRASES:
        assert phrase in flat(text), phrase


def test_the_workspace_command_and_its_flags_exist():
    commands = next(action for action in build_parser()._actions if action.dest == "command").choices
    options = commands["workspace"]._option_string_actions
    for flag in ("--branch", "--owner", "--json"):
        assert flag in options, flag
