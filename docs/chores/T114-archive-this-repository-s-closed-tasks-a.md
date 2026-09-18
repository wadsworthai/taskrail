# T114 — Archive this repository's closed tasks and epics

`taskrail archive` was built by T107 (DESIGN.md §7.6) and merged without ever being run on this
repository's own backlog: decision 6 of that task deliberately left `TODO.md` untouched, because
rewriting 84 rows while run 20260918-1's branches were open would have landed backlog noise on
every lane. Those branches are all merged now, no other lane is running and `taskrail claims` is
empty, so this task carries the feature's first real use.

## Goal

Run `taskrail archive` on this repository's `TODO.md`, so that the backlog a future reader or lane
opens holds the open work rather than two hundred lines of finished work, and the history is intact
and greppable in `docs/archive.md`.

## What the dry run actually reports

The figures in the task's own row are T107's, measured before the last twenty-odd tasks closed.
They are out of date in every term, and the difference is not a problem — it is what a run of this
size does to a backlog.

```
$ .taskrail/bin/taskrail archive --dry-run
main: would archive 108 task(s) and 5 epic(s) into docs/archive.md
```

| | The row says | The dry run says now |
|---|---|---|
| Rows archived | 84 | **108** |
| Epics archived | E07 | **E01, E02, E05, E07, E08** |
| Rows held back | 9 | **0** |

**Nothing is held back**, and there is exactly one line of output because there is nothing to
explain. The hold-back rule keeps a closed row while a row *staying behind* depends on it; the only
row staying behind is T114 itself, and T114 has no dependencies (`depends_on: []`). T107's nine
held-back rows were the transitive closure behind T003, T109 and T110, all three of which have
since closed and now archive themselves. `held_back` in `--json` is `[]`.

The backlog is 161 lines and holds 109 rows: 108 closed, and T114 open.

## Change set

| File | What changes |
|---|---|
| `TODO.md` | 108 closed rows leave their epic tables; the `## Epics` listing loses E01, E02, E05, E07 and E08 and their sections go with them. 161 lines → **15**: the `## Epics` table with E06 alone, E06's heading and `Done when:` line, and T114's row. Written by `taskrail archive`, never by hand. |
| `docs/archive.md` | New, 157 lines / 46,645 bytes. Six `## E## — Name` sections (E01, E02, E05, E06, E07, E08) in file order, each with the source table's own header and each row byte-for-byte as it stood in `TODO.md`. The five fully-closed epics carry their `Objective:` and `Done when:` lines across; E06 keeps its heading only, because it keeps T114. Written by `taskrail archive`. |
| `CLAUDE.md` | `docs/archive.md` added to the *Layout* block, and a *Backlog* bullet saying `TODO.md` holds the open work only, how to grep both files for a task, and that nothing comes back out of the archive. Decision 4. |
| `docs/chores/T114-…md` | This artifact. |
| `docs/chores/README.md` | Its index row. |
| `TODO.md` (row) | T114's own description corrected to the real figures through `taskrail edit`, and its status through `taskrail done`. Decisions 1 and 3. |

Nothing under `src/`, `tests/`, `DESIGN.md`, `README.md` or `CHANGELOG.md`. No `.gitattributes`
question arises: this repository has none — the merge driver is not installed here.

## Decisions

All five were approved at the scope gate as recommended, and are recorded in
`docs/autopilot/decisions/T114-archive-this-repository-s-closed-tasks-a.md`.

### 1. Correct T114's own description to the real figures?

After the archive, T114's row is *the whole of `TODO.md`* — one row under one epic. Its description
still reads "moves 84 closed rows and epic E07 into `docs/archive.md` and holds back the 9 rows
open tasks still depend on", which is wrong in all three numbers and will be the only sentence a
reader of the backlog sees until the next task is opened.

*Recommended:* `taskrail edit T114 --description` to the measured figures — 108 rows, five epics,
nothing held back. Alternatives: leave it, treating the description as a record of the intent the
task was written with (defensible in general, but this row is unusually load-bearing for the next
reader); or rewrite it to drop the numbers entirely.

### 2. Does the archive land at the default `docs/archive.md`?

*Recommended: yes, leave `[[backlog]].archive` unset.* `docs/` holds one directory per artifact
kind (`autopilot/ bugs/ chores/ features/ research/ spikes/`) and no loose files, so `archive.md`
is the first file at that level — which reads as a document about the backlog sitting beside the
documents about the tasks, and is exactly what §7.6 documents as the default. Alternatives:
`docs/backlog/archive.md`, which buys a directory holding one file; or a dated
`docs/archive/2026.md`, which pre-commits this repository to a splitting policy T107 put out of
scope and which would leave the default path untested in its first real use.

