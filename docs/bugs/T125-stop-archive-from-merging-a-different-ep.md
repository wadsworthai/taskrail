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

The diagnose gate approved all five points as recommended
(`docs/autopilot/decisions/T125-stop-archive-from-merging-a-different-ep.md`). The decisions
were: refuse with exit 5 and move nothing in any backlog, including on `--dry-run`; use the name
alone as the key, compared exactly; keep T107's second-run test unchanged; write a regression test
with a negative control; and add the DESIGN.md §7.6 and changelog lines, correcting T122's §7.6
clause.

A **legitimate rename** between two archive runs is refused too, because the name is the key. The
message names the one line to edit: the archive heading, which gets renamed to match the epic's
new name.

## Fix

- `src/taskrail/archive.py`: new `refusal(edits, plan)`. For each epic with rows moving, it looks
  up that epic's archive section by ID, the same way `_ensure_section` does, and compares the
  heading's name with the live epic's name. On a mismatch it returns the message. It does nothing
  when the plan is empty or the archive does not exist yet. The write path itself is unchanged.
- `src/taskrail/cli.py`, `cmd_archive`: calls `archive.refusal` for every selected backlog before
  any plan is applied, on the real run and on `--dry-run`. It prints
  `taskrail: <reason>` and returns exit 5 (`EXIT_REFUSED`), so a refusal writes nothing to any
  backlog.
- DESIGN.md §7.6: a new bullet describing the refusal, the name key and what a rename costs. T122's
  bullet now ends "a later `archive` refuses to file the new epic's rows (below)" instead of saying
  that archive files them in the old section.
- `CHANGELOG.md`: one bullet under Unreleased.

## Verification

The two new tests are in `tests/test_archive.py` and use the file's `TODO` fixture. The first
`archive` run moves E02 `Auth` whole. After that, `reissue_e02` brings E02 back into `TODO.md` by
hand edit, with one closed row, T007.

- `test_a_different_epic_under_an_archived_id_is_refused_and_nothing_moves`: the live E02 is named
  `Payments`. `validate` exits 0. `archive --dry-run` and then `archive` each exit 5, and their
  stderr names `` `E02` `Payments` ``, `` `E02 — Auth` ``, `docs/archive.md` and both remedies.
  Afterwards `TODO.md` and `docs/archive.md` are byte-identical to how they were before.
- `test_the_same_epic_under_its_archived_id_still_archives_into_its_section`: this is the negative
  control. The live E02 is named `Auth`, and archive moves T007 into the one `## E02 — Auth`
  section, after T006. This shows the refusal depends on the name, not on the ID alone.

**Before the fix**, `uv run pytest -q tests/test_archive.py -k "archived_id_is_refused_and or same_epic_under"`:

```
>           assert code == 5, out
E           AssertionError: main: would archive 1 task(s) and 1 epic(s) into docs/archive.md
E             held back T004: T003 depends on it
E
E           assert 0 == 5
tests/test_archive.py:441: AssertionError
FAILED tests/test_archive.py::test_a_different_epic_under_an_archived_id_is_refused_and_nothing_moves
1 failed, 1 passed, 24 deselected in 1.00s
```

In that run the dry run promised the move. I then put the real run first, temporarily, and ran the
test again. It failed the same way: `main: archived 1 task(s) and 1 epic(s) into docs/archive.md`,
then `assert 0 == 5`, `1 failed, 25 deselected in 0.14s`. Both failures match the root cause. The
control passed, as it must, because the same epic is supposed to archive into its own section.

**After the fix**, `uv run pytest -q tests/test_archive.py` printed `26 passed in 0.79s`. That
includes T107's second-run test, `test_the_archive_is_created_once_and_a_second_run_appends_to_its_section`,
which is unchanged. `taskrail checks T125 --stage fix` printed `1261 passed in 143.10s (0:02:23)`,
`passed test`, `not configured lint` and `T125 in <worktree>: passed`.

**The reproduction, rerun with the fixed source** in the same scratch clones:

```
repro$ taskrail --root . archive --dry-run
taskrail: epic `E07` `taskrail phase 3` would be archived under `E07 — Current-branch workflow` in docs/archive.md, a different epic; give the live epic an unused ID, or, if it was renamed, rename that heading to match
dry-run exit 5
repro$ taskrail --root . archive
taskrail: (same message)
archive exit 5
repro$ git status --short
(empty: E06's T114 did not move either)

rename$ taskrail --root . archive
taskrail: epic `E06` `Backlog tooling` would be archived under `E06 — Repository tooling` in docs/archive.md, a different epic; give the live epic an unused ID, or, if it was renamed, rename that heading to match
archive exit 5
```

**Both ways out, followed.** In `rename`, I edited the heading to `## E06 — Backlog tooling`.
`archive` then printed `main: archived 1 task(s) and 1 epic(s) into docs/archive.md` and exited 0,
and the archive has one `## E06 — Backlog tooling` section. In `repro`, I renumbered the live epic
to E09. `archive` printed `main: archived 2 task(s) and 2 epic(s) into docs/archive.md` and exited
0. The archive then holds `## E07 — Current-branch workflow` and a separate
`## E09 — taskrail phase 3`, and no `Probe` text appears in the E07 section.

**A normal run is unaffected.** A fresh clone at `origin/main` (`245f484`), run with
`taskrail --root mainclone archive --dry-run`, printed
`main: would archive 2 task(s) and 1 epic(s) into docs/archive.md` and exited 0.

## Impact

Nothing outside this fix needs a follow-up. The root cause lived entirely in `archive`'s choice of
section. T122 covers the `epic add` route. T124 tracks the cross-branch allocation race.
`validate` stays out of the archive by design (§7.6). Nothing in `never_edit` was touched.
