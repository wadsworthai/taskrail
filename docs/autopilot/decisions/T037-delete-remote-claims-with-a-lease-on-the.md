# T037 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the write-up `docs/bugs/T037-delete-remote-claims-with-a-lease-on-the.md` (commit
`a3a4e2a`), the reproductions (`release --force`, `done`, `discard` and `claim --takeover` all exit
2 with `claim_remote` set, and `done`/`discard` leave the row written with both claims in place),
the git lease probes on a ref outside `refs/heads`, and the table of every remote push and delete
path. The workspace was set up by cherry-picking the row from T036's branch, as instructed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Claim record without `remote.commit` | read the ref and compare contents · refuse with a clear message · lease on whatever `ls-remote` returns | **refuse with a clear message** naming `--local-only` and the ref to delete by hand, in both `release` and `rename_branch` | Every version of taskrail records the commit, so only a damaged record lacks it; a content-comparing lookup adds code for that case, and leasing blindly could delete another clone's claim. |
| 2 | Order and exit code in `done`/`discard` | row first, catch the failure, keep the local claim, exit 2 naming the retry · leave as is · exit 0 with a warning | **row first; exit 2 saying the row was written and naming `taskrail release <ID> --force`** | Releasing first could free a task whose row write still fails; hiding a claim other clones still see is worse than a partial success, as T019 decided for a failed claim re-push. |
| 3 | Scope | `claims.py` `_delete_remote` and `rename_branch`, `cli.py` `_change_status`, tests in `test_claims.py` · wider | **approve** | Stays clear of T036's branch records and T030's autopilot files. |

Diagnosis approved with decision 1 changed to the smaller refusal. The lane must use local bare
remotes only and remove its scratch repositories when it no longer needs them.

## fix gate

Reviewed: commit `e55bba7` (`claims._delete_remote` and `rename_branch`, `cli._change_status`,
eleven tests in `tests/test_claims.py`, CHANGELOG, write-up). Re-ran `uv run pytest -q` in the lane's worktree: 480 passed. Ten tests failed on the unfixed code:
five with git's `stale info` rejection and five for the messages decided at diagnosis. The CLI run
covered `release --force`, `done`, `claim --takeover`, a rename followed by a forced release, a
remote ref holding another commit, and records without `remote.commit`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · changes | **approve** | The lease is always the recorded commit, `force` only waives the owner check, and a failed close says the row was written. |
| 2 | `done`/`discard` on a record without `remote.commit` suggests a `--force` retry that refuses again | accept · special-case the hint | **accept** | The inner message names `--local-only` and the manual delete, which is the right action; only a damaged record reaches it. |
| 3 | Guard test that passes before the fix | keep · drop | **keep** | It is the only test pinning that `--force` never deletes another clone's claim, which the new lease must preserve. |

The orchestrator unset the branch's upstream (set to `origin/main` by `git worktree add`).

## rebase after T034

T034 was squash-merged into `main` as `0f01370`. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/bugs/README.md` and `docs/autopilot/decisions/README.md` | keep both rows · stop | **keep both** | Rows added on both sides. |

After the rebase: no conflict markers, `TODO.md` differs from `main` only in the added T037 row,
`pytest -q` 484 passed, `taskrail validate` 0 errors, `upgrade` reports nothing to create or update.
