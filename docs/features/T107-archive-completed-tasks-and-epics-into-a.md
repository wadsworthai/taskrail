# T107 — Archive completed tasks and epics into a configurable document

Closed rows stay in their epic's table forever (DESIGN.md §3.1), so a long-lived backlog grows
without bound and a reader meets years of finished work before the open rows. This repository is
already there: `TODO.md` holds 93 closed rows against 8 open ones, and one epic (E07) is closed
end to end.

This task adds `taskrail archive`: a command the human runs that moves closed rows — and a closed
epic's whole section — out of the backlog and into one document per backlog, leaving the backlog
valid and the archive greppable.

## Behaviour

`taskrail archive [--backlog NAME] [--dry-run] [--json]`

- It moves every **closed row** (`✅` or `❌`) of the selected backlogs out of its epic's table and
  appends it to that backlog's archive file, under a `## E## — Name` section of the same shape the
  backlog uses, with the source table's own header (aliases and custom columns included).
- A closed row that a **row staying behind still depends on** is *held back*: it stays in the
  backlog and the command says which task holds it. This is what keeps the backlog valid —
  `depends-unknown` is an error (`src/taskrail/project.py`) and `validate` never reads the archive.
- An **epic whose every row archives** is archived whole: its `## Epics` listing row and its
  section go too, and an epic that lives in its own file takes the file with it. Its objective and
  its `Done when:` line are carried into the archived section, so nothing is lost. An epic that
  keeps even one row keeps its heading and table.
- Nothing archives on its own. `taskrail done` and `taskrail discard` are unchanged; only this
  command moves a row.
- `--dry-run` reports exactly what would move and writes nothing.
- Archiving never breaks ID allocation: `ids.used_ids` reads the archive file too — in the working
  tree and on every scanned branch — so an archived ID is still "used" and is never handed out
  again (§6.3: IDs are never reused).
- The archive file is listed in the merge driver's `.gitattributes` block, so two branches
  archiving at once merge row by row like any backlog table.

### The archive file

`[[backlog]].archive`, a path template taking `{artifacts}` and `{backlog}`, default
`{artifacts}/archive.md` — `docs/archive.md` for this repository. It is created on first use:

```markdown
# Archive — main

Closed tasks and epics moved out of `TODO.md` by `taskrail archive`. taskrail does not validate
this file and never writes to the backlog from it; it reads it only so an archived ID is never
allocated again.

## E07 — Current-branch workflow

Objective: Let a single maintainer work tasks on the checked-out branch …
Done when: a maintainer works a task on the current branch …

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T079 | feature | 3   | —          | …                              | …                              |
```

Same Markdown as the backlog, so `grep -n 'T079' TODO.md docs/archive.md` finds a task wherever it
lives, and the merge driver's existing table merge applies unchanged. Sections and rows are
append-only and never reordered: rows go to the end of their epic's table, a new epic section to
the end of the file.

## Acceptance criteria, and the tests that cover them

Every test below was written before the implementation and observed failing — `22 failed, 80
passed` across `tests/test_archive.py` and `tests/test_merge_driver.py` before a line of the
feature existed (see *Evidence*). Tests are in `tests/test_archive.py` unless named otherwise.

