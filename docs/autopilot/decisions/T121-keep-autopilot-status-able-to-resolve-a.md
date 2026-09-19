# T121 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T121-keep-autopilot-status-able-to-resolve-a.md` and its commit
`938ba0e` (artifact and index row alone, no code edited); the reproduction on `main` and against a
temporary detached checkout of `5e8cd1c`, the commit before the archive, which shows every run
flipping from `complete: true` to `complete: false`; the three-lookup probe; and the lane's own
disclosure of a stray write to run `20260918-1`, confirmed by the orchestrator in the run file
(36 members, `T121` present in state `running`).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 0 | The stray `tasks.T121` entry the lane wrote into run `20260918-1` by claiming with the wrong run ID | **leave it; it resolves when T121 merges** · remove it by hand · close the run | **leave it** | The autopilot skill forbids editing a run file by hand — run state is written only through the `autopilot` commands — and none of them removes a member. `autopilot close` would hide the run for good and destroy this task's own reproduction. The entry is also self-healing: once T121 merges, `autopilot merged T121` records the merge in every run that holds it, so the stray member reads `done-merged` like the other 35. The orchestrator verifies that after the merge. The lane was right to stop and ask instead of undoing it, and right to say exactly what changed and what did not. |
| 1 | Which fix | **read the archive only** · record completion once · both | **read the archive** | It keeps every derived state true and repairs all ten runs in this clone with no migration, because the merge records are intact and only the lookup was blind. Recording completion repairs none of the existing runs — no record exists for them — needs a writer where `status` is read-only today, and is stored state that a reverted merge can make stale. The lane's finding that the same blindness makes **`autopilot next` over-dispatch past a run's count** is a second consequence the row did not know about, and only the archive read fixes it. The cost is to be measured in `fix`, as CLAUDE.md asks, not assumed. |
| 2 | What a resumed run needs | **nothing beyond the fix** | **nothing more** | After the fix an archived member reads `done-merged` or `discarded` with its title and kind, and an archived task cannot be reopened (§7.6), so it never needs a lane. |
| 3 | `--json` shape | **unchanged**; an archived member is a normal task row and `problem` stays reserved for a member found nowhere · an additive `archived` key | **unchanged** | The autopilot skill and the orchestrator read specific keys; an extra one has no reader today. YAGNI. |
| 4 | Documentation | **§7.6 names `autopilot status` and `next` as readers of the archive; §12.4's `done-merged`/`discarded` say "in the backlog or its archive"; one changelog bullet** | **as recommended** | §7.6 is where a reader looks for which commands read the archive, and it currently says only what does not. |

Given with the answers: `show`, `list`, `validate` and plain `next` stay archive-blind, as the lane
proposes — the read happens only where a run names a member the backlog no longer holds.
