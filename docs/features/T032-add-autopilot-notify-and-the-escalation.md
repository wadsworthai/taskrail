# T032 — Add autopilot notify and the escalation flags in autopilot status

Kind: feature · Epic: E02 · Status: verified (plan approved as recommended, D1–D9)

Source: the accepted autopilot design, `DESIGN.md` §12.1 (the `autopilot notify`
row) and §12.6 (*Escalation, notification and supervision*), and the evidence behind it in
`docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md` §5. Builds on T029: run files and
`lane` (`autopilot/runs.py`), `touched` per lane in `autopilot/status.py`, `register()` in
`autopilot/commands.py`, and `AutopilotConfig`, which already parses and checks `governing`,
`escalate_gates` (shaped `kind:stage`), `notify` and `notify_on` (`escalation`, `lane-done`,
`lane-failed`). The questions this plan needs settled are D1–D8 below, each with a
recommendation; the plan's wording assumes the recommendations. The plan gate approved D1–D9 as
recommended; the record is `docs/autopilot/decisions/T032-add-autopilot-notify-and-the-escalation.md`.

## Today

In a throwaway repository with `governing = ["docs/adr"]`, `escalate_gates = ["feature:plan"]`
and `notify = "cat > notified.txt"`, a lane T001 whose branch commits `docs/adr/0001.md` and is
stopped at its plan gate (full output in *Evidence*):

- `autopilot notify` does not exist (exit 2, `invalid choice: 'notify'`) and no command runs;
- `autopilot lane --gate plan` does not exist (exit 2), so a run file cannot say which stage a lane
  is stopped at — only the free-text `--reason`;
- `autopilot status --json` lists `docs/adr/0001.md` in `touched` but has no field saying it is a
  governing path, nor that `feature:plan` is an escalated gate.

The configuration keys are read and checked, and then used by nothing.

## Behaviour

After this change:

- **`autopilot lane <ID> --run R --state gate|escalated --gate <stage>`** (D2) records the stage the
  lane is stopped at as `gate` in the run file. The stage must be one of the task's kind stages
  (exit 2 naming them otherwise). `--gate` with another `--state`, or without `--state` on a lane
  not recorded `gate` or `escalated`, exits 2. A new `--gate` replaces the recorded one; a move to
  `gate` or `escalated` without `--gate` keeps it; `--state running` or `failed` clears it;
  `--state handed-off`, which does not change the recorded state, does not change it either. Run
  files without `gate` still load; it reads as `null`.
- **`autopilot status`** gains, per run task (D8):
  - `gate`: the recorded stage, or `null`;
  - `governing_touched`: the paths in `touched` that a `[autopilot].governing` entry matches
    (D1), sorted, empty when none;
  - `escalate_gate`: `"<kind>:<gate>"` when the task's derived state is `gate` or `escalated` and
    that string is in `[autopilot].escalate_gates`, else `null`;
  - `escalation`: the reasons that apply, in this order: `"governing"` (when `governing_touched`
    is non-empty) and `"escalate-gate"` (when `escalate_gate` is set); empty when none.

  A task whose derived state has moved past the gate (`done-branch`, `done-merged` …) never gets
  `escalate_gate`, even if the run file still records the gate; `governing_touched` follows
  `touched`, which T029 already computes only for states with a branch. The text form adds
  `ESCALATE: governing docs/adr/0001.md; gate feature:plan` to the lane's line. `status` never runs
  the notify command (D7). Conflicts outside the known classes get no computed flag (D6).
