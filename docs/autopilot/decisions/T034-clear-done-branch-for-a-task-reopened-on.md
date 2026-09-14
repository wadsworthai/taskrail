# T034 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the write-up `docs/bugs/T034-clear-done-branch-for-a-task-reopened-on.md` (commit
`99ba96e`), the reproduction (a task reopened on `main` stays `done-branch`, hidden from `next`,
and `claim` exits 5, through the local branch or its remote copy alone), and the probe of the
proposed git query, including a second done on a branch that contains the reopen.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Diagnosis and fix | approve · changes | **approve** | Drop a ✅ tip when a mainline ref has a `Reopens: <ID>` commit the tip lacks; run only for tasks that would otherwise be `done-branch`, on local refs, cached. It matches the backlog conflict rule. Also cover in a test the reopen of a task whose earlier reopen the stale tip already contains (a second reopen cycle). |
| 2 | Clear the recorded branch on reopen | no · follow-up about guidance · clear in `reopen` | **no, and no follow-up** | Records survive `reopen` by design (§6.4) and clearing wouldn't fix this. When the old branch still exists, the skill's "stop and ask" is the right outcome: a human decides whether to delete or reuse a stale branch. |
| 3 | Trailer match | tolerate whitespace like `review.REOPENS` · exact | **tolerate whitespace** | Squash bodies edited in a web UI can carry trailing spaces or CRLF; one pattern for taskrail's own code. |

Diagnosis approved. The lane must remove its scratch repositories under a temporary directory
when it no longer needs them.

## fix gate

Reviewed: commit `5ca09d0` (`stack.py` `_reopened_since`, four regression tests in
`tests/test_stacked_base.py`, DESIGN.md §7, CHANGELOG). Re-ran `uv run
pytest -q` in the lane's worktree: 373 passed. The four tests failed on the unfixed code for the
diagnosed reason. `review.REOPENS` is multiline with `\s*` around the ID, so a trailer line ending
in spaces and `\r` still matches, which the whitespace test proves.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · changes | **approve** | Minimal, only for would-be `done-branch` tips, signatures unchanged, pattern reused as decided. |

## rebase after T029 and T035

T029 (`45eb96f`) and T035 (`2312a2a`) were squash-merged into `main`. The lane rebased onto T029
at close and the orchestrator rebased again onto T035.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` (both times) | keep both rows · stop | **keep both** | Rows added on both sides. |

After the rebase: no conflict markers, `pytest -q` 473 passed, `taskrail validate` 0 errors,
`upgrade` reports nothing to create or update. `stack.done_on_branch` and `stack._read_statuses`
keep their signatures, so the autopilot's `status` is unaffected.
