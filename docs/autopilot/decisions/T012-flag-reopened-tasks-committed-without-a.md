# T012 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T012-flag-reopened-tasks-committed-without-a.md` (commit
`6efb7b8`), its eleven acceptance criteria, and the lane's measurements: this repository's backlog
history (31 commits) reads in about 40 ms with no reopens, and a synthetic 1,000-commit history
takes about 6 s to parse, hence the required text pre-filter.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Severity | warning `reopen-untraced` · error for reopens not yet on a mainline | **warning** | Pushed history cannot be reworded; an error would block every later commit and CI run. |
| 2 | History window | last 500 backlog-changing commits from `HEAD`, `--history-limit`, `--no-history` · `<mainline>..HEAD` · unbounded | **as recommended** | Sees reopens committed on the mainline and squashes that lost the trailer, with a bounded cost. |
| 3 | Discarded tasks reopened | include · done only | **include** | `reopen` accepts discarded tasks and writes the same trailer. |
| 4 | Uncommitted reopens | not reported · informational note | **not reported** | The pre-commit hook runs before the message exists and would warn on every correct `taskrail reopen`. |
| 5 | Follow-up for the generated GitHub workflow's shallow checkout | open a chore now · record only | **open it** (kind `chore`, epic E02, committed on this branch) | The check is inert in that workflow until it fetches full history, and the fix belongs in `install.py`, outside this task. |

Plan approved.

## implement gate

Reviewed: commits `b4d5561` (T039) and `68fdae4` (`history.py`, the `cmd_validate` hook with
`--no-history` and `--history-limit`, DESIGN.md §7, README, CHANGELOG, `tests/test_history.py`).
Re-ran the 28 new tests in the lane's worktree: all pass. The tests failed at collection before the
code, which proves little on its own; six deliberate breakages did, and the one no test caught (an
epic-file rule) was removed rather than kept untested. This repository validates in 0.16 s with 32
commits examined and no warning.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve, with epic files read by the working tree's paths and `skipped: "no commits"` | approve · changes | **approve** | Removing an untested rule is better than keeping it; a row moved between files is still no change because every revision is read across all those paths. |
| 2 | T039 dependency on T012 | none · depends on T012 | **none** | The workflow's `fetch-depth: 0` is correct on its own. |

## verify, close and rebase after T024

The verify stage covered a hand reopen, an empty acknowledgment commit, the CLI reopen with its
trailer, `epic split` across revisions (no false warning; a reopen before the split still reported
at the row's new place), merges, a shallow clone and a directory outside git, with no gap against
the plan. T024 was squash-merged into `main` as `977064f`; the orchestrator rebased the branch.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/features/README.md`, `docs/autopilot/decisions/README.md`, CHANGELOG | keep both · stop | **keep both** | Rows and bullets added on both sides; one bullet each for T024 and T012. |

No code conflicted. After the rebase: `TODO.md` differs from `main` in T012 `✅` and the added T039
row, `pytest -q` 693 passed, `taskrail validate` 0 errors and 0 warnings (the history check included),
`upgrade` reports nothing to create or update.
