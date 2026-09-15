# T053 — Order the autopilot hand-off queue by completion, not branch tip time

Kind: bug · Epic: E02 · Status: fixed · Source: T033 finding F8

## Symptom

`taskrail autopilot status` orders `handoff.queue` — and so names `handoff.next` — by the commit
time of each waiting branch's tip. Any commit that lands on a finished branch after `taskrail done`
moves that task to the back of the queue, although it finished no later than before:

- the orchestrator's rebase of the branch it is about to hand off (`git rebase` rewrites every
  commit's committer date), so `next` switches to another task in the middle of that hand-off;
- a decision-record commit the orchestrator adds on a lane's branch while it is stopped.

In the T033 trial `next` went T001 → T004 during T001's rebase and T004 → T002 during T004's rebase.

Expected (DESIGN.md §12.8): "dependencies first, then in completion order". A task's place in the
queue is fixed when it is marked done on its branch, and rebases or later commits do not change it.

## Reproduction

A throwaway repository under a temporary directory with a bare `origin`, running the CLI from this
branch (`uv run taskrail --root <repo> …`). Commit times are pinned with
`GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`, as the orchestrator's real commits would simply be later.
The script, kept outside the repository and deleted afterwards together with the directory:

```sh
#!/bin/sh
# Reproduction for T053: handoff.next follows the branch tip's commit time.
set -eu
SRC=<this worktree>
BASE=$(mktemp -d)
REPO=$BASE/repo
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com
tr() { uv run --quiet --project "$SRC" taskrail "$@"; }
at() { d=$1; shift; GIT_AUTHOR_DATE=$d GIT_COMMITTER_DATE=$d "$@"; }
queue() {
  echo "\$ taskrail --root repo autopilot status --run $RUN --json  (handoff; tip commit times)"
  tr --root "$REPO" autopilot status --run "$RUN" --json | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["runs"][0]["handoff"]))'
  for b in T003-independent T004-another-one; do
    echo "  $b tip: $(git -C "$REPO" log -1 --format='author %aI  committer %cI  %s' "$b")"
  done
}

mkdir -p "$REPO"
git -C "$REPO" init -q -b main
mkdir -p "$REPO/.taskrail"
printf '%s\n' 'version = "v0.1.0"' '' '[[backlog]]' 'name = "main"' 'prefix = "T"' 'file = "TODO.md"' '' '[columns]' 'custom = []' '' '[autopilot]' 'enabled = true' > "$REPO/.taskrail/config.toml"
printf '%s\n' '# TODO' '' '## Epics' '' '| ID  | Epic | Objective | File |' '|-----|------|-----------|------|' '| E01 | Demo | Try lanes | —    |' '' '## E01 — Demo' '' \
  '| ✓  | ID   | Kind    | Pts | Depends On | Title       | Description |' \
  '|----|------|---------|-----|------------|-------------|-------------|' \
  '| ⬜ | T003 | bug     | 3   | —          | Independent | —           |' \
  '| ⬜ | T004 | chore   | 1   | —          | Another one | —           |' > "$REPO/TODO.md"
git -C "$REPO" add -A
at 2026-01-01T09:00:00Z git -C "$REPO" commit -q -m backlog
git -C "$REPO" init -q --bare -b main "$BASE/origin.git"
git -C "$REPO" remote add origin "$BASE/origin.git"
git -C "$REPO" push -q origin main
RUN=$(tr --root "$REPO" autopilot start --count 2 --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["run"]["id"])')
echo "run $RUN"

echo "--- 1. T003 finishes at 10:00, T004 at 11:00"
for pair in T003:T003-independent:10 T004:T004-another-one:11; do
  id=${pair%%:*}; rest=${pair#*:}; branch=${rest%%:*}; hour=${rest#*:}
  git -C "$REPO" worktree add -q "$BASE/$branch" -b "$branch" origin/main
  tr --root "$BASE/$branch" claim "$id" --owner lane --run "$RUN" > /dev/null
  tr --root "$BASE/$branch" done "$id" --owner lane > /dev/null
  git -C "$BASE/$branch" add -A
  at "2026-01-01T$hour:00:00Z" git -C "$BASE/$branch" commit -q -m "chore($id): mark done"
done
queue

echo "--- 2. main moves at 12:00; the orchestrator rebases T003 (handoff.next) at 12:30"
echo x > "$REPO/other.txt"; git -C "$REPO" add -A
at 2026-01-01T12:00:00Z git -C "$REPO" commit -q -m "other work"
GIT_COMMITTER_DATE=2026-01-01T12:30:00Z git -C "$BASE/T003-independent" rebase -q main
queue

echo "--- 3. the orchestrator commits a decision record on T004 at 13:00"
mkdir -p "$BASE/T004-another-one/docs"; echo decision > "$BASE/T004-another-one/docs/T004.md"
git -C "$BASE/T004-another-one" add -A
at 2026-01-01T13:00:00Z git -C "$BASE/T004-another-one" commit -q -m "docs(T004): record decision"
queue

echo "--- 4. T004 is pushed, and its worktree and local branch are removed: only origin/T004-another-one is left"
git -C "$REPO" push -q origin T004-another-one
git -C "$REPO" worktree remove --force "$BASE/T004-another-one"
git -C "$REPO" branch -q -D T004-another-one
git -C "$REPO" fetch -q origin
echo "\$ taskrail --root repo autopilot status --run $RUN --json  (state of T004; handoff)"
tr --root "$REPO" autopilot status --run "$RUN" --json | python3 -c 'import json,sys; r=json.load(sys.stdin)["runs"][0]; print([t["state"] for t in r["tasks"] if t["id"]=="T004"], json.dumps(r["handoff"]))'
rm -rf "$BASE"
```

