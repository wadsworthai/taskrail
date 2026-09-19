# T126 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T126-resolve-the-mainline-refs-once-per-backl.md` and its commit
`5e20c5c`; the profile reproduced five times on `main` as it stands after T121, with the load
average and the concurrent suites recorded beside it; and the caller breakdown showing where the
795 git processes come from.

**A correction to the row, accepted:** `_mainline_refs` runs once per merge *record*, not once per
task, and each call starts four git processes, not two. The measurement holds anyway — 59 calls,
236 of 795 git processes, 0.53 s of 2.05 s, stable within 6 % across five runs — and it now rests
on this lane's profile rather than T121's.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the saving still worth a change? | **go ahead** · discard | **go ahead** | A quarter of `status --all`, stable across runs, removed by memoizing one function. This is what CLAUDE.md allows an optimization to rest on: a measurement, named in the change. |
| 2 | How to measure before and after so load cannot fake it | **git process count first; byte-identical `--json` output; interleaved cProfile runs with min/median/max** · wall time over many runs | **as recommended, with the lane's own not-merge rule** | The process count cannot be moved by load, which is the lesson T121's figures taught. Do not merge if the count does not fall by about 236, if the output differs by a byte, or if the new median is not below the old minimum. Wall time is reported and never used as evidence. |
| 3 | Where the cache lives | **`project.cache`, per backlog, one command's lifetime** · a local dict passed down · module-level `functools.cache` | **`project.cache`** | It is the lifetime `recorded_merges` already has, so the refs cannot outlive the answer they feed, and T121's reader uses the same home. It stores which ref *names* exist, not their commits, and `_is_ancestor` still reads the refs themselves, so staleness would need a mainline ref created or deleted mid-command. A module-level cache would leak across projects in one process — the test suite. |
| 4 | A changelog line | **no** | **no** | Only speed changes, and the changelog records user-facing behaviour. |
| 5 | A follow-up for the other per-member git calls in the same profile | open one now · **no** | **no** | None was this row's measured target, and each would need its own measurement before it could justify a change. The profile is kept in the artifact for whoever measures next. |
