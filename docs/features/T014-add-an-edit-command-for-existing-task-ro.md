# T014 — Add an edit command for existing task rows

Kind: feature · Epic: E02 · Status: implemented

Source: T001 friction F4 ([T001 spike](../spikes/T001-validate-the-taskrail-skills-by-working.md)).
A task was created without its dependency and fixed by editing `Depends On` with `sed`: no
command changes an existing row, and the core skill only allows hand edits of titles and
descriptions.

## Behaviour

```bash
taskrail edit <ID> [--title T] [--pts N] [--depends-on IDS] [--description D] [--kind K] \
  [--column NAME=VALUE]... [--owner O] [--force] [--local-only] [--allow-invalid] [--json]
```

`edit` changes cells of one existing task row, in the current checkout, and nothing else:

- **Editable:** `Title`, `Pts`, `Depends On`, `Description`, `Kind`, and custom columns through
  `--column`. Aliased core columns (§3.2) are written under their alias through their usual flag,
  as `new` does.
- **Not editable:** `ID` (never), and the status (`✓`), which stays with `done`, `discard` and
  `reopen`. Moving a task to another epic is out of scope (see below).
- **Values.** Each flag replaces the whole cell. `--depends-on` takes a comma-separated list and
  writes it as `new` does (`T001, T003`). An empty value clears the cell and writes what `new`
  writes for an omitted value: `—` for `Pts`, `Depends On` and custom columns, an empty
  `Description`. An empty `--title` is left to validation (`task-title`). `--pts` accepts a
  whole number or an empty string; anything else is a usage error.
- **Minimal diff.** Each changed value rewrites only its own cell with `writer.replace_cell`,
  keeping the cell's width when the value fits; the table is never re-aligned. A value equal to
  the current one is not rewritten; when nothing changes, nothing is written and the command
  still succeeds.
- **Validate before writing.** The row is edited in memory through `writer.Edits` and the whole
  project is validated by `writer.apply`; with any error nothing is written (exit 1) and the
  errors are printed. This covers unknown dependencies, self-dependencies, dependency cycles,
  forbidden backlog directions, points that are not whole numbers or not on the scale, unknown
  or disallowed kinds, and an empty title, with the same rules and codes as `validate`.
- **Refusals, checked before editing:**
  - no field flag given, `--column` without `=`, a value with a line break, or a column the
    task's table does not have — exit 2;
  - `--column` naming a core column, by core name or alias and in any letter case — exit 2,
    naming the `edit` flag that sets it (`ID` and `✓` are not editable), reusing `new`'s
    message;
  - an unknown ID — exit 3;
  - a task claimed by someone else — exit 4;
  - a task that is `done`, `discarded` or `done-branch` — exit 5;
  - an invalid backlog — exit 1, as for every write command.
  `--force` overrides the claim and status refusals. `--allow-invalid` lets the edit run on an
  invalid backlog, and it is still written only if the edited project has no errors — so a
  cycle or unknown dependency left by a hand edit or a merge can be fixed with `edit` itself.
- **Claims.** No claim is needed — editing a row is backlog planning, like `new` and `discard`.
  `--owner` (default `$TASKRAIL_OWNER`, then `user@host`) only identifies the caller against an
  existing claim. The claim itself is never changed.
- **Branch names (§6.4).** A task with a recorded branch keeps that name: `edit` never renames
  or records over it, and never touches a git branch. For a task whose branch comes from the
  template, a new title (or a kind whose template differs) changes the rendered name. When the
  old name exists as a local branch, `edit` records the old name so the work on it stays the
  task's branch — what `claim` does for the same reason — and mirrors the record as `claim`
  does when `[git].branch_record_remote` is set (`--local-only` skips it). When no such branch
  exists, nothing is recorded and the task simply resolves to the new name.
- **Output.** The text form prints one line per changed field (`T014 title: old → new`) and a
  line when the branch name changed or was recorded. `--json` returns:

  ```json
  {
    "id": "T014",
    "changes": {
      "title": {"from": "Old", "to": "New"},
      "points": {"from": 3, "to": 5},
      "depends_on": {"from": ["T001"], "to": ["T001", "T003"]},
      "columns": {"Owner": {"from": "—", "to": "api"}}
    },
    "branch": {"name": "T014-…", "source": "recorded", "previous": null, "recorded": false},
    "record_remote": null,
    "files": ["TODO.md"]
  }
  ```

  Field names are the JSON names `show` uses (`title`, `points`, `depends_on`, `description`,
  `kind`, `columns`); only changed fields appear. `branch.previous` is the name the task
  resolved to before the edit when it differs from `branch.name`, else `null`; `branch.recorded`
  is true when `edit` wrote a record. `files` is empty when nothing changed.

## Acceptance criteria

1. `edit T002 --title X` rewrites only the `Title` cell of T002's row: the file diff is that one
   line, every other cell unchanged; `--json` reports `changes.title` with `from` and `to`.
2. `--pts 5` sets `Pts`; `--pts ""` writes `—`; `--pts abc` exits 2; a value off
   `[points].scale` exits 1. Neither refusal writes anything.
