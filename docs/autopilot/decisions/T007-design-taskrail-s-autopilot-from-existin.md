# T007 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane. The `decide` gate is escalated to the human: it
settles the autopilot's architecture.

## frame gate

Reviewed: the framed draft `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md` (commit
`06ee5d3`) — its question with nine points to settle, planned evidence and limits.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Scope: the nine points including the task breakdown | approve · design only | **approve** | T024 at 8 points cannot be picked up without a breakdown; T017, T019 and T020 are waiting on this decision. |
| 2 | Evidence on agent capabilities | docs and trivial runs · docs only | **docs first, plus trivial runs under constraints** | Resuming and notification are the least documented behaviours. Constraints: a handful of minimal runs, in a temporary directory outside the repository, never with flags that skip permission prompts; stop and report if a login or permission prompt appears. Runs spend the human's agent quota, so keep them minimal. |
| 3 | Where the design lives | the spike document, with a follow-up · edit `DESIGN.md` now | **the spike document, with a follow-up** | A spike decides; moving the design into `DESIGN.md` and the skills is implementation work. |
| 4 | This repository's squash merges #8–#11 as merge-detection data | yes, read-only · throwaway repositories only | **yes, read-only** | Real squash history is the case the detection must handle; reading git history changes nothing. |

State corrections for the lane: T005 was stopped before doing any work, to follow the agreed task
order (T005 runs last); its claim was released. T026 now runs in parallel and edits `cmd_new`'s
`--column` handling in `cli.py`.

## decide gate — escalated to the human

The orchestrator reviewed the decision document (`f2eb2df`) — evidence E1–E7, the design and the
task breakdown — and escalated the gate, as agreed at the frame gate. It flagged one conflict
before asking: the lane recommended installing the autopilot skill only when
`[autopilot].enabled` is true, while the human had required the autopilot to end up installed in
every consumer repository, with each repository deciding whether to use it.

Decisions taken by the human:

| # | Question | Decision |
|---|---|---|
| 1 | Accept the design as the autopilot's architecture | **accepted**: one judgement skill over a `taskrail autopilot` command group; state derived from git plus a local run file; claims stay the only lock. |
| 2 | Open tasks A–G and edit T017 and T024 as in the breakdown | **yes, all of it**, including hand-edited points and dependencies while `taskrail edit` does not exist. |
| 3 | Where run-level decisions live | **copied into each affected task's record**, and kept in the local run file. |
| 4 | When the autopilot skill is installed | **always**; `taskrail autopilot start` refuses (exit 5) until `[autopilot].enabled` is true. This overrides the lane's recommendation 5. |

## close and rebase after T025 and T026 merged

The lane rebased onto `origin/main` (`d93ecdc`). One resolution went beyond the agreed classes
and was reviewed by the orchestrator: in `TODO.md`, the branch's hand edit of T024 (points,
dependencies, title, description) sat next to T026's ✅ from `main`. They are different rows, so
the rows were united by ID — the branch's edited T024 and `main`'s ✅ on T026. **Accepted**: it is
the row-union rule applied to an edited cell, with no row losing either side's change.

Verified before publishing: the branch changes only `TODO.md`, two indexes, this record and the
spike document; no conflict markers; `validate` reports 33 tasks and no errors; T027–T033 exist
with the breakdown's dependencies; T017 is 5 points; T024 is 5 points and depends on T030, T031
and T032, not T025; `review` needs no further rebase.
