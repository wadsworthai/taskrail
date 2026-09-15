# T063 — Name taskrail checks in the lane brief and the autopilot skill's re-run steps

Kind: chore · Epic: E02 · Depends on: T052, T055 (both merged) · Status: implemented (scope
approved: Decisions 1–4 as recommended; implementation approved; follow-up T066). Record:
`docs/autopilot/decisions/T063-name-taskrail-checks-in-the-lane-brief-a.md`.

## Goal

T052 added `taskrail checks <ID>`, which runs a task's configured checks in its worktree, with its
autopilot lane's resource values, from any directory of the clone, as one command (DESIGN §7.5).
Its Claude Code notes already tell agents to use it, but the portable `taskrail-autopilot` text
does not name it: the lane brief tells a lane to set its resource values "for every command that
runs the checks", and the orchestrator's re-run steps say only "re-run the checks". T052's plan gate
deferred naming the command there to this chore (decision record
`docs/autopilot/decisions/T052-add-taskrail-checks-for-a-task-and-a-cla.md`, question 7), because
T055 was rewriting that text. The source finding is F11 of
[T033](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md): permission prompts dominated
because lanes and the orchestrator ran checks as `cd <worktree> && TASKRAIL_RESOURCE_…=… <command>`.

Premises checked on the base (`301ba0e`):

- `taskrail checks` exists (`src/taskrail/checks.py`, `cmd_checks` in `cli.py`) with
  `--stage` and `--check`, and passes `TASKRAIL_RESOURCE_<NAME>` from the run that lists the task.
- The Claude Code notes (`integrations/claude.md`) already name it in both skills; the core
  `taskrail` skill's step 5 names it (T052 D6).
- **Partly different from the task row.** The row speaks of "the lane brief's check commands run
  from the worktree root", quoting T052 D7 ("Checks: `<command>`, run from the worktree root").
  The shipped template `references/lane-brief.md` has never had such a line
  (`git log -S "worktree root"` and `git log -S "Checks:"` on the skill directory find nothing); it
  was in orchestrator-filled briefs. The shipped template's only check instruction is the resource
  bullet "Set them for every command that runs the checks or the application.", in both Workspace
  sections. The intent still holds: the brief names no command for the checks and asks the lane to
  pass resource values itself. Decision 1.
- Resource values after release: `lane_resources` returns the values the run still records for the
  task; `autopilot next --run` clears them for a lane no longer in use (`dispatch.py`), so after the
  refill that follows a reviewed close, `taskrail checks <ID>` passes none and the inherited
  environment decides. At hand-off and after a merge the orchestrator must still supply values no
  lane in use holds, as T055's text says.

`prior_work` in `taskrail show T063` was empty.

## Change set

### `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md`

Free in the touch map. In **both** Workspace sections — the brief's `## Workspace` and
`## Workspace (restart from the branch)` — the bullet

```markdown
- Resource values reserved for this lane: <ENVIRONMENT>. Set them for every command that runs the
  checks or the application.
```

is replaced by these two bullets:

```markdown
- Run your checks with `taskrail checks <ID>`, adding `--stage <stage>` for one stage's checks: it
  runs them in your worktree with this lane's resource values, from any directory of the clone.
- Resource values reserved for this lane: <ENVIRONMENT>. `taskrail checks` passes them to the checks
  itself; set them for every other command that runs the application.
```

### `src/taskrail/skills/taskrail-autopilot/SKILL.md`

Only *Close and hand off* step 1 and *After a merge* step 2, both free in the touch map. Nothing in
*Before the first dispatch* (T061), *Escalate* (T059, T048) or *Supervise* (T051).

*Close and hand off* step 1, currently:

```markdown
1. In the lane's worktree, run `taskrail review <ID> --json`. If `rebase.needed` is true, run
   `git rebase <rebase.onto>`, resolve only the known classes, re-run the checks and
   `taskrail validate`, record the rebase in the task's record and commit it. The refill after the
   close may have released the lane's resource values: run the checks with values that no lane in
   use holds in `status`.
```

becomes:

```markdown
1. In the lane's worktree, run `taskrail review <ID> --json`. If `rebase.needed` is true, run
   `git rebase <rebase.onto>`, resolve only the known classes, re-run the checks with
   `taskrail checks <ID>` and run `taskrail validate`, record the rebase in the task's record and
   commit it. `taskrail checks` passes the lane's resource values while its run still records them,
   but the refill after the close may have released them (its `resources` is then empty): run the
   checks with values that no lane in use holds in `status`, set as `TASKRAIL_RESOURCE_<NAME>`.
```

*After a merge* step 2, the clause "resolve only the known classes, re-run the checks with resource
values as at hand-off," becomes "resolve only the known classes, re-run the checks with
`taskrail checks <ID>` for that dependent and resource values as at hand-off,". The rest of the
step is unchanged.