### 3. The order of operations at the close

The archive moves T114's neighbours; `taskrail done T114` writes T114's row. Both touch `TODO.md`.

*Recommended: archive first, in the implement stage; `done` at the close, as the procedure says.*
The backlog after each step:

- after `archive` — 15 lines: `## Epics` holding E06, E06's section, T114 still `⬜`;
- after `done T114` — the same 15 lines with T114 `✅`.

The alternative, closing T114 first and archiving afterwards, would archive 109 rows and **six**
epics: with T114 closed, no row stays behind, so E06 archives whole and `TODO.md` is left with an
empty `## Epics` table and no sections at all. That is valid but hostile — the next
`taskrail new --epic E06` exits "epic not found" and a human has to re-add an epic that was never
finished — and it also puts a row into the archive claiming it is done in the same commit that is
still doing it. The recommended order leaves E06, an epic whose `Done when:` is not met, where it
belongs, and leaves the next task a home.

**Not running `taskrail archive` a second time after `done` is part of this decision, not an
omission.** A later reader who notices that `TODO.md` still holds one `✅` row and "fixes" it by
archiving again would take E06 with it and leave the backlog with an empty `## Epics` table, which
is the outcome this decision exists to avoid. T114's row leaves the backlog on the *next* archive
run, by which time another epic and another open row will be keeping the file company.

### 4. Does anything need documenting?

*Recommended: one line in `CLAUDE.md`, nothing else.* After the archive, `TODO.md` is fifteen lines
with no reference to `docs/archive.md` anywhere in it; a reader or a lane that wants to know
whether something was already done has no pointer at all, and the pointer does not belong in
`TODO.md`, whose shape the CLI owns. `CLAUDE.md`'s *Backlog* section is what every future lane
reads first. Not recommended: a `CHANGELOG.md` bullet — the changelog is taskrail's user-facing
history, and `archive` is already in it under Unreleased from T107; running it on this repository's
own backlog changes nothing for anyone installing taskrail. `README.md` and `DESIGN.md` describe
the command and are already correct.

## Out of scope

- Any change to `src/`, `tests/` or the command's behaviour. If the run exposes a bug, it becomes a
  task, not an edit here.
- Archiving a second time after `done` (decision 3), and archiving T114 or E06.
- Splitting the archive, dating it, or setting `[[backlog]].archive` (decision 2).
- Reopening, unarchiving or editing any archived row.
- Installing the merge driver in this repository.

## Verification

Every command below was run in this task's worktree unless it names a scratch root. A full preview
had already been run against a scratch copy of `TODO.md`, `.taskrail/` and `docs/` outside the
worktree before anything here was written; the real run reproduced it exactly.

**V1 — the archive itself, and it matches the dry run word for word.**

```
$ .taskrail/bin/taskrail archive
main: archived 108 task(s) and 5 epic(s) into docs/archive.md          exit=0
```

**V2 — the backlog is still valid.**

```
$ .taskrail/bin/taskrail validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)                    exit=0
```

**V3 — only rows moved; nothing was rewritten.** The diff against the pre-archive backlog is
deletions and nothing else, and `docs/archive.md` is the one new file:

```
$ git status --porcelain
 M TODO.md
?? docs/archive.md

$ git diff --stat
 TODO.md | 146 ----------------------------------------------------------------
 1 file changed, 146 deletions(-)
```

161 − 146 = the 15 lines quoted under *The result* below.

**V4 — every archived row is byte-identical to the row it replaced, and every closed row is
accounted for.** Checked for all 108, not sampled, against `git show HEAD:TODO.md`:

```
archived rows: 108
byte-identical to the pre-archive TODO.md: 108
differing: 0
closed rows in old TODO.md: 108
all present in the archive: True
```

**V5 — idempotent.**

```
$ .taskrail/bin/taskrail archive --dry-run
main: nothing to archive                                               exit=0
```

**V6 — the ID check: no archived ID is ever handed out again.** This is the one way the change
could do lasting damage — 108 IDs now live outside `TODO.md`, and an allocator that cannot see them
would reissue `T115`. Run for real in git-initialised scratch copies of this worktree's post-archive
state, with `uv run taskrail --root <scratch> new --epic E06 --kind chore --title "ID allocation probe"`:

| Scratch repository | Next ID |
|---|---|
| archive present in the working tree | **T121** |
| archive deleted from the working tree, present only in `HEAD` — the case T107's §6.3 scan exists for | **T121** |
| *negative control:* no `docs/archive.md` anywhere, working tree or history | **T115** — a live reissue of an archived, done task |

