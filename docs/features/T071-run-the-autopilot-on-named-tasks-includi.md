# T071 — Run the autopilot on named tasks, including ones whose workspace new --workspace prepared

Kind: feature · Epic: E02 · Status: plan

Source: an autopilot session in a consuming repository, generalized here. The human asked for a run
on specific tasks; one of them had been created with `taskrail new --workspace`, so its row existed
only on its own branch. Prior work: `show` lists the branch `T071-run-the-autopilot-on-named-tasks-includi`,
which is this task's own prepared workspace (one commit, `chore(backlog): add T071`); no artifact and
no commit naming the task.

## Premise, checked on the current mainline

Reproduced on `fb9a26b` in a scratch repository (`T001` chore 1 pt, `T002` feature 5 pt, and `T003`
created with `new --workspace`, its row committed on its branch only):

1. `autopilot start --help` offers only `--count` and `--kinds`. A run meant for `T002` alone
   (`--count 1`) dispatches `T001`, the cheaper task: `next` chooses by points.
2. `new --workspace` without `--branch` writes no branch record (`<common dir>/taskrail/branches` does
   not exist). From the main checkout, `show T003` and `autopilot lane T003 --run R` exit 3
   (`no task`).
3. From `T003`'s worktree, `autopilot next` dispatches it with `prior_work.branches` naming its branch,
   and the lane brief's Workspace section says "If the branch already exists, stop and report".
4. After the lane joins a run with `claim T003 --run R`, `autopilot status --run R` reports
   `T003 not in the backlog` from the main checkout and `running` from the worktree.
5. `autopilot next` counts `T003`'s claimed lane from its worktree (`free: 0`) but not from the main
   checkout (`free: 1`): `dispatch.next_lanes` gives a member whose `project.task()` is `None` the
   state `None`, so it occupies nothing. Lanes and states depend on which checkout runs the command.

The premise holds.

## Behaviour

**Named runs.** `taskrail autopilot start --tasks T012,T015 [--json]` starts a run that works only
those tasks. The run file records `named` (the IDs in the order given, duplicates dropped) and `count`
(their number). `--count` may be given too, and must then equal that number; `--kinds` with `--tasks`
is refused. `start` refuses an ID it cannot find (exit 3), and a named task that is already closed —
`done`, `discarded`, `done-branch`, `discarded-branch`, or closed on a mainline ref — or whose kind
`[autopilot].kinds` excludes (exit 5). A blocked or claimed task may be named: `next` says why it waits.

`autopilot next --run R` on a named run takes its candidates from `named`, in that order, instead of
every eligible task by points; lanes, groups, resources, the count and every existing skip reason
apply unchanged. A named task that is not eligible and not already one of the run's lanes is listed in
`skipped` with its reason (`blocked by T010`, `claimed by <owner>`, `done-branch`, a kind not driven).
A task that is not named is never dispatched by a named run. `status` lists a named run's `named` and
every named task, dispatched or not. Count-only runs behave exactly as today.

**Extending a live run** (added at the plan gate, decision 3).
`taskrail autopilot extend <R> [--tasks IDs] [--count N] [--json]` changes an open run in place,
under the common-directory lock:

- `--tasks` on a named run appends the IDs to `named`, dropping duplicates and IDs already named, and
  raises `count` by the number added, with `start`'s refusals for each new ID (exit 3 unknown, exit 5
  closed or of a kind the autopilot does not drive). Naming only tasks already named changes nothing
  and exits 0 with `added: []`.
- `--count N` on a count-only run sets `count` to N; N below 1 exits 2, and N lower than the run's
  tasks already counted toward its count (§12.7: `dispatched`, `running`, `gate`, `escalated`,
  `failed`, `done-branch`, `handed-off`, `done-merged`) exits 5.
- `--count` on a named run, `--tasks` on a count-only run, or neither flag exits 2; an unknown run
  exits 3; a closed run exits 5. Like `start`, it exits 5 while the autopilot is disabled (checked
  first) and 1 for an invalid backlog.
- `--json` returns the updated `run`, `added` (the IDs appended) and `previous_count`. `next` and
  `status` read the run file, so they reflect the new count and named list at once.