### `src/taskrail/skills/taskrail-autopilot/references/gate-review.md`

Only the *Every gate* bullet "Never approve with failing checks" and the *Rebase* section's
re-run bullet, both free in the touch map. Not the *Governing documents first* bullet (T061) or the
*Close* section (T059).

```markdown
- **Never approve with failing checks.** Re-run the checks in the lane's worktree yourself, with the
  lane's resource values, before the next `autopilot next --run`, while those values are still the
  lane's own.
```

becomes:

```markdown
- **Never approve with failing checks.** Re-run the checks in the lane's worktree yourself with
  `taskrail checks <ID>`, which runs them there with the lane's resource values, before the next
  `autopilot next --run`, while those values are still the lane's own.
```

and in *Rebase: at hand-off or after a merge*,
"- Re-run the checks and `taskrail validate`, then record the rebase in the task's record." becomes
"- Re-run the checks with `taskrail checks <ID>` and run `taskrail validate`, then record the rebase
in the task's record."

Left as they are: the *implement* bullet "re-run the checks in the lane's worktree, as for every
gate" and the *Close* bullet "The checks pass, …", which point back to the *Every gate* rule.

### `tests/test_autopilot_skill.py`

One new test, `test_the_brief_and_the_re_run_steps_name_taskrail_checks`, using the existing
`autopilot_copy` fixture, so it asserts on the shipped source and on the copies `init` installs
with `--integration claude` and with `--integration opencode`, on whitespace-collapsed section
text:

- `references/lane-brief.md`, sections *Workspace* and *Workspace (restart from the branch)*: each
  contains "run your checks with `taskrail checks <id>`" and "`taskrail checks` passes them to the
  checks itself", and neither contains "every command that runs the checks".
- `SKILL.md`, *Close and hand off*: "re-run the checks with `taskrail checks <id>`" and
  "set as `taskrail_resource_<name>`"; *After a merge*: "`taskrail checks <id>` for that
  dependent".
- `references/gate-review.md`, *Every gate*: "yourself with `taskrail checks <id>`"; *Rebase: at
  hand-off or after a merge*: "re-run the checks with `taskrail checks <id>`".

