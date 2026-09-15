# T054 — Keep a closing lane from reading as pending between done and its commit

Kind: bug · Epic: E02 · Status: fixed

Source: finding F13 of [the T033 autopilot trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md).

## Symptom

An autopilot lane closes its task with `taskrail done <ID>` in its worktree and commits that change
on its own a moment later. In between, `done` has already released the claim, but the `✅` exists
only in the lane's working tree. During that window:

- `autopilot status` reports the task as `pending` (not `running`), with `claim: null` and an empty
  `touched` list — T033 saw exactly this for T002 at 14:39:22Z;
- when the lane's dispatch is older than `[git].claim_grace_minutes`, `autopilot next --run R`
  dispatches the same task again to a new lane, and counts it against the run's count;
- plain `taskrail next` also offers it.

Expected: the lane is still working (it has a commit, `review` and `validate` left), so `status`
keeps it `running` with its `touched` files, and `next` does not dispatch it again. After the commit
it becomes `done-branch`, as today.

## Reproduction

A throwaway Python script outside the repository, run with this branch's CLI
(`uv run python <script>`). It builds a repository under a temporary
directory — a `TODO.md` with one pending task `T001` (bug), `[autopilot] enabled = true`,
`max_lanes = 10`, a bare `origin` — and calls `taskrail.cli.main` in-process:

1. `autopilot start --count 1`, then `autopilot next --run <run>` dispatches `T001`;
2. `git worktree add <lane> -b T001-first origin/main`, then `--root <lane> claim T001 --owner lane --run <run>`;
3. moves the lane's `dispatched` time in the run file 16 minutes into the past
   (`claim_grace_minutes` is 15), as the trial's lane was;
4. `autopilot status --run <run>` while claimed;
5. `--root <lane> done T001 --owner lane`, **without committing**; `git status --short` in the lane;
6. `autopilot status --run <run>`, `autopilot next --run <run>` and `taskrail next` from the main checkout;
7. commits the lane's change and runs `autopilot status` again.

## Evidence

```text
$ uv run --directory /…/.worktrees/T054-keep-a-closing-lane-from-reading-as-pend python /…/T054/repro.py
--- autopilot next --run 20260914-1 (exit 0): dispatch
["T001"]
--- claim T001 --run 20260914-1 (exit 0)
claimed T001 as lane
--- autopilot status while claimed
exit 0: state=running claim=True touched=[]
--- done T001 in the lane worktree, not committed (exit 0)
T001 done
--- git status --short in the lane worktree
M TODO.md
--- autopilot status between done and its commit
exit 0: state=pending claim=False touched=[]
--- autopilot next --run 20260914-1 between done and its commit (exit 0)
{"dispatch": ["T001"], "skipped": [], "remaining": 0}
--- taskrail next between done and its commit (exit 0)
["T001"]
--- autopilot status after the commit
exit 0: state=done-branch claim=False touched=['TODO.md']
```

The second `autopilot next` dispatched `T001` again while its first lane was still closing, and
took the run's only remaining slot for it (`remaining: 0`).

## Root cause

`autopilot.status.task_state` (`src/taskrail/autopilot/status.py`) derives a lane's
state from committed git refs, the claim and the run file only:

```python
if task.id in stack.done_on_branch(project):   # ✅ at the task branch *tip* (committed)
    return "handed-off" if ... else "done-branch"
...
if claim is not None:
    return "running"
if lane and runs_module.dispatch_live(lane, project.config.claim_grace_minutes, now):
    return "dispatched"
return "pending"
```

`taskrail done` writes the `✅` to the working tree and releases the claim in the same command
(`_change_status` in `cli.py`, as §6 specifies), and the commit comes afterwards. Between the two,
none of the inputs above says the lane is alive: the tip still has `⬜`, the claim is gone, and the
dispatch has expired — so the precedence falls through to `pending`. Nothing in `task_state` looks
at the one place the `✅` already is: the working tree of the worktree that has the task branch
checked out.

`autopilot next` reuses `task_state`, so the task is not in its `occupied` lanes, and its candidate
list (`query.eligible`) contains it because it is unclaimed and not `done-branch`. Its skip checks
cover only `failed` in the run and `dispatched` in any run, so it is dispatched again. `touched` is
empty for the same reason: `_lane_details` collects it only for states in `WITH_BRANCH`, which does
not include `pending`.