- **`autopilot notify --event escalation|lane-done|lane-failed --run R [--task ID] [--message TEXT]`**
  (D3–D5, D7):
  - exits 3 for an unknown run, an unknown task, or a task that is not a member of run R (listed in
    the run file or claimed with `--run R`); exits 2 for an unknown event (argparse) or for
    `lane-done` / `lane-failed` without `--task`. It does not need `[autopilot].enabled` and does
    not refuse an invalid backlog, like `lane`;
  - when `[autopilot].notify` is empty, or the event is not in `notify_on`, runs nothing and exits
    0, reporting `sent: false` and `skipped` with the reason;
  - otherwise runs `notify` through the platform shell, in the repository root the command was
    invoked for, with the environment of the caller plus `TASKRAIL_EVENT`, `TASKRAIL_RUN` and
    `TASKRAIL_TASK` (the task ID, or an empty string without `--task`), the message on stdin, and a
    30-second timeout (D4);
  - the message (D3) is plain UTF-8 text:
    ```
    taskrail autopilot: escalation in run 20260913-1
    T001 Base task
    lane: gate at plan — plan gate

    <the --message text>
    ```
    the second line only with `--task`, the third only when the run records a lane for that task
    (its recorded state, ` at <gate>` when set, ` — <reason>` when set), and the blank line plus
    text only with `--message`;
  - a notify command that exits non-zero, times out (its process group is killed) or cannot be
    started is reported — `sent: false` with `exit_code`, `timed_out` and `error`, plus a
    `taskrail: warning: …` line on stderr — and **`autopilot notify` still exits 0** (D4); the
    command's stdout and stderr are captured (last 2000 characters each in the JSON), never mixed
    into taskrail's own output;
  - JSON result: `event`, `run`, `task`, `command`, `sent`, `skipped`, `exit_code`, `timed_out`,
    `error`, `stdout`, `stderr`, `message`. Text result: `notified: escalation` or
    `not sent: <reason>`.

## Decisions for the plan gate

| # | Question | Options | Recommendation | Reason |
|---|---|---|---|---|
| D1 | How a `governing` entry matches a touched path | exact paths only · exact or directory prefix · shell-style globs · gitignore syntax · git pathspecs through `git diff -- <spec>` | **A repository-relative path or shell-style glob that matches the file or any of its leading directories.** `docs/adr` and `docs/adr/` match `docs/adr/0001.md`; `*` and `?` stay within one path segment, `**` crosses segments, `[…]` is a character class; case-sensitive; a leading `./` is ignored. No config-load check beyond T029's non-empty strings. | Covers the real cases (one constitution file, an ADR directory, `docs/**/decision-*.md`) with one rule. Matching in Python over `touched` keeps uncommitted worktree changes included, which a `git diff` pathspec would miss. Gitignore negation and anchoring rules are more than a governing list needs. Python 3.11 has no `PurePath.full_match`, so a small translator is written and tested. |
| D2 | How `status` knows the gate a lane is stopped at | parse `--reason` · a structured `lane --gate <stage>` · the lane's artifact or commits | **`lane --gate <stage>`**, stored as `gate`, validated against the task's kind stages, accepted with `gate` and `escalated`, kept from `gate` to `escalated`, cleared by `running` and `failed` | A free-text reason cannot be matched reliably. The kind comes from the task row, so the lane only needs the stage name; validating it catches a typo that would silently skip an escalation. Keeping it into `escalated` lets `status` still show which gate was escalated. |
| D3 | Message on stdin; `--message` and stdin passthrough | CLI-composed summary only · caller's text only · summary plus optional `--message` · also read taskrail's own stdin | **A composed summary plus optional `--message TEXT`; no stdin passthrough** | The summary makes every notification self-describing with no effort from the skill; `--message` carries the escalation question. Reading taskrail's stdin would hang an agent's shell call when stdin is an open pipe or a terminal. |
| D4 | How the command runs, and what "never blocks" means | shell · `shlex.split` argv; cwd; timeout fixed · flag · config key; exit code on failure 0 · a distinct code | **Shell (`sh -c`, `cmd` on Windows), cwd the repository root, 30 s fixed timeout that kills the process group, stdin/stdout/stderr through temporary files; exit 0 on any failure of the command, with `sent: false`, the details and a stderr warning** | The config value is written like `[checks]` commands, which executors also run through a shell, so pipes and `$TASKRAIL_EVENT` work. Temporary files avoid a hang when the command leaves a background child holding a pipe, and a command that never reads stdin. The shared exit-code table tells agents to stop on any non-zero exit, so a failed notification must exit 0 to never block. A timeout key would touch `config.py`, which T030 is editing; add one when someone needs it. Usage errors (unknown run or task, missing `--task`) still exit 2 or 3: those are the caller's mistakes. |
| D5 | Events | `escalation`, `lane-done`, `lane-failed` as T029 checks them · add more | **the three; `--task` required for `lane-done` and `lane-failed`, optional for `escalation`** | Matches the design and the config check. An escalation can be run-wide (two lanes contradict), so its task is optional; a lane event without a lane is a mistake. No check that the task is actually done or failed: that is the orchestrator's judgement. |
| D6 | A computed flag for merge conflicts outside the known classes (§12.6 defers it to this gate) | **(a) none; stays judgement** · (b) predicted: `git merge-tree --write-tree` of each lane head into its base, conflicted paths classified by path (backlog files, index files and changelogs, installed skills and manifest) · (c) conflicted paths of a rebase in progress in a lane's worktree | **(a) no computed flag in T032**; §12.6 records why, and a follow-up task is opened only if the T033 trial shows the orchestrator missing such conflicts | A conflict exists only during the rebase the orchestrator itself runs, and git's output already names the files. The known classes are defined by content (rows added on both sides, appended bullets), not by path: a path-based class would call a real edit inside a backlog or changelog "known" and give false confidence. (b) also costs one merge per lane per `status` and needs git 2.38; (c) repeats what the orchestrator just saw. |
| D7 | Does anything call notify implicitly (`status`, `lane --state escalated`) | no, only `autopilot notify` · `lane` triggers events · `status` triggers on new flags | **Only `autopilot notify`** | `status` runs every time the orchestrator wakes and would repeat notifications; `lane` staying side-effect free keeps the skill in control of when a human is paged, and keeps tests and dry runs silent. No record of sent notifications is kept. |
| D8 | Shape of the flags in `status --json` | per-task fields `gate`, `governing_touched`, `escalate_gate`, `escalation` · one nested `escalation` object · a top-level list | **per-task fields as in *Behaviour*** | Flat like T029's `silent` and `touched`; `escalation` gives the skill one non-empty check, and the two detail fields say what to show the human. |

