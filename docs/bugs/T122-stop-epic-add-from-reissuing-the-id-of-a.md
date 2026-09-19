# T122 — Stop epic add from reissuing the ID of an archived epic

## Symptom

`taskrail epic add` without `--id` allocates `epic_prefix` plus two digits, one above the highest
epic in the backlog's `## Epics` table. It never looks at the backlog's archive. Once
`taskrail archive` has moved an epic out, and no live epic has a higher number, `epic add` hands
that epic's ID out again. It writes the reissued ID into the `## Epics` table while the archive
still holds a section with the same ID and the old epic's name. `validate` accepts the result.

## Reproduction

Run in a scratch clone of this repository
(`git clone -q /thezone/shared/repositories/utils/taskrail repro`), with the CLI from this
worktree's unfixed source (`uv run --project <worktree> taskrail --root <clone>`). The real
backlog was never touched.

**1. On `origin/main` today (`df31678`) the conditions no longer hold.** E09 is live, so the
highest live epic is above every archived one:

```
$ taskrail --root repro epic add --name "Probe" --objective "Probe" --json
{ "id": "E10", ... }            exit 0
```

**2. On the commit right after T114 merged (`5215682`), where only E06 is live and E01, E02, E05,
E07 and E08 are archived:**

```
$ git checkout -q 5215682
$ grep -n '^## E07' docs/archive.md
120:## E07 — Current-branch workflow
$ taskrail --root repro epic add --name "taskrail phase 3" --objective "Probe" --json
{
  "id": "E07",
  "backlog": "main",
  "file": null,
  "files": [
    "TODO.md"
  ]
}
exit 0
$ git diff
 | E06 | Repository tooling | How this repository runs its own backlog with taskrail while it is worked on | —    |
+| E07 | taskrail phase 3 | Probe     | —    |
 ...
+## E07 — taskrail phase 3
$ taskrail --root repro validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
validate exit 0
```

**Expected:** `E09`, one above the highest epic ID the backlog has ever used, E08 being archived.

## Evidence