## Evidence

`sh repro.sh`, unfixed code at `b184707`:

```text
run 20260914-1
--- 1. T003 finishes at 10:00, T004 at 11:00
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T10:00:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T11:00:00Z  committer 2026-01-01T11:00:00Z  chore(T004): mark done
--- 2. main moves at 12:00; the orchestrator rebases T003 (handoff.next) at 12:30
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T004", "T003"], "next": "T004"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T12:30:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T11:00:00Z  committer 2026-01-01T11:00:00Z  chore(T004): mark done
--- 3. the orchestrator commits a decision record on T004 at 13:00
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T12:30:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T13:00:00Z  committer 2026-01-01T13:00:00Z  docs(T004): record decision
--- 4. T004 is pushed, and its worktree and local branch are removed: only origin/T004-another-one is left
$ taskrail --root repo autopilot status --run 20260914-1 --json  (state of T004; handoff)
['done-branch'] {"mode": "sequential", "in_review": null, "queue": ["T004", "T003"], "next": "T004"}
```

Step 2 is the bug as T033 saw it: rebasing the task named by `next` makes another task `next`,
although T003 finished an hour before T004. Step 3 flips it back through a commit that is not
work on the task at all. Both tasks stay `done-branch` throughout, and no task is in review.
Step 4 shows the smaller defect below: T004, still `done-branch` through `origin/T004-another-one`,
jumps to the front because its local branch is gone.

## Root cause

`_handoff` in `src/taskrail/autopilot/status.py` sorts the waiting tasks by the
tip of their local branch:

```python
def tip_time(row: dict) -> int:
    head = _branch_ref(root, row.get("branch"))
    value = gitutil.run(root, "log", "-1", "--format=%ct", head, check=False).stdout.strip() if head else ""
    return int(value) if value.isdigit() else 0

waiting = sorted((row for row in rows if row["state"] == "done-branch"), key=lambda row: (tip_time(row), row["id"]))
```

The tip's committer time (`%ct`) is not the completion time. It is the time of the latest commit
on the branch, whatever it is (decision records, a rebase-conflict resolution, the record of a
rebase), and `git rebase` rewrites the committer time of every commit it replays. The
`autopilot status` row of DESIGN.md §12.1's command table specifies exactly this ("then by the branch tip's commit time"),
while §12.8 asks for "completion order", so the implementation follows a specification that does
not say what §12.8 means.

A second, smaller defect sits in the same function: `tip_time` reads only the local branch
(`refs/heads/<branch>`) and returns `0` when it does not exist, so a task that is `done-branch`
through its `<remote>/<branch>` copy alone always sorts to the front.

## Ruled out

- **The dependency pass.** The `while pending` loop only picks the earliest waiting task with no
  unplaced waiting dependency; the tasks in the reproduction have no dependencies, and the order it
  starts from is already wrong.
- **State detection.** `stack.done_on_branch` keeps both tasks `done-branch` at every step (both
  stay in `queue`); a rebase does not make the ✅ disappear or reappear.