## Acceptance criteria

1. `lane T001 --run R --state gate --gate plan --json` records `gate: "plan"` in the run file and
   prints it; `--gate nope` exits 2 naming the kind's stages and writes nothing; `--gate plan`
   with `--state running` or `failed`, or without `--state` on a lane recorded `running`, exits 2.
   A later `--state escalated --reason …` keeps `gate`; `--state running` clears it; a run file
   lane without `gate` loads and `status` reports `gate: null`.
2. With `governing = ["docs/adr", "CONSTITUTION.md", "src/**/policy-*.py", "./ops/*.toml"]`, a lane
   touching `docs/adr/0001.md` (committed), `CONSTITUTION.md` (uncommitted),
   `src/a/b/policy-x.py`, `ops/deploy.toml`, `docs/adrx.md`, `ops/sub/deploy.toml` and
   `src/policy.py` reports `governing_touched` with exactly the first four and
   `escalation: ["governing"]`; unit cases cover `*` not crossing `/`, `**` crossing zero or more
   directories, `?`, `[…]`, a trailing `/`, and case sensitivity.
3. A lane that touches no governing path, or a repository without `governing`, reports
   `governing_touched: []`; a lane in `done-merged` or `pending` reports `[]`.
4. With `escalate_gates = ["feature:plan"]`: a `feature` lane recorded `gate` at `plan` reports
   `escalate_gate: "feature:plan"` and `escalation: ["escalate-gate"]`; the same lane at
   `implement`, a `bug` lane at `diagnose` (not listed), a `running` lane, and a lane recorded
   at `plan` whose derived state is `done-branch` report `null`; recorded
   `escalated` at `plan` keeps the flag. A lane with both reasons reports
   `["governing", "escalate-gate"]`.
