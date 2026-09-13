# T018 — Restrict the task kinds a repository allows

Kind: feature · Epic: E05 · Status: implemented

## Behaviour

A repository can state the closed set of task kinds it allows, in `.taskrail/config.toml`:

```toml
[kinds]
allowed = ["spec", "bug", "chore"]   # omit the table, or the key, to allow every defined kind
```

taskrail always ships the core kinds `bug`, `chore`, `feature` and `spike`. Today a repository
whose own rules name exactly three kinds cannot make taskrail enforce that: every core kind is
always resolved, so a `feature` row passes `validate`. With `allowed` set:

- **Resolution.** Kinds are still resolved in layers (core, then `.taskrail/types/`, then
  `.taskrail/overrides/`), and every descriptor is still parsed and checked. The allowlist is
  applied to the resolved set afterwards, so it covers core, local and overridden kinds the same
  way. A kind that is not allowed is left out of the project: `kind list` does not show it,
  `show` has no descriptor for it, and no command resolves it.
- **Validation.** A task whose kind is defined but not allowed is an error with its own code,
  `task-kind-disallowed`, reported with file and line and naming the allowed kinds — distinct
  from `task-kind-unknown`, which stays for kinds nothing defines. As with every validation
  error, commands that refuse an invalid backlog (`show`, `claim`, `new`, `done`, `review`, …)
  refuse it too.
- **A stale allowlist.** A name in `allowed` that no core, local or override kind defines is a
  validation error, `kind-allowed-unknown`, so a typo cannot silently shrink the set.
- **Unused local work.** A kind defined under `.taskrail/types/` or `.taskrail/overrides/` that
  `allowed` leaves out is a warning, `kind-not-allowed`: the repository wrote a descriptor it
  then excluded, which is most likely a mistake. Excluded core kinds are silent — excluding them
  is the point of the setting.
- **Creating tasks.** `taskrail new --kind feature` in such a repository writes nothing: without
  `--workspace` the in-memory validation reports `task-kind-disallowed` (exit 1); with
  `--workspace` it refuses before creating a branch, saying the kind is not allowed (exit 2).
- **Configuration errors.** `[kinds]` must be a table; `allowed` must be a non-empty list of
  kind names (lowercase letters, digits and dashes) without repeats. Anything else is a
  configuration error (exit 2), like the rest of `config.toml`.

Without `[kinds]`, behaviour is unchanged.

## Acceptance criteria

1. With no `[kinds]` table, the resolved kinds and validation results are exactly as today.
2. With `allowed = ["bug", "chore"]`, `load_kinds` resolves only `bug` and `chore`, and
   `kind list --json` lists only those two.
3. A task of a core kind left out of `allowed` fails `validate` with `task-kind-disallowed` at
   its file and line, and the message names the allowed kinds; a task of a kind nothing defines
   still fails with `task-kind-unknown`.
4. A local kind under `.taskrail/types/` that is named in `allowed` resolves and validates its
   tasks; one that is not named is excluded and produces a `kind-not-allowed` warning.
5. An override of a kind that `allowed` leaves out is excluded and produces a
   `kind-not-allowed` warning; an override of an allowed kind still replaces it.
6. A name in `allowed` that no layer defines fails `validate` with `kind-allowed-unknown`.
7. `[kinds]` that is not a table, `allowed` that is not a list, is empty, holds a non-string or a
   malformed name, or repeats a name, raises a configuration error naming the problem.
8. `new --kind <disallowed>` writes nothing and exits non-zero, both without `--workspace`
   (exit 1) and with it (exit 2, before any branch or worktree is created).

## Test coverage

All in `tests/test_allowed_kinds.py`.

| Criterion | Tests |
|---|---|
| 1. No `[kinds]` table: unchanged | `test_without_kinds_table_every_defined_kind_is_allowed` |
| 2. Only allowed kinds resolve; `kind list` | `test_only_allowed_core_kinds_resolve` |
| 3. `task-kind-disallowed` vs `task-kind-unknown` | `test_task_of_a_disallowed_kind_is_an_error_naming_the_allowed_kinds`, `test_closed_tasks_of_a_disallowed_kind_are_errors_too`, `test_undefined_kind_is_still_unknown_with_an_allowlist` |
| 4. Local kinds | `test_allowed_local_kind_resolves_and_validates_its_tasks`, `test_local_kind_left_out_of_the_allowlist_is_excluded_with_a_warning` |
| 5. Overrides | `test_override_of_a_disallowed_kind_is_excluded_with_a_warning`, `test_override_of_an_allowed_kind_still_replaces_it` |
| 6. `kind-allowed-unknown` | `test_allowed_name_that_no_layer_defines_is_an_error` |
| 7. Configuration errors | `test_malformed_kinds_table_is_a_configuration_error` (six cases) |
| 8. `new` writes nothing | `test_new_with_a_disallowed_kind_writes_nothing`, `test_new_in_a_workspace_with_a_disallowed_kind_refuses_before_branching`, `test_new_in_a_workspace_with_an_undefined_kind_says_it_is_not_defined` |

