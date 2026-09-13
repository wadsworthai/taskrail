# T020 — Run stages conditionally on a column or the executor's judgement

Kind: feature · Epic: E05 · Status: implemented

## Behaviour

Today every `[[stage]]` of a kind applies to every task of that kind, so a repository that wants
one extra stage for some tasks — a visual check for UI work, a migration review for database
work — has to duplicate the whole kind. After this change a stage can declare when it applies:

```toml
[[stage]]
name = "visual-check"
summary = "Compare the changed screens against the design and attach screenshots."
gate = "always"
column = "Area"          # applies only when the task's Area cell matches
match = ["ui", "ux"]     # any of these values

[[stage]]
name = "migration-review"
summary = "Check the migration is reversible and safe on a large table."
gate = "always"
judgement = true         # the executor decides whether the stage is relevant

[[stage]]
name = "a11y-audit"
column = "Area"
match = ["ui"]
judgement = true         # only UI tasks, and then only when the executor judges it relevant
```

A stage with none of these keys applies to every task, as today.

### The column predicate

`column` plus `match` is a **column predicate**, defined once in its own module
(`taskrail/predicates.py`) and documented in DESIGN.md next to kinds, so the autopilot's
`[[autopilot.group]]` (DESIGN.md §12.7) reuses the same parser, matcher and wording:

- `column` names a custom column declared in `[columns].custom`, matched case-insensitively
  and resolved to its declared spelling. The cell is read from the task's row; a table without
  that column reads as empty.
- `match` is a non-empty list of non-empty strings; a single string is accepted as a
  one-element list. The predicate holds when the cell equals **any** value.
- Values compare **case-insensitively**, after trimming. `"*"` matches any non-empty cell and
  `"—"` (or `"-"`) matches an empty one, the same markers `[[route]]` uses.
- One column per predicate. Several conditions on different columns are out of scope.

### Validation

Checked when kinds load, so `validate` reports them and every command that refuses an invalid
backlog refuses on them:

- `column` without `match`, `match` without `column`, an empty `match`, a non-string value, or a
  non-boolean `judgement` — `kind-invalid` (error), as for any malformed descriptor.
- `column` naming a column `[columns].custom` does not declare — new `stage-column-unknown`
  (error) at the descriptor's path. When the name is a core column or a core column's alias
  (compared case-insensitively), the message says so, for example
  ``stage `visual-check`: column `Size` is the alias of core column Pts; stage predicates read custom columns only``.
  Unlike `kind-invalid`, this error keeps the kind loaded, so its tasks are not additionally
  reported as `task-kind-unknown`.

### Reporting in `show`

`show --json` resolves the predicate for the task, so executors and skills never re-implement it.
Each entry of `kind_descriptor.stages` gains:

| Field | Value |
|---|---|
| `column` | the resolved column name, or `null` |
| `match` | the list of values, or `[]` |
| `judgement` | `true` or `false` |
| `applies` | the column predicate's result for this task: `true` or `false`, and `true` when the stage has no predicate |

`kind list --json` has no task, so its stages carry `column`, `match` and `judgement` but no
`applies`. `applies` is always a boolean and `judgement` stays a separate boolean, so a consumer
never type-checks a field: the stage is skipped when `applies` is false, and left to the
executor when `applies` and `judgement` are both true. Text `show` marks each stage line with
`— not applicable (Area)` when `applies` is false, and `— executor's judgement` when it is true
and `judgement` is set.

### Executing

The core skill's step 5 changes, and nothing else in it:

- Skip a stage whose `applies` is `false`, without asking.
- When `applies` and `judgement` are both true, decide whether the stage is relevant to this
  task. To skip it, record the stage and the reason in the artifact and in the next gate report. When the skipped
  stage's gate is `always`, stop at that point and ask instead of skipping silently: the kind's
  author wanted a human to see that stage.
- A stage the executor skill does not describe — one a repository added through an override —
  is done as its `summary` says. Without this line, adding a stage by override leaves the
  executor with no instructions for it.

### Layered kinds

Predicates work the same in every layer. An override still replaces the whole descriptor, so a
repository adds a conditional stage to a core kind by copying it to
`.taskrail/overrides/<kind>/kind.toml` and adding the stage; the core kinds ship no predicates.
`stage-column-unknown` is reported against the layer file that declares the stage. `[kinds].allowed`
is unaffected.

## Acceptance criteria