5. The text form of `status` adds `ESCALATE: governing <paths>; gate <kind:stage>` to a flagged
   lane's line and nothing to others.
6. `notify --event escalation --run R --task T001 --message "Approve?"` with
   `notify = "cat > <tmp>/out.txt; env | grep ^TASKRAIL_ > <tmp>/env.txt"` exits 0, reports
   `sent: true, exit_code: 0`, and the files hold exactly the composed message (header, task line,
   lane line, blank line, `Approve?`) and `TASKRAIL_EVENT=escalation`, `TASKRAIL_RUN=R`,
   `TASKRAIL_TASK=T001`; the command ran in the repository root. Without `--task`,
   `TASKRAIL_TASK` is empty and the message is the header only.
7. An event not in `notify_on` (default: `lane-failed`) and an empty `notify` run nothing (the
   output file is not created), exit 0 and report `sent: false` with a `skipped` reason.
8. A command exiting 3 with text on stderr, a command that cannot be found, and a command that
   sleeps past the timeout (timeout shortened in the test) each exit 0 with `sent: false`, the
   matching `exit_code` / `timed_out` / `error`, the captured `stderr`, and a `taskrail: warning:`
   line on stderr; the sleeping command's process group is gone afterwards, and the call returns
   within a few seconds of the timeout even when the command started a background child. The
   command's own stdout does not appear in `--json` output outside the `stdout` field.
9. `notify` for an unknown run, an unknown task or a task not in the run exits 3; `lane-done` or
   `lane-failed` without `--task` exits 2; an unknown `--event` exits 2; none of them runs the
   command. `notify` works while `enabled` is `false`.
10. `status` never runs the notify command, flagged lanes or not (the output file is not created).
11. The whole existing suite still passes, with no change to existing tests.
12. `DESIGN.md` §12.1 marks `notify` implemented with its contract, adds `--gate` to the `lane`
    row and the flags to the `status` row; §12.4 lists `gate` in the run file's lane keys; §12.6
    describes the matching rule, the two computed reasons and D6's outcome; §12.10 marks T032
    implemented; `README.md` shows `notify`; `CHANGELOG.md` has one bullet under *Unreleased*.

## Test coverage

In `tests/test_autopilot_notify.py`, reusing `test_autopilot.py`'s `pilot` fixture
(throwaway repositories with a local bare `origin` and lanes in their own worktrees). Every notify
command is a local shell command writing to a temporary file; nothing goes over the network.

The tests were written before the implementation. With the implementation set aside (the new
`escalation.py` moved to a temporary directory and `status.py` restored from `HEAD`, then both put
back; `notify.py`, `commands.py` and `runs.py` were not yet changed), from the repository root,
`uv run pytest -q -p no:cacheprovider -rf --tb=no tests/test_autopilot_notify.py` gave (ANSI colours
removed; the 29 `test_governing_patterns` cases all failed the same way and are shortened to one line):

```
FAILED tests/test_autopilot_notify.py::test_lane_records_the_gate_a_lane_is_stopped_at - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_governing_patterns[docs/adr-docs/adr/0001.md-True] - ImportError: cannot import name 'escalation' from 'taskrail.autopilot' (/th...
  … the same ImportError for the other 28 test_governing_patterns cases …
FAILED tests/test_autopilot_notify.py::test_status_flags_governing_paths_a_lane_touched - KeyError: 'governing_touched'
FAILED tests/test_autopilot_notify.py::test_no_governing_flag_without_a_match_or_a_branch - KeyError: 'governing_touched'
FAILED tests/test_autopilot_notify.py::test_status_flags_a_gate_listed_in_escalate_gates - KeyError: 'gate'
FAILED tests/test_autopilot_notify.py::test_status_text_marks_flagged_lanes - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_notify_runs_the_command_with_the_message_and_environment - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_notify_skips_events_not_configured_and_an_empty_command - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_a_failing_notify_command_is_reported_and_never_blocks - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_a_notify_command_past_the_timeout_is_killed_with_its_children - ImportError: import error in taskrail.autopilot.notify: No module named 'ta...
FAILED tests/test_autopilot_notify.py::test_notify_checks_its_arguments_before_running_anything - SystemExit: 2
FAILED tests/test_autopilot_notify.py::test_status_never_runs_the_notify_command - SystemExit: 2
40 failed in 1.97s
```

