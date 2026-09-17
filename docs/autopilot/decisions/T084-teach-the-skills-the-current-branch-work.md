# T084 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the scope artifact `docs/chores/T084-teach-the-skills-the-current-branch-work.md` (commit
`349ac1f`, the artifact only, clean worktree), its change set against DESIGN.md §5.6, §12.6, §13.5
and §13.8 and the T084 row, and the lane's scratch run of the merged CLI under `task_branch =
"current"` and `commit = "on-done"` (`show`'s `close`, `done`'s `commit`, `review`'s report and the
`--publish` refusal). The stage defines no checks. This is the only live lane.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Mark §13 fully implemented | heading, status line, §11 and §5.3 as proposed · a separate docs task · status line only | **as recommended** | T084 completes E07; §12 sets the precedent, and leaving "planned" text would misdescribe the CLI. |
| 2 | Where the executor's close moves | new "The repository's workflow" block in §8 · §7.1 | **as recommended** | It is skill behaviour, which §8 describes; §7.1 stays the CLI contract. |
| 3 | T081's CHANGELOG sentence that the skills still commit per stage | delete · keep | **as recommended** | Unreleased must describe what the release does; the sentence becomes false with this task. |
| 4 | Integration notes | extend Claude and OpenCode notes and the verbatim test constants · no change | **as recommended** | Asking and the subagent hand-back must cover decision stops and the push question on each agent; the safety rule stays in the portable prose too. |
| 5 | Executor skills | one identical intro paragraph · rewrite each stage · core only | **as recommended** | The gate and commit come from `show`; one paragraph avoids restating per-stage text the CLI already overrides. |
| 6 | Autopilot skill | three small `decisions` additions · none | **as recommended** | §12.6 allows `decisions` gates in a run; the orchestrator must record them and review the whole diff at the close. |
| 7 | Commit subjects naming the task under `"current"` | end each subject with `(<ID>)` · say nothing | **as recommended** | `review`'s `commits` lists only subjects naming the task; the push question needs them. |
| 8 | `init`'s seeded config lacks `task_branch` and `commit` | leave · add commented lines · follow-up | **leave, no follow-up** | Both keys default correctly; §4 and the README document them. |
| 9 | (orchestrator) Step 3's "stop and ask … if the checkout is not on the branch the human means to work on" | a concrete rule · keep | **a concrete rule** | Under `"current"` any checked-out branch is the task's. Stop and ask only when `HEAD` is detached (`branch` null) or when the task's live claim names a different branch than the checked-out one; otherwise proceed without asking. |