| # | Criterion | Test |
|---|---|---|
| 1 | Closed rows move out of their epic's table into the archive, cell for cell, and `validate` passes afterwards | `test_closed_rows_move_into_the_archive_and_the_backlog_stays_valid` |
| 2 | A discarded (`❌`) row archives exactly like a done (`✅`) one | `test_a_discarded_row_archives_exactly_like_a_done_row` |
| 3 | A closed row a remaining row depends on is held back, and the output names what keeps it | `test_a_row_a_remaining_row_depends_on_is_held_back_and_named` |
| 4 | Holding one row back holds back the closed rows it depends on, to a fixed point | `test_a_chain_of_closed_rows_behind_a_held_back_one_stays_whole` |
| 5 | An epic whose every row moves loses its `## Epics` row and its section, and its objective and `Done when:` are carried across | `test_a_fully_closed_epic_loses_its_listing_row_and_section` |
| 6 | An epic that keeps a row keeps its heading and table, and its objective is not carried | `test_an_epic_that_keeps_a_row_keeps_its_heading_and_table` |
| 7 | An epic in its own file is archived with the file: the file is gone, so is its listing row, and the backlog validates | `test_an_epic_in_its_own_file_is_archived_with_its_file` |
| 8 | The archive is created once, a second run appends under the same section in order, and an epic archived later gains its objective there | `test_the_archive_is_created_once_and_a_second_run_appends_to_its_section` |
| 9 | The archived table keeps the source header, `[columns].aliases` and custom columns | `test_the_archived_table_keeps_aliases_and_custom_columns` |
| 10 | `--dry-run` writes nothing and reports what would move and what is held back; `--json` carries `dry_run`, `archived`, `epics`, `held_back` | `test_dry_run_writes_nothing_and_reports_what_would_move` |
| 11 | Nothing to archive is reported, and the archive is left byte-identical | `test_nothing_to_archive_is_reported_and_writes_nothing` |
| 12 | `--backlog` archives one backlog and leaves the others; an unknown name exits 2 | `test_backlog_selects_one_backlog_and_an_unknown_name_is_usage` |
| 13 | `[[backlog]].archive` is a template: `docs/{backlog}/closed.md` is honoured and the default is not written | `test_the_archive_path_is_configurable` |
| 14 | An empty `archive`, or one with an unknown placeholder, exits 2 when the config loads | `test_a_bad_archive_value_is_a_configuration_error` |
| 15 | Two backlogs sharing an archive, or an archive that is another backlog's file, are refused by the command, not by the config | `test_two_backlogs_may_not_archive_into_one_file` |
| 16 | `archive` is a known configuration key: writing it warns nothing (T094) | `test_archive_is_a_known_configuration_key` |
| 17 | `validate`, `show` and `list` ignore the archive, even one holding a row that would be invalid in a backlog | `test_validate_show_and_list_ignore_the_archive` |
| 18 | `reopen` of an archived ID exits 3 naming the archive file; an ID nowhere at all keeps the bare message | `test_reopening_an_archived_task_names_the_archive` |
| 19 | An archived ID is never allocated again from the working tree | `test_an_archived_id_is_never_allocated_again` |
| 20 | …nor from a revision, when the working tree no longer has the archive at all | `test_an_archived_id_counts_from_a_branch_that_no_longer_has_the_file` |
| 21 | `init --merge-driver` and `upgrade` write `/docs/archive.md merge=taskrail` in the block | `tests/test_merge_driver.py::test_init_merge_driver_writes_attributes_config_and_the_extra` |
| 22 | Two branches archiving at once merge row by row, and a row both archived appears once | `tests/test_merge_driver.py::test_two_branches_archiving_at_once_merge_row_by_row` |

Criterion 22 is the one that **passed before the implementation as well as after**, and that is the
result, not an accident: the archive was shaped as an ordinary backlog table precisely so the
driver needs no new code. All the archive needed was its path in the block (criterion 21).

## Affected areas

| Area | Change |
|---|---|
| `src/taskrail/archive.py` | New. Selecting what archives, building the archive document, and the edits that remove the rows, the epic sections and the listing rows. |
| `src/taskrail/cli.py` | `cmd_archive` and its parser entry; the archive hint in `cmd_reopen`'s not-found path. |
| `src/taskrail/config.py` | `BacklogConfig.archive`, the `archive_path` property, the default, the empty and placeholder checks, and `TABLE_KEYS["backlog"]`. |
| `src/taskrail/writer.py` | `Edits.delete` (an epic file that archives with its epic; `apply` unlinks it and overlays it empty so anything still referencing it is reported), and `remove_epic`, the inverse of `add_epic`/`split_epic`. |
| `src/taskrail/ids.py` | `used_ids` scans the archive file too, in the working tree and on every scanned revision. |
| `src/taskrail/mergedriver.py` | `known_conflict_paths` lists each backlog's archive, class `backlog`. |
| `tests/test_archive.py` | New; criteria 1-20. |
| `tests/test_merge_driver.py` | Criteria 21-22: the new archive line in the block's expected contents, and the two-branch merge. |
| `DESIGN.md` | §3.1 (closed rows stay *until archived*), §4 (`archive` key), §7 (the command's row), a new §7.6 describing the file and the rules, §7.4 (the driver's paths). |
| `README.md` | One line in the command list. |
| `CHANGELOG.md` | One bullet under `## Unreleased`. |
| `TODO.md` | This task's own row, through the CLI only. |

## Out of scope

- **Unarchiving.** No command brings a row back; see decision 3.
- Any automatic trigger — on `done`, on a merge, on a count of closed rows.
- Selecting what to archive by ID, by epic or by date, and any `--since`/`--keep-last` policy.
- Splitting the archive into several files, or per-year files.
- `validate` gaining any rule about the archive's contents.
- Archiving this repository's own `TODO.md` in this branch's commits; see decision 6.

## Decisions for the gate