`SystemExit: 2` is argparse refusing `lane --gate` or `autopilot notify`. After the implementation:
`40 passed`, and the whole suite `509 passed` (469 before this task).

| Criterion | Tests |
|---|---|
| 1. `lane --gate` records, checks, keeps and clears the stage | `test_lane_records_the_gate_a_lane_is_stopped_at` |
| 2. Governing matching: paths, directories, globs, uncommitted files | `test_governing_patterns` (29 cases), `test_status_flags_governing_paths_a_lane_touched` |
| 3. No governing flag without a match, a branch, or once merged | `test_no_governing_flag_without_a_match_or_a_branch` |
| 4. `escalate_gates` by kind, stage and derived state; both reasons | `test_status_flags_a_gate_listed_in_escalate_gates` |
| 5. `ESCALATE:` in the text form | `test_status_text_marks_flagged_lanes` |
| 6. Command, message, environment, working directory | `test_notify_runs_the_command_with_the_message_and_environment` |
| 7. Skipped events and an empty command | `test_notify_skips_events_not_configured_and_an_empty_command` |
| 8. Failure, missing command, timeout killing the process group | `test_a_failing_notify_command_is_reported_and_never_blocks`, `test_a_notify_command_past_the_timeout_is_killed_with_its_children` |
| 9. Argument checks; disabled autopilot and invalid backlog | `test_notify_checks_its_arguments_before_running_anything` |
| 10. `status` never notifies | `test_status_never_runs_the_notify_command` |
| 11. Existing behaviour | the whole suite, with no existing test changed |
| 12. Documentation | for review at the implement gate: `DESIGN.md` §7, §12 intro, §12.1, §12.4, §12.6, §12.10; `README.md`; `CHANGELOG.md` |

As a further check, four behaviours were broken one at a time (each file copied aside first and
restored afterwards, `cmp` identical) and the new tests run with
`uv run pytest -q -p no:cacheprovider --tb=no -rf tests/test_autopilot_notify.py`:

| Mutation | Result |
|---|---|
| (a) `cmd_notify` returns 1 when the command failed | `2 failed, 38 passed`: `test_a_failing_notify_command_is_reported_and_never_blocks` (`assert 1 == 0`), `test_a_notify_command_past_the_timeout_is_killed_with_its_children` (`assert (1 == 0)`) |
| (b) `escalate_gate` ignores the derived state (`if kind and gate and …`) | `1 failed, 39 passed`: `test_status_flags_a_gate_listed_in_escalate_gates` (a `done-branch` lane still flagged) |
| (c) the timeout kills only the shell (`process.kill()` instead of `os.killpg`) | `1 failed, 39 passed`: `test_a_notify_command_past_the_timeout_is_killed_with_its_children` (`AssertionError: child`) |
| (d) a governing entry no longer covers files below it (no `(?:/.*)?` suffix) | `8 failed, 32 passed`: three `test_governing_patterns` cases and five status tests |

Deviations from the plan's wording:

- `lane --json` always includes `gate` in `task` (`null` when none is recorded), and the text form
  prints ` at <stage>` after the state (`T001 in run R: gate at plan (plan gate)`).
- The `taskrail: warning:` line for a failed command ends with the last line of the command's
  stderr, when there is one.
- Only a timeout kills the process group; a command that exits on its own may leave a background
  child running, so a notifier that deliberately detaches keeps working.
- A command the shell cannot find is reported by the shell's own status (`exit_code: 127`); the
  "cannot be started" `error` remains for a shell that cannot start at all, which is not tested.
