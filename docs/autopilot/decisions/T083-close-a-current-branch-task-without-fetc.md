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

## implement gate

Reviewed: `git diff be210d3..482dd54` — `cmd_show`'s `close.review`, `cmd_review`'s early branch
into `_review_current` (publish refusal, closed check, no record fetch, git fetch, rebase or push),
the extracted `_review_closed` and `_review_title_body` (the task-branch path unchanged), `review.upstream`
and its constants, `prior.matching_commits(head_only=…)`, the four narrowed assertions in
`tests/test_commit_policy.py`, the DESIGN.md §5.1, §6.4, §7, §7.1 and §13 changes and the CHANGELOG
bullet; the new `tests/test_review_current.py` reported 15 of 16 failing before the code with the
premise's exit 2; the checks re-run with `taskrail checks T083 --stage implement` (1134 passed, lint not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | approve · change | **approve** | The diff matches the plan and the plan-gate answers; every criterion has a test observed failing first (criterion 7 guards existing exit codes). |
| 2 | `head_only` flag instead of a `revisions` list | keep · list argument | **as recommended** | One extra caller, and the default path stays as it was. |
| 3 | Narrowing T081's `close` assertions to `close.commit` | narrow · compare whole object | **as recommended** | Those tests cover `close.commit`; `close.review` has its own test here. |