3. `--depends-on "T001,T003"` writes `T001, T003`; `--depends-on ""` writes `—`. An unknown ID,
   the task itself, or a dependency that creates a cycle each exit 1 and write nothing, with the
   validation error printed.
4. `--description D` sets the description; `--description ""` empties the cell.
5. `--kind bug` changes the kind; an undefined kind or one outside `[kinds].allowed` exits 1 and
   writes nothing.
6. `--column Owner=api` sets a custom column and `--column Owner=` writes `—`. A core column
   given to `--column` — core name or alias, any letter case — exits 2 naming the flag; a column
   the task's table lacks, `--column` without `=`, and a value containing a line break exit 2.
   Nothing is written.
7. With `[columns].aliases` mapping `Pts` to `Size`, `--pts 5` writes the `Size` column.
8. Several flags in one call change all their cells in one write; a task in an epic's own file is
   edited in that file.
9. No field flag exits 2. Values equal to the current ones exit 0 with empty `changes` and
   `files`, and leave the file untouched.
10. An unknown ID exits 3. A done, discarded or `done-branch` task exits 5; with `--force` the edit
    is made.
11. A task claimed by another owner exits 4; with `--force`, or claimed by the caller, or
    unclaimed, the edit is made and the claim file is unchanged.
12. An invalid backlog exits 1 and writes nothing. With `--allow-invalid`, an edit that removes the
    only error (a dependency cycle) is written and exits 0; one that leaves an error exits 1 and
    writes nothing.
13. A task with a recorded branch keeps it after a title change: `branch.name` and the record are
    unchanged and no git branch is renamed.
14. A template-named task whose old branch exists locally: after a title change, the old name is
    recorded, `branch.recorded` is true and `show` still reports the old branch. Without that
    local branch, nothing is recorded, `branch.name` is the new template name and
    `branch.previous` the old one.
15. The text output names each changed field with its old and new value.

## Test coverage

All in `tests/test_edit.py`.

| Criterion | Tests |
|---|---|
| 1. Title rewrites one cell | `test_title_rewrites_only_its_cell`, `test_a_shorter_value_keeps_the_cell_width`, `test_a_pipe_in_a_value_is_escaped` |
| 2. Points | `test_points_are_set_and_cleared`, `test_points_that_are_not_a_whole_number_are_a_usage_error`, `test_points_off_the_scale_are_refused_by_validation` |
| 3. Dependencies | `test_dependencies_are_replaced_and_cleared`, `test_invalid_dependencies_write_nothing` (unknown, self, cycle) |
| 4. Description | `test_description_is_set_and_emptied` |
| 5. Kind | `test_kind_is_changed`, `test_an_undefined_kind_is_refused`, `test_a_disallowed_kind_is_refused` |
| 6. Custom columns and refusals | `test_a_custom_column_is_set_and_cleared`, `test_column_refuses_a_core_column_and_names_the_flag`, `test_a_column_the_table_lacks_is_refused`, `test_an_optional_core_column_the_table_lacks_is_refused`, `test_column_without_an_equals_sign_is_refused`, `test_a_line_break_in_a_value_is_refused` |
| 7. Aliased columns | `test_pts_writes_an_aliased_column`, `test_column_names_an_alias_to_refuse` |
| 8. Several flags; epic files | `test_several_flags_change_their_cells_in_one_write`, `test_a_task_in_an_epic_file_is_edited_there` |
| 9. Nothing to change | `test_no_field_flag_is_a_usage_error`, `test_values_equal_to_the_current_ones_write_nothing`, `test_text_output_when_nothing_changes` |
| 10. Unknown, closed, `done-branch` | `test_an_unknown_task_is_not_found`, `test_a_closed_task_is_refused_unless_forced` (done, discard), `test_a_task_done_on_its_branch_is_refused_unless_forced` |
| 11. Claims | `test_someone_elses_claim_is_refused_unless_forced`, `test_the_callers_claim_or_no_claim_is_fine` |
| 12. Invalid backlogs | `test_an_invalid_backlog_is_refused`, `test_allow_invalid_writes_an_edit_that_fixes_the_backlog` |
| 13. Recorded branch kept | `test_a_recorded_branch_keeps_its_name` |
| 14. Template branch recorded or moved | `test_an_existing_template_branch_is_recorded_before_the_title_changes`, `test_without_a_branch_the_task_resolves_to_the_new_name`, `test_an_edit_that_keeps_the_branch_name_reports_no_previous`, `test_a_recorded_branch_is_mirrored_like_claim`, `test_local_only_records_without_mirroring` |
| 15. Text output | `test_text_output_names_each_change`, `test_text_output_when_nothing_changes` |

The existing `new --column` tests (`tests/test_write.py`, `tests/test_column_aliases.py`) cover
the core-column check `new` and `edit` now share, and the `set_status` tests cover it now that it
delegates to `writer.set_cells`.

## Affected areas

