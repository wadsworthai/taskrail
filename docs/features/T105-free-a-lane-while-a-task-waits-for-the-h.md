# T105 — Free a lane while a task waits for the human and requeue it when they answer

Kind: feature · Epic: E02 · Status: implemented

The task comes from run 20260918-1 itself: the run stalled more than once with one lane working
and two waiting for an answer, while `autopilot next` reported `limited_by: max_lanes`.

## What the code does today

Measured on this branch (`origin/main` at `e9a20ce`), not assumed.

`src/taskrail/autopilot/dispatch.py` has two tuples:

```python
OCCUPYING = ("running", "gate", "escalated", "dispatched")  # states that use a lane and hold resources
COUNTED = ("dispatched", "running", "gate", "escalated", "failed", "done-branch", "handed-off", "done-merged")  # toward a run's count
```

A temporary test (`tests/test_t105_measure.py`, deleted after this gate) reproduced the stall with
`max_lanes = 3`, three claimed lanes, two of them recorded `escalated`:

```json
{"occupied": {"max": 3,
  "occupied": [{"id": "T001", "state": "escalated"}, {"id": "T002", "state": "escalated"}, {"id": "T003", "state": "running"}],
  "free": 0},
 "limited_by": "max_lanes", "dispatch": [], "remaining": 3,
 "text": "nothing to dispatch · 3/3 lanes in use · 3 more for run 20260918-1 · limited by max_lanes"}
```

Three further facts the design rests on:

1. **`handed-off` does not hold a lane.** It is absent from `OCCUPYING` and present in `COUNTED`.
   Measured with `max_lanes = 2` and T001 handed off: `lanes.occupied` is `["T002", "T003"]` — the
   two tasks `next` dispatched in the same call — T001's `claim` is `null`, and `remaining` is 3 of
   6. So a handed-off task holds no lane; it holds a place in the **run's count**, which is
   §12.7 as written ("the count caps what a run starts") and not this task's subject.
2. **`failed` already is the state this task needs.** `failed` is in `COUNTED` but not in
   `OCCUPYING`: it keeps its claim, branch and worktree, keeps its place in the count, and frees
   its lane. The change for `escalated` is the same move, plus a way back.
3. **A claimed task is not a candidate.** `next` builds candidates with
   `query.eligible(project, None, claimed)`, and `query.state` returns `claimed` for any task with
   a live claim, so an escalated task that keeps its claim can never return through the ordinary
   candidate list. The way back has to be an explicit path in `next_lanes`, and it cannot be
   subject to the run's `count`, since the task is already counted.

`status` already reports an escalated task's `branch`, `worktree`, `claim`, `touched`,
`idle_minutes` and `gate` (`WITH_BRANCH` contains `escalated`), but nothing in its output says
whether the task holds a lane.

## Behaviour

**1. An escalated lane frees its lane.** `escalated` leaves `OCCUPYING` and stays in `COUNTED`. The
task keeps its claim, branch and worktree; `next` may dispatch another task in its place;
`lanes.occupied` no longer lists it and `lanes.free` counts its place. Its resource values are
released by the next `next --run`, reported in `released`, exactly as a failed lane's are today.

**2. The human's answer parks the task in the queue.** A new lane state `parked`, recorded with

```bash
taskrail autopilot lane <ID> --run <R> --state parked [--reason "<what was answered>"]
```

means *the human has answered; the task waits for a lane*. It holds no lane and no resources, keeps
its place in the count, and keeps the recorded `gate`, so the restart knows where the lane stopped.
It is refused (exit 5) unless the task's current state is `running`, `gate`, `escalated`, `failed`
or `parked` — a task with no lane to resume cannot jump the queue.

**3. `next` redispatches parked tasks first.** Before the ordinary candidates, `next --run R` takes
the run's `parked` tasks, oldest answer first (`updated`, then ID), subject to `max_lanes`, group
limits and resources but **not** to the run's `count`, since they are already counted. Each one is
recorded `dispatched` with fresh resources, its recorded state returns to `running`, and its entry
in `dispatch` carries `"restart": true` beside the usual fields, so the orchestrator uses the lane
brief's *Workspace (restart from the branch)* section, or resumes the existing sub-session by its
handle when that still reaches it.

**4. When every lane is busy, the answer waits.** A parked task that no free lane takes stays
`parked` and is reported, so the orchestrator never loses it:

- `next` gains a `parked` list — `[{id, run, gate, reason, dispatched, why}]` — holding every parked
  task of every open run, whether or not this call dispatched it, with `why` (`"no free lane"`,
  `"group ui is full"`, `"resource:PORT"`, `"needs --run <R>"` in the preview). `limited_by` still
  names the limit that stopped the call, so `max_lanes` now means real work is waiting;
