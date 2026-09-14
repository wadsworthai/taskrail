# T030 — Dispatch autopilot lanes with autopilot next

Kind: feature · Epic: E02 · Status: verified (plan approved with Q3 and Q7 changed at the gate)

Source: the accepted autopilot design, `DESIGN.md` §12 (§12.1 *Skill and CLI*,
§12.4 *State*, §12.7 *Resources*, §12.9 *Configuration*), and the evidence behind it in
`docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md`. Builds on T029 (run files,
`lane`, `status`, `AutopilotConfig`), T020 and T035 (the column predicate in `predicates.py`),
and T017/T019 (`done-branch`, stacked bases, `branches.task_branch`). The plan-gate decisions
are recorded in `docs/autopilot/decisions/T030-dispatch-autopilot-lanes-with-autopilot.md`.

## Behaviour

Today there is no `autopilot next` (`taskrail autopilot next` exits 2 with
`invalid choice: 'next'`), `[[autopilot.group]]` and `[[autopilot.resource]]` are ignored without
any check — even `limit = "one"`, an undeclared `column` and an empty `values` validate cleanly —
and `autopilot lane --group` stores any name (see *Evidence*). An orchestrator has to work out on
its own which tasks to start, how many, and which port or database each lane uses.

After this change:

- **Configuration.** `[autopilot]` accepts the two tables of §12.9, checked when the config loads
  (exit 2, naming the table entry and key):
  - `[[autopilot.group]]`: `name` (a unique name, lowercase letters, digits and dashes), `limit`
    (an integer, at least 1), and either `column` plus `match` — parsed by
    `predicates.parse_column_predicate` and resolved with `predicates.resolve_column`, so a core
    column, an alias or an undeclared column is refused exactly as for stages — or neither, which
    makes a *judgement group*.
  - `[[autopilot.resource]]`: `name` (unique, `^[A-Z][A-Z0-9_]*$`, so `TASKRAIL_RESOURCE_<NAME>`
    is a valid environment variable) and `values` (a non-empty list of unique non-empty strings).
