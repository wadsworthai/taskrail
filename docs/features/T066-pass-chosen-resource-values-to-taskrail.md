# T066 — Pass chosen resource values to taskrail checks for a lane whose values were released

Kind: feature · Epic: E02 · Status: verified (plan approved: D1–D6 and the race as recommended;
implementation approved, including the one-line change to T063's test and the order of refusals).
Record:
`docs/autopilot/decisions/T066-pass-chosen-resource-values-to-taskrail.md`.

Source: question 4 of T063's scope gate
(`docs/autopilot/decisions/T063-name-taskrail-checks-in-the-lane-brief-a.md`), which follows finding
F11 of `docs/spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md` (permission prompts dominated
because commands carried `cd … &&` chains and shell variables that an allowlist cannot match).

## Today

- `taskrail checks <ID>` (T052, DESIGN §7.5) passes the values the task's autopilot lane holds as
  `TASKRAIL_RESOURCE_<NAME>`, read from the claim's run, else the newest run that lists the task.
- `autopilot next --run` releases a lane's values lazily once the lane is no longer in use (§12.7),
  and the orchestrator refills as soon as a close is reviewed (T033 F5). By hand-off or after a
  merge the lane's `resources` is therefore usually `{}`, and `taskrail checks` passes nothing.
- The `taskrail-autopilot` skill (*Close and hand off* step 1, T063) tells the orchestrator to run
  the checks "with values that no lane in use holds in `status`, set as
  `TASKRAIL_RESOURCE_<NAME>`" — that is, `TASKRAIL_RESOURCE_PORT=5434 taskrail checks <ID>`, an
  environment-prefix command of the shape F11 warns against. *After a merge* step 2 says "resource
  values as at hand-off", so it inherits the same shape. Nothing checks that the chosen value is not
  held by another lane.

## Behaviour

After this change:

- **`taskrail checks <ID> … --resource NAME=VALUE`**, repeatable, passes `VALUE` to the checks as
  `TASKRAIL_RESOURCE_<NAME>`, as one allowlistable command with no environment prefix.
  - **Merge with the lane's values.** The lane's recorded values are read as today; each
    `--resource` sets or replaces its name on top of them (D1). `resources` and `environment` in
    the result report the values actually passed; a new `chosen` field reports the
    `--resource` pairs as given (`{}` without the flag).
  - **Validation, before anything runs** (D2): a pair without `=` exits 2; `NAME` must be a
    `[[autopilot.resource]]` of the invoking checkout's configuration — the one `autopilot next`
    allocates from — and `VALUE` one of its `values`, otherwise exit 2 naming the configured names
    or values; a name given twice exits 2.
  - **A value another lane holds is refused** (D3): when a `--resource` value is held by a lane in
    use of a different task — the `held` map of the read-only `autopilot next` preview — the command
    exits 4, naming the holder task and value, and runs no check. A value held by the task's own lane
    is accepted.
  - Everything else in §7.5 is unchanged: which checks, where, exit 0/6/2/3/5.
- **The orchestrator's re-run steps name the flag** (D5): *Close and hand off* step 1 and
  `references/gate-review.md`'s *Rebase* bullet say to pass values no lane in use holds with
  `--resource NAME=VALUE` instead of setting `TASKRAIL_RESOURCE_<NAME>`.

## Acceptance criteria

1. In a fixture with a `PORT` pool of two values, after a lane's task is finished and
   `autopilot next --run` has released its value, `taskrail checks <ID> --resource PORT=<free>
   --json` runs the checks with `TASKRAIL_RESOURCE_PORT=<free>` (a check echoes it), exits 0, and
   reports `resources`, `environment` and `chosen` with that value; without the flag, `resources`
   is `{}`.
2. While the lane still holds a value, `--resource` replaces that name's value and keeps the lane's
   other names (a second pool `DB` still passes the lane's value).
3. A value held by another task's lane in use exits 4, names that task and the value, and runs no
   check (a check that touches a file leaves no file); the task's own held value is accepted.
4. A malformed pair (`PORT`), an unconfigured name, a value outside the pool, and a name given twice
   each exit 2 with a message naming the problem, and run no check.
5. Text mode shows the chosen values' effect the same way (the echoed value), with the same exit
   codes; no environment prefix is needed in the invocation.
6. The shipped `taskrail-autopilot` skill's *Close and hand off* section and `gate-review.md`'s
   *Rebase* section name `--resource NAME=VALUE` (source and both integrations' installed copies),
   no longer tell the orchestrator to set `TASKRAIL_RESOURCE_<NAME>` itself, and the existing
   command-and-flag test finds `--resource` in the parser.

## Tests per criterion

All in `tests/`. Each was observed failing before the implementation: the five
`test_checks.py` tests with `taskrail: error: unrecognized arguments: --resource …` (argparse exit
2), or `KeyError: 'chosen'` for the first call without the flag; the skill test on each copy
(`source`, `claude`, `opencode`) with ``'`taskrail checks <id> --resource name=value`' in …`` false.

| Criterion | Test |
|-----------|------|
| 1 | `test_checks.py::test_a_chosen_value_reaches_the_checks_of_a_lane_whose_values_were_released` (`PORT` pool `5433, 5434`, `max_lanes = 1`: T004 finished, the refill releases `5433` and gives it to the next task; without the flag `resources`, `environment` and `chosen` are `{}`; `--resource PORT=5434` echoes `port=5434` and reports it in all three) |
| 2 | `test_checks.py::test_a_chosen_value_replaces_its_name_and_keeps_the_lane_s_other_values` (pools `PORT` and `DB`; the running lane holds `5433`/`db_a`; `--resource PORT=5434` echoes `port=5434 db=db_a`) |
| 3 | `test_checks.py::test_a_value_another_lane_holds_exits_4_and_runs_nothing` (`PORT=5433`, held by the refilled lane: exit 4, stderr names `PORT=5433` and the holder, no `ran-5433` file); the own-value half in `…replaces_its_name…` (`--resource PORT=5433` while T004's lane holds it: exit 0) |
| 4 | `test_checks.py::test_a_rejected_resource_pair_exits_2_and_runs_nothing` (`PORT`, `CACHE=1`, `PORT=9999`, `PORT` twice: exit 2, a message naming `NAME=VALUE`, the configured names, the pool's values or "more than once"; no `ran-*` file) |
| 5 | `test_checks.py::test_text_mode_passes_chosen_values_and_refuses_held_ones` (text mode: `port=5434` and `passed test`, exit 0; a held value exits 4 naming the holder, with no `== test` header) |
| 6 | `test_autopilot_skill.py::test_refill_runs_once_a_close_is_reviewed_not_at_hand_off` (source, `claude` and `opencode` copies: *Close and hand off* names `` `taskrail checks <ID> --resource NAME=VALUE` `` and no longer "set as `TASKRAIL_RESOURCE_<NAME>`"; gate-review's *Rebase* section names `--resource NAME=VALUE`); `test_every_taskrail_command_and_flag_shown_exists` (unchanged, passes with `--resource` in the parser) |

Implementation notes:

- `test_autopilot_skill.py::test_the_brief_and_the_re_run_steps_name_taskrail_checks` (T063) asserted
  the sentence D5 replaces ("set as `TASKRAIL_RESOURCE_<NAME>`"). The full run failed on it on all
  three copies after the skill edit; its assertion now names the new phrase
  ("with `taskrail checks <ID> --resource NAME=VALUE`"). This test was not listed in the plan's
  affected areas.
- The worktree and the stage/check selection are resolved first, then `--resource`, so a task with no
  worktree still exits 5 and an unknown stage 2 before the pairs are read; in every refusal no check
  runs.
- The holder check runs only when `--resource` is given, so plain `taskrail checks` does no extra
  work.
- This repository's installed copies (`.claude/skills/taskrail-autopilot/SKILL.md`,
  `references/gate-review.md`, `.taskrail/installed.json`) were updated with `taskrail upgrade`.

## Verify

The real CLI from this branch (`<worktree>/.taskrail/bin/taskrail`, pinned to the branch's source),
invoked with `--root` at this repository's main checkout. T066 is claimed in run `20260915-2`; this
repository configures no `[[autopilot.resource]]`, so the pool paths are covered by the fixture tests
above and the real run exercises parsing, validation and the result shape.

```text
$ taskrail --root <main checkout> checks T066 --stage plan --resource PORT=1 --json
taskrail: --resource: `PORT` is not an [[autopilot.resource]] (configured: none)
exit 2

$ taskrail --root <main checkout> checks T066 --stage plan --resource PORT
taskrail: --resource expects NAME=VALUE, got `PORT`
exit 2

$ taskrail --root <main checkout> checks T066 --stage plan --json          # exit 0
"worktree": "<main checkout>/.worktrees/T066-pass-chosen-resource-values-to-taskrail",
"run": "20260915-2", "resources": {}, "environment": {}, "chosen": {}, "stage": "plan",
"checks": [], "passed": true

$ taskrail --root <main checkout> checks --help
usage: taskrail checks [-h] [--json] [--stage STAGE] [--check NAME]
                       [--resource NAME=VALUE] [--allow-invalid]
                       id
  --resource NAME=VALUE
                        pass this pool value as TASKRAIL_RESOURCE_<NAME>,
                        replacing the lane's; refused when another lane holds
                        it; repeatable
```

No gap against the plan.

## Affected areas

Named against the touch map; all are free for this lane.

- `src/taskrail/checks.py` — a new `chosen_resources(project, task_id, pairs)`
  (parse, validate against `project.config.autopilot.resources`, holder check through
  `dispatch.next_lanes(project, None, claims)`'s `resources[].held`, read-only, no edit to
  `dispatch.py`); `run_checks` gains a `chosen` parameter, merges it over `lane_resources`' values
  and adds `chosen` to the result; `ChecksRefused` carries exit 4 for a held value. Module docstring
  updated.
- `src/taskrail/cli.py` — `cmd_checks` passes `args.resource`; the `checks` parser
  registration gains `--resource` (`action="append"`, `metavar="NAME=VALUE"`). No other command.
- `tests/test_checks.py` — new tests for criteria 1–5.
- `tests/test_autopilot_skill.py` — `test_refill_runs_once_a_close_is_reviewed_not_at_hand_off`
  (the assertion on *Close and hand off*) and one assertion on gate-review's *Rebase* section, for
  criterion 6.
- `src/taskrail/skills/taskrail-autopilot/SKILL.md` — *Close and hand off* step 1,
  its last sentence only (D5).
- `src/taskrail/skills/taskrail-autopilot/references/gate-review.md` — *Rebase: at
  hand-off or after a merge*, the *Re-run the checks* bullet only (D5).
- `.claude/skills/taskrail-autopilot/…` and `.taskrail/installed.json` — through
  `taskrail upgrade`.
- `DESIGN.md` §7 CLI table row for `checks`, §7.5, and the last sentence of §12.7's
  `[[autopilot.resource]]` bullet (D4).
- `README.md` — none unless D4 is extended; `CHANGELOG.md` one
  *Unreleased* bullet; `docs/features/README.md` index row.

## Out of scope

- Choosing free values automatically (for example `--free-resources`): the task row asks for chosen
  values; a follow-up can add it if the orchestrator's choice proves error-prone.
- Reserving or recording chosen values in the run: `checks` keeps reading run files and never
  writes them, so a chosen value is not held against a later dispatch while the checks run.
- `dispatch.py` (`next_lanes`, T064's area), `status.py` (T064, T065), the lane brief (lanes keep
  their own values), *After a merge* step 2 (its "resource values as at hand-off" already points at
  step 1), and the `claude`/`opencode` integration notes.

## Open questions and risks

- **D1 — how chosen values combine with the lane's.** Recommendation: merge, `--resource` winning per
  name, so one flag replaces one value and a lane that still holds others keeps them. Alternatives:
  `--resource` replaces the whole set (a lane's other values are dropped); or refuse `--resource`
  while the lane still holds values (forces the orchestrator to know whether release happened).
- **D2 — what values are accepted.** Recommendation: the name must be a configured
  `[[autopilot.resource]]` and the value one of its `values` in the invoking checkout's configuration
  (the pool `next` allocates from), so a typo exits 2 instead of running against a wrong database.
  Alternatives: any `NAME` matching the resource-name pattern and any value (usable for a scratch
  value outside the pool, but typos pass silently); name checked, value free.
- **D3 — refusing a value another lane holds.** Recommendation: yes, exit 4 ("conflict", as the core
  skill's table reads it: stop and report who holds it), computed from the read-only
  `dispatch.next_lanes(project, None, claims)` preview, which writes nothing and needs no lock.
  Alternatives: exit 5 (refused); or no holder check, leaving the choice to the orchestrator reading
  `status` (cheaper, but the mistake it prevents is two lanes sharing one database). Risk: T064
  changes `next_lanes` on its unmerged branch; this lane only calls it and reads
  `resources[].held`, which `autopilot next --json` already reports, so a conflict is unlikely, but a behaviour change
  there would show in these tests after the rebase.
- **D4 — DESIGN.md text** (read first, decided by the orchestrator). Recommendation: approve as
  written.
  - §7 CLI table, the `checks` row becomes:
    ```markdown
    | `taskrail checks <ID> [--stage STAGE] [--check NAME]… [--resource NAME=VALUE]…` | Run a task's configured checks in its worktree with its autopilot lane's resources, or chosen ones, from anywhere in the clone (§7.5) |
    ```
  - §7.5: after the sentence ending "…its lane's resource values as `TASKRAIL_RESOURCE_<NAME>`
    (§12.7).", insert:
    ```markdown
    `--resource NAME=VALUE`, repeatable, passes a chosen value instead, replacing that name's lane
    value if any — for a lane whose values `next` has released, at hand-off or after a merge. The
    name must be an `[[autopilot.resource]]` and the value one of its `values` (exit 2 otherwise),
    and a value that a lane of another task in use holds is refused with exit 4, naming it; no
    check runs in either case.
    ```
    and in the `--json` sentence, "with `worktree`, `run`, `resources`, `environment` and `passed`"
    becomes "with `worktree`, `run`, `resources` and `environment` (the values passed), `chosen`
    (the `--resource` pairs) and `passed`"; "Exit 0 when every check that ran passed, 6 when one
    failed, 2 for an unknown stage, …" becomes "…, 2 for an unknown stage or a rejected
    `--resource`, 3 for an unknown task, 4 for a value another lane holds, 5 when the task has no
    worktree".
  - §12.7, the `[[autopilot.resource]]` bullet's last sentence "…so the checks it re-runs at
    hand-off or after a merge (§12.8) use values no lane in use holds." becomes "…so the checks it
    re-runs at hand-off or after a merge (§12.8) use values no lane in use holds, passed with
    `taskrail checks <ID> --resource NAME=VALUE` (§7.5)."
  Alternative: §7 row and §7.5 only, leaving §12.7 as is.
- **D5 — skill text** (portable, free in the touch map). Recommendation: approve as written.
  - `SKILL.md` *Close and hand off* step 1, the sentence "…but the refill after the close may have
    released them (its `resources` is then empty): run the checks with values that no lane in use
    holds in `status`, set as `TASKRAIL_RESOURCE_<NAME>`." becomes:
    ```markdown
    but the refill after the close may have released them (its `resources` is then empty): pass
    values that no lane in use holds in `status` with `taskrail checks <ID> --resource NAME=VALUE`,
    one flag per resource; it refuses a value another lane holds.
    ```
  - `references/gate-review.md` *Rebase* section, the bullet "Re-run the checks with `taskrail
    checks <ID>` and run `taskrail validate`, then record the rebase in the task's record." becomes:
    ```markdown
    - Re-run the checks with `taskrail checks <ID>`, adding `--resource NAME=VALUE` for each value
      the lane no longer holds, and run `taskrail validate`, then record the rebase in the task's
      record.
    ```
  Alternative: CLI only, leaving the skill's environment-prefix sentence until a later chore (the
  command shape F11 warns against would then stay the documented procedure).
- **D6 — CHANGELOG.** Recommendation: one *Unreleased* bullet: "**Chosen resource values for
  checks.** `taskrail checks <ID> --resource NAME=VALUE` passes a pool value to the checks of a lane
  whose values were released, refusing one another lane holds (exit 4), so the orchestrator's
  hand-off and after-merge re-runs need no environment prefix (T066)." Alternative: none.
- **Risk — race.** The holder check and the checks run are not atomic: a `next --run` between them
  could hand the same value to a new lane. The orchestrator runs `next` and re-runs checks in one
  session, one at a time, so this needs two orchestrators on one clone; recording chosen values in
  the run is out of scope.
