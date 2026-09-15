# T055 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing` (T060)** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope in `docs/chores/T055-fix-the-autopilot-skill-text-found-wrong.md` (commit
`946ce5f`) with the exact skill, lane-brief, DESIGN and CHANGELOG text, and the premises the lane
checked on `origin/main` (`1631ab8`): `OCCUPYING` excludes `done-branch` (F5), `ids.reserve` locks in
the common directory (F6), `dispatch_live` expires after the claim grace (F7), and `claims.create`
accepts a repeat claim by the same owner and branch (F2). This run's orchestrator already refills on
`done-branch` and was told the IDs premise at T049's implement gate. Nothing else is edited yet.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §12.3 first paragraph and lane-contract bullet, §12.7 resource sentence, §12.8 hand-off bullet | approve all · only §12.3 | **as recommended (approve all)** | §12.7 and §12.8 would otherwise contradict the new skill text. Decided by the orchestrator under the human's delegation; the edits avoid T056's §12.3 sentence and the §12.1 rows other lanes change. |
| 2 | Resource values after an early refill | skill rule · CLI keeps values until hand-off · refill at hand-off | **as recommended (skill rule)** | Fixes F5 without changing §12.7's release rule; a CLI change is not needed while no repository here configures resources. |
| 3 | Which installed copies the tests read | copies `init` installs · also this repository's copy | **as recommended (`init` copies)** | Keeps the tool's tests independent of this checkout, as T056 did. |
| 4 | When a `running` lane is restarted | once `silent` · as soon as the handle fails | **as recommended (once `silent`)** | Two sub-sessions must never write in one worktree. |
| 5 | Hand-off message body | always · only without a link | **as recommended (always)** | The finding was exactly a hand-off without title and body. |
| 6 | CHANGELOG entry | add · none | **as recommended (add)** | Consumers get changed skill text. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T055 owns `taskrail-autopilot` SKILL.md *Dispatch* steps 6–7 and the IDs paragraph, *Close and hand off* steps 1 and 4, *After a merge* step 2, the new *Resume a run* section, `references/lane-brief.md`, its five tests in `tests/test_autopilot_skill.py`, and the DESIGN §12.3 first paragraph and lane bullet, §12.7 resource sentence and §12.8 hand-off bullet. T049 owns *Escalate* condition 1 and gate-review *Close*; T048 the paragraph at the end of *Escalate*; T050 (merged) the `--gate close` sentence; T051 the *Supervise* `overlaps` bullet; T056 the OpenCode note and its §12.3 sentence; T052 (later) the Claude Code note.** | Built from the gates reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs, adjacent new tests in `test_autopilot_skill.py` | resolve at hand-off · serialize | **resolve at hand-off, keeping every entry** | Known conflict classes 1–3; new test functions added at the same place are kept side by side, as at T049's rebase. |

## implement gate

Reviewed: commit `9e02945` (range `6b29f2b..9e02945`): the approved *Dispatch*, *Close and hand off*,
*After a merge* and *Resume a run* text in the skill source, `references/lane-brief.md` with the
restart section, their installed copies and digests, the four approved DESIGN.md edits (§12.3 ×2,
§12.7, §12.8), one CHANGELOG bullet at the end of *Unreleased*, and five tests over the source and
both integrations' installed copies, shown failing (15 cases) before the edit. *Escalate*,
*Supervise*, `gate-review.md` and the integration notes are untouched. The lane's scripted check gave
two worktrees distinct IDs (T001, T002). Re-ran `uv run pytest -q` in the
lane's worktree: 846 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · wording changes | **approve** | Each finding (F2, F4, F5, F6, F7) maps to text and a test seen failing first; the diff stays inside the touch map. |

## close gate

Reviewed: `e366fe2` (artifact *Docs*: the taskrail README needs no change; the T007 and T033 spike
documents keep their historical wording) and `8c888af` (`taskrail done T055` on its own, changing only
T055's row). No code, skill or test changed after the checks re-run at the implement gate (846
passed). `taskrail validate`: 0 errors. No upstream is configured. `review --json`: `rebase.needed`
false.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch | queue · changes | **queue, as `docs(taskrail)`** | Skill text, lane brief, design text and tests; no CLI behaviour changes, as for T056. |

## rebase after T049, T060 and T054

T050 (`1631ab8`), T049 (`ff8e4e6`), T060 (`502ea3b`) and T054 (`4420c8d`) were merged into `main`
since the branch started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/chores/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2: appended index rows and *Unreleased* bullets. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`** | Class 3; the rewritten digests match the merged skill sources. |
| 4 | Conflict in `tests/test_autopilot_skill.py` | keep both · stop | **keep both** | T049's test and T055's new section of tests were added at the same place; no existing line changed. |

After the rebase: no conflict markers (`git diff --check` clean), the installed autopilot skill equals
its source above the harness notes, `uv run pytest -q` 857 passed,
`taskrail validate` 0 errors.
