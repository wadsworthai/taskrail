# T031 — Detect squash merges by content and follow through with autopilot merged

Kind: feature · Epic: E02 · Status: verified

Source: the accepted autopilot design, `DESIGN.md` §12.1 (the `autopilot merged`
row), §12.4 (`done-merged`), §12.8 (*Merge follow-through*) and §6.1 (the fork point of a finished
dependent), with the evidence in `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md`
(E4). The plan-gate decisions are in
`docs/autopilot/decisions/T031-detect-squash-merges-by-content-and-foll.md` (Q1–Q10 as recommended,
no `--force` for cleanup). Builds on T029 (`taskrail/autopilot/`: run files, `status.done_on_mainline`,
`commands.register`), T019 (`branches.task_branch` and branch records) and T017 (`done-branch`,
stacked bases, `base` in the claim).

## Behaviour

Today nothing tells whether a task branch was squash-merged: ancestry sees nothing after a squash
(E4), `autopilot status` reports `done-merged` only from a `✅` row on a mainline ref, and removing
a finished lane's worktree and branch, and finding the `rebase --onto` command for the branches
stacked on it, is left to hand-typed git.

After this change, `taskrail autopilot merged <ID> [--run R] [--cleanup] [--no-fetch] [--json]`:

1. **Resolves the task and its branch.** The task must be in the checkout's backlog (exit 3
   otherwise). Its branch is the live claim's `branch` when a claim exists, else
   `branches.task_branch` — the T019 record, which outlives `done` and branch deletion, else the
   kind's template (Q1).
2. **Fetches once:** `git fetch --prune <remote>`, `<remote>` being the task mainline's remote
   (`review.resolve_remote`, as `review` uses). Skipped with `--no-fetch`, or when that remote is
   not configured at all (a local-only repository); `fetched` says which. A failing fetch exits 2.
3. **Picks the head to check** (Q2): the local branch `refs/heads/<branch>` when it exists — it is
   what `--cleanup` deletes, so its own commits must be the ones proven merged — else the
   remote-tracking copy `<remote>/<branch>` that survived the prune. Both SHAs are reported. With
   neither, the check falls back to a merge recorded earlier in a run (below); without one it exits 3.
4. **Picks the mainline ref:** the further-ahead of `<mainline>` and `<remote>/<mainline>`
   (`review.choose_base`). When they have diverged it checks `<remote>/<mainline>` first, then
   `<mainline>`, and reports `mainline.diverged`.
5. **Requires a finished branch** (Q3): the task's row must be `✅` at the head (read with
   `stack._read_statuses`, so epic files count). Otherwise `merged` is false with that reason: an
   unstarted branch is an ancestor of the mainline and its `merge-tree` is a no-op, so without this
   guard checks 1 and 4 would report it merged (see *Evidence*).
6. **Detects the merge**, stopping at the first check that proves it, with `M` the merge-base of
   the head and the mainline ref:
   1. `ancestor` — the head is an ancestor of the mainline. `commit` is the oldest first-parent
      commit that contains it (`git rev-list --first-parent --ancestry-path=<head> <head>..<mainline>`,
      last line): the head itself after a fast-forward, the merge commit otherwise.
   2. `tree` — a commit of `git log --first-parent M..<mainline>` has the head's tree; `commit` is
      the oldest one.
   3. `patch-id` — the stable patch-id of `git diff M <head>` equals that of a first-parent commit
      in `M..<mainline>`. One `git log --first-parent -p M..<mainline> | git patch-id --stable`
      pipeline, read newest first and stopped at the first match (Q9); `commit` is that commit.
   4. `merge-tree` — `git merge-tree --write-tree <mainline> <head>` writes the mainline's own
      tree; `commit` is the mainline tip checked.

   Each check's outcome is reported in `checks`, including the ones not reached. Two confirmations
   are reported and never used as proof: `row_done_on_mainline` (the `✅` on the mainline ref) and
   `title_commit` (a first-parent commit in `M..<mainline>` whose subject ends in `(<ID>)` or
   `(<ID>) (#<n>)`).
7. **Records the merge in runs** (Q4, Q5): with `--run R`, in that run (exit 3 for an unknown run
   or a task R does not hold); without it, in every run that holds the task — none in standalone
   use, which needs no run and no `[autopilot].enabled`. The lane entry gains
   `merged: {"via", "commit", "head", "mainline", "detected"}`; the lane's recorded `state` is left
   as the orchestrator set it. Nothing is written when `merged` is false.
   `status.done_on_mainline` then also counts a task with a recorded merge whose `commit` is still
   an ancestor of the local or remote mainline, so `status` reports it `done-merged` (and the run's
   `handoff.in_review` clears) even after `--cleanup` removed the branch, or when the squash lost
   the `✅`. A later run of `merged` on a task whose branches are gone reports the recorded merge
   with `via` unchanged and `recorded: true`.
