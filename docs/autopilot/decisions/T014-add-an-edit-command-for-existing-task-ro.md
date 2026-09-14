# T014 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T014-add-an-edit-command-for-existing-task-ro.md` (commit
`300ccb3`), its fifteen acceptance criteria, refusals and branch-record handling.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Moving a task to another epic | leave out, no follow-up · `--epic` now · follow-up | **leave out, no follow-up now** | A move rewrites two tables, possibly two files, and conflicts easily; no one has asked for it yet. |
| 2 | Closed and `done-branch` tasks | exit 5, `--force` overrides · allow all · allow text fields only | **as recommended** | A closed row is history other branches rely on; `--force` covers a deliberate correction. |
| 3 | Claim | not required, exit 4 on someone else's claim, `--force` overrides · require the caller's claim | **as recommended** | Matches `discard`; fixing a dependency on a pending task should not need a claim. |
| 4 | `--kind` | editable and validated · excluded | **editable** | A wrong kind is the same kind of mistake as a wrong dependency, and validation catches disallowed kinds. |
| 5 | `--allow-invalid` | run on an invalid backlog, write only an error-free result · plain refusal | **as recommended** | Lets `edit` repair a cycle a merge left behind without writing another invalid state. |
| 6 | Title change that alters the template branch name | record the old name when that local branch exists, mirrored like `claim`, `--local-only` skips · warn only | **as recommended** | A task already being worked must not lose its branch because its title changed. |
| 7 | Dependencies | `--depends-on` replaces the list, `""` clears · add and remove flags | **replace** | Same shape as `new --depends-on`; `show` gives the current list to build from. |
| 8 | Hand edits in the core skill | point to `taskrail edit` only · keep hand edits with `validate` as fallback | **point to `edit`** | The CLI owns the table format; conflict resolution keeps its own rule in step 8. |

Plan approved.

## implement gate

Reviewed: commit `6da8ca2` (`writer.set_cells`, with `set_status` now calling it; `cli._custom_columns`
shared with `new`; `cmd_edit`; DESIGN.md §3.2 and §7; README; CHANGELOG; a new "Editing tasks"
section in the core skill and its installed copy; `tests/test_edit.py`). The lane rebased onto
`977064f` before editing the skill. Re-ran `test_edit.py`, `test_write.py` and `test_cli.py` in the
lane's worktree: 90 passed; the lane's full suite gave 713 passed. The 48 new tests failed before
the code.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Follows decisions 1–8; one cell-writing helper now serves `done`, `discard`, `reopen` and `edit`. |
| 2 | Separate "Editing tasks" section in the core skill | keep · fold into "Creating tasks" | **keep** | It is its own procedure with its own refusals; step 8's conflict rule is untouched. |
| 3 | `--title ""` | validation error, exit 1 · usage error, exit 2 | **exit 1** | The same `task-title` check `validate` applies to any empty title. |

## verify and close

The verify stage ran `taskrail edit` in a throwaway repository — the missing-dependency case from
T001's friction note, every refusal, several flags at once, a closed and a `done-branch` task, a
claim held by someone else, branch recording after a title change, repairing a cycle with
`--allow-invalid`, and an epic in its own file — with no gap against the plan. No rebase was needed
(`origin/main` is `977064f`). Checked before publishing: `TODO.md` differs from `main` only in T014
`✅`, the full suite passes, `taskrail validate` 0 errors, `upgrade` reports nothing to create or
update, no upstream.

## rebase after T012

T012 was squash-merged into `main` as `525af38`. The orchestrator rebased the branch onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in the docs indexes, CHANGELOG and `TODO.md` | keep both · stop | **keep both** | Rows and bullets added on both sides; T012 and T014 each `✅`, no `Reopens:` commit. |

No code conflicted. After the rebase: no conflict markers, one bullet each for T012 and T014,
`pytest -q` passes, `taskrail validate` 0 errors and 0 warnings (including T012's history check),
`upgrade` reports nothing to create or update.
