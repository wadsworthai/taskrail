# T074 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Run this task | — | **run 20260915-5 with `autopilot start --tasks T074,T075`** | The human's instruction ("lanza T074 y T075") after merging T073. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Touch map, T074's part (run decision 1) | split by diagnosis · serialize | **T074 changes only `autopilot/merged.py` (`_cleanup`), a regression test in `tests/test_autopilot_merged.py`, the `autopilot merged` row of DESIGN.md's command table and one CHANGELOG bullet; not `gitutil.py`, `query.py`, `cli.py` or the skills, which stay available to T075** | The two lanes then share only the changelog, a known class, and separate DESIGN.md rows. |

## diagnose gate

Reviewed: the artifact `docs/bugs/T074-refuse-merged-cleanup-for-a-worktree-tha.md` (commit `3bb5e34`, the
artifact and its index row only); the reproduction with `autopilot merged --cleanup` itself in a scratch
repository (exit 0, the nested worktree's untracked `WORK.md` deleted, its entry left prunable); the four
plain `git worktree remove` cases (an ignored nested worktree, locked or not, and ignored non-worktree
content are deleted; a nested worktree in a directory that is not ignored is refused by both taskrail and
git). On `fd4290b`, `merged._cleanup` lists `_worktree_entries(root)` only to find the task's own entry and
`_remove_worktree` runs `git worktree remove` without `--force`; T031's feature document records that
ignored files do not refuse cleanup. The root cause is located. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | What counts as "contains" | registered worktrees inside the path whose directory still exists · every registered entry inside, prunable ones included | as recommended | Locked or not, ignored or not, an existing nested worktree has work to lose; a prunable entry whose directory is gone has none, and refusing on it would only force a `git worktree prune`. |
| 2 | Refusal message and exit code | exit 5 with the message only · also a `cleanup.contains` JSON list | as recommended | It matches the other cleanup refusals (`cleanup.refused` and stderr), and the message names the paths; no schema change is needed. |
| 3 | Ignored content that is not a worktree | no block and no follow-up · refuse on an ignored directory holding a `.git` entry · follow-up task | as recommended | T031 decided ignored files do not refuse, lanes nearly always hold ignored `.venv/` and `__pycache__/`, and taskrail never creates a standalone repository inside a lane. |
| 4 | `lint` not configured | — | noted | Reported by `taskrail checks` as not configured. |

## fix gate

Reviewed: commit `0d0fa16` (`git show`): in `merged._cleanup`, the worktree entries are read once and,
after the `locked` refusal and before the dirty check, a registered worktree other than the task's whose
path is inside it (`_inside(path, e["path"])`, the argument order of the existing current-directory check)
and whose directory exists refuses cleanup with exit 5; the regression test
`test_cleanup_refuses_a_worktree_that_contains_other_worktrees` (a locked ignored nested worktree with
untracked work, a prunable entry that does not refuse, a non-ignored nested worktree, then success after
`git worktree move`), which the lane reports failing with exit 0 against the unfixed code; the DESIGN.md
`autopilot merged` row; one CHANGELOG bullet. The touched files match the touch map. Re-ran
`taskrail checks T074 --stage fix`: `test` gave `1037 passed in 140.26s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · a JSON list of nested paths · the check after the dirty check | as recommended | It is the guard approved at diagnose, under a regression test observed failing for the root cause; placed first, it gives the precise reason for a nested worktree that is not ignored too. |

## close

Reviewed: the impact stage recorded that nothing else was found and no follow-up was opened (`8a649e6`,
the artifact only). `taskrail done` is committed on its own (`978a5ea`); the backlog differs from
`origin/main` only in this task's row, as `✅`. `governing_touched` is empty, the branch has no upstream,
and `review --json` reported `rebase.needed: false`. The fix-stage checks passed at `0d0fa16` and only the
artifact and the row changed since. `autopilot status` lists `DESIGN.md` as touched by T074 and T075,
which the touch map covers (separate rows of the command table), and the changelog and indexes as known
classes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | `fix(autopilot)` · `fix(cli)` | **`fix(autopilot)`** | The change is in `autopilot merged --cleanup`. |