- **`taskrail autopilot next --run R [--json]`** returns the tasks to dispatch now and records the
  dispatch in run R, under the common-directory lock, in one atomic step:
  1. **Occupied lanes** are counted across every run in the clone (Q2): a run task whose derived
     state (T029's `status` precedence) is `running` (a claim, stale or not), `gate` or
     `escalated`, or which is *dispatched* — recorded by an earlier `next` and not yet claimed,
     for less than `[git].claim_grace_minutes` (Q1, Q4). `failed`, `done-branch`, `handed-off`,
     `done-merged`, `discarded` and an expired dispatch occupy nothing.
  2. **Releases** (Q5): every lane, in any run, that holds resources but no longer occupies a lane
     has its `resources` cleared, and the released values are reported.
  3. **Candidates** are `taskrail next`'s eligible tasks in its order (points ascending, then file
     position), across backlogs: pending, unclaimed, not `done-branch`, not blocked — one
     dependency done only on its unmerged branch still counts as a stacked base (T017). Of those,
     a task is left out when its kind is not one the run drives (Q7): the intersection of the
     run's `kinds` and `[autopilot].kinds` when both are set, whichever is set otherwise, and
     every allowed kind when neither is. It is skipped with a reason when it is
     dispatched in a run already, recorded `failed` in run R, a member of a group at its limit,
     or when `show`'s `base` is diverged or has no `onto` (Q8).
  4. **Capacity** is the smallest of: free lanes (`max_lanes` minus occupied), the run's remaining
     target (`count` minus its tasks that are dispatched, `running`, `gate`, `escalated`,
     `failed`, `done-branch`, `handed-off` or `done-merged` — only `discarded` and `pending` run
     tasks leave their place free; Q3), and the free values of each resource.
     Candidates are taken in order until capacity runs out; each one taken counts immediately
     toward the lanes, the target, its groups and the resources for the next one.
  5. **Groups**: a task is a member of a column group when the predicate matches its row, and of a
     judgement group when run R records that group for it — assigned beforehand with
     `autopilot lane <ID> --run R --group G` (Q9). Occupied members are counted the same way.
  6. **Resources**: each dispatched task gets the first free value of every resource, in the
     order `values` lists them.
  7. **Recorded** for each dispatched task in run R: `dispatched` (a timestamp) and `resources`;
     nothing else (Q4).

  The result holds `run`, `preview` (false), `dispatch` — for each task `show --json`'s fields
  (`base` already carries `commit`, `kind_descriptor` and `prior_work` included), plus
  `resources`, `environment` (`TASKRAIL_RESOURCE_<NAME>` → value), `groups` (the names it counts
  toward), `decisions` and `decisions_index` — then `lanes` (`max`, `occupied` with each lane's ID,
  run, state and groups, `free`), `remaining`, `groups` and `resources` (each with its limit or
  values, occupants or holders, and what is free after this dispatch), `released`, `skipped`
  (`id` and `reason`, only for eligible tasks of the run's kinds met before capacity ran out) and
  `limited_by` (`max_lanes`, `count`, `resource:<NAME>`, or `null` when candidates ran out). Text
  output prints one line per dispatched task (ID, kind, branch, base, resource values) and a
  summary line.
- **`taskrail autopilot next` without `--run`** is a preview (Q10): the same computation for
  `[autopilot].kinds`, with no run target and judgement groups taken from any run's record; it
  writes nothing, `preview` is true, and `resources` shows the values that would be allocated.
- **Exit codes** (Q11): 5 when `[autopilot].enabled` is not true, checked first as in `start`; 1
  for an invalid backlog (no `--allow-invalid`: dispatching on a broken backlog is refused); 3 for
  an unknown run; 4 when the lock cannot be taken; 0 otherwise, including an empty `dispatch`.
- **`autopilot lane --group G`** now checks the name (Q9): exit 2 when no judgement group `G` is
  configured, naming the judgement groups, and exit 2 for a column group, naming its column, since
  its membership is computed. This replaces T029's "stored as given".
- **`autopilot status`** reports a dispatched, not yet claimed task as `dispatched` instead of
  `pending` (Q6); an expired dispatch is `pending` again.

## Acceptance criteria

1. Without the tables, `AutopilotConfig.groups` and `.resources` are empty; a config with a column
   group, a judgement group and a resource loads them, the column resolved to its declared
   spelling. Each of these exits 2 from any command and names the key: a `group` or `resource`
   that is not an array of tables; a group without `name` or `limit`, with a duplicate or
   malformed name, a non-integer or a `limit` below 1, `column` without `match` or the reverse, a
   `column` not in `[columns].custom`, or a core column; a resource without `name` or `values`, a
   duplicate or malformed name, an empty `values`, a non-string, empty or duplicate value.
2. `autopilot next` and `next --run R` with `enabled` absent or false exit 5 naming
   `[autopilot].enabled` and write nothing; `--run` for an unknown or malformed run exits 3; an
   invalid backlog exits 1.
3. With four independent pending tasks, `max_lanes = 2` and a run of count 5, `next --run R --json`
   dispatches the first two in `taskrail next` order, records `dispatched` for both in the run
   file, reports `limited_by: "max_lanes"`, and each entry carries `show`'s fields (`base.commit`,
   `branch`, `worktree`, `kind_descriptor`, `prior_work`) and the rendered decision-record paths.
4. Calling `next --run R` again at once dispatches nothing (both lanes are occupied by dispatch).
   After `claim T001 --run R` it still dispatches nothing. Once the dispatch of T002 is older than
   `claim_grace_minutes` without a claim, `next` releases its resources and offers T002 again.
5. A lane recorded `gate` or `escalated` occupies a lane; one recorded `failed` does not. The
   failed task stays out of `dispatch` while its claim is held (not eligible), and is skipped with
   reason `failed` once its claim is released; its dependents are not candidates (blocked). A
   `done-branch` lane frees its lane and its resources.
6. Lanes are counted across runs: a claim in run A occupies a lane seen by `next --run B`; a task
   dispatched in run A is skipped by run B with reason `dispatched`.
7. The run target limits dispatch: with count 1 and nothing dispatched, `next` dispatches one task
   and reports `limited_by: "count"`; a run task recorded `failed` keeps its place (nothing more is
   dispatched), and a discarded run task frees its place.
