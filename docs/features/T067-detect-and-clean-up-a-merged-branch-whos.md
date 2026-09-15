# T067 — Detect and clean up a merged branch whose task was discarded on it

Kind: feature · Epic: E02 · Status: verified

Source: [T065's plan](T065-hand-off-a-branch-whose-task-was-discard.md) (*Out of scope*, first
bullet), opened at T065's plan gate
([decision record](../autopilot/decisions/T065-hand-off-a-branch-whose-task-was-discard.md), question 6).
Its dependency T065 is merged (`0404505`). No prior work: `show` reported no artifact, branch or
commit for T067.

## Premise, checked on the current mainline

On `origin/main` (`01af8ee`), `src/taskrail/autopilot/`:

- `merged.cmd_merged` sets `done_at_head = _row_done(project, task, head_commit)` and, when it is
  false, skips `detect` with the reason `<ID> is not done at the head of <ref>; content detection
  needs a finished branch`. A branch whose row is `❌` at its head therefore reads `merged: false`
  whatever the mainline holds, and `--cleanup` refuses it with exit 5 (`_cleanup`, `not merged`).
- `merged.recorded_merges` returns every task with a lane `merged` record whose commit is still on a
  mainline ref, whatever status the task was closed with, and `status.done_on_mainline` unions it
  into the `✅` rows. Recording a proven merge of a discarded branch would make `task_state` return
  `done-merged` and count it toward the run's `complete`.
- Without a record, a squash merge brings the `❌` row to `<remote>/<mainline>`, which
  `status.discarded_on_mainline` reads, so `status` already shows `discarded` after the merge (T065,
  criterion 3). The gap is `autopilot merged` itself: no proof, no record, no cleanup.

The premise holds.

## Behaviour

