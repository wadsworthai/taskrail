# T080 — Work a task on the checked-out branch with task_branch = current

Kind: feature · Epic: E07 · Status: verified

Source: `DESIGN.md` §13.1, §13.2, §13.6, §13.7 and the T080 row of §13.8, as merged in T079; the
T079 decision record (`docs/autopilot/decisions/T079-write-the-current-branch-workflow-into-d.md`,
scope gate decisions 2–6 and 11).

## Behaviour

A repository sets `[git] task_branch = "current"` (with `worktree = "never"`) and works every task
on whatever branch the checkout has, the mainline included:

- `show`, `list` and `next` report a top-level `task_branch` (`"task"` or `"current"`, under every
  setting). Under `"current"`: `branch` is the checked-out branch (`null` on a detached `HEAD`) with
  `branch_source` `"current"`, also while a claim names another branch; `base`, `worktree` and
  `worktree_base` are `null`; `prior_work.branches` is `[]` and `prepared` is `null`. The text form
  of `show` has no base line.
- A task is never `done-branch` or `discarded-branch`, a dependency blocks until it is `✅` in the
  checkout, and no task is stacked on another.
- `claim` records the checked-out branch in the claim, writes no branch record, gives no warning
  and records `base` `null`; on a detached `HEAD` it warns to check out a branch to work the task
  on (plan gate decision 2).
- `new --workspace` exits 5 before reserving an ID; `workspace <ID>` and `branch <ID> <NAME>` exit
  5; each message names `[git].task_branch`. `new` without `--workspace` never warns on the
  mainline (`warning` is `null`).
- `edit` never records a task's old branch name.
- `checks` runs in the claim's worktree when it exists, else in the checkout it runs from, and
  never exits 5 for a missing worktree.
- `autopilot start`, `extend` and `next` exit 5 right after the `[autopilot].enabled` check, with
  `taskrail: the autopilot needs a branch per task; [git].task_branch is "current" in .taskrail/config.toml`.
- The configuration is checked when it loads (exit 2 from every command, `validate` included): an
  unknown `git.task_branch`, and `task_branch = "current"` without `worktree = "never"`.

Under the default `"task"` nothing changes except the new `task_branch` field.

## Acceptance criteria

1. `[git].task_branch` defaults to `"task"`; a value other than `"task"` or `"current"` makes every
   command (`validate`, `show`) exit 2 naming `git.task_branch`.
2. `task_branch = "current"` with `worktree` absent or `"required"` exits 2 with
   `git.task_branch = "current" requires git.worktree = "never"`.
3. `show --json`, every `list --json` entry and every `next --json` entry carry `task_branch`:
   `"task"` in a default repository, `"current"` in a current-branch one.
4. Under `"current"`, `show --json` reports `branch` = the checked-out branch and `branch_source`
   = `"current"` — on the mainline, on another branch, and while the task's claim names a different
   branch (`claim.branch` keeps that name); on a detached `HEAD` `branch` is `null`.
5. Under `"current"`, `base`, `worktree` and `worktree_base` are `null` even with a remote and a
   mainline configured, and `show`'s text has no `base` line.
6. Under `"current"`, `prior_work.branches` is `[]` and `prepared` is `null`, while `artifact` and
   `commits` (a commit whose subject names the task) are still reported.
7. Under `"current"`, a task whose row is `✅` on another local branch (named as its template branch
   would be) is `pending`, not `done-branch` (likewise `❌` is not `discarded-branch`); its dependent
   is `blocked` by it, `next` does not list the dependent, and `claim` of the dependent exits 5.
8. Under `"current"`, `claim` exits 0 with `warning` `null` and `branch_recorded` `false`, the claim
   records the checked-out branch and `base` `null`, and no branch record file is written; on a
   detached `HEAD` the claim has `branch` `null` and the warning, returned and printed, says to check
   out a branch to work the task on and does not name `taskrail branch`.
9. Under `"current"`, `new --workspace` exits 5 naming `[git].task_branch`, reserves no ID (the next
   `new` gets the ID it would have got) and creates no branch; `workspace <ID>` and
   `branch <ID> <NAME>` exit 5 naming `[git].task_branch` and change nothing.
10. Under `"current"`, `new` without `--workspace` on the mainline checkout returns `warning` `null`
    and prints no warning on stderr.
