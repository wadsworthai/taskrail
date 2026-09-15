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
