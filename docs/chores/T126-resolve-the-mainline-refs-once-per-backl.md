# T126 — Resolve the mainline refs once per backlog when checking recorded merges

Kind: chore · Epic: E09 · Depends on: — · Branch: `T126-resolve-the-mainline-refs-once-per-backl`

## Goal

`recorded_merges` (`src/taskrail/autopilot/merged.py`) checks every merge record of every task a
run holds, and for each record `_still_on_mainline` calls `_mainline_refs(project, task)`, which
resolves the backlog's remote (`resolve_remote`: `git config --get branch.<mainline>.remote` and
`git remote`) and `rev-parse`s both mainline refs: four git processes per record, although the
result depends only on the task's backlog. Resolve it once per backlog per project.

This is an optimization, so CLAUDE.md's *Premature optimization* principle applies: it is allowed
only because a measurement shows the cost, and the change names what was measured.

## Measurement on `main` before the change

T121 measured this under cProfile (1.18 s of 2.93 s in `recorded_merges`, 0.73 s in
`_mainline_refs`, 54 calls), with other lanes' suites running. T121's fix changed what `status`
does, so the profile was taken again on `origin/main` at `0fb3fe0` (this branch before any edit).

Method: an in-process profiler script runs `taskrail.cli.main(["--root", <worktree>, "autopilot",
"status", "--all", "--json"])` under `cProfile` five times in one process, and reports per run the
call count and cumulative time of `recorded_merges`, `_still_on_mainline`, `_mainline_refs`,
`resolve_remote`, `_sha`, `_is_ancestor` and `subprocess.run`. Twelve run files exist in the clone.

```
run 1: wall 2.192s   subprocess.run calls=795 cum=1.712s (78.1%)
                     recorded_merges calls=1 cum=0.911s (41.6%)
                     _still_on_mainline calls=64 cum=0.891s (40.6%)
                     _mainline_refs calls=59 cum=0.558s (25.5%)
                     resolve_remote calls=116 cum=0.508s   _sha calls=183 cum=0.464s   _is_ancestor calls=59 cum=0.180s
run 2: wall 2.051s   subprocess.run 795 · recorded_merges 0.870s (42.4%) · _mainline_refs 59 calls 0.526s (25.6%)
run 3: wall 2.055s   subprocess.run 795 · recorded_merges 0.874s (42.5%) · _mainline_refs 59 calls 0.531s (25.8%)
run 4: wall 2.049s   subprocess.run 795 · recorded_merges 0.870s (42.4%) · _mainline_refs 59 calls 0.529s (25.8%)
run 5: wall 2.056s   subprocess.run 795 · recorded_merges 0.875s (42.6%) · _mainline_refs 59 calls 0.534s (26.0%)
```

`pstats.print_callers` on the same profile attributes the git processes: `resolve_remote` spawned
232 (59 of its 116 calls come from `_mainline_refs`, 53 from `branchrows._lookup`, the rest one or
two each), `_sha` 183. `_mainline_refs` therefore spawns 59 × 4 = **236 of the 795 git processes**
and takes **0.53 s of 2.05 s (26 %)** of `status --all`, consistently across five runs (spread
0.526–0.558 s). The load average was 2.47 on 16 cores while this ran, with two other lanes'
`pytest -q` suites active; the call counts do not depend on load, and the cumulative times held
within 6 % over five runs.

The saving is still worth the change: a quarter of the command, removed by memoizing one function.

## Change set

- `src/taskrail/autopilot/merged.py` — `_mainline_refs` keeps what it computes in `project.cache`
  under `autopilot_mainline_refs`, a dict keyed by backlog name, and computes a backlog's refs only
  the first time it is asked (about four lines). No signature changes; `_still_on_mainline`,
  `_latest_record`, `recorded_merges` and `cmd_merged` are untouched.
- `tests/` — one test beside the existing `autopilot merged`/`status` tests: several recorded merges
  in one backlog, read through `recorded_merges`, resolve the mainline refs once (counted by
  wrapping `merged.resolve_remote`), and still return the same statuses.
- `docs/chores/T126-…md` and `docs/chores/README.md` — this write-up and its index row.

## Decisions needed

1. **Reproduced profile** (above): `_mainline_refs` is still 59 calls and 26 % of `status --all`.
   Recommendation: go ahead. Alternative: discard the task — not recommended, the share is stable
   and large.
2. **How before and after are compared so load cannot fake it.** Recommendation, in order of
   weight:
   - **git process count** for `status --all`, from cProfile's `subprocess.run` calls — load-free.
     Expected: 795 → 563 (236 removed, 4 added back for the one backlog), `_mainline_refs`' body
     running once instead of 59 times.
   - **identical output**: `status --all --json` from the old and new code, run back to back
     against the same clone, compared byte for byte.
   - **cProfile cumulative time** of `recorded_merges` and of the whole command, five runs of the
     old and five of the new code *interleaved* (old, new, old, new, …) so a burst of load hits both,
     reported as min / median / max with the load average at the time.

   Not merging is recommended if the process count does not fall by about 236, if the output
   differs in any byte, or if the new median total is not below the old code's minimum. Wall time
   alone is reported, never used as the evidence.
   Alternative: wall time over many repetitions — rejected, it is what T121 found unreliable here.
3. **Where the cache lives and how long.** Recommendation: `project.cache`, key
   `autopilot_mainline_refs`.
   - Lifetime is the `Project` object, i.e. one CLI command. `recorded_merges` is itself already
     cached there for the project's lifetime (`status.RECORDED_KEY`), so the refs cannot outlive
     the answer they feed.
   - Invalidation: every command that moves the refs reloads the project after fetching
     (`autopilot merged` and `autopilot status --fetch` both call `_load(args)` again), which starts
     an empty cache. The `autopilot_` prefix also makes `branchrows._forget_derived` drop it, which
     only costs one recomputation.
   - Stale-ref risk: no long-lived process holds a `Project` across a ref change; the only ref
     `autopilot merged` writes after reading records is the task branch it deletes in `--cleanup`,
     which is not a mainline ref. The cached value is the list of mainline ref *names* that exist, not
     their commits (`_is_ancestor` still reads the ref when it runs), so it could go stale only if a
     mainline ref were created or deleted mid-command, which nothing does.
   - Alternatives: a local dict inside `recorded_merges` passed down to `_latest_record` — equally
     correct but changes two signatures and `cmd_merged`'s call for no gain, since `cmd_merged` asks
     for one task; a module-level `functools.cache` — rejected, it would leak across projects in one
     process (the test suite) and never invalidate.
4. **CHANGELOG.md.** Recommendation: no line. The change alters no output, flag or behaviour a
   user can observe beyond speed, and the changelog lists user-facing changes. Alternative: one
   bullet quoting the measured saving.

## Out of scope

- The other per-member git calls the same profile shows — `branchrows._lookup`'s 53
  `resolve_remote` calls, `gitutil.refs` (110 processes), `branch_exists` (63), `common_dir` (61),
  `worktree_branches` (54), and the per-record `_sha`/`_is_ancestor` in `_still_on_mainline`. They
  are real but were not what the row measured; a follow-up could be opened if the orchestrator
  wants one, each justified by its own measurement.
- `archive.py`, `ids.py`, `cli.py`, run files.

## Verification

Planned:

- `taskrail checks T126 --stage implement` (the full suite).
- The new test fails without the cache (resolves once per record) and passes with it.
- The three comparisons of decision 2, recorded here with their real output.