1. A local kind with a stage `column = "Area"`, `match = ["ui"]` loads with no issues when
   `[columns].custom` declares `Area`; `show --json` reports `applies: true` for a task whose
   `Area` cell is `ui`, `UI` or ` Ui `, and `applies: false` for `api` or an empty cell.
2. `match` with several values holds when any of them matches; `"*"` holds for any non-empty
   cell and not for `—`/empty; `"—"` holds for an empty cell, `—` or `-`, and for a task in a
   table that lacks the column.
3. `match = "ui"` (a string) behaves as `["ui"]`.
4. A stage with `judgement = true` and no column reports `applies: true, judgement: true`; with
   a column predicate too, it reports `applies: true` when the predicate holds and
   `applies: false` when it does not, with `judgement: true` in both cases. `applies` is a JSON
   boolean in every case.
5. A stage without `column`, `match` or `judgement` reports `column: null`, `match: []`,
   `judgement: false`, `applies: true`; the core kinds' `show --json` output changes only by
   those added fields.
6. `kind list --json` stages carry `column`, `match` and `judgement` and no `applies`.
7. `column` without `match`, `match` without `column`, `match = []`, a non-string match value, or
   `judgement = "yes"` makes `validate` report `kind-invalid` naming the stage.
8. `column` naming an undeclared column makes `validate` report `stage-column-unknown` (error)
   at the descriptor's path, the kind stays loaded (no `task-kind-unknown` for its tasks), and
   `show` exits 1. Naming a core column, or a core column's alias from `[columns].aliases`, in
   any letter case, gives the same code with a message naming the core column.
9. `column = "area"` resolves to a declared `Area` and `show --json` reports `column: "Area"`.
10. A predicate in `.taskrail/overrides/<kind>/kind.toml` for a core kind resolves exactly as
    one in `.taskrail/types/`, and its errors carry the override's path.
11. The column predicate's parser and matcher live in one module that takes the column and
    match values plus the declared custom columns and aliases, with no dependency on kinds, so
    a `[[autopilot.group]]` can call it.
12. Text `show` marks a stage that does not apply and a judgement stage.
13. The installed core skill's step 5 says to skip a stage whose `applies` is false and to decide
    one whose `applies` and `judgement` are both true,
    including recording a skipped judgement stage and asking first when its gate is `always`,
    and that a stage the executor skill does not describe follows its `summary`.
14. DESIGN.md documents the conditional stage keys and the column predicate in §5, and §12.7
    points to that definition instead of deferring to "whichever lands first".

## Test coverage

All in `tests/test_conditional_stages.py`.

| # | Tests |
|---|---|
| 1 | `test_column_predicate_matches_case_insensitively_after_trimming` |
| 2 | `test_any_of_several_values`, `test_star_matches_any_non_empty_cell`, `test_empty_marker_matches_an_empty_cell_or_a_missing_column` (`—` and `-`) |
| 3 | `test_match_as_a_string` |
| 4 | `test_judgement_alone`, `test_judgement_with_a_column_predicate` (both assert `applies is True`/`False`, never another type) |
| 5 | `test_plain_stage_reports_defaults`, `test_core_kind_stages_only_gain_the_new_fields` |
| 6 | `test_kind_list_reports_the_predicate_without_applies` |
| 7 | `test_malformed_predicate_is_kind_invalid` (8 cases: column without match, match without column, empty list, non-string value, blank value, empty column, non-string column, non-boolean judgement) |
| 8 | `test_undeclared_column_is_an_error_that_keeps_the_kind` (including `show` exit 1), `test_core_column_is_refused` (5 names and letter cases), `test_alias_of_a_core_column_is_refused` (`Size`, `size`) |
| 9 | `test_column_predicate_matches_case_insensitively_after_trimming` (`column = "area"` reported as `Area`) |
| 10 | `test_predicate_in_an_override_of_a_core_kind`, `test_override_errors_carry_the_override_path` |
| 11 | `test_predicate_module_parses_resolves_and_matches_without_kinds`, `test_predicate_module_imports_nothing_else_from_taskrail` |
| 12 | `test_text_show_marks_conditional_stages` |
| 13 | `test_core_skill_step_5_covers_applies_and_judgement`; the installed copy is refreshed by `taskrail upgrade` |
| 14 | Documentation; reviewed in the diff of `DESIGN.md` (§5.1, §5.4, §12.7) |