- `status` gains a per-task `holds_lane` boolean, true for the states in `OCCUPYING`. A task with a
  `branch` and a `worktree` and `holds_lane: false` is a task holding a workspace but no lane; the
  text form appends `no lane` to such a row.

**5. The skill answers every escalation through the queue.** `taskrail-autopilot`'s *Escalate* step
gains: when the human answers, record `--state parked`, then run `next --run <R>`; resume or
restart the lane only when `next` dispatches the task. The orchestrator never decides on its own
whether a lane is free — the CLI computes that, as §12.1 says.

## Acceptance criteria

1. With `max_lanes = 3`, two escalated lanes and one running, `autopilot next --run R` dispatches a
   further task: `lanes.occupied` lists only the running lane and the new one, `lanes.free` counts
   the escalated tasks' places, and `limited_by` is not `max_lanes`.
2. An escalated task keeps its claim, branch, worktree and its place in the run's count:
   `remaining` is unchanged by criterion 1's escalations, and `status` still reports its `claim`,
   `branch`, `worktree`, `gate` and `reason`.
3. The next `next --run R` releases an escalated lane's resource values and reports them in
   `released`; another dispatched task may then hold them.
4. `autopilot lane <ID> --run R --state parked` records `parked`, keeps the recorded `gate` and
   accepts an optional `--reason`; `status` and `next` read the task as `parked`.
5. `--state parked` exits 5 for a task whose state is `pending`, `dispatched`, `done-branch`,
   `handed-off`, `done-merged`, `discarded` or `discarded-branch`, naming the states it allows.
6. `next --run R` dispatches a parked task before a never-started candidate, with `restart: true`
   in its entry, the task's own branch and worktree in the entry's fields, fresh resources, and the
   run file recording it `running` with a live `dispatched` stamp and empty `gate`.
7. A parked task is redispatched even when the run's `remaining` is 0, and a redispatch does not
   lower `remaining`.
8. Two parked tasks are redispatched oldest answer first.
9. With every lane busy, `next --run R` dispatches no parked task, reports each in `parked` with
   `dispatched: false` and `why: "no free lane"`, and reports `limited_by: "max_lanes"`; the text
   form names them.
10. `next` without `--run` (the preview) lists open runs' parked tasks in `parked` with
    `why: "needs --run <R>"` and dispatches none, writing nothing.
11. `status` reports `holds_lane` for every task row: false for `escalated`, `parked`, `failed`,
    `done-branch`, `handed-off`, `done-merged`, `discarded-branch` and `discarded`, true for
    `dispatched`, `running` and `gate`; the text form marks a row with a workspace and no lane.
12. A parked task's escalation flags are unchanged by the new state: an unapproved governing path
    still raises `governing`, and `escalate_gate` is null once it is no longer `gate` or
    `escalated`.
13. `DESIGN.md` §12 states the new state, the freed lane, the redispatch order and the count rule;
    the `taskrail-autopilot` skill states the answer-through-the-queue procedure; the installed
    copies match (`taskrail upgrade`).

## Tests

Every test was observed failing against this branch's parent before the code was written
(`git stash push -- src/` then `uv run pytest tests/test_autopilot_parked.py -q`: 12 failed).

| # | Test |
|---|---|
| 1, 2 | `tests/test_autopilot_parked.py::test_an_escalated_lane_frees_its_lane_and_keeps_its_claim_and_its_place`, and `tests/test_autopilot_next.py::test_a_gate_occupies_a_lane_while_escalated_and_failed_do_not` for the gate that still holds one |
| 3 | `::test_an_escalated_lane_gives_its_resource_values_back` |
| 4 | `::test_lane_state_parked_records_the_answer_and_keeps_the_gate` |
| 5 | `::test_parked_is_refused_for_a_task_that_holds_no_lane` |
| 6 | `::test_next_redispatches_a_parked_task_before_a_task_never_started`, and `::test_a_parked_task_whose_claim_was_released_is_dispatched_once` for the one lane a released claim could have doubled |
| 7 | `::test_a_parked_task_returns_even_when_the_run_s_count_is_used_up` |
| 8 | `::test_parked_tasks_return_oldest_answer_first` |
| 9 | `::test_a_parked_task_waits_while_every_lane_is_busy` |
| 10 | `::test_the_preview_lists_parked_tasks_and_dispatches_none` |
| 11 | `::test_status_reports_which_tasks_hold_a_lane` |
| 12 | `::test_a_parked_task_still_flags_an_unapproved_governing_path` |
| 13 | `::test_design_and_skill_describe_the_parked_state`, plus `tests/test_autopilot_skill.py` and `tests/test_install.py` for the installed copies |