- `src/taskrail/writer.py` — a `set_cells(edits, task, values)` helper that locates
  the row and replaces the named cells, refusing columns the table lacks; `set_status` now
  delegates to it.
- `src/taskrail/cli.py` — the `edit` subparser and `cmd_edit`; the core-column
  check shared with `cmd_new` is factored into one helper, and `CORE_COLUMN_FLAGS` serves both
  commands' messages.
- `tests/test_edit.py` — tests for the criteria above.
- `DESIGN.md` — §7 command table and write rules (§3.2 mentions `edit --column`).
- `README.md` — one line in the Use block.
- `src/taskrail/skills/taskrail/SKILL.md` — replace "Editing a title or
  description by hand is fine" with `taskrail edit`, and add an *Editing tasks* section right
  after *Creating tasks*; installed copies refreshed with `taskrail upgrade`. Step 8's rebase
  conflict rule is unchanged.
- `CHANGELOG.md` — one bullet at the end of `## Unreleased`.

## Out of scope

- Moving a task to another epic (`--epic`). It deletes a row in one table and appends it in
  another, possibly another file, which is a larger and more conflict-prone change than a cell
  edit; a follow-up task if wanted.
- Editing epics (name, objective, `Done when`).
- Changing the status or the ID.
- Renaming git branches when a title changes; `taskrail branch` does that.
- Adding or removing single dependencies (`--add-depends-on`); `show --json` gives the current
  list to extend.
- Resolving conflicts between two branches that edited the same row; that is T004's merge driver.

## Open questions and risks

- **Conflicts.** A row edited on one branch and changed on another — most often its status cell
  set by `done` on the task's branch — conflicts on rebase, since both touch the same line. The
  core skill's rebase rule already stops and asks for conflicts other than added rows and status
  cells. The skill text will say to edit a task you are working on inside its own workspace, so
  the edit and the status change travel together.
- **Kind changes mid-work.** Changing the kind of a claimed task changes its executor skill and
  stages. It is allowed (the caller holds the claim or passes `--force`); the claim's recorded
  branch is unaffected.
- **Recording the old branch** reads only local branches, like `claim`; a branch that exists only
  on a remote is not protected.

Decisions at the plan gate (recorded in `docs/autopilot/decisions/T014-add-an-edit-command-for-existing-task-ro.md`):
no `--epic` and no follow-up; exit 5 for closed and `done-branch` tasks with `--force`; no claim,
exit 4 on someone else's claim with `--force`; `--kind` editable; `--allow-invalid` writes only an
error-free result; the old template branch name is recorded when that local branch exists,
mirrored like `claim`; `--depends-on` replaces the list; the skill points to `taskrail edit` only.

Decisions at the implement gate: the implementation is approved, the separate *Editing tasks*
section stays, and `--title ""` stays a validation error (exit 1).

## Verification

Run through the real CLI (`uv run taskrail --root <repo>`) against a
throwaway git repository with a custom `Owner` column, `[points].scale = [1, 2, 3, 5, 8]`, one done
task (T001), and two pending ones (T002 depending on T001, T003 with no dependency):

- The F4 case, `edit T003 --depends-on T002 --json`, exited 0 with `changes.depends_on` from `[]`
  to `["T002"]`; `git diff --word-diff` showed only `[-—-]{+T002+}` in T003's row.
- `--depends-on T001,T003` on T002 printed `dependency cycle: T002 → T003 → T002 [depends-cycle]`
  and `nothing was written` (exit 1); `--pts 4` printed `task-points-scale` (exit 1); `--pts x`
  exited 2; `--title ""` printed `task-title` (exit 1); `--column Pts=3` exited 2 naming `--pts`;
  no field flag exited 2.
- `edit T002 --title "Retroactive repricing" --pts 5 --column owner=api --description ""` printed
  one line per change plus `T002 branch: T002-repricing → T002-retroactive-repricing`, and changed
  only T002's line. Repeating `--pts 5` printed `T002 unchanged`.
- `edit T001 --title X` exited 5 (`T001 is done, not pending`); with `--force` it was written.
  With T003 claimed by `alice`, `--owner bob` exited 4 and `--owner alice` changed the kind.
- With a local branch `T002-retroactive-repricing`, a title change returned `branch.recorded:
  true`, `show` reported that branch as `recorded`, and the git branch was unchanged; a second
  title change returned `recorded: false` with the same name.
- T003 marked done on its branch `T003-rounding-error`: `edit` on main exited 5 (`done on branch`),
  and passed with `--force`.
- A hand-made cycle (T001 → T002 → T001): a plain `edit` exited 1 up front; `--allow-invalid` with
  an unrelated title change exited 1 with the cycle printed and nothing written; `edit T001
  --depends-on "" --allow-invalid --force` exited 0 and `validate` reported 0 errors.
- After `epic split E01`, `edit T002 --pts 8` wrote `todo/E01-billing.md`.

The repository was deleted afterwards. In this repository, `.taskrail/bin/taskrail edit T099 --title x`
exited 3, and an unchanged title on T014 returned empty `changes` and `files`. No difference from the
plan was found.
