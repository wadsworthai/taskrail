# T017 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T017-branch-a-task-from-its-single-unmerged-d.md` (commit
`d41471f`), its twelve criteria, and the lane's reproduction of T007's evidence E1 plus a second
symptom: inside a finished dependency's worktree, a dependent task already looks pending and would
branch from a mainline that lacks the dependency's work.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | "Merged" means ✅ on the local or remote mainline | mainline · current checkout | **mainline** | The same answer in every checkout; it removes the wrong base inside a lane's worktree. |
| Q2 | `done-branch` with a live claim | `done-branch` wins · `claimed` wins | **`done-branch`** | The work is finished; the orchestrator must not dispatch it again. |
| Q3 | Two or more unmerged dependencies | `blocked` with `blocked_by` · new state | **`blocked`** | The reference behaviour makes such a task ineligible; reusing `blocked` means existing refusals apply and no consumer learns a new state. |
| Q4 | `base.commit` | fork point · tip of `onto` at claim time | **fork point** (`merge-base`) | Stays correct for `rebase --onto` even if `onto` moves before the claim. |
| Q5 | Stacked branch in `review` | rebase onto the dependency, PR targets the mainline · PR against the dependency · refuse publishing | **rebase onto the dependency; PR targets the mainline** | Branches are handed off dependencies first; after the dependency merges, follow-through rebases the dependent onto the mainline (T031). |
| Q6 | Claims read by older CLIs | accept, tolerant loader from now on · separate file | **accept; the loader ignores unknown keys** | No released consumer relies on the old format beyond 0.1.0's own claims, which stay local; tolerance prevents the same problem next time. |
| 7 | Scope | keep 5 points · split | **keep** | Coherent change; points order work, they do not budget it. |

Plan approved. The lane must remove its scratch repositories under `/tmp` when it no longer needs them.

## implement gate

Reviewed: commit `296f400` (`stack.py`, `query.py`, `claims.py`, `cli.py`, `model.py`, the core
skill, DESIGN.md §6.1, §6.2 and §7). Re-ran `uv run pytest -q` in the
lane's worktree: 278 passed. The four existing tests that changed only gained the new keys.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `base` in the remote claim (DESIGN.md §6.2) | keep · drop from the published copy | **keep** | It holds refs and a commit that already live on that remote, no machine details; §6.2 stays in the claims section T017 owns. |
| 2 | State column width in `list` and `next` | 11 · 9 | **11** | Text output is for people; aligned rows matter more than a two-space shift, and `--json` is the stable contract. |
| 3 | Approve the code | approve · changes | **approve, with one doc correction** | The code follows Q1–Q6. `done` releases the claim, so `base.commit` is gone by the time a finished dependent needs `rebase --onto`. DESIGN.md §6.1 must say the fork point is also `git merge-base HEAD <dependency branch>` while that branch exists, so follow-through computes it before removing the branch (T031). |
| 4 | Stale branch of a reopened task | fix now · follow-up | **follow-up task** | A task reopened on the mainline whose old branch still has `✅` reads as `done-branch` and `claim` refuses it. Follow-through deletes merged branches, so it is rare, and the refusal names the branch; a mainline `Reopens: <ID>` commit the branch lacks should clear the state. Opened at the docs stage with `taskrail new`, kind bug, depending on T017. |

## rebase after T028 and T027

T028 (`2b617b6`) and T027 (`0c94945`) were squash-merged into `main`. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both rows · stop | **keep both** | Both sides add an index row; a known additive class. |
| 2 | Conflict in `CHANGELOG.md` | keep both bullets · stop | **keep both** | Both sides add an `Unreleased` bullet. |

`DESIGN.md` merged without conflict (T028 edits §1, §11, §12; this branch §6 and §7). After the
rebase: no conflict markers, `pytest -q` 300 passed, `taskrail validate` 0 errors, T017 `done`,
`taskrail upgrade` reports every installed file unchanged.
