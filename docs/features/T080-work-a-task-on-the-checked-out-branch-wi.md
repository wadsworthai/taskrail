# T080 — Work a task on the checked-out branch with task_branch = current

Kind: feature · Epic: E07 · Status: planned

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
  and records `base` `null`; on a detached `HEAD` it keeps today's warning.
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
   detached `HEAD` the claim has `branch` `null` and the warning is returned.
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
5. **Conflict risk.** T081 edits the same §4 note, the §12.2 bullet, `load_config`, `task_dict` and
   the three autopilot commands. Each of this task's hunks is kept on its own lines; the §4 note and
   §12.2 bullet are the likely textual conflicts, resolved by keeping both halves.
