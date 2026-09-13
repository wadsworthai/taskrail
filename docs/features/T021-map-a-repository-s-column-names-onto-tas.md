# T021 — Map a repository's column names onto taskrail's columns

Kind: feature · Epic: E05 · Status: implemented

## Behaviour

A repository whose backlog already has established column headers — for example `Size` for
story points, where taskrail's core column is `Pts` — declares an alias in config instead of
renaming its headers:

```toml
[columns]
custom = ["Owner"]
aliases = { Pts = "Size", "Depends On" = "Blocked By" }
```

Each key is a core task column (`✓`, `ID`, `Kind`, `Depends On`, `Title`, `Pts`,
`Description`, matched case-insensitively) and each value is the header that repository uses
for it. One name per column.

With an alias in place:

- **Reading.** Every command that reads task tables — `validate`, `list`, `show`, `next`, ID
  allocation — resolves the aliased header to the core column, case-insensitively as today.
  `Size` feeds `points`; an aliased `ID`, `✓` or `Kind` still identifies a task table.
- **The alias replaces the name.** In that repository the column is called by its alias only.
  A task table that still uses the core name of an aliased column (a `Pts` header when `Pts` is
  aliased to `Size`) fails validation with a `column-alias` error naming the expected header,
  so the repository's convention is enforced rather than silently drifting.
- **Writing.** `new --pts 3` fills the `Size` cell; `done`, `discard` and `reopen` find an
  aliased `✓` column; a table created for an epic that has none, with no other table to copy,
  uses the alias names in its header. `new --column Size=3` (or `--column Pts=3`) is refused
  with a message naming the flag that fills that column, so an agent following the
  repository's header names is told how to set it.
- **Messages.** A missing required column is reported by the name the repository uses, with the
  core name alongside, for example `task table is missing column(s): Blocked By (Depends On)`.
- **Output is unchanged.** `--json` keeps its field names (`points`, `depends_on`, …) and
  `columns` keeps holding custom columns only, so callers do not depend on a repository's
  headers.

Conflicting configuration is refused at load time, like every other config error (exit 2):
an unknown key, an empty value or one containing `|`, an alias equal to another core column's
name, two columns given the same alias, or an alias equal to a `[columns].custom` entry — all
compared case-insensitively.

## Acceptance criteria

1. A backlog whose task tables use `Size` instead of `Pts`, with `aliases = { Pts = "Size" }`,
   validates with no errors and no `column-undeclared` warning, and `show --json` reports
   `points` from the `Size` cell.
2. An alias for each required column (`✓`, `ID`, `Kind`, `Depends On`, `Title`) and for
   `Description` is honoured: the table is recognised as a task table, the values are read into
   the same fields, and a missing aliased required column is reported by its alias and core
   name.
3. Alias headers match case-insensitively (`size`, `SIZE`).
4. With `Pts` aliased to `Size`, a task table whose header says `Pts` fails validation with a
   `column-alias` error at the table's line; without the alias, the same table validates as
   today.
5. `new --pts 3 --depends-on T001 --description D` appends a row whose `Size`, `Blocked By` and
   `Description` cells hold those values, in an existing table with aliased headers; the diff
   is that one row. `new --column <name>=<value>`, where the name is an aliased core column's
   alias or core name (case-insensitively), exits 2 without writing or consuming an ID, and its
   message names the flag that sets that column (`--pts`, `--depends-on`, …), or says taskrail
   sets it for `ID` and `✓`.
6. `new` in an epic with no task table, in a backlog with no table to copy, writes a header
   that uses the alias names.
7. `done`, `discard` and `reopen` change the status cell of a table whose `✓` column is
   aliased (for example to `Status`).
8. ID allocation sees the IDs of a table whose `ID` column is aliased, so `new` never reuses one
   — on the working tree and on scanned branches.
9. Config is refused with exit 2 and a message naming the problem for: an alias key that is not
   a core column; an empty alias or one containing `|`; an alias equal (case-insensitively) to
   another core column's name; two columns with the same alias; an alias equal to a custom
   column.
10. A repository without `aliases` behaves exactly as before (the existing test suite passes
    unchanged).

## Affected areas

- `src/taskrail/config.py` — parse and check `[columns].aliases` into a new
  `Config.column_aliases` (core name → header); one self-contained hunk next to `custom`.
- `src/taskrail/backlog.py` — `_index` and `_is_task_table` take an optional
  aliases mapping, applied to task tables only (the Epics table is untouched); `_parse_tasks`
  reports `column-alias` and names aliased columns in `task-columns`.
- `src/taskrail/ids.py` — pass the aliases when scanning for used IDs.
- `src/taskrail/writer.py` — pass the aliases in `set_status`, `add_task` and
  `_header_template`, and render alias names in a default header.
- `src/taskrail/install.py` — a commented `aliases` example in the `init` config.
- `src/taskrail/cli.py` — `new` refuses `--column` for an aliased core column
  and names the flag to use.
- Tests: one dedicated file, `tests/test_column_aliases.py`, rather than additions to
  `test_validate.py`, `test_write.py` and `test_ids.py`, to stay clear of parallel lanes'
  edits to those files.
- Docs: `DESIGN.md` (§3.2 Columns, §4 Configuration), `README.md` where config
  is described, and one line under `## Unreleased` in `CHANGELOG.md`.