## Ruled out

- **`done` itself.** Exit 0, the lane's `TODO.md` is modified (`M TODO.md`), and releasing the claim
  at `done` is the documented contract (§6, *Close* in the core skill). Keeping the claim until the
  commit would need a new command or a hook and change every non-autopilot user.
- **Run membership.** The task stays a member of the run after the release — `claim --run` lists it
  in the run file — so the row is still reported; only its state is wrong.
- **`stack.done_on_branch`.** It reads committed refs by design (§7); right after the commit it
  reports `done-branch` (last line of the evidence). Reading working trees there would make an
  uncommitted `✅` `done-branch`, which would put an uncommitted branch in the hand-off queue.
- **Dispatch expiry (`dispatch_live`).** It works as T030 specified. With a dispatch younger than
  the grace the window reads `dispatched` instead and `next` skips it, which is why the trial saw
  the re-dispatch risk only for a lane older than the grace.
- **A recorded lane state.** Only `failed`, `escalated` and `gate` are recorded states that take
  precedence; a closing lane was resumed from its last gate with `lane --state running`, which is not
  one of them, so the recorded state cannot hide the window.
- **Stale claims.** The claim is not stale; it no longer exists.

## Affected areas

- `autopilot/status.py` `task_state` — `autopilot status`'s state, `touched`, `idle_minutes` and
  escalation flags for the lane.
- `autopilot/dispatch.py` `next_lanes` — lane occupancy, resource release, the run's count, and the
  skip check.
- Plain `taskrail next`, `show` and `claim` (`query.state`) show the same task as `pending` in that
  window. Outside the autopilot the person who ran `done` is the one who commits, seconds later, so
  this proposal leaves them unchanged (question 3 at the gate).
- Not affected: a committed discard (`❌`) on a task branch is also invisible to `status` and `next`
  until merged, because `done-branch` counts only `✅`; that is a different, lasting state rather than
  this window, and is noted here only for the impact stage.

## Proposed fix

1. **`status.py`.** Add `_closing(task, project) -> bool`: the worktree that has the task's branch
   (`branches.task_branch`) checked out — from `gitutil.worktree_branches`, read once and cached in
   `project.cache` — holds the task's row as `✅` in its working-tree copy of `task.file`, parsed
   with the same `stack._statuses` helper the ref reader uses. In `task_state`, return `running`
   when `claim is not None or _closing(task, project)`. The precedence is unchanged: committed
   `done-branch` and the recorded `gate`/`escalated`/`failed` still come first, and `dispatched`
   and `pending` after. Because `running` is in `WITH_BRANCH`, `touched` and `idle_minutes` come
   back for the window with no further change. The check self-heals: if the lane abandons the
   change, the `✅` disappears and the task is `pending` again.
2. **`dispatch.py`.** Generalize the `dispatched in run R` skip to any state that occupies a lane
   (`OCCUPYING`: `dispatched`, `running`, `gate`, `escalated`), with reason `<state> in run R`, so a
   candidate that is unclaimed but still occupying a lane is not dispatched again. The existing
   `dispatched in run R` text is unchanged.
3. **Regression tests** in `tests/test_autopilot_next.py` with the `pilot` fixture: claim with
   `--run`, backdate the dispatch past the grace, run `done` in the lane without committing, then
   assert `autopilot status` reports `running` with `TODO.md` in `touched`, `autopilot next --run`
   dispatches nothing new and skips the task as `running in run R`; after the commit it is
   `done-branch`.
4. **Docs.** `DESIGN.md` §12.4 and the §12.1 `autopilot status` and `autopilot next` rows (exact text
   at the gate), and one bullet under `## Unreleased` in `CHANGELOG.md`.

## Gate decisions

Recorded in [the autopilot decisions](../autopilot/decisions/T054-keep-a-closing-lane-from-reading-as-pend.md):
the diagnosis and fix 1–4 are approved; the `DESIGN.md` §12.4 `running` bullet and the two §12.1
phrases are approved as proposed; plain `next`, `show` and `claim` stay unchanged; the skip covers
every lane-occupying state.

## Fix

`src/taskrail/autopilot/status.py`:

- `_closing(task, project)` resolves the task's branch with `branches.task_branch`, looks it up in
  `gitutil.worktree_branches` (read once per project, cached as `autopilot_worktree_branches`), reads
  that worktree's copy of `task.file`, and returns whether `stack._statuses` finds the row `✅`. A
  task without a branch, a branch not checked out, or an unreadable file returns false.
- `task_state` returns `running` when `claim is not None or _closing(task, project)`. `_closing`
  runs only after the committed `done-merged`, `discarded`, `done-branch` and recorded
  `failed`/`escalated`/`gate` checks, and only for a task without a claim.

`src/taskrail/autopilot/dispatch.py`: the candidate skip `dispatched_in` becomes
`occupying_in`, any run in which the task is in an `OCCUPYING` state (`running`, `gate`,
`escalated`, `dispatched`), with reason `<state> in run R`. The `failed in run R` skip still comes
first, and `dispatched in run R` reads as before.

Also: the three approved phrases in `DESIGN.md` (§12.1 `autopilot next` and
`autopilot status` rows, §12.4 `running`), and one bullet under `## Unreleased` in
`CHANGELOG.md`.

## Verification

Regression tests in `tests/test_autopilot_next.py`, with the `pilot` fixture:

- `test_a_lane_between_done_and_its_commit_is_running_and_not_dispatched_again` — `max_lanes = 1`,
  T001 dispatched, claimed with `--run`, dispatch backdated 16 minutes, `done` in the lane without
  a commit: `status` reports `running`, `claim` null, `touched == ["TODO.md"]`; with
  `max_lanes = 2`, `next --run` skips T001 as `running in run R`, dispatches only T002, and lists
  T001 among the occupied lanes; after the commit T001 is `done-branch`.
- `test_a_lane_at_a_gate_without_a_claim_is_not_dispatched_again` — T001 claimed with `--run`,
  recorded `gate`, claim released: `next --run` skips it as `gate in run R` and dispatches T002
  and T003.

Run against the unfixed code:

```text
$ uv run pytest -q -p no:cacheprovider --color=no tests/test_autopilot_next.py -k "between_done or without_a_claim"
FF                                                                       [100%]
>       assert (lane["state"], lane["claim"], lane["touched"]) == ("running", None, ["TODO.md"])
E       AssertionError: assert ('pending', None, []) == ('running', None, ['TODO.md'])
tests/test_autopilot_next.py:579: AssertionError
>       assert skipped(result)["T001"] == f"gate in run {run_id}"
E       KeyError: 'T001'
tests/test_autopilot_next.py:597: KeyError
FAILED tests/test_autopilot_next.py::test_a_lane_between_done_and_its_commit_is_running_and_not_dispatched_again
FAILED tests/test_autopilot_next.py::test_a_lane_at_a_gate_without_a_claim_is_not_dispatched_again
2 failed, 36 deselected in 1.94s
```

The first fails on the root cause: `pending` with no `touched` between `done` and its commit. The
second fails because the unclaimed `gate` lane was dispatched again instead of skipped.

After the fix:

```text
$ uv run pytest -q -p no:cacheprovider --color=no tests/test_autopilot_next.py -k "between_done or without_a_claim"
2 passed, 36 deselected in 1.01s
$ uv run pytest -q
830 passed in 107.95s (0:01:47)
```

The `lint` check the `fix` stage names is not configured in this repository's `[checks]`.

The reproduction script from *Reproduction*, re-run with the fixed CLI:

```text
--- autopilot status between done and its commit
exit 0: state=running claim=False touched=['TODO.md']
--- autopilot next --run 20260914-1 between done and its commit (exit 0)
{"dispatch": [], "skipped": [], "remaining": 0}
--- taskrail next between done and its commit (exit 0)
["T001"]
--- autopilot status after the commit
exit 0: state=done-branch claim=False touched=['TODO.md']
```

`remaining: 0` now counts the closing lane toward the run's count of 1, so nothing is dispatched;
plain `taskrail next` still offers T001, as decided.

## Impact

- **T062** (bug, E02) — *Treat a task discarded on its unmerged branch as closed in status and
  next*: a `❌` committed on a task branch reads as `pending` to `autopilot status`, `autopilot next`
  and `next` until merged, because `done-branch` counts only `✅`. To be verified by a pytest that
  discards on a branch, commits, and asserts the task is neither `pending` nor offered.
- Plain `next`, `show` and `claim` keep reading the window between `done` and its commit as
  `pending`, by decision; no task.
