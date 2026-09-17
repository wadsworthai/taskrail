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

## implement gate

Reviewed: `git diff 205fad5..fa59565` — the one-line `GATES` change in `kinds.py`, the new
`tests/test_decisions_gate.py` (8 tests, one per criterion, reported failing before the change with
the old message and validation errors), DESIGN.md §2, §5.1, §5.4, new §5.6, §12.6 and the §13 marks
(only T082's lines; §13's introduction, summary table and other lanes' lines untouched), and the
CHANGELOG bullet; the checks re-run with `taskrail checks T082 --stage implement` (test passed, lint
not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | approve · change | **as recommended** | The diff matches the plan and the touch map; every criterion has a test observed failing first. |
| 2 | Wording of the §13 in-place marks | "— *implemented (T082)*, now §x.y" · bare "*implemented (T082)*" | **as recommended** | The pointer says where the rule lives now; T080 and T081 are told to use the same form. |

## close gate

Reviewed: the verify section (commit `9595636`) and `taskrail done` committed on its own in `3feb255`
(only T082's status cell); no upstream on the branch; clean worktree; `review --json` reports no
rebase needed onto `origin/main`; `autopilot status` shows no escalation and no governing path.
Exercised in a scratch repository with this branch's CLI: an override setting spike's gates to
`decisions` gives `validate` 0 errors and `show` prints `(gate: decisions, commit)`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request title's type and scope | `feat(cli)` · `feat(kinds)` | **`feat(cli)`** | A new accepted value in the CLI's kind descriptors, the lane's suggestion; CLAUDE.md asks for a scope. |
| 2 | Hand-off order among T080, T081, T082 | T082 first · wait for the others | **T082 first** | It is the first done and the smallest; T080 and T081 rebase onto it at their hand-off (conflicts limited to known classes and separate DESIGN.md lines). |
