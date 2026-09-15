# T048 — Add autopilot close to abandon a run

Kind: feature · Epic: E02 · Status: verified

Source: finding F7 of the
[T033 trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md) (*Findings* and
*Recommendation*, follow-up row T048). Builds on T029 (run files, `autopilot lane`, `decision`,
`status`, `claim --run`) and T030 (`autopilot next`, dispatches and resources). The gate decisions
are recorded in `docs/autopilot/decisions/T048-add-autopilot-close-to-abandon-a-run.md`.

## Behaviour

Today a run cannot be ended by anyone. In the T033 trial a conversation rewind restored the
orchestrator's conversation but not its run file: run `20260914-1` still recorded three dispatched
tasks holding all three lanes, and the rewound session had to start a second run and ask what to do.
A dispatch only frees its lane after `[git].claim_grace_minutes`, a resource value only when a later
`next --run` finds its lane ended, and `status` keeps listing the dead run forever, since runs are
never removed.

After this change, `taskrail autopilot close <R> --reason <text> [--json]` abandons run `R`:

1. **Records the close** in the run file as `closed: {at, by, reason}` — the UTC time, the caller's
   owner name (`claims.default_owner()`), and the trimmed reason. The run file stays on disk; runs are
   still never removed.
2. **Releases the run's dispatches and resources**, under the common-directory lock: every lane of
   the run loses its `dispatched` time and its `resources`. Each lane that had either is reported in
   `released` as `{id, dispatched, resources}` with the values it held.
3. **Leaves claims alone.** A claim is a lane's lock on work in a worktree, not run state. Live
   claims naming the run are reported in `claims` (`{id, owner, branch, worktree}`), so the human can
   decide whether to `taskrail release` each one; `close` never releases one.