- `runs.py` holds `GATE_STATES` (`gate`, `escalated`), which `escalation.py` imports.
- DESIGN.md §7 lists `notify` in the autopilot row; the README shows `lane --gate` and `notify`.

## Verification

### Real CLI

Run through this checkout's wrapper, `.taskrail/bin/taskrail`, in a throwaway repository under
`/tmp` with a bare `origin`, removed afterwards. Three tasks (T001 feature, T002 bug, T003 chore),
each claimed with `--run` in its own worktree: T001 commits `docs/adr/0007-lanes.md`, T002 leaves
`src/billing/policy-rounding.py` and `src/billing/round.py` uncommitted, T003 leaves `tooling.txt`.
`[autopilot]`: `governing = ["docs/adr", "src/**/policy-*.py"]`,
`escalate_gates = ["feature:plan", "spike:decide"]`, `notify_on = ["escalation", "lane-done"]`,
and `notify` a local script appending its environment, working directory and stdin to a log file
in the temporary directory. Output as printed (`/tmp/t032-verify.KGGD` is the temporary directory):

```
$ taskrail autopilot lane T001 --run 20260914-1 --handle agent-1 --state gate --gate plan --reason plan gate
T001 in run 20260914-1: gate at plan (plan gate)
exit=0
$ taskrail autopilot lane T002 --run 20260914-1 --handle agent-2 --state gate --gate nope
taskrail: --gate: `nope` is not a stage of kind bug (diagnose, fix, impact)
exit=2
$ taskrail autopilot lane T002 --run 20260914-1 --handle agent-2 --state running --gate diagnose
taskrail: --gate needs --state gate or escalated (the lane is running)
exit=2
$ taskrail autopilot lane T002 --run 20260914-1 --handle agent-2 --state gate --gate diagnose --reason root cause found
T002 in run 20260914-1: gate at diagnose (root cause found)
exit=0
$ taskrail autopilot lane T003 --run 20260914-1 --handle agent-3 --state gate --gate scope
T003 in run 20260914-1: gate at scope
exit=0
$ taskrail autopilot status
run 20260914-1 · 0/3 done-merged · kinds: every allowed kind · started 2026-09-14T06:45:55+00:00 by abigail@archlinux
  T001   gate         handle agent-1  idle 0m  — plan gate  ESCALATE: governing docs/adr/0007-lanes.md; gate feature:plan
  T002   gate         handle agent-2  idle 0m  — root cause found  ESCALATE: governing src/billing/policy-rounding.py
  T003   gate         handle agent-3  idle 0m
  hand-off: next — · in review — · queue —
exit=0
$ taskrail autopilot status --json | (T001..T003: id, state, gate, touched, governing_touched, escalate_gate, escalation)
{"id": "T001", "state": "gate", "gate": "plan", "touched": ["docs/adr/0007-lanes.md"], "governing_touched": ["docs/adr/0007-lanes.md"], "escalate_gate": "feature:plan", "escalation": ["governing", "escalate-gate"]}
{"id": "T002", "state": "gate", "gate": "diagnose", "touched": ["src/billing/policy-rounding.py", "src/billing/round.py"], "governing_touched": ["src/billing/policy-rounding.py"], "escalate_gate": null, "escalation": ["governing"]}
{"id": "T003", "state": "gate", "gate": "scope", "touched": ["tooling.txt"], "governing_touched": [], "escalate_gate": null, "escalation": []}
notifications.log after status: absent
$ taskrail autopilot lane T001 --run 20260914-1 --state escalated --reason the plan adds an ADR
T001 in run 20260914-1: escalated at plan (the plan adds an ADR)
exit=0
$ taskrail autopilot notify --event escalation --run R --task T001 --message "T001 adds docs/adr/0007-lanes.md. Approve the ADR?" --json
{
  "event": "escalation",
  "run": "20260914-1",
  "task": "T001",
  "command": "/tmp/t032-verify.KGGD/notify.sh",
  "sent": true,
  "skipped": null,
  "exit_code": 0,
  "timed_out": false,
  "error": null,
  "stdout": "",
  "stderr": "",
  "message": "taskrail autopilot: escalation in run 20260914-1\nT001 Base task\nlane: escalated at plan — the plan adds an ADR\n\nT001 adds docs/adr/0007-lanes.md. Approve the ADR?\n"
}
exit=0
$ taskrail autopilot notify --event escalation --run 20260914-1
notified: escalation
exit=0
$ taskrail autopilot notify --event lane-failed --run 20260914-1 --task T002
not sent: lane-failed is not in [autopilot].notify_on (escalation, lane-done)
exit=0
$ taskrail autopilot notify --event lane-done --run 20260914-1
taskrail: --event lane-done needs --task
exit=2
$ taskrail autopilot notify --event escalation --run 20260914-1 --task T999
taskrail: no task `T999`
exit=3
$ taskrail autopilot notify --event escalation --run 20000101-1
taskrail: no autopilot run `20000101-1`
exit=3
--- /tmp/t032-verify.KGGD/notifications.log:
--- event=escalation run=20260914-1 task=T001 cwd=/tmp/t032-verify.KGGD/repo
taskrail autopilot: escalation in run 20260914-1
T001 Base task
lane: escalated at plan — the plan adds an ADR

T001 adds docs/adr/0007-lanes.md. Approve the ADR?
--- event=escalation run=20260914-1 task= cwd=/tmp/t032-verify.KGGD/repo
taskrail autopilot: escalation in run 20260914-1
$ taskrail autopilot notify --event lane-done --run 20260914-1 --task T003     # notify = 'echo notifier down >&2; exit 7'
taskrail: warning: the notify command exited with status 7: notifier down
not sent: the notify command exited with status 7
exit=0
$ ... --json | jq {sent, exit_code, timed_out, error, stderr}
{"sent": false, "exit_code": 7, "timed_out": false, "error": "the notify command exited with status 7", "stderr": "notifier down\n"}
$ time taskrail autopilot notify --event escalation --run R --json   # notify = 'sleep 45 & sleep 45; …'
{"sent": false, "exit_code": null, "timed_out": true, "error": "the notify command timed out after 30 s and was stopped"}
exit=0 elapsed=30s
taskrail: warning: the notify command timed out after 30 s and was stopped
$ taskrail autopilot notify --event escalation --run 20260914-1 --task T002    # enabled = false again
notified: escalation
exit=0
taskrail autopilot: escalation in run 20260914-1
T002 Rounding error
lane: gate at diagnose — root cause found
```