- **`in_review` and the run's `handed_off` order.** Nothing is handed off in the reproduction;
  `in_review` is `null` throughout.
- **The ID tie-break.** It only decides between equal times; the times here differ by hours.
- **`idle_minutes`, which also reads the tip's `%ct`.** It measures a lane's latest activity, and
  a rebase or a decision record is activity, so it is right there; it does not feed the queue.
- **Using the tip's author time (`%at`) instead.** It survives a rebase (step 2 would keep its
  order), but a decision record's author time is when the record was written, so a decision record
  on the *earlier* task's branch would still move that task to the back. Not run: it follows from
  what `%at` of the tip means, and the regression test covers that case.
- **The claim's or the run file's timestamps.** `taskrail done` releases the claim, and neither the
  run file nor any other record stores when a task became `done-branch`; `status` is read-only, so it
  cannot start recording one.

## Affected areas

- `src/taskrail/autopilot/status.py` — `_handoff` (the only reader of `tip_time`).
- `DESIGN.md` §12.1, the `autopilot status` row of the command table: "`queue` (dependencies first, then
  by the branch tip's commit time)" specifies the bug. Governing path: changed only on approval.
- `CHANGELOG.md` — an Unreleased entry.
- The autopilot skill (`handoff.next`) needs no change: it already relies on completion order.

## Proposed fix

Order the waiting tasks by their **done commit**: the most recent first-parent commit on the task's
branch, not on its mainline, that turns the task's row ✅ — its row is ✅ in that commit and not in
its parent — and sort by that commit's **author time**. `git rebase`, `commit --amend` and
squashing into that commit all keep the author time, and later commits on the branch are not the
done commit.

In `status.py`:

1. Replace `tip_time` with a `_done_time(project, task_id)` helper. It takes the ref from
   `stack.done_on_branch(project)[task_id].refs` (the local branch first, else `<remote>/<branch>`,
   which also fixes the remote-only case), lists
   `git log --first-parent --format='%H %at' <ref> --not <mainline refs>`, reads the task's status at
   those commits and at the oldest one's parent with the existing `stack._read_statuses`, and
   returns the author time of the newest commit where the status turns ✅.
2. When no such commit is found (none should be, but history can be rewritten by hand), fall back
   to the tip's author time, so the queue still has an order.
3. Keep the sort key `(time, id)` and the dependency pass unchanged.

Regression test in `tests/test_autopilot.py`, next to
`test_handoff_queue_puts_dependencies_first`: two lanes finished at pinned times, then (a) `main`
moves and the earlier task's branch is rebased with a later `GIT_COMMITTER_DATE`, and (b) a
decision-record commit lands on the earlier task's branch; `handoff.queue` and `handoff.next` must
not change after either. A third assertion covers a task `done-branch` only through its
`origin/<branch>` copy.

Known limit, to state in DESIGN.md: a rebase run with `--reset-author-date` (or `--ignore-date`)
rewrites author times too, and moves the task to the back again.

DESIGN.md change (governing path; approved at the diagnose gate and applied in the fix), in the
`autopilot status` row of §12.1, replacing "`queue` (dependencies first, then by the branch tip's commit time)" with:

> `queue` (dependencies first, then in completion order: by the author time of the task's done
> commit — the latest first-parent commit on its branch, local or else remote, that turns its row
> ✅ — which a rebase or a later commit on the branch leaves unchanged, though a rebase with
> `--reset-author-date` does not; T053)

Plus a `CHANGELOG.md` Unreleased entry.

Diagnose-gate decisions (recorded in `docs/autopilot/decisions/T053-order-the-autopilot-hand-off-queue-by-co.md`):
the fix approach as proposed, the DESIGN.md phrase as written, and the remote-only ordering in scope.

## Fix

Regression tests first, in `tests/test_autopilot.py`. A shared setup,
`finished_in_order`, finishes T003 at 10:00 and T004 at 11:00 on their branches (pinned author and
committer dates) and asserts the queue starts as `["T003", "T004"]`. Then:

- `test_handoff_queue_keeps_its_order_when_a_waiting_branch_is_rebased` — `main` gets a commit at
  12:00 and T003's branch is rebased onto it with `GIT_COMMITTER_DATE` 12:30;