8. **Lists stacked dependents** (Q6), computed before anything is removed: every task that lists
   `<ID>` in `Depends On`, is not `✅` on the mainline, and has a local or remote-tracking branch.
   For each:
   - `fork`: the live claim's `base.commit` when its `base.dependency` is `<ID>` (exact even if the
     dependency was rewritten later, `fork_source: "claim"`); otherwise
     `git merge-base <dependent head> <dependency head>` with the dependency head SHA resolved in
     step 3 — which works after the dependency's branch is deleted, since the SHA is already in hand
     (`fork_source: "merge-base"`); otherwise, when this run found no dependency head, the `head`
     recorded in the run (`fork_source: "run"`); otherwise `null` with a reason.
   - a dependent whose `fork` is already on the mainline branched from the mainline, not from the
     dependency: it is reported with `stacked: false` and no command;
   - `onto`: the dependent's base as `show` computes it after the fetch — the mainline once the
     dependency is `✅` there (`null` with its reason when diverged);
   - `command`: `git rebase --onto <onto> <fork>`, to run inside `worktree` (the dependent's
     checked-out worktree, else `null`): naming the branch as a third argument fails while another
     worktree has it checked out.
9. **`--cleanup`** (Q7, Q8) runs only when `merged` is true. In order: refuse, changing nothing, when
   the worktree that has the branch checked out is the main worktree, contains the current directory
   or `--root`, is locked, or has any change `git status --porcelain --untracked-files=all` reports
   (untracked files count; ignored files do not, as for `git worktree remove`); exit 4 when a live
   claim on the task belongs to another owner. Then `git worktree remove <path>`, then delete the
   local branch with `git update-ref -d refs/heads/<branch> <verified head SHA>`, so a commit added
   since the check keeps the branch; then release the caller's own claim if one is left. The remote
   branch is never deleted (§6.4); `cleanup.remote_branch` names it when it still exists. The T019
   branch record is kept (Q8). A cleanup with nothing left to remove succeeds.

Text output: one line `T001 merged into origin/main via patch-id at 1b1a198` (or
`T001 not merged into origin/main: <reason>`), then one line per cleanup action and one per
dependent with its command.

**Exit codes** (Q10): 0 when the check ran — merged or not — and any requested cleanup completed
or had nothing to do; 1 for an invalid backlog unless `--allow-invalid`; 2 for a failed fetch or
git error; 3 for an unknown task, an unknown run, a task the run does not hold, or no branch and no
recorded merge; 4 for cleanup against someone else's claim; 5 when `--cleanup` is refused (not
merged, dirty, current directory, main worktree, locked).

**Code shape:** a new `taskrail/autopilot/merged.py` holds detection, dependents, cleanup and the
`cmd_merged` handler; `commands.py` gains one import and one `add(...)` call; `status.py` changes
only inside `done_on_mainline`, away from the lines T030 edits.

## Acceptance criteria

Every scenario runs in a throwaway repository with a local bare `origin`, lanes in their own
worktrees, and merges made by a second clone that pushes to `origin`.

1. **Ancestor.** A finished task branch merged into `origin/main` with a merge commit reports
   `merged: true`, `via: "ancestor"`, `commit` the merge commit; fast-forwarded, `commit` is the
   head.
2. **Tree.** Squash-merged on an unchanged mainline: `via: "tree"`, `commit` the squash commit,
   `checks` shows `ancestor` false.
3. **Patch-id.** Squash-merged after an unrelated commit landed first: `via: "patch-id"`, `commit`
   the squash commit; `tree` false.
4. **Merge-tree.** The branch's changes reached the mainline in two separate commits, after an
   unrelated one: `via: "merge-tree"`, `commit` the mainline tip.
5. **Negatives.** An unmerged finished branch, and a squash-merged branch with one more commit
   added afterwards, report `merged: false`, `via: null`, every check false, exit 0. An unstarted
   branch at the mainline tip and a branch whose row is not `✅` at its head report `merged: false`
   with the not-finished reason, although `ancestor` would hold.