## Affected areas

- `src/taskrail/predicates.py` (new) — `ColumnPredicate`: parse `column` and
  `match` against declared custom columns and aliases, match a task's columns.
- `src/taskrail/kinds.py` — `Stage` gains `predicate` and `judgement`; `_parse`
  reads and validates them; `Stage.applies(task)`; `Kind.to_dict(task=None)`.
- `src/taskrail/cli.py` — `cmd_show` passes the task to `to_dict` and marks
  stages in text output. No other command changes.
- `src/taskrail/model.py` — `NONE_MARKERS` now comes from the new module and is
  re-exported, so the module stays free of imports from the rest of the package.
- `src/taskrail/skills/taskrail/SKILL.md` — step 5 only; installed copy
  refreshed with `taskrail upgrade`.
- `DESIGN.md` — §5.1 example, a new §5.4 *Conditional stages* with the column
  predicate, and one sentence in §12.7.
- `README.md` — a short paragraph under *Task kinds*.
- `CHANGELOG.md` — one bullet under *Unreleased*.
- `tests/test_conditional_stages.py` (new).

## Out of scope

- Changing `[[route]]` matching, which stays case-sensitive. Moving it onto the shared column
  predicate would be a behaviour change and is a candidate follow-up task.
- Predicates on core columns (`Pts`, `Kind`, …) or on the epic, and conditions over several
  columns.
- Merging an override into the kind it overrides (adding one stage without copying the
  descriptor).
- Recording skipped stages in any CLI state; taskrail has no stage state today.
- Filtering the `checks` map in `show` by applicable stages; it keeps every stage's checks.
- The autopilot's `[[autopilot.group]]` itself (T029).

## Open questions and risks

- **Case-insensitive values diverge from routes.** A repository using both sees `ui` match a
  stage but not a route. Accepted for now because a stage skipped by a letter-case typo is
  invisible; the follow-up above would align them.
- **A mistyped cell still skips silently.** `applies: false` is visible in `show`, but nothing
  warns about a value outside `match`. A per-column set of allowed values is out of scope.
- **Parallel lanes.** T017 edits the core skill's steps 2, 3 and 8 and DESIGN.md §6–§7; this
  task edits step 5, §5 and one sentence of §12.7, so a rebase conflict should be mechanical.

## Verification

Exercised with the real CLI (`uv run taskrail --root <tmp> …`) in a
throwaway repository under a temporary directory, deleted afterwards. Its config declared
`custom = ["Area"]` and `aliases = { Pts = "Size" }`; its backlog had two tasks of a local
`screen` kind (`Area` = `UI` and `api`) and two of core `feature` (`ui` and `—`), with an
override of `feature` adding `visual-check` on `column = "Area"`, `match = ["*"]`.

The `screen` kind had `build` (plain), `visual-check` (`column = "area"`, `match = ["ui", "ux"]`),
`migration-review` (`judgement = true`) and `a11y-audit` (`column = "Area"`, `match = "ui"`,
`judgement = true`).

- `validate`: `4 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`, exit 0.
- `show T001` (`UI`): `visual-check (gate: always)` unmarked, `migration-review` and `a11y-audit`
  marked `— executor's judgement`.
- `show T002` (`api`): `visual-check` and `a11y-audit` marked `— not applicable (Area)`,
  `migration-review` `— executor's judgement`.
- `show T003` / `show T004` (override): `visual-check` unmarked for `ui`, `— not applicable (Area)`
  for `—`.
- `show T002 --json`: `visual-check` `column: "Area"`, `match: ["ui", "ux"]`, `judgement: false`,
  `applies: false`; `migration-review` `judgement: true`, `applies: true`; `a11y-audit`
  `match: ["ui"]`, `judgement: true`, `applies: false`; `build` `column: null`, `match: []`.
- `kind list --json`: the same `column`, `match` and `judgement`, and no `applies`.
- `column = "Team"`: `stage-column-unknown` "column `Team` is not declared in [columns].custom",
  exit 1. `column = "size"`: "… is the alias of core column Pts; a column predicate reads custom
  columns only". `column = "PTS"`: "… is core column Pts; …". `show T001` then exits 1.
- Override with `match = []`: `kind-invalid` at `.taskrail/overrides/feature/kind.toml`; with
  `column = "Owner"`: `stage-column-unknown` at the same path. Restored: 0 errors.

No gap against the plan.