- `test_handoff_queue_ignores_commits_after_the_done_commit` — a decision-record commit lands on
  T003's branch at 12:00 (later than T004's done commit, so ordering by the tip's author time would
  fail it too);
- `test_handoff_queue_orders_a_branch_left_only_on_the_remote` — T004's branch is pushed, its
  worktree removed and its local branch deleted; T004 must still be `done-branch`.

Each asserts that `handoff.queue` stays `["T003", "T004"]` and `handoff.next` stays `T003`.

Run against the unfixed code (`uv run pytest -q --color=no --tb=line
tests/test_autopilot.py -k handoff_queue`):

```text
.FFF                                                                     [100%]
=================================== FAILURES ===================================
E   AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
      
      At index 0 diff: ['T004', 'T003'] != ['T003', 'T004']
      Use -v to get more diff
.../tests/test_autopilot.py:585: AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
E   AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
      
      At index 0 diff: ['T004', 'T003'] != ['T003', 'T004']
      Use -v to get more diff
.../tests/test_autopilot.py:593: AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
E   AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
      
      At index 0 diff: ['T004', 'T003'] != ['T003', 'T004']
      Use -v to get more diff
.../tests/test_autopilot.py:603: AssertionError: assert (['T004', 'T003'], 'T004') == (['T003', 'T004'], 'T003')
=========================== short test summary info ============================
FAILED tests/test_autopilot.py::test_handoff_queue_keeps_its_order_when_a_waiting_branch_is_rebased
FAILED tests/test_autopilot.py::test_handoff_queue_ignores_commits_after_the_done_commit
FAILED tests/test_autopilot.py::test_handoff_queue_orders_a_branch_left_only_on_the_remote
3 failed, 1 passed, 40 deselected in 1.74s
```

All three fail for the root cause: after the rebase, the decision record, and the loss of the local
branch, T004 moves ahead of T003 although T003 finished first. The one passing test is the existing
`test_handoff_queue_puts_dependencies_first`.

The fix, in `src/taskrail/autopilot/status.py`: `_handoff`'s nested `tip_time`
(the local tip's `%ct`, or `0` without a local branch) is replaced by a module-level
`_done_time(project, task_id)`, as proposed. It reads the ref from `stack.done_on_branch` (local
first, else remote), lists `git log --first-parent --format=%H %at <ref> --not <mainline refs> --`,
reads the statuses at those commits and at the oldest one's parent with `stack._read_statuses`, and
returns the author time of the newest commit whose row is ✅ while its parent's is not; without
one, the ref's tip author time. The sort key stays `(time, id)` and the dependency pass is
unchanged. The DESIGN.md phrase and the CHANGELOG entry above were applied.

## Verification

The regression tests after the fix
(`uv run pytest -q --color=no tests/test_autopilot.py -k handoff_queue`):

```text
....                                                                     [100%]
4 passed, 40 deselected in 2.52s
```

The stage's checks:

- `test` — `uv run pytest -q --color=no`: `831 passed in 96.66s (0:01:36)`.
- `lint` — not configured: the repository's `.taskrail/config.toml` sets no `lint` command and
  `pyproject.toml` has no linter.

The reproduction script above, re-run on the fixed code:

```text
run 20260914-1
--- 1. T003 finishes at 10:00, T004 at 11:00
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T10:00:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T11:00:00Z  committer 2026-01-01T11:00:00Z  chore(T004): mark done
--- 2. main moves at 12:00; the orchestrator rebases T003 (handoff.next) at 12:30
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T12:30:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T11:00:00Z  committer 2026-01-01T11:00:00Z  chore(T004): mark done
--- 3. the orchestrator commits a decision record on T004 at 13:00
$ taskrail --root repo autopilot status --run 20260914-1 --json  (handoff; tip commit times)
{"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
  T003-independent tip: author 2026-01-01T10:00:00Z  committer 2026-01-01T12:30:00Z  chore(T003): mark done
  T004-another-one tip: author 2026-01-01T13:00:00Z  committer 2026-01-01T13:00:00Z  docs(T004): record decision
--- 4. T004 is pushed, and its worktree and local branch are removed: only origin/T004-another-one is left
$ taskrail --root repo autopilot status --run 20260914-1 --json  (state of T004; handoff)
['done-branch'] {"mode": "sequential", "in_review": null, "queue": ["T003", "T004"], "next": "T003"}
```

The queue is `["T003", "T004"]` at every step.
