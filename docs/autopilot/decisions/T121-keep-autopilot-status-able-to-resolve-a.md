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

## fix gate

Reviewed: commit `c18eff0` and the diff `6089ae1..HEAD` — the archive reader in `archive.py`, the
one-line fallback in `status.py`, `dispatch.py` and `merged.py`, `_on_mainline` reading the archive
at the mainline refs, a new test module, the §7.6 and §12.4 lines, the changelog bullet and the
artifact, with `ids.py`, the workflows and every run file untouched; the recorded failures before
the fix, **one per blind lookup** and one confirming the over-dispatch past a count of 2; the guard
that `list` and `show` stay archive-blind passing before and after; `taskrail checks T121 --stage
fix` (1,262 passed); and `autopilot status --all` from the branch, where all ten finished runs read
`complete: true` again. The orchestrator read the changelog's cost sentence in place.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | **approve** | **approve** | Every root-cause lookup has a test that failed for its own reason and now passes, and the live repository's ten runs are the end-to-end proof. |
| 2 | The header of a *newly created* archive file changed, since "reads it only so an archived ID is never allocated again" became false | **keep** · revert | **keep** | Small, inseparable from the fix, and the same class of accuracy repair this session has made several times. The existing `docs/archive.md` is not rewritten, which is right: it is history. |
| 3 | No dedicated test for `_on_mainline`'s no-mainline-refs branch | **accept without a test** · add a parametrized case | **accept** | Three lines mirroring an existing fallback, reached only outside git or before a first commit. Recorded here as a known untested branch rather than left implicit. |
| 4 | A follow-up for `merged._mainline_refs` running `rev-parse` once per task | **open it** · leave it | **open it** | CLAUDE.md allows optimizing only what a measurement shows is slow, and this one is measured: 0.73 s of a 2.93 s `status --all`, under cProfile. It predates this task, so it is a new task, not a widening of this one. |

On the cost figures, for whoever reads the changelog: the bullet claims only what was measured
directly — about 15 ms for the archive reads, split into 3 ms of parsing and 12–14 ms at the two
mainline refs. The wall-time comparison against the pre-archive checkout (≈1.7 s against ≈2.3 s)
is **not** evidence of a slowdown from this change: it was taken while other lanes' suites were
running on the same machine, and the profile attributes the time to per-member work that predates
T121. That is why the bullet does not quote it, and it should not be quoted later as if it were.
