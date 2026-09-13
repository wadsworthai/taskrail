# T025 — Skip installing skills for kinds a repository does not allow

Kind: feature · Epic: E05 · Status: implemented

## Behaviour

T018 added `[kinds].allowed`, but `taskrail init` and `taskrail upgrade` still install every
skill shipped under `src/taskrail/skills/`. A repository allowing only `bug` and `chore` is
therefore still offered `taskrail-feature` and `taskrail-spike`, and its agent may pick them up
for work the repository does not accept.

Afterwards, installation installs the executor skills the repository's kinds actually use:

- **Which skills are executor skills.** A shipped skill is an *executor skill* when a core kind
  descriptor names it, in its `skill` field or in a `[[route]]`'s `skill`. The mapping comes
  from the descriptors, never from the directory name. Today that is `taskrail-bug`,
  `taskrail-chore`, `taskrail-feature` and `taskrail-spike`.
- **Which executor skills install.** An executor skill installs when a kind in the repository's
  resolved set — core, local and overrides, after `[kinds].allowed` is applied, exactly what
  `load_kinds` returns — names it in `skill` or a route. So a local `research` kind that routes
  to `taskrail-spike` installs `taskrail-spike` even when `spike` itself is not allowed.
- **Everything else always installs.** The core `taskrail` skill, and any future shipped skill
  that no core kind names, installs whatever the kinds are.
- **Skills taskrail does not ship.** A local kind naming a skill taskrail does not ship (such as
  a Spec Kit pipeline skill) is ignored by installation, as today: nothing is written and
  nothing is reported.
- **Changing `allowed`.** On the next `init` or `upgrade`, a skill that is no longer wanted is
  removed through the existing manifest rule (`Installer.remove_managed`): an unedited copy is
  deleted with its directory and listed under `removed`, and the report asks for an agent
  restart; a locally edited copy is left in place, listed under `skipped` ("no longer installed
  here, but edited locally; left in place") and stays tracked in the manifest; `--force`
  deletes it. Widening `allowed` again reinstalls the skill.
- **Report.** When executor skills are left out, the report carries one note naming them,
  `not installing skills that no allowed kind uses: taskrail-feature, taskrail-spike`, so the
  absence is explained rather than silent.
- **First `init`.** `init` seeds `.taskrail/config.toml` before reading it, and the seeded config
  has no `[kinds]` table, so a first `init` installs every skill, as today. A repository that
  already has a config with `[kinds]` gets the filtered set on its first `init`.
- **Invalid configuration.** A `config.toml` that fails to load already stops `init` and
  `upgrade`; that does not change.
- **Kind resolution errors.** Errors from kind resolution (for example `kind-allowed-unknown`
  from a typo, or an invalid local descriptor) do not stop installation, which installs from the
  resolved set as it is. But nothing the kind filter would remove is removed while they last:
  such skills stay on disk and in the manifest, and a note says so — `kind resolution reports
  errors (run `taskrail validate`), so skills no longer wanted were left in place: <paths>`.
  An install step must never delete skills because of bad input; once the config is fixed, the
  next run removes what is no longer wanted. Removals unrelated to kinds, such as the
  `.opencode/skills` copies dropped when `claude` is added, are unaffected.

Without `[kinds]` and without an override that changes a core kind's `skill`, the installed
files are exactly as today.

## Acceptance criteria

1. Without `[kinds]`, `init --integration claude` installs all five skills (`taskrail`,
   `taskrail-bug`, `taskrail-chore`, `taskrail-feature`, `taskrail-spike`), and a second run
   reports nothing created, updated, removed or skipped, and no "not installing" note.
2. With `allowed = ["bug", "chore"]` in an existing config, `init --integration claude` installs
   exactly `taskrail`, `taskrail-bug` and `taskrail-chore`; the same holds under
   `.opencode/skills` for `--integration opencode`. The report has a note naming
   `taskrail-feature` and `taskrail-spike`. A second run changes nothing.
3. In a repository installed with every skill, setting `allowed = ["bug", "chore"]` and running
   `upgrade` deletes `taskrail-feature/SKILL.md` and `taskrail-spike/SKILL.md` and their
   directories, lists both under `removed`, drops them from `.taskrail/installed.json`, and adds
   the restart note.
4. If `taskrail-feature/SKILL.md` was edited locally before that `upgrade`, it stays on disk,
   appears under `skipped` with the "edited locally; left in place" reason and remains in the
   manifest; `upgrade --force` then deletes it.
5. Removing `[kinds]` again and running `upgrade` reinstalls the removed skills under `created`.
6. A local kind in `.taskrail/types/` whose `skill` — or one of whose routes — names
   `taskrail-spike`, allowed alongside `bug`, makes `taskrail-spike` install although `spike` is
   not allowed.
7. The core `taskrail` skill installs even when `allowed` names only a local kind whose skill
   taskrail does not ship; that unshipped skill name produces no file and no error.
8. An override of an allowed core kind that replaces its `skill` with a skill taskrail does not
   ship stops that core kind's executor skill from installing (for example `bug` overridden to
   `skill = "my-bug"` no longer installs `taskrail-bug`), even without `[kinds]`.
