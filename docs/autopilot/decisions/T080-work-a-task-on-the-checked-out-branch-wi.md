# T080 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan `docs/features/T080-work-a-task-on-the-checked-out-branch-wi.md` (commit
`362a96e`, the artifact and its index row only, clean worktree), its 14 acceptance criteria against
DESIGN.md §13.1, §13.2, §13.6, §13.7 and the T080 rows of §13.8 and TODO.md. The stage defines no
checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `branch` form of `prior_work.commits` under `"current"` | pass no branch · pass the checked-out branch | **as recommended** | Subjects naming `main` or another shared branch are not evidence of work on the task; §13.2 already drops `branches` for the same reason. |
| 2 | Detached-`HEAD` claim warning text under `"current"` | today's text · "check out a branch to work the task on" | **"check out a branch to work the task on"** | Today's text names `taskrail branch`, which exits 5 under `"current"`; §13.2 keeps the warning, and a warning must not point to a refused command. Say so in §13.2's pointer and §6.1. |
| 3 | Where the refusals happen | after the task or epic is found, before fetch or reservation · before the lookup | **as recommended** | Same order as §13.5's `review --publish`; an unknown ID keeps exit 3. |
| 4 | Moving §13.2, and editing §12.2 | pointer line marked implemented, §12.2 edited · keep §13.2 whole | **as recommended** | Run decision 1 (the §13 marking convention); §12.2 is where the refusal sits next to the `enabled` refusal. |
| 5 | `review` exits 2 under `"current"` until T083 | accept · special-case now | **as recommended** | `review` under `"current"` is T083's, which follows once T080 and T081 merge; only a repository that sets the new key reaches it, and no release happens in between. Note it in the artifact's risks. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How §13 is marked once a part is implemented (run decision 1) | one-line pointer for a moved subsection, in-place marks for shared bullets and own §13.8 row · keep full text | **one-line pointer and in-place marks; never §13's introduction, summary table or another lane's lines** | One place per rule, same convention on T080, T081, T082. |
| 2 | Touch map, T080's part (run decision 3) | as planned · narrower | **config.py (`task_branch` field and its load checks, own lines next to `worktree`), branches.py, stack.py `_find`, query.py `base_dict` and one `task_branch` line in `task_dict`, cli.py `cmd_show` prior-work call, `_freeze_branch`, `cmd_new` refusal and warning, `cmd_workspace`, `cmd_branch`, a refusal helper, checks.py `worktree()`, branchrows.py `branch_of`, autopilot/commands.py `_task_branch_refusal` with one call line in `cmd_start`, `cmd_extend`, `cmd_next`; new tests/test_current_branch.py; DESIGN.md §4 task_branch line and half of the planned note, §6.1, §6.4, §7 rows show/next/new/workspace/branch, *Dependencies and the base*, §7.2, §7.5, task_branch half of §12.2's planned bullet, §13.2, §13.6/§13.7 task_branch bullets, §13.8 T080 row; one CHANGELOG bullet** | From T080's plan; shared with T081 only as separate hunks (config load, `task_dict`, the autopilot refusal call lines, §4 and §12.2 planned notes — keep both halves), and with T082 nothing but the changelog. |
