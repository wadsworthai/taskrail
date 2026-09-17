# T081 — Commit a task's changes only when it is done with commit = on-done

Kind: feature · Epic: E07 · Status: verified

Contract: DESIGN.md §13.1, §13.3, §13.6, §13.7 and the T081 row of §13.8, decided at T079's scope
gate (decisions 7, 8 and 12 of its decision record). Prior work: none (`show` lists no artifact,
branch or commit naming the task).

## Premise, checked on the current mainline

On `f0eafa9`: `kinds.Stage.commit` is the declared boolean and nothing else changes it;
`load_config` reads no `[git].commit` and a descriptor's top-level `commit` is silently ignored
(`_parse` never reads it); `done` and `discard` return `{id, status}` only; `autopilot start`,
`extend` and `next` check `[autopilot].enabled` first and nothing about commits. The premise holds.

## Behaviour

- **Configuration.** `[git] commit = "stages" | "on-done"` sets the repository's commit policy.
  Any other value, including a non-string, fails the config load with exit 2 naming `git.commit`.
- **Kind policy.** A descriptor (core, local or override) may declare a top-level
  `commit = "stages" | "on-done"`. It wins over `[git].commit` in both directions. Any other value,
  such as a boolean at the top level, is a `kind-invalid` error naming the descriptor (exit 1 from
  `validate`). A stage's `commit` stays a boolean.
- **Effective policy.** The kind's `commit` when declared (`commit_source` `"kind"`), else
  `[git].commit` when set (`"config"`), else `"stages"` (`"default"`).
