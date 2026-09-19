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
