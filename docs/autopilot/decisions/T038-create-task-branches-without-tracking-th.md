# T038 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

The orchestrator opened this task with `taskrail new --workspace` after noticing that every lane's
branch, and that workspace's own branch, tracked `origin/main`; it committed the row and unset the
upstream before starting the lane.

## scope gate

Reviewed: the scope in `docs/chores/T038-create-task-branches-without-tracking-th.md` (commit
`a52a4cc`), and the evidence: under `push.default=upstream` a plain `git push` from a task branch
created from `origin/main` landed the task's commit on `main`; `--no-track` leaves no upstream even
with `branch.autoSetupMerge=always`; `new --workspace` sets `branch.<task>.merge refs/heads/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Apply `--no-track` to every base | unconditionally, CLI and skill · only for remote-tracking bases | **unconditionally** | A stacked base is a dependency's pull request branch, and `autoSetupMerge=always` tracks local start points too. |
| 2 | `review --publish` keeps `--set-upstream` | keep · drop | **keep** | The upstream then is the task's own remote branch, which is what a plain push or pull should reach. |
| 3 | Two clauses in DESIGN.md | add · leave | **add** | The design states the rule the CLI and skill follow. |
| 4 | Existing branches that track the mainline | no migration, mention the fix in the CHANGELOG · follow-up check | **no migration; the CHANGELOG bullet names `git branch --unset-upstream`** | Few branches are affected and the fix is one command; a detector is not worth its code. |

Change set approved.

## implement gate

Reviewed: commit `fb7c080` (`--no-track` in `_open_workspace`, core skill step 3 on top of T036's
text, DESIGN.md's two clauses, CHANGELOG, `test_workspace_branch_has_no_upstream`). Re-ran
`uv run pytest -q` in the lane's worktree: 504 passed. The new test failed
on the old code in all four cases (remote and local start points, both worktree modes). The
throwaway runs showed a plain push refused under `push.default=upstream`, `review --publish` setting
the task's own remote branch as upstream, and a stacked base left untracked.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Start point as a second test parameter | accept · two remote-base cases only | **accept** | Only a local start point exercises `branch.autoSetupMerge=always`. |
| 2 | Scope commit without attribution trailers | leave · reword | **leave** | The pull request is squash-merged, so branch commits never reach `main`; rewording would rewrite the orchestrator's decision commit too. |

## close and rebase after T030

The docs stage found nothing more to change: older task write-ups record the commands as they were
run at the time. The lane rebased onto `origin/main` (`53bd1fb`); the decisions index and CHANGELOG
conflicted and kept both, and the skill source keeps T036's and this task's step 3 text. Checked
before publishing: `pytest -q` 540 passed, `taskrail validate` 0 errors, `upgrade` reports nothing to
create or update, the branch has no upstream.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type | `fix` · `chore` | **`fix`** | It removes a hazard where a plain `git push` could land on the mainline; users should see it in the release notes. |

## rebase after T032, T031 and T005

T032 (`151e290`), T031 (`a41ca8a`) and T005 (`766b5da`) were squash-merged into `main`. The
orchestrator rebased the branch onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/autopilot/decisions/README.md` and CHANGELOG | keep both · stop | **keep both** | Rows and bullets added on both sides; one T038 bullet, last. |

No code, skill or manifest conflicted. After the rebase: no conflict markers, the skill source and
its installed copy keep `--no-track` in step 3, `pytest -q` passes, `taskrail validate` 0 errors,
`upgrade` reports nothing to create or update.
