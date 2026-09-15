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

## fix gate

Reviewed: commit `8e9be3d` (`git show`): `gitutil.main_worktree` reads the first porcelain block and returns
its parent when the block holds a `bare` line; `query.task_dict` adds `worktree_base`
(`str(main_checkout)`, `null` with `worktree`), inherited by `list`, `next` and `autopilot next`; the
comment in `cli._workspace_target`; the `taskrail` skill's workspace step and the lane brief's `<WORKTREE>`
note now use `worktree_base` and no longer name `git worktree list`, with their installed copies;
DESIGN.md §7's `show`, `list` and `new` rows and the `workspace` paragraph (the `autopilot merged` row
untouched); one CHANGELOG bullet; `tests/test_bare_layout.py`, 15 cases the lane reports all failing
against the unfixed code. The touched files match the touch map. Re-ran `taskrail checks T075 --stage fix`:
`test` gave `1051 passed in 145.96s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · request changes | as recommended | It implements both of the human's decisions under regression tests observed failing for the root cause. |
| 2 | Name the worktree base in DESIGN.md §8's "Skills never compute paths" sentence | leave it · add it | as recommended | The sentence still holds with `worktree_base` reported by `show`, and §7 documents the field. |

## close

Reviewed: the impact stage recorded what it checked — other readers of the base, other text deriving it
from `git worktree list`, T074's merged guard in a bare layout, tests naming the main checkout — and
opened no follow-up (`b1352bf`, the artifact only). `taskrail done` is committed on its own (`f46b0d8`);
the backlog differed from the base only in this task's row, as `✅`. `governing_touched` is empty and the
branch has no upstream. `review --json` reported `rebase.needed: true` onto `origin/main`, which had gained
T074.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Reword T072's unreleased CHANGELOG bullet, which still describes joining against the main checkout | keep it · reword it | as recommended: **keep it** | It records T072's change, and T075's bullet in the same *Unreleased* section describes the result. |
| 2 | Pull request type and scope | `fix(cli)` · `feat(cli)` | **`fix(cli)`** | It corrects where worktrees are reported and created in a bare layout; `worktree_base` is the contract that fix needs. |

## rebase after T074

T074 was merged into `main` (`fe270eb`). The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/bugs/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |
| 2 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |
| 3 | Conflict in `CHANGELOG.md` | keep both · stop | **keep both, each once** | Bullets added under *Unreleased* by both sides, a known class. |
| 4 | Conflict in `TODO.md` (T074 `✅` on the base, T075 `✅` on the branch) | both `✅` · stop | **both `✅`** | Backlog rows, a known class: a `✅` on either side stays, and neither side has a `Reopens:` commit. |

`DESIGN.md` merged without conflict (T074's `autopilot merged` row and T075's rows are separate lines).
After the rebase: `git diff --check origin/main` reports nothing, `git diff origin/main --stat` lists only
this task's files, `taskrail upgrade` reports every file up to date, `taskrail checks T075` gave
`1052 passed in 146.95s` (`lint` not configured), and `taskrail validate` reports
`64 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
