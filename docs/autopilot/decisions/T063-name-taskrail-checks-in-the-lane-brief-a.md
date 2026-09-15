# T063 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Continue the autopilot with the follow-up tasks | — | **run 20260914-2 with T059, T061, T062 and T063, each dispatched once its row reaches `main`** | The human's instruction. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope in `docs/chores/T063-name-taskrail-checks-in-the-lane-brief-a.md` (commit
`7d79e16`) with the exact text for `lane-brief.md`, the skill's *Close and hand off* step 1 and
*After a merge* step 2, and `gate-review.md`'s *Never approve with failing checks* and *Rebase*
bullets; the lane's search showing the shipped lane brief never named a check command; and
`checks.py`/`dispatch.py` on `origin/main` (`301ba0e`), which confirm that a released lane's values
are no longer passed. Nothing else is edited yet.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Task row premise | proceed · escalate as false premise · re-run steps only | **as recommended (proceed)** | The "run from the worktree root" line was in the briefs this orchestrator filled, not in the template; the aim — the brief and the re-run steps name `taskrail checks` — holds, so this is not a premise that changes the work. |
| 2 | DESIGN.md | unchanged · name the command in §12.8 *Publishing* | **as recommended (unchanged)** | §7.5 and the §8 `claude` row already define and name it. |
| 3 | CHANGELOG bullet | add · none | **as recommended (add)** | Consumers get changed skill text. |
| 4 | Follow-up for released resource values | open · none · widen this chore | **as recommended (open)**: feature, E02, "Pass chosen resource values to taskrail checks for a lane whose values were released", verified by a `test_checks.py` test, opened at the docs stage with `taskrail new` on this branch | The environment-prefix command it would otherwise need is the shape F11 warns against; the CLI change is outside a chore about text. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T063 owns both Workspace resource bullets of `references/lane-brief.md`, *Close and hand off* step 1 and *After a merge* step 2 of the skill, gate-review's *Never approve with failing checks* and *Rebase* bullets, and one test in `tests/test_autopilot_skill.py`. T061 (closed) owns *Before the first dispatch* and *Governing documents first*; T059 (closed) *Escalate* and gate-review *Close*; T048 (unmerged) the end of *Escalate*; T051 (unmerged) *Supervise*.** | Built from the plans reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs, adjacent bullets | resolve at hand-off · serialize | **resolve at hand-off, keeping both sides** | Known conflict classes 1–3; adjacent bullets from different tasks are kept. |

## implement gate

Reviewed: commit `45b5f11` (range `2de2fd3..45b5f11`): both Workspace bullets of `lane-brief.md`,
*Close and hand off* step 1 and *After a merge* step 2 of the skill, gate-review's *Never approve
with failing checks* and *Rebase* bullets, installed copies and digests, one CHANGELOG bullet, and a
test over the source and both integrations' copies, shown failing on each file before its edit. Re-ran
`taskrail checks T063 --stage implement` in the lane's worktree: 870 passed, `lint` not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | The diff is the approved text only; every section's assertions were seen failing first. |

## close gate

Reviewed: `3e0a8bc` (follow-up T066, feature, E02), `96016d3` (artifact docs stage) and `51dd6b1`
(`taskrail done T063` on its own). The backlog differs from its base only in T063's row and the T066
row. No skill text or test changed after the checks re-run at the implement gate (870 passed; the
lane's `taskrail checks T063` before closing also passed). `taskrail validate`: 0 errors. No upstream
is configured. `review --json`: `rebase.needed` true onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Queue the branch for hand-off | queue · changes | **queue, as `docs(taskrail)`** | Skill text, lane brief and a test; no CLI behaviour changes, as for T055 and T056. |

## rebase after the merged tasks

T053, T056, T048, T051, T047, T061, T059 and T062 (`33f3531`) were merged into `main` since the branch
started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/chores/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID, ✅ winning · stop | **unite by ID: T062 ✅, T063 ✅, T064, T065, T066** | Class 1. The first resolution of the `mark T063 done` commit left T062 `⬜`; `taskrail validate` reported it as `reopen-untraced`, and the commit was redone with T062 `✅` before anything was pushed. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |

The skill source, lane brief, gate review and `test_autopilot_skill.py` merged without conflicts beside
T059 and T061's sections. After the rebase: no conflict markers, `taskrail checks T063 --stage
implement`: `test` 937 passed, `lint` not configured; `taskrail validate` 0 errors, 0 warnings.
