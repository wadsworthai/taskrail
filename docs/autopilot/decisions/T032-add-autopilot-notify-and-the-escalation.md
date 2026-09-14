# T032 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T032-add-autopilot-notify-and-the-escalation.md` (commit
`8fa369b`), its twelve acceptance criteria and D1–D9, against DESIGN.md §12.1, §12.4 and §12.6,
and the lane's evidence that `status` today reports only free-text gate reasons and has no
escalation flags.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | `governing` matching | path or glob matching the file or any parent folder, over `touched` · exact paths · prefixes · gitignore · pathspecs | **as recommended** | Covers `docs/adr` and `docs/**/*.md` alike, and counts uncommitted files, which pathspecs over commits would miss. |
| D2 | Knowing which gate a lane is at | structured `lane --gate <stage>`, checked against the kind's stages · parse `--reason` · infer | **`lane --gate`** | `escalate_gates` names `kind:stage`; free text cannot be matched reliably. |
| D3 | Message on stdin | CLI summary plus optional `--message`, no passthrough · summary only · caller text only | **as recommended** | Passing taskrail's own stdin through can hang an agent's shell call. |
| D4 | Running the command | shell in the repository root, 30 s timeout killing the process group, temp files for output, exit 0 with `sent: false` on failure; caller mistakes still fail · argv split · configurable timeout · distinct exit code | **as recommended** | The command is repository configuration, like `checks`; "never blocks" means a broken notifier never stops the orchestrator. |
| D5 | Events | the three T029 already accepts, `--task` required for lane events · more events | **as recommended** | Enough for escalation and lane completion; no enablement or valid backlog needed to notify. |
| D6 | Flag conflicts outside the known classes | no computed flag, reason recorded in §12.6 · predict with `merge-tree` · list a rebase in progress | **no computed flag** | Conflicts arise in the orchestrator's own rebase, where git names them; classing by path would mark a real edit in a backlog or changelog as known. T033 can reopen the question with evidence. |
| D7 | Automatic notification | only `autopilot notify` runs it · `lane` or `status` trigger it | **only `autopilot notify`** | `status` runs on every wake-up and would repeat notifications. |
| D8 | Flag shape in `status --json` | flat per-task fields · nested · top-level list | **flat** | Matches the rest of the task row. |
| D9 | Code layout | new `autopilot/escalation.py`, small `status.py` addition · inside `status.py` | **new module** | Keeps the overlap with T030's `status.py` edits small. |

Plan approved. Notify commands in tests and verification stay local scripts writing to temporary
files; the lane removes its scratch repositories when done.

## implement gate

Reviewed: commit `b6de564` (`autopilot/escalation.py`, `autopilot/notify.py`, the `gate` field and
`_flag_escalations` in `status.py`, `record_lane(gate=)` in `runs.py`, `lane --gate` and
`cmd_notify` in `commands.py`, DESIGN.md, README, CHANGELOG, `tests/test_autopilot_notify.py`).
Re-ran `uv run pytest -q` in the lane's worktree: 509 passed. The lane
was interrupted by an API limit mid-stage; on resuming it set the implementation aside, recorded 40
failing tests, and restored it without a stash. Four deliberate breakages (a failed notify changing
the exit code, a gate flag ignoring the derived state, a timeout killing only the shell, a governing
entry not covering files below it) each failed the tests that cover them. `status` never calls
`notify`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Follows D1–D9 with the edits kept away from T030's and T031's lines. |
| 2 | Deviations: `gate` always in `lane --json`; stderr warning ends with the command's last stderr line; only a timeout kills the process group; a missing command reports the shell's 127; `notify` in the §7 row | accept · reject some | **accept all** | Each is visible and harmless; a notifier that deliberately detaches keeps working. |
| 3 | Expected rebase conflicts in DESIGN.md §7/§12 and CHANGELOG | keep both · stop | **keep both; stop on any code conflict** | Neighbouring rows and bullets are a known class. |

## verify, close and rebase after T034 and T037

The verify stage ran the real CLI with three lanes, committed and uncommitted governing files and a
local notify script, and found no gap against the plan. The lane rebased onto `origin/main`
(`d092c96`) at close: the decisions index and CHANGELOG conflicted and kept both sides; no code
conflicted. Checked by the orchestrator before publishing: `TODO.md` differs from `main` only in
T032 `✅`, `pytest -q` 524 passed, `taskrail validate` 0 errors, `upgrade` reports nothing to create
or update.

## rebase after T036 and T030

T036 (`591fa5b`) and T030 (`53bd1fb`) were squash-merged into `main`. The orchestrator rebased the
branch onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in the docs indexes and CHANGELOG | keep both · stop | **keep both** | Rows and bullets added on both sides; one T032 bullet remains. |
| 2 | Conflicts in `autopilot/commands.py`, `runs.py`, `status.py` | keep both · stop | **keep both** | Each hunk was an import or constant added on both sides: `dispatch` and `notify` imported together, `DISPATCHED` beside `GATE_STATES`/`GATE_CLEARING`, `runs_module` beside `escalation`. |
| 3 | Conflicts in DESIGN.md §7, §12 intro, §12.1 and §12.4 | merge both texts · stop | **merge both** | T030's implemented `next` row and group check, T032's `--gate` sentence and escalation fields; `status` lists `dispatched` (T030) and the escalation reasons (T032); the run file lists both `gate` and `dispatched`. |

The full suite ran on the conflict-resolved commit before continuing (576 passed). After the rebase:
no conflict markers, `pytest -q` 576 passed, `taskrail validate` 0 errors, `upgrade` reports nothing
to create or update.
