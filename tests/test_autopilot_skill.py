"""T024: the taskrail-autopilot skill — installation, per-skill agent notes and prose invariants."""

import hashlib
import json
import re
import shutil

import pytest
from test_install import empty_repo, init, installed_skills, run, seed_config, set_kinds, upgrade  # noqa: F401

from taskrail import install
from taskrail.cli import build_parser

SKILL = "taskrail-autopilot"
SOURCE = install.SKILLS_SOURCE / SKILL
REFERENCES = ["references/decision-record.md", "references/gate-review.md", "references/lane-brief.md"]
FILES = ["SKILL.md", *REFERENCES]

# The core skill's agent notes: those from before per-skill sections, plus T052's command shape.
CORE_CLAUDE_NOTES = """## On Claude Code

- At a gate, ask the human with the AskUserQuestion tool when it is available; otherwise ask in
  plain text.
- Running as a subagent, you have no channel to the human: end your turn with the gate report
  and wait to be resumed.
- Create task worktrees with git as described above rather than through a subagent's worktree
  isolation, which picks its own branch name and location.
- Shape every shell command so a permission allowlist can match it: one command per Bash
  call, the taskrail wrapper and files by absolute path, and `git -C <worktree>` or
  `taskrail --root <worktree>` instead of `cd <worktree> && …`. Avoid `&&`, `;` and `|`
  chains, shell variables, `$?` and heredocs, and edit files with the Edit tool: Claude Code
  checks each part of a compound command on its own, so it asks for permission even when
  every part is allowed.
- Run a task's checks with `taskrail checks <ID>`, adding `--stage <stage>` for one stage's
  checks, rather than changing into its worktree: it runs them there, with the task's
  autopilot resources, as one command that a single allowlist entry covers."""
CORE_OPENCODE_NOTES = """## On OpenCode

- At a gate, ask the human in plain text and wait for the reply.
- Running as a subagent, your final message goes back to the agent that started you: end with
  the gate report so that agent can relay it."""


def source(name: str) -> str:
    return (SOURCE / name).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """Lower-cased, with every run of whitespace collapsed, so prose checks survive re-wrapping."""
    return re.sub(r"\s+", " ", text).lower()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- 1. Installed with each integration, references included -------------------------------------


@pytest.mark.parametrize(("integration", "skills_dir"), [("claude", ".claude/skills"), ("opencode", ".opencode/skills")])
def test_init_installs_the_autopilot_skill_and_its_references(empty_repo, capsys, integration, skills_dir):
    report = init(empty_repo, "--integration", integration, capsys=capsys)
    for name in FILES:
        assert f"{skills_dir}/{SKILL}/{name}" in report["created"]
        assert (empty_repo / skills_dir / SKILL / name).is_file()
    for name in REFERENCES:
        assert (empty_repo / skills_dir / SKILL / name).read_text(encoding="utf-8") == source(name)


def test_claude_and_opencode_share_one_copy_references_included(empty_repo, capsys):
    init(empty_repo, "--integration", "opencode", capsys=capsys)
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    for name in FILES:
        assert f".opencode/skills/{SKILL}/{name}" in report["removed"]
        assert (empty_repo / ".claude/skills" / SKILL / name).is_file()
    assert not (empty_repo / ".opencode/skills").exists()


# --- 2. Never left out by the kind filter ----------------------------------------------------------


def test_allowed_kinds_never_leave_out_the_autopilot_skill(empty_repo, capsys):
    seed_config(empty_repo, "bug")
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert SKILL in installed_skills(empty_repo)
    assert not any(SKILL in note for note in report["notes"])
    set_kinds(empty_repo, "chore")
    again = upgrade(empty_repo, capsys=capsys)
    assert SKILL in installed_skills(empty_repo)
    assert not [path for path in again["removed"] if SKILL in path]
    assert not any(SKILL in note for note in again["notes"])


# --- 3. Reference files are managed files ----------------------------------------------------------