11. Under `"current"`, `edit --title` returns `branch.recorded` `false` and writes no branch record,
    even when a branch named after the old template exists.
12. Under `"current"`, `checks <ID>` runs in the checkout when the task has no claim (exit 0, not 5),
    and in the claim's worktree when that directory exists.
13. Under `"current"`, `autopilot start --count 1`, `autopilot extend <R> --count 2` and
    `autopilot next` (with and without `--run`) exit 5 with the message above, checked right after
    `[autopilot].enabled`; `autopilot status` still exits 0 for an existing run.
14. Under the default `"task"`, the existing suite passes unchanged.

## Affected areas

Code (each change a small hunk of its own, per the touch map):

- `src/taskrail/config.py` — `Config.task_branch` field; in `load_config`, the `task_branch` key,
  its value check and the `worktree = "never"` requirement, each on their own lines next to
  `worktree`.
- `src/taskrail/branches.py` — `CURRENT = "current"`; `resolve()` answers the checked-out branch
  (cached per project) with source `"current"`; a `is_current(config)` helper used by the others.
- `src/taskrail/stack.py` — `_find()` returns no tasks under `"current"` (no `done-branch`,
  `discarded-branch`, or unmerged dependency, hence no stacking).
- `src/taskrail/query.py` — `base_dict()` returns `None` under `"current"`; `task_dict()` gains the
  `task_branch` field on its own line.
- `src/taskrail/cli.py` — `cmd_show` passes no branch and no base to `prior.prior_work` under
  `"current"`; `_freeze_branch` records nothing and warns only on a detached `HEAD`; `cmd_new`
  refuses `--workspace` and skips the mainline warning; `cmd_workspace` and `cmd_branch` refuse
  right after the task is found; one shared refusal helper for those three messages.
- `src/taskrail/checks.py` — `worktree()` falls back to the checkout under `"current"`.
- `src/taskrail/branchrows.py` — `branch_of()` returns `None` under `"current"`, so a row absent
  from the checkout is not read from the checked-out branch's tip.
- `src/taskrail/autopilot/commands.py` — a `_task_branch_refusal(config)` helper, called with one
  line after the `enabled` check in `cmd_start`, `cmd_extend` and `cmd_next`.
- `cmd_edit` needs no change: it records only when the source is `template`, which `"current"`
  never is; a test covers it.

Tests: a new `tests/test_current_branch.py` with a fixture repository (git, a bare `origin`,
`[git] worktree = "never"`, `task_branch = "current"`) covering criteria 1–13; criterion 14 is the
full suite.

Documentation:

- `DESIGN.md` — §4 (the `task_branch` line of the example and the *Planned (§13.6)* note, keeping
  `commit` planned), §6.1 (claim under `"current"`), §6.4 (the resolver's *Planned* sentence),
  §7 table rows for `show`, `next`, `new`, `workspace` and `branch`, *Dependencies and the base*,
  §7.2 (`branches`, `prepared`), §7.5 (the worktree `checks` uses), §12.2 (the task_branch half of
  the *Planned (§13.7)* bullet, keeping the on-done half planned). In §13: §13.2's body replaced by
  a pointer to where it now lives, marked implemented by T080; the `task_branch` bullets of §13.6
  and §13.7 marked implemented; the T080 row of §13.8 marked. §13's introduction, §13.1, §13.3–§13.5
  and other lanes' rows untouched.
- `CHANGELOG.md` — one bullet under *Unreleased*.
- `docs/features/README.md` — this artifact's row.

## Out of scope

- `review` under `"current"` (§13.5) and `show`'s `close` object — T083 and T081. Until T083,
  `review` under `"current"` finds no base (`base_dict` is `None`) and, with `[review].rebase` on,
  exits 2 "could not determine the base"; nobody can reach that state before T083 except by setting
  the new key.
- `[git].commit`, the kind `commit` policy and the on-done autopilot refusal — T081.
- `gate = "decisions"` — T082.
- Skills, integration notes and the README — T084.
- `claim_remote` and `branch_record_remote` stay as they are: records are simply never written, so
  nothing is pushed; `--fetch` still fetches mirrored records.

## Plan gate decisions

Recorded in `docs/autopilot/decisions/T080-work-a-task-on-the-checked-out-branch-wi.md`:

1. The prior-work search gets no branch under `"current"`, so `commits` has no `branch` form.
2. On a detached `HEAD` under `"current"`, `claim` warns
   `<ID> was claimed on a detached HEAD: check out a branch to work the task on`, not naming
   `taskrail branch`, which exits 5 there; §6.1 and §13.2's pointer say so.
3. `workspace` and `branch` refuse right after the task is found; `new --workspace` after its epic is
   found, before the record fetch, any name check and the ID reservation.
4. §13.2's body is a one-line *Implemented (T080)* pointer; the `task_branch` bullets of §13.6 and
   §13.7 and the T080 row of §13.8 are marked in place; §12.2 carries the `task_branch` refusal.
5. `review` exiting 2 under `"current"` until T083 is accepted (see the risks below).

## Implementation

- `config.py`: `Config.task_branch`; `load_config` checks the value and the `worktree = "never"`
  requirement.
- `branches.py`: `CURRENT`, `is_current()`, `CURRENT_REFUSAL`; `resolve()` returns the checked-out
  branch (cached per project as `current_branch`) with source `current`.
- `stack.py`: `_find()` returns nothing under `"current"`, which also empties
  `query.unmerged_dependencies`, so no task is stacked.
- `query.py`: `base_dict()` returns `None` under `"current"`; `task_dict()` adds `task_branch`.
- `cli.py`: `cmd_show` passes no branch to `prior.prior_work` (with `base` `null`, no `onto` either);
  `_freeze_branch` returns no record and warns only on a detached `HEAD`; `cmd_new`, `cmd_workspace`
  and `cmd_branch` refuse with `CURRENT_REFUSAL`; `cmd_new` skips the mainline warning.
- `checks.py`: `worktree()` returns the checkout's top level when the claim records no existing
  worktree.
- `branchrows.py`: `branch_of()` returns `None`.
- `autopilot/commands.py`: `_task_branch_refusal(config)`, called after the `enabled` check in
  `cmd_start`, `cmd_extend` and `cmd_next`.
- `cmd_edit` is unchanged: it records only a `template` source.

## Acceptance criteria and tests

All in `tests/test_current_branch.py`.

| # | Tests |
|---|---|
| 1 | `test_task_branch_defaults_to_task`, `test_current_with_worktree_never_loads`, `test_an_unknown_task_branch_exits_2_naming_the_key` (3 values) |
| 2 | `test_current_requires_worktree_never` (absent and `"required"`) |
| 3 | `test_show_list_and_next_report_task_branch` |
| 4 | `test_branch_is_the_checked_out_branch_with_no_base_or_worktree`, `test_branch_follows_the_checkout_while_the_claim_names_another`, `test_branch_is_null_on_a_detached_head` |
| 5 | `test_branch_is_the_checked_out_branch_with_no_base_or_worktree`, `test_show_text_has_no_base_line` |
| 6 | `test_prior_work_reports_no_branches_and_no_prepared_workspace` (includes a commit only the `branch` form would match) |
| 7 | `test_a_task_closed_on_another_branch_is_not_done_branch` (the same refs give `done-branch`, `discarded-branch` and a stacked base under `"task"`), `test_a_dependency_done_in_the_checkout_unblocks` |
| 8 | `test_claim_records_the_checked_out_branch_without_a_warning_or_record`, `test_claim_on_a_detached_head_warns_to_check_out_a_branch` |
| 9 | `test_new_workspace_is_refused_before_reserving_an_id`, `test_new_workspace_with_branch_is_refused_the_same_way`, `test_new_workspace_with_an_unknown_epic_still_exits_3`, `test_workspace_and_branch_are_refused` (2), `test_workspace_and_branch_of_an_unknown_task_still_exit_3` (2) |
| 10 | `test_new_on_the_mainline_does_not_warn` |
| 11 | `test_edit_never_records_the_old_branch` |
| 12 | `test_checks_run_in_the_checkout_without_a_claim`, `test_checks_run_in_the_checkout_on_a_detached_head`, `test_checks_run_in_the_claims_worktree_when_it_exists` |
| 13 | `test_autopilot_start_extend_and_next_are_refused` (start `--count` and `--tasks`, extend, next preview and `--run`; status still exits 0), `test_the_enabled_check_comes_first` |
| 14 | the full suite: 1083 passed |

Written before the code: 31 tests, of which 25 failed and 6 passed on the plan's commit. The 6 that
passed guard orderings the change must keep (exit 3 for an unknown epic or task, the `enabled` check
first, a claim's worktree used by `checks`, a dependency done in the checkout unblocking).

## Verify

The real CLI (`uv run --project <worktree> taskrail`) against a throwaway repository: `main` pushed
to a bare `origin`, `[git] worktree = "never"`, `task_branch = "current"`, `[autopilot] enabled`, a
`test` check printing its directory, and T001 plus T002 depending on it.

- `show T001` text: no base line. `show T001 --json`: `task_branch` `current`, `branch` `main`,
  `branch_source` `current`, `base`, `worktree` and `worktree_base` `null`, state `pending`;
  `prior_work` all empty with `prepared` `null`, even with a local `T001-base-task` branch present.
- `list --json`: T002 `blocked` by T001, every entry `current` on `main` with `base` `null`;
  `next` lists only T001.
- `claim T001 --json`: claim on `main`, `base` `null`, `branch_recorded` `false`, `warning` `null`;
  no `.git/taskrail/branches` directory was created.
- `checks T001`: ran in the repository's checkout, exit 0.
- `new --workspace`, `workspace T001` and `branch T001 feature/x`: exit 5 with
  `taskrail: [git].task_branch is "current": tasks have no branch of their own; work on the checked-out branch`.
- `new --json` on `main`: `warning` `null`.
- `autopilot start --count 1` and `autopilot next`: exit 5 with
  `taskrail: the autopilot needs a branch per task; [git].task_branch is "current" in .taskrail/config.toml`.
- `done T001`, then `show T002`: `pending`.
- On a detached `HEAD`, `claim T002 --json`: claim `branch` `null`, and stderr and `warning` both read
  `T002 was claimed on a detached HEAD: check out a branch to work the task on`.
- With `worktree = "required"`, `validate` exits 2:
  `taskrail: .taskrail/config.toml: git.task_branch = "current" requires git.worktree = "never"`.

The behaviour matches the plan.

## Implement gate decisions

Recorded in the decisions file: `new --workspace` refuses before the `--branch` name check; `edit`
needs no change of its own; the `branchrows.branch_of` hunk stays; the §13 marks follow the wording
`— *implemented (T080)*, now §N`.

## Open questions and risks

1. **`prior_work.commits` and the `branch` form.** Under `"current"` the task's "branch" is the
   checked-out branch, say `main`; matching commit subjects that contain it would flag unrelated
   commits. Plan: pass no branch to the prior-work search, so `commits` keeps the `prefix`, `scope`
   and `suffix` forms and drops `branch`. Alternative: pass the checked-out branch and accept the
   noise.
2. **Detached-`HEAD` warning text.** §13.2 says `claim` "keeps today's warning", which ends with
   "run `taskrail branch <ID> <NAME>`" — a command that exits 5 under `"current"`. Plan: keep the
   text as today, literally. Alternative: under `"current"` say "check out a branch to work the
   task on" instead.
3. **Where `workspace` and `branch` refuse.** Plan: right after the task is found, so an unknown ID
   still exits 3 (as §13.5 orders it for `review --publish`), and before any fetch or name check.
   `new --workspace` refuses after its epic is found and before the record fetch and the ID
   reservation.
4. **"Moves its part into §4–§8 and marks it here."** Plan: §13.2's body becomes a pointer to §4,
   §6.1, §6.4, §7, §7.2 and §7.5, since keeping it would describe the same behaviour twice.
   Alternative: keep §13.2 whole and add an *Implemented (T080)* mark. §12.2 is outside §4–§8 but
   is where §13.7's refusal belongs, next to the `enabled` refusal.
5. **`review` under `"current"` until T083.** `base_dict` is `None` there, so `review` with
   `[review].rebase` on exits 2 "could not determine the base"; accepted at the plan gate. T083
   replaces `review`'s behaviour under `"current"`.
6. **Conflict risk.** T081 edits the same §4 note, the §12.2 bullet, `load_config`, `task_dict` and
   the three autopilot commands. Each of this task's hunks is kept on its own lines; the §4 note and
   §12.2 bullet are the likely textual conflicts, resolved by keeping both halves.
