# T012 — Flag reopened tasks committed without a Reopens trailer

Kind: feature · Epic: E02 · Status: implemented

## Behaviour

`taskrail reopen` (T006) returns a commit message ending in a `Reopens: <ID>` trailer, and two
things depend on that trailer reaching git: the core skill's rebase rule for status-cell conflicts
(a `✅` wins unless the other side has a `Reopens: <ID>` commit) and `done-branch` detection
(`stack._reopened_since`, a stale `✅` tip does not count once a mainline has that commit). A task
moved back to `⬜` by hand, or committed with another message, silently breaks both.

`taskrail validate` now also reads git history and warns when a task that is pending in the
working tree went from `✅` done or `❌` discarded to `⬜` pending in a commit, and no commit
recording that reopen carries a `Reopens: <ID>` trailer. The warning names the task, the commit
and the remedy. It never changes the exit code, and no other command runs the check.

**Which history.** The commits reachable from `HEAD` that change a backlog file — each backlog's
main file and the epic files its working-tree main file names — newest first, at most
`--history-limit N` of them (default 500). `--no-history` skips the check. The window is the same
on a task branch and on a mainline, so it needs no mainline and catches a reopen committed
directly on the mainline as well as one on a branch. Running on a mainline in CI is where
squash-merged reopens are checked.

**Detecting a transition.** For each examined commit `C`, taskrail reads the backlog files at `C`
and at each of its parents with one `git cat-file --batch` (the main file and the epic files the
working tree names), and builds
one `ID → status` map per revision across all of a backlog's files, so a row moved between the main
file and an epic file is not a change. `C` reopens a task when the task is `⬜` at `C` and `✅` or
`❌` at **every** parent. For a merge, that means only a resolution that flipped the cell counts;
a reopen brought in from one side is detected at its own commit on that side. A root commit, and a
commit whose parents are missing in a shallow clone, reopen nothing. Only tasks that are `⬜` in
the working tree are considered: a hand reopen that was later completed again no longer affects
the rebase rule or `done-branch`, so it is not reported.

**What counts as recorded.** A transition at `C` is recorded when some commit reachable from
`HEAD` but not from every parent of `C` (`git log HEAD --not <parents of C>`) has a
`Reopens: <ID>` trailer, matched with `review.REOPENS` (whitespace around the ID tolerated). That
covers, with one rule: the reopen commit itself; a squash commit on the mainline whose message
carries the trailer `taskrail review` wrote into the pull request description; a later commit on
the branch; and a later commit written only to acknowledge an old reopen that can no longer be
reworded, such as `git commit --allow-empty` with the trailer. A trailer older than `C` — from an
earlier reopen of the same task that was done again — does not count, since it is reachable from
the parent. That is the same "a side has a `Reopens` commit the other lacks" test the rebase rule
and `done-branch` apply, so a warning disappears exactly when those two work again.

**Output.** One warning per task, for its most recent unrecorded transition:

```
TODO.md:36: warning: T012 went from ✅ done to ⬜ pending in 1a2b3c4 ("Mark T012 pending") without a `Reopens: T012` trailer; the rebase rule and done-branch detection cannot see this reopen — record it in a commit whose message ends with `Reopens: T012` [reopen-untraced]
```

`validate --json` gains a `history` object: `examined` (commits read), `limit`, `truncated` (more
commits changed backlog files than the limit), `shallow`, and `skipped` (`null`, `"--no-history"`
or `"not a git repository"`). The text output adds one line only when the check was truncated,
shallow or impossible, so a quiet CI run on a depth-1 checkout does not look like a clean one.
Outside git the check is skipped without a warning.

**Uncommitted reopens are not reported.** The working tree cannot carry a trailer, and the
pre-commit hook `taskrail init --pre-commit` installs runs `validate` before the commit message
exists, so a warning there would fire on every correct `taskrail reopen`.

## Acceptance criteria

1. A commit that turns a done task's cell to `⬜` with a message lacking the trailer, the task still
   `⬜`, makes `validate` report one `reopen-untraced` warning at the task's file and line naming
   the task and the commit's short hash; the exit code stays 0 and `valid` stays true.
2. The same for a discarded task (`❌` → `⬜`).
3. No warning when that commit carries `Reopens: <ID>` (also as `Reopens:  <ID> `), when a later
   commit on `HEAD` carries it (including an empty commit), or when a squash-style single commit on
   the mainline carries it in its body.
4. A `Reopens: <ID>` trailer in a commit older than the transition — an earlier reopen, then done
   again, then a hand reopen — does not cover it: the warning is reported.