## Affected areas

- `src/taskrail/config.py` — a new `allowed_kinds: tuple[str, ...]` field on
  `Config` and a self-contained block parsing `[kinds]`. Kept to small, separate hunks because
  T021 (column aliases) edits the same file in parallel.
- `src/taskrail/kinds.py` — `load_kinds` applies the allowlist after resolution
  and reports `kind-allowed-unknown` and `kind-not-allowed`. Its signature does not change. A
  new `defined_kind_names(config)` lists every kind a layer has a descriptor for, so callers can
  tell a kind the allowlist excluded from one nothing defines; the layer tuple moved into a
  `_layers(config)` helper both functions share.
- `src/taskrail/project.py` — `_check_tasks` reports `task-kind-disallowed` for a
  kind that is defined but excluded, and keeps `task-kind-unknown` for any other.
- `src/taskrail/cli.py` — the `new --workspace` refusal message distinguishes a
  disallowed kind from an undefined one.
- `tests/test_allowed_kinds.py` — a new file with the tests for the criteria, so
  no existing test file changes.
- `DESIGN.md` (§3.3 `Kind` value, §4 configuration example, §5.2 resolution),
  `README.md` (Task kinds) and one line under `## Unreleased` in
  `CHANGELOG.md`.

## Out of scope

- Skipping the executor skills of disallowed core kinds when `init` or `upgrade` installs
  skills: `taskrail-feature` and `taskrail-spike` are still installed. Installation does not
  read the resolved kinds today; this would be a follow-up task if wanted.
- A denylist (`disabled = [...]`) alongside the allowlist. An allowlist matches rules that name a
  closed set, and a core kind added by a later taskrail release stays excluded instead of
  appearing silently.
- Per-backlog allowlists; `[kinds]` applies to every backlog in the repository.
- Adding a commented `[kinds]` example to the config that `taskrail init` writes.
- Migrating or rewriting existing rows whose kind becomes disallowed.

## Open questions and risks

- **Closed tasks of a disallowed kind.** A repository adopting taskrail with history may have
  done or discarded rows of a kind it no longer allows. The plan rejects them like pending ones,
  consistent with `task-kind-unknown` today, which ignores status. The alternative is a warning
  for closed tasks and an error only for pending ones.
- **Name of the setting.** `[kinds] allowed` follows the task title; `enabled` would read
  equally well.
- **Parallel edits to `config.py`.** T021 also changes config loading; the hunks here are kept
  small so a rebase conflict, if any, is mechanical.

Decisions at the plan gate: an allowlist named `[kinds] allowed`; tasks of a disallowed kind are
errors whatever their status; skipping the skills of disallowed kinds at install time stays out
of scope and becomes a follow-up task.

## Verification

Run through the real CLI (`uv run taskrail`) in a throwaway git
repository created with `taskrail init`, holding one epic and three tasks (T001 `bug`, T002
`feature`, T003 `chore`), after appending `[kinds]` with `allowed = ["bug", "chore"]`:

- `validate` exited 1 with `TODO.md:14: error: kind `feature` is not allowed (kinds.allowed:
  bug, chore) [task-kind-disallowed]`; `show T001` refused with exit 1 for the invalid backlog.
- `kind list` printed only `bug` and `chore`, both `core`.
- With T002 retyped as `chore`, `validate` reported 0 errors and `show T001` printed the `bug`
  stages and `skill taskrail-bug`.
- `new --kind feature` exited 1 with `task-kind-disallowed` and `nothing was written`; `git
  status --porcelain` was empty. With `--workspace` it exited 2 with `kind `feature` is not
  allowed (kinds.allowed: bug, chore)`, and `git branch --list` still showed only `main`, with no
  `.worktrees` directory. `new --kind spec --workspace` exited 2 with `kind `spec` is not
  defined`.
- With a local `research` kind, an override of `spike` and `allowed = ["bug", "chore", "spec"]`,
  `validate` exited 1 with `kind-allowed-unknown` for `spec` and a `kind-not-allowed` warning
  for each of `.taskrail/overrides/spike/kind.toml` and `.taskrail/types/research/kind.toml`.
- With `allowed = ["bug", "chore", "research"]` and T002 retyped as `research`, `validate`
  exited 0 with only the `spike` override warning, and `kind list` added `research local`.
- `allowed = []` exited 2 with `kinds.allowed must name at least one kind; omit it to allow
  every kind`.
- Without `[kinds]`, `kind list` printed all four core kinds and `validate` reported 0 errors.

No difference from the plan was found.
