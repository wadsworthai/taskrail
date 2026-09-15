# T052 — Add taskrail checks for a task and a Claude Code note on command shape

Kind: feature · Epic: E02 · Status: verified (plan and implementation approved: D1–D7 as recommended; D4, D5 and
D6 applied as written; D7 opened as T063). Record:
`docs/autopilot/decisions/T052-add-taskrail-checks-for-a-task-and-a-cla.md`.

Source: finding F11 of `docs/spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md`: permission
prompts dominated the Claude Code run, because the orchestrator and the lanes used compound
commands (`cd … &&`, shell variables, `$?`, heredocs) that a shared allowlist cannot match, and
Claude Code checks each part of a compound command on its own.

## Today

- A lane runs a check as the stage's `checks` map gives it (`uv run
  pytest -q` here), and it has to be run from the task's worktree root, with the lane's
  `TASKRAIL_RESOURCE_<NAME>` values in the environment. From a shell that does not start in the
  worktree that means `cd <worktree> && TASKRAIL_RESOURCE_PORT=… <command>` — a compound command
  with a variable, one per check, different for every lane, which no single allowlist entry covers.
- The orchestrator re-runs a lane's checks at a gate and at hand-off (§12.7, §12.8) the same way.
- No shipped text tells a Claude Code agent how to shape its commands; the `claude` integration
  notes cover asking, subagents, worktrees and lane handles only.

## Behaviour

After this change:

- **`taskrail checks <ID> [--stage STAGE] [--check NAME]… [--json]`** runs a task's configured checks
  in the task's worktree, from any directory of the clone, as one command:
  - **Which checks:** by default every check named by the task's kind's stages that apply to the
    task, in stage order, each name once — the same set as `show`'s `checks` map. `--stage STAGE`
    narrows to that stage's checks; `--check NAME` (repeatable) narrows to those names. A named
    check that `[checks]` does not define is reported `not configured` and not run, as the core
    skill already asks ("say so if a check is not configured"); it does not fail the command.
  - **Where:** the worktree recorded in the task's claim when that directory exists, otherwise the
    worktree that has the task's branch checked out (`git worktree list`). The commands and the
    kind come from that worktree's own `.taskrail/config.toml`, so a branch that changes its checks
    runs its own (D2).
  - **Resources:** the values its autopilot lane holds — the lane in the claim's run, or, once
    `done` has released the claim, the newest run that lists the task — passed as
    `TASKRAIL_RESOURCE_<NAME>` on top of the inherited environment. No run, or released values,
    means no extra variables. The command reads run files and never writes them.
  - **How:** each command through the platform shell (as `[checks]` holds shell strings), with the
    worktree as working directory. Every selected check runs even after one fails, so one call
    reports them all.
  - **Output:** in text mode each check's output passes straight through, preceded by a line
    naming the check and its command, and followed by a summary line per check. With `--json`,
    stdout is one JSON document — `id`, `worktree`, `run`, `resources`, `environment`, `stage`,
    `checks` (each `name`, `command`, `status` `passed`/`failed`/`not-configured`, `exit`, and
    `output`, the check's combined stdout and stderr) and `passed` (D3).
  - **Exit codes:** 0 when every check that ran passed (none ran counts as 0); **6** when any
    check failed (D1); 1 for an invalid backlog (as every command, `--allow-invalid` to skip);
    2 for an unknown `--stage`; 3 for an unknown task; 5 when the task has no worktree to run in,
    naming why (no claim with an existing worktree, and its branch is not checked out anywhere).
- **Claude Code integration notes** (exact text in D4) tell an agent, in the `taskrail` skill, to
  shape shell commands for an allowlist — one command per call, absolute paths, `git -C <worktree>`
  and `taskrail --root <worktree>` instead of `cd … &&` chains, no shell variables, `$?`, pipes or
  heredocs — and to run a task's checks with `taskrail checks <ID>`; and, in the
  `taskrail-autopilot` skill, to use the same shape itself and to re-run a lane's checks with that
  command.

## Acceptance criteria

1. In a fixture repository with a task claimed in its worktree, `taskrail --root <main checkout>
   checks T001 --json` runs every check of the kind's stages in the worktree (a check that writes
   `pwd` shows the worktree path) and exits 0 when they pass; `checks` lists each with `status`,
   `exit` and `output`, and a stage check `[checks]` does not define is `not-configured` and does
   not change the exit code.
2. A failing check makes the command exit 6, with `passed: false` and that check `failed` with its
   exit code, and the checks after it still run.
3. `--stage implement` runs only that stage's checks; `--check NAME` runs only the named ones;
   an unknown stage exits 2.
4. A task claimed with `--run R` whose lane holds resources runs its checks with
   `TASKRAIL_RESOURCE_<NAME>` set to those values (a check echoes them), and `resources` /
   `environment` report them. After `done` releases the claim, the values recorded in the run are
   still used.
5. The worktree's own `.taskrail/config.toml` decides the command: a check redefined on the task's
   branch runs in its branch form when invoked from the main checkout.
6. With no claim and no worktree that has the task's branch checked out, the command exits 5 and
   runs nothing; an unknown task exits 3.
7. Text mode (no `--json`) shows each check's output and a summary line, with the same exit codes.
8. The `claude` integration installs the command-shape note and the `taskrail checks <ID>` note
   into the installed `taskrail` and `taskrail-autopilot` skills (a test runs `init --integration
   claude` on a fixture and asserts the text in the installed copies), and not into an
   `opencode`-only install; every `taskrail` command and flag the notes show exists in the parser.

## Tests per criterion

All in `tests/`. Each was observed failing before the implementation: the seven
`test_checks.py` tests with `argparse.ArgumentError: argument command: invalid choice: 'checks'`
(exit 2), the note tests with the text missing from the installed copies and from `claude.md`, and
the core-skill test with the step 5 sentence missing.

| Criterion | Test |
|-----------|------|
| 1 | `test_checks.py::test_runs_every_stage_check_in_the_worktree_from_the_main_checkout` (a local `feature` kind with checks in two stages: order `test, lint, smoke, missing`, `pwd` is the worktree, stderr captured, `missing` is `not-configured`, exit 0) |
| 2 | `test_checks.py::test_a_failing_check_exits_6_and_the_later_checks_still_run` (`exit 3` check: `failed`, exit 6, the checks after it `passed`) |
| 3 | `test_checks.py::test_stage_and_check_narrow_the_selection` (`--stage implement`, `--check smoke --check test` in stage order, a stage with no checks, unknown stage exit 2 naming the stages, a `--check` outside the stage exit 2) |
| 4 | `test_checks.py::test_the_lane_resources_reach_the_checks_before_and_after_done` (`autopilot next` gives T004 `PORT=5433`; the check echoes it while claimed and again after `done` and its commit) |
| 5 | `test_checks.py::test_the_worktree_configuration_decides_the_commands` (an uncommitted config change in the worktree wins when invoked with `--root` at the main checkout) |
| 6 | `test_checks.py::test_no_worktree_exits_5_and_an_unknown_task_exits_3` (unclaimed T003: exit 5 naming its branch, the check did not run; T999: exit 3) |
| 7 | `test_checks.py::test_text_mode_streams_each_check_and_summarises` (headers, streamed output, `missing: not configured`, `passed …` lines; a failing check from the worktree's own kind prints `failed broken (exit 3)` and exits 6) |
| 8 | `test_autopilot_skill.py::test_claude_notes_on_command_shape_and_checks_reach_the_installed_copies` (`init --integration claude`: phrases in the installed `taskrail` and `taskrail-autopilot` skills); `test_with_claude_each_skill_gets_only_its_own_notes` and `test_with_both_integrations_the_shared_copy_carries_both_agents_notes` (the exact installed core skill, `CORE_CLAUDE_NOTES` extended); `test_with_opencode_alone_the_autopilot_skill_gets_its_opencode_notes` (unchanged: an opencode-only copy is exactly the source plus the OpenCode notes, so it carries none of these); `test_every_taskrail_command_and_flag_in_the_claude_notes_exists`; and for D6 `test_core_skill_runs_stage_checks_with_taskrail_checks_and_documents_exit_6` |

This repository's own installed copies (`.claude/skills/taskrail/SKILL.md`,
`.claude/skills/taskrail-autopilot/SKILL.md`, `.taskrail/installed.json`) were updated with
`taskrail upgrade`.

Implementation details the plan left open:

- `--stage` runs that stage's checks even when the stage does not apply to the task (an explicit
  request); the default set skips stages whose `applies` is false.
- A `--check` name that is not among the selected stages' checks exits 2, listing the ones that are,
  so a typo is not silently a pass.
- A task whose kind is not defined in the worktree's configuration exits 2.
- In text mode each check's output is inherited by the terminal, not captured, so long runs stream.

## Verify

The real CLI from this branch (`<worktree>/.taskrail/bin/taskrail`, pinned to the branch's source),
invoked with `--root` at this repository's main checkout, so neither the shell nor the `--root`
pointed at the worktree. T052 was claimed in run `20260914-1` with no resources configured.

```text
$ taskrail --root <main checkout> checks T052 --stage implement --json      # exit 0
"worktree": "<main checkout>/.worktrees/T052-add-taskrail-checks-for-a-task-and-a-cla",
"run": "20260914-1", "resources": {}, "environment": {}, "stage": "implement",
"checks": [
  {"name": "test", "command": "uv run pytest -q", "status": "passed", "exit": 0,
   "output": "…841 passed in 87.55s (0:01:27)…"},
  {"name": "lint", "command": null, "status": "not-configured", "exit": null, "output": null}],
