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

The full caller breakdown of the git processes, from `pstats.print_callers` on one more profiled
run of the same command, kept so whoever measures the other per-member calls next starts from it:

```
gitutil.run  <-  review.resolve_remote        232   0.521s
                 review._sha                  183   0.489s
                 gitutil.refs                 110   0.250s
                 gitutil.branch_exists         63   0.162s
                 gitutil.common_dir            61   0.133s
                 review._is_ancestor           59   0.200s
                 gitutil.worktree_branches     54   0.129s
                 status._lane_details           8   0.022s
                 status._resolves               4   0.010s
                 status._fork_point             4   0.011s
                 status._changed_in_worktree    3   0.012s
                 stack._reopened_since          3   0.009s
                 status._reopened_elsewhere     2   0.006s
                 gitutil.worktrees              2   0.004s
                 status._closed_time            1   0.003s
                 mergedriver.changelog_paths    1   0.003s
review.resolve_remote  <-  merged._mainline_refs   59   0.279s
                           branchrows._lookup      53   0.227s
                           query.base_dict          2   0.008s
                           status._on_mainline      1   0.004s
                           stack._find              1   0.004s
```

## Change set

- `src/taskrail/autopilot/merged.py` — `_mainline_refs` keeps what it computes in `project.cache`
  under `MAINLINE_REFS_KEY = "autopilot_mainline_refs"`, a dict keyed by backlog name, and
  computes a backlog's refs only the first time it is asked. Its docstring names the measurement.
  No signature changes; `_still_on_mainline`, `_latest_record`, `recorded_merges` and `cmd_merged`
  are untouched.
- `tests/test_autopilot_merged.py` — `test_recorded_merges_resolve_the_mainline_refs_once_per_backlog`:
  four merge records in one backlog (three on `main`, one on an unmerged lane commit) read through
  `recorded_merges`, with `merged.resolve_remote` wrapped to count its calls. It asserts the same
  statuses as before (the stray record still does not count) and one resolution.
- `docs/chores/T126-…md` and `docs/chores/README.md` — this write-up and its index row.

## Decisions (scope gate)

Answered by the orchestrator, each as recommended; recorded in
`docs/autopilot/decisions/T126-resolve-the-mainline-refs-once-per-backl.md`.

1. **Go ahead**: the reproduced profile (59 calls, 236 of 795 git processes, 26 %) justifies it.
2. **Measure** by, in order of weight: the git process count (load-free); byte-identical
   `status --all --json` from old and new code against the same clone; cProfile cumulative time
   over five interleaved old/new runs, as min / median / max with the load. Recommend not merging
   if the count does not fall by about 236, if the output differs in a byte, or if the new median
   total is not below the old minimum. Wall time is reported, never evidence.
3. **Cache** in `project.cache`, per backlog, for one command's lifetime. It holds which mainline
   ref *names* exist, not their commits: `_is_ancestor` still reads each ref when it runs, so the
   cache could go stale only if a mainline ref were created or deleted mid-command, which nothing
   does. Every command that fetches (`autopilot merged`, `autopilot status --fetch`) reloads the
   project, starting an empty cache; the `autopilot_` prefix makes `branchrows._forget_derived`
   drop it too. `recorded_merges` is itself cached for the same lifetime (`status.RECORDED_KEY`).
   No module-level cache: it would leak across projects in one process and never invalidate.
4. **No changelog line**: nothing a user can observe changes except speed.
5. **No follow-up** for the other per-member git calls (the breakdown above): none was this row's
   target, and each would need its own measurement.

## Out of scope

- The other per-member git calls in the breakdown above — `branchrows._lookup`'s 53
  `resolve_remote` calls, `gitutil.refs`, `branch_exists`, `common_dir`, `worktree_branches`, and
  the per-record `_sha`/`_is_ancestor` in `_still_on_mainline`.
- `archive.py`, `ids.py`, `cli.py`, run files, `CHANGELOG.md`.

## Verification

**The new test, seen failing first.** Before the cache (`uv run pytest tests/test_autopilot_merged.py -q -k once_per_backlog`):

```
E        +  where 4 = len([(PosixPath('/tmp/pytest-of-abigail/pytest-32/test_recorded_merges_resolve_t0'), 'main', 'origin'), (PosixPath('/tmp/p..., 'main', 'origin'), (PosixPath('/tmp/pytest-of-abigail/pytest-32/test_recorded_merges_resolve_t0'), 'main', 'origin')])
tests/test_autopilot_merged.py:935: AssertionError
FAILED tests/test_autopilot_merged.py::test_recorded_merges_resolve_the_mainline_refs_once_per_backlog
1 failed, 39 deselected in 1.22s
```