4. **Hides the run** from the commands that plan work:
   - `autopilot next`, with or without `--run`, ignores closed runs entirely: their lanes do not
     occupy `max_lanes`, count toward groups, hold resource values, or make a task "dispatched in run
     …"; nothing in them is released or written;
   - `autopilot status` without `--run` lists only open runs, so `overlaps` ignore closed ones too;
     `status --run R` still shows a closed run, with its `closed` record (and `closed …` in the text
     form's run line), so its history stays readable.
5. **Refuses new work in a closed run** with exit 5: `autopilot next --run R`, `autopilot lane <ID>
   --run R`, `autopilot decision --run R`, and `taskrail claim <ID> --run R` (checked before the
   claim is taken, so nothing is written).
6. **Exit codes:** 0 closed; 2 for an empty `--reason`; 3 for an unknown run; 4 when the lock cannot
   be taken; 5 when the run is already closed (nothing changes). `close` needs neither
   `[autopilot].enabled` nor a valid backlog: abandoning a run must work in a repository that has
   since disabled the autopilot or broken its backlog.

Unchanged: `autopilot merged` still records a proven merge in a closed run that holds the task, and
recorded merges in closed runs still count toward `done-merged` (they are evidence, not lane state);
`autopilot notify` is unaffected.

## Acceptance criteria

Each is verified by pytest on fixture repositories and run files (`tests/test_autopilot_close.py`).

1. `autopilot close R --reason …` writes `closed` with `at`, `by` and `reason` into the run file, keeps
   every other key (unknown keys included), and exits 0; `--json` reports `run`, `closed`,
   `released` and `claims`.
2. After closing a run with dispatched lanes, every lane of the run has `dispatched` null and empty
   `resources`, and `released` lists each of those lanes with the dispatch time and values it held.
3. A live claim naming the run is still present after `close`, and is listed in `claims`.
4. With run A closed while it held all `max_lanes` dispatches and every resource value, `autopilot
   next --run B` for an open run B dispatches up to `max_lanes` tasks — including the tasks A had
   dispatched — and gets the first resource values again; a preview `next` sees the same free lanes.
5. A task claimed with `--run A`, a group member recorded in A, and a `gate` lane recorded in A do not
   occupy a lane or a group place in `next` once A is closed.
6. `autopilot status` without `--run` omits a closed run (and its files from `overlaps`);
   `status --run A` shows it with its `closed` record, and the text form says `closed`.
7. `next --run A`, `lane <ID> --run A`, `decision --run A` and `claim <ID> --run A` exit 5 for a closed
   run A and write nothing (no run-file change, no claim).
8. `close` exits 3 for an unknown run, 2 for an empty or blank `--reason`, and 5 for a run already
   closed, leaving the first `closed` record unchanged.
9. `close` works with `[autopilot].enabled = false` and with an invalid backlog.
10. A merge recorded in a closed run still makes its task `done-merged` in `status` of an open run
    holding it.

## Affected areas

- `src/taskrail/autopilot/runs.py`: `closed` defaulted to null in `_normalize`; an
  `is_closed(run)` helper; a `close(run, reason, owner, now)` function that records the close and
  clears the lanes, returning what it released.
- `src/taskrail/autopilot/commands.py`: new `cmd_close` and its `add("close", …)` in
  `register`; a closed-run refusal (exit 5) at the start of `cmd_lane`, `cmd_decision` and
  `cmd_next`; the default listing of `cmd_status` filtered to open runs; the run line of
  `_status_text`. Not touched: `_gate_problem` and `--gate` help (T050), `_escalation_text` (T049).
- `src/taskrail/autopilot/dispatch.py`: `next_lanes` drops closed runs from
  `every_run` before deriving states, and raises for a `run_id` that is closed (the lock-held
  re-check behind `cmd_next`'s refusal).
- `src/taskrail/autopilot/status.py`: only the dictionary `run_status` returns gains
  `closed`. Not touched: `_handoff`, `_done_time` (T053), `task_state`.
- `src/taskrail/cli.py`: `cmd_claim`'s existing `--run` check refuses a closed run
  with exit 5.
- `tests/test_autopilot_close.py`: new.
- `DESIGN.md` §12.1 (a new `autopilot close` table row), §12.4 (the `closed` run-file
  key), §12.7 (lanes counted across open runs) — exact text proposed at the plan gate.
- `src/taskrail/skills/taskrail-autopilot/SKILL.md` and its installed copies, only if
  the plan gate approves the one-line command reference (question at the gate).
- `CHANGELOG.md` (one bullet), `docs/features/README.md` (index row).

## Out of scope

- Releasing claims, removing worktrees or branches of a closed run's lanes: that stays
  `taskrail release` and `autopilot merged --cleanup`, on a human's decision.
- Reopening a closed run, or deleting run files.
- Skill text on dispatch expiry and on resuming a run from a new session (T055).
- Detecting a stale orchestrator automatically, or closing a run on a timer.
- `autopilot notify` and `autopilot merged` behaviour for closed runs.

## Open questions and risks

- **Claims left behind.** A lane that claimed before the close keeps its claim, so its task stays out
  of `next`'s candidates although its lane no longer counts. That is the intended trade: the claim
  protects the worktree's work, and `close` reports it.
- **Race with a claiming lane.** `claim --run R` reads the run before claiming; a close landing in
  between leaves a claim naming a closed run, which `next` then ignores as a lane and `close`'s
  report would have missed. Accepted: the window is one command, and the claim still shows in
  `taskrail claims`.
- **Merge with sibling lanes.** T049, T050 and T053 edited other functions of `commands.py` and
  `status.py` and other rows of DESIGN §12.1; this plan adds a row and keeps to separate hunks, so
  a rebase should see at most adjacent-line conflicts in the table.

## Plan-gate decisions

Approved as written (record: `docs/autopilot/decisions/T048-add-autopilot-close-to-abandon-a-run.md`):
the DESIGN §12.1 row, §12.4 (a)–(d) and §12.7 text; the skill paragraph at the end of *Escalate*,
with `taskrail upgrade`; exit 5 for an already-closed run; claims kept and reported; `status --run R`
shows a closed run with `closed`. `dispatch.py` keeps to filtering closed runs out of `every_run`
and the `run_id` re-check, leaving the candidate loop to T054.

## Implementation

- `runs.py`: `closed` defaults to null; `RunClosed`, `is_closed`, `closed_message` and `close`, which
  records `{at, by, reason}` and clears each lane's `dispatched` and `resources`, returning what it
  released.
- `commands.py`: `cmd_close` and its parser; `lane`, `decision` and `next` refuse a closed run with
  exit 5, both before the lock and again inside it; `status` without `--run` filters closed runs,
  and the text form adds a `closed <at> by <by> — <reason>` line under the run.
- `dispatch.py`: `next_lanes` raises `RunClosed` for a closed `run_id` and derives every state from
  open runs only, so nothing in a closed run is released or written.
- `status.py`: `run_status` reports `closed`.
- `cli.py`: `claim --run` refuses a closed run with exit 5 before taking the claim.
- DESIGN §12.1, §12.4, §12.7, the autopilot skill (source and installed copy,
  `.taskrail/installed.json`) and the changelog, as approved.

## Acceptance criteria → tests

All in `tests/test_autopilot_close.py`.

| # | Tests |
|---|---|
| 1 | `test_close_records_who_when_and_why_and_keeps_every_other_key` |
| 2 | `test_close_releases_every_dispatch_and_resource_of_the_run`, `test_close_text_names_what_it_released_and_the_kept_claims` |
| 3 | `test_close_keeps_and_reports_the_claims_naming_the_run`, `test_close_text_names_what_it_released_and_the_kept_claims` |
| 4 | `test_a_closed_run_frees_its_lanes_and_resources_for_other_runs` |
| 5 | `test_claims_groups_and_gates_of_a_closed_run_hold_no_lane` |
| 6 | `test_status_lists_a_closed_run_only_when_named`, `test_close_records_who_when_and_why_and_keeps_every_other_key` (text form) |
| 7 | `test_a_closed_run_refuses_new_work_and_writes_nothing` |
| 8 | `test_close_exit_codes` |
| 9 | `test_close_works_while_disabled_and_with_an_invalid_backlog` |
| 10 | `test_a_merge_recorded_in_a_closed_run_still_counts` |

## Verification

Run with this branch's CLI (`.taskrail/bin/taskrail --root <scratch>`) against a scratch git
repository in a temporary directory: three pending tasks, `worktree = "never"`, `max_lanes = 2` and a
`PORT` resource with two values. No run file of this repository was touched.

1. `autopilot start --count 3` twice made runs `20260914-1` and `20260914-2`. `next --run 20260914-1`
   dispatched T001 (`PORT=5433`) and T002 (`PORT=5434`), `limited by max_lanes`; `next --run
   20260914-2` then printed `nothing to dispatch · 2/2 lanes in use`. `claim T003 --run 20260914-1`
   gave run 1 a claimed lane.
2. `autopilot close 20260914-1 --reason "orchestrator session rewound"` printed the close, one
   `released dispatch of … and PORT=… from T00x` line each for T001 and T002, and
   `kept claim T003 by lane in <repo>; release it with `taskrail release T003``.
3. `autopilot status` listed only run 2. `status --run 20260914-1` showed run 1 with
   `closed <at> by <owner> — orchestrator session rewound`, T001 and T002 `pending`, and T003 still
   `running` on its kept claim.
4. `next --run 20260914-2` dispatched T001 and T002 with `PORT=5433` and `PORT=5434`, `2/2 lanes in
   use`: run 1's claimed T003 no longer held a lane.
5. On the closed run, `lane T001 --run … --handle h1`, `decision --run …`, `next --run …` and
   `claim T002 --run …` each exited 5 with ``autopilot run `20260914-1` is closed``; a second
   `close` exited 5 naming the first close; `close 20000101-1` exited 3; `close … --reason "   "`
   exited 2.
6. With `[autopilot].enabled = false`, `close 20260914-2 --json` exited 0 with `run`, `closed`,
   `released` (T001 and T002 with their dispatch times and ports) and `claims: []`; `status` then
   printed `no autopilot runs`, and the run file kept every key with `closed` added and each lane's
   `dispatched` null and `resources` empty.

The behaviour matches the plan; no gap.