"passed": true

$ taskrail --root <main checkout> checks T052 --stage implement              # exit 0
== test: uv run pytest -q
…841 passed in 86.15s (0:01:26)
== lint: not configured
passed test
not configured lint
T052 in <main checkout>/.worktrees/T052-add-taskrail-checks-for-a-task-and-a-cla: passed

$ taskrail --root <main checkout> checks T057 --json
taskrail: T057 has no worktree to run its checks in: no claim records an existing worktree, and its branch `T057-check-autopilot-compaction-and-old-lane` is not checked out in any worktree
exit=5
```

No gap against the plan. The captured output carries pytest's colour codes because the agent's
shell exports `FORCE_COLOR=3`, which the check inherits along with the rest of the environment,
as §7.5 says.

## Affected areas

- `src/taskrail/checks.py` (new) — choosing the checks, finding the worktree and
  the lane's resources, running them.
- `src/taskrail/cli.py` — `EXIT_CHECK_FAILED = 6`, `cmd_checks`, and the `checks`
  parser registration (a new top-level command; `cmd_claim` is not touched).
- `src/taskrail/autopilot/dispatch.py` — none; `ENVIRONMENT_PREFIX` is imported
  from it, not changed.
- `src/taskrail/integrations/claude.md` — the two notes (D4).
- `.claude/skills/taskrail/SKILL.md`, `.claude/skills/taskrail-autopilot/SKILL.md` and
  `.taskrail/installed.json` — through `taskrail upgrade`.
- `tests/test_checks.py` (new) for criteria 1–7; `tests/test_autopilot_skill.py`
  (`CORE_CLAUDE_NOTES` and a new test) for criterion 8.
- `DESIGN.md` §7 (CLI table row and a *Checks* subsection) and §8 (the `claude`
  integration row) — governing, exact text in D5. Only if approved: the core `taskrail` skill
  (D6).
- `README.md` (one line in its command list), `CHANGELOG.md` (one
  *Unreleased* bullet), `docs/features/README.md` (index row).

## Out of scope

- The lane brief template (`references/lane-brief.md`) and the `taskrail-autopilot` portable
  text, which T055 is rewriting (D7).
- An allowlist or permission profile shipped as adapter packaging, and any change to agent
  settings (T033's *What would change the decision*).
- Changing the `.taskrail/bin/taskrail` wrapper to find the root from its own path.
- Timeouts, parallel checks, or a fail-fast flag.
- The OpenCode integration note (T056's area).

## Open questions and risks

- **D1 — exit code for a failing check.** Recommendation: a new exit 6, "a check failed", so an
  agent never confuses it with 1 (the core skill says exit 1 means "run `taskrail validate`, report
  the errors, stop"). Alternatives: exit 1 (reuses "fails validation"), or the failing check's own
  exit code (collides with taskrail's codes).
- **D2 — whose configuration defines the checks.** Recommendation: the task worktree's own
  `.taskrail/config.toml` and kinds, falling back to the invoking checkout's when the worktree has
  none, so a branch runs its own checks, as this repository's pin runs a branch's own code.
  Alternative: always the invoking checkout's configuration (simpler, but the main checkout's
  wrapper would then run the mainline's checks against a branch that changed them).
- **D3 — check output with `--json`.** Recommendation: capture each check's combined output into
  `output`, so stdout stays one parseable document and the output is evidence in the result.
  Alternative: stream check output to stderr and keep only statuses in the JSON (lower memory,
  but output and result arrive on different streams).
- **D4 — the exact integration note text** (`src/taskrail/integrations/claude.md`,
  free in the touch map). Recommendation: approve as written.
  - Appended to the `taskrail` section:
    ```markdown
    - Shape every shell command so a permission allowlist can match it: one command per Bash
      call, the taskrail wrapper and files by absolute path, and `git -C <worktree>` or
      `taskrail --root <worktree>` instead of `cd <worktree> && …`. Avoid `&&`, `;` and `|`
      chains, shell variables, `$?` and heredocs, and edit files with the Edit tool: Claude Code
      checks each part of a compound command on its own, so it asks for permission even when
      every part is allowed.
    - Run a task's checks with `taskrail checks <ID>`, adding `--stage <stage>` for one stage's
      checks, rather than changing into its worktree: it runs them there, with the task's
      autopilot resources, as one command that a single allowlist entry covers.
    ```
  - Appended to the `taskrail-autopilot` section:
    ```markdown
    - Use the command shape of the `taskrail` skill's Claude Code notes yourself — one command
      per Bash call, absolute paths, `git -C` and `taskrail --root` rather than `cd … &&` — and
      re-run a lane's checks at a gate or at hand-off with `taskrail checks <ID>`, which runs them
      in its worktree with its resources.
    ```
  Alternative: only the `taskrail` section (the orchestrator loads that skill too, but would not
  be reminded about re-running lane checks).
- **D5 — DESIGN.md text (governing).** Recommendation: approve as written.
  - §7 CLI table, a row after the `taskrail review` row:
    ```markdown
    | `taskrail checks <ID> [--stage STAGE] [--check NAME]…` | Run a task's configured checks in its worktree with its autopilot lane's resources, from anywhere in the clone (§7.5) |
    ```
  - A new subsection after §7.4:
    ```markdown
    ### 7.5 Checks

    `taskrail checks <ID>` runs the checks named by the stages of the task's kind that apply to it —
    in stage order, each once, the same set as `show`'s `checks` — or only those of `--stage`, or
    only the `--check` names. It runs them in the task's worktree: the one its claim records when
    that directory exists, else the one that has its branch checked out; the commands and kinds
    come from that worktree's own configuration. Each runs through the platform shell with the
    worktree as working directory and, when an autopilot run lists the task (the claim's run, else
    the newest run), its lane's resource values as `TASKRAIL_RESOURCE_<NAME>` (§12.7). Every
    selected check runs; one that `[checks]` does not define is reported `not-configured` and does
    not fail. `--json` returns each check's `name`, `command`, `status`, `exit` and combined
    `output`, with `worktree`, `run`, `resources`, `environment` and `passed`. Exit 0 when every
    check that ran passed, 6 when one failed, 2 for an unknown stage, 3 for an unknown task, 5 when
    the task has no worktree. It reads run files and never writes them, so one allowlist entry
    covers a lane's checks without `cd` or variables in the command.
    ```
  - §8 *Integrations* table, `claude` row: the *Notes in `taskrail`* cell becomes
    "ask with AskUserQuestion; create task worktrees with git rather than subagent isolation; one
    allowlistable command per call, without `cd … &&` chains, and `taskrail checks`", and the
    *Notes in `taskrail-autopilot`* cell becomes "lanes are background subagents resumed with
    `SendMessage`; the model per lane; no timer; the same command shape, and lane checks re-run
    with `taskrail checks`". The `opencode` row is unchanged.
  Alternative: the §7 row only, without §7.5 (the behaviour would then live only in `--help`).
- **D6 — name the command in the core `taskrail` skill (portable text).** Proposed: in step 5
  *Stages*, replace "run each of its `checks` with the command from the `checks` map (say so if a
  check is not configured)" with "run its checks with `taskrail checks <ID> --stage <stage>`, which
  runs each command from the `checks` map in the task's worktree and reports one it does not
  define as not configured (say so)", and add `| 6 | a check failed | report the failing check's
  output; fix it or stop at the gate |` to the exit-code table. Recommendation: yes — it is the
  agent-neutral place where every executor reads how to run checks, and the area is free in the
  touch map. Alternative: leave the core skill as is and rely on the Claude Code note.
- **D7 — the lane brief and `taskrail-autopilot` skill text.** The brief's "Checks: `<command>`,
  run from the worktree root" line would read better as "Checks: `taskrail checks <ID>`". T055
  rewrote `references/lane-brief.md`, so this lane should not touch it. Recommendation: open a
  follow-up chore after T055 merges — "Name `taskrail checks` in the lane brief and the
  autopilot skill's re-run steps", verified by a `test_autopilot_skill.py` assertion on the shipped
  text. Alternative: the orchestrator folds the sentence in at hand-off.
- **Risk — allowlist prefix per worktree.** A lane calling its own worktree's wrapper still has a
  different absolute path per lane; the note fixes the shape, but an allowlist entry has to match
  each worktree's path (or the main checkout's wrapper, which `checks` makes sufficient, since it
  finds the worktree itself). The note does not promise a single literal entry for every lane.
- **Risk — installed copies.** `.claude/skills/*` and `.taskrail/installed.json` are also rewritten
  by other lanes' `taskrail upgrade`; a conflict there is regenerated by re-running `upgrade` after
  the rebase.