8. Kinds: a run started with `--kinds bug` dispatches only bug tasks; a run with empty kinds uses
   `[autopilot].kinds` when set, otherwise every allowed kind; a run with `bug,chore` under
   `[autopilot].kinds = ["chore", "feature"]` dispatches only chore tasks, and one with `bug` under
   `["feature"]` dispatches nothing. Tasks of other kinds are not listed in `skipped`.
9. A column group `ui` with `limit = 1` matching `Area = ui`: with two `ui` tasks and one other,
   one `next` dispatches one `ui` task and the other task, and skips the second `ui` task with reason
   `group ui is full`; while the first `ui` lane runs, a later `next` still skips it; once that lane is
   `done-branch`, it is offered.
10. A judgement group `db` with `limit = 1`: after `lane T003 --run R --group db` and
    `lane T004 --run R --group db`, `next` dispatches only the first of them. `lane --group nope`
    and `lane --group ui` (a column group) exit 2 and change nothing.
11. A resource `PORT` with values `5433`, `5434` and `max_lanes = 3`: `next` dispatches two tasks
    with `5433` and `5434` (with `environment.TASKRAIL_RESOURCE_PORT`), stored in the run, and
    reports `limited_by: "resource:PORT"`; once a lane is `done-branch` or recorded `failed`,
    the next `next` reports its value in `released`, clears it from that lane and allocates it again.
    Two resources are allocated together, and a task gets no values when it is not dispatched.
12. Two `next --run` calls on different runs, run concurrently, never allocate the same value or
    exceed `max_lanes` (both under the lock).
13. A task whose single dependency is `done-branch` is dispatched with `base.dependency` and
    `base.onto` naming that branch; a task whose `base.diverged` is true is skipped with reason
    `base diverged`; a task with two unmerged dependencies is not a candidate.
14. `next` without `--run` returns the same selection with `preview: true`, and the run files and
    their modification times are unchanged.
15. `status` reports a dispatched, unclaimed task as `dispatched` with its resources, and as
    `pending` once the dispatch expires; a claimed one is `running`.
16. The whole existing suite still passes; T029's `lane --group ui` test configures `ui` as a
    judgement group, the only change to an existing test.
17. `DESIGN.md` §4 lists the two tables and their checks, §12.1 marks `next` implemented with its
    rules and `lane --group`'s check, §12.4 adds `dispatched` to the run keys and states, §12.7
    defines occupied lanes and release, §12.9 and §12.10 mark T030 implemented; `README.md` shows
    the command; `CHANGELOG.md` has one bullet under *Unreleased*.

## Test coverage

