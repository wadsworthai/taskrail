"""T084: the skills follow the workflow `show` reports — the current branch, on-done commits,
`decisions` gates and a report-only close — in the sources and in the copies `init` installs."""

import re

import pytest
from test_autopilot_skill import flat, subparsers
from test_install import empty_repo, init  # noqa: F401

from taskrail import install
from taskrail.cli import build_parser

EXECUTORS = ("bug", "chore", "feature", "spike")
SKILLS_DIRS = {"claude": ".claude/skills", "opencode": ".opencode/skills"}


@pytest.fixture(params=["source", "claude", "opencode"])
def skill_copy(request, empty_repo, capsys):
    """A reader of one shipped skill file, `<skill>/<file>`: the source, or the copy `init` installs."""
    if request.param == "source":
        return lambda name: (install.SKILLS_SOURCE / name).read_text(encoding="utf-8")
    init(empty_repo, "--integration", request.param, capsys=capsys)
    skills = empty_repo / SKILLS_DIRS[request.param]
    return lambda name: (skills / name).read_text(encoding="utf-8")


def step(text: str, start: str, end: str) -> str:
    return flat(text[text.index(start) : text.index(end)])


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"no section {heading!r}"
    return flat(match.group(1))


def assert_phrases(text: str, phrases) -> None:
    for phrase in phrases:
        assert phrase in text, phrase


# --- 1. The core skill: inspect, workspace and claim -----------------------------------------------


def test_inspect_reads_the_workflow_from_show(skill_copy):
    text = skill_copy("taskrail/SKILL.md")
    assert_phrases(
        step(text, "2. **Inspect.**", "3. **Workspace.**"),
        ("`task_branch`", "`close.commit`", "`close.review`", "effective `gate` and `commit`"),
    )


def test_the_workspace_step_is_skipped_on_the_current_branch(skill_copy):
    text = step(skill_copy("taskrail/SKILL.md"), "3. **Workspace.**", "4. **Claim.**")
    assert text.startswith('3. **workspace.** when `task_branch` is `"current"`, skip this step')
    assert_phrases(
        text,
        (
            "whichever it is, the mainline included",
            "`base`, `worktree` and `worktree_base` are `null`",
            "`taskrail new --workspace`, `taskrail workspace` and `taskrail branch` exit 5",
            'under `"task"`: run `git fetch <base.remote>`',
        ),
    )


def test_on_the_current_branch_it_stops_only_for_a_detached_head_or_a_claim_on_another_branch(skill_copy):
    """Orchestrator decision 9: any checked-out branch is the task's; two concrete reasons to stop."""
    text = step(skill_copy("taskrail/SKILL.md"), "3. **Workspace.**", "4. **Claim.**")
    assert_phrases(
        text,
        (
            "stop and ask only when `branch` is `null` (a detached `head`)",
            "or when the task's live claim (`claim.branch`) names another branch than `branch`",
            "otherwise go on to claiming, in the checkout you are in",
        ),
    )
    assert "the branch the human means" not in text


def test_claim_happens_in_the_checkout_on_the_current_branch(skill_copy):
    text = step(skill_copy("taskrail/SKILL.md"), "4. **Claim.**", "5. **Stages.**")
    assert 'from inside the workspace — under `"current"`, the checkout you are in — run `taskrail claim <id>`' in text


def test_a_claim_warning_on_the_current_branch_means_a_detached_head(skill_copy):
    """Implement gate fix: `taskrail branch` exits 5 under "current", so the warning cannot mean a branch to name."""
    text = step(skill_copy("taskrail/SKILL.md"), "4. **Claim.**", "5. **Stages.**")
    assert "switch to that branch, or name it with `taskrail branch`, before any edit" in text
    assert_phrases(
        text,
        (
            'under `"current"`, where `taskrail branch` exits 5, a `warning` means a detached `head`',
            "check out a branch before any edit",
        ),
    )


# --- 2. Stages and commits -------------------------------------------------------------------------


def test_stages_commit_by_the_effective_policy(skill_copy):
    text = step(skill_copy("taskrail/SKILL.md"), "5. **Stages.**", "6. **Scope.**")
    assert_phrases(
        text,
        (
            "commit when the stage's `commit` is true",
            'under `"on-done"` every stage reports `false`, and you commit nothing until the task is done',
            "where an executor skill says to commit, that holds only when the stage's `commit` is true",
            "a stage whose gate is `decisions` is skipped without asking",
            "if its gate is `always`, stop and ask before",
        ),
    )


def test_the_close_commits_as_close_commit_says(skill_copy):
    text = step(skill_copy("taskrail/SKILL.md"), "8. **Close.**", "9. **Hand off.**")
    assert_phrases(
        text,
        (
            "run `taskrail done <id>`",
            "commit as `close.commit` says",
            'inside the workspace — under `"current"`, in the checkout —',
            'under `"current"` no branch is recorded',
            '`"stages"` — commit that status change on its own',
            '`"on-done"` — make one or more logical commits of everything the task changed, the status change included',
        ),
    )


# --- 3. The report-only close asks before any push -------------------------------------------------


