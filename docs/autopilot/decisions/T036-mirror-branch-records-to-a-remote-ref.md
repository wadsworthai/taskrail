# T036 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T036-mirror-branch-records-to-a-remote-ref.md` (commit
`9870d48`), its eleven acceptance criteria, the reproduction (a second clone resolves a renamed
task to its template branch and blocks its dependent on the mainline), the git behaviour probes,
and a separate defect found on the way: `claims._delete_remote` leases without an expected commit,
so `release --force` — and therefore `done` — fails with exit 2 whenever `claim_remote` is set.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | Setting | new `[git].branch_record_remote`, off · reuse `claim_remote` · boolean requiring `claim_remote` | **new key, off by default** | Records outlive claims and add one ref per task; a repository that enabled remote claims must not start publishing more refs after an upgrade without choosing to. |
| D2 | Ref name and content | one parentless ref per task · one shared ref | **`refs/taskrail/branches/<ID>` with `branch.json` (`id`, `branch`, `recorded`)** | Independent leases per task, the same shape as remote claims; nothing private. |
| D3 | Reading and fetching | `--fetch` on `show`/`list`/`next` plus automatic fetch in `claim`, `branch`, `new --workspace`, `review` · `show` only · none · separate command | **as recommended, and update core skill step 3** | Read-only commands stay offline by default, and the skill fetches before choosing a base, where a second clone would otherwise pick the wrong one. |
| D4 | Disagreement | later `recorded` wins, written locally · remote wins · local wins | **later `recorded` wins** | Neither side silently undoes the other; clock drift is repaired by running `branch` again. |
| D5 | Failures | warn, report `record_remote`, exit unchanged · exit 4 on a rejected lease | **warn and report** | Local state stays correct and `branch` is the retry; a rejected lease is reported in the JSON for anyone who needs to act. |
| D6 | Cleanup | none, documented · follow-up | **none, documented; no follow-up now** | Refs are tiny; pruning merged tasks belongs with merge follow-through if it is ever needed. |
| D7 | Remote-claim lease bug | follow-up task · fix inside T036 | **follow-up bug task, opened at implement with `taskrail new`** | It breaks `done` for every repository with `claim_remote` today, independent of branch records; a separate pull request can be merged first. T036 must not depend on its fix. |
| D8 | `new --local-only` | no · add | **no** | A failed push only warns there. |

Plan approved. The lane must push only to local bare remotes and remove its scratch repositories
under a temporary directory when it no longer needs them.

## implement gate

Reviewed: commits `1b9465a` (T037) and `218dd1e` (`config.py` key, `gitutil.write_file_commit`,
`branches.fetch`/`push`, `cli.py` fetch and push points and `--fetch`, core skill step 3, DESIGN.md
§4, §6.1, §6.2, §6.4, §7, README, CHANGELOG, `tests/test_branch_records_remote.py`). Re-ran
`uv run pytest -q` in the lane's worktree: 385 passed. The new tests
failed before the code, and two deliberate breakages (a no-op fetch, adopting every remote record)
failed the tests that cover them. A push leases on this clone's copy of the remote ref, so a record
another clone pushed meanwhile is never overwritten.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Follows D1–D8; every criterion maps to a test seen failing. |
| 2 | `new` reports `record_remote` only with `--branch` | only then · always, `null` otherwise | **only with `--branch`** | `new`'s output stays unchanged when no record is written. |
| 3 | Close rebase onto T029 and T035 | keep both sides · stop and ask | **keep both sides** | Index rows keep both; DESIGN.md keeps T029's §4/§12 text and adds this branch's key and §6/§7 text; in `cmd_claim` T029's `--run` block stays and this branch's record push follows `_freeze_branch`; regenerate the installed skill and manifest with `upgrade --force` if they conflict. |

## rebase after T029 and T035

The lane rebased onto `origin/main` (`2312a2a`) at close, as decided at the implement gate.
Checked by the orchestrator before publishing: no conflict markers, `TODO.md` differs from `main`
only in T036 `✅` and the added T037 row, the skill source differs only in step 3, `upgrade` reports
nothing to create or update, `pytest -q` 485 passed, `taskrail validate` 0 errors. The branch's
upstream, set to `origin/main` by `git worktree add`, was unset so no plain `git push` can target
the mainline.

## rebase after T034 and T037

T034 (`0f01370`) and T037 (`d092c96`) were squash-merged into `main`. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both rows · stop | **keep both** | Rows added on both sides. |
| 2 | Conflicts in `TODO.md` | union by ID, `✅` wins · stop | **union by ID** | T037 is `✅` on `main` and `⬜` here; no `Reopens: T037` commit. The commit that opened T037 on this branch became empty and was dropped. |

`claims.py` merged without conflict: T037's lease fix sits beside this branch's `write_file_commit`
call. After the rebase: no conflict markers, `pytest -q` 500 passed, `taskrail validate` 0 errors,
`upgrade` reports nothing to create or update.
