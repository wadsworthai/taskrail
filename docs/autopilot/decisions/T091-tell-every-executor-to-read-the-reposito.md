# T091 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T091-tell-every-executor-to-read-the-reposito.md` at commit ae03e38, the diff
range against the base (the artifact and one index row; the skill source untouched, as `scope`
requires), `taskrail checks T091 --stage scope` (`no checks` … `passed`), `taskrail validate` (82
tasks, 0 errors), step 5 of the core skill as it stands, `taskrail-chore/SKILL.md:24-25` as the only
existing pointer, and `tests/test_skills_current_branch.py`, whose `skill_copy` fixture reads each
skill from the source and from both integrations' installed copies.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the wording? | as quoted · "where the repository has them" · end at "and follow them" · "instructions for the agents that work in it" | **as quoted, as recommended** | It names no principle, agent, file or layout, reuses `taskrail-chore`'s existing phrase, and "if it has any" keeps it true in a repository that has no such file. "Before the first stage" says "before it plans" without naming a stage, which matters because `plan` belongs to `feature` alone — the same defect T090 is fixing in `CLAUDE.md`. |
| 2 | Approve the place — first sentence of step 5, *Stages*? | step 5 · end of step 4 *Claim* · step 2 *Inspect* · a new section | **step 5, as recommended** | A new section or a tenth step would make `DESIGN.md` §8's nine-step list wrong and pull that document into this chore. Step 2 is about reading `show`, the task rather than the repository; step 4 is about claiming. |
| 3 | Leave `taskrail-chore`'s line unchanged? | leave it · delete the overlapping clause | **leave it, as recommended** | Its list is the area's conventions at `scope` time; the core line is the repository-wide habit before any kind plans. The overlap is one clause, and removing it would edit a second shipped skill for no measured gain. |
| 4 | Add the test, and where? | in `tests/test_skills_current_branch.py` · a new module · no test | **in that module, with two corrections** | Its `skill_copy` fixture already covers the source and both installed copies, which is exactly the property to protect; a new module for one assertion would duplicate the fixture. Corrections: (a) the assertion must compare case-insensitively or quote the sentence as written — the text begins "Before", so the drafted `"before the first stage, …" in text` would fail; lower-case the extracted step once and match against that, and lower-case it for the forbidden words too, or `Claude` would slip through; (b) the module's docstring names T084 only, so extend it to say it also covers the repository-instructions pointer, since a reader takes that docstring as the module's scope. |
| 5 | A `CHANGELOG.md` bullet under `## Unreleased`? | yes · no | **yes — the touch map is widened to `CHANGELOG.md` for this** | The line ships to every consumer at the next release and 0.3.0 recorded skill-text changes the same way. `CHANGELOG.md` is a known conflict class, so a parallel lane appending its own bullet costs nothing to resolve. |
| 6 | Pull request type and scope? | `docs(skills)` · `chore` · `feat(skills)` | **`feat(skills)`** | Departing from the lane's recommendation. The same reasoning that earns a changelog entry decides the type: this adds an instruction every executor follows in every consuming repository after `upgrade`, which is a change in what the tool does, not a documentation edit. The precedent is `feat(skills): teach the skills the current-branch workflow, on-done commits and decisions gates (T084)`. The kind's default `chore` would undersell it. |

Instructions given with the answers: observe the new test fail against the unchanged skill text
before it passes; run `.taskrail/bin/taskrail upgrade` rather than editing any installed copy, commit
what it rewrites, and run it a second time to show it is idempotent; run the full suite with a
generous timeout and record its real output.

## implement gate