def test_a_report_close_runs_review_and_asks_before_any_push(skill_copy):
    text = skill_copy("taskrail/SKILL.md")
    close = step(text, "8. **Close.**", "9. **Hand off.**")
    report = close[close.index('under `"report"`') : close.index('under `"publish"`')]
    assert_phrases(
        report,
        (
            "run `taskrail review <id> --json`",
            "fetches, rebases and pushes nothing",
            "`commits`",
            "`upstream`",
            "`pull_request.title`",
            "never rebase, never run `taskrail review --publish` (it exits 5), and never merge",
            "**ask the human before any push**",
            "only once the human approves, never with force",
            "without approval, push nothing",
            "whatever agent runs the task",
        ),
    )
    publish = close[close.index('under `"publish"`') :]
    assert_phrases(publish, ("`git rebase <rebase.onto>`", "taskrail review <id> --publish --json"))
    hand_off = step(text, "9. **Hand off.**", "## Gates")
    assert_phrases(hand_off, ('under `"report"`', "whether the human approved a push", "there is no link"))


def test_commits_on_the_current_branch_name_the_task(skill_copy):
    text = section(skill_copy("taskrail/SKILL.md"), "Commit messages")
    assert "end each subject with the task id in parentheses" in text
    assert "`fix(billing): round totals half-up (t012)`" in text


# --- 4. The decisions gate -------------------------------------------------------------------------


def test_the_gates_section_describes_the_decisions_gate(skill_copy):
    text = section(skill_copy("taskrail/SKILL.md"), "Gates")
    assert_phrases(
        text,
        (
            "use the gate `show` reports",
            "`always` —",
            "`conditional` —",
            "`none` —",
            "`decisions` — stop during the stage as soon as a decision appears",
            "never at its end to have the stage approved or to report",
            "to the next stop, or to the close hand-off",
            "a **decision** is a choice that the task, the artifact already written",
            "every place an executor skill says to stop and ask is one",
            "what an executor skill calls approved is what the artifact records",
            "with your recommendation and the alternatives",
            "or with the decision or push question",
        ),
    )


@pytest.mark.parametrize("kind", EXECUTORS)
def test_each_executor_skill_takes_gates_and_commits_from_show(skill_copy, kind):
    text = flat(skill_copy(f"taskrail-{kind}/SKILL.md"))
    assert_phrases(
        text,
        (
            "the gate in each heading below is the core kind's default",
            "follow the gate and the `commit` that `taskrail show` reports for each stage",
            '"commit" in a stage holds only when that stage\'s `commit` is true',
            "under a `decisions` gate, where a stage says the human approves at the gate, record what would be approved in the artifact and continue",
            'every "stop and ask" below is one',
        ),
    )


def test_the_autopilot_skill_handles_decisions_gates(skill_copy):
    skill = section(skill_copy("taskrail-autopilot/SKILL.md"), "Answer a gate")
    assert_phrases(
        skill,
        (
            "a stage whose gate is `decisions` stops a lane during the stage",
            "record the stop with `--gate <stage>`, naming the stage the decision arose in",
            "the close is your first full review of the lane's diff",
        ),
    )
    brief = section(skill_copy("taskrail-autopilot/references/lane-brief.md"), "Gates")
    assert "a stage whose gate is `decisions` stops only when a decision appears" in brief
    review = section(skill_copy("taskrail-autopilot/references/gate-review.md"), "Close")
    assert "when a stage's gate was `decisions`" in review and "apply that stage's criteria above to the close review" in review


# --- 5. Agent notes and portability ----------------------------------------------------------------


@pytest.mark.parametrize(("integration", "heading"), [("claude", "On Claude Code"), ("opencode", "On OpenCode")])
def test_each_agents_notes_ask_at_a_decision_and_before_a_push(empty_repo, capsys, integration, heading):
    init(empty_repo, "--integration", integration, capsys=capsys)
    core = (empty_repo / SKILLS_DIRS[integration] / "taskrail/SKILL.md").read_text(encoding="utf-8")
    notes = section(core, heading)
    assert "at a gate, at a decision and before a push, ask the human" in notes
    assert "the gate report or the question" in notes


def test_the_portable_core_skill_asks_before_a_push_without_the_agent_notes():
    text = (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")
    body = flat(text[: text.index(install.HARNESS_MARKER)])
    assert "**ask the human before any push**" in body
    for word in ("Claude", "OpenCode", "AskUserQuestion", "subagent"):
        assert word.lower() not in body, word


def test_every_taskrail_command_and_flag_in_the_core_skill_exists():
    top = subparsers(build_parser())
    text = (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")
    spans = re.findall(r"`([^`\n]+)`", text)
    shown = [m for span in spans for m in re.findall(r"(?<![\w/-])taskrail ([a-z][a-z-]*)([^`]*)", span)]
    assert ("review", " <ID> --json") in shown
    for command, rest in shown:
        assert command in top, command
        parser = top[command]
        words = rest.split()
        if words and any(a.__class__.__name__ == "_SubParsersAction" for a in parser._actions):
            parser = subparsers(parser)[words[0]]  # `epic add`, `kind list`
        for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", rest):
            assert flag in parser._option_string_actions, f"{flag} in `taskrail {command}{rest}`"