**Rows that live only on their task's branch.** The autopilot commands — `start`, `next`, `status`,
`lane`, `notify`, `approve-governing`, `merged` — and `taskrail checks <ID>` find a task whose row is
absent from the checkout they run in on the task's own branch: the branch of its live claim, else its
branch record. The row is read from the worktree that has that branch checked out (so a row not yet
committed counts), else from the local branch tip, else from `<remote>/<branch>`. Such a row reads `⬜`
in the checkout, since the checkout does not close it; `done-branch`, `discarded-branch`, `done-merged`
and `discarded` come from the refs as for any task. So every checkout of the clone computes the same
states, lanes in use and hand-off queue. A claim naming an open run whose row cannot be found anywhere
still uses a lane (`running`).

To make such a task findable before anyone claims it, `new --workspace` records the branch it creates
(§6.4), as `new --workspace --branch` already does; with `branch_record_remote` set it is mirrored the
same way. For a workspace created before this change, `start`'s exit-3 message names
`taskrail branch <ID> <NAME>`, run in that worktree, to record it.

**Prepared workspaces.** `prior_work` gains `prepared`: `null`, or `{branch, worktree, fork, commits,
row}` when the task's local branch exists and its content — the branch tip plus the uncommitted and
untracked changes of the worktree that has it checked out — differs from its fork point (the
merge-base with `base.onto`) only by the task's own row: every changed path is a file of the task's
backlog, no line is removed, and the added non-blank lines are exactly one task row whose ID is the
task's, plus at most the task-table header and separator `new` writes into an epic without a table.
`commits` counts the branch's commits since the fork; `row` is `committed` when the tip holds the row,
else `uncommitted`. The rule is by content, so it holds whoever made the branch. `branches` keeps
listing the branch; `show`'s text adds `(prepared: only the task's row)` to its prior-work line.

**Skills.**

- `taskrail-autopilot` `SKILL.md`: the autopilot runs when the human explicitly asks and gives a task
  count **or names the tasks** (description and *When to run*); step 1 runs `start --tasks <IDs>` for
  named tasks and `--count <N>` otherwise; when the human adds tasks to a run or raises its count,
  the orchestrator extends that run with `autopilot extend` rather than starting another, which still
  needs the human's explicit request; exit 3 on a named task is reported to the human with the `taskrail branch` hint;
  *Dispatch* step 1 fills the brief's prepared Workspace section when the entry's
  `prior_work.prepared` is set.
- `references/lane-brief.md`: the Workspace section keeps "If the branch already exists, stop and
  report", and the brief's introduction says to use a new section, `## Workspace (prepared by taskrail
  new --workspace)`, when `prior_work.prepared` is set. That section says: the branch and worktree
  already exist and hold only the task's row; work inside them; do not create a workspace and do not
  stop because the branch exists; run the CLI from inside the worktree, since the row may exist only on
  that branch; commit an uncommitted row on its own; claim with `taskrail claim <ID> --run <RUN>` before
  any edit, and stop and report if it exits non-zero; plus the checks, resources and services lines
  every Workspace section has.
- `taskrail` `SKILL.md`, step 2 (*Inspect*): `prior_work.prepared` means the branch is the workspace
  `new --workspace` prepared, not someone's prior work; step 3's existing "skip to claiming" applies.

## Acceptance criteria

1. `autopilot start --tasks T005,T002,T005 --json` exits 0 with `run.named == ["T005", "T002"]`,
   `run.count == 2` and `run.kinds == []`; `--tasks T005,T002 --count 2` is accepted.
2. `start` exits 5 when the autopilot is disabled (before anything else); exits 2 with neither
   `--count` nor `--tasks`, with an empty `--tasks`, with `--count` different from the number of named
   tasks, and with `--kinds` beside `--tasks`; exits 3 for an unknown ID; exits 5 for a named task that
   is done, discarded, `done-branch` or `discarded-branch`, and for one whose kind `[autopilot].kinds`
   excludes. No run file is written on any refusal.
3. `next --run R` on a run named `T005,T002` dispatches `T005` then `T002` and nothing else, although
   `T001` is cheaper and eligible; with `max_lanes = 1` it dispatches `T005` only (`limited_by:
   max_lanes`), and `T002` on the next call once `T005`'s lane has ended.
4. On a named run, a blocked named task is in `skipped` as `blocked by <IDs>`, a named task claimed
   without the run as `claimed by <owner>`, and one of a kind the run does not drive with that reason;
   none is dispatched, and no task outside `named` appears in `dispatch` or `skipped`.
5. `new --epic E01 --kind feature --title … --workspace` writes the branch record for the template
   branch (`branch_source: recorded` in `show` inside the worktree).
6. With `T008` created by `new --workspace` and its row committed only on its branch, from the main
   checkout: `start --tasks T008` exits 0; `next --run R` dispatches `T008` with its `branch`,
   `worktree` and `prior_work.prepared`; `lane T008 --run R --state running`, `notify --event
   lane-done --run R --task T008` exit 0, and `approve-governing T008 --run R` finds the task (exit 5
   for its empty `governing_touched`, not exit 3);
   after `claim T008 --run R` in the worktree, `status --run R` reports it `running`, and after `done`
   is committed there, `done-branch` with `T008` in `handoff.queue`; `merged T008 --no-fetch` exits 0
   with `merged: false`; `taskrail checks T008` runs its checks in its worktree.
7. The same task discarded and committed on its branch reads `discarded-branch`, not `discarded`, in
   `status --run R` from the main checkout; with the row written by `new --workspace` but not
   committed, `next --run R` still finds and dispatches it.
8. From a checkout lacking the row of a claimed lane of an open run, `next` (preview and `--run`)
   lists that lane in `lanes.occupied` as `running` and `free` matches the worktree's own `next`; a
   claim naming an open run whose branch and worktree no longer exist still counts as `running`.
9. Count-only runs are unchanged: every existing `tests/test_autopilot*.py` test passes unmodified
   except the skill-text assertions of criterion 11.
10. `prior_work.prepared`, from `show --json` inside the worktree and from `next`'s entry: set with
    `commits: 1`, `row: committed` right after the row commit; `commits: 0`, `row: uncommitted` before
    it; `null` once any other file is changed (committed, uncommitted or untracked), once another row
    or other backlog text changes, once a row is removed, and when the branch does not exist. A task
    with a `prepared` branch still lists it in `branches`.
11. The shipped skill sources say: `SKILL.md` — `autopilot start --tasks`, "names the tasks" in the
    description and in *When to run*, `autopilot extend` for tasks added to a run or a raised count,
    and that the
    prepared Workspace section is used when `prior_work.prepared` is set; `lane-brief.md` — a
    `Workspace (prepared by taskrail new --workspace)` section with "do not stop because the branch
    exists", `claim <ID> --run <RUN>` and `taskrail checks <ID>`; the `taskrail` skill — `prior_work.prepared`.
    `taskrail upgrade` leaves the installed copies equal to the sources.
12. `uv run pytest -q` and `taskrail validate` pass.
13. `autopilot extend R --tasks T006,T005 --json` on a run named `T005,T002` exits 0 with
    `added == ["T006"]`, `run.named == ["T005", "T002", "T006"]`, `run.count == 3` and
    `previous_count == 2`; the next `next --run R` can dispatch `T006`, and `status --run R` lists it
    with `count` 3. `extend R --tasks T005` exits 0 with `added: []` and the count unchanged.
14. `extend R --tasks` exits 3 for an unknown ID and 5 for a closed task or a kind not driven, writing
    nothing; a task whose row is only on its branch can be added from the main checkout.
15. `extend R --count 4` on a count-only run with one lane `running` exits 0 with `run.count == 4`,
    and the next `next --run R` dispatches up to the new count; `--count 0` exits 2; with two tasks
    counted toward the run, `--count 1` exits 5 and `--count 2` exits 0.
16. `extend` exits 2 for `--count` on a named run, `--tasks` on a count-only run, and neither flag;
    3 for an unknown run; 5 for a closed run and while the autopilot is disabled.

Criteria 1–8, 10 and 13–16 are verified by pytest in a new `tests/test_autopilot_named.py` (reusing the
`pilot` pattern of `tests/test_autopilot_next.py`, with a worktree created by `new --workspace`) and
`tests/test_prior.py`; criterion 11 by `tests/test_autopilot_skill.py`.

## Affected areas

- `src/taskrail/branchrows.py` (new): `find(project, task_id, claimed) -> Task | None` and
  `adopt(project, task_ids, claimed)`, which appends the rows found on task branches to the loaded
  project (their epic too, when the checkout lacks it) with status `⬜`.
- `src/taskrail/autopilot/commands.py`: `cmd_start` (`--tasks`, validation, `named`), a new
  `cmd_extend`, `register` (`start --tasks`, `extend`), `cmd_lane` and `cmd_notify` (adopt before the
  lookup), `_status_text` (named line).
- `src/taskrail/autopilot/runs.py`: `create(…, named)`, `_normalize` (`named` defaults to `[]`), a new
  `extend` helper.
- `src/taskrail/autopilot/dispatch.py`: `next_lanes` (adopt members; named candidates and their skip
  reasons; a rowless claimed member occupies a lane), `_members` (adds `named`), `_entry` (passes what
  `prepared` needs). The candidate loop's final `else` is left as it is, for T070's missing-row skip
  (touch map).
- `src/taskrail/autopilot/status.py`: `run_status` (members include `named`; rows adopted).
- `src/taskrail/autopilot/approve.py` `cmd_approve_governing`, `src/taskrail/autopilot/merged.py`
  `cmd_merged`: adopt before the lookup.
- `src/taskrail/prior.py`: `prepared_workspace(…)`; `prior_work(…)` gains keyword arguments and the
  `prepared` key; `text_lines` marks it.
- `src/taskrail/cli.py` — three small edits in functions T070 may also change: `cmd_new`'s
  `record_branch` (record for every `--workspace`), `cmd_show` (the `prior_work` call's new
  arguments), `cmd_checks` (adopt before the lookup).
- Skills: `src/taskrail/skills/taskrail-autopilot/SKILL.md` (description, *When to run*, *Dispatch*
  step 1), `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md` (introduction, Workspace,
  new prepared section), `src/taskrail/skills/taskrail/SKILL.md` (step 2, one sentence); installed
  copies under `.claude/skills/` through `taskrail upgrade`.
- `DESIGN.md`: §6.4 (record writers), the §7 `autopilot` row, §7.2 (`prepared`), §12.1 (`start`,
  `extend`, `next` — whose cell also carries T070's clause "skips a task whose `base.row` is `missing`,
  with the reason" — and a paragraph on rows absent from the checkout), §12.3 (the lane's workspace),
  §12.4 (`named`), §12.7 (a rowless claimed lane). The §7 `new` row is T070's.
- `README.md`: the `autopilot start` line of the command list. `CHANGELOG.md`: Unreleased bullets.
- Tests: `tests/test_autopilot_named.py` (new), `tests/test_prior.py`, `tests/test_autopilot_skill.py`.

## Out of scope

- Lowering a named run's count, removing named tasks, or turning a count-only run into a named one.
- `show`, `list`, plain `next`, `claim`, `edit`, `done` and `review` still read only their checkout's
  rows; they run inside the task's worktree. Detecting a row absent from `base.onto` and carrying a row
  into a workspace are T070's.
- A named run as a pool (`--count` smaller than the named tasks).
- Recording the branch of a workspace created before this change automatically (a branch scan).

## Open questions and risks

- An older taskrail reading a named run keeps `named` (unknown keys are kept) but dispatches by points.
- Each `status`, `next` or `lane` parses the backlog once per run member whose row the checkout lacks;
  cost grows with those members only. A worktree backlog that fails to parse falls back to the tip.
- `cli.py` and the `taskrail` skill are shared with T070; the edits above are confined to the named
  functions and one sentence.
- The plan is at the upper end of a feature; the plan gate kept it as one task, `autopilot extend`
  included (decisions 3 and 8).
