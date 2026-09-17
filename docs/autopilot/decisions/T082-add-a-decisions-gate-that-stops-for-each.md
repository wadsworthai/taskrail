# T082 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan `docs/features/T082-add-a-decisions-gate-that-stops-for-each.md` (commit
`01e47e2`, the artifact and its index row only, clean worktree); `GATES` in `kinds.py` is the only
list of gate values in `src/` and is read only by `_parse`'s stage check; no test or source repeats
the tuple. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan | approve · change | **as recommended** | The criteria cover the T082 row and §13.4, §13.6 and §13.8; the code change is the one constant the design needs. |
| 2 | How §13 is marked once a part moves out | replace a moved subsection's body with a one-line *Implemented (T0xx)* pointer, mark shared bullets and §13.8 rows in place · keep the full text with a marker | **as recommended** | One place per rule; the same convention is given to T080 and T081, so the three branches mark §13 alike. |
| 3 | Where the gate semantics go | new §5.6 *Gates* · a paragraph under §5.1 | **as recommended** | Its own hunk, away from §5.1's planned note that T081 edits. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Touch map, T082's part | as planned · narrower | **T082 changes only `kinds.GATES`, a new `tests/test_decisions_gate.py`, DESIGN.md §2's Gate row, the gate half of §5.1's planned note, §5.4's judgement sentence, a new §5.6, §12.6's escalated-gates bullet, §13.1's `gate` bullet, §13.4, §13.6's kind-gate bullet and §13.8's T082 row, and one CHANGELOG bullet; not `config.py`, `show`'s fields, the autopilot refusals, the stage-parsing loop, skills or README** | From T082's plan, so it shares with T081 only separate hunks of `kinds.py` and DESIGN.md §5.1/§13, and the changelog (a known class). |