Reviewed: the diffs of `src/taskrail/skills/taskrail/SKILL.md` and of the installed copy
`.claude/skills/taskrail/SKILL.md` read by commit range in the lane's worktree — the same three-line
hunk in both, inside step 5, naming no agent, principle or file; the six files of commit 368a408
against the approved change set; and `taskrail checks T091 --stage implement` re-run by the
orchestrator: 1186 passed in 165.55s, `lint` not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the applied change what was approved? | accept · amend | **accepted; the sentence is verbatim and the change set is the six approved files** | The source and the installed copy carry the identical hunk, `upgrade` wrote the copy and a second run reported everything up to date, and the test was observed failing on all three parametrisations — source, claude, opencode — before it passed. |
| 2 | The orchestrator's lower-case correction at the `scope` gate | apply it · drop it | **dropped: the correction was wrong** | The lane checked and the orchestrator confirmed it: `step()` returns `flat()`, which collapses whitespace *and* lower-cases (`tests/test_autopilot_skill.py:50-52`), so the assertion already compares lower-cased text and a capitalised `Claude` cannot slip past. Adding `.lower()` would have been redundant. The docstring half of that correction was applied and stands. |
| 3 | `.taskrail/installed.json` now records `"version": "v0.4.0"` instead of `v0.3.0` | keep · revert by hand | **keep** | Not an edit of the lane's: `upgrade` writes `release_tag()` of the running CLI, and `main` is at `0.4.0.dev0` since T086. T086's own decision 2 anticipated exactly this — "the next `.taskrail/bin/taskrail upgrade` on `main` rewrites it" — and left it to land in the next upgrade, which is this one. Nothing reads the field back and this repository pins `local:.`, so no behaviour changes; reverting would mean hand-editing a generated file so that it disagreed with its generator. |
| 4 | The `CHANGELOG.md` bullet as written | accept · amend | **accepted** | It states the behaviour change in the user's terms, names `taskrail upgrade` as what installs it, and carries the task ID, as 0.3.0's entries do. |

Instructions given with the answers: run the `docs` stage, then close; the branch's rebase onto the
`main` that now carries T088 is the orchestrator's at hand-off, not the lane's.

## rebase after T088 and T090 merged

`review T091 --json` reported `rebase.needed: true`. The orchestrator rebased at hand-off, while the
lane was stopped at the `close` gate:

```
git rebase origin/main
```

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `docs/chores/README.md` and `docs/autopilot/decisions/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, appended index rows. |
| 2 | `TODO.md`: the status cells of T090 and T091 | keep all rows, `✅` wins per ID · stop | **one row per ID, `✅` from whichever side has it** | Known class 1, backlog rows united by ID. T090 arrived `✅` from the mainline, T091 `✅` from this branch, and neither side carries a `Reopens:` commit the other lacks. |

**A mistake the orchestrator made and corrected, recorded because the branch shows it.** The first
resolution of conflict 2 kept both sides' lines instead of uniting them by ID, which duplicated the
T090 and T091 rows; `taskrail validate` caught it immediately with two `task-duplicate` errors at
`TODO.md:133` and `:134`. The rows were united by ID with the `✅` cell winning, and the closing
commit was amended. Validation after the fix: 87 tasks, 0 errors, 0 warnings; `git diff --check`
clean; `taskrail checks T091` passed. The lesson is in the class itself: class 1 unites rows **by
ID**, and a generic keep-both resolution is right for appended index rows (class 2) and wrong here.

After the rebase: six commits ahead of `origin/main`, the branch's diff adding only this task's own
files and rows.

## Conflict handling agreed for all lanes

Run 20260918-1. T090 and T091 adopt T087's verdict in separate areas.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T091 edits `src/taskrail/skills/taskrail/SKILL.md`, the test module, `CHANGELOG.md` and what `upgrade` rewrites; T090 edits `CLAUDE.md` only** | The two halves of T087's verdict were opened as separate tasks: one is this repository's own text, the other ships to every consumer. |
| 2 | What do they share? | nothing · the backlog file and the indexes | **`TODO.md` and `docs/chores/README.md`** | Backlog rows are known class 1, appended index rows known class 2; `CHANGELOG.md` is the third known class. All are resolved by the orchestrator at hand-off. |
| 3 | Installed copies | edit by hand · through `upgrade` | **through `upgrade` only** | `CLAUDE.md` states that the skills under `.claude/skills/taskrail*` are installed copies: edit the source and upgrade. `.taskrail/installed.json` and the copies it records are a known conflict class, resolved with `taskrail upgrade --force`. |