6. **Confirmations.** `row_done_on_mainline` and `title_commit` are reported for a squash titled
   `… (T001) (#3)`, and a `✅` added by hand on the mainline for an unmerged branch leaves `merged`
   false.
7. **Fetch.** Without `--no-fetch`, a merge pushed to `origin` after the last fetch is detected and
   a remote branch deleted on `origin` disappears from `origin/<branch>` (`fetched: true`);
   `--no-fetch` leaves the refs as they were; a repository without the remote skips the fetch; an
   unreachable remote exits 2.
8. **Heads.** Local branch gone and `origin/<branch>` present: detected on the remote copy,
   `head.ref` names it. Local present and remote pruned: detected on the local branch. Local branch
   with an unpushed commit after its squash-merged remote copy: `merged: false`. Neither branch and
   no recorded merge: exit 3. Unknown task: exit 3. A renamed branch (T019 record) is found after
   `done` released the claim.
9. **Runs.** With `--run R`, the lane of the task in R gains `merged` with `via`, `commit`, `head`,
   `mainline`, `detected`, keeps its `state`, and other run keys survive; `--run` unknown or not
   holding the task exits 3; without `--run` every run holding the task is updated and standalone
   use writes no run file; `merged: false` writes nothing; `[autopilot].enabled = false` does not
   stop it.
10. **Status.** A task whose squash dropped the `✅` (row resolved by hand to `⬜` on the mainline)
    is `done-merged` in `autopilot status` after `merged --run R` and not before; a recorded merge
    whose commit is no longer on either mainline ref is not; after `--cleanup`, a second `merged`
    reports `recorded: true` with the same `via` and exit 0.
11. **Cleanup.** After a verified merge, `--cleanup` removes the lane's worktree directory and
    `git worktree list` entry, deletes the local branch, keeps `origin/<branch>` when it exists and
    names it, keeps the branch record, and releases the caller's leftover claim.
12. **Cleanup refusals.** Exit 5 and nothing removed when: not merged; the worktree has a modified
    file; the worktree has only an untracked file; the command runs from inside the worktree; the
    branch is checked out in the main worktree; the worktree is locked. An ignored file alone does
    not refuse. Exit 4 for another owner's live claim. A commit added to the branch between the check
    and the deletion keeps the branch (the `update-ref` lease), exit 2.
13. **Dependents.** T002 stacked on T001's branch, claimed with `--run`: after T001 is
    squash-merged, `dependents` lists T002 with `fork` its claim's `base.commit`,
    `fork_source: "claim"`, `onto: "origin/main"`, `worktree`, and `command`; running that command
    in T002's worktree leaves only T002's commits on top of `origin/main`. With T002 done (claim
    released) the fork comes from `merge-base` with T001's head, also after `--cleanup` deleted
    T001's local branch and the remote branch was pruned in the same call. A dependent branched from
    the mainline reports `stacked: false` and no command. A second call after the dependency's
    branches are gone uses the run's recorded `head` (`fork_source: "run"`).
14. **Text and JSON.** The text form prints the merged line, cleanup actions and dependent commands;
    `--json` returns `id`, `branch`, `remote`, `fetched`, `mainline` (`ref`, `commit`, `diverged`),
    `head` (`ref`, `commit`, `local`, `remote`), `done_at_head`, `merged`, `via`, `commit`,
    `recorded`, `reason`, `checks`, `confirmations`, `runs`, `cleanup` and `dependents`.
15. **Existing behaviour and documentation.** The whole suite passes unchanged; `DESIGN.md` §12.1
    marks `merged` implemented with `--run` and `--no-fetch`, §12.4 describes the recorded merge,
    §12.8 marks detection and cleanup implemented with the finished-branch guard and the bounded
    patch-id range, §7's autopilot row names `merged`; `README.md` shows the command; `CHANGELOG.md`
    has one bullet under *Unreleased*.

## Test coverage

In `tests/test_autopilot_merged.py`: 29 tests in throwaway repositories with a local
bare `origin`, lanes in their own worktrees, and a second clone of `origin` (the `Host` helper)
that merges, squashes, commits and deletes branches the way a hosting service would; no network.

The tests were committed first (`22104ab`), before any implementation. Against that commit every
test fails because the command does not exist yet (27 through the parser, one importing the
module, one while setting up — see *Implementation evidence*). One test was then corrected, not
weakened: in criterion 10, a second `merged` can only report `recorded: true` once no copy of the
branch is left, so the test deletes the remote branch after `--cleanup`, as the plan's behaviour
step 7 states.