**What the reissue does later.** On a branch from `5215682`, the reissued epic got one task
(scratch ID `T124`, unrelated to this repository's later T124). The task was marked done with `--force` and `taskrail archive` was run. Archive folds the
new epic into the old epic's section. The section keeps the old name, gets a second
`Objective:` line from the new epic, and the new epic's row joins the old epic's table:

```
## E07 — Current-branch workflow

Objective: Probe objective

Objective: Let a single maintainer work tasks on the checked-out branch, ...
Done when: a repository configured for the current branch works a task ...

| ✓  | ID   | ...
| ✅ | T079 | chore   | ...
...
| ✅ | T084 | chore   | ...
| ✅ | T124 | chore   | —   | —          | Probe task                     |                                |
```

`grep -c '^## E07' docs/archive.md` prints `1`. Two different epics now share one section and
one heading, so the archive no longer says which epic a row belonged to. This happens because
`archive._ensure_section` reuses any section whose heading has the epic's ID.

**Live epics on other branches: a separate, older gap.** From `main`, create branch `lane-a` and
run `epic add` there (commit it). Go back to `main` and run `epic add` again:

```
lane-a$ taskrail epic add --name "Lane A epic" --objective "A" --json   -> "id": "E10"
main$   taskrail epic add --name "Main epic"   --objective "M" --json   -> "id": "E10"
```

In the same scratch clone, `taskrail new` allocated scratch ID `T125`, because it saw `T124` on another
local branch. Epic allocation reads only the working tree, and it has done so since before the
archive existed.

## Root cause

`cmd_epic_add` in `src/taskrail/cli.py` computes the next ID from the parsed working-tree
backlog only:

```python
numbers = [int(e.id[len(prefix):]) for e in backlog.epics]
epic_id = f"{prefix}{max(numbers, default=0) + 1:02d}"
if any(e.id == epic_id for e in backlog.epics):
```

`backlog.epics` holds the live epics. T107 made `taskrail archive` move whole epics out of that
table, and it taught `ids.used_ids` to read the archive for **task** IDs (DESIGN.md §6.3, §7.6).
Nothing did the same for **epic** IDs. T107's artifact never mentions epic allocation. So the
"highest live epic plus one" rule, which was safe while epics were never removed, stopped being
safe once they could be removed.

## Ruled out

- **The wrapper or pin running a stale build.** The reproduction ran this worktree's own source
  through `uv run --project`, and it printed the same `E07` the orchestrator got through
  `.taskrail/bin/taskrail`.
- **`used_ids` failing to read the archive.** The archive is read correctly for task IDs.
  T114's negative control showed that, and the T125 allocation above shows it again. `epic add`
  just never calls `used_ids`, and `used_ids` only collects IDs from task tables.
- **Epic IDs held elsewhere, such as an own-file epic or a second backlog.** An own-file epic is
  still listed in `## Epics`, so `backlog.epics` sees it. Each backlog has its own archive, and
  the command refuses two backlogs that share one (§7.6). The gap is specific to the archive.
- **A missing reservation ledger.** No ledger would change this outcome. The archived E07 is
  committed on `main`, and a scan of the working tree's archive finds it. A ledger only matters
  for IDs that exist nowhere yet (an uncommitted epic in another worktree). That belongs to the
  cross-branch gap below, not to this defect.

## Affected areas

- `taskrail epic add` without `--id`, in every consuming repository that has run
  `taskrail archive` and archived its highest-numbered epic.
- `taskrail epic add --id <archived ID>` is refused for a live duplicate but accepted for an
  archived one.
- Later `taskrail archive` runs, which merge the reissued epic into the archived epic's section
  (see *Evidence*).
- Not affected: task ID allocation, `validate`, `show`, `list`, `next`, and `new --epic <archived
  ID>`, which exits 3 because the epic is not in the backlog.

## Proposed fix

Approved at the diagnose gate (`docs/autopilot/decisions/T122-stop-epic-add-from-reissuing-the-id-of-a.md`):

1. **D1:** read the archive's epic headings on the working tree only. There is no revision scan
   and no ledger. The cross-branch race (evidence 4) is follow-up **T124**.
2. **D2:** no `validate` change. `epic add --id` of an archived ID exits 5. The archive merging a
   reissued epic into the old section (evidence 3) is follow-up **T125**.
3. **D3:** a regression test with a negative control.
4. **D4:** one line each in DESIGN.md §6.3, DESIGN.md §7.6 and `CHANGELOG.md`.

## Fix

- `src/taskrail/ids.py`: new `archived_epic_ids(config, backlog)`. It returns the IDs in the
  working-tree archive's `## <ID> — Name` headings (`EPIC_HEADING`) that match the backlog's
  `epic_prefix`. A missing or undecodable archive yields an empty set.
- `src/taskrail/cli.py`, `cmd_epic_add`: allocates one above the highest of the live epics and
  `archived_epic_ids`. If `--id` names an archived epic, it prints
  ``taskrail: epic `E02` is archived in docs/archive.md; an archived ID is never reused`` and exits 5.
- DESIGN.md §6.3 has an **Epic IDs** paragraph, which states that they are not scanned across
  branches and not reserved. DESIGN.md §7.6 has a new bullet under what reads the archive.
  `CHANGELOG.md` has a bullet under Unreleased.

## Verification

Three tests were added to `tests/test_archive.py`. They use the file's `TODO` fixture, where
`archive` moves E02 whole and E01 keeps T003 and T004:

- `test_an_archived_epic_id_is_never_allocated_again`: after `archive`, `epic add` prints `E03`.
- `test_without_the_archive_the_same_backlog_would_reissue_the_epic_id`: the negative control. The
  archive is deleted, and `epic add` prints `E02`, which is genuinely free then.
- `test_an_archived_epic_id_is_refused_when_passed_explicitly`: `--id E02` exits 5, names
  `docs/archive.md`, and leaves `TODO.md` unchanged.

**Before the fix**, `uv run pytest -q tests/test_archive.py -k "epic_id"`:

```
>       assert (code, out.strip()) == (0, "E03"), err
E       AssertionError:
E       assert (0, 'E02') == (0, 'E03')
tests/test_archive.py:394: AssertionError
...
>       assert code == 5
E       assert 0 == 5
tests/test_archive.py:410: AssertionError
FAILED tests/test_archive.py::test_an_archived_epic_id_is_never_allocated_again
FAILED tests/test_archive.py::test_an_archived_epic_id_is_refused_when_passed_explicitly
2 failed, 1 passed, 21 deselected in 0.17s
```

Both failures match the root cause: E02 was reissued, and an archived `--id` was accepted with
exit 0. The control passed, as it must. Without the archive, E02 is the correct next ID.

**After the fix**, the same command printed `3 passed, 21 deselected in 0.15s`. `taskrail checks T122 --stage fix` then printed `1259 passed in 161.77s (0:02:41)`, `passed test`, `not configured lint` and `T122 in <worktree>: passed`, exit 0.

**The original reproduction, rerun with the fixed source** in the same scratch clone at `5215682`:

```
$ taskrail --root repro epic add --name "taskrail phase 3" --objective "Probe" --json
{ "id": "E09", "backlog": "main", "file": null, "files": ["TODO.md"] }      exit 0
$ taskrail --root repro epic add --id E07 --name "taskrail phase 3" --objective "Probe" --json
taskrail: epic `E07` is archived in docs/archive.md; an archived ID is never reused
exit 5
```
