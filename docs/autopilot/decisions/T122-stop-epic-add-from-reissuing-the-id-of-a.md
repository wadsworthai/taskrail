# T122 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T122-stop-epic-add-from-reissuing-the-id-of-a.md` and its commit
`b587d52` (artifact and index row alone); the four reproductions, all in a scratch clone, with
`epic add` never run without `--id` on the real backlog; and `cmd_epic_add` at
`src/taskrail/cli.py:1408-1413`, read by the orchestrator, which allocates from `backlog.epics`
alone.

**A correction to the orchestrator's brief, accepted:** the brief said `epic add` "on this
repository today reissues E07". That stopped being true the moment E09 was added: on `main` it now
returns E10. The defect is still live — it returns as soon as the highest-numbered epic is archived,
and any consuming repository with that shape hits it now — so the lane reproduced it at `5215682`,
the commit where T114 merged. Reproducing at the commit where the conditions held, rather than
declaring the bug gone, is what this correction needed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | How much of T107's task-ID treatment epics get | **(a) the working-tree archive only** · (b) full §6.3 parity — live epics and archives on every branch, plus a reservation ledger · (c) parity without the ledger | **(a)**, and **open (b) as a follow-up** | The lane's argument is exact: an epic can only be archived after it has been in the backlog, so any archived ID the working tree lacks must come from a branch that never reached this history — which is the older cross-branch race, not this bug. Evidence 4 shows that race exists with no archive involved (E10 on two branches), so fixing it here would widen this task into a new guarantee. It is real, though, and task IDs already have it, so it gets its own task. |
| D2 | Should `validate` refuse an epic ID that also exists in the archive? | **no; refuse at the write instead — `epic add --id` of an archived ID exits 5** · (b) `validate` reads archive epic headings · (c) `archive` refuses to append into an existing section whose name differs · (d) leave `--id` alone | **refuse at the write**, and **open (c) as a follow-up** | §7.6's rule that `validate` never reads the archive was a deliberate T107 decision, and reversing it would cost every consumer's CI a second file on every run. What makes epics genuinely different is not that duplicates are bad but **evidence 3**: once a reissued epic is itself archived, `archive._ensure_section` merges it under the old epic's heading and name — two objectives stacked, a new task filed under *Current-branch workflow*. That is silent structural corruption of the history, and it can still arrive through a hand edit or a merge that this fix does not see. Guarding the place the damage happens — (c) — is the right second task. |
| D3 | The regression test | **archive E02 and assert E03; negative control deleting the archive and asserting E02; `--id E02` refused while archived** | **as recommended** | The control is what proves the fixture exercises the gap rather than something else in it: without the archive the next ID is a genuine reissue, so the scan is what makes E03 correct. |
| D4 | Documentation | **§6.3 on how epic IDs are allocated and that they are not scanned across branches or reserved; a §7.6 bullet that `epic add` reads the archive's epic headings; one changelog bullet** | **as recommended** | §6.3 stating plainly that epics are *not* race-free across branches is what keeps the follow-up from D1 honest until it is done. |

## fix gate

Reviewed: commit `29333f6` and the diff `5be733a..HEAD` — `archived_epic_ids` in `ids.py`, the two
changes in `cmd_epic_add`, three tests, the §6.3 and §7.6 lines, the changelog bullet, the two
follow-up rows (T124, T125) and the artifact, with `validate`, `src/taskrail/autopilot/`, the
workflows and `install.py` untouched; the recorded failures before the fix, **`E02` reissued and an
archived `--id` accepted**, with the negative control passing as it must; the end-to-end run at
`5215682`, where the fixed source now returns E09 and refuses `--id E07` with exit 5; and
`taskrail checks T122 --stage fix` (1,259 passed). The orchestrator read the §7.6 lead-in in place.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The §7.6 lead-in, "neither the ID scan nor the merge driver needs anything new", now sits above a bullet describing new code | leave it · **reword to "needs nothing new from the format"** | **reword** | The sentence was true when T107 wrote it. With `archived_epic_ids` added, "needs anything new" overstates: the *format* needed nothing new, the *readers* did. A document that says "nothing new" directly above the new thing is the same kind of small inaccuracy this session has corrected several times — in T110's title, in §9's planned marker — and it costs one clause. |
| 2 | T125's description edited to stop naming a scratch-copy task ID that the real T124 now collides with | **accept** | **accept** | Citing a scratch ID that later becomes a real task's ID would send a reader to the wrong row. Rewording it through `taskrail edit`, and marking the artifact's scratch IDs as such, is the right repair. |

## close

Reviewed: the whole diff against the merge base — the fix in `ids.py` and `cmd_epic_add`, three
tests, the §6.3 and §7.6 lines with the reworded lead-in, the changelog bullet, T124's and T125's
rows, the artifact with its *Impact* section, and T122's `✅`; `taskrail validate` (6 tasks,
0 errors). The last full `checks` run predates three commits that touch no code.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | **`fix` / `cli`** | **`fix` / `cli`** | `epic add` reissued an ID it had already handed out; the change is in the CLI. |
| 2 | Hand-off order | **behind T123** | **behind T123** | T123 is published and awaiting merge; this branch will then need a rebase with a known-class `CHANGELOG.md` conflict. |

## published ahead of T123, on the human's instruction

Hand-off is sequential by default, and T123 was in review when the human asked for this branch's
pull request directly. Publishing it puts two branches in review at once. That is the human's call
to make and they made it; recorded here so the order is not mistaken for an oversight.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Publish while T123 is in review | **publish now** · wait for T123 to merge | **publish now** | Asked for by the human. `origin/main` is still `df31678`, this branch's base, so no rebase is needed. Whichever of the two merges second will meet one known-class conflict — a `CHANGELOG.md` bullet — resolved at its rebase. |

Answered by the human (the repository's maintainer), 2026-09-19.
