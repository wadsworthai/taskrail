# T029 — Add the autopilot configuration, runs, and the start, lane and status commands

Kind: feature · Epic: E02 · Status: verified

Source: the accepted autopilot design, `DESIGN.md` §12 (§12.1 *Skill and CLI*,
§12.2 *Installation and opt-in*, §12.4 *State*, §12.9 *Configuration*, §12.10 *Delivery*), and
the evidence behind it in `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md`. Builds
on T017 (`done-branch`, stacked bases, `base` in the claim, `Claim.from_dict`). The plan-gate
decisions are in `docs/autopilot/decisions/T029-add-the-autopilot-configuration-runs-and.md`.

## Behaviour

Before this change there was no `autopilot` command (`taskrail autopilot start --count 1` exits 2
with `invalid choice: 'autopilot'`), and an `[autopilot]` table in `.taskrail/config.toml` was
ignored without any check, even `enabled = "yes"` or `max_lanes = -1` (see *Evidence*). An
orchestrator kept the state of its lanes only in its own context.

After this change:

- **Configuration.** `.taskrail/config.toml` accepts an `[autopilot]` table with every
  single-value key of §12.9 — `enabled`, `max_lanes`, `kinds`, `governing`, `escalate_gates`,
  `decisions`, `decisions_index`, `silent_minutes`, `handoff`, `notify`, `notify_on` (Q1) — with
  §12.9's defaults, checked when the config loads: a wrong type or value exits 2 and names the key.
  `max_lanes`, `governing`, `escalate_gates`, `notify` and `notify_on` take effect with T030 and
  T032; the `group` and `resource` tables stay with T030, which reuses T020's column predicate.
- **Runs.** `taskrail autopilot start --count N [--kinds a,b]` creates a run file at
  `$(git rev-parse --git-common-dir)/taskrail/runs/<run>.json`, local and never committed, and
  prints the run ID, `YYYYMMDD-N`: the UTC date and the first number of that day no run holds
  (Q2). The file holds `id`, `started`, `owner`, `count`, `kinds`, `tasks` (per task: `handle`,
  `group`, `state`, `reason`, `updated`, `resources`), `handed_off` and `decisions`. It is created
  exclusively, so concurrent starts take the next free number; updated under the common-directory
  lock `reserve-id` already uses and replaced atomically; and read keeping keys this version does
  not know. Run files are written only by the CLI.
  - Unless `[autopilot].enabled` is `true`, `start` exits 5 naming `[autopilot].enabled` and
    creates nothing. That check comes first, so a disabled repository always gives the refusal
    the skill stops on, even without `--count`.
  - Without `--count`, or with a count below 1, it exits 2.
  - `--kinds` defaults to `[autopilot].kinds`; every kind named must be one the project resolves
    (defined and allowed), otherwise exit 2. An empty list means every allowed kind.
  - An invalid backlog exits 1, as for other commands.
- **`run` in the claim (Q3).** `taskrail claim <ID> --run R` records `run: "R"` in the claim, and
  exits 3 without claiming when run R does not exist. A claim without `--run` records `run: null`;
  a claim file without `run` still loads; the remote claim copy carries `run`, which names no
  machine detail. The claim also lists the task in the run file, so the task stays a member of the
  run after `done` releases the claim.
- **`taskrail autopilot lane <ID> --run R [--handle H] [--group G] [--state …] [--reason …]`**
  records the orchestrator's view of one lane in the run file and prints the lane. An unknown run
  or task exits 3.
  - `--state` takes `running`, `gate`, `escalated`, `failed` or `handed-off`.
  - `--reason` is required with `failed` and `escalated` (exit 2 without), optional with `gate`,
    and cleared by `running`; a reason for a running lane exits 2 (Q5).
  - `--group` is stored as given; T030 checks it against configured groups (Q6).
  - `failed` changes nothing in the claim, so the task stays ineligible and its dependents stay
    blocked.
  - `handed-off` appends the task to the run's hand-off order once, keeping that order, and exits
    5 unless the task is `done-branch` (Q4).
  - `lane` does not require `enabled`: only `start` is gated.
- **`taskrail autopilot decision --run R --question … --decision … --reason …`** appends a
  numbered run-level decision (`number`, `question`, `decision`, `reason`, `recorded`) to the run
  file (Q4). An empty value exits 2; an unknown run exits 3.