| Criterion | Tests |
|---|---|
| 1. Ancestor | `test_ancestor_with_a_merge_commit_names_the_merge`, `test_ancestor_after_a_fast_forward_names_the_head` |
| 2. Tree | `test_tree_match_after_a_squash_on_an_unchanged_mainline` |
| 3. Patch-id | `test_patch_id_after_an_unrelated_commit_landed_first` |
| 4. Merge-tree | `test_merge_tree_when_the_changes_arrived_in_separate_commits` |
| 5. Negatives and the finished-branch guard | `test_an_unmerged_finished_branch_is_not_merged`, `test_a_local_commit_after_the_squash_is_not_merged`, `test_an_unstarted_branch_is_not_merged_although_it_is_an_ancestor`, `test_a_merged_branch_whose_row_is_not_done_at_its_head_is_not_merged` |
| 6. Confirmations | `test_confirmations_are_reported_and_never_prove` |
| 7. Fetch | `test_fetch_prunes_and_no_fetch_leaves_refs_alone`, `test_a_repository_without_the_remote_skips_the_fetch`, `test_an_unreachable_remote_exits_2` |
| 8. Heads, unknown task, renamed branch | `test_the_remote_copy_is_checked_when_the_local_branch_is_gone`, `test_the_local_branch_is_checked_when_the_remote_was_pruned`, `test_a_local_commit_after_the_squash_is_not_merged`, `test_no_branch_no_record_and_unknown_task_exit_3`, `test_a_renamed_branch_is_found_after_done` |
| 9. Runs | `test_the_merge_is_recorded_in_the_run`, `test_run_selection_and_standalone_use`, `test_standalone_use_writes_no_run_file` |
| 10. Status and recorded merges | `test_status_counts_a_recorded_merge_after_the_row_was_edited_by_hand` |
| 11. Cleanup | `test_cleanup_removes_the_worktree_and_local_branch_only` |
| 12. Cleanup refusals and the lease | `test_cleanup_refusals_change_nothing`, `test_cleanup_refuses_the_main_worktree`, `test_cleanup_keeps_a_branch_that_moved_after_the_check` |
| 13. Dependents | `test_a_claimed_stacked_dependent_gets_its_rebase_command`, `test_a_finished_dependent_forks_from_the_dependency_head_even_after_cleanup`, `test_a_dependent_branched_from_the_mainline_is_not_stacked` |
| 14. Text and JSON | `test_text_and_json_forms` |
| 15. Existing behaviour and documentation | the whole suite (469 before, 498 after, no existing test changed); documentation reviewed at the implement gate: `DESIGN.md` §7, §12 status, §12.1, §12.4, §12.8, §12.10; `README.md`; `CHANGELOG.md` |

Deviations from the plan's wording:

- `checks` is an object keyed by check name (`{"ancestor": false, "tree": true, "patch-id": null,
  "merge-tree": null}`, `null` for a check not reached or skipped) rather than a list.
- `--owner` was added, as on `done` and `release`, so `--cleanup` can tell the caller's leftover
  claim (released) from another owner's (exit 4).
- `runs` lists the runs written by this call; a merge reported from a run's record writes nothing,
  so it is `[]` there. The text form marks such a line `(recorded in a run)`.
- `head.commit` is the recorded `head` when the merge comes from a run's record.
- Found at verify: a dependent already rebased with the reported command was offered the same
  rebase again, from its claim's `base.commit`, which the rebased branch no longer contains. The
  claim's fork point is now used only while the dependent's head contains it; otherwise the
  `merge-base` with the dependency head applies, which after the rebase is on the mainline, so the
  dependent reads `stacked: false`. Covered by an assertion added to
  `test_a_claimed_stacked_dependent_gets_its_rebase_command`, shown failing first (below).
- Check 1 uses the classic `git rev-list --first-parent --ancestry-path <head>..<mainline>`, which
  works before git 2.38 and names the merge commit (criterion 1 covers it).

## Implementation evidence

Tests first, against commit `22104ab` (the tests alone; `--tb=line`, summarised with
`grep -E "^E |passed|failed" | sort | uniq -c`):

```
$ uv run pytest -q -p no:cacheprovider --color=no --tb=line tests/test_autopilot_merged.py
     28 E   argparse.ArgumentError: argument autopilot_command: invalid choice: 'merged' (choose from start, lane, decision, status)
      1 E   ImportError: cannot import name 'merged' from 'taskrail.autopilot' (…/src/taskrail/autopilot/__init__.py)
     28 E   SystemExit: 2
      1 29 failed in 6.91s
```

