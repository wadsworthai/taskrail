# T064 — Skip a task merged on the remote mainline but not pulled in autopilot next

Kind: bug · Epic: E02 · Status: fixed

Source: found on the way in [T062](T062-treat-a-task-discarded-on-its-unmerged-b.md) (its *Verification*,
"Found on the way, not fixed here", and *Impact*), opened as decided in
[T062's autopilot decisions](../autopilot/decisions/T062-treat-a-task-discarded-on-its-unmerged-b.md),
fix gate question 2. It continues the lane-state work that started from the findings of
[the T033 autopilot trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md).

## Symptom

A lane closes its task on its branch — `taskrail done <ID>` or `taskrail discard <ID>`, committed —
and the branch is merged into `<remote>/<mainline>`. The orchestrator's checkout fetches (as
`autopilot merged` does with `git fetch --prune`) but its local mainline is not pulled; nothing in
the autopilot procedure pulls it. From that checkout:

- `autopilot status` reads the task `done-merged` (for `✅`) or `discarded` (for `❌`);
- `autopilot next` (preview) offers the same task in `dispatch`, and `autopilot next --run R`
  dispatches it again to a new lane, records `dispatched` for it and, for `✅`, spends the run's last
  place on it;
- the same holds after the lane's worktree and local branch are removed, and for a task closed from
  another clone that never was in a run.

Expected: `autopilot next` never offers a task that `autopilot status` reads as `done-merged` or
`discarded`; a lane started for it can only find the task closed on its base and stop.

## Reproduction

A throwaway Python script outside the repository (`repro.py`), run with this branch's CLI:
`uv run python repro.py`. For `done` and then for `discard`, it builds a
repository under a temporary directory — `TODO.md` with pending tasks `T001` (bug, 1 pt), `T002`,
`T003`, `T004` (2–4 pts), `[autopilot] enabled = true`, `max_lanes = 10`, a bare `origin` — and calls
`taskrail.cli.main` in-process:

1. `autopilot start --count 5`, then `autopilot next --run <run>` dispatches `T001`–`T004`;
2. `git worktree add <lane> -b T001-first-bug origin/main`, `--root <lane> claim T001 --owner lane
   --run <run>`, then `done` (or `discard`) `T001` and `git commit -am` in the lane;
3. moves `T001`'s `dispatched` time 16 minutes into the past (`claim_grace_minutes` is 15);
4. prints `autopilot status --run <run>`, `autopilot next` (preview), `taskrail next`, `show T001`
   and the `T001` cell at `main` and at `origin/main`;
5. `git push origin T001-first-bug:main` (the merge), `git fetch origin` without pulling `main`,
   repeats step 4, then runs `autopilot next --run <run>`;
6. removes the lane worktree and deletes the local branch (as `autopilot merged --cleanup` does),
   repeats step 4;
7. `git merge --ff-only origin/main` (the pull), repeats step 4;
8. `reopen T001 --reason "not finished"` on the local `main`, commits it with the result's
   `commit_message` (its `Reopens: T001` trailer) without pushing, repeats step 4.

A third block clones `origin` elsewhere, claims and marks `T004` done there, pushes it to
`origin/main`, fetches in the first checkout and prints `autopilot next` (preview).

## Evidence