The run file afterwards held `gate` per lane (`plan` for T001, now `escalated`; `diagnose`;
`scope`) next to T029's keys. That run also printed `sleep processes left: 2` from
`pgrep -fc 'sleep 45'`, which counts every process whose command line contains the text,
including the shell running the verification script itself. A focused re-run in a second
throwaway repository, removed afterwards, with `notify = 'sleep 47 & sleep 47'`, counted only
real `sleep` processes:

```
sleep 47 processes before: 0
$ taskrail autopilot notify --event escalation --run 20260914-1 --json   # notify = 'sleep 47 & sleep 47'
taskrail: warning: the notify command timed out after 30 s and was stopped
{"sent": false, "exit_code": null, "timed_out": true, "error": "the notify command timed out after 30 s and was stopped"}
elapsed=30s
sleep 47 processes right after: 0
```

What this shows against the plan, with no gap found:

- `lane --gate` checks the stage against the kind (`diagnose, fix, impact`) and the state, keeps the
  gate into `escalated`, and prints it;
- `status` flags a committed governing file (directory entry), an uncommitted one (`**` glob), and
  `feature:plan`, while `bug:diagnose` and `chore:scope` are not flagged; `status` wrote nothing to
  the notification log;
- `notify` sends the composed message with `--message`, sets `TASKRAIL_TASK` empty without
  `--task`, runs in the repository root, skips an event outside `notify_on`, exits 2 or 3 for the
  caller's mistakes, and exits 0 with `sent: false` for a failing command and for one killed at the
  30-second timeout together with its background child; it works with `enabled = false`.

