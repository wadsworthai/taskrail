# T125 — Stop archive from merging a different epic into an archived epic's section

## Symptom

`taskrail archive` puts an epic's closed rows into the archive section whose heading has the
epic's ID. It does not look at the name in that heading. So when a live epic carries an ID that the
archive already holds for a different epic, archive merges the live epic into the old epic's
history. The old heading and name stay. The new epic's `Objective:` line is written above the old
epic's own `Objective:` and `Done when:` lines, and the new epic's rows are appended to the old
epic's table. After that, nothing in the archive shows which epic a row belonged to. The command
exits 0.

Since T122, `epic add` no longer hands out an archived ID. A live epic can still end up with one
through a hand edit, through a merge, or because `epic add` issued it before T122.

## Reproduction

The reproduction ran in a scratch clone of this repository, checked out at `5215682`, the commit
where T114 archived E01, E02, E05, E07 and E08. It used the CLI from this worktree's unfixed source
(`uv run --project <worktree> taskrail --root .`). The real backlog was never archived.

At that commit, `epic add --id E07` is now refused (T122). So E07 was reissued by a hand edit
instead: a `| E07 | taskrail phase 3 | Probe objective | — |` listing row and an empty
`## E07 — taskrail phase 3` section, committed.

```
$ taskrail --root . validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
validate exit 0
$ taskrail --root . new --epic E07 --kind chore --title "Probe task" --json
{ "id": "T126", "backlog": "main", "epic": "E07", ... }          new exit 0
$ taskrail --root . done T126 --force --json                     done exit 0
$ taskrail --root . archive --json
{ ... "archived": ["T114", "T126"], "epics": ["E06", "E07"], "held_back": [] ...
  "files": ["TODO.md", "docs/archive.md"] }
archive exit 0
$ grep -c '^## E07' docs/archive.md
1
```

`T126` is a scratch ID that the clone allocated. It is not this repository's T126.

**Expected:** archive does not file the rows of `E07 — taskrail phase 3` under
`E07 — Current-branch workflow`.

## Evidence

The archive's E07 section after the run above:

```
## E07 — Current-branch workflow

Objective: Probe objective

Objective: Let a single maintainer work tasks on the checked-out branch, commit when a task is done and stop only for decisions
Done when: a repository configured for the current branch works a task from claim to close with no task branch, no stage approvals and no push the human did not approve

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T079 | chore   | —   | —          | Write the current-branch workflow into DESIGN.md | ...
...
| ✅ | T084 | chore   | —   | T080, T081, T082, T083 | Teach the skills the current-branch workflow, ... |
| ✅ | T126 | chore   | —   | —          | Probe task                     |                                |
```

This is the same corruption that T122's Evidence recorded, now reached without `epic add`.

**A legitimate rename, for contrast.** In a second scratch clone at `5215682`, E06 is live and
already partly archived as `## E06 — Repository tooling`. Its listing row and heading were renamed
by hand to `Backlog tooling`, and archive was run:

```
$ taskrail --root . validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
$ taskrail --root . archive
main: archived 1 task(s) and 1 epic(s) into docs/archive.md
archive exit 0
$ grep -n '^## E06' docs/archive.md
111:## E06 — Repository tooling
```

In this case the rows belong together, because it is the same epic. The archived section keeps the
old name. A check that uses the name as its key cannot tell this case apart from a reissue. See
the questions below.

## Root cause

`_ensure_section` in `src/taskrail/archive.py` looks up the section with `_section(lines, epic.id)`.
That function returns the first section whose `EPIC_HEADING` match has the epic's ID, and it throws
the heading's name away:

```python
def _ensure_section(lines: list[str], epic: Epic) -> None:
    if _section(lines, epic.id) is not None:
        return
```

After that, `_describe` and `_append_row` look up the same section by ID. `_describe` skips an
`Objective:` line only when the section already holds identical text, so a different objective
gets inserted above the old one. T107 wrote this code at a time when an ID in the archive could
only belong to the same epic, the one still live and partly archived. T122 closed the tool's own
route to a reissued ID. It did not close routes from outside the tool.

## Ruled out

- **`_describe` alone.** If `_describe` refused a second objective, the rows would still land in the
  old epic's table. The wrong decision is the choice of section, and `_describe` and `_append_row`
  both inherit it.
- **`validate` accepting the reissued ID.** It does accept it, and that is by design. §7.6 keeps
  `validate` out of the archive (T122 D2), and the row repeats that. The damage happens at the
  write, so that is where the guard belongs.
- **The merge driver.** It merges two archives row by row and never creates an epic section from a
  backlog epic. The E07 section above was written by `archive` in one run, with no merge involved.
- **A heading the parser misreads.** The archive heading is written as `## {epic.id} — {epic.name}`
  and read back with `EPIC_HEADING`, the same regular expression `validate` uses for its
  `epic-name-mismatch` check. A live epic's name therefore round-trips exactly. The comparison can
  be a plain string equality.
- **This repository's own archive.** Its sections are E01, E02, E05, E06, E07 and E08. The live
  epics are `E06 — Repository tooling` and `E09 — taskrail phase 3`. E06's archive heading has the
  same name, and E09 has no section. A name check would not fire here.

## Affected areas

- `taskrail archive`, in any repository where a live epic's ID matches an archive section that
  belongs to another epic.
- Not affected: `validate`, `show`, `list` and `next`, which never read the archive, and `epic add`,
  which T122 already guards.

## Proposed fix

This is the lane's recommendation. The diagnose gate decides it.

1. **Refuse, with exit 5.** Before anything is written, `archive` checks every epic that has rows
   moving. If its archive section has the same ID but a different name, archive moves nothing, in
   any backlog, and exits 5 with a message like this:
   ``taskrail: epic `E07` `taskrail phase 3` would be archived under `E07 — Current-branch workflow` in docs/archive.md, a different epic; give the live epic an unused ID, or, if it was renamed, rename that heading to match``.
   `--dry-run` refuses the same way, because a dry run should not promise a move that the real run
   refuses.
2. **Use the name as the key.** The objective is not compared. See the questions below.
3. The check lives in `archive.py`'s write path, next to `_ensure_section`, with a small `except`
   in `cmd_archive` that maps it to exit 5. `validate` stays as it is.
4. A regression test with a negative control, a DESIGN.md §7.6 bullet, and a changelog bullet.