## Affected areas

| File | Change |
|---|---|
| `src/taskrail/autopilot/dispatch.py` | `OCCUPYING` drops `escalated`; `COUNTED` gains `parked`; a parked pass before the candidate loop; `parked` in the report; `text()` lines |
| `src/taskrail/autopilot/runs.py` | `LANE_STATES` gains `parked`; `GATE_CLEARING` unchanged (`parked` keeps its gate); a helper for the parked lanes of a run |
| `src/taskrail/autopilot/status.py` | `STATES` and `WITH_BRANCH` gain `parked`; `RECORDED` gains `parked`; `holds_lane` per row |
| `src/taskrail/autopilot/commands.py` | `--state parked` in the parser, its refusal, `holds_lane` in `_status_text`, the `parked` lines in `next`'s text |
| `src/taskrail/skills/taskrail-autopilot/SKILL.md` | *Escalate*, *Dispatch* step 6 and *Resume a run* step 4 |
| `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md` | one line in the restart section: the lane may be restarting after an answered escalation |
| `DESIGN.md` | §12.1 (`lane`, `next`, `status` rows), §12.4 (state list), §12.6 (escalation frees the lane), §12.7 (lane in use, count) |
| `CHANGELOG.md` | one Unreleased entry |
| `tests/` | new `tests/test_autopilot_parked.py`; edits to `tests/test_autopilot_next.py::test_gate_and_escalated_occupy_a_lane_and_failed_does_not` (its name and premise change) and to the state assertions in `tests/test_autopilot.py` |
| `.claude/skills/taskrail-autopilot/`, `.taskrail/installed.json` | regenerated by `taskrail upgrade` |
| `TODO.md`, `docs/features/README.md`, this artifact | task row, index, write-up |

Other lanes in run 20260918-1: T104 edits `src/taskrail/skills/taskrail/SKILL.md` (a different
skill file) and `CHANGELOG.md` (a known conflict class); T057 touches no code. No file above is
shared with them except `CHANGELOG.md` and `.taskrail/installed.json`, both known classes.

## Out of scope

- **`gate` keeps its lane.** A lane at an ordinary gate waits for the orchestrator, which answers
  within one wake-up; freeing that lane would let a run start work it is about to stop.
- **`handed-off`.** Measured above: it holds no lane. That it keeps a place in the run's count is
  §12.7 as designed, and changing it would let a run start more tasks than the human asked for.
- **A cap on parked workspaces.** Freeing lanes lets a run hold more claims and worktrees than
  `max_lanes`. No new limit is added; §12.7's `count` still caps the run.
- **Automatic requeueing.** Nothing infers that the human answered: the orchestrator records it.
- **`failed` → `parked` by a command other than `lane`**, and any new top-level command.

## Decisions taken at the plan gate

Answered by the orchestrator from this repository's `CLAUDE.md` and `DESIGN.md` §12; the full
record is in the [decision record](../autopilot/decisions/T105-free-a-lane-while-a-task-waits-for-the-h.md).

1. **The state is named `parked`**, not `queued` — for the state, the `--state` value and the report
   key. `status` already reports `handoff.queue`, the branches waiting to be handed off, and two
   *queue* fields in one `--json` output meaning different things is a defect waiting to be written
   into someone's tooling. `parked` says the thing exactly: the workspace is kept, the lane is not.
2. **Parked tasks are redispatched first**, oldest answer first, ahead of tasks never started.
3. **A parked lane releases its resource values**, as a failed one does. Holding them would turn
   `limited_by: max_lanes` into `limited_by: resource:<name>` — the same stall with a new label.
4. **A redispatch records the lane `running`** with a live `dispatched` stamp: one rule, instead of
   a conditional in three places.
5. **An answered escalation always goes through the queue** — recorded `parked`, returned by
   `next` — even when a lane is free, so the lane budget is enforced by the CLI and not by the
   orchestrator's arithmetic.
6. **`handed-off` is not covered and opens no follow-up**; **`gate` does not free its lane.**

## Risks

- **Work in flight outgrows the lanes.** With lanes freed, a run can hold `max_lanes` working lanes
  **plus** any number of parked workspaces — claims and worktrees. That is what the row asks for:
  no `max_parked` limit is added, and `holds_lane` makes the parked workspaces visible. Accepted at
  the plan gate; if it ever bites, that visibility is the evidence a limit would need.