The existing `test_every_taskrail_command_and_flag_shown_exists` then also covers the new
`taskrail checks <ID>` and `--stage` spans, and the existing phrase tests for T055 ("values that no
lane in use holds", "resource values as at hand-off", "re-run the checks in the lane's worktree")
keep passing.

### `CHANGELOG.md`

One bullet under *Unreleased*, as T052 and T055 did (Decision 3):

```markdown
- **The autopilot text names `taskrail checks`.** The lane brief tells a lane to run its checks
  with `taskrail checks <ID>`, which passes its resource values itself, and the
  `taskrail-autopilot` skill's gate, rebase, hand-off and after-merge steps re-run a lane's checks
  with it (T063).
```

### Installed copies in this repository

`.taskrail/bin/taskrail upgrade`, as CLAUDE.md says, rewrites
`.claude/skills/taskrail-autopilot/SKILL.md`,
`.claude/skills/taskrail-autopilot/references/lane-brief.md`,
`.claude/skills/taskrail-autopilot/references/gate-review.md` and their digests in
`.taskrail/installed.json`.

### This artifact

And its row in `docs/chores/README.md`.

## Decisions needed

1. **The task row's premise.** The shipped lane brief never had a "Checks: `<command>`, run from
   the worktree root" line; that was in orchestrator-filled briefs. Recommendation: proceed — the
   intent holds on the template as shipped (it names no check command and asks the lane to pass
   resource values to the checks itself), so the change adds the `taskrail checks` bullet and
   narrows the resource bullet to the application. Alternatives: (b) escalate as a false premise
   (condition 6) and edit the row first with `taskrail edit`; (c) change only the skill's re-run
   steps and leave the brief as is.
2. **`DESIGN.md`.** Recommendation: leave it unchanged. §7.5 defines `taskrail checks`, the §8
   `claude` row already says lane checks are re-run with it, and §12.7/§12.8 describe *that* the
   orchestrator re-runs checks, not the command. Alternative: in §12.8 *Publishing*, "rebases when
   needed, re-runs the checks, then runs" becomes "rebases when needed, re-runs the checks with
   `taskrail checks <ID>` (§7.5), then runs".
3. **CHANGELOG bullet.** Recommendation: add the bullet above, as T052 and T055 did for skill text.
   Alternative: none, since only skill text changes.
4. **Follow-up for released resource values.** After the refill releases a lane's values,
   `taskrail checks` passes none, so the hand-off and after-merge re-runs need an environment prefix
   (`TASKRAIL_RESOURCE_<NAME>=… taskrail checks <ID>`), the shape F11 and the Claude Code notes warn
   against. Recommendation: open a follow-up at the docs stage with `taskrail new` on this branch —
   kind feature, epic E02, no dependencies, title "Pass chosen resource values to taskrail checks
   for a lane whose values were released", description "Add `taskrail checks <ID> --resource
   NAME=VALUE` so the orchestrator's hand-off and after-merge re-runs pass values no lane in use
   holds without an environment prefix; verified by a test_checks.py test." Alternatives: (b) no
   follow-up, keeping the environment prefix (this repository configures no resources, so it never
   hits it); (c) widen this chore to the CLI, which the task row does not cover.

## Out of scope

- Any CLI change, including the `--resource` flag of Decision 4.
- The Claude Code and OpenCode integration notes (`integrations/*.md`), already done by T052/T056.
- The core `taskrail` skill (step 5 already names `taskrail checks`, T052 D6).
- `references/decision-record.md`, whose "the checks re-run and their results" is a record field,
  not a step.
- Skill areas the touch map gives other lanes: *Before the first dispatch* and the gate-review
  *Governing documents first* bullet (T061); *Escalate* and the gate-review *Close* section (T059,
  T048); the *Supervise* overlaps bullet (T051).
- `CLAUDE.md` and `TODO.md` beyond the close's own row change.

## Verification

- The new test observed failing on the unchanged skill text for all three copies (source, `claude`,
  `opencode`), then passing after the edits.
- `init --integration claude --integration opencode` in a throwaway repository from this branch's
  source, reading the installed `lane-brief.md`, `SKILL.md` and `gate-review.md` for the new text.
- `.taskrail/bin/taskrail upgrade`, then the installed copies equal the sources plus the Claude Code
  note (`git diff` shows the same hunks in `.claude/skills/taskrail-autopilot/`).
- `taskrail --root <worktree> checks T063` (the `test` check: `uv run
  pytest -q`; `lint` is not configured), exercising the command the new text names on this task.
- `taskrail validate`.

Results:

- The new test, before any skill edit:
  `uv run pytest -q tests/test_autopilot_skill.py -k
  test_the_brief_and_the_re_run_steps_name_taskrail_checks` → `3 failed, 44 deselected` — the
  `source`, `claude` and `opencode` copies each failing with `AssertionError: Workspace`: the phrase
  "run your checks with `taskrail checks <id>`" was not in a *Workspace* section that still read
  "… every command that runs the checks or the application.". Re-run after each file's edit, so
  every group of assertions was seen failing: after the lane brief, `3 failed` on "re-run the checks
  with `taskrail checks <id>`" in *Close and hand off*; after `SKILL.md`, `3 failed` on "yourself
  with `taskrail checks <id>`" in *Every gate*; after `gate-review.md`,
  `tests/test_autopilot_skill.py` `47 passed`, including
  `test_every_taskrail_command_and_flag_shown_exists` over the new `taskrail checks <ID>` and
  `--stage` spans and the T055 phrase tests.
- `.taskrail/bin/taskrail upgrade --json` in the worktree: `updated`
  `.claude/skills/taskrail-autopilot/SKILL.md`, `references/gate-review.md` and
  `references/lane-brief.md`; `.taskrail/installed.json` digests rewritten. The installed
  `lane-brief.md` and `gate-review.md` equal the sources (`git diff --no-index`, no output), and
  the installed `SKILL.md` diff has the same two hunks as the source's.
- Throwaway `git init /tmp/t063-init-check`, then this branch's
  `taskrail --root /tmp/t063-init-check init --integration claude --integration opencode --json`:
  `grep -rn "taskrail checks"` in the installed `.claude/skills/taskrail-autopilot` finds the brief
  bullets at lines 28/30 and 84/86, `gate-review.md` lines 13 and 72, `SKILL.md` lines 134–135 and
  154, and the existing Claude Code note at line 228. The repository was deleted afterwards.
- That a lane's resource values reach its checks through `taskrail checks` is T052's
  `test_checks.py::test_the_lane_resources_reach_the_checks_before_and_after_done`, which passes in
  the full run below.
- `taskrail --root <worktree> checks T063 --stage implement` → `test` `870 passed in 86.95s`,
  `lint` not configured, `T063 in <worktree>: passed`, exit 0.
- `taskrail --root <worktree> validate` → `61 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- `DESIGN.md` unchanged (Decision 2).

## Docs

No README, `CLAUDE.md` or `DESIGN.md` text describes the changed steps, so none changed. The
follow-up of Decision 4 is **T066** (feature, E02, no dependencies), "Pass chosen resource values to
taskrail checks for a lane whose values were released", opened with `taskrail new` on this branch
(commit `3e0a8bc`).

## Risks

- **Adjacent-line conflicts at hand-off.** T061 changes the gate-review *Governing documents first*
  bullet, directly above *Never approve with failing checks*; T059 changes the gate-review *Close*
  section, directly above *Rebase*. Git may report these as conflicts though the edits are
  disjoint; each side's sentences are kept. Installed copies and `installed.json` are known class 3.