The statuses assertion before it passed, so the test failed only on the count: four resolutions
for four records. With the cache, `uv run pytest tests/test_autopilot_merged.py tests/test_autopilot_archived.py -q`:
`46 passed in 18.55s`.

**Comparison of old and new code** against this clone (twelve run files). The old code is
`git archive 0fb3fe0 src`, extracted to a scratch directory; the new code is this branch's `src`.
A scratch script runs each measurement in a fresh interpreter with `PYTHONPATH` set to one tree
(the reported `taskrail.__file__` confirms which), alternating old, new, old, new for five rounds.
Load average before: `1.92 2.03 1.90`, after: `2.56 2.18 1.95` (16 cores, other lanes' suites
running).

```
old 1: total 2.414s  subprocess 801  recorded_merges 1.042s  _mainline_refs 59 calls 0.641s  resolve_remote 117  load 2.33
new 1: total 1.802s  subprocess 569  recorded_merges 0.411s  _mainline_refs 59 calls 0.012s  resolve_remote  59  load 2.33
old 2: total 2.411s  subprocess 801  recorded_merges 1.020s  _mainline_refs 59 calls 0.630s  resolve_remote 117  load 2.33
new 2: total 1.806s  subprocess 569  recorded_merges 0.430s  _mainline_refs 59 calls 0.015s  resolve_remote  59  load 2.38
old 3: total 2.459s  subprocess 801  recorded_merges 1.039s  _mainline_refs 59 calls 0.631s  resolve_remote 117  load 2.38
new 3: total 1.781s  subprocess 569  recorded_merges 0.417s  _mainline_refs 59 calls 0.009s  resolve_remote  59  load 2.43
old 4: total 2.260s  subprocess 801  recorded_merges 0.949s  _mainline_refs 59 calls 0.572s  resolve_remote 117  load 2.43
new 4: total 1.659s  subprocess 569  recorded_merges 0.378s  _mainline_refs 59 calls 0.009s  resolve_remote  59  load 2.56
old 5: total 2.308s  subprocess 801  recorded_merges 0.985s  _mainline_refs 59 calls 0.599s  resolve_remote 117  load 2.56
new 5: total 1.813s  subprocess 569  recorded_merges 0.404s  _mainline_refs 59 calls 0.010s  resolve_remote  59  load 2.56

old total:           min 2.260  median 2.411  max 2.459
new total:           min 1.659  median 1.802  max 1.813
old recorded_merges: min 0.949  median 1.020  max 1.042
new recorded_merges: min 0.378  median 0.411  max 0.430
```

(`total` is the profiled command's cumulative time, which here equals its wall time.)

1. **git process count**: 801 → 569, **232 fewer** in every round. That is 236 removed less the 4
   the one backlog still spends, as predicted; `resolve_remote` falls from 117 to 59 calls, the 58
   `_mainline_refs` no longer makes. The baseline is 801 rather than the scope stage's 795 because
   the clone's lanes moved in between; old and new were measured against the same state.
2. **Output**: in this unfrozen run the outputs of each round differed, and only in
   `idle_minutes`, which `status` derives from the clock, when a round straddled a minute
   boundary (for example round 1: `"idle_minutes": 1243` against `1244` on two lines). Round 5's
   old output and round 4's new output are byte-identical (sha256 `7c98d7c8…`). To compare without
   the clock, a second scratch script freezes `status`'s `datetime.now` at `2026-09-19T12:00:00+00:00`
   and runs old then new three times: `cmp` reports **all three rounds identical**, and all six
   files share sha256 `a949efd3dbcffde26b58b47c264d81390c4024a7c6bc8724aee6fcabbbcd4e73`
   (75,671 bytes).
3. **cProfile time**: the new median total (1.802 s) is below the old minimum (2.260 s), and the
   new maximum (1.813 s) is below the old minimum too. `_mainline_refs` falls from 0.57–0.64 s to
   0.009–0.015 s; `recorded_merges` from a median of 1.020 s to 0.411 s.

None of the three not-merge conditions holds.

**Checks**: `taskrail checks T126 --stage implement`: `1266 passed in 176.64s (0:02:56)`;
`lint: not configured`; `T126 … passed`.