## Affected areas

- `src/taskrail/autopilot/notify.py` (new): message composition, running the
  command, the result.
- `src/taskrail/autopilot/escalation.py` (new): governing-path matching and the
  per-task flags, so `status.py` gains only the `gate` field and one call in its own function.
- `src/taskrail/autopilot/status.py`: `gate` in the lane details and one small
  function applying the flags to each row.
- `src/taskrail/autopilot/commands.py`: `cmd_notify` and its registration; `--gate`
  on `lane` and its checks; the `ESCALATE` text.
- `src/taskrail/autopilot/runs.py`: `record_lane` takes `gate`, and `GATE_STATES`
  (no change to `_lane`'s defaults, which T030 edits; a missing key reads as `null`).
- `tests/test_autopilot_notify.py` (new), reusing `test_autopilot.py`'s fixtures.
- `DESIGN.md` §7, §12 intro, §12.1, §12.4, §12.6, §12.10; `README.md`;
  `CHANGELOG.md`.
- Not changed: `config.py` (T029's checks are enough for D1–D5).

## Out of scope

- A computed flag for conflicts outside the known classes (D6), and escalation reasons 3–7 of
  §12.6, which stay judgement.
- Calling notify from `status`, `lane` or any other command; de-duplicating or recording sent
  notifications; retries.
- A configurable timeout, a `validate` warning for an `escalate_gates` entry naming an unknown kind
  or stage, and a config-load check of `governing` patterns.
- `autopilot next` (T030), `autopilot merged` (T031), and the `taskrail-autopilot` skill that
  decides when to notify (T024).

## Open questions and risks

- **Parallel lanes.** T030 edits `status.py` (`task_state`), `runs.py` (`_lane`), `commands.py`
  (`cmd_lane`, `register`) and the §12.1, §12.4 and §12.10 lines of DESIGN.md that this task also
  touches; T031 adds a row to §12.1 and edits §12.10. Code edits are kept to separate functions
  and lines, so conflicts should be limited to adjacent documentation rows, resolved at rebase by
  keeping both.
- **Shell portability.** The command runs through the platform shell; tests use POSIX `sh`, and
  the process-group kill on timeout is POSIX-only (on Windows only the shell is killed).
- **A broad governing entry.** Listing the backlog file or `docs` as governing flags every lane;
  that is the configuration's choice, documented in §12.6.

## Evidence

On this branch's base (`2312a2a`), in a throwaway repository under `/tmp` (removed afterwards)
with `[autopilot]` holding `enabled = true`, `governing = ["docs/adr"]`,
`escalate_gates = ["feature:plan"]`, `notify = "cat > notified.txt"`, and T001 claimed with
`--run` on its branch, which commits `docs/adr/0001.md`:

```
$ taskrail autopilot start --count 1
20260913-1
$ taskrail autopilot lane T001 --run R --state gate --gate plan
usage: taskrail [-h] [--version] [--root ROOT]
                {validate,list,show,next,claim,release,claims,reserve-id,unreserve-id,init,upgrade,integration,self,new,done,discard,reopen,branch,review,epic,kind,autopilot}
                ...
taskrail: error: unrecognized arguments: --gate plan
exit=2
$ taskrail autopilot notify --event escalation --run 20260913-1 --task T001
usage: taskrail autopilot [-h] {start,lane,decision,status} ...
taskrail autopilot: error: argument autopilot_command: invalid choice: 'notify' (choose from start, lane, decision, status)
exit=2
$ taskrail autopilot status --json | jq T001        # after lane --state gate --reason "plan gate"
{"id": "T001", "state": "gate", "reason": "plan gate", "touched": ["docs/adr/0001.md"]}
['blocked_by', 'branch', 'claim', 'decisions', 'decisions_index', 'group', 'handle', 'id', 'idle_minutes', 'kind', 'reason', 'resources', 'silent', 'state', 'title', 'touched', 'worktree']
exists notified.txt: no
```
