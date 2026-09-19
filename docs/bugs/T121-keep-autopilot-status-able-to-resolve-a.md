# T121 — Keep autopilot status able to resolve a run whose tasks have been archived

## Symptom

After `taskrail archive` (T114) moved this repository's closed rows from `TODO.md` into
`docs/archive.md`, `taskrail autopilot status` reports every run whose tasks were archived as
unfinished, with none of its tasks resolved: each member reads `state: null`,
`problem: "not in the backlog"`, `done_merged` is 0 and `complete` is false. The run files and the
decision records are intact; `status` misreports them.

## Reproduction

On `main` at `df31678` (after T114's archive commit `5215682`):

```
$ .taskrail/bin/taskrail autopilot status --run 20260918-1 --json
  "count": 35,
  "complete": false,
  "done_merged": 0,
  "tasks": [
    {"id": "T087", "title": null, "kind": null, "state": null, "problem": "not in the backlog"},
    ... the same for all 35 members ...
  "handoff": {"mode": "sequential", "in_review": null, "queue": [], "next": null},
```

Expected, and what the same run read before the archive: `complete: true`, `done_merged: 35`,
each member `done-merged` with its title and kind.

Every run in this clone, summarised from `autopilot status --all --json`:

| run | on `main` (after the archive) | on a detached checkout of `5e8cd1c` (before it) |
|---|---|---|
| 20260918-2 | complete true, 1 done-merged | complete true, 1 done-merged |
| 20260918-1 | complete false, 0 done-merged, 35 `null` | complete true, 35 done-merged |
| 20260917-1 | complete false, 8 `null` | complete true, 8 done-merged |
| 20260915-1 … -7 | complete false, every member `null` | complete true, every member done-merged |

20260918-2's task is still in `TODO.md`, so it is unaffected. (Both columns also show one
`running` T121 lane in 20260918-1: an unrelated slip while claiming this task, reported at the
diagnose gate, not part of the bug.)

## Evidence

A probe (`status._on_mainline`, `status._recorded`, `Project.task`) for T087, T107 and T120:

```
# post-archive checkout (this branch at df31678)
T087 in_checkout_backlog= False done_on_mainline_rows= False recorded_merge= False
T107 in_checkout_backlog= False done_on_mainline_rows= False recorded_merge= False
T120 in_checkout_backlog= False done_on_mainline_rows= False recorded_merge= False

# pre-archive checkout (5e8cd1c, detached), same mainline refs
T087 in_checkout_backlog= True done_on_mainline_rows= False recorded_merge= True
T107 in_checkout_backlog= True done_on_mainline_rows= False recorded_merge= True
T120 in_checkout_backlog= True done_on_mainline_rows= False recorded_merge= True
```

So even before the archive reaches the checkout, the mainline rows no longer show these tasks
closed (`main`'s `TODO.md` has lost them); the pre-archive checkout reads them `done-merged` only
because every one of them has a merge record from `autopilot merged` (12.8), and that record is
honoured only for a task `Project.task` finds.

`status --all --json` takes 1.05–1.21 s on this clone today (three runs: 1.207, 1.063, 1.054 s).

## Root cause

`autopilot status` derives every member's state from the member's backlog row, and three lookups
see only the backlog file, never its archive:

1. `run_status` (`src/taskrail/autopilot/status.py`) calls `project.task(task_id)` and, when it
   returns `None`, emits a `state: null` row with `problem: "not in the backlog"`; `complete` counts
   `done-merged` rows only, so it can never become true again.
2. `_on_mainline` reads the task statuses from the backlog's main file (and its epic files) at
   `refs/heads/<mainline>` and `refs/remotes/<remote>/<mainline>`; once the archive commit is on
   the mainline, an archived ✅ row is in neither, so `done_on_mainline` and
   `discarded_on_mainline` lose it.
3. `recorded_merges` (`src/taskrail/autopilot/merged.py`) skips a recorded merge whose task
   `project.task` does not find, so a proven merge stops counting too.

T107 made `archive` safe for `validate`, ID allocation, the merge driver and `reopen`
(DESIGN.md §7.6), and did not list the autopilot, whose §12.4 states are defined as "✅ on the
local mainline or on `<remote>/<mainline>`" of the backlog.

The same lookup drives `autopilot next` (`next_lanes` in `src/taskrail/autopilot/dispatch.py`):
an archived member gets state `None`, which is not in `COUNTED`, so
`remaining = run["count"] - <COUNTED members>` over-counts what is left, and `next --run` on a
count-based run whose finished members were archived would dispatch past the run's count.

## Ruled out

- **The run files lost data.** `.git/taskrail/runs/*.json` still list every member and every
  `merged` record: 20260918-1 has 35 lanes with a `merged` record, 20260917-1 has 8, each
  20260915 run has one per lane.
- **The merge records are invalid.** The same records make the pre-archive checkout read all 35
  `done-merged` against today's mainline refs, so each record's commit is still on `main`.
- **`branchrows.adopt` should have found the rows.** It adopts a member whose row only its task
  branch holds (T071); these rows are on no branch at all now, and their branches are merged.
- **Claims or worktrees.** The members hold no claim and no worktree; neither enters the
  `not in the backlog` branch.
- **A problem limited to this repository.** The cause is in the CLI: any consumer that archives
  and runs the autopilot sees it, and without merge records (a human merged by hand) even the
  mainline half fails.

## Affected areas

- `src/taskrail/autopilot/status.py` — `run_status`, `_on_mainline`.
- `src/taskrail/autopilot/merged.py` — `recorded_merges`.
- `src/taskrail/autopilot/dispatch.py` — `next_lanes`' state of every lane, and so a count run's
  `remaining`; `_waiting_reason` for a named task (reports "not in the backlog", which is true and
  harmless: an archived task is closed and is never dispatched).
- DESIGN.md §7.6 (*What does not read it*) and §12.4 (`done-merged`, `discarded`); CHANGELOG.md.

## Proposed fix

Read the archive for a run member the backlog no longer holds; record nothing new in the run file.

- `archive.py` gains a reader that parses a backlog's archive document in the checkout into
  `Task`s with the parser the backlog already uses, cached per project, and a lookup
  `archived_task(project, task_id)`.
- `run_status`, `next_lanes` and `recorded_merges` fall back to it when `project.task` returns
  `None`; the member is then derived like any other row.
- `_on_mainline` reads the archive at the same mainline refs as the backlog file (same batched
  blob read), and, without mainline refs, the archive rows in the checkout, so an archived ✅ or ❌
  still counts as closed on the mainline, under the same reopen rule.
- `show`, `list`, `next` without a run and `validate` still do not read the archive.
- `--json` keeps its shape: an archived member is a normal task row again.
- DESIGN.md §7.6 and §12.4 name the autopilot as a reader of the archive; CHANGELOG.md gets a
  *Fixed* bullet.

Recording a run's completion once in its run file is not proposed: every run in this clone was
archived before any such record existed, so it would not repair one of them, and it adds a stored
state that a later reopen or a reverted merge can make stale.
