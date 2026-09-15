# T062 — Treat a task discarded on its unmerged branch as closed in status and next

Kind: bug · Epic: E02 · Status: fixed

Source: the impact stage of [T054](T054-keep-a-closing-lane-from-reading-as-pend.md) (its
*Affected areas* and *Impact*), decided in
[T054's autopilot decisions](../autopilot/decisions/T054-keep-a-closing-lane-from-reading-as-pend.md),
fix gate question 2. It extends the lane-state work that started from the findings of
[the T033 autopilot trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md).

## Symptom

A task is discarded on its own branch — `taskrail discard <ID>` in the task's worktree, committed
there — and the branch is not merged yet. Seen from the main checkout, the task still reads as open:

- `autopilot status` reports it `pending` (once its dispatch is older than
  `[git].claim_grace_minutes`), with no `touched` files, and the hand-off queue is empty;
- `autopilot next` offers it, and `autopilot next --run R` dispatches it again to a new lane and
  counts it against the run's count;
- plain `taskrail next` offers it, `show` reports `state: pending`, and `claim` from another
  checkout succeeds.

The same holds after the branch is merged into `<remote>/<mainline>` while the local mainline is not
pulled: `autopilot status` still says `pending`, where a `✅` merged the same way reads `done-merged`.

Expected: a discard committed on the task's branch is a closed task waiting to be merged, as a `✅`
there is (`done-branch`, §7 *Done on its branch*): neither `pending` nor offered by `next` or
`autopilot next`, and not claimable.

## Reproduction

A throwaway Python script outside the repository, run with this branch's CLI
(`uv run python <script>`). It builds a repository under a temporary
directory — a `TODO.md` with pending tasks `T001` (bug), `T002` (chore, depends on `T001`) and `T003`
(feature), `[autopilot] enabled = true`, `max_lanes = 10`, a bare `origin` — and calls
`taskrail.cli.main` in-process:

1. `autopilot start --count 2`, then `autopilot next --run <run>` dispatches `T001` and `T003`;
2. `git worktree add <lane> -b T001-first-bug origin/main`, then
   `--root <lane> claim T001 --owner lane --run <run>`;
3. `--root <lane> discard T001 --owner lane`, then `git commit -am "chore(T001): discard"` in the
   lane; prints the `T001` row at the branch and at `main`;
4. moves `T001`'s `dispatched` time in the run file 16 minutes into the past
   (`claim_grace_minutes` is 15), as a lane that stopped at a gate a while ago would be;
5. from the main checkout: `autopilot status --run <run>`, `autopilot next` (preview),
   `taskrail next`, `show T001`, `show T002`, `claim T001 --owner someone --local-only` (released
   again), and `autopilot next --run <run>`;
6. pushes the lane branch to `origin/main` (a merge), fetches without pulling the local `main`, and
   repeats the reads of step 5.

## Evidence

```text
$ uv run --directory /…/.worktrees/T062-treat-a-task-discarded-on-its-unmerged-b python /…/T062/repro.py
--- autopilot next --run 20260915-1 (exit 0): dispatch
["T001", "T003"]
--- claim T001 --run 20260915-1 in the lane (exit 0)
claimed T001 as lane
--- discard T001 in the lane worktree (exit 0)
T001 discarded
--- git log --oneline -1 in the lane worktree; git status --short
076ef5b chore(T001): discard
(clean)
--- T001's row at refs/heads/T001-first-bug and at main
| ❌ | T001 | bug     | 1   | —          | First bug   | —           |
| ⬜ | T001 | bug     | 1   | —          | First bug   | —           |
--- T001's dispatch moved 16 minutes into the past
--- autopilot status --run 20260915-1 after the discard is committed on the branch (exit 0)
T001: state=pending claim=False touched=[]
T003: state=dispatched claim=False touched=[]
handoff={"mode": "sequential", "in_review": null, "queue": [], "next": null}
--- autopilot next (preview) after the discard is committed on the branch (exit 0)
{"dispatch": ["T001"], "skipped": [{"id": "T003", "reason": "dispatched in run 20260915-1"}]}
--- taskrail next after the discard is committed on the branch (exit 0)
["T001", "T003"]
--- show T001 after the discard is committed on the branch (exit 0)
{"status": "pending", "state": "pending", "blocked_by": [], "base.onto": "origin/main"}
--- show T002 after the discard is committed on the branch (exit 0)
{"status": "pending", "state": "blocked", "blocked_by": ["T001"], "base.onto": "origin/main"}
--- claim T001 from the main checkout (exit 0)
claimed T001 as someone
--- autopilot next --run 20260915-1 after the discard is committed on the branch (exit 0)
{"dispatch": ["T001"], "skipped": [], "remaining": 0}
--- autopilot status --run 20260915-1 after the branch is merged into origin/main (local main not pulled) (exit 0)
T001: state=pending claim=False touched=[]
T003: state=dispatched claim=False touched=[]
handoff={"mode": "sequential", "in_review": null, "queue": [], "next": null}
--- autopilot next (preview) after the branch is merged into origin/main (local main not pulled) (exit 0)
{"dispatch": ["T001"], "skipped": [{"id": "T003", "reason": "dispatched in run 20260915-1"}]}
--- taskrail next after the branch is merged into origin/main (local main not pulled) (exit 0)
["T001", "T003"]
--- show T001 after the branch is merged into origin/main (local main not pulled) (exit 0)
{"status": "pending", "state": "pending", "blocked_by": [], "base.onto": "origin/main"}
--- show T002 after the branch is merged into origin/main (local main not pulled) (exit 0)
{"status": "pending", "state": "blocked", "blocked_by": ["T001"], "base.onto": "origin/main"}
```

The branch tip holds `❌` and the lane is clean, yet every reader from the main checkout reports
`T001` as `pending`; `autopilot next --run` dispatched it again and took the run's last slot for it
(`remaining: 0`). With the dispatch still inside the grace (a first run of the same script without
step 4), `status` read `dispatched` and `next` skipped it only for that reason.

## Root cause

Every reader decides "closed" from two sources, and neither sees a committed `❌` on a task branch:

1. **The checkout's own row** (`task.status`), which is `⬜` until the branch is merged and pulled.
2. **`stack.done_on_branch`** (`src/taskrail/stack.py`), the only reader of task
   branch tips, which keeps a tip only when the row there is `✅`:

   ```python
   done = tuple(
       _short(ref)
       for ref in refs
       if statuses[ref].get(task_id) == Status.DONE.value and not _reopened_since(...)
   )
   ```

   `_find` already reads the row at every task-branch tip (`_read_statuses`, one
   `git cat-file --batch`) and has the `❌` in hand; it discards it.

Consequences, reader by reader:

- `query.state` returns `done-branch` only for `done_on_branch`, so the task falls through to
  `pending` (or `claimed`); `next`/`eligible` offer it, and `show` reports it.
- `cli.cmd_claim` refuses only `task.status` not pending or `done_on_branch`, so it claims it.
- `autopilot.status.task_state` checks `done_on_mainline` (`✅` on a mainline ref), the checkout's
  `❌`, `done_on_branch`, the recorded states, the claim, `_closing` and the dispatch — so it falls
  through to `pending`. `done_on_mainline` counts only `✅`, which is why a `❌` merged into
  `<remote>/<mainline>` but not pulled stays `pending` too, and `_closing` (T054) looks only for an
  uncommitted `✅`, so the moment between `discard` and its commit reads `pending` in the same way.
- `autopilot.dispatch.next_lanes` takes its candidates from `query.eligible` and its lane states
  from `task_state`, so the task is both a candidate and, being `pending`, not counted toward the
  run's count — it is dispatched again.

## Ruled out

- **`discard` itself.** Exit 0; the lane's tree is clean after the commit, and the branch tip holds
  `| ❌ | T001 |` while `main` holds `⬜`. Releasing the claim on discard is the documented contract
  (§6 write rules).
- **Branch resolution (`branches.task_branch`).** `show T001` resolves `T001-first-bug`, the branch
  the lane created, and `done_on_branch` reads the same candidate refs; with `done` in place of
  `discard`, the same flow reads `done-branch` (T054's regression test
  `test_a_lane_between_done_and_its_commit_is_running_and_not_dispatched_again` ends there).
- **`_reopened_since`.** No `Reopens:` commit exists in the reproduction; the tip is dropped before
  that check, by the `✅` comparison.
- **The dispatch grace (`dispatch_live`).** Inside the grace the task read `dispatched` and was
  skipped; the grace only hides the bug for 15 minutes, as T054 found for its window.
- **`autopilot next`'s skip checks.** They run over the candidates `query.eligible` already chose;
  the task should not be a candidate at all, so no skip reason is missing.
- **`blocked_by` for dependents.** `T002` is `blocked` by `T001`, which is right both before and
  after the fix: a discarded dependency is not `done`, so it keeps blocking (§7 *Dependencies and
  the base*), and `unmerged_dependencies` must not stack a dependent on a discarded branch.

## Affected areas

- `stack.py` `_find` / `done_on_branch` — the tip reader.
- `query.py` `state`, `STATES` — `list`, `show`, `next`, `list --state`.
- `cli.py` `cmd_claim` (and `cmd_edit`, which refuses `done-branch` the same way).
- `autopilot/status.py` `task_state`, `done_on_mainline`, `_closing`, `STATES`.
- `autopilot/dispatch.py` `next_lanes` — affected only through `query.eligible` and `task_state`;
  no change needed there (see *Proposed fix*).
- Not in this fix: the hand-off of a discarded branch (the queue, `autopilot lane --state
  handed-off`, the `touched` files and escalation flags of a moved-on task) — see *Proposed fix*,
  point 6.

## Proposed fix

1. **`stack.py`.** `_find` keeps, in the same scan, the tips where the row is `❌`, under the same
   rules as `✅`: the local branch or `<remote>/<branch>`, not closed (`✅` or `❌`) on either
   mainline ref, and not older than a `Reopens: <ID>` commit on a mainline ref. A task with a `✅`
   tip stays `done-branch` only. New `discarded_on_branch(project) -> dict[str, DoneOnBranch]`,
   cached next to `done_on_branch`. `done_on_branch`'s result is unchanged.
2. **`query.py`.** New state `discarded-branch`, after `done-branch` in `STATES` and in `state`:
   `next` never offers it, `show` and `list` report it, `list --state discarded-branch` filters it.
   `blocked_by`, `unmerged_dependencies` and `base_dict` are unchanged, so dependents stay blocked
   and are never stacked on it.
3. **`cli.py`.** `cmd_claim` refuses a `discarded-branch` task with exit 5, as it refuses
   `done-branch` (`<ID> is discarded on branch <refs>, not yet merged into <mainline>`), and
   `cmd_edit` refuses it without `--force`, as it refuses `done-branch` (questions 2 and 3).
4. **`autopilot/status.py`.**
   - `task_state` returns `discarded-branch` after `handed-off`/`done-branch` and before the
     recorded states; it is not in `WITH_BRANCH`, so it reports no `touched` files and raises no
     escalation flag. New `discarded-branch` in `STATES`.
   - `task_state` returns `discarded` also when the row is `❌` on the local mainline or
     `<remote>/<mainline>`: `done_on_mainline`'s scan of the mainline refs is shared, cached, with
     a sibling `discarded_on_mainline` (question 4).
   - `_closing` also matches an uncommitted `❌`, so the moment between `discard` and its commit
     reads `running`, as T054 made it for `done` (question 5).
5. **`autopilot/dispatch.py`: no change.** The task leaves `query.eligible`, so it is no longer a
   candidate. `discarded-branch` is neither in `OCCUPYING` (it uses no lane) nor in `COUNTED` (it
   frees its place in the run's count, as `discarded` does in §12.7).
6. **Hand-off queue: not queued by this fix.** `_handoff` (whose ordering T053 rewrites on its
   unmerged branch, with `_done_time` reading the `✅` commit from `done_on_branch`) keeps queuing
   only `done-branch` rows, and `autopilot lane --state handed-off` keeps refusing anything but
   `done-branch`. A `discarded-branch` row carries its `branch`, so the orchestrator sees that the
   branch still has to be merged; queuing it — with a discard-commit time in `_done_time`, a
   `handed-off` that accepts it, and `touched` plus `MOVED_ON` for its close review — is a
   follow-up task once T053 is merged (question 6).
7. **Regression tests.**
   - `tests/test_autopilot_next.py`, `pilot` fixture: dispatch, claim with `--run`, `discard` in the
     lane and commit, backdate the dispatch; assert `autopilot status` reports `discarded-branch`,
     `autopilot next --run` does not dispatch it (and counts it free), and plain `next` does not
     offer it; after pushing the branch to `origin/main` without pulling, `status` reports
     `discarded`. A second test: `discard` without a commit reads `running`.
   - A plain-CLI test next to the `done-branch` tests (`tests/test_stacked_base.py`): `show` reports
     `discarded-branch`, `next` omits it, `claim` exits 5, a dependent stays `blocked`, and a tip
     older than a `Reopens:` commit on the mainline does not count.
8. **Docs.** `DESIGN.md` §7 (state list, a *Discarded on its branch* paragraph, the `next` row),
   §12.1 `autopilot status` row, §12.4 and §12.7 (exact text at the gate), and one bullet under
   `## Unreleased` in `CHANGELOG.md`.

## Gate decisions

Recorded in [the autopilot decisions](../autopilot/decisions/T062-treat-a-task-discarded-on-its-unmerged-b.md):
the diagnosis and fix points 1–8 with the new `discarded-branch` state are approved; `claim` refuses
it with exit 5 and `edit` without `--force`; `❌` on either mainline ref reads `discarded` in
`autopilot status`; `_closing` also matches an uncommitted `❌`; the hand-off stays out, with a
follow-up feature once T053 is merged; the `DESIGN.md` texts a–h are approved as proposed.

## Fix

`src/taskrail/stack.py`:

- `_find` returns two maps from the same scan: `done` as before, and `discarded`, the tasks with a
  `❌` tip that are not in `done` (a `✅` tip wins) and whose row is closed (`✅` or `❌`) on neither
  mainline ref. Both use the same tip rule — the local branch or `<remote>/<branch>`, and not older
  than a `Reopens: <ID>` commit on a mainline ref — through a local `tips` helper.
- `done_on_branch` returns the first map, unchanged; the new `discarded_on_branch` returns the
  second. Both share the one cache entry (`CACHE_KEY`), which `_fetch_records` still clears.

`src/taskrail/query.py`: `discarded-branch` joins `STATES` after `done-branch` (so
`list --state discarded-branch` accepts it), and `state` returns it after `done-branch`.

`src/taskrail/cli.py`: `cmd_claim` refuses a `discarded-branch` task with exit 5 —
`<ID> is discarded on branch <refs>, not yet merged into <mainline>` — right after the `done-branch`
refusal; `cmd_edit` refuses it without `--force` — `<ID> is discarded on branch <refs>; pass --force
to edit it anyway`.

`src/taskrail/autopilot/status.py`:

- `_on_mainline(project, status)` reads the mainline refs once per project (cached as
  `autopilot_closed_on_mainline`) and keeps both the `✅` and the `❌` rows, falling back to the
  checkout's rows outside git as before. `done_on_mainline` is built on it, still adding
  `recorded_merges`; the new `discarded_on_mainline` returns the `❌` rows.
- `task_state` returns `discarded` for `❌` in the checkout or on a mainline ref, and
  `discarded-branch` right after `handed-off`/`done-branch`, before the recorded states. It is not
  in `WITH_BRANCH`, so it has no `touched` files and no escalation flag; `STATES` lists it.
- `_closing` matches an uncommitted `✅` or `❌`.

`autopilot/dispatch.py` is unchanged: the task is no longer in `query.eligible`, and
`discarded-branch` is in neither `OCCUPYING` nor `COUNTED`. `_handoff` is unchanged, so the hand-off
queue still holds only `done-branch` rows.

Also: the approved `DESIGN.md` texts a–h (§7 state list, *Discarded on its branch*, the `next` row;
§12.1 `autopilot status` row; §12.4 `running`, `discarded-branch` and `discarded`; §12.7 twice) and
one bullet under `## Unreleased` in `CHANGELOG.md`.

## Verification

Regression tests:

- `tests/test_stacked_base.py`, `lanes` fixture, with a `discard_on_branch` helper (claim, discard,
  commit in the task's worktree):
  - `test_a_task_discarded_on_its_branch_is_discarded_branch_and_never_offered` — `show` reports
    `status: pending`, `state: discarded-branch`; `next` offers only `T003`;
    `list --state discarded-branch` lists `T001`; `claim` exits 5 naming the branch; dependent
    `T002` stays `blocked` by `T001` with no stacked `dependency`.
  - `test_a_discard_only_on_the_remote_branch_is_discarded_branch` — pushed, local branch and
    worktree removed: `discarded-branch`, `refs == ("origin/T001-base-task",)`, not in
    `done_on_branch`.
  - `test_a_done_tip_wins_over_a_discarded_one` — `origin` keeps the `❌`, the local tip is `✅`:
    `done-branch`, not in `discarded_on_branch`.
  - `test_a_discard_older_than_a_reopen_on_the_mainline_does_not_count` — the discard merged on
    `main` and reopened there: `pending` and offered again (a guard: it passes before the fix too).
- `tests/test_edit.py::test_a_task_discarded_on_its_branch_is_refused_unless_forced` — exit 5 with
  `T003 is discarded on branch T003-rounding-error`, then `--force` edits it.
- `tests/test_autopilot_next.py`, `pilot` fixture:
  - `test_a_task_discarded_on_its_unmerged_branch_is_closed_and_not_dispatched_again` — count 2,
    `T001` and `T002` dispatched, `T001` claimed with `--run`, discarded and committed, dispatch
    backdated 16 minutes: `status` reports `discarded-branch`, `claim` null, its branch, no
    `touched`, an empty hand-off queue; plain `next` omits `T001`; `next --run` does not skip it
    (it is no candidate) and dispatches `T003` into the place it freed (`remaining: 0`). After the
    branch is pushed to `origin/main` without pulling, `status` reports `discarded`.
  - `test_a_lane_between_discard_and_its_commit_is_running` — `discard` without a commit: `running`,
    `claim` null, `touched == ["TODO.md"]`; after the commit, `discarded-branch`.

Run against the unfixed code — the final test files copied into a temporary detached worktree at
`6258c5b` (the diagnosis commit), removed afterwards:

```text
$ uv run --directory /…/T062/unfixed pytest -q -p no:cacheprovider --color=no tests/test_stacked_base.py tests/test_edit.py tests/test_autopilot_next.py -k "discard"
FFF..FFF                                                                 [100%]
>       assert (shown["status"], shown["state"]) == ("pending", "discarded-branch")
E       AssertionError: assert ('pending', 'pending') == ('pending', '...arded-branch')
tests/test_stacked_base.py:409: AssertionError
>       assert data(lanes.root, "show", "T001", capsys=capsys)["state"] == "discarded-branch"
E       AssertionError: assert 'pending' == 'discarded-branch'
tests/test_stacked_base.py:425: AssertionError
>       assert "T001" not in stack.discarded_on_branch(project)
E       AttributeError: module 'taskrail.stack' has no attribute 'discarded_on_branch'
tests/test_stacked_base.py:440: AttributeError
>       assert "T003 is discarded on branch T003-rounding-error" in refused(git_repo, "T003", "--description", "X", code=5, capsys=capsys)
tests/test_edit.py:325:
>       assert (result, out) == (code, ""), err
E       assert (0, 'T003 des...by one → X\n') == (5, '')
tests/test_edit.py:51: AssertionError
>       assert (lane["state"], lane["claim"], lane["branch"], lane["touched"]) == ("discarded-branch", None, branch, [])
E       AssertionError: assert ('pending', N...first-ui', []) == ('discarded-b...first-ui', [])
tests/test_autopilot_next.py:611: AssertionError
>       assert (lane["state"], lane["claim"], lane["touched"]) == ("running", None, ["TODO.md"])
E       AssertionError: assert ('pending', None, []) == ('running', None, ['TODO.md'])
tests/test_autopilot_next.py:633: AssertionError
FAILED tests/test_stacked_base.py::test_a_task_discarded_on_its_branch_is_discarded_branch_and_never_offered
FAILED tests/test_stacked_base.py::test_a_discard_only_on_the_remote_branch_is_discarded_branch
FAILED tests/test_stacked_base.py::test_a_done_tip_wins_over_a_discarded_one
FAILED tests/test_edit.py::test_a_task_discarded_on_its_branch_is_refused_unless_forced
FAILED tests/test_autopilot_next.py::test_a_task_discarded_on_its_unmerged_branch_is_closed_and_not_dispatched_again
FAILED tests/test_autopilot_next.py::test_a_lane_between_discard_and_its_commit_is_running
6 failed, 2 passed, 105 deselected in 2.68s
```

Each fails on the root cause: the committed `❌` reads `pending` (plain and autopilot), `edit` goes
through (exit 0), the uncommitted `❌` reads `pending` with no `touched`, and the reader
`discarded_on_branch` does not exist. The two passes are the existing
`test_a_closed_task_is_refused_unless_forced[discard]` and the reopen guard above. The mainline part
of the autopilot test is not reached on the unfixed code; the reproduction's last block shows it
reading `pending` there.

After the fix:

```text
$ uv run pytest -q -p no:cacheprovider --color=no tests/test_stacked_base.py tests/test_edit.py tests/test_autopilot_next.py -k "discard"
........                                                                 [100%]
8 passed, 105 deselected in 2.61s
$ uv run pytest -q
849 passed in 87.45s (0:01:27)
```

The `lint` check the `fix` stage names is not configured in this repository's `[checks]`.

The reproduction script, re-run with the fixed CLI (changed lines):

```text
--- autopilot status --run 20260915-1 after the discard is committed on the branch (exit 0)
T001: state=discarded-branch claim=False touched=[]
--- autopilot next (preview) after the discard is committed on the branch (exit 0)
{"dispatch": [], "skipped": [{"id": "T003", "reason": "dispatched in run 20260915-1"}]}
--- taskrail next after the discard is committed on the branch (exit 0)
["T003"]
--- show T001 after the discard is committed on the branch (exit 0)
{"status": "pending", "state": "discarded-branch", "blocked_by": [], "base.onto": "origin/main"}
--- claim T001 from the main checkout (exit 5)
taskrail: T001 is discarded on branch T001-first-bug, not yet merged into main
--- autopilot next --run 20260915-1 after the discard is committed on the branch (exit 0)
{"dispatch": [], "skipped": [{"id": "T003", "reason": "dispatched in run 20260915-1"}], "remaining": 1}
--- autopilot status --run 20260915-1 after the branch is merged into origin/main (local main not pulled) (exit 0)
T001: state=discarded claim=False touched=[]
--- autopilot next (preview) after the branch is merged into origin/main (local main not pulled) (exit 0)
{"dispatch": ["T001"], "skipped": [{"id": "T003", "reason": "dispatched in run 20260915-1"}]}
--- taskrail next after the branch is merged into origin/main (local main not pulled) (exit 0)
["T001", "T003"]
```

**Found on the way, not fixed here.** After a merge into `<remote>/<mainline>` that the local
mainline has not pulled, `autopilot next` still offers the task, for a `✅` as much as for a `❌`.
`autopilot status` reports `done-merged` or `discarded`, but `next_lanes` takes its candidates from
`query.eligible`, which by §7 reads merged rows only from the checkout, and none of its skip checks
looks at `done-merged` or `discarded`. A throwaway probe (`closing` = `done` or `discard`, dispatch,
claim with `--run`, close and commit in the lane, push the branch to `origin/main`, fetch, backdate
the dispatch):

```text
unfixed code
PROBE done {'status': 'done-merged', 'show': 'pending', 'preview': ['T001']}
PROBE discard {'status': 'pending', 'show': 'pending', 'preview': ['T001']}
fixed code
PROBE done {'status': 'done-merged', 'show': 'pending', 'preview': ['T001']}
PROBE discard {'status': 'discarded', 'show': 'pending', 'preview': ['T001']}
```

The `✅` case is on `main` today, before this fix; it is proposed as a follow-up at the gate.

## Impact

- **T064** (bug, E02) — *Skip a task merged on the remote mainline but not pulled in autopilot
  next*: `autopilot next` offers a task whose `✅` or `❌` is on the remote mainline but not in the
  checkout, because its candidates come from `query.eligible`. To be verified by a pytest that closes
  a task on its branch with `done` and with `discard`, pushes it to `origin/main` without pulling,
  and asserts `autopilot next` does not offer it.
- **T065** (feature, E02, depends on T053) — *Hand off a branch whose task was discarded on it*:
  `autopilot status` leaves `discarded-branch` out of the hand-off queue and `autopilot lane --state
  handed-off` refuses it; queue it by its discard commit, accept `handed-off`, and report its
  `touched` files without a `governing` flag. To be verified by a pytest that discards on a branch
  and hands it off.