- **Reports.**
  - `show --json` and `kind list --json`: every stage's `commit` is the effective value — `false`
    for every stage under `"on-done"`, the declared boolean under `"stages"`. `kind_descriptor` and
    each `kind list` entry gain `commit` (the effective policy) and `commit_source`. The text form
    of `show` follows: its stage lines lose `, commit` under `"on-done"`.
  - `show --json` gains a top-level `close` object with `commit` only (`close.review` is T083's).
  - `done --json` and `discard --json` gain `commit`, the task's effective policy. Under
    `"on-done"` their text adds the line
    `commit everything <ID> changed now, the status change included`.
- **Autopilot.** `autopilot start`, `extend` and `next` (preview included) exit 5 right after the
  `[autopilot].enabled` check when any kind the run drives has the effective policy `"on-done"`,
  naming each such kind and its source: `[git].commit in .taskrail/config.toml`, or the descriptor
  path that declares it. `status`, `lane`, `decision`, `approve-governing`, `merged`, `notify` and
  `close` are unchanged.

Driven kinds, as §13.7 lists them:

| Command | Kinds checked |
|---|---|
| `start --tasks IDs` | the kinds of the named tasks found (checkout row or branch row, as `start` finds them) |
| `start [--kinds …]` | `--kinds`, else `[autopilot].kinds`, intersected as `next` drives them (`dispatch.run_kinds`); every allowed kind when neither is set |
| `extend R` | the run's kinds as `next --run R` (below), plus the kinds of the tasks `--tasks` adds |
| `next --run R` | a count-only run: `dispatch.run_kinds` of the run; a named run: the kinds of its named tasks (question 2) |
| `next` (preview) | `[autopilot].kinds`, else every allowed kind |

Unknown kind names, unknown task IDs and unknown or closed runs are skipped by this check, so the
command's existing exit 3, 2 or 5 still reports them.

## Acceptance criteria

1. `[git].commit = "on-done"` loads; `"stages"` loads; any other string, and a boolean, exit 2 from
   `validate` with a message naming `git.commit`.
2. A descriptor with top-level `commit = "on-done"` or `"stages"` loads; `commit = true` at the top
   level, or `"sometimes"`, is a `kind-invalid` error naming that descriptor.
3. With no policy anywhere, `show --json` reports `kind_descriptor.commit = "stages"`,
   `commit_source = "default"`, the declared stage booleans, and `close = {"commit": "stages"}`.
4. With `[git].commit = "on-done"`, every stage of `show --json`'s `kind_descriptor` and of every
   `kind list --json` entry has `commit: false`, with `commit = "on-done"`, `commit_source =
   "config"`, and `close.commit = "on-done"`; the text of `show` has no `, commit` marker.
5. An override declaring `commit = "stages"` under `[git].commit = "on-done"` reports that kind with
   its declared stage booleans and `commit_source = "kind"`; one declaring `"on-done"` without
   `[git].commit` reports that kind `on-done` from `"kind"` while other kinds stay `"stages"`.
6. A descriptor with `commit = "on-done"` whose stages say `commit = true` raises no issue.
7. `done --json` and `discard --json` report `commit` with the task's effective policy; under
   `"on-done"` their text includes `commit everything <ID> changed now, the status change included`,
   and under `"stages"` it does not.
8. With the autopilot enabled and an on-done kind driven, `autopilot start --count`, `start --tasks`,
   `extend` (count-only and named) and `next` (with `--run` and preview) exit 5 with a message naming
   the kind and its source (`[git].commit` in `.taskrail/config.toml`, or the descriptor path); when
   no driven kind is on-done (for example, `[autopilot].kinds` leaves the on-done kind out) they
   behave as before. A disabled autopilot still gets the `enabled` refusal first.
9. `autopilot status` still works on a run after `[git].commit` changes to `"on-done"`.

## Affected areas

- `src/taskrail/config.py` — `COMMIT_POLICIES = ("stages", "on-done")`; `Config.commit: str | None`
  (`None` when unset); loading and validation on their own lines after `push_task_branch`.
- `src/taskrail/kinds.py` — `Kind.commit` and `Kind.commit_source` (new fields with defaults, after
  `path`); `Kind.to_dict` adds `commit` and `commit_source` after `commit_type`; in `_parse`, reading
  and validating the top-level `commit` next to `commit_type`, and one hunk after the stage loop that
  resolves the effective policy and sets every stage's `commit` to `False` under `"on-done"`
  (`dataclasses.replace`). The stage loop, `GATES` and the gate check are not touched.
  A small `commit_policy(kind, config)` helper returns `(policy, source)`, falling back to the config
  when a task's kind is not loaded.
- `src/taskrail/cli.py` — `cmd_show`: one `data["close"] = {"commit": …}` line after
  `kind_descriptor`, plus the optional text line (question 1); `_change_status`: `commit` in the
  result and the on-done text line.
- `src/taskrail/autopilot/commands.py` — one helper `_on_done_refusal(project, …)` returning the
  message or `None`, called with one line right after the `enabled` check in `cmd_start`,
  `cmd_extend` and `cmd_next`.
- `tests/test_commit_policy.py` — new: config, kind overrides, `show`/`kind list --json`, `done` and
  `discard`, and the autopilot refusals.
- `DESIGN.md` — the implemented parts move into §4 (the `commit` line of the `[git]` example and the
  config check paragraph), §5.1 (the descriptor's top-level `commit`), §7 (the `show` and
  `done`/`discard` rows) and §12.1/§12.2 (the refusal in the `start`, `extend`, `next` rows and the
  §12.2 bullet, `on-done` half only); in §13, §13.3 is marked implemented (T081) and my rows/bullets
  in §13.1, §13.6, §13.7 and §13.8 are marked. §13's introduction and other lanes' parts are left
  as they are.
- `CHANGELOG.md` — one bullet under Unreleased.
- `docs/features/README.md` — this artifact's row.

## Out of scope

- `[git].task_branch`, anything under `"current"` (T080); `gate = "decisions"` (T082); `review`
  and `close.review` (T083); skills, integration notes and README (T084). The skills keep
  committing per stage until T084 teaches them `close.commit`.
- No warning for stage booleans under `"on-done"` (§13.6).
- No change to `list`/`next` entries: `close` is `show`-only, per §13.3.

## Open questions and risks

1. **`show`'s text form.** §13.3 specifies only the JSON. Recommendation: add one line
   `  commit on-done (<source>)` to the text only under `"on-done"`, so a human reading `show` sees
   why no stage commits; the default output stays byte-identical. Alternative: no text change.
2. **Driven kinds of a named run** (`extend`, `next --run`). §13.7 says "the run's" kinds, and a named
   run stores `kinds = []`, which read literally is "every allowed kind". Recommendation: the kinds of
   its named tasks, which are all it can dispatch, so a named run of `feature` tasks is not refused
   because some other kind is on-done. Alternative: literal reading (every allowed kind), which
   refuses more.
3. **Wording of the autopilot refusal.** §13.7 fixes only what it names. Recommendation:
   `taskrail: the autopilot needs lanes that commit as each stage ends; kind `feature` commits on done ([git].commit in .taskrail/config.toml)`,
   listing every offending kind with its source, separated by `; `.
4. **Conflict risk with T080 and T082.** Same regions of `config.py`, `cmd_show`, the three
   autopilot handlers and `_parse`; kept to separate small hunks as the touch map asks. Both
   refusals sit right after the `enabled` check; if T080 lands first, mine goes after its line.

Answered at the plan gate
([decision record](../autopilot/decisions/T081-commit-a-task-s-changes-only-when-it-is.md)): 1, 2 and
3 as recommended; the plan approved, with the effective stage `commit` required for a `[git].commit`
set in config as well as for a descriptor policy, in both `show` and `kind list`.

## Implementation notes

- The effective policy is resolved in `kinds._parse`, which already receives the loaded `Config`, so
  every kind the project loads — core, local and override — carries its effective `commit`,
  `commit_source` and stage booleans; `show`, `kind list` and the autopilot read them from there.
- §13.3 keeps a one-line pointer (run decision 1) and names what stays planned for T083
  (`close.review`), since §13.5 and T083's row still point at it.

## Acceptance criteria and tests

All in `tests/test_commit_policy.py`.

| # | Tests |
|---|---|
| 1 | `test_config_commit_accepts_both_policies`, `test_config_commit_is_unset_by_default`, `test_config_commit_rejects_other_values` |
| 2 | `test_kind_commit_accepts_both_policies`, `test_kind_commit_rejects_other_values` |
| 3 | `test_show_reports_the_default_policy` |
| 4 | `test_config_on_done_turns_every_stage_commit_off_in_show_and_kind_list`, `test_config_stages_keeps_the_declared_booleans` |
| 5 | `test_kind_stages_wins_over_config_on_done`, `test_kind_on_done_without_config` |
| 6 | `test_on_done_kind_with_committing_stages_is_not_an_issue` |
| 7 | `test_done_and_discard_report_the_policy`, `test_done_and_discard_text_under_on_done`, `test_done_and_discard_under_stages` |
| 8 | `test_autopilot_refuses_a_config_on_done`, `test_autopilot_names_every_on_done_kind_with_its_source`, `test_autopilot_refuses_existing_runs_after_the_switch`, `test_autopilot_checks_only_the_kinds_a_run_drives`, `test_a_disabled_autopilot_is_refused_first` |
| 9 | `test_autopilot_refuses_existing_runs_after_the_switch` (its `autopilot status` step) |

## Verification

Run with this branch's CLI (`uv run --project <worktree> taskrail --root <scratch>`) against a scratch
repository: the core kinds, three pending tasks (feature, chore, bug), `[checks] test = "true"`,
`[git] commit = "on-done"` and `[autopilot] enabled = true`.

| Step | Seen |
|---|---|
| `show T001` | stage lines `· plan (gate: always)`, `· implement (gate: always)`, `· verify (gate: conditional)` with no `, commit`, and the line `commit on-done ([git].commit)` |
| `show T001 --json` | `close` `{"commit": "on-done"}`; `kind_descriptor.commit` `on-done` from `config`; every stage `commit: false` |
| `kind list --json` | bug, chore, feature and spike each `on-done` from `config`, every stage `false` |
| `autopilot next`, `autopilot start --count 1` | exit 5: `taskrail: the autopilot needs lanes that commit as each stage ends; kind `bug` commits on done ([git].commit in .taskrail/config.toml); …` for all four kinds |
| `autopilot status` | exit 0, `no autopilot runs` |
| override `feature` with `commit = "stages"` and one `commit = true` stage; `[autopilot] kinds = ["feature"]` | `show T001 --json`: `close.commit` `stages`, `stages` from `kind`, `build` `commit: true`; `autopilot next` exit 0, dispatching T001 in the preview |
| `autopilot start --tasks T002` (a chore) | exit 5, naming only `chore` from `[git].commit`; the on-done check comes before `start`'s own exit 5 for a kind `[autopilot].kinds` leaves out |
| `claim T002`, `done T002` | `T002 done` and `commit everything T002 changed now, the status change included` |
| `discard T003 --json` | `"commit": "on-done"` |
| `done T001 --force` (the `stages` override) | `T001 done` only |
| override's top-level `commit = true`, then `validate` | exit 1: `.taskrail/overrides/feature/kind.toml: error: `commit` must be "stages" or "on-done", the kind's commit policy; a stage's `commit` is true or false [kind-invalid]` |
| `[git] commit = "later"`, then `validate` | exit 2: `taskrail: .taskrail/config.toml: git.commit must be "stages" or "on-done"` |

The behaviour matches the plan.