5. No warning when the task was reopened by hand but is `✅` or `❌` again in the working tree, when
   the task no longer exists, or when the reopen is only in the working tree (uncommitted).
6. A row moved from `TODO.md` to an epic file in the same commit, keeping its status, is not a
   transition; a hand reopen of a task that lives in an epic file is detected.
7. A merge whose parents both have the task `✅` and whose result has `⬜` is detected at the merge;
   a true merge of a branch holding a recorded reopen raises no warning.
8. Several unrecorded transitions of one task produce a single warning, for the most recent one.
9. `--no-history` skips the check (`history.skipped = "--no-history"`); `--history-limit N` examines
   at most `N` commits and reports `truncated`; outside git `validate` behaves as before and
   reports `skipped = "not a git repository"`; a shallow clone reports `shallow: true` and does not
   fail.
10. `validate --json` includes the `history` object in every case; write commands, `list`, `show`
    and `next` do not read history (the check lives in `validate` only, not in `load_project`).
11. On a synthetic history of 1,000 commits each changing a 50 KB backlog, `validate` completes the
    check in under two seconds at the default limit (the reader currently parses one revision in
    about 6 ms, so a cheap text pre-filter — skip a revision pair unless a line containing `✅` or
    `❌` and a pending task's ID disappeared — is part of the implementation).

## Test coverage

All in `tests/test_history.py`.

| Criterion | Tests |
|---|---|
| 1. Hand reopen of a done task warned, exit 0 | `test_a_done_task_reopened_without_a_trailer_is_reported`, `test_the_warning_appears_in_text_output` |
| 2. Discarded tasks | `test_a_discarded_task_reopened_without_a_trailer_is_reported` |
| 3. Trailer in the commit, a later commit, a squash body | `test_a_trailer_in_the_reopen_commit_records_it` (three spellings), `test_a_later_commit_with_the_trailer_records_it`, `test_a_squash_commit_carrying_the_trailer_in_its_body_records_it` |
| 4. Older trailer does not cover | `test_an_older_trailer_does_not_cover_a_later_hand_reopen` |
| 5. Closed again, gone, uncommitted | `test_a_hand_reopen_closed_again_is_not_reported`, `test_a_hand_reopen_closed_again_in_the_working_tree_is_not_reported`, `test_a_task_that_no_longer_exists_is_not_reported`, `test_an_uncommitted_reopen_is_not_reported` |
| 6. Epic files | `test_a_row_moved_to_an_epic_file_is_not_a_transition`, `test_a_hand_reopen_in_an_epic_file_is_reported` |
| 7. Merges | `test_a_merge_resolution_that_reopens_a_task_is_reported`, `test_a_merged_branch_with_a_recorded_reopen_is_not_reported`, `test_a_merged_branch_with_a_hand_reopen_is_reported_at_its_own_commit` |
| 8. One warning per task | `test_several_hand_reopens_of_one_task_give_one_warning_for_the_latest` |
| 9. Flags, outside git, shallow | `test_no_history_skips_the_check`, `test_history_limit_bounds_the_commits_examined`, `test_history_limit_must_be_positive`, `test_outside_git_the_check_is_skipped`, `test_a_shallow_clone_reports_it_and_does_not_fail`, `test_repository_without_commits_is_skipped` |
| 10. `history` always present; only `validate` reads history | `test_the_default_run_reports_its_history` (and every test above reading `history`), `test_other_commands_do_not_read_history` |
| 11. Long history under two seconds | `test_a_long_history_is_checked_quickly` (1,000 commits built with `git fast-import`, a 50 KB backlog) |

Differences from the plan, decided while implementing:

- Epic files are read at every revision by the paths the working tree names, rather than by the
  paths each revision's main file names; the path filter of `git log` uses the same list, so both
  sides agree, and `history.py` reuses only the row parser `stack._statuses`.
- A repository without commits reports `skipped: "no commits"`, a fourth value beside the three the
  plan listed.

## Affected areas

- `src/taskrail/history.py` — new module: commit listing, transition detection,
  coverage, the `history` summary. Reuses `stack._statuses`, `review.REOPENS` and
  `gitutil.read_blobs`.
- `src/taskrail/cli.py` — `cmd_validate` calls the check after `load_project`;
  `validate` gains `--no-history` and `--history-limit`.
- `tests/test_history.py` — new tests for the criteria.
- `DESIGN.md` — §7 `validate` row, a short *Reopens in history* paragraph beside the
  `reopen` write rule; `README.md` Use block; `CHANGELOG.md` one bullet at the end of
  `## Unreleased`.

## Out of scope

- Any error or exit-code change: pushed history cannot be reworded, so an error would block every
  later commit on that branch and every CI run.
- Checking the working tree, and making the pre-commit hook aware of the commit message (a
  `commit-msg` hook could; follow-up if wanted).
- The GitHub workflow `taskrail init --github-workflow` writes checks out with depth 1, where this
  check examines at most one commit. Setting `fetch-depth: 0` there is an `install.py` change —
  proposed as a follow-up task, since a parallel lane is editing `install.py`.
- A configuration key for the limit; the flags are enough until a managed hook or workflow needs
  another value.
- `✅` → `❌` and other transitions; changes to the core skill, `review` or `stack`.
- Epic files that are no longer named by any backlog's main file in the working tree are not added
  to the path filter; their commits are still examined when they also change a main file.

## Open questions and risks

- **Warning or error, and its code.** Recommended: always a warning, code `reopen-untraced`.
  Alternative: an error for transitions not yet on any mainline ref (still fixable by rewording),
  a warning for the rest — stricter on task branches, but it adds a mainline lookup and makes the
  pre-commit hook refuse unrelated commits until the branch is rebased.
- **The window.** Recommended: the last 500 backlog-changing commits reachable from `HEAD`, with
  `--history-limit` and `--no-history`. Alternatives: only `<mainline>..HEAD` (cheap, but blind on
  the mainline, where squash messages lose trailers), or the whole history (unbounded cost).
- **History simplification.** The path-limited `git log` prunes side branches whose backlog changes
  a merge discarded; those changes cannot affect the working tree, so nothing that matters is lost.
- **Shallow clones and CI.** Depth-1 checkouts make the check inert; `shallow` in the output makes
  that visible rather than silent.
- **Squash message settings.** A host configured to squash with only the pull request title drops
  the trailer; the mainline warning is then exactly the signal this task adds.

## Verification

Run through the real CLI (`uv run taskrail --root <repo>`) against
throwaway git repositories under a temporary directory, each starting from a backlog with T001 and
T002 done and T003 pending; the repositories were deleted afterwards.

- **Hand reopen.** After `sed` turned T001 to `⬜` and `git commit -m 'Mark T001 pending'`,
  `validate` printed `TODO.md:15: warning: T001 went from ✅ done to ⬜ pending in f3cc32c ("Mark
  T001 pending") without a `Reopens: T001` trailer; … [reopen-untraced]` and `0 error(s), 1
  warning(s)`, exit 0; `--json` gave `valid: true` and `history` `{examined: 2, limit: 500,
  truncated: false, shallow: false, skipped: null}`. `--no-history` printed no warning; with
  `--history-limit 1` the warning stayed and the line `history: examined only the latest 1
  commit(s) changing backlog files (--history-limit 1)` appeared; `--history-limit 0` exited 2.
- **Empty acknowledgment commit.** `git commit --allow-empty -m 'Record the reopen of T001' -m
  'Reopens: T001'` cleared the warning.
- **Reopen with the CLI.** `reopen T002 --reason …` committed with its `commit_message`
  (`%(trailers:key=Reopens,valueonly)` printed `T002`): no warning. A further uncommitted `reopen
  T001`: no warning.
- **Epic files.** `epic split E01` committed, then a title edit in the epic file: `history`
  examined 3 commits and there were no issues. A hand reopen of T002 inside
  `todo/E01-billing.md` was reported at `todo/E01-billing.md:8`. A hand reopen committed before
  the split was still reported after it, at the task's new row (`todo/E01-billing.md:7`); a
  recorded reopen followed by a split and an edit in the epic file gave no issues.
- **Merges.** A `--no-ff --no-commit` merge of two branches that both kept T001 `✅`, resolved with
  T001 `⬜`, was reported at the merge commit (`37ba308 ("Merge side")`). After an acknowledgment
  commit, a true merge of a branch holding `Reopens: T002` gave no warning.
- **Shallow clone.** `git clone --depth 1` of that repository: `validate` printed `history: shallow
  clone; examined 1 commit(s), so older reopens are not checked` and no warning, exit 0; `history`
  reported `shallow: true`.
- **Outside git.** A copy of the files without `.git` printed `history: not checked (not a git
  repository)`, exit 0.

In this repository, `.taskrail/bin/taskrail validate` examined 32 commits in 0.16 s with no issues.
No difference from the plan was found beyond the two recorded under Test coverage.