After the implementation (from the repository root):

```
$ uv run pytest -q tests/test_autopilot_merged.py
29 passed in 11.61s
$ uv run pytest -q
498 passed in 51.56s
```

Since the first failure only shows that the command was missing, six behaviours were broken one at
a time in the working tree, the autopilot tests re-run, and the files restored from a copy
(compared with `cmp` afterwards):

| # | Mutation | Tests that failed |
|---|---|---|
| a | the finished-branch guard skipped (`if not done_at_head:` → `if False:`) | `test_an_unstarted_branch_is_not_merged_although_it_is_an_ancestor`, `test_a_merged_branch_whose_row_is_not_done_at_its_head_is_not_merged` (`assert (True, False) == (False, False)`) |
| b | untracked files ignored by the dirty check (`--untracked-files=no`) | `test_cleanup_refusals_change_nothing` (the cleanup went on to `git worktree remove`, which refused) |
| c | the claim's recorded fork point never used | `test_a_claimed_stacked_dependent_gets_its_rebase_command` |
| d | branch deleted without the lease (`update-ref -d` without the checked SHA) | `test_cleanup_keeps_a_branch_that_moved_after_the_check` |
| e | `done_on_mainline` no longer reads recorded merges | `test_status_counts_a_recorded_merge_after_the_row_was_edited_by_hand` (`assert 'done-branch' == 'done-merged'`) |
| f | the patch-id check never matches | `test_patch_id_after_an_unrelated_commit_landed_first` (`via` became `merge-tree`) |

Each mutation failed only its own tests (for example `2 failed, 68 passed` for (a) over both
autopilot test files, `1 failed, 28 passed` for (c)).

## Verification

### Real CLI

Run through this checkout's wrapper, `.taskrail/bin/taskrail --root <repo>`, in a throwaway
repository under `/tmp` with a bare `origin` (`main` tracking it), lanes in `.worktrees/`, and a
second clone of `origin` as the host; removed afterwards. Four tasks: T001, T002 depending on
T001, T003 and T004. A first attempt was discarded because the host clone had not fetched the task
branch before squashing, so nothing was merged and every answer was correctly "not merged"; the
run below fetches on the host first. Paths are shown as `$D`, and git's own merge messages from the
host are left out.