def test_reference_files_are_recorded_and_reinstalling_changes_nothing(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    for name in REFERENCES:
        assert manifest["files"][f".claude/skills/{SKILL}/{name}"] == digest(source(name))
    again = init(empty_repo, capsys=capsys)
    assert again["created"] == again["updated"] == again["removed"] == again["skipped"] == []


def test_a_locally_edited_reference_is_kept_unless_forced(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    relative = f".claude/skills/{SKILL}/references/gate-review.md"
    path = empty_repo / relative
    path.write_text(path.read_text() + "\nLocal note.\n")
    report = init(empty_repo, capsys=capsys)
    assert report["skipped"] == [{"path": relative, "reason": "edited locally; --force replaces it"}]
    assert "Local note." in path.read_text()
    forced = init(empty_repo, "--force", capsys=capsys)
    assert relative in forced["updated"]
    assert path.read_text() == source("references/gate-review.md")


def test_a_changed_reference_is_updated_and_asks_for_a_restart(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    relative = f".claude/skills/{SKILL}/references/lane-brief.md"
    older = "an older shipped version\n"
    (empty_repo / relative).write_text(older)
    manifest_path = empty_repo / ".taskrail/installed.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][relative] = digest(older)
    manifest_path.write_text(json.dumps(manifest))
    report = init(empty_repo, capsys=capsys)
    assert report["updated"] == [relative]
    assert any("restart the agent session" in note for note in report["notes"])


def test_a_managed_reference_no_longer_shipped_is_removed(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    relative = f".claude/skills/{SKILL}/references/retired.md"
    (empty_repo / relative).write_text("retired\n")
    manifest_path = empty_repo / ".taskrail/installed.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][relative] = digest("retired\n")
    manifest_path.write_text(json.dumps(manifest))
    report = init(empty_repo, capsys=capsys)
    assert report["removed"] == [relative]
    assert not (empty_repo / relative).exists()
    assert any("restart the agent session" in note for note in report["notes"])


def test_the_kind_filter_removes_an_executor_skills_references_with_it(empty_repo, capsys, tmp_path_factory, monkeypatch):
    shipped = tmp_path_factory.mktemp("shipped") / "skills"
    shutil.copytree(install.SKILLS_SOURCE, shipped)
    (shipped / "taskrail-feature/references").mkdir()
    (shipped / "taskrail-feature/references/extra.md").write_text("extra\n")
    monkeypatch.setattr(install, "SKILLS_SOURCE", shipped)
    init(empty_repo, "--integration", "claude", capsys=capsys)
    assert (empty_repo / ".claude/skills/taskrail-feature/references/extra.md").is_file()
    set_kinds(empty_repo, "bug", "chore")
    report = upgrade(empty_repo, capsys=capsys)
    assert ".claude/skills/taskrail-feature/references/extra.md" in report["removed"]
    assert not (empty_repo / ".claude/skills/taskrail-feature").exists()


# --- 4. Agent notes are per skill ------------------------------------------------------------------


def core_source() -> str:
    return (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")


def test_with_claude_each_skill_gets_only_its_own_notes(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    skills = empty_repo / ".claude/skills"
    assert (skills / "taskrail/SKILL.md").read_text() == core_source().replace(install.HARNESS_MARKER, CORE_CLAUDE_NOTES)
    autopilot = (skills / SKILL / "SKILL.md").read_text()
    assert "## On Claude Code" in autopilot and "## On OpenCode" not in autopilot
    assert "SendMessage" in autopilot and "Agent tool" in autopilot
    assert "SendMessage" not in (skills / "taskrail/SKILL.md").read_text()
    for kind in ("bug", "chore", "feature", "spike"):
        assert "## On " not in (skills / f"taskrail-{kind}/SKILL.md").read_text()
    for path in skills.rglob("*.md"):
        assert "<!-- taskrail:" not in path.read_text(), path


def test_with_opencode_alone_the_autopilot_skill_gets_its_opencode_notes(empty_repo, capsys):
    init(empty_repo, "--integration", "opencode", capsys=capsys)
    skills = empty_repo / ".opencode/skills"
    assert (skills / "taskrail/SKILL.md").read_text() == core_source().replace(install.HARNESS_MARKER, CORE_OPENCODE_NOTES)
    autopilot = (skills / SKILL / "SKILL.md").read_text()
    assert "## On OpenCode" in autopilot and "## On Claude Code" not in autopilot
    assert "task_id" in autopilot and "waves" in autopilot


def test_with_both_integrations_the_shared_copy_carries_both_agents_notes(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", "--integration", "opencode", capsys=capsys)
    skills = empty_repo / ".claude/skills"
    expected_core = core_source().replace(install.HARNESS_MARKER, CORE_CLAUDE_NOTES + "\n\n" + CORE_OPENCODE_NOTES)
    assert (skills / "taskrail/SKILL.md").read_text() == expected_core
    autopilot = (skills / SKILL / "SKILL.md").read_text()
    assert autopilot.index("## On Claude Code") < autopilot.index("## On OpenCode")
    assert "SendMessage" in autopilot and "task_id" in autopilot


@pytest.mark.parametrize(("integrations", "skills_dir"), [(["opencode"], ".opencode/skills"), (["claude", "opencode"], ".claude/skills")])
def test_opencode_note_ends_the_turn_at_an_escalation_and_checks_lanes_between_batches(empty_repo, capsys, integrations, skills_dir):
    # T033 F3: blocking task calls left the human no point at which to answer an escalation.
    init(empty_repo, *[arg for name in integrations for arg in ("--integration", name)], capsys=capsys)
    skills = empty_repo / skills_dir
    autopilot = (skills / SKILL / "SKILL.md").read_text()
    note = flat(re.search(r"^## On OpenCode\n.*?(?=^## |\Z)", autopilot, re.MULTILINE | re.DOTALL).group(0))
    for phrase in (
        "end your turn with that question",
        "never start another batch of blocking task calls in the same turn",
        "resume the other lanes in the batch that follows the human's reply",
        "when a batch returns, before anything else, record the handle of every lane it started with `autopilot lane --handle`",
        "run `autopilot status --run <r> --json` and deal with every `silent` lane before you start the next batch",
    ):
        assert phrase in note, phrase
    core = flat((skills / "taskrail/SKILL.md").read_text())
    assert "blocking task calls" not in core and "`silent`" not in core


# --- 5. The portable text names no agent -----------------------------------------------------------


@pytest.mark.parametrize("name", FILES)
def test_portable_text_names_no_agent_or_agent_tool(name):
    text = source(name)
    for word in ("Claude", "OpenCode", "AskUserQuestion", "SendMessage", "Agent tool", "task_id", "subagent"):
        assert word.lower() not in text.lower(), f"{name} names {word}"


# --- 6. Frontmatter and description ----------------------------------------------------------------


def test_description_says_what_and_only_on_an_explicit_request_with_a_count():
    frontmatter = source("SKILL.md").split("---\n")[1]
    assert re.search(r"^name: taskrail-autopilot$", frontmatter, re.MULTILINE)
    description = flat(re.search(r"^description: (.+)$", frontmatter, re.MULTILINE).group(1))
    assert len(description) <= 1024
    assert "lanes" in description and "gates" in description
    assert "only when the human explicitly asks" in description
    assert "number of tasks" in description


# --- 7. Only when asked; stop on exit 5 ------------------------------------------------------------


def test_skill_runs_only_when_asked_with_a_count_and_stops_on_exit_5():
    text = flat(source("SKILL.md"))
    assert "only when the human explicitly asks for it and gives a task count" in text
    assert "never start the autopilot on your own initiative" in text
    assert "taskrail autopilot start --count" in text
    assert "exits 5" in text and "stop and report" in text
    assert "never change `[autopilot].enabled` yourself" in text


# --- 8. The lane brief carries the lane contract ---------------------------------------------------


def test_lane_brief_carries_the_lane_contract_and_placeholders():
    text = flat(source("references/lane-brief.md"))
    for phrase in (
        "the `taskrail` skill",
        "executor skill",
        "claim <id> --run <run>",
        "end your turn with the full gate report",
        "continue <id>",
        "never run `taskrail review <id> --publish`",
        "never merge",
        "never start shared services",
        "never touch another lane's worktree",
        "taskrail review <id> --json",
        "do not rebase",
    ):
        assert phrase in text, phrase
    for placeholder in ("<ID>", "<RUN>", "<BRANCH>", "<WORKTREE>", "<BASE>", "<ENVIRONMENT>", "<DECISIONS>", "<OTHER_LANES>", "<TOUCH_MAP>"):
        assert placeholder in source("references/lane-brief.md"), placeholder


# --- 9. Gate criteria per gate type ----------------------------------------------------------------


def test_gate_review_covers_every_gate_type_with_its_criteria():
    raw = source("references/gate-review.md")
    headings = flat(" ".join(re.findall(r"^## (.+)$", raw, re.MULTILINE)))
    for stage in ("plan", "scope", "diagnose", "frame", "decide", "implement", "fix", "verify", "close", "rebase"):
        assert stage in headings, stage
    text = flat(raw)
    for phrase in (
        "governing documents first",
        "never approve with failing checks",
        "read the diff",
        "commit range",
        "re-run the checks in the lane's worktree",
        "observed failing",
        "real runtime",
        "premise",
        "no upstream",
    ):
        assert phrase in text, phrase


# --- 10. Decision records --------------------------------------------------------------------------


def test_decision_record_template_has_the_design_structure():
    raw = source("references/decision-record.md")
    text = flat(raw)
    assert "recorded before it is given" in text
    for heading in ("## <stage> gate", "## Conflict handling agreed for all lanes", "## rebase after", "## escalated to the human"):
        assert heading in raw, heading
    assert "Reviewed:" in raw
    assert raw.count("| # | Question | Options | Decision | Reason |") >= 3
    assert "File | Conflict | Resolution" not in raw
    assert "only while the lane is stopped" in text
    assert "decisions_index" in raw


# --- 11. Escalation, conflict classes, hand-off ----------------------------------------------------


def test_skill_lists_escalations_conflict_classes_and_hand_off():
    text = flat(source("SKILL.md"))
    for phrase in (
        "governing",
        "escalate_gates",
        "reserve the decision to humans",
        "contradict each other",
        "outside the known classes",
        "false premise",
        "diverged",
    ):
        assert phrase in text, phrase
    for phrase in ("united by id", "reopens:", "changelog bullets", "taskrail upgrade --force", "anything else escalates"):
        assert phrase in text, phrase
    for phrase in ("one branch at a time", "taskrail autopilot merged <id> --cleanup", "git rebase --onto", "never merge"):
        assert phrase in text, phrase
    for name in REFERENCES:
        assert name in text, name


def test_skill_records_the_close_stop_as_a_gate():
    """T050: the close section records the stop after done with `lane --gate close` before reviewing it."""
    text = source("SKILL.md")
    close = flat(text[text.index("## Close and hand off") : text.index("## After a merge")])
    assert "taskrail autopilot lane <id> --run <r> --state gate --gate close" in close


def test_governing_escalates_by_its_reason_and_the_close_review_checks_the_paths():
    """T049: `status` drops `governing` from `escalation` at `done-branch`; the close review covers the paths."""
    escalate = flat(re.search(r"^## Escalate$(.*?)^## ", source("SKILL.md"), re.MULTILINE | re.DOTALL).group(1))
    condition = re.search(r"1\. (.*?)2\. ", escalate).group(1)
    assert "governing path" in condition and "`governing` in `escalation`" in condition
    close = flat(re.search(r"^## Close$(.*?)^## ", source("references/gate-review.md"), re.MULTILINE | re.DOTALL).group(1))
    assert "`governing_touched`" in close and "escalates" in close


# --- 11b. Skill text found wrong in the T033 trial (T055) --------------------------------------------


def section(text: str, heading: str) -> str:
    """The whitespace-collapsed body of `## <heading>`, up to the next `## ` heading or a `---` rule."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |^---$|\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"no section {heading!r}"
    return flat(match.group(1))


@pytest.fixture(params=["source", "claude", "opencode"])
def autopilot_copy(request, empty_repo, capsys):
    """A reader of one autopilot skill file: the shipped source, or the copy `init` installs for an integration."""
    if request.param == "source":
        return source
    init(empty_repo, "--integration", request.param, capsys=capsys)
    skills = empty_repo / (".claude/skills" if request.param == "claude" else ".opencode/skills")
    return lambda name: (skills / SKILL / name).read_text(encoding="utf-8")


def test_hand_off_message_carries_branch_title_body_and_link(autopilot_copy):
    """T033 F4: the first hand-off reached the human without the branch or the title."""
    close = section(autopilot_copy("SKILL.md"), "Close and hand off")
    for phrase in ("the branch", "`pull_request.title`", "`pull_request.body`", "`pull_request.url`", "never send one"):
        assert phrase in close, phrase


def test_refill_runs_once_a_close_is_reviewed_not_at_hand_off(autopilot_copy):
    """T033 F5: a lane is free at `done-branch`, but the skill refilled only after the hand-off."""
    text = autopilot_copy("SKILL.md")
    dispatch = section(text, "Dispatch")
    assert "without waiting for its hand-off" in dispatch
    assert "`done-branch`" in dispatch
    close = section(text, "Close and hand off")
    assert "values that no lane in use holds" in close
    assert "resource values as at hand-off" in section(text, "After a merge")
    # T066: chosen values go through `--resource`, not an environment prefix (T033 F11).
    assert "`taskrail checks <id> --resource name=value`" in close  # `section` lowercases
    assert "set as `taskrail_resource_<name>`" not in close
    assert "adding `--resource name=value` for each value the lane no longer holds" in section(
        autopilot_copy("references/gate-review.md"), "Rebase: at hand-off or after a merge"
    )


def test_task_ids_are_unique_across_lanes(autopilot_copy):
    """T033 F6: a run decision assumed each branch allocates IDs from its own backlog."""
    dispatch = section(autopilot_copy("SKILL.md"), "Dispatch")
    for phrase in ("`taskrail new` reserves each id", "lock shared by every worktree of the clone", "never forbid lanes to create tasks"):
        assert phrase in dispatch, phrase
    assert "`taskrail new` are reserved across every worktree" in section(autopilot_copy("references/lane-brief.md"), "How to work")


def test_a_dispatch_expires_after_the_claim_grace(autopilot_copy):
    """T033 F7: the skill never said that an unclaimed dispatch stops holding its lane."""
    dispatch = section(autopilot_copy("SKILL.md"), "Dispatch")
    for phrase in ("a dispatch expires", "`[git].claim_grace_minutes`", "reads `pending` again", "may dispatch it again"):
        assert phrase in dispatch, phrase


def test_a_new_session_resumes_a_run_by_handle_and_restarts_from_the_branch(autopilot_copy):
    """T033 F2: a new session restarted a lane from its branch, with no procedure in the skill."""
    resume = section(autopilot_copy("SKILL.md"), "Resume a run")
    for phrase in (
        "never runs `autopilot start`",
        "by the handle",
        "restart the lane from its branch",
        "only once `status` reports it `silent`",
        "restart workspace section",
        "taskrail autopilot lane <id> --run <r> --handle <h> --state running",
    ):
        assert phrase in resume, phrase
    brief = autopilot_copy("references/lane-brief.md")
    restart = section(brief, "Workspace (restart from the branch)")
    for phrase in ("already exist", "do not stop because the branch exists", "claim <id> --run <run>", "resume point: <resume_point>", "never discard"):
        assert phrase in restart, phrase
    assert "everything between the two rules is the brief" in flat(brief)


def test_an_approved_governing_edit_is_recorded_and_the_close_review_reads_it():
    """T059: the orchestrator records an approved governing edit; the close review uses `governing_approved`."""
    escalate = flat(re.search(r"^## Escalate$(.*?)^## ", source("SKILL.md"), re.MULTILINE | re.DOTALL).group(1))
    condition = re.search(r"1\. (.*?)2\. ", escalate).group(1)
    assert "governing path not yet approved" in condition
    assert "taskrail autopilot approve-governing <id> --run <r>" in escalate
    assert "a later change to an approved file flags it again" in escalate
    close = flat(re.search(r"^## Close$(.*?)^## ", source("references/gate-review.md"), re.MULTILINE | re.DOTALL).group(1))
    assert "`governing_approved`" in close


def test_a_discarded_branch_is_handed_off_like_a_done_one(autopilot_copy):
    """T065: a task discarded on its branch is queued, handed off as a chore and read through `handoff.in_review`."""
    text = autopilot_copy("SKILL.md")
    close = section(text, "Close and hand off")
    for phrase in ("stops after `taskrail discard`", "`discarded-branch`", "`--type chore`", "`handoff.in_review` says it is in review"):
        assert phrase in close, phrase
    assert close.index("stops after `taskrail discard`") < close.index("1. in the lane's worktree")
    escalate = section(text, "Escalate")
    assert "until the task is `done-branch` or `discarded-branch`" in re.search(r"1\. (.*?)2\. ", escalate).group(1)
    assert "a `done-branch` or `discarded-branch` task in `handoff.queue` has its close reviewed" in section(text, "Resume a run")
    close_review = flat(re.search(r"^## Close$(.*?)^## ", autopilot_copy("references/gate-review.md"), re.MULTILINE | re.DOTALL).group(1))
    assert "no longer flags a `done-branch` or `discarded-branch` task" in close_review


def test_skill_starts_from_several_unmerged_dependencies_only_on_explicit_instruction():
    text = flat(source("SKILL.md"))
    assert "several unmerged dependencies" in text
    assert "only on the human's explicit instruction" in text
    assert "--ignore-deps --run" in text
    assert "fork point" in text


# --- 12. Commands shown exist in the CLI -----------------------------------------------------------


def subparsers(parser):
    return next(action for action in parser._actions if action.__class__.__name__ == "_SubParsersAction").choices


def shown_commands() -> list[tuple[str, str]]:
    spans: list[str] = []
    for name in FILES:
        text = source(name)
        spans += re.findall(r"`([^`\n]+)`", text)
        for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.DOTALL):
            spans += block.splitlines()
    return [(span, match) for span in spans for match in re.findall(r"(?<![\w/-])taskrail ((?:autopilot )?[a-z][a-z-]*[^`]*)", span)]


def test_every_taskrail_command_and_flag_shown_exists():
    top = subparsers(build_parser())
    autopilot = subparsers(top["autopilot"])
    shown = shown_commands()
    assert shown, "the skill shows no taskrail command"
    used: set[str] = set()
    for span, command in shown:
        words = command.split()
        if words[0] == "autopilot":
            assert len(words) > 1 and words[1] in autopilot, span
            used.add(words[1])
            parser = autopilot[words[1]]
        else:
            assert words[0] in top, span
            parser = top[words[0]]
        for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", command):
            assert flag in parser._option_string_actions, f"{flag} in `{span}`"
    assert used == set(autopilot), sorted(set(autopilot) - used)


# --- 13. Command shape and `taskrail checks` (T052) ------------------------------------------------


def test_claude_notes_on_command_shape_and_checks_reach_the_installed_copies(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    skills = empty_repo / ".claude/skills"
    core = flat((skills / "taskrail/SKILL.md").read_text())
    for phrase in (
        "one command per bash call",
        "`git -c <worktree>` or `taskrail --root <worktree>` instead of `cd <worktree> && …`",
        "checks each part of a compound command on its own",
        "run a task's checks with `taskrail checks <id>`",
    ):
        assert phrase in core, phrase
    autopilot = flat((skills / SKILL / "SKILL.md").read_text())
    for phrase in ("one command per bash call", "rather than `cd … &&`", "re-run a lane's checks at a gate or at hand-off with `taskrail checks <id>`"):
        assert phrase in autopilot, phrase


def test_every_taskrail_command_and_flag_in_the_claude_notes_exists():
    top = subparsers(build_parser())
    text = (install.SKILLS_SOURCE.parent / "integrations/claude.md").read_text(encoding="utf-8")
    shown = [m for span in re.findall(r"`([^`\n]+)`", text) for m in re.findall(r"(?<![\w/-])taskrail (--root <[a-z]+> )?([a-z][a-z-]*)([^`]*)", span)]
    assert ("", "checks", " <ID>") in shown
    for root, command, rest in shown:
        assert command in top, command
        for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", rest):
            assert flag in top[command]._option_string_actions, flag
    assert "--root" in build_parser()._option_string_actions


def test_the_brief_and_the_re_run_steps_name_taskrail_checks(autopilot_copy):
    """T063 (T052 D7): the lane brief and every step that re-runs a lane's checks name `taskrail checks <ID>`."""
    brief = autopilot_copy("references/lane-brief.md")
    for heading in ("Workspace", "Workspace (restart from the branch)"):
        workspace = section(brief, heading)
        assert "run your checks with `taskrail checks <id>`" in workspace, heading
        assert "`taskrail checks` passes them to the checks itself" in workspace, heading
        assert "every command that runs the checks" not in workspace, heading
    skill = autopilot_copy("SKILL.md")
    close = section(skill, "Close and hand off")
    assert "re-run the checks with `taskrail checks <id>`" in close
    assert "with `taskrail checks <id> --resource name=value`" in close  # T066 replaced the environment prefix
    assert "`taskrail checks <id>` for that dependent" in section(skill, "After a merge")
    review = autopilot_copy("references/gate-review.md")
    assert "yourself with `taskrail checks <id>`" in section(review, "Every gate")
    assert "re-run the checks with `taskrail checks <id>`" in section(review, "Rebase: at hand-off or after a merge")


def test_core_skill_runs_stage_checks_with_taskrail_checks_and_documents_exit_6():
    text = (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")
    stages = flat(text[text.index("5. **Stages.**") : text.index("6. **Scope.**")])
    assert "run its checks with `taskrail checks <id> --stage <stage>`" in stages
    assert "| 6 | a check failed |" in text
    assert "--stage" in subparsers(build_parser())["checks"]._option_string_actions


# --- 14. Named runs, extending a run and prepared workspaces (T071) --------------------------------


def test_named_runs_extended_runs_and_prepared_workspaces(autopilot_copy):
    """T071: the human names the tasks or adds them to a live run; a branch `new --workspace` prepared is not prior work."""
    skill = autopilot_copy("SKILL.md")
    description = flat(re.search(r"^description: (.+)$", skill, re.MULTILINE).group(1))
    assert "gives the number of tasks to complete or names the tasks" in description
    when = section(skill, "When to run")
    for phrase in (
        "gives a task count or names the tasks",
        "taskrail autopilot start --tasks <ids> --json",
        "in the order they gave",
        "extend that run rather than starting another",
        "taskrail autopilot extend <r> --tasks <ids> --json",
        "taskrail autopilot extend <r> --count <n> --json",
        "extending also needs the human's explicit request",
        "`taskrail branch <id> <name>`",
    ):
        assert phrase in when, phrase
    dispatch = section(skill, "Dispatch")
    assert "`prior_work.prepared`" in dispatch and "prepared workspace section" in dispatch

    brief = autopilot_copy("references/lane-brief.md")
    assert "the prepared workspace section after it instead" in flat(brief)
    assert "if the branch already exists, stop and report" in section(brief, "Workspace")
    prepared = section(brief, "Workspace (prepared by taskrail new --workspace)")
    for phrase in (
        "already exist",
        "hold only the task's row (<row>)",
        "do not stop because the branch exists",
        "commit it on its own",
        "claim <id> --run <run>",
        "run your checks with `taskrail checks <id>`",
        "`taskrail checks` passes them to the checks itself",
    ):
        assert phrase in prepared, phrase


def test_core_skill_reads_a_prepared_workspace_as_no_prior_work():
    text = (install.SKILLS_SOURCE / "taskrail/SKILL.md").read_text(encoding="utf-8")
    inspect = flat(text[text.index("2. **Inspect.**") : text.index("3. **Workspace.**")])
    assert "`prior_work.prepared` set means the branch is the workspace `taskrail new --workspace` prepared" in inspect