9. With kind resolution errors (`allowed = ["bgu", "chore"]`), `upgrade` on a fully installed
   repository removes nothing, keeps every skill in the manifest, and adds a note naming the
   skills left in place and why; after fixing the config, the next `upgrade` removes the skills
   no longer wanted. A first `init` with that config still installs from the resolved set
   (`taskrail`, `taskrail-chore`) without the note.

## Affected areas

- `src/taskrail/install.py` — a new `unused_executor_skills(config)` returns the
  shipped executor skills no resolved kind names and whether kind resolution reported errors;
  `install()` filters `skill_files()` by it (whose signature does not change), withholds removals
  while there are errors, and adds the two notes.
- `src/taskrail/kinds.py` — two read-only additions: `Kind.skill_names()` (its
  `skill` plus each route's) and `core_kinds(config)` (the shipped descriptors alone). No change
  to `load_kinds`.
- `tests/test_install.py` — tests for the criteria, appended. `cli.py` is not
  changed.
- `DESIGN.md` (§5.2 resolution, §9 distribution), `README.md`
  (Task kinds) and one bullet under `## Unreleased` in `CHANGELOG.md`.

## Out of scope

- Installing skills that local kinds name but taskrail does not ship; a repository provides those
  itself.
- An `init` option to set `[kinds].allowed` or to choose skills directly, and adding a commented
  `[kinds]` example to the seeded config.
- Filtering skills per backlog; `[kinds]` applies to the whole repository.
- Changing how the core `taskrail` skill describes kinds, or rewriting executor skills to mention
  the allowlist.
- Removing unmanaged skill directories that taskrail did not write.

## Open questions and risks

- **Skill named by a disallowed kind and an allowed one.** A skill installs if any resolved kind
  names it, so sharing a skill across kinds is safe.
- **Withheld copies are not refreshed.** While kind resolution reports errors, a skill the filter
  leaves out is neither removed nor rewritten, so it may lag a CLI upgrade until the config is
  fixed.

Decisions at the plan gate (recorded in
`docs/autopilot/decisions/T025-skip-installing-skills-for-kinds-a-repos.md`): the filter applies
always, so criterion 8 holds without `[kinds]`; the report notes the executor skills left out;
with kind resolution errors, installation uses the resolved set but removes nothing and says why
in a note, which replaced the original criterion 9.

## Test coverage

All in `tests/test_install.py`.

| Criterion | Tests |
|---|---|
| 1. Without `[kinds]`: every skill, no note | `test_without_allowed_kinds_every_skill_installs_without_a_note`, `test_init_creates_a_valid_project`, `test_init_is_idempotent` |
| 2. Filtered install for claude and opencode, note, idempotent | `test_allowed_kinds_limit_the_executor_skills_installed` (both integrations) |
| 3. Narrowing removes unedited copies | `test_narrowing_allowed_kinds_removes_their_skills_on_upgrade` |
| 4. Edited copy kept until `--force` | `test_an_edited_skill_of_a_disallowed_kind_is_kept_unless_forced` |
| 5. Widening reinstalls | `test_widening_allowed_kinds_reinstalls_their_skills` |
| 6. Local kind pulls in a shipped skill | `test_a_local_kind_naming_a_shipped_skill_installs_it` (by `skill` and by route) |
| 7. Core skill always; unshipped skill ignored | `test_core_skill_installs_when_only_a_local_kind_with_its_own_skill_is_allowed` |
| 8. Override replacing a core kind's skill | `test_an_override_replacing_a_core_kinds_skill_skips_that_skill` |
| 9. Errors withhold removals | `test_kind_resolution_errors_withhold_removals_until_fixed`, `test_kind_resolution_errors_still_install_from_the_resolved_kinds` |

## Verification

Run through the real CLI (`uv run taskrail --root <tmp>`) in a throwaway
git repository whose `.taskrail/config.toml` was the default config plus `[kinds]`:

- With `allowed = ["bug", "chore"]`, `init --integration claude` created only `taskrail`,
  `taskrail-bug` and `taskrail-chore`, with the note `not installing skills that no allowed kind
  uses: taskrail-feature, taskrail-spike` and the restart note.
- Removing `[kinds]` and running `upgrade` created `taskrail-feature` and `taskrail-spike`.
- After appending a line to `taskrail-feature/SKILL.md` and restoring `allowed = ["bug",
  "chore"]`, `upgrade` removed `taskrail-spike` and skipped `taskrail-feature` (`no longer
  installed here, but edited locally; left in place`); `upgrade --force` then removed it.
- With every skill installed again and `allowed = ["bgu", "chore"]`, `upgrade` exited 0, removed
  nothing, and noted `kind resolution reports errors (run `taskrail validate`), so skills no
  longer wanted were left in place:` followed by the `taskrail-bug`, `taskrail-feature` and
  `taskrail-spike` paths; all five skills stayed. `validate` exited 1 with
  `kind-allowed-unknown` for `bgu`. After correcting the typo, `upgrade` removed
  `taskrail-feature` and `taskrail-spike` and kept `taskrail-bug`.
- A local `research` kind with `skill = "taskrail-spike"` and `allowed = ["bug", "chore",
  "research"]` made `upgrade --json` create `taskrail-spike`, noting only `taskrail-feature` as
  left out.

In this repository (no `[kinds]`, `local:.` pin), `.taskrail/bin/taskrail upgrade`
printed `8 file(s) already up to date` and `git status --short` stayed empty: its installed
skills do not change.

No difference from the plan was found.