```text
$ uv run --directory /…/.worktrees/T064-skip-a-task-merged-on-the-remote-mainlin python /…/T064/repro.py
===== closing with `done` =====
autopilot next --run 20260915-1: dispatch ["T001", "T002", "T003", "T004"]
claim T001 in the lane: 0
done T001 in the lane: 0
--- closed and committed on the branch, dispatch 16 minutes old
autopilot status --run 20260915-1: {"T001": "done-branch", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T002", "T003", "T004"]
show T001: {"status": "pending", "state": "done-branch"}
row T001 at main / origin/main: ⬜ / ⬜
--- branch merged into origin/main, fetched, local main not pulled
autopilot status --run 20260915-1: {"T001": "done-merged", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ✅
autopilot next --run 20260915-1: {"dispatch": ["T001"], "skipped": [], "remaining": 0}
--- lane worktree and local branch removed (as `autopilot merged --cleanup` does)
autopilot status --run 20260915-1: {"T001": "done-merged", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ✅
--- local main pulled
autopilot status --run 20260915-1: {"T001": "done-merged", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T002", "T003", "T004"]
show T001: {"status": "done", "state": "done"}
row T001 at main / origin/main: ✅ / ✅
--- reopened and committed on local main, not pushed (origin/main still closed)
autopilot status --run 20260915-1: {"T001": "done-merged", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ✅
===== closing with `discard` =====
autopilot next --run 20260915-1: dispatch ["T001", "T002", "T003", "T004"]
claim T001 in the lane: 0
discard T001 in the lane: 0
--- closed and committed on the branch, dispatch 16 minutes old
autopilot status --run 20260915-1: {"T001": "discarded-branch", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T002", "T003", "T004"]
show T001: {"status": "pending", "state": "discarded-branch"}
row T001 at main / origin/main: ⬜ / ⬜
--- branch merged into origin/main, fetched, local main not pulled
autopilot status --run 20260915-1: {"T001": "discarded", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ❌
autopilot next --run 20260915-1: {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}], "remaining": 1}
--- lane worktree and local branch removed (as `autopilot merged --cleanup` does)
autopilot status --run 20260915-1: {"T001": "discarded", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ❌
--- local main pulled
autopilot status --run 20260915-1: {"T001": "discarded", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T002", "T003", "T004"]
show T001: {"status": "discarded", "state": "discarded"}
row T001 at main / origin/main: ❌ / ❌
--- reopened and committed on local main, not pushed (origin/main still closed)
autopilot status --run 20260915-1: {"T001": "discarded", "T002": "dispatched", "T003": "dispatched", "T004": "dispatched"}
autopilot next (preview): {"dispatch": ["T001"], "skipped": [{"id": "T002", "reason": "dispatched in run 20260915-1"}, {"id": "T003", "reason": "dispatched in run 20260915-1"}, {"id": "T004", "reason": "dispatched in run 20260915-1"}]}
taskrail next: ["T001", "T002", "T003", "T004"]
show T001: {"status": "pending", "state": "pending"}
row T001 at main / origin/main: ⬜ / ❌
===== T004 closed from another clone, never in a run =====
claim T004 in the other clone: (0, 'taskrail: warning: T004 was claimed on branch main, but its branch is T004-fourth; work on that branch, or run `taskrail branch T004 <NAME>` to name the branch the task is worked on\n')
done T004 in the other clone: (0, '')
autopilot next (preview): ["T001", "T002", "T003", "T004"]
row T004 at main / origin/main: 1 pending / 1 done
```