## Out of scope

- Aliases for the Epics table columns (`ID`, `Epic`, `Objective`, `File`).
- Several aliases for one column, or aliases that differ per backlog in the same repository.
- Renaming the fields of `--json` output or the CLI flags (`--pts` stays `--pts`).
- Filling an aliased core column through `--column`: it stays for custom columns, and is
  refused with a hint instead (criterion 5).
- Aliasing custom columns, or kinds routing (`when`) on an aliased core column.
- Rejecting duplicate header cells in general (a table naming the same column twice), which is
  pre-existing behaviour.
- A command that rewrites existing headers from one name to another.

## Open questions and risks

- **Replace versus add.** The alias replaces the core name (a `Pts` header is an error once
  `Pts` is aliased), rather than accepting both names, so a repository's fixed header is
  enforced.
- **Config shape.** `aliases` maps core name → repository header, which keeps keys to a closed,
  checkable set.
- **An alias equal to its own core name** in another case (`Pts = "pts"`) is dropped as a
  no-op rather than refused.
- **Signature changes in shared helpers.** `_index` and `_is_task_table` gain an optional
  argument with a default, so callers that do not pass it keep today's behaviour; a missed call
  site would silently ignore aliases, which the write and ID tests are there to catch.
- **Parallel work.** T018 also edits config loading; the change here is one hunk beside
  `[columns].custom` to keep a rebase conflict small.

Decisions at the plan gate (recorded in `docs/autopilot/decisions/`): the alias replaces the core
name; the mapping is core name → header; `--column` for an aliased core column stays refused but
must name the flag to use; scope kept.

## Test coverage

All in `tests/test_column_aliases.py`.

| Criterion | Tests |
|---|---|
| 1. `Size` for `Pts` validates and feeds `points` | `test_size_alias_for_pts_validates_and_feeds_points` |
| 2. Every core column; missing column named by both names | `test_every_core_column_can_be_aliased`, `test_a_missing_aliased_column_is_named_by_alias_and_core_name` |
| 3. Case-insensitive | `test_aliases_match_case_insensitively[size]`, `[SIZE]`, `test_alias_for_the_other_case_of_its_own_name_changes_nothing` |
| 4. Core name of an aliased column is `column-alias` | `test_core_name_of_an_aliased_column_is_a_column_alias_error` |
| 5. `new` fills aliased columns; `--column` hint | `test_new_fills_aliased_columns_with_a_one_row_diff`, `test_new_column_for_an_aliased_core_column_names_the_flag_to_use` (5 cases: `Size`, `size`, `Pts`, `Blocked By`, `Key`) |
| 6. New table uses alias names | `test_new_table_without_a_template_uses_the_alias_names` |
| 7. `done`, `discard`, `reopen` on an aliased `✓` | `test_status_commands_change_an_aliased_status_column` |
| 8. ID allocation, working tree and branches | `test_id_allocation_sees_an_aliased_id_column` |
| 9. Conflicting configuration refused, exit 2 | `test_conflicting_aliases_are_refused` (9 cases) |
| 10. No aliases: unchanged | the existing suite, unchanged and passing |

## Verification

Run through this branch's own wrapper (`.taskrail/bin/taskrail`, pinned to `local:.`)
in a scratch clone of the branch, on this repository's real backlog (24 tasks, five task tables).
`Pts` was renamed to `Size` and `Depends On` to `Blocked By` in every task table header:

- Without aliases, `validate` exited 1 with `task table is missing column(s): Depends On` for
  each of the five tables. After adding
  `aliases = { Pts = "Size", "Depends On" = "Blocked By" }` it exited 0 with
  `24 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- `show T021 --json` reported `points: 2`, `depends_on: []`, `columns: {}`; `list --epic E05`
  and `next` printed points and dependencies as before.
- `new --epic E05 --kind chore --title "Scratch aliased row" --pts 5 --depends-on T021
  --description verify` printed `T025` (T024 already exists), and `diff` showed one added row:
  `| ⬜ | T025 | chore   | 5    | T021       | Scratch aliased row ...`.
- `new ... --column Size=3` exited 2 with `taskrail: --column cannot set core column Pts
  (named `Size` here); set it with --pts`.
- `discard T024` and then `reopen T024 --reason "verify reopen"` changed only the status cell,
  `✅`/`❌`/`⬜` as expected.
- Putting `Pts` back in one table's header made `validate` exit 1 with `TODO.md:17: error:
  [columns].aliases names column(s) differently: use `Size` instead of `Pts` [column-alias]`,
  plus a knock-on `depends-unknown`, because that table's tasks are skipped, as with any
  table that fails `task-columns`.
- `epic add --name Scratch` followed by `new --epic E06` created the epic's table by copying
  the backlog's aliased header (`| ✓  | ID   | Kind    | Size | Blocked By | ...`), and
  `validate` exited 0. The path that builds a header from defaults, when no table exists to
  copy, is covered by `test_new_table_without_a_template_uses_the_alias_names`.
- `aliases = { Pts = "Size", Description = "size" }` made `validate` exit 2 with
  `columns.aliases: alias `size` is given to both Pts and Description`.

No difference from the plan was found.
