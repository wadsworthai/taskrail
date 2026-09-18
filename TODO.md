# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E06 | Repository tooling | How this repository runs its own backlog with taskrail while it is worked on | —    |
| E09 | taskrail phase 3 | Keep the CLI and the autopilot correct as the backlog they manage changes shape | —    |

## E06 — Repository tooling

Done when: this repository's own backlog runs through the taskrail autopilot

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T114 | chore   | 1   | —          | Archive this repository's closed tasks and epics | Run taskrail archive on TODO.md now that run 20260918-1's branches are merged: it moved 108 closed rows and epics E01, E02, E05, E07 and E08 into docs/archive.md, holding nothing back.   |

## E09 — taskrail phase 3

Done when: the tool's own state and its identifiers survive the operations it offers on the backlog

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T121 | bug     | 2   | —          | Keep autopilot status able to resolve a run whose tasks have been archived | taskrail archive moved this repository's closed rows out of TODO.md and autopilot status stopped being able to resolve them: run 20260918-1 reported count 35, complete true with 35 done-merged before the archive and count 35, complete false with all 35 tasks in state null after it, and the nine older runs read the same way. status computes each task's state from its backlog row, so a run whose tasks are archived has nothing left to resolve and a finished run reads as unfinished for ever. Nothing is lost -- the run files and the decision records are intact -- but status misreports what was done, and a run that someone tried to resume would show none of its tasks. Decide whether status reads the archive for a task it cannot find, whether a run records its own completion once and stops recomputing, or both; T107 considered validate, ID allocation, the merge driver and reopen when it built archive, and did not consider the autopilot's run files. |
| ⬜ | T122 | bug     | 2   | —          | Stop epic add from reissuing the ID of an archived epic | taskrail epic add allocates epic_prefix plus two digits one above the backlog's highest, and it does not look at the archive: with E01, E02, E05, E07 and E08 archived and only E06 left in TODO.md, epic add allocated E07, the ID of the archived epic Current-branch workflow, and wrote it into the Epics table beside a section of that name in docs/archive.md. Reproduced on this repository right after T114 merged; the row was reverted by hand and E09 was passed explicitly instead. Task IDs are safe because T107 made ids.used_ids scan the archive on the working tree and on every scanned branch; epic IDs have no such scan. Give epic allocation the same guarantee DESIGN.md section 6.3 gives task IDs, and decide whether validate should refuse an epic ID that exists in the archive. |
| ⬜ | T123 | chore   | 1   | —          | Cancel a pull request's superseded workflow runs when a new one is queued | Every push to a pull request queues a fresh run of ci.yml and taskrail.yml while the runs from the previous push keep going: the suite takes about three minutes on two matrix legs, so a branch pushed twice in a minute burns runner time on a commit nobody will merge and the checks a reviewer sees are a race between the two. Add a concurrency group keyed on the workflow and the ref with cancel-in-progress true, so queueing supersedes rather than adds. T108 left concurrency out of ci.yml at its scope gate as beyond what its row asked for; this row asks for it. Decide whether the generated workflow's template gets the same block -- it runs validate in every consuming repository and has the same waste -- or whether this repository's own ci.yml is the whole change, and decide what the group key is, since a run on the mainline after a merge must not be cancelled by the next push. |
