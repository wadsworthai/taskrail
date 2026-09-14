# T050 — Accept --gate close for the stop after done

Kind: feature · Epic: E02 · Status: verified (plan approved: D2–D5 as recommended; D1, the
DESIGN.md text, approved as written at the implement gate and applied). Record:
`docs/autopilot/decisions/T050-accept-gate-close-for-the-stop-after-don.md`.

Source: finding F10 of `docs/spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md`. Builds on
T032, which added `autopilot lane --gate` (`autopilot/commands.py`, `_gate_problem`) and the
escalation flags (`autopilot/escalation.py`).

## Today

A lane stops after `taskrail done` and `taskrail review <ID> --json`, and the `taskrail-autopilot`
skill reviews that stop like any other gate (*Close and hand off*: "Review the close by
`references/gate-review.md`"). But `lane --gate` only accepts a stage of the task's kind, and no
kind has a stage for the close, so the orchestrator cannot record it. Reproduced with a throwaway
pytest against the `pilot` fixture (a feature task T001 claimed in a run, marked done and committed
on its branch, then):

```text
autopilot lane T001 --run <run> --state gate --gate close
exit=2
stdout=''
stderr='taskrail: --gate: `close` is not a stage of kind feature (plan, implement, verify)\n'
```

In the trial it was `` `close` is not a stage of kind bug (diagnose, fix, impact) ``, exit 2.

## Behaviour

After this change:

- `autopilot lane <ID> --run R --state gate|escalated --gate close` records `gate = "close"` for a
  task of any kind: `close` names the stop after `taskrail done` that every kind shares, next to
  the kind's own stages. Every other rule of `--gate` is unchanged: it still needs the lane to be
  (or be set) `gate` or `escalated` (exit 2 otherwise), a new `--gate` replaces the recorded one,
  `running` and `failed` clear it, `handed-off` keeps it.
- Any other name that is not a stage of the kind still exits 2, and the message now lists `close`
  as well: `` --gate: `nope` is not a stage of kind feature (plan, implement, verify) or `close` ``.
- `autopilot status` shows the recorded `gate: "close"` for the task. The task's derived state at
  that point is `done-branch`, so, like every gate a task has moved past, `close` never sets
  `escalate_gate` (D5).
- The `taskrail-autopilot` skill's *Close and hand off* section tells the orchestrator to record
  the stop with `taskrail autopilot lane <ID> --run <R> --state gate --gate close` before reviewing
  it.

## Acceptance criteria

1. `autopilot lane T001 --run R --state gate --gate close` exits 0 for a feature task, and the run
   file and the JSON result carry `gate: "close"`.
2. The same is accepted for a task of another kind (bug), whose stages differ.
3. `--gate close` on a `done-branch` task (done and committed on its branch) exits 0, the F10
   scenario, and `autopilot status` then reports that task `done-branch` with `gate: "close"` and
   `escalate_gate: null`, even with `escalate_gates = ["feature:close"]`.
4. `--gate close` keeps the state rules: with `--state running` or `--state failed`, or with no
   `--state` on a lane recorded `running`, it exits 2 and the run file is unchanged.
5. An unknown gate name still exits 2 with the run file unchanged, and the message names the kind's
   stages and `close`.
6. The shipped `taskrail-autopilot` skill's close section contains the `--gate close` command, and
   the installed copy under `.claude/skills/` matches it after `taskrail upgrade`.

## Tests per criterion

All in `tests/`; each was observed failing before the implementation (the two lane
tests with `` `close` is not a stage of kind bug `` and `` kind `mystery` is not defined ``, exit 2;
the skill test with the phrase missing).

| Criterion | Test |
|-----------|------|
| 1 | `test_autopilot_notify.py::test_lane_records_close_for_the_stop_after_done_in_every_kind` (feature task T001: JSON result and run file carry `close`) |
| 2 | same test (bug task T003); `test_lane_records_close_for_a_task_whose_kind_is_not_defined` (D2: an undefined kind accepts `close` and still refuses a stage name) |
| 3 | `test_lane_records_close_for_the_stop_after_done_in_every_kind` (T001 done and committed, then `--gate close`; `status` row `done-branch`, `close`, `escalate_gate: null`, `escalation: []` with `escalate_gates = ["feature:close"]`) |
| 4 | same test (`--state running`, `--state failed --reason`, and no `--state` on a running lane: exit 2, run file byte-identical) |
| 5 | same test (`--gate nope` on the bug task: exit 2, message contains `(diagnose, fix, impact) or `close``, run file unchanged); T032's `test_lane_records_the_gate_a_lane_is_stopped_at` still checks `plan, implement, verify` |
| 6 | `test_autopilot_skill.py::test_skill_records_the_close_stop_as_a_gate` (shipped source). The installed copy is not a tool test: `taskrail upgrade` updated `.claude/skills/taskrail-autopilot/SKILL.md` and its digest in `.taskrail/installed.json`, and a `diff` of the two *Close and hand off* sections is empty |

## Verify

The real CLI from this branch's source (`uv run --quiet --project <worktree>
taskrail --root <scratch>`), against a throwaway git repository outside this one: a backlog with a
single bug task T001, `[autopilot] enabled = true` and `escalate_gates = ["bug:close"]`. Steps:
`autopilot start --count 1` (run `20260914-1` in the scratch repository's own git directory),
`git switch -c T001-fix-a-thing`, `claim T001 --run 20260914-1`, `done T001`, commit. Then:

```text
$ taskrail autopilot lane T001 --run 20260914-1 --state gate --gate close
T001 in run 20260914-1: gate at close
exit=0

$ taskrail autopilot lane T001 --run 20260914-1 --state gate --gate nope
taskrail: --gate: `nope` is not a stage of kind bug (diagnose, fix, impact) or `close`
exit=2

$ taskrail autopilot status --run 20260914-1
run 20260914-1 · 0/1 done-merged · kinds: every allowed kind · started 2026-09-14T22:16:58+00:00 by abigail@archlinux
  T001   done-branch  idle 0m
  hand-off: next T001 · in review — · queue T001
exit=0

$ taskrail autopilot status --run 20260914-1 --json   # fields of T001's row
{'id': 'T001', 'state': 'done-branch', 'gate': 'close', 'escalate_gate': None, 'escalation': []}
```

No gap against the plan: `close` is recorded on a `done-branch` task, an unknown name names
`close`, and `bug:close` in `escalate_gates` does not flag, as §12.6 now says.

## Affected areas

- `src/taskrail/autopilot/commands.py` — `_gate_problem` accepts `close` (a module
  constant, e.g. `runs.CLOSE_GATE = "close"` or local to `commands.py`) and the error message; the
  `--gate` help text.
- `tests/test_autopilot_notify.py` — tests for criteria 1–5, next to T032's `--gate`
  tests (it already imports the `pilot` fixture).
- `src/taskrail/skills/taskrail-autopilot/SKILL.md` — one sentence in *Close and hand
  off*; `.claude/skills/taskrail-autopilot/SKILL.md` (and `installed.json` if `upgrade` rewrites
  its digest) via `taskrail upgrade`. A test in `tests/test_autopilot_skill.py` for criterion 6's
  shipped half.
- `DESIGN.md` §12.1 (`autopilot lane` row) and §12.6 (*Escalated gates*) — governing,
  exact text in D1.
- `CHANGELOG.md` (one *Unreleased* bullet), `docs/features/README.md` (index row).

Not touched: `autopilot/status.py`, `autopilot/escalation.py` (T049 and T053's areas).

## Out of scope

- Flagging `kind:close` in `escalate_gates` (D5).
- Reserving `close` as a stage name in kind validation (D4).
- Requiring the task to be `done-branch` for `--gate close` (D3).
- The other T033 findings (F1, F7, F8, F9, F12) and their tasks.

## Open questions and risks

- **D1 — DESIGN.md text (governing).** Proposed exact changes:
  - §12.1, `autopilot lane` row: replace `*Implemented (T029; `--gate` T032).*` with
    `*Implemented (T029; `--gate` T032; `close` T050).*`, and replace
    "`--gate` records the stage whose gate the lane is stopped at, as `gate`: it must be a stage of
    the task's kind and the lane must be (or be set) `gate` or `escalated`, otherwise exit 2;"
    with
    "`--gate` records the stage whose gate the lane is stopped at, as `gate`: it must be a stage of
    the task's kind, or `close` for the stop after `taskrail done` that every kind shares, and the
    lane must be (or be set) `gate` or `escalated`, otherwise exit 2;"
  - §12.6, *Escalated gates*: after "A task that has moved on (`done-branch` and later) is not
    flagged." append " That includes `close`, recorded once the task is `done-branch`, so a
    `<kind>:close` entry in `escalate_gates` never flags."
  Recommendation: approve as written. Alternative: leave DESIGN.md unchanged (the row would then
  contradict the CLI).
- **D2 — `close` for a task whose kind is not defined.** Recommendation: accept it — `close` does
  not depend on the kind's stages, so check it before the kind lookup. Alternative: keep the
  existing exit 2 for an undefined kind for every `--gate` value.
- **D3 — require `done-branch` for `--gate close`.** Recommendation: no; the lane brief's close
  step commits `done` before stopping, and the gate review checks it. Alternative: exit 5 unless the
  task is `done-branch`, which also catches a lane that stopped before committing `done`.
- **D4 — a kind with its own stage named `close`.** None of the core kinds has one. Recommendation:
  do not reserve the name; `--gate close` then records the same string for either, and the decision
  record says which stop it was. Alternative: make `validate` reject a stage named `close`, a
  breaking change for any custom kind that uses it.
- **D5 — `<kind>:close` in `escalate_gates`.** At the close the task is `done-branch`, and §12.6
  says such a task is not flagged, so the entry would never flag. Recommendation: keep that rule and
  document it (D1's §12.6 sentence); flagging closes would change `escalation.py` and
  `status.py`, where T049 is changing the flags for `done-branch` tasks. Alternative: flag
  `escalate_gate` for a `done-branch` task whose recorded gate is `close` — a separate follow-up
  task, verified by pytest, if wanted.
- **Risk:** the installed skill copy and `installed.json` are also touched by other lanes running
  `taskrail upgrade`; a conflict there is regenerated by re-running `upgrade` after the rebase.