In `tests/test_autopilot_next.py`: throwaway repositories with a local bare `origin`
and lanes in their own worktrees; no network. The tests were written before the implementation.
Against the code without T030 (only the test file and the one-line change to T029's test present),
`uv run pytest -q -p no:cacheprovider tests/test_autopilot_next.py` gave `36 failed in 5.72s`, each
test failing on its own assertion rather than at collection:

```
FAILED tests/test_autopilot_next.py::test_group_and_resource_configuration - ImportError: cannot import name 'GroupConfig' from 'taskrail.config' (…)
FAILED tests/test_autopilot_next.py::test_group_and_resource_errors_name_the_key[…] - Failed: DID NOT RAISE ConfigError   (20 cases)
FAILED tests/test_autopilot_next.py::test_next_is_refused_while_disabled_and_checks_the_run_and_backlog - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_next_dispatches_within_max_lanes_in_next_order - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_next_text_lists_each_dispatched_task - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_a_dispatch_holds_its_lane_until_it_is_claimed_or_expires - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_gate_and_escalated_occupy_a_lane_and_failed_does_not - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_lanes_and_dispatches_are_counted_across_runs - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_the_run_count_limits_dispatch - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_kinds_come_from_the_run_and_the_configuration - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_a_column_group_limits_its_lanes - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_a_judgement_group_follows_lane_group_records - assert (0 == 2)
FAILED tests/test_autopilot_next.py::test_resources_are_allocated_per_lane_and_released_when_it_ends - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_concurrent_dispatches_share_the_limits - AssertionError: usage: taskrail autopilot [-h] {start,lane,decision,status}...
FAILED tests/test_autopilot_next.py::test_stacked_bases_diverged_bases_and_blocked_tasks - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_next_without_a_run_is_a_preview - SystemExit: 2
FAILED tests/test_autopilot_next.py::test_status_reports_a_dispatched_task - SystemExit: 2
36 failed in 5.72s
```

(`SystemExit: 2` is argparse's `invalid choice: 'next'`; `assert (0 == 2)` is `lane --group nope`
being accepted.) After the implementation: `36 passed`, and the whole suite `505 passed`.

| Criterion | Tests |
|---|---|
| 1. Group and resource configuration | `test_group_and_resource_configuration`, `test_group_and_resource_errors_name_the_key` (20 cases) |
| 2. Disabled, unknown run, invalid backlog | `test_next_is_refused_while_disabled_and_checks_the_run_and_backlog` |
| 3. `max_lanes`, order, recorded dispatch, `show`'s fields | `test_next_dispatches_within_max_lanes_in_next_order`, `test_next_text_lists_each_dispatched_task` |
| 4. A dispatch holds its lane until claimed or expired | `test_a_dispatch_holds_its_lane_until_it_is_claimed_or_expires` |
| 5. `gate`, `escalated`, `failed`, `done-branch` | `test_gate_and_escalated_occupy_a_lane_and_failed_does_not`, `test_resources_are_allocated_per_lane_and_released_when_it_ends` |
| 6. Across runs | `test_lanes_and_dispatches_are_counted_across_runs` |
| 7. The run's count (Q3 as decided) | `test_the_run_count_limits_dispatch` |
| 8. Kinds (Q7 as decided) | `test_kinds_come_from_the_run_and_the_configuration` |
| 9. Column group | `test_a_column_group_limits_its_lanes` |
| 10. Judgement group and `lane --group` check | `test_a_judgement_group_follows_lane_group_records` |
| 11. Resources and lazy release | `test_resources_are_allocated_per_lane_and_released_when_it_ends`, `test_a_dispatch_holds_its_lane_until_it_is_claimed_or_expires` |
| 12. Concurrent dispatches | `test_concurrent_dispatches_share_the_limits` (two CLI processes started together) |
| 13. Stacked, diverged, doubly blocked | `test_stacked_bases_diverged_bases_and_blocked_tasks` |
| 14. Preview | `test_next_without_a_run_is_a_preview` |
| 15. `dispatched` in `status` | `test_status_reports_a_dispatched_task` |
| 16. Existing behaviour | the whole suite; `tests/test_autopilot.py::test_lane_records_handle_state_reason_and_group` now configures `ui` as a judgement group |
| 17. Documentation | reviewed at the implement gate: `DESIGN.md` §4, §7, §12 intro, §12.1, §12.4, §12.7, §12.9, §12.10; `README.md`; `CHANGELOG.md` |

As a further check, four rules were broken one at a time in `dispatch.py` (restored from a copy
afterwards, `cmp` identical) and the new tests run:

| Mutation | Tests that failed |
|---|---|
| a `failed` task frees its place in the count | `test_gate_and_escalated_occupy_a_lane_and_failed_does_not`, `test_the_run_count_limits_dispatch` |
| release does not clear a lane's `resources` | `test_resources_are_allocated_per_lane_and_released_when_it_ends` |
| kinds are the union instead of the intersection | `test_kinds_come_from_the_run_and_the_configuration` |
| `failed` occupies a lane | `test_gate_and_escalated_occupy_a_lane_and_failed_does_not`, `test_resources_are_allocated_per_lane_and_released_when_it_ends` |

Details the plan left open, settled in the implementation:

- `skipped` lists a task dispatched in the same run too (`dispatched in run R`), not only in
  another run; capacity is checked before each candidate, so tasks after the point where capacity
  ran out are neither dispatched nor listed.
- When several limits are exhausted at once, `limited_by` names the first of `max_lanes`, `count`,
  `resource:<NAME>` (in `[[autopilot.resource]]` order).
- The preview skips a task recorded `failed` in any run, since it has no run of its own.
- A lane in use is reported under the run its claim names when that run lists it, else the first
  run (newest first) where it is in use.
- `lane --group` checks the group after the run and the task, so an unknown run or task still
  exits 3 first.
- The text output also prints a `skipped` line per skipped task and a `released` line per release.
- The `lint` check the kind names is not configured in this repository's `[checks]`.

## Verification

### Real CLI

Run through this checkout's wrapper, `.taskrail/bin/taskrail --root <repo>`, in a throwaway
repository under `/tmp` with a bare `origin`; the repository was removed afterwards. Its config:
`[columns].custom = ["Area"]`, `max_lanes = 3`, a column group `ui` (`limit = 1`, `Area` matches
`ui`), a judgement group `db` (`limit = 1`) and a resource `PORT` with `5433` and `5434`. Five tasks:
T001 feature `ui` (1 pt), T002 bug `UI` (1 pt), T003 chore `api` (2 pts), T004 feature depending on
T001 (2 pts), T005 bug (3 pts). Output as printed:

```
$ taskrail autopilot next   # enabled = false
taskrail: the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot next`
exit=5

$ taskrail autopilot next   # preview, no run
T001   feature  T001-first-ui  base origin/main  PORT=5433
T003   chore    T003-api-work  base origin/main  PORT=5434
  skipped T002: group ui is full
dispatched 2 · 2/3 lanes in use · limited by resource:PORT · preview: nothing recorded
exit=0

$ taskrail autopilot start --count 3
20260913-1 exit=0

$ taskrail autopilot lane T003 --run 20260913-1 --group db
T003 in run 20260913-1: running
exit=0

$ taskrail autopilot lane T005 --run 20260913-1 --group db
T005 in run 20260913-1: running
exit=0

$ taskrail autopilot lane T005 --run 20260913-1 --group nope
taskrail: no judgement group `nope` in [[autopilot.group]] (judgement groups: db)
exit=2

$ taskrail autopilot lane T005 --run 20260913-1 --group ui
taskrail: group `ui` is computed from column Area; --group assigns only a group without column and match
exit=2

$ taskrail autopilot next --run 20260913-1 --json | jq (summary)
exit=0
{"dispatch":[{"id":"T001","groups":["ui"],"resources":{"PORT":"5433"},"environment":{"TASKRAIL_RESOURCE_PORT":"5433"},"branch":"T001-first-ui","worktree":".worktrees/T001-first-ui","base":"origin/main","commit":"02abcb1","decisions":"docs/autopilot/decisions/T001-first-ui.md","has_kind_descriptor":true,"prior_work":["artifact","branches","commits","commits_total"]},{"id":"T003","groups":["db"],"resources":{"PORT":"5434"},"environment":{"TASKRAIL_RESOURCE_PORT":"5434"},"branch":"T003-api-work","worktree":".worktrees/T003-api-work","base":"origin/main","commit":"02abcb1","decisions":"docs/autopilot/decisions/T003-api-work.md","has_kind_descriptor":true,"prior_work":["artifact","branches","commits","commits_total"]}],"skipped":[{"id":"T002","reason":"group ui is full"}],"limited_by":"resource:PORT","remaining":1,"lanes":{"free":1,"occupied":[["T001","dispatched",["ui"]],["T003","dispatched",["db"]]]},"groups":[["ui",["T001"],0],["db",["T003"],0]],"resources":[{"name":"PORT","values":["5433","5434"],"held":{"5433":"T001","5434":"T003"},"free":[]}],"released":[]}

$ taskrail autopilot next --run 20260913-1   # again at once
nothing to dispatch · 2/3 lanes in use · 1 more for run 20260913-1 · limited by resource:PORT
exit=0

$ taskrail autopilot status --run 20260913-1
run 20260913-1 · 0/3 done-merged · kinds: every allowed kind · started 2026-09-13T23:09:01+00:00 by orchestrator
  T003   dispatched   group db  idle 0m
  T005   pending      group db  idle 0m
  T001   dispatched 
  hand-off: next — · in review — · queue —
exit=0
$ run file tasks:
["T003","db",true,{"PORT":"5434"}]
["T005","db",false,{}]
["T001",null,true,{"PORT":"5433"}]
--- lane T001: worktree, claim --run, gate

$ taskrail claim T001 --run 20260913-1 (in the worktree)
claimed T001 as lane
exit=0

$ taskrail autopilot lane T001 --run 20260913-1 --state gate --reason plan gate
T001 in run 20260913-1: gate (plan gate)
exit=0

$ taskrail autopilot next --run 20260913-1   # T001 at a gate still holds its lane and value
nothing to dispatch · 2/3 lanes in use · 1 more for run 20260913-1 · limited by resource:PORT
exit=0
--- T001 marked done and committed on its branch

$ taskrail autopilot next --run 20260913-1   # T001 done-branch
T002   bug      T002-second-ui  base origin/main  PORT=5433
  released PORT=5433 from T001 (run 20260913-1)
dispatched 1 · 2/3 lanes in use · 0 more for run 20260913-1 · limited by count
exit=0

$ taskrail autopilot lane T003 --run 20260913-1 --state failed --reason tests hang
T003 in run 20260913-1: failed (tests hang)
exit=0

$ taskrail autopilot next --run 20260913-1   # T003 failed: keeps its place in the count, gives back its value
  released PORT=5434 from T003 (run 20260913-1)
nothing to dispatch · 1/3 lanes in use · 0 more for run 20260913-1 · limited by count
exit=0

$ taskrail autopilot next   # preview
T004   feature  T004-after-first  base T001-first-ui  PORT=5434
  skipped T002: dispatched in run 20260913-1
  skipped T003: failed in run 20260913-1
dispatched 1 · 2/3 lanes in use · limited by resource:PORT · preview: nothing recorded
exit=0

$ taskrail autopilot status --run 20260913-1
run 20260913-1 · 0/3 done-merged · kinds: every allowed kind · started 2026-09-13T23:09:01+00:00 by orchestrator
  T003   failed       group db  idle 0m  — tests hang
  T005   pending      group db  idle 0m
  T001   done-branch  idle 0m  — plan gate
  T002   dispatched 
  hand-off: next T001 · in review — · queue T001
exit=0
$ run file tasks:
["T003","failed","db",true,{}]
["T005","running","db",false,{}]
["T001","gate",null,true,{}]
["T002","running",null,true,{"PORT":"5433"}]

$ taskrail autopilot next --run 20000101-1
taskrail: no autopilot run `20000101-1`
exit=3
```

What this shows against the plan, with no gap found:

- `next` is refused with exit 5 while disabled, preview included, and exits 3 for an unknown run;
- the preview and the first `next --run` choose the same tasks in `taskrail next`'s order, and only
  the latter records `dispatched` and `resources`;
- the column group `ui` (matching `UI` case-insensitively) skips T002 while T001 holds it; the
  judgement group recorded with `lane --group db` puts T003 in `db`; `lane --group` refuses an
  unknown name and a column group with exit 2;
- each lane gets its own `PORT` value and `TASKRAIL_RESOURCE_PORT`, and dispatch stops at
  `resource:PORT`; a second `next` at once dispatches nothing;
- `status` reports the unclaimed lanes as `dispatched`; T001 at a gate keeps its lane and value;
  once it is `done-branch` its value is released and given to T002, and the run's count stops
  further dispatch;
- T003 recorded `failed` gives back its value but keeps its place in the count (Q3 as decided), and
  a preview skips it as failed; T004 is offered stacked on `T001-first-ui`.

Observed, not a gap: a `dispatched` lane with no `lane` update has no `idle_minutes` in `status`
(the dispatch time is not one of the moments T029 measures idle time from), so its text line shows
no `idle` part.

## Affected areas

- `src/taskrail/config.py` — `GroupConfig`, `ResourceConfig`,
  `AutopilotConfig.groups` and `.resources`; `_autopilot` receives the declared columns and
  aliases to resolve group columns.
- `src/taskrail/autopilot/dispatch.py` (new) — occupancy, candidates, capacity,
  group membership, allocation and release.
- `src/taskrail/autopilot/runs.py` — `update_all`, a context manager that takes the lock once and
  yields every run for reading and updating together (the lock is not re-entrant, and `next` reads
  every run and may clear resources in several); `dispatch_live`, the expiry rule `status` and
  `next` share; `dispatched` in the lane defaults.
- `src/taskrail/autopilot/commands.py` — `cmd_next` and its `add(...)` call; the
  group check in `cmd_lane`.
- `src/taskrail/autopilot/status.py` — the `dispatched` state (one branch in
  `task_state`, one entry in `STATES`), subject to Q6.
- Reused, not changed: `query.eligible`, `query.task_dict`, `query.base_dict`,
  `kinds.Kind.to_dict`, `prior.prior_work`, `predicates`, `claims.read_all`, `templates.render`,
  `ids.id_lock`.
- `DESIGN.md` §4, §12.1, §12.4, §12.7, §12.9, §12.10; `README.md`;
  `CHANGELOG.md`.
- `tests/test_autopilot_next.py` (new, so T031 and T032 editing
  `test_autopilot.py` do not conflict); one test in `tests/test_autopilot.py`.

## Out of scope

- Claiming, creating worktrees or launching lanes: claiming stays the lane's job.
- Allocating resources to a lane that becomes active again after it ended (a reopened or resumed
  failed lane): it keeps none; `status` shows its empty `resources`. A follow-up if the trial
  (T033) needs it.
- A resource for the orchestrator's own checks at hand-off (§12.8).
- `autopilot merged` (T031), `notify` and escalation flags (T032), the `taskrail-autopilot` skill
  (T024).
- Removing a judgement group from a lane, or changing `taskrail next`.

## Open questions and risks

Decisions for the plan gate, each with a recommendation. The gate decided Q3 and Q7 differently
(marked below) and every other question as recommended; the record is
`docs/autopilot/decisions/T030-dispatch-autopilot-lanes-with-autopilot.md`.

- **Q1 — What occupies a lane?** Recommended: derived `running` (stale claims included, reported
  with their stale reason, since the task is still blocked), `gate`, `escalated`, and a dispatch
  not yet claimed within the grace. Alternatives: also `failed` (a run with `max_lanes` failures
  stalls with no command to free it); only live claims (a stale claim or a lane between `next` and
  its claim would be dispatched over).
- **Q2 — Scope of `max_lanes` and group limits.** Recommended: every run in the clone, since both
  are repository settings and resource pools are necessarily clone-wide; two orchestrators then
  share three lanes. Alternative: per run (two orchestrators double the lanes and can break "one
  UI lane"). Claims without a run are not lanes and occupy nothing, but their tasks stay
  ineligible.
- **Q3 — The run's `count` in dispatch.** §12.1 does not list it. *Decided (changed from the
  recommendation):* dispatch at most the remaining target; a `discarded` task frees its place, a
  `failed` task keeps counting, since it keeps its claim and waits for a human, and replacing it
  would start more work than the human asked for.
- **Q4 — What `next` records.** Recommended: `dispatched` and `resources` per task. Without a
  record, a second `next` before the lanes claim — minutes, while each lane reads its skills and
  creates a worktree — would offer the same tasks again and exceed `max_lanes`. The dispatch
  expires after `[git].claim_grace_minutes` without a claim, the same grace a claim's missing
  branch gets, so a lane that was never launched does not hold a lane forever. Alternatives: a
  separate `[autopilot]` key for the expiry; no expiry (a leaked dispatch needs a new command to
  clear it); record nothing (double dispatch).
- **Q5 — When resources are released.** §12.7 says "when the lane ends" without defining it.
  Recommended: a lane holds values while it occupies a lane (Q1); `next` releases lazily, under
  the lock, by clearing the `resources` of every lane in any run that no longer occupies one, and
  reports them in `released`. Release has to be lazy anyway, because `done-branch` and
  `done-merged` are derived from git, with no autopilot command at those transitions. Clearing
  (rather than only ignoring old values) keeps a failed lane resumed later, or a reopened task,
  from holding a value already given to another lane. *Decided as recommended*, and §12.7 states
  that the orchestrator re-runs a lane's checks — at a gate or at hand-off (§12.8) — before its
  next `next`, while the lane's value is still held. Alternatives: hold until `done-merged` or
  `discarded` (the sequential review queue then starves the pools); release also on
  `lane --state failed` (a second release point for the same rule).
- **Q6 — `dispatched` in `status`.** Recommended: yes, a one-branch change in `status.py`, which
  the lane brief did not list; without it `status` shows a dispatched lane as `pending` with
  resources. Alternative: leave `status` unchanged and rely on `next`'s output.
- **Q7 — Allowed kinds.** *Decided (changed from the recommendation):* the intersection of the
  run's `kinds` and `[autopilot].kinds` when both are set — the configuration limits what the
  autopilot may drive, and a run may narrow it, never widen it; whichever is set otherwise; every
  allowed kind when neither is. An empty intersection dispatches nothing.
- **Q8 — Stacked bases and blocked tasks.** Recommended: reuse `query.eligible`, so a single
  unmerged dependency gives a stacked base and anything else blocked is not a candidate; skip a
  diverged or missing base with its reason, since the lane would stop at step 3 and §12.6 makes a
  diverged base an escalation. A task recorded `failed` in run R is skipped even when its claim
  was released, so the run does not retry it on its own; another run may.
- **Q9 — Judgement groups before a lane exists.** Recommended: the orchestrator judges the
  candidates (from a preview, Q10) and assigns them with `lane <ID> --run R --group G` before
  `next --run R`, which honours the recorded group; an unassigned candidate counts only toward
  column groups. `lane --group` checks the name (exit 2 for an unknown name or a column group),
  changing T029's "stored as given" and its test. Alternatives: `next --group T003=db` flags
  (a second way to write the same record); report judgement groups and let the orchestrator skip
  (`next` would already have allocated and recorded the dispatch); keep storing any name (a typo
  silently disables a limit).
- **Q10 — `next` without `--run`.** Recommended: a preview that writes nothing, for
  `[autopilot].kinds` and with no target, and is refused with exit 5 like the rest of dispatch
  while the autopilot is disabled. Alternatives: use the newest run (an orchestrator could dispatch
  into another session's run by omission); allow the preview while disabled.
- **Q11 — Exit codes.** Recommended: 5 disabled (first), 1 invalid backlog, 3 unknown run, 4 lock
  timeout, 0 with an empty dispatch — `taskrail next` also exits 0 with nothing eligible.
- **Q12 — Group and resource name rules.** Recommended as in *Behaviour*: group names like kind
  names, resource names as environment-variable suffixes, values strings only (a port is
  written `"5433"`, as in §12.9). Alternative: accept integer values and convert them.
- **§12 wording.** §12.1 says "`show`'s fields plus `base.commit`", but `show`'s `base` already
  carries `commit` (T017); §12.1 will say so instead of implying a second field.

Risks:

- **Parallel lanes.** T031 and T032 add modules to `autopilot/` and edit `commands.py`,
  `status.py` and DESIGN.md §12.1; this task adds one handler, one `add` call, one `task_state`
  branch and its own rows, so conflicts should be both-sides additions. T036 edits
  DESIGN.md §4 near `[git]`; this task edits §4's `[autopilot]` block.
- **Cost.** `next` computes `show` for each dispatched task, `prior_work` included, and derives the
  state of every run task; fine for a handful of lanes.
- **Clock.** Dispatch expiry compares the local clock with a timestamp written on the same
  machine; run files are local, so no cross-machine skew.

## Evidence

On this branch's base (`2312a2a`), in a throwaway repository under `/tmp` with `[autopilot]`
enabled, `[columns].custom = ["Area"]`, a group with `limit = "one"` and `column = "Nope"`, and a
resource with `values = []`; the repository was removed afterwards:

```
$ taskrail validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
$ taskrail autopilot next
usage: taskrail autopilot [-h] {start,lane,decision,status} ...
taskrail autopilot: error: argument autopilot_command: invalid choice: 'next' (choose from start, lane, decision, status)
exit=2
$ taskrail autopilot next --run 20260913-1
usage: taskrail autopilot [-h] {start,lane,decision,status} ...
taskrail autopilot: error: argument autopilot_command: invalid choice: 'next' (choose from start, lane, decision, status)
exit=2
$ taskrail autopilot start --count 1
20260913-1
exit=0
$ taskrail autopilot lane T001 --run 20260913-2 --group no-such-group --json
{
  "run": "20260913-2",
  "task": {
    "id": "T001",
    "handle": null,
    "group": "no-such-group",
    "state": "running",
    "reason": null,
    "updated": "2026-09-13T22:49:25+00:00",
    "resources": {}
  },
  "handed_off": []
}
exit=0
```

The suite on the base: `469 passed`.
