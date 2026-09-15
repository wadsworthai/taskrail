# T072 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The form of `worktree` in `show`, `list`, `next` and `autopilot next` (diagnose decision 1) | always absolute · relative to the repository's main checkout | **relative to the main checkout** | Decided by the human. A change to the CLI's JSON contract. |
| 2 | A follow-up task for `new --workspace` and `workspace` nesting a new worktree inside the lane that runs them | open it · note it only | **open it** | Decided by the human. |

Answered by the human (repository owner), in the orchestrator session.

## diagnose gate

Reviewed: the artifact `docs/bugs/T072-report-a-task-s-worktree-path-in-one-for.md` (commit
`fd6ace5`, the artifact and its index row only), the reproduction matrix in a scratch repository, and
`query.worktree_path` on `e3a57ca`, which makes an existing worktree relative to `config.root` — the
checkout running the command — and leaves one not yet created as `<worktree_dir>/<branch>`. Reproduced
in this clone: `taskrail show T072 --json` gives `.worktrees/T072-…` from the main checkout and the
absolute path with `--root` at the task's worktree. The root cause is located. The stage defines no
checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which form `worktree` takes | absolute · relative to the main checkout | **relative to the repository's main checkout (the main worktree, the first entry of `git worktree list`), computed the same from every checkout; a worktree outside it uses `..` segments** | Decided by the human. |
| 2 | Where a worktree not created yet resolves | against the running checkout · against the main checkout | **against the main checkout: `<worktree_dir>/<branch>`, unchanged as a string** | Follows from decision 1: one value from every checkout. It disagrees with where `new --workspace` and `workspace` create a worktree when run inside a lane; that is the follow-up task. |
| 3 | Open the follow-up task | open · note only | **open it at the impact stage, after reproducing it** | Decided by the human. |

Instructions given with the answers: since a relative `worktree` only resolves against the main
checkout, bring its consumers in line in the fix stage — the `taskrail` skill's workspace step (say
the path is relative to the main checkout and run `git -C <main checkout> worktree add --no-track
<worktree> …`, naming how to find the main checkout, such as the first entry of
`git worktree list --porcelain`), the lane brief's `<WORKTREE>` (the orchestrator fills it as an
absolute path: the main checkout joined with `worktree`), and DESIGN.md §7's `show` row. If a consumer
cannot be served without a new JSON field, stop at the fix gate and ask instead of adding one.

## fix gate

Reviewed: commit `34edbdc` (`git show`): `gitutil.main_worktree` (the first entry of
`git worktree list --porcelain`), `query.worktree_path` returning `os.path.relpath` against it, cached
per project and falling back to the running root when git fails; the regression test
`tests/test_worktree_path.py`, `show` and `list` from the main checkout, a nested worktree and one
outside the repository, reported by the lane as 6 failing against the unfixed code for the root cause;
one absolute assertion in `tests/test_task_branch.py` rewritten to the new form; the `taskrail` skill's
workspace step and the lane brief's `<WORKTREE>` note, with their installed copies; DESIGN.md §7; one
CHANGELOG bullet. No JSON field was added. Re-ran `taskrail checks T072 --stage fix`: `test` gave
`1028 passed in 146.06s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix, with the first `git worktree list` entry as the main checkout (running root as fallback) and `.` for a branch checked out in the main checkout | approve · report the main checkout otherwise | as recommended | Git documents the main worktree as listed first, which holds with a separate git dir and in submodules where the common dir's parent does not; `.` is the consistent relative path. |
| 2 | A separate regression test through `autopilot next` | no · add one | as recommended | `autopilot next` copies the field from `query.task_dict`, which the new tests cover, and `test_autopilot_named.py` already asserts the form through it. |

## close

Reviewed: the impact stage reproduced, in a scratch repository, `new --workspace` and `workspace` run
inside a lane creating the new worktree below that lane, and opened T073 (bug, E02) for it (`064dd85`,
the row only; the artifact's *Impact* section in `9f54030`). `taskrail done` is committed on its own
(`daa19c8`); the backlog differs from `origin/main` only in this task's row, as `✅`, and T073's row.
`governing_touched` is empty, the branch has no upstream, and `review --json` reported
`rebase.needed: false`. The fix-stage checks passed at `34edbdc` and only the backlog and the artifact
changed since.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | `fix(cli)` · `feat(cli)` | **`fix(cli)`** | It corrects a field that depended on the running checkout. |
| 2 | Mark the change breaking | not breaking · `--breaking` | **not breaking** | From the main checkout, where the skills read it, the value is unchanged for every worktree under it; only runs from inside a worktree or for a worktree outside the repository change, and the skill and lane brief that consume the field were updated in the same change. The human can still mark it breaking in the pull request title before merging. |
