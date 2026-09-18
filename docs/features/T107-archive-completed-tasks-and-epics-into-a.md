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

## Acceptance criteria

Each is a test in `tests/test_archive.py` unless noted, written before the implementation.

| # | Criterion |
|---|---|
| 1 | `archive` moves a closed row out of its epic's table into the archive file, keeping every cell, and `validate` passes afterwards |
| 2 | A pending row is never moved; neither is a closed row that a remaining row depends on — it is reported held back, naming the dependent |
| 3 | An epic whose every row archives loses its `## Epics` row and its section; its objective and `Done when:` line appear in the archived section |
| 4 | An epic in its own file is archived with its file: the file is gone, the listing row is gone, and the merge driver's `.gitattributes` block no longer names it |
| 5 | An epic that keeps one row keeps its heading and table, and the archive holds only the moved rows |
| 6 | The archive file is created with its heading on first use, and a second run appends under the existing epic section instead of repeating it |
| 7 | The archive's table keeps the source table's header, including `[columns].aliases` and custom columns |
| 8 | `--dry-run` writes nothing and reports what would move; `--json` reports `archived`, `epics`, `held_back`, `archive` and `files` |
| 9 | `taskrail new` after an archive never re-allocates an archived ID, on the working tree and from a branch (`tests/test_ids.py` style, git fixture) |
| 10 | `validate` does not read the archive: an archive holding a row whose kind and dependencies would be invalid in a backlog produces no issue, and `show`/`list` do not report archived tasks |
| 11 | `taskrail reopen <ID>` of an archived task exits 3 and the message names the archive file the ID sits in, instead of the bare `no task` |
| 12 | `init --merge-driver` and `upgrade` write `/docs/archive.md merge=taskrail` in the block (`tests/test_merge_driver.py`) |
| 13 | The merge driver merges two branches' archives row by row: both sets of rows, one copy of a row both added (`tests/test_merge_driver.py`) |
| 14 | `[[backlog]].archive` is a known config key (no T094 warning), empty or a template with an unknown placeholder exits 2, and two backlogs resolving to the same archive path exits 2 (`tests/test_config_unknown_keys.py` neighbours) |

## Affected areas

| Area | Change |
|---|---|
| `src/taskrail/archive.py` | New. Selecting what archives, building the archive document, and the edits that remove the rows, the epic sections and the listing rows. |
| `src/taskrail/cli.py` | `cmd_archive` and its parser entry; the archive hint in `cmd_reopen`'s not-found path. |
| `src/taskrail/config.py` | `BacklogConfig.archive`, its default, its placeholder and collision checks, and `TABLE_KEYS["backlog"]`. |
| `src/taskrail/writer.py` | Deleting a file through `Edits` (an epic file that archives with its epic), and removing an epic's listing row and section — the inverse of `add_epic`/`split_epic`. |
| `src/taskrail/ids.py` | `used_ids` scans the archive file too, in the working tree and on every scanned revision. |
| `src/taskrail/mergedriver.py` | `known_conflict_paths` lists each backlog's archive, class `backlog`. |
| `tests/test_archive.py` | New; criteria 1-11. |
| `tests/test_merge_driver.py`, `tests/test_ids.py`, `tests/test_config_unknown_keys.py` | Criteria 9, 12-14. |
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