After this change, the orchestrator's *After a merge* step 1 (`autopilot merged <ID> --cleanup
--json`) works for a branch whose task was discarded on it, as for a done one:

- **Detected.** The content checks of §12.8 run for a head whose task row is `✅` **or `❌`**. A head
  whose row is still `⬜` is refused as before (an unstarted branch is an ancestor of the mainline).
  The reason for a pending head reads `<ID> is not done or discarded at the head of <ref>; content
  detection needs a closed branch`.
- **Reported.** A new key `closed` is `"done"` or `"discarded"`: the status the checked head's row
  closes the task with, or, when no branch is left, the recorded merge's status; `null` for a
  pending head. `done_at_head` keeps its meaning. `confirmations` gains `row_discarded_on_mainline`
  beside `row_done_on_mainline`. The text form's first line ends in ` (discarded)` for a discarded
  task.
- **Recorded, without reading done-merged.** The lane's `merged` record gains
  `status: "done" | "discarded"`. `recorded_merges` returns, per task, the status of its newest valid
  record (by `detected`; a record without `status`, written before T067, is `done`).
  `done_on_mainline` takes the tasks whose newest record is `done`; `discarded_on_mainline` takes
  those whose newest record is `discarded` (question 2). So a discarded branch merged and recorded
  reads `discarded` in `autopilot status`, even after its mainline row was edited by hand, and never
  counts toward `done_merged` or `complete`.
- **Cleaned up.** `--cleanup` removes the worktree, deletes the local branch with its lease and
  releases a leftover claim for a proven discarded merge exactly as for a done one; `_cleanup` is not
  changed.

## Acceptance criteria

1. A lane that claims a task, commits work, runs `taskrail discard` and commits it, pushes its
   branch, and is squash-merged on the host: `autopilot merged <ID> --json` exits 0 with
   `merged: true`, `via` `tree`, `closed: "discarded"`, `done_at_head: false`,
   `confirmations.row_discarded_on_mainline: true` and `row_done_on_mainline: false`.
2. With the task in a run, that call writes `merged` to the run's lane with `status: "discarded"`;
   `autopilot status --run R` then reports the task `discarded` (not `done-merged`), `done_merged` 0
   and `complete` false — also after the host edits the `❌` row back to `⬜` by hand.
3. `autopilot merged <ID> --cleanup --owner <lane>` on that discarded, merged branch exits 0, removes
   the worktree, deletes the local branch, releases a claim left behind and keeps the remote branch,
   as `test_cleanup_removes_the_worktree_and_local_branch_only` asserts for a done one. With the remote
   branch deleted afterwards, a second call reports `recorded: true`, `merged: true` and
   `closed: "discarded"`.
4. A done branch keeps its behaviour: its record has `status: "done"`, `closed` is `"done"`, it reads
   `done-merged`; a record without `status` (as written before T067) still counts as done.
5. When a task has records in two runs with different statuses, the newest by `detected` decides:
   a newer `discarded` record over an older `done` one reads `discarded`, not `done-merged`.
6. A branch whose row is `⬜` at its head is still not merged (`merged: false`, `closed: null`,
   `reason` containing `not done or discarded`, no check run), and `--cleanup` still exits 5 for it.
7. The text form names a discarded merge: `<ID> merged into origin/main via tree at <sha7> (discarded)`.
8. All tests pass: `uv run pytest -q`.

All criteria are verified by pytest on the `pilot` fixture of `tests/test_autopilot_merged.py`
(criteria 1–7), which already has a host that squash-merges, `unmark` and `delete`; a `discard`
helper beside `finish` is added there.

## Affected areas

- `src/taskrail/autopilot/merged.py`
  - `_row_done` → `_row_status(project, task, rev)` returning the row's cell at `rev`; callers compare
    it with `Status.DONE.value` / `Status.DISCARDED.value`.
  - `recorded_merges(project) -> dict[str, str]`: task ID → `"done"` or `"discarded"` from the newest
    valid record (by `detected`), a missing `status` read as `done`.
  - `_latest_record`: unchanged selection; its `status` feeds `closed` in the recorded case.
  - `cmd_merged`: the guard accepts `✅` or `❌` at the head; `closed`, `status` in the written entry,
    `confirmations.row_discarded_on_mainline`, the new pending reason.
  - `_text`: the ` (discarded)` suffix.
  - `_cleanup` and `_dependents`: not changed.
- `src/taskrail/autopilot/status.py`
  - `done_on_mainline`: unions the IDs whose recorded status is `done`.
  - `discarded_on_mainline`: unions the IDs whose recorded status is `discarded`, cached under its own
    key beside `MERGED_KEY` (question 2).
  - `task_state`, `_handoff`, `WITH_BRANCH` and `WAITING`: not changed.
- `src/taskrail/autopilot/runs.py`: not changed (records are free-form lane keys).
- Tests: `tests/test_autopilot_merged.py` — new tests for criteria 1–7; the existing
  `test_text_and_json_forms` key set gains `closed`, and `test_confirmations_are_reported_and_never_prove`
  gains `row_discarded_on_mainline: False`.
- `DESIGN.md` §12.1, §12.4, §12.8 (question 1, exact text below).
- `CHANGELOG.md`: one *Unreleased* bullet. `docs/features/README.md`: this row.
- The `taskrail-autopilot` skill: not changed (question 3).

## Out of scope

- A new state for a merged discard, and any change to `task_state`'s precedence, `autopilot next`,
  the run's count or the hand-off queue.
- A recorded merge that outlives a later reopen on the mainline: a record still counts while its
  commit is on a mainline ref, for done and discarded alike, as since T031.
- Stacked dependents of a discarded task: `_dependents` lists them as for a done one, which is what
  their rebase needs, since the discarded branch's content did reach the mainline.
- The plain `taskrail` skill, which never runs `autopilot merged`.

## Open questions and risks

- **`discarded_on_mainline` gains an input.** It feeds `task_state` and T064's candidate skip in
  `dispatch.next_lanes`. A recorded discard merge now makes a task `discarded` there even when both
  mainline rows read `⬜`, as a recorded done merge already makes one `done-merged`; that is the
  symmetry question 2 asks about.
- **Newest record wins.** Today any valid record counts. Choosing the newest by `detected` changes
  nothing for a task with one record or only done records; it only settles the mixed case of
  criterion 5. `detected` is an ISO timestamp, compared as text as `_latest_record` already does.
- **Output shape.** `closed` and `row_discarded_on_mainline` are additions; no key is removed or
  renamed, so existing consumers keep working.

## Questions for the plan gate

1. **`DESIGN.md` texts a–d** below: approve as written, or drop or change parts.
2. **Recorded discard merges and `discarded_on_mainline`.** (recommended) a record with
   `status: "discarded"` also feeds `discarded_on_mainline`, so a hand-edited mainline row cannot turn
   a proven discard merge back into `discarded-branch` or a dispatchable task — the same protection a
   recorded done merge has; or (B) records with `discarded` feed nothing, and only the `❌` rows decide
   `discarded` (smaller, but a hand edit of the row makes the task `discarded-branch` again with no
   branch left to hand off).
3. **Skill text.** (recommended) no change: *After a merge* step 1 already runs
   `autopilot merged <ID> --cleanup --json` for whatever branch was merged, and *Close and hand off*
   already says a discarded branch is handed off like a done one; or add "— for a `done-branch` or
   `discarded-branch` task alike —" to step 1, with installed copies refreshed by `taskrail upgrade`
   and a prose assertion in `tests/test_autopilot_skill.py`.
4. **Output key.** (recommended) one new key `closed` (`"done"`, `"discarded"`, `null`) that also
   covers the recorded case with no branch left; or `discarded_at_head` (bool) mirroring
   `done_at_head`, which cannot say which status a branchless recorded merge had.

## Plan-gate decisions

Recorded in [the decision record](../autopilot/decisions/T067-detect-and-clean-up-a-merged-branch-whos.md):
all five answers as recommended — the `DESIGN.md` texts a–d approved as written, recorded discard
merges feed `discarded_on_mainline`, no skill text change, the output key `closed`, and the newest
record by `detected` decides.

## Implementation

- `autopilot/merged.py`
  - `_row_done` became `_row_status`, returning the task's status cell at a revision; `CLOSED` maps
    `✅`/`❌` to `done`/`discarded`.
  - `record_status(record)`: a record's `status`, `done` unless it is `discarded` (so a record without
    one, written before T067, is `done`).
  - `recorded_merges(project)` returns `dict[task ID → status]`, taken from each task's newest valid
    record across every run through the existing `_latest_record`.
  - `cmd_merged`: detection runs when the head's cell is `✅` or `❌`; the pending reason reads
    `<ID> is not done or discarded at the head of <ref>; content detection needs a closed branch`;
    `closed` comes from the head's cell, or from the record when no branch is left; the written entry
    carries `status`; `confirmations` gains `row_discarded_on_mainline`.
  - `_text`: ` (discarded)` after the first line of a discarded merge.
  - `_cleanup` and `_dependents` are unchanged.
- `autopilot/status.py`: new `_recorded(project, status)`, caching `recorded_merges` under
  `RECORDED_KEY`; `done_on_mainline` unions the `done` IDs and `discarded_on_mainline` the
  `discarded` IDs. `task_state`, `_handoff`, `WITH_BRANCH` and `WAITING` are unchanged.
- `DESIGN.md` texts a–d applied as approved; one *Unreleased* bullet in `CHANGELOG.md`.

The new and changed tests were run before the implementation and failed for the reasons the criteria
name:

```text
$ uv run pytest -q -p no:cacheprovider --color=no --tb=line tests/test_autopilot_merged.py
.......F.F.....................FFFFFFF                                   [100%]
tests/test_autopilot_merged.py:276: KeyError: 'closed'
tests/test_autopilot_merged.py:299: AssertionError: … Right contains 1 more item: {'row_discarded_on_mainline': False}
tests/test_autopilot_merged.py:747: AssertionError: … Extra items in the right set: 'closed'
tests/test_autopilot_merged.py:789: AssertionError: assert (False, None, None) == (True, 'tree'...ef2865cc221a')
tests/test_autopilot_merged.py:802: AssertionError: assert (False, []) == (True, ['20260915-1'])
tests/test_autopilot_merged.py:53: AssertionError: taskrail: cleanup refused: T003 is not merged, so nothing was removed
tests/test_autopilot_merged.py:841: KeyError: 'closed'
tests/test_autopilot_merged.py:859: KeyError: 'merged'
tests/test_autopilot_merged.py:872: AssertionError: … + T003 not merged into origin/main: T003 is not done at the head of T003-independent; content detection needs a finished branch
9 failed, 29 passed in 19.58s
```

Criterion 5's test first failed at the missing record (line 859), before reaching the rule it checks.
After the implementation, replacing the newest-record rule with "any `done` record wins" made it
fail on the rule itself, and the change was reverted:

```text
$ uv run pytest -q -p no:cacheprovider --color=no --tb=line tests/test_autopilot_merged.py -k newest_recorded
tests/test_autopilot_merged.py:864: AssertionError: 2000-01-01T00:00:00+00:00
    assert 'done-merged' == 'discarded'
1 failed, 37 deselected in 1.18s
```

After it:

```text
$ uv run pytest -q -p no:cacheprovider --color=no --tb=short tests/test_autopilot_merged.py
38 passed in 21.38s
$ taskrail checks T067 --stage implement
== test: uv run pytest -q
959 passed in 132.81s (0:02:12)
== lint: not configured
```

## Criteria and tests

All in `tests/test_autopilot_merged.py`, section 15 unless named otherwise.

| # | Tests |
|---|---|
| 1 | `test_a_merged_discarded_branch_is_detected_and_reported` (`merged`, `tree`, the squash commit, `closed: "discarded"`, `done_at_head: false`, `row_discarded_on_mainline: true`, `row_done_on_mainline: false`) |
| 2 | `test_a_recorded_discard_merge_reads_discarded_and_never_done_merged` (row edited back to `⬜` on the host: `discarded-branch` before `merged`; record `status: "discarded"`; then `discarded`, `done_merged` 0, `complete` false) |
| 3 | `test_cleanup_removes_a_merged_discarded_branch` (the full `cleanup` object, worktree and local branch gone, remote branch and no claim; after the remote branch is deleted, `recorded: true`, `closed: "discarded"`, same commit) |
| 4 | `test_a_done_merge_records_done_and_a_record_without_status_counts_as_done` (`closed: "done"`, record `status: "done"`, `done-merged`, still `done-merged` with `status` removed); the existing done tests in sections 1–14 unchanged |
| 5 | `test_the_newest_recorded_merge_decides_the_status` (an older `done` record in another run: `discarded`; a newer one: `done-merged`) |
| 6 | `test_an_unstarted_branch_is_not_merged_although_it_is_an_ancestor` (section 5: `closed: null`, `not done or discarded`, no check run, `--cleanup` exit 5 `not merged`) |
| 7 | `test_the_text_form_names_a_discarded_merge`; `test_text_and_json_forms` (section 14) with the `closed` key; `test_confirmations_are_reported_and_never_prove` (section 6) with `row_discarded_on_mainline` |
| 8 | `taskrail checks T067 --stage implement`: 959 passed |

## Implement-gate decisions

Recorded in [the decision record](../autopilot/decisions/T067-detect-and-clean-up-a-merged-branch-whos.md):
the implementation approved; the §12.1 `autopilot close` row's last phrase now reads "`merged` still
records merges in it, and those still count toward `done-merged`, or `discarded` for a discarded
branch (T067)", in its own commit; `recorded_merges` kept as is.

## Verification

The real CLI from this branch, one subprocess per command
(`uv run taskrail --root …`), driven by a throwaway script in a temporary
directory outside this repository, removed afterwards. The scratch repository has `TODO.md` with
pending `T001` (feature, *Dropped idea*) and `T002` (bug, *Real fix*), `[autopilot] enabled = true`,
a bare `origin` and a second clone as the host. Steps: `autopilot start --count 2`; a worktree for
T001 from `origin/main`, claimed with `--run`; a commit, `discard T001` committed and the branch
pushed; `merged` and `merged --cleanup` before any merge; the host squash-merges the branch and then
edits the `❌` row back to `⬜` by hand; `merged --run R --cleanup`; the remote branch deleted and
`merged` again; `next --run R`.

```text
== T001 discarded on its branch and pushed, not merged
--- taskrail autopilot status --run 20260915-1 --fetch --json (exit 0)
states={'T001': 'discarded-branch'} done_merged=0 complete=False handoff={"mode": "sequential", "in_review": null, "queue": ["T001"], "next": "T001"}
--- taskrail autopilot merged T001 --json (exit 0)
{"merged": false, "via": null, "closed": "discarded", "done_at_head": false, "recorded": false, "reason": "no check proves that T001-dropped-idea is contained in origin/main", "confirmations": {"row_done_on_mainline": false, "row_discarded_on_mainline": false, "title_commit": null}, "runs": [], "cleanup": null}
--- taskrail autopilot merged T001 --cleanup --owner lane --json (exit 5)
stderr: taskrail: cleanup refused: T001 is not merged, so nothing was removed
lane still exists: True
== T001 squash-merged on the host, then its row edited back to ⬜ by hand
--- taskrail autopilot status --run 20260915-1 --fetch --json (exit 0)
states={'T001': 'discarded-branch'} done_merged=0 complete=False handoff={"mode": "sequential", "in_review": null, "queue": ["T001"], "next": "T001"}
== autopilot merged T001 --run --cleanup
--- taskrail autopilot merged T001 --run 20260915-1 --cleanup --owner lane --json (exit 0)
{"merged": true, "via": "tree", "closed": "discarded", "done_at_head": false, "recorded": false, "reason": null, "confirmations": {"row_done_on_mainline": false, "row_discarded_on_mainline": false, "title_commit": "c18254ff838d2f1e907151635082c91508daff2d"}, "runs": ["20260915-1"], "cleanup": {"worktree": "/tmp/t067-verify-AgbTlm/lanes/T001-dropped-idea", "worktree_removed": true, "branch_deleted": true, "claim_released": false, "remote_branch": "origin/T001-dropped-idea", "refused": null}}
lane still exists: False | local branch: False
run record: {"via": "tree", "commit": "c18254ff838d2f1e907151635082c91508daff2d", "head": "409a48dc66bc1ad3e355ffb0e2bdb45c21fbca30", "mainline": "origin/main", "detected": "2026-09-15T02:16:45+00:00", "status": "discarded"}
--- taskrail autopilot status --run 20260915-1 --fetch --json (exit 0)
states={'T001': 'discarded'} done_merged=0 complete=False handoff={"mode": "sequential", "in_review": null, "queue": [], "next": null}
== remote branch deleted: only the run knows the merge
--- taskrail autopilot merged T001 (exit 0)
T001 merged into origin/main via tree at c18254f (recorded in a run) (discarded)
--- taskrail autopilot merged T001 --json (exit 0)
{"merged": true, "via": "tree", "closed": "discarded", "done_at_head": null, "recorded": true, "reason": null, "confirmations": {"row_done_on_mainline": false, "row_discarded_on_mainline": false, "title_commit": "c18254ff838d2f1e907151635082c91508daff2d"}, "runs": [], "cleanup": null}
--- taskrail autopilot status --run 20260915-1 --fetch --json (exit 0)
states={'T001': 'discarded'} done_merged=0 complete=False handoff={"mode": "sequential", "in_review": null, "queue": [], "next": null}
== next --run does not dispatch T001 again
--- taskrail autopilot next --run 20260915-1 --json (exit 0)
"skipped": [{"id": "T001", "reason": "discarded on the mainline, not in this checkout"}, …]
```

The behaviour matches the plan; no gap. `closed` is reported for a closed head whether or not the
merge is proven, as planned. `claim_released` is false because `discard` had already released the
claim; the leftover-claim case is criterion 3's test. `row_discarded_on_mainline` is false after the
merge only because the host edited the row back to `⬜`, which is what makes the recorded merge the
only evidence here. The script's first `next --run` call dispatched T002 and failed to print its
output (a bug in the throwaway script reading `lanes`); the output above is a second call, where T002
is already dispatched.

## DESIGN.md text (approved at the plan gate, applied as written)

Each replacement is one phrase; a phrase the file wraps across lines is replaced across them, keeping
the surrounding lines as they are.

**a. §12.1, `autopilot merged` row** — two phrases:

- replace "Reports `merged`, `via` (`ancestor`, `tree`, `patch-id`, `merge-tree`), the mainline
  `commit`, each check in `checks`, the `confirmations`, and both heads." with "Reports `merged`,
  `via` (`ancestor`, `tree`, `patch-id`, `merge-tree`), the mainline `commit`, each check in
  `checks`, `closed` (`done` or `discarded`: the status the head's row, or the recorded merge, closes
  the task with; T067), the `confirmations`, and both heads.";
- replace "A proven merge is recorded as `merged` in the lane of every run holding the task," with
  "A proven merge is recorded as `merged`, with that `status`, in the lane of every run holding the
  task,".

**b. §12.4, the `done-merged` bullet** — two phrases:

- replace "or a merge `autopilot merged`
    proved as in §12.8 and recorded in a run," with "or a merge of its ✅ branch `autopilot merged`
    proved as in §12.8 and recorded in a run, the task's newest such record deciding (*T067*),";
- replace "The record — `merged: {via, commit, head, mainline, detected}` in the lane — is evidence"
  with "The record — `merged: {via, commit, head, mainline, detected, status}` in the lane, `status`
  being `done` or `discarded` (`done` when absent) — is evidence".

**c. §12.4, the `discarded` bullet** — replace "under the same reopen rule (*T064*), so a
    discarded run task stays visible." with "under the same reopen rule (*T064*), or a recorded
    merge of its ❌ branch under the same rule as `done-merged` (*T067*), so a discarded run task
    stays visible.".

**d. §12.8, *Merge detection*** — two phrases:

- replace "and only for a head whose task row is ✅ —" with "and only for a head whose task row is ✅
  or ❌ (*T067*) —";
- replace "The ✅ row on the mainline and an `(ID)` pull request
  title confirm a merge" with "The ✅ row (❌ for a discarded task) on the mainline and an `(ID)` pull
  request title confirm a merge".