The negative control is what makes the first two mean something: the archive scan, not luck, is
what keeps the counter at T121.

One thing the first attempt at this check got wrong, recorded because it would mislead the next
person to try it: probing twice in the same scratch repository returns T121 then **T122**, which
looks like a scan failure and is not. `ids.reserve` keeps a pending-reservation ledger in
`.git/taskrail/reserved/<backlog>.json` that `git checkout -- TODO.md` does not revert, so the
second probe is one above the first probe's own reservation. Each probe needs a fresh repository.

**V7 — the suite.**

```
$ .taskrail/bin/taskrail checks T114 --stage implement
…
1256 passed in 179.92s (0:02:59)
== lint: not configured
passed test
not configured lint
T114 in <worktree>: passed                                             exit=0
```

No test changed, and none needed to: the change is data, not code. The suite is the guard that the
archive did not disturb the parser, the ID scan or the writer it runs through.

## The result, judged as a document

The point of this task is not that the command exits 0 — it is that what it leaves behind is the
backlog every future reader opens.

`TODO.md`, in full, after the archive:

```markdown
# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E06 | Repository tooling | How this repository runs its own backlog with taskrail while it is worked on | —    |

## E06 — Repository tooling

Done when: this repository's own backlog runs through the taskrail autopilot

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T114 | chore   | 1   | —          | Archive this repository's closed tasks and epics | Run taskrail archive on TODO.md now that run 20260918-1's branches are merged: it moved 108 closed rows and epics E01, E02, E05, E07 and E08 into docs/archive.md, holding nothing back. |
```

(the description as decision 1 rewrote it, through `taskrail edit`; `taskrail done` turns the `⬜`
into a `✅` at the close and changes nothing else)

`docs/archive.md` opens with a header that names where the rows came from and what taskrail does
and does not do with the file, then six epic sections:

```markdown
# Archive — main

Closed tasks and epics moved out of `TODO.md` by `taskrail archive`.
taskrail does not validate this file and never reads a row back into the backlog; it
reads it only so an archived ID is never allocated again.

## E01 — taskrail release

Objective: Publish a first version other repositories can install
Done when: v0.2.0 is tagged and a repository installs it with uv and runs it through the wrapper.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | spike   | 3   | —          | Validate the taskrail skills by working a real task end to end | … |
```

Three observations, offered as findings rather than objections:

- **It is greppable and it reads well.** `grep -n 'T079' TODO.md docs/archive.md` finds a task
  wherever it lives, the rows are unchanged, and the epics keep their objectives, so the archive is
  a readable history of the project rather than a dump. Judged: good.
- **`## Epics` is the one thing that changes meaning.** The archive has no `## Epics` listing — the
  epics are sections only — and `TODO.md`'s listing shrinks to one row. That is the right split:
  the listing is an index of *live* epics, and the archive is chronological. The one seam is
  E06, which appears in both, with its objective only in `TODO.md`; a reader of the archived E06
  section is one file away from what the epic was for.
- **The archive is not discoverable from the backlog**, which is what decision 4 addresses.
  Fifteen lines of `TODO.md` give no sign that 108 tasks and five epics of history exist, and
  `docs/archive.md` is not named in `CLAUDE.md`, `README.md` or any index. One line in `CLAUDE.md`
  fixes it; without it, the most likely failure is a future lane re-opening a question this
  repository already answered. **Fixed here** (decision 4): `docs/archive.md` is now in
  `CLAUDE.md`'s *Layout* block, and *Backlog* gained a bullet saying that `TODO.md` holds the open
  work only, that `grep -n '<ID>' TODO.md docs/archive.md` answers "did we already do this", and
  that nothing comes back out of the archive.

## Evidence for this stage

```
$ .taskrail/bin/taskrail archive --dry-run
main: would archive 108 task(s) and 5 epic(s) into docs/archive.md

$ .taskrail/bin/taskrail archive --dry-run --json      # abridged
{"dry_run": true, "backlogs": [{"backlog": "main", "archive": "docs/archive.md",
  "archived": ["T001", …108 IDs…], "epics": ["E01","E02","E05","E07","E08"],
  "held_back": []}], "removed": [], "files": []}

$ grep -c '^| ⬜' TODO.md
1

# preview, on a copy of TODO.md/.taskrail/docs outside this worktree
$ uv run taskrail --root <preview> archive
main: archived 108 task(s) and 5 epic(s) into docs/archive.md
$ uv run taskrail --root <preview> validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)          exit=0
$ uv run taskrail --root <preview> archive --dry-run
main: nothing to archive                                     exit=0
$ wc -l <preview>/TODO.md <preview>/docs/archive.md
 15 TODO.md
157 docs/archive.md
```