1. **The trigger.** A single command, `taskrail archive [--backlog NAME] [--dry-run]`, that
   archives everything eligible; nothing automatic.
   *Recommended.* Alternatives: add `--epic E##` or positional IDs for partial archiving (YAGNI —
   the human's job here is periodic cleanup, and no caller wants a subset yet); or make it a dry
   run by default with `--write`, like `import` (rejected: `import` converts a foreign file,
   while this is an ordinary backlog edit, and every other writing command writes).

2. **The file's shape and its config key.** `[[backlog]].archive`, default
   `{artifacts}/archive.md`, holding the same epic sections and task tables as the backlog.
   *Recommended*: it is greppable, it stays valid Markdown, `ids.used_ids` can read it with the
   parser it already has, and the merge driver merges it with no new code. Alternatives: a bullet
   list or a plain heading-per-task document (loses the row-by-row merge and the ID scan); one
   file per epic (more files, no benefit until an archive is huge).

3. **A reopen after archiving.** Archived is archived: `taskrail reopen <ID>` of an archived task
   exits 3, with a message naming the archive file it found the ID in; if that work must come back,
   the human opens a new task, which may reference the archived row.
   *Recommended* — it adds a lookup and a message, not a mechanism. Alternatives: an `unarchive`
   command or `reopen --from-archive` that moves the row back and recreates the epic section if it
   was archived (real work, no caller today); or leaving the bare `no task T042`, which is what the
   human would see with no hint at all.
   **The branch case answers itself and needs no code:** a branch that reopened a task before the
   archive merges into a mainline that removed the row, and the driver's existing modify/delete
   rule leaves that row conflicted for the human (§7.4) — exactly the right outcome. The reverse,
   a branch carrying a closed row unchanged, merges clean as a removal.

4. **Whether `validate` reads the archive.** It does not, and that is what the held-back rule is
   for: every dependency named in a backlog is in that backlog, so nothing is validated across the
   boundary. `ids.used_ids` does read it, which is not validation — without that, an archived ID
   could be handed out twice once the branches carrying it are gone.
   *Recommended.* Alternative: `validate` parses the archive and checks it for duplicate IDs
   against the backlog and for rows that are not closed. That buys a class of error the command
   itself cannot produce, at the cost of a second file in every load and a new set of rules — the
   simpler outcome wins.

5. **The merge driver.** The archive is added to `known_conflict_paths` with class `backlog`, so
   `init --merge-driver` and `upgrade` list it in `.gitattributes` and the existing table merge
   handles it. Two lanes archiving different rows keep both; the same row archived twice merges to
   one line.
   *Recommended*; no new driver code. Alternative: leave it out of the block and let git merge it
   as text, which conflicts on every concurrent append — the very problem §7.4 exists to solve.

6. **This repository's own backlog.** Should this branch's commits actually archive `TODO.md`
   (84 rows and epic E07 would move: 93 closed rows less T002, T101 and T103, which open rows
   depend on), or leave `TODO.md` untouched and demonstrate the command on a copy?
   *Recommendation: leave `TODO.md` untouched in this branch.* Every other lane and the
   orchestrator read that file, and rewriting 84 rows mid-run would collide with rows their
   branches also carry — the driver would resolve most of it, but the noise lands on branches that
   did not ask for it. I would verify on a scratch copy of this repository, paste the real output
   in this artifact, and open a follow-up chore to run `taskrail archive` on `TODO.md` once the
   run's branches are merged. Alternative: archive for real here, which gives the feature a real
   first use in the same pull request but rewrites the backlog every open branch shares.

## One decision changed while building it

Decision 2a was answered "refuse two backlogs resolving to the same archive path, in the config's
existing checks". **Built as a refusal by the command instead**, for a reason that only showed up
once the check existed: the default archive is `{artifacts}/archive.md`, so *any* two backlogs
sharing an artifacts root resolve to the same path — including the two in DESIGN.md §4's own
example and four of this repository's test fixtures. A config-load refusal therefore exits 2 on
every command of a repository that has two backlogs and never archives anything:

```
$ uv run pytest -q          # with the check at config load
taskrail: .taskrail/config.toml: archive `docs/archive.md` is used by more than one backlog
5 failed, 1238 passed
```

Writing is the only operation that would mix two backlogs into one file — `ids.used_ids` filters
by prefix and the driver lists a path once — so the refusal sits where the damage would be done.
`taskrail archive` exits 2 naming both backlogs and the key, and `validate` stays 0. The same check
covers an archive that is another backlog's file. The decision's intent (never mix two backlogs
silently) is kept; only its position moved.

## Follow-up opened

- **T114** (chore, E06): *Archive this repository's closed tasks and epics* — run `taskrail
  archive` on `TODO.md` once run 20260918-1's branches are merged. Decision 6 keeps this branch's
  `TODO.md` untouched, and T114 carries the real run.

## Open questions and risks

- **Held-back rows keep some closed work visible.** A closed task an open task depends on cannot
  leave the table. On this repository that is 3 rows out of 87 — an acceptable residue, and it
  shrinks as those tasks close.
- **An epic archived while a new task wants it.** The epic is gone from the `## Epics` table, so
  `new --epic E07` exits with the epic not found. The human adds an epic. Recorded rather than
  worked around.
- **The archive is a file two lanes append to**, mitigated by decision 5; the first lane to run
  `archive` also creates it, which is an add/add the driver handles with an empty base.
- **A stale `.gitattributes`.** A repository that archives before running `upgrade` gets a text
  merge on the archive until the block is refreshed. The command reports the archive path, and
  `upgrade` picks it up, as it does for a new changelog.
