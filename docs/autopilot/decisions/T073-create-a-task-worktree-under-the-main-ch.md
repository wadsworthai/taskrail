# T073 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Run this task | — | **run 20260915-4 with `autopilot start --tasks T073`** | The human's instruction ("lanza T073") after merging T072. |
| 2 | In a bare clone with worktrees, the fix moves `new --workspace` placement from the running worktree's `.worktrees/` into the bare directory, where `show` already reads paths since T072 (found at the impact stage) | publish now, T075 later · fix it in T073 · publish and run T074 and T075 | **publish now; T075 later** | Decided by the human, as recommended: the bare layout was already inconsistent since T072, is in no release, and T075 fixes reporting and placement together. |

Answered by the human (repository owner), in the orchestrator session.

## diagnose gate

Reviewed: the artifact `docs/bugs/T073-create-a-task-worktree-under-the-main-ch.md` (commit `1f470ac`,
the artifact and its index row only) and its reproduction in a scratch repository: `new --workspace`
and `workspace` run with `--root` at a lane create `<lane>/.worktrees/<branch>`, the existence check
misses a directory at `<main checkout>/.worktrees/<branch>`, and removing the lane leaves its nested
worktrees prunable, their uncommitted rows lost. On `87df06b`, `grep -rn worktree_dir src/taskrail`
finds the path built from `config.root` only in `cli._workspace_target` (line 579); `autopilot merged
--cleanup` checks `git status --porcelain --untracked-files=all` in the worktree it removes, which does
not list worktrees nested under an ignored `.worktrees/`. The root cause is located. The stage defines
no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Diagnosis and fix direction: place the worktree at `<main checkout>/<worktree_dir>/<branch>`, the existence check on that path, with the helper `show` uses made public as `query.main_checkout` | public helper · import the private `_main_checkout` | as recommended | It follows the human's decision at T072 that `worktree` is relative to the main checkout, so creation and reporting agree again; a helper used across modules should not be private. |
| 2 | Bare-repository layout (the first `git worktree list` entry is the bare directory) | follow-up task · special case now in `gitutil.main_worktree` | as recommended: **open a follow-up task at the impact stage** covering both reporting and placement for bare layouts | A special case would change T072's reporting too, which is outside this bug. |
| 3 | `autopilot merged --cleanup` removing a worktree that contains other registered worktrees | follow-up task · guard in this task · not tracked | as recommended: **open a follow-up task (kind bug) at the impact stage** so cleanup refuses such a worktree | It loses uncommitted work, so it must be tracked; this fix stops new nesting, but worktrees nested by earlier versions or by hand remain, and the guard is a separate change in `merged.py`. |
| 4 | Documentation | DESIGN.md §7 `new`/`workspace` rows and the `workspace` paragraph, a CHANGELOG entry, no skill change · also a sentence in the skill | as recommended | The skill's manual step already uses the main checkout since T072, and after these commands the agent works in the returned `workspace` path. |

## fix gate

Reviewed: commit `13055b9` (`git show`): `cli._workspace_target` builds the worktree path, and checks
its existence, under `query.main_checkout` (renamed from `_main_checkout`, whose only caller
`worktree_path` follows); the regression test `tests/test_workspace_placement.py`, run from the main
checkout and from a lane, which the lane reports as failing in its four lane cases against the unfixed
code for this cause while the main-checkout controls passed; DESIGN.md §7's `new` and `workspace` rows
and the `workspace` paragraph; one CHANGELOG bullet; the artifact. No skill change. Re-ran
`taskrail checks T073 --stage fix`: `test` gave `1036 passed in 163.19s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · request changes | as recommended | It is the change approved at diagnose, under a regression test observed failing for the root cause, with the checks passing. |
| 2 | DESIGN.md's `new` row with two asides in a row | keep · restructure | as recommended | The row stays accurate and readable in the table; the paragraph below carries the detail. |

## close

Reviewed: the impact stage ran `autopilot merged --cleanup` itself in a scratch repository and lost a
nested worktree's untracked file, leaving its entry prunable, and checked a bare clone with worktrees,
where the fix places `new --workspace`'s worktree inside the bare directory; it opened T074 (bug, the
cleanup guard) and T075 (bug, bare layouts) in `ef6c12c`, with the evidence in the artifact.
`taskrail done` is committed on its own (`b6e1aec`); the backlog differs from `origin/main` only in this
task's row, as `✅`, and the rows of T074 and T075. `governing_touched` is empty, the branch has no
upstream, and `review --json` reported `rebase.needed: false`. The fix-stage checks passed at `13055b9`
and only the backlog and the artifact changed since. The bare-layout effect was escalated (above).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | `fix(cli)` · `feat(cli)` | **`fix(cli)`** | It corrects where two commands create a worktree. |