```
run: 20260914-1
claimed T001 on T001-base-task from origin/main
T001 done and pushed at c46cd45
claimed T002 on T002-depends-on-base from origin/T001-base-task
claimed T003 on T003-independent from origin/main

## 1. before any merge

$ taskrail autopilot merged T001
T001 not merged into origin/main: no check proves that T001-base-task is contained in origin/main
T002: git rebase --onto origin/T001-base-task c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=0

$ taskrail autopilot merged T003
T003 not merged into origin/main: T003 is not done at the head of T003-independent; content detection needs a finished branch
exit=0

## 2. host: an unrelated commit, then the squash of T001, then the branch deleted
squash 0d5f593, remote T001-base-task deleted

$ taskrail autopilot merged T001 --no-fetch
T001 not merged into origin/main: no check proves that T001-base-task is contained in origin/main
T002: git rebase --onto origin/T001-base-task c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=0

$ taskrail autopilot status --run 20260914-1 --json | jq states   # not fetched
[{"id":"T001","state":"done-branch"},{"id":"T002","state":"running"},{"id":"T003","state":"running"}]

$ taskrail autopilot merged T001 --run 20260914-1 --json | jq
{"fetched":true,"merged":true,"via":"patch-id","commit":"0d5f593","recorded":false,"head":{"ref":"T001-base-task","local":"c46cd45","remote":null},"mainline":"origin/main","checks":{"ancestor":false,"tree":false,"patch-id":true,"merge-tree":null},"confirmations":{"row":true,"title":"0d5f593"},"runs":["20260914-1"],"dependents":[{"id":"T002","stacked":true,"fork":"c46cd45","fork_source":"claim","onto":"origin/main","command":"git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca","worktree":"$D/repo/.worktrees/T002-depends-on-base"}]}
remote-tracking branches after the prune:
  origin/HEAD -> origin/main
  origin/main

run file, lane T001:
{"handle":null,"group":null,"state":"running","reason":null,"updated":null,"resources":{},"merged":{"via":"patch-id","commit":"0d5f5936f396edca117e389545a79f7ff046994b","head":"c46cd45726002e299830326eb764c9fbcb7ffbca","mainline":"origin/main","detected":"2026-09-14T06:52:08+00:00"}}

$ taskrail autopilot merged T001
T001 merged into origin/main via patch-id at 0d5f593
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=0

$ taskrail autopilot status --run 20260914-1 --json | jq states
[{"id":"T001","state":"done-merged"},{"id":"T002","state":"running"},{"id":"T003","state":"running"}]

## 3. cleanup refusals, then cleanup

$ taskrail autopilot merged T001 --cleanup        # an untracked notes.txt in the worktree
taskrail: cleanup refused: the worktree $D/repo/.worktrees/T001-base-task has uncommitted or untracked changes
T001 merged into origin/main via patch-id at 0d5f593
cleanup refused: the worktree $D/repo/.worktrees/T001-base-task has uncommitted or untracked changes
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=5

$ (cd .worktrees/T001-base-task && taskrail autopilot merged T001 --cleanup)
taskrail: cleanup refused: the current directory or --root is inside the worktree $D/repo/.worktrees/T001-base-task; run the cleanup from outside it
T001 merged into origin/main via patch-id at 0d5f593
cleanup refused: the current directory or --root is inside the worktree $D/repo/.worktrees/T001-base-task; run the cleanup from outside it
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=5

$ taskrail autopilot merged T001 --cleanup        # after git worktree lock
taskrail: cleanup refused: the worktree $D/repo/.worktrees/T001-base-task is locked; unlock it first
T001 merged into origin/main via patch-id at 0d5f593
cleanup refused: the worktree $D/repo/.worktrees/T001-base-task is locked; unlock it first
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=5

$ taskrail autopilot merged T001 --cleanup        # unlocked, clean
T001 merged into origin/main via patch-id at 0d5f593
removed worktree $D/repo/.worktrees/T001-base-task
deleted branch T001-base-task
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=0
worktrees:
$D/repo                                 e592478 [main]
$D/repo/.worktrees/T002-depends-on-base 52ee920 [T002-depends-on-base]
$D/repo/.worktrees/T003-independent     e592478 [T003-independent]
local task branches:
+ T002-depends-on-base
+ T003-independent
branch record kept: T001.json
T002.json
T003.json

## 4. after cleanup: the run's record, and the stacked dependent's command

$ taskrail autopilot merged T001
T001 merged into origin/main via patch-id at 0d5f593 (recorded in a run)
T002: git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca (in $D/repo/.worktrees/T002-depends-on-base)
exit=0

$ (cd .worktrees/T002-depends-on-base && git rebase --onto origin/main c46cd45726002e299830326eb764c9fbcb7ffbca)
Rebasing (1/1)Successfully rebased and updated refs/heads/T002-depends-on-base.
exit=0
$ git log --format=%s origin/main..HEAD
stacked work

## 5. a merge commit, and a row marked by hand
claimed T004 on T004-another-one from origin/main
merge 595950f

$ taskrail autopilot merged T004
T004 merged into origin/main via ancestor at 595950f
exit=0
T003 marked ✅ on main by hand

$ taskrail autopilot merged T003 --json | jq
{"merged":false,"reason":"no check proves that T003-independent is contained in origin/main","checks":{"ancestor":false,"tree":false,"patch-id":false,"merge-tree":false},"confirmations":{"row":true}}

$ taskrail autopilot merged T999
taskrail: no task `T999`
exit=3
removed /tmp/t031-verify.4h2S
```

What this shows against the plan:

- an unmerged branch and an unstarted one are not merged, with their reasons; `--no-fetch` sees
  nothing new; a fetch finds the squash that landed after an unrelated commit by patch-id, prunes
  `origin/T001-base-task`, reports the `✅` and the `(T001) (#1)` title as confirmations, and
  records `merged` in the lane without touching its `state`;
- `status` turns T001 from `done-branch` to `done-merged` once the merge is recorded and fetched;
- cleanup refuses an untracked file, the current directory inside the worktree and a locked
  worktree with exit 5, then removes the worktree and the local branch and keeps the branch record;
- after cleanup a second call reports the recorded merge; the dependent's command, run in its
  worktree, leaves only `stacked work` on top of `origin/main`;
- a merge commit is found by ancestry and names the merge; a `✅` marked by hand proves nothing.

Before the merge, `dependents` already lists T002 with a rebase onto its unmerged dependency
(`origin/T001-base-task`), a no-op there; the plan does not restrict the list to merged
dependencies, so it is left as is.

### A dependent already rebased

A second throwaway repository (same setup, removed afterwards) repeated `merged` after T002 had
been rebased with the reported command. Before the fix, the report still offered the same rebase
from the claim's `base.commit`:

```
first call: git rebase --onto origin/main 567f103750755957de330ee613592dda8377b579
after rebase: stacked work
second call: {"stacked":true,"fork":"567f103","fork_source":"claim","command":"git rebase --onto origin/main 567f103750755957de330ee613592dda8377b579"}
$ git rebase --onto origin/main 567f103750755957de330ee613592dda8377b579
dropping 44704ef6828304da653e8a2a7fbec1453a7acd95 squash (T001) -- patch contents already upstream
Rebasing (3/3)
Successfully rebased and updated refs/heads/T002-depends-on-base.
after second rebase: stacked work
removed /tmp/t031-edge.nXLb
```

Git dropped the replayed mainline commits here, but on a mainline with conflicting changes the
second rebase would replay them and conflict. The assertion added to the claimed-dependent test
failed first:

```
$ uv run pytest -q --tb=line tests/test_autopilot_merged.py -k claimed_stacked
E   AssertionError: assert (True, 'claim...2d79bf8048f4') == (False, 'merge-base', None)
FAILED tests/test_autopilot_merged.py::test_a_claimed_stacked_dependent_gets_its_rebase_command
1 failed, 28 deselected in 1.10s
```

After the fix: `29 passed` for the file and `498 passed` for the suite.

## Affected areas

- `src/taskrail/autopilot/merged.py` (new): detection, confirmations, dependents,
  cleanup, `cmd_merged` and its arguments.
- `src/taskrail/autopilot/commands.py`: one import, one `add(...)` call.
- `src/taskrail/autopilot/status.py`: `done_on_mainline` also reads recorded merges.
- Reused, not changed: `branches.task_branch`, `stack._read_statuses`, `query.base_dict`,
  `review.resolve_remote`, `review.choose_base`, `runs.update`/`read_all`, `claims.read`/`release`,
  `gitutil.worktree_branches`, `cli._emit`/`_load`/`_refuse_if_invalid`.
- `DESIGN.md` §7, §12.1, §12.4, §12.8, §12.10; `README.md`;
  `CHANGELOG.md`.
- `tests/test_autopilot_merged.py` (new).

## Out of scope

- Rebasing dependents, re-running checks and publishing again: the orchestrator does it with the
  reported commands (§12.8); `merged` only lists them.
- Updating a rebased dependent's claim `base` (its `onto` names the deleted dependency branch and
  its `commit` a squashed-away commit). `status`'s `touched` for such a lane may then include
  mainline files until it is released; proposed as a follow-up task if it matters.
- Content detection inside `autopilot status`: `status` stays a read of local refs and run files.
- Deleting remote branches, host APIs and pull-request state (§1).
- Naming the next branch in the hand-off queue: `status` already does.
- A merge whose host squash rewrote content (§12.10 names it as a design change).

## Open questions and risks

Decisions for the gate, each with a recommendation:

- **Q1 — Which branch the ID resolves to.** Recommended: the live claim's branch, else
  `branches.task_branch` (record, else template). Alternatives: only `task_branch` (a claim moved
  by hand would be missed); require `--branch` (typing error-prone).
- **Q2 — Local vs remote copy.** Recommended: check the local branch when it exists, else
  `<remote>/<branch>`; report both SHAs; a local branch with unpushed commits is not merged, which
  keeps `--cleanup` from deleting work. Alternatives: check the remote copy first (it is what the
  host merged, but a cleanup could then delete unpushed local commits); prove either (same risk).
- **Q3 — Finished-branch guard.** Recommended: require `✅` for the task at the head before any
  check. Alternatives: no guard (an unstarted branch reports merged via `ancestor` or `merge-tree`,
  shown in *Evidence*); guard only with the claim's `base.commit` (gone after `done` releases the
  claim).
- **Q4 — What "marks done-merged in the run" stores.** Recommended: a `merged` object in the lane
  entry (`via`, `commit`, `head`, `mainline`, `detected`) as evidence, with `done-merged` still
  derived: `done_on_mainline` counts it only while `commit` is on a mainline ref. It is what lets
  `status` and a later `merged` know the merge once `--cleanup` removed the branch. Alternatives:
  store nothing and rely on `✅` (the design's "marks" has no effect, and a lost `✅` stays
  undetected); set the lane `state` to `done-merged` (a stored state, contrary to §12.4).
- **Q5 — Without a run vs `--run`.** Recommended: `--run R` optional; without it, update every run
  holding the task; standalone use needs no run and no `enabled`. Alternatives: require `--run`
  (standalone use impossible); `--run` adding the task to R (membership should come from `claim`).
