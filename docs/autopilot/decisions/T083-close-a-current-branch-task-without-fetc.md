# T083 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan `docs/features/T083-close-a-current-branch-task-without-fetc.md` (commit
`c51ac56`, the artifact and its index row only, clean worktree), its 10 acceptance criteria against
DESIGN.md §13.5, the `close.review` part of §13.3 and the T083 rows of §13.8 and TODO.md, and the
premise reproduced on `59adba0` (`review` exits 2 "could not determine the base of main" under
`task_branch = "current"`, and fetches before failing). The stage defines no checks. This is the
only live lane, so the touch map is the plan's affected areas.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | A `show` text line for `close.review` | no line · `review report ([git].task_branch)` under `"current"` | **as recommended** | It follows from `task_branch`, which the JSON reports; the default text stays unchanged. |
| 2 | Commits scanned for `Reopens:` trailers in the reference body | `<upstream>..HEAD`, all of `HEAD` without an upstream · always all of `HEAD` | **as recommended** | Matches what a push would send, like the rebase range under `"task"`. |
| 3 | Refuse on a detached `HEAD` | no refusal, `head` and `upstream` null · exit 5 | **as recommended** | §13.5: `review` does not refuse because of the branch. |
| 4 | `upstream` when the configured upstream ref is gone | null · `{ref, ahead: null}` | **as recommended** | Nothing to compare against is the same as no upstream. |
| 5 | The rebase `reason` wording | `[git].task_branch is "current": review does not rebase` · other | **as recommended** | Names the setting, as §13.5 requires. |
| 6 | Approve the plan | approve · change | **approve** | The criteria cover §13.5 and the T083 row, and the change stays inside `review`, `show`, `prior.matching_commits` and the docs. |
