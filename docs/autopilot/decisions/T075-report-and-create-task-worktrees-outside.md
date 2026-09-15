# T075 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Run this task | — | **run 20260915-5 with `autopilot start --tasks T074,T075`** | The human's instruction ("lanza T074 y T075") after merging T073. |
| 2 | In a bare clone with worktrees, the directory `worktree` is reported against and task worktrees are created under (diagnose decision 1) | the directory containing the bare repository · the first non-bare worktree · the running checkout, in bare layouts only | **the directory containing the bare repository** | Decided by the human, as the lane recommended: the same from every checkout, independent of which worktrees exist, and nesting nothing. |
| 3 | How the `taskrail` skill and the lane brief learn that base (diagnose decision 2) | an absolute JSON field · prose only | **an absolute field, `worktree_base`, beside `worktree`** | Decided by the human, departing from the lane's recommendation: DESIGN.md §8 says "Skills never compute paths", and the prose rule T072 added makes agents derive the base from `git worktree list`. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Touch map (run decisions 1 and 2) | split by diagnosis · serialize | **T074: `autopilot/merged.py` (`_cleanup`), its regression test, the `autopilot merged` row of DESIGN.md's command table, one CHANGELOG bullet. T075: `gitutil.main_worktree`, `query.main_checkout`/`worktree_path` and `query.task_dict` (`worktree_base`), at most the comment in `cli._workspace_target`, the `taskrail` skill's workspace step and the lane brief's `<WORKTREE>` note with their installed copies, DESIGN.md §7's rows for `show`, `list`, `next`, `new` and `workspace` and the paragraph on a row missing from its base, one CHANGELOG bullet, `tests/test_bare_layout.py`.** | The lanes share only the changelog, a known class, and separate DESIGN.md rows. |

## diagnose gate

Reviewed: the artifact `docs/bugs/T075-report-and-create-task-worktrees-outside.md` (commit `e95704e`, the
artifact and its index row only) and its reproduction in a control clone and three bare layouts (a bare
clone beside its worktree, a `.bare` directory with a `.git` file, a bare clone holding its worktree): in
each, `git worktree list --porcelain` names the bare directory first with a `bare` line, and
`new --workspace` creates the worktree inside it; with `safe.bareRepository=explicit`, `git -C <bare
directory>` fails. On `fd4290b`, `gitutil.main_worktree` returns the first `worktree` line and ignores the
attribute lines after it. The root cause is located. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The worktree base in a bare layout | parent of the bare directory · first non-bare worktree · running checkout · configuration · keep the bare directory | **the parent of the bare directory; an ordinary clone keeps its main checkout** | Decided by the human. |
| 2 | How the skill and the brief learn the base | absolute `worktree_base` field · prose only | **an absolute `worktree_base` field in `show`, `list`, `next` and `autopilot next`, `null` when `worktree` is `null`** | Decided by the human. |
| 3 | The touch map | as proposed · amended | **as proposed, plus `query.task_dict` for `worktree_base`** | The field follows from decision 2; `autopilot next` inherits it from `task_dict`. |

Instructions given with the answers: the skill's workspace step and the lane brief use `worktree_base`
joined with `worktree` (the skill creates the worktree with `git -C <this checkout> worktree add --no-track
<worktree_base>/<worktree> …`, which also works under `safe.bareRepository=explicit`), and no longer tell
agents to read `git worktree list`; DESIGN.md §7 documents `worktree_base` for every command that reports
`worktree`.