- **`taskrail autopilot status [--run R] [--fetch]`** reports every run, newest first, each with
  `complete` once `count` of its tasks are `done-merged`, `done_merged`, and its `decisions` (Q7).
  For each run task — one the run file lists or whose claim names the run:
  - `state`, derived with this precedence: `done-merged` (the row is `✅` on the local mainline
    or `<remote>/<mainline>`), `discarded` (`❌`, Q8), `handed-off` (done on its branch and in the
    run's hand-off order), `done-branch` (T017), then the recorded `failed`, `escalated` or
    `gate`, then `running` (a claim of this task, stale or not), then `pending`, with
    `blocked_by`;
  - the lane's `handle`, `group`, `reason` and `resources` (empty until T030), its `branch` and
    `worktree` (from the claim, else T019's `branches.task_branch` — a recorded name, else the
    kind's template — and the worktree `gitutil.worktree_branches` finds it checked out in), and the claim with its `stale` reason, if any (Q8);
  - `idle_minutes`: minutes since the latest of the branch tip's commit time, the modification
    time of any file `git status` reports changed in the worktree, the claim's creation and the
    lane's last `lane` update; `silent` is true when a `running` lane is idle past
    `[autopilot].silent_minutes`. A lane stopped at a gate, escalated or failed is never silent;
  - `touched`: files changed on the branch since its fork point — `git merge-base` with the base
    the claim recorded, or with `show`'s base once the claim is released — plus uncommitted
    changes in its worktree (Q9). A stacked branch does not list its dependency's files;
  - `decisions` and `decisions_index`, rendered from `[autopilot]` for the task.

  Across all reported runs, `overlaps` maps each file touched by more than one lane to their IDs,
  backlog files and changelogs included (Q9). Per run, `handoff` gives `mode` (`sequential`),
  `in_review` (a handed-off task not yet `done-merged`), `queue` (`done-branch` tasks not handed
  off: dependencies first, then by the branch tip's commit time) and `next` (the head of the
  queue, or `null` while a branch is in review). `status` reads local git only; `--fetch` first
  fetches each backlog mainline's remote and reports the remotes in `fetched`. It needs no
  `enabled`, exits 3 for an unknown `--run`, reports no runs as an empty list with exit 0, and
  like `list` refuses an invalid backlog with exit 1 unless `--allow-invalid`.
- **Code shape for the next tasks.** A new package `taskrail/autopilot/`: `runs.py` (run files),
  `status.py` (derived states, activity, touched files, hand-off queue), `commands.py` (argparse
  registration and handlers for `start`, `lane`, `decision`, `status`). T030 (`next`), T031
  (`merged`) and T032 (`notify`) each add a module, a handler and one `add` call in `register`,
  without restructuring. `cli.py` only registers the group and handles `claim --run`.

## Acceptance criteria

1. Without `[autopilot]`, the loaded config has `enabled` false and §12.9's defaults for every
   single-value key; a table with every key set loads them all. Each of these exits 2 from any
   command and names the key: a non-table `[autopilot]`; a value of the wrong type; `max_lanes`
   below 1; negative `silent_minutes`; `handoff` other than `sequential`; a `kinds` entry that is
   not a kind name; an `escalate_gates` entry not shaped `kind:stage`; a `notify_on` value outside
   `escalation`, `lane-done`, `lane-failed`; a `decisions` template with an unknown placeholder.
2. `autopilot start --count 2`, with `enabled` absent or `false`, exits 5, stderr names
   `[autopilot].enabled`, and no `runs` directory exists afterwards; without `--count` it still
   exits 5.
3. With `enabled = true`: no `--count`, `--count 0` or `--count -1` exits 2 and writes nothing.
4. With `enabled = true`, `start --count 2 --json` exits 0 and the run file under the git common
   directory holds the ID printed (`<UTC date>-1`), `count` 2, `kinds` `[]`, `started`, `owner`,
   empty `tasks`, `handed_off` and `decisions`; a second `start` returns `-2`; `start` run inside a
   task worktree writes into the same common directory; the text form prints only the ID. Starts on
   the same UTC day take consecutive numbers, the next day starts again at 1, and runs list newest
   first.
5. `start --kinds bug,chore` stores those kinds; `--kinds nope`, or a kind `[kinds].allowed`
   excludes, exits 2 and writes nothing; without `--kinds`, `[autopilot].kinds` is stored and
   checked the same way. With an invalid backlog `start` exits 1 and writes nothing.
6. `claim T001 --run R` records `run: "R"` and lists T001 in the run file; `claim --run` for an
   unknown run exits 3 and writes no claim; a claim without `--run` records `run: null`; the remote
   claim copy carries `run`; a claim file without `run` loads.
7. `lane T001 --run R --handle H1 --state gate --reason "plan gate" --json` records all three with
   `updated`; a later `lane T001 --run R --state running --group ui` keeps `H1`, clears the reason
   and stores the group; `--state failed` or `escalated` without `--reason`, and `--reason` with
   `--state running`, exit 2; `--state failed --reason …` leaves the claim file unchanged; an
   unknown run, an unknown task or a run ID that is not `YYYYMMDD-N` exits 3; keys the run file
   holds that this version does not know survive a `lane` update.
8. `lane --state handed-off` exits 5 for a task that is not `done-branch`; for done-branch tasks
   handed off as T004, T003, T004, the run's hand-off order is `["T004", "T003"]`.
9. `autopilot decision` appends numbered entries with `question`, `decision`, `reason` and
   `recorded`, and `status` reports them; an empty value exits 2, a missing flag exits 2, and an
   unknown run exits 3.
10. `status --run R --json` reports each state in a scenario built for it: `pending` (listed, no
    claim, with `blocked_by`), `running` (a claim naming R), `gate`, `escalated` (with its reason),
    `failed`, `done-branch`, `handed-off`, `done-merged` (`✅` on `main`, and separately only on
    `origin/main` after a fetch), `discarded`; a task recorded `failed` but done on its branch
    reports `done-branch`; a run whose `count` tasks are `done-merged` is `complete`. A claim whose
    worktree was removed stays `running` and shows its stale reason.
11. A `running` lane whose branch tip, worktree files, claim and lane update are all older than
    `silent_minutes` is `silent` with `idle_minutes` above it; a worktree file modified five minutes
    ago makes it not silent with `idle_minutes` 5; the same lane recorded at `gate` is never silent.
12. Two lanes changing the same file, one committed on its branch and one uncommitted in its
    worktree, both list it in `touched` and `overlaps` names it with both IDs; a lane stacked on
    an unmerged dependency does not list the dependency's files.
13. With two `done-branch` tasks, one depending on the other and finished later than its
    dependent's tip, `handoff.queue` lists the dependency first and `next` is it; after it is
    handed off, `in_review` is it and `next` is `null`; once its row is `✅` on `main`, `next` is
    the other task.
14. `decisions` and `decisions_index` are rendered for each task from the defaults, and from custom
    `[autopilot]` templates.
15. `status` without runs prints an empty list (`no autopilot runs` in text) and exits 0; `--run X`
    for an unknown run exits 3; `status` lists every run newest first with `complete`, in JSON and
    text; without `--fetch` it does not update `origin/main` after the remote moved, and with
    `--fetch` it does; `lane`, `decision` and `status` work while `enabled` is `false`; an invalid
    backlog exits 1 unless `--allow-invalid`.
16. The whole existing suite still passes; the only change to existing output is the claim's new
    `run` key.
17. `DESIGN.md` §4 lists the `[autopilot]` keys, §6.1 and §6.2 the claim's `run`, §7 the new
    commands and `claim --run`, and §12 marks what T029 implemented, with `handed-off`, `decision`
    and `discarded` in §12.1; `README.md` shows the commands; `CHANGELOG.md` has one bullet under
    *Unreleased*.

## Test coverage

In `tests/test_autopilot.py`: throwaway repositories with a local bare `origin` and
lanes in their own worktrees; no network. Against the base code the file fails at collection
(`ModuleNotFoundError` for `taskrail.autopilot`); after the implementation it has 39 passing tests, and 41 after the rebase onto T019.

| Criterion | Tests |
|---|---|
| 1. Configuration defaults, keys and errors | `test_autopilot_configuration_defaults`, `test_autopilot_configuration_reads_every_single_value_key`, `test_autopilot_configuration_errors_name_the_key` (12 cases) |
| 2. `start` refused while disabled | `test_start_is_refused_until_the_autopilot_is_enabled` |
| 3. `--count` required and positive | `test_start_needs_a_positive_count` |
| 4. Run file, IDs, worktrees, ordering | `test_start_creates_a_run_file_in_the_common_directory`, `test_concurrent_starts_take_the_next_free_number` |
| 5. Kinds; invalid backlog | `test_start_stores_and_checks_kinds`, `test_start_refuses_an_invalid_backlog` |
| 6. `claim --run` | `test_claim_records_the_run`, `test_claim_run_on_the_template_branch_still_records_the_branch` (after T019), `test_the_remote_claim_carries_the_run`, `test_claim_files_without_a_run_still_load` |
| 7. `lane` records | `test_lane_records_handle_state_reason_and_group`, `test_run_files_keep_keys_this_version_does_not_know` |
| 8. `handed-off` | `test_handed_off_needs_done_branch_and_keeps_the_order` |
| 9. `decision` | `test_decision_appends_to_the_run` |
| 10. Derived states | `test_status_derives_every_state`, `test_a_stale_claim_stays_running_with_its_reason` |
| 11. Silent lanes | `test_a_running_lane_idle_past_silent_minutes_is_silent` |
| 12. Touched files and overlaps | `test_touched_files_and_overlaps_between_lanes`, `test_a_stacked_lane_does_not_list_its_dependency_files` |
| 12a. Branch lookup after T019 (a renamed branch) | `test_status_follows_a_renamed_task_branch` |
| 13. Hand-off queue | `test_handoff_queue_puts_dependencies_first` |
| 14. Decision record paths | `test_status_renders_decision_record_paths` |
| 15. `status` edges | `test_status_without_runs_and_for_an_unknown_run`, `test_status_lists_every_run_newest_first`, `test_status_fetches_only_when_asked`, `test_status_lane_and_decision_work_while_disabled`, `test_status_refuses_an_invalid_backlog_unless_allowed` |
| 16. Existing behaviour | the whole suite, 339 passed before T019 and 410 after the rebase onto it; one existing assertion gained only the new key (below) |
| 17. Documentation | reviewed at the implement gate: `DESIGN.md` §4, §6.1, §6.2, §7, §12.1, §12.2, §12.4, §12.9, §12.10; `README.md`; `CHANGELOG.md` |

Existing test changed: `tests/test_claims.py::test_remote_claim_does_not_publish_machine_details`
lists the public claim's keys, which gained `run`.

Deviations from the plan's wording:

- `claim --run` also lists the task in the run file. Without it, a lane that claims with `--run`
  and finishes before the orchestrator calls `lane` would drop out of `status` once `done`
  releases the claim, since membership came only from the run file or a live claim.
- `status` reports `done_merged` (the count) per run and `fetched` (the remotes fetched) at the top
  level; a run task whose ID is no longer in the backlog is reported with `state: null` and
  `problem: "not in the backlog"` instead of being dropped.
- Criterion 1 also covers a `decisions` template with an unknown placeholder, which would otherwise
  fail only when `status` renders it.
- §6.2 names `run` among the remote claim's fields.

## Verification

### Real CLI

Run through this checkout's wrapper, `.taskrail/bin/taskrail --root <repo>`, in a throwaway
repository under `/tmp` with a bare `origin`, lanes in `.worktrees/`, and T001 squash-merged on
`origin/main` by a second clone; the repository was removed afterwards. Four tasks: T001, T002
depending on T001, T003, and T004 discarded. Output as printed (git's own `Squash commit -- not
updating HEAD` line from the second clone is left out):

```

$ taskrail autopilot start --count 2   # [autopilot] absent
taskrail: the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot start`
exit=5

$ taskrail autopilot start             # still disabled, no count
taskrail: the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot start`
exit=5

$ taskrail validate                    # max_lanes = 0
taskrail: .taskrail/config.toml: autopilot.max_lanes must be at least 1
exit=2

$ taskrail autopilot start             # enabled, no count
taskrail: autopilot start needs --count N, the number of tasks to complete
exit=2

$ taskrail autopilot start --count 2 --kinds nope
taskrail: --kinds: kind `nope` is not defined (known: bug, chore, feature, spike)
exit=2

$ taskrail autopilot start --count 2
20260913-1 exit=0
run file: 20260913-1.json

$ taskrail claim T001 --run 20000101-1 (unknown run)
taskrail: no autopilot run `20000101-1`
exit=3

$ taskrail claim T001 --run 20260913-1
claimed T001 as abigail@archlinux
exit=0

$ taskrail claim T003 --run 20260913-1
claimed T003 as abigail@archlinux
exit=0

$ taskrail autopilot lane T001 --run 20260913-1 --handle agent-1 --state gate --reason 'plan gate'
T001 in run 20260913-1: gate (plan gate)
exit=0

$ taskrail autopilot lane T003 --run 20260913-1 --handle agent-3 --state failed
taskrail: --state failed needs --reason
exit=2

$ taskrail autopilot lane T003 --run 20260913-1 --handle agent-3 --group ui
T003 in run 20260913-1: running
exit=0

$ taskrail autopilot decision --run 20260913-1 --question 'Touch map' --decision 'T001 owns shared.txt' --reason 'one writer'
decision 1 recorded in run 20260913-1
exit=0

$ taskrail autopilot status
run 20260913-1 · 0/2 done-merged · kinds: every allowed kind · started 2026-09-13T22:23:07+00:00 by abigail@archlinux
  T001   gate         handle agent-1  idle 0m  — plan gate
  T003   running      handle agent-3  group ui  idle 0m
  hand-off: next — · in review — · queue —
files touched by more than one lane:
  shared.txt: T001, T003
exit=0

$ taskrail autopilot status --json | jq '.overlaps, [.runs[0].tasks[] | {id, state, handle, group, reason, touched, idle_minutes, silent}]'
{"shared.txt":["T001","T003"]}
{"id":"T001","state":"gate","handle":"agent-1","group":null,"reason":"plan gate","touched":["shared.txt"],"idle_minutes":0,"silent":false}
{"id":"T003","state":"running","handle":"agent-3","group":"ui","reason":null,"touched":["shared.txt"],"idle_minutes":0,"silent":false}

$ taskrail autopilot lane T003 --run 20260913-1 --state handed-off   # T003 not done-branch
taskrail: T003 is not done on its branch (done-branch), so it cannot be handed off
exit=5
(T001 marked done and committed on its branch; its claim is released)

$ taskrail autopilot status --json | jq T001 and handoff
{"id":"T001","state":"done-branch","claim":null,"touched":["TODO.md","shared.txt"]}
{"mode":"sequential","in_review":null,"queue":["T001"],"next":"T001"}

$ taskrail autopilot lane T001 --run 20260913-1 --state handed-off
T001 in run 20260913-1: gate (plan gate); handed off (1 of 1)
exit=0

$ taskrail autopilot status --json | jq handoff
{"mode":"sequential","in_review":"T001","queue":[],"next":null}

$ taskrail claim T002 --run 20260913-1   # stacked on T001's branch
claimed T002 as abigail@archlinux
exit=0

$ taskrail autopilot status --json | jq T002
{"id":"T002","state":"running","touched":["stacked.txt"],"decisions":"docs/autopilot/decisions/T002-stacked.md","decisions_index":"docs/autopilot/decisions/README.md"}

$ taskrail autopilot status --json | jq T001 state   # merged on origin, not fetched
[[],"handed-off",{"mode":"sequential","in_review":"T001","queue":[],"next":null}]

$ taskrail autopilot status --fetch --json | jq
[["origin"],"done-merged",1,false,{"mode":"sequential","in_review":null,"queue":[],"next":null}]

$ taskrail autopilot start --count 1   # disabled again
taskrail: the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot start`
exit=5

$ taskrail autopilot status --run 20260913-1   # still works while disabled
run 20260913-1 · 1/2 done-merged · kinds: every allowed kind · started 2026-09-13T22:23:07+00:00 by abigail@archlinux
  T001   done-merged  handle agent-1  idle 0m  — plan gate
  T003   running      handle agent-3  group ui  idle 0m
  T002   running      idle 0m
  hand-off: next — · in review — · queue —
exit=0

$ taskrail autopilot status --run 20000101-1
taskrail: no autopilot run `20000101-1`
exit=3

run file:
{
  "id": "20260913-1",
  "started": "2026-09-13T22:23:07+00:00",
  "owner": "abigail@archlinux",
  "count": 2,
  "kinds": [],
  "tasks": {
    "T001": {
      "handle": "agent-1",
      "group": null,
      "state": "gate",
      "reason": "plan gate",
      "updated": "2026-09-13T22:23:09+00:00",
      "resources": {}
    },
    "T003": {
      "handle": "agent-3",
      "group": "ui",
      "state": "running",
      "reason": null,
      "updated": "2026-09-13T22:23:08+00:00",
      "resources": {}
    },
    "T002": {
      "handle": null,
      "group": null,
      "state": "running",
      "reason": null,
      "updated": null,
      "resources": {}
    }
  },
  "handed_off": [
    "T001"
  ],
  "decisions": [
    {
      "number": 1,
      "question": "Touch map",
      "decision": "T001 owns shared.txt",
      "reason": "one writer",
      "recorded": "2026-09-13T22:23:08+00:00"
    }
  ]
}
removed /tmp/t029-verify.VjiE
```

What this shows against the plan, with no gap found:

- the refusal names `[autopilot].enabled` and comes before the `--count` check; config errors,
  `--count` and `--kinds` exit 2; the run ID is `YYYYMMDD-N`;
- `claim --run` refuses an unknown run with exit 3 and lists the task in the run, so T002, claimed
  but never passed to `lane`, is in the run file;
- `status` reports `gate`, `running`, `done-branch` once T001 is done and its claim released,
  then `handed-off` and `done-merged` only after `--fetch`; `touched` and `overlaps` include
  uncommitted files and T001's `TODO.md`, and stacked T002 lists only its own file;
- the hand-off queue moves from `next: T001` to `in_review: T001` to empty once merged;
- `lane --state handed-off` is refused with exit 5 for T003, which is not `done-branch`; a
  `failed` state without `--reason` exits 2;
- `status` and `lane` keep working while `enabled = false`, and the run file holds exactly what
  was recorded.

`silent` needs a lane idle for longer than `silent_minutes` (at least a minute), so it was not
waited for here; `test_a_running_lane_idle_past_silent_minutes_is_silent` covers it with a clock
two hours ahead.

After the real-CLI run, a lane's recorded `state` and `reason` stay in the text line of a task
whose derived state has moved on (`T001 done-merged … — plan gate`), as the plan describes: the
run file keeps the orchestrator's last record, and the derived state takes precedence.

### The tests catch broken behaviour

The tests were written after the code, so at the implement gate the orchestrator asked to break
three behaviours one at a time and show that the matching tests fail. Each change was made in the
working tree, the autopilot tests were run with `uv run pytest -q --tb=line tests/test_autopilot.py`
(from the repository root; ANSI colours and the progress line removed below), and the file was
restored with `git checkout`. Nothing broken was committed.

(a) `autopilot start` no longer refuses while disabled:

```
-    if not config.autopilot.enabled:
+    if False and not config.autopilot.enabled:  # MUTATION (a)
E   assert 0 == 5
.../tests/test_autopilot.py:200: assert 0 == 5
E   assert 0 == 5
.../tests/test_autopilot.py:598: assert 0 == 5
FAILED tests/test_autopilot.py::test_start_is_refused_until_the_autopilot_is_enabled
FAILED tests/test_autopilot.py::test_status_lane_and_decision_work_while_disabled
2 failed, 37 passed in 4.54s
```

(b) A recorded `gate`, `escalated` or `failed` is checked before `done-branch` (the two blocks of
`task_state` swapped):

```
-    if task.id in stack.done_on_branch(project):
-        return "handed-off" if task.id in run["handed_off"] else "done-branch"
-    lane = run["tasks"].get(task.id)
+    lane = run["tasks"].get(task.id)  # MUTATION (b)
+    if task.id in stack.done_on_branch(project):
+        return "handed-off" if task.id in run["handed_off"] else "done-branch"
E   AssertionError: assert ('failed', 'gate') == ('done-branch', 'handed-off')
      At index 0 diff: 'failed' != 'done-branch'
.../tests/test_autopilot.py:429: AssertionError: assert ('failed', 'gate') == ('done-branch', 'handed-off')
FAILED tests/test_autopilot.py::test_status_derives_every_state - AssertionEr...
1 failed, 38 passed in 4.24s
```

T003 was recorded at `gate` and then finished and handed off: the broken precedence reports `gate`
instead of `handed-off`, and T001, recorded `failed`, reports `failed` instead of `done-branch`.

(c) `lane --state handed-off` accepted for a task that is not `done-branch`:

```
-    if handed_off and task.id not in stack.done_on_branch(project):
+    if False and handed_off and task.id not in stack.done_on_branch(project):  # MUTATION (c)
E   assert (0 == 5)
.../tests/test_autopilot.py:366: assert (0 == 5)
FAILED tests/test_autopilot.py::test_handed_off_needs_done_branch_and_keeps_the_order
1 failed, 38 passed in 4.69s
```

After restoring the files, `git status --short` was empty and the full suite passed again:
`339 passed in 21.67s`.

### After rebasing onto T019

T019 (`1543057`) merged while this branch waited, replacing `stack.task_branch` with
`branches.task_branch` and adding `gitutil.worktree_branches`. At the rebase, `status.py` switched
to both and dropped its own worktree listing (T019's returns `Path` values, rendered as strings in
`status`); `claim` keeps T019's branch freeze and warning and then lists the task in the run. Two
tests were added: `claim --run` on the template branch still reports `branch_recorded: true`, a
recorded `branch_source` and the task in the run; and `status` of a finished lane whose branch was
renamed with `taskrail branch` reports `done-branch` on the new name, its worktree and its files.
Conflicts were all both-sides additions: the two indexes, the changelog, the §7 claim row next to
T019's `branch` row, `cli.py`'s imports and the end of `cmd_claim`. After it:
`uv run pytest -q` gave `410 passed`, `taskrail validate` gave
`36 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`, and `taskrail upgrade --json` created,
updated and removed nothing.

## Affected areas

- `src/taskrail/autopilot/` (new package): `__init__.py`, `runs.py`, `status.py`,
  `commands.py`.
- `src/taskrail/config.py` — `AutopilotConfig`, `Config.autopilot`, and
  `_autopilot`, its parsing and checks.
- `src/taskrail/claims.py` — `Claim.run` and the `run` argument of `claim()`.
- `src/taskrail/cli.py` — `claim --run` (check the run, record it, list the task in
  the run) and one call registering the `autopilot` group in `build_parser`.
- Reused, not changed: `stack.done_on_branch`, `branches.task_branch` and
  `gitutil.worktree_branches` (T019), `stack._read_statuses`,
  `query.base_dict`, `query.blocked_by`, `review.resolve_remote`, `ids.id_lock`,
  `templates.render`, `claims.stale_reason`, `cli._emit`, `cli._load`, `cli._refuse_if_invalid`.
- `DESIGN.md` §4, §6.1, §6.2, §7 and §12; `README.md`;
  `CHANGELOG.md`.
- `tests/test_autopilot.py` (new); `tests/test_claims.py` (one
  assertion).

## Out of scope

- `autopilot next`, kinds filtering at dispatch, `max_lanes` enforcement, `[[autopilot.group]]`
  and `[[autopilot.resource]]` tables, checking `--group` names, resource allocation (T030).
- `autopilot merged`, content-based merge detection and cleanup (T031); until then `done-merged`
  is only `✅` on a mainline ref.
- `autopilot notify` and the escalation flags in `status` — governing files touched,
  `escalate_gates` (T032).
- The `taskrail-autopilot` skill and its integration notes (T024); the core skill is unchanged.
- Removing or archiving old runs.
- T019's branch naming and T020's conditional stages.

## Decisions and risks

The plan gate settled Q1–Q9 as recommended, with one addition to Q4 (the `decision` command); the
record is `docs/autopilot/decisions/T029-add-the-autopilot-configuration-runs-and.md`.

Risks:

- **Parallel lanes.** T019 changes branch lookup in `claims.py` and `cli.py`'s claim path, where
  this task adds `run` and `--run`: small textual conflicts are likely, resolved at rebase.
  `status` used `stack.task_branch` rather than a lookup of its own, so it followed T019's change.
  T020 edits one sentence in §12.7; this task changes §12's heading, status line, §12.1, §12.2,
  §12.4, §12.9 and §12.10, not §12.7.
- **Cost.** `status` runs a few git commands per lane (merge-base, diff, status, log). Fine for a
  handful of lanes; not meant for hundreds.
- **Clock.** Idle time mixes commit times with local file modification times; a lane on another
  machine is out of scope (§12.10 names a remote run file as a future change).

## Evidence

On this branch's base (`a9ae799`), in a throwaway repository with `[autopilot]` holding
`enabled = "yes"` and `max_lanes = -1`:

```
$ taskrail validate
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
$ taskrail autopilot start --count 1
usage: taskrail [-h] [--version] [--root ROOT]
                {validate,list,show,next,claim,release,claims,reserve-id,unreserve-id,init,upgrade,integration,self,new,done,discard,reopen,review,epic,kind}
                ...
taskrail: error: argument command: invalid choice: 'autopilot' (choose from validate, list, show, next, claim, release, claims, reserve-id, unreserve-id, init, upgrade, integration, self, new, done, discard, reopen, review, epic, kind)
exit=2
```

The suite on the base: `300 passed`.