- **Q6 — Dependents and their fork point.** Recommended: as in step 8 — dependents by `Depends On`
  with an existing branch; fork from the claim's `base.commit`, else `merge-base` with the
  dependency head SHA resolved in this call (so deleting the dependency branch later cannot lose
  it), else the run's recorded `head`; command `git rebase --onto <onto> <fork>` run in the
  dependent's worktree. Alternatives: only dependents with a live claim (misses finished dependents
  waiting in the hand-off queue); name the branch in the command (fails while it is checked out in
  another worktree).
- **Q7 — What refuses cleanup.** Recommended: any modified or untracked file, the current directory
  or `--root` inside the worktree, the main worktree, a locked worktree; ignored files do not refuse;
  exit 4 for another owner's claim; branch deleted with a lease on the verified SHA. Alternative:
  `--force` to override dirtiness (not recommended: the lane's uncommitted work would be lost).
- **Q8 — Branch records on cleanup.** Recommended: keep them. §6.4 already says a record outlives
  branch deletion; the run's `status` keeps showing the task's branch name, and a reopened task
  reuses its name. Alternative: remove it, so a reopened task renders a fresh template name.
- **Q9 — Cost of patch-id.** Recommended: the range is bounded by the merge-base
  (`M..<mainline>`, first-parent only), read as one streamed `git log -p | git patch-id` pipeline
  newest first and stopped at the first match, and run only after `ancestor` and `tree` missed
  (`tree` reads hashes only). The squash is usually among the newest commits, so a long-lived
  branch costs little unless it is not merged, when the whole range is read once. Alternative: a
  cap on the commits read (a merge older than the cap would be missed silently).
- **Q10 — Exit codes.** Recommended: exit 0 for a completed check whether merged or not (`merged`
  in the output), exit 5 only when `--cleanup` is refused. Alternative: exit 5 whenever `merged` is
  false (easier in shell scripts, but a check that worked would look like a refusal).

Risks:

- **Parallel lanes.** T030 edits `commands.py` (imports, a handler, an `add` call), `status.py`
  (`STATES`, `task_state`) and §12.1's rows; this task adds one import and one `add` in
  `commands.py`, edits only `done_on_mainline` in `status.py`, and edits the `merged` row, §12.4's
  `done-merged` bullet and §12.8. Expected conflicts are both-sides additions in imports, the
  changelog, indexes and DESIGN.md tables. T036 changes `branches.py` internals but keeps
  `task_branch`.
- **`merge-tree --write-tree`** needs git 2.38 or later (this machine: 2.55.0). With an older git
  the check is reported as skipped rather than failing the command.
- **Rewritten dependencies.** When a stacked dependent's claim is gone and its dependency was
  rebased after the dependent branched, `merge-base` falls back to a point on the mainline and the
  dependent is reported `stacked: false`; the orchestrator's rebase then shows conflicts in the
  dependency's files. Stated in `fork_source` and DESIGN.md.
- **Host rewrites** (squash with altered content or trailers inside files) defeat `tree` and
  `patch-id`; `merge-tree` may still hold. Already a named design change (§12.10).

## Evidence

A scratch repository under `/tmp`, removed afterwards (git 2.55.0): `empty` is a branch never
worked on; `task` was squash-merged after an unrelated commit `c3`; `task2` was merged with a merge
commit.

```
$ git merge-base --is-ancestor empty main && echo "ancestor: yes (false positive)"
ancestor: yes (false positive)
$ [ "$(git merge-tree --write-tree main empty)" = "$(git rev-parse main^{tree})" ] && echo yes
merge-tree no-op: yes
--- task (squashed)
ancestor: no
(no tree match expected: c3 came before the squash)
$ git diff $M task | git patch-id --stable
branch patch-id 0400669f87943ae34fd50be5e11a5dff2c6e45bb
$ git log --first-parent -p --format='commit %H' $M..main | git patch-id --stable   # filtered on that id
patch-id matches 1b1a198
$ git rev-list --first-parent --ancestry-path=task2 task2..main | tail -1 | xargs git log -1 --format='%h %s'
4221cd5 merge task2
removed /tmp/t031-plan.XFeJ
```

It shows the unstarted-branch false positive behind Q3, that one `git log -p | git patch-id`
pipeline finds a squash that a tree match misses (Q9), and that `--ancestry-path` with
`--first-parent` names the merge commit for check 1.