Between the merge and the pull, `status` and `next` disagree about `T001` in both runs: `status`
says `done-merged` or `discarded`, `next` offers it, and `next --run` dispatched it again (for `✅`
with `remaining: 0`, the run's last place). After the pull both agree. The `claim` warning in the
last block is the other clone claiming on `main`, which does not matter here.

The reopen block shows a second, older disagreement that the fix must not spread: once `T001` is
reopened on the local `main` and not pushed, `status` still reads it `done-merged` (or `discarded`)
from `origin/main`, while `next` correctly offers it.

## Root cause

`autopilot.dispatch.next_lanes` takes its candidates from `query.eligible`, and none of its skip
checks reads the mainline refs:

```python
candidates = eligible(project, None, claimed)
stack.done_on_branch(project)  # read git before the lock; both are cached per project
done_on_mainline(project)
```

- `query.eligible` keeps tasks whose `query.state` is `pending`. `state` reads `✅`/`❌` only from the
  checkout's own rows (`task.status`), which stay `⬜` until the mainline is pulled, and from the task
  branch tips (`stack.done_on_branch`, `discarded_on_branch`). `stack._find` deliberately drops a
  tip whose task is closed on a mainline ref (`if task_id in merged: continue`, `elif task_id not in
  closed`), because §7 treats "closed on a mainline ref" as merged — and so the task falls through
  to `pending`. With the branch removed there is no tip at all.
- `next_lanes` does call `done_on_mainline(project)`, but only to warm the cache for `task_state`,
  which it applies to run members to find occupied lanes. The candidate loop's reasons are
  `failed` in a run, a state in `OCCUPYING` (`done-merged` and `discarded` are not), a full group, and
  the base. So a candidate `task_state` would read `done-merged` or `discarded` is dispatched.

The disagreement in the reopen block has its own cause in `autopilot/status.py` `_on_mainline`: it
unions the `✅` and `❌` rows of `refs/heads/<mainline>` and `refs/remotes/<remote>/<mainline>`, with
no reopen rule, so a row still closed on one ref counts even when the other ref has the
`Reopens: <ID>` commit that reopened it. §7 applies that rule to task-branch tips
(`stack._reopened_since`) but not to the two mainline refs. It matters here because the fix below
makes `next` follow `_on_mainline`.

## Ruled out

- **The merge or the fetch.** `origin/main` holds `✅`/`❌` for `T001` after the push and fetch (the
  `row T001 at main / origin/main` lines), and `autopilot status` sees it.
- **The lane branch.** The bug is the same with the branch kept and removed, and for a task closed
  in another clone with no task branch here (`T004`).
- **The dispatch grace.** `T001` was backdated past `claim_grace_minutes`; inside the grace a run
  member reads `dispatched` and is skipped for that reason only, and a task never in a run (`T004`)
  has no grace at all.
- **`done_on_mainline` / `discarded_on_mainline` themselves.** They report `T001` correctly after
  the merge (`status` reads `done-merged`/`discarded`); they are simply not consulted for candidates.
- **`autopilot merged`.** It fetches with `--prune` and reads `done_on_mainline`, but updating the
  local mainline is not its job (§12.8), and the bug exists without it (the reproduction never calls
  it).
- **Plain `taskrail next`, `show` and `claim`.** They offer and report `T001` as `pending` too, but by
  §7 they read the checkout's rows ("only local claims and local refs are consulted"), and the gap is
  self-limiting there: a workspace is created from `base.onto`, the further-ahead mainline, where the
  row is closed, so `claim` inside it refuses with exit 5. `autopilot next` is different because it
  launches a lane and records a dispatch before anyone claims (question 3).
- **Dependents.** `T004` in the test fixture depends on `T001`; while `T001` is closed only on
  `origin/main`, `blocked_by` still reads the checkout and keeps the dependent blocked. That is
  conservative, not a wrong dispatch, and unchanged by this fix.

## Affected areas

- `autopilot/dispatch.py` `next_lanes` — the candidate loop's skip reasons.
- `autopilot/status.py` `_on_mainline` — the rows read from the two mainline refs, and through it
  `done_on_mainline`, `discarded_on_mainline`, `task_state` (`done-merged`, `discarded`) and
  `merged._dependents` (which skips `done_on_mainline` dependents).
- Not changed: `query.py` (`eligible`, `state`), `stack.py`, `cli.py`, the hand-off (`_handoff`,
  `_done_time`, `WITH_BRANCH`), which belong to T065's touch map, and `merged.recorded_merges`.

## Proposed fix

1. **`autopilot/dispatch.py` `next_lanes`.** Warm `discarded_on_mainline(project)` next to
   `done_on_mainline(project)` before the lock, and make the first skip reason in the candidate loop
   a task that `task_state` would read as closed on the mainline:
   `done-merged on the mainline, not in this checkout` for `done_on_mainline`, and
   `discarded on the mainline, not in this checkout` for `discarded_on_mainline` (question 1). The
   task is reported in `skipped`, not dispatched, takes no lane, no resource value and no place in
   the run's count. `query.eligible` stays unchanged.
2. **`autopilot/status.py` `_on_mainline`.** When both mainline refs exist, a row read on one ref
   does not count when the other ref has a `Reopens: <ID>` commit that the first lacks — the rule §7
   applies to task-branch tips, applied between the two mainline refs. One
   `git log --format=%B --grep=^Reopens: <other> --not <ref>` per ref (two at most per backlog),
   parsed with `stack.REOPENS`, not one per task. `status` then reads a task reopened on the local
   mainline and not pushed as not closed, and `next` offers it (question 2).
3. **Regression tests** in `tests/test_autopilot_next.py`, `pilot` fixture:
   - `test_a_task_closed_on_the_remote_mainline_but_not_pulled_is_not_dispatched`, parametrized over
     `done` and `discard`: count 2, `T001` and `T002` dispatched, `T001` claimed with `--run`, closed
     and committed in its lane, pushed to `origin/main`, fetched, dispatch backdated 16 minutes;
     `status` reads `done-merged`/`discarded`; the preview and `next --run` do not dispatch `T001`
     and skip it with the reason above; after the lane worktree and local branch are removed, the
     preview still skips it; after `git merge --ff-only origin/main`, `T001` is no candidate at all.
   - `test_a_task_reopened_on_the_local_mainline_is_offered_while_the_remote_is_still_closed`: the
     same up to the pull, then `reopen T001` committed on `main` and not pushed; `status` no longer
     reads `done-merged` and the preview dispatches `T001`.
4. **Docs.** `DESIGN.md` §12.1 (`autopilot next` row) and §12.4 (`done-merged` and
   `discarded`), exact text in the gate report; one bullet under `## Unreleased` in
   `CHANGELOG.md`.

## Gate decisions

Recorded in [the autopilot decisions](../autopilot/decisions/T064-skip-a-task-merged-on-the-remote-mainlin.md):
the diagnosis and fix points 1–4 are approved; a task closed on the mainline is reported in `skipped`
with its reason; the reopen rule goes into `_on_mainline` in this fix; plain `next`, `show` and
`claim` are recorded only, with no follow-up; the `DESIGN.md` texts a–c and the CHANGELOG bullet are
approved as written.

## Fix

`src/taskrail/autopilot/dispatch.py` `next_lanes`: reads `done_on_mainline` and
`discarded_on_mainline` before the lock (both cached per project, one scan of the mainline refs), and
the candidate loop's first skip reason is `done-merged on the mainline, not in this checkout` or
`discarded on the mainline, not in this checkout`. The task is not dispatched, takes no lane, resource
value or place in the run's count, and its run record is not written.

`src/taskrail/autopilot/status.py` `_on_mainline`: when both mainline refs exist, a
closed row read on one ref is dropped for tasks that `_reopened_elsewhere` finds — IDs from
`git log --format=%B --grep=^Reopens: <other ref> --not <ref>`, parsed with `review.REOPENS` (one
`git log` per mainline ref per backlog). `done_on_mainline`, `discarded_on_mainline` and
`task_state` follow it.

Also: the approved `DESIGN.md` texts a–c (§12.1 `autopilot next` row; §12.4 `done-merged` and
`discarded`) and one bullet under `## Unreleased` in `CHANGELOG.md`. `query.py`,
`stack.py`, `cli.py` and T062's tests are unchanged.

## Verification

Regression tests in `tests/test_autopilot_next.py`, `pilot` fixture, with a `merge_without_pull`
helper (close in the lane, commit, push the branch to `origin/main`, fetch):

- `test_a_task_closed_on_the_remote_mainline_but_not_pulled_is_not_dispatched[done|discard]` — count
  6, five tasks dispatched, `T001` claimed with `--run`, closed, merged without a pull, dispatch
  backdated 16 minutes: `status` reads `done-merged`/`discarded` while `show` still reads `pending`;
  the preview and `next --run` dispatch nothing and skip `T001` with the reason, and the run's
  `dispatched` time for `T001` is unchanged; with the lane worktree and branch removed the preview
  still skips it; after `git merge --ff-only origin/main` it is neither dispatched nor skipped.
- `test_a_task_reopened_on_the_local_mainline_is_offered_while_the_remote_is_still_closed` — `T001`
  done, merged and pulled, then reopened and committed on `main` without a push: `status` reads
  `pending` and the preview dispatches it; after pushing the reopen and resetting the local `main`
  one commit back (the remote reopen not pulled), `status` still reads `pending`.

Run against the unfixed code (the tests written, `dispatch.py` and `status.py` untouched):

```text
$ uv run pytest -q -p no:cacheprovider --color=no tests/test_autopilot_next.py -k "remote_mainline or reopened_on_the_local_mainline"
FFF                                                                      [100%]
>       assert (ids(preview), skipped(preview).get("T001")) == ([], reason)
E       AssertionError: assert (['T001'], None) == ([], 'done-me...his checkout')
tests/test_autopilot_next.py:665: AssertionError
>       assert (ids(preview), skipped(preview).get("T001")) == ([], reason)
E       AssertionError: assert (['T001'], None) == ([], 'discard...his checkout')
tests/test_autopilot_next.py:665: AssertionError
>       assert row(pilot.root, capsys, run_id, "T001")["state"] == "pending"
E       AssertionError: assert 'done-merged' == 'pending'
tests/test_autopilot_next.py:691: AssertionError
FAILED tests/test_autopilot_next.py::test_a_task_closed_on_the_remote_mainline_but_not_pulled_is_not_dispatched[done-done-merged]
FAILED tests/test_autopilot_next.py::test_a_task_closed_on_the_remote_mainline_but_not_pulled_is_not_dispatched[discard-discarded]
FAILED tests/test_autopilot_next.py::test_a_task_reopened_on_the_local_mainline_is_offered_while_the_remote_is_still_closed
3 failed, 40 deselected in 2.85s
```

Each fails on the root cause: `status` reads `T001` closed and the preview still dispatches it, with no
skip; and a reopen on the local mainline still reads `done-merged` from `origin/main`.

After the fix:

```text
$ uv run pytest -q -p no:cacheprovider --color=no tests/test_autopilot_next.py -k "remote_mainline or reopened_on_the_local_mainline"
...                                                                      [100%]
3 passed, 40 deselected in 3.22s
$ taskrail checks T064 --stage fix
== test: uv run pytest -q
937 passed in 107.13s (0:01:47)
== lint: not configured
```

The reproduction script, re-run with the fixed code (changed lines):

```text
--- branch merged into origin/main, fetched, local main not pulled            (closing with `done`)
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T001", "reason": "done-merged on the mainline, not in this checkout"}, …]}
autopilot next --run 20260915-1: {"dispatch": [], "skipped": [{"id": "T001", "reason": "done-merged on the mainline, not in this checkout"}, …], "remaining": 1}
--- lane worktree and local branch removed (as `autopilot merged --cleanup` does)
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T001", "reason": "done-merged on the mainline, not in this checkout"}, …]}
--- reopened and committed on local main, not pushed (origin/main still closed)
autopilot status --run 20260915-1: {"T001": "pending", …}
autopilot next (preview): {"dispatch": ["T001"], …}
--- branch merged into origin/main, fetched, local main not pulled            (closing with `discard`)
autopilot next (preview): {"dispatch": [], "skipped": [{"id": "T001", "reason": "discarded on the mainline, not in this checkout"}, …]}
autopilot next --run 20260915-1: {"dispatch": [], "skipped": [{"id": "T001", "reason": "discarded on the mainline, not in this checkout"}, …], "remaining": 2}
--- reopened and committed on local main, not pushed (origin/main still closed)
autopilot status --run 20260915-1: {"T001": "pending", …}
autopilot next (preview): {"dispatch": ["T001"], …}
===== T004 closed from another clone, never in a run =====
autopilot next (preview): ["T001", "T002", "T003"]
```

Plain `taskrail next` and `show` still report `T001` as `pending` until the pull, as decided (§7).
