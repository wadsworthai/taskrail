# T065 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Launch the follow-ups T064 and T065 | — | **run 20260915-1 with T064 and T065** | The human's instruction ("lanza T063, T064 y T065"; T063 was already finished and in review). |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T065-hand-off-a-branch-whose-task-was-discard.md` (commit
`cdd7225`), its nine acceptance criteria, and on `origin/main` (`33f3531`) `task_state`, `WITH_BRANCH`,
`_handoff`, `_done_time`, `cmd_lane`'s `handed-off` check and `MOVED_ON`, which all leave a
`discarded-branch` task out of the hand-off, plus the lane's finding that `review` refuses a task that
is not `✅`. The premise holds. No code changed, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | State after hand-off | A: stays `discarded-branch`, `in_review` names it · B: `handed-off` · C: new state | **as recommended (A)** | No change to `task_state`, the dispatch counts (T064's area) or §12.7, and the state still tells a discard from a done. |
| 2 | `taskrail review` for a discarded task | include, default type `chore` · follow-up · include with the kind's type | **as recommended (include, `chore`)** | Without it a queued discarded branch cannot be published; a discard delivers no feature or fix. |
| 3 | T062's two assertions in `tests/test_autopilot_next.py` | change them here · leave to T064 | **as recommended (change them here)** | They state the behaviour this task replaces; a conflict with T064 in that file keeps both at hand-off. |
| 4 | DESIGN.md texts a–f | approve as written · change parts | **approve as written** | Decided under the human's delegation of DESIGN.md decisions; each is a phrase-level edit kept at hand-off. |
| 5 | Skill text: *Escalate* condition 1, a new paragraph before *Close and hand off* step 1, *Resume a run* step 4, gate-review *Close* third bullet | approve as written · no change | **approve as written** | The orchestrator must know a discarded lane is handed off too. T063 (in review) edits *Close and hand off* step 1 and other gate-review bullets; the new paragraph sits above step 1 and both are kept at hand-off. |
| 6 | Follow-up for detecting and cleaning up a merged discarded branch | open · record only · none | **as recommended (open)**: feature, E02, "Detect and clean up a merged branch whose task was discarded on it", verified by pytest, opened with `taskrail new` on this branch and committed on its own | `autopilot merged` requires a `✅` row and would record a discard as `done-merged`; that is its own change to `merged.py`. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T065 owns `WITH_BRANCH`, `_closed_time` (renamed from `_done_time`) and `_handoff` in `status.py`, `MOVED_ON` in `escalation.py`, the `handed-off` check in `commands.py` `cmd_lane`, the `Status.DONE` check and default type in `cli.py` `cmd_review`, its tests in `tests/test_autopilot.py`, `tests/test_review.py` and `tests/test_autopilot_skill.py`, T062's two assertions in `tests/test_autopilot_next.py`, and the approved DESIGN and skill text. T064 owns the candidate filtering in `dispatch.py` `next_lanes` and its tests. T063 (in review) owns *Close and hand off* step 1, *After a merge* step 2, gate-review's check bullets and the lane brief.** | Built from the plans reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs, adjacent tests and phrases | resolve at hand-off · serialize | **resolve at hand-off, keeping both sides** | Known conflict classes 1–3. |

## implement gate

Reviewed: commits `b58657f`, `3148216` and `afccf10` (range `4f04eea..afccf10`): `WITH_BRANCH`,
`WAITING`, `_closed_time` and `_handoff` in `status.py`, `MOVED_ON`, `cmd_lane`'s `handed-off` check,
`cmd_review` accepting a discard with `chore` as default type, the approved skill text with installed
copies, DESIGN.md a–f, one CHANGELOG bullet, follow-up T067, and ten tests shown failing before the
code. `dispatch.py` is untouched. Re-ran `taskrail checks T065 --stage implement` in the lane's
worktree: 942 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Criteria 1–9 map to tests seen failing first; the diff stays inside the touch map. |
| 2 | T067 depends on T065 | keep · clear | **as recommended (keep)** | The follow-up builds on this hand-off. |
| 3 | Four phrase replacements past the line width | keep · re-wrap | **as recommended (keep)** | Phrase-sized diffs merge with the other branches' phrases in the same paragraphs. |

## close gate

Reviewed: `1b0a1fe` (verification in a scratch repository: a running lane refused `handed-off`; after
the discard the task read `discarded-branch` with its `touched` files and no escalation, queued ahead
of a later done by its discard commit; `review --publish` titled it `chore`; after `handed-off` it
stayed `discarded-branch` with `in_review` naming it; after its branch reached `origin/main` it read
`discarded` and the next task was offered) and `dd3dce2` (`taskrail done T065` on its own). The
backlog differs from its base only in T065's row and the T067 row. No code changed after the checks
re-run at the implement gate (942 passed). `taskrail validate`: 0 errors. No upstream is configured.
`review --json`: `rebase.needed` false.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Queue the branch for hand-off | queue · changes | **queue, as `feat(taskrail)`, after T063 and T064** | Every close check holds; the verification walks the whole hand-off of a discarded branch. |

## rebase after T063 and T064

T063 (`8555317`) and T064 (`acec04a`) were merged into `main` since the branch started. The branch was
rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID, ✅ winning · stop | **unite by ID: T064 ✅, T065 ✅, T067** | Class 1. The orchestrator's resolver first kept T064 `⬜` because it looked for `✅` anywhere in the row and T064's description contains one; `taskrail validate` reported `reopen-untraced`, the resolver now reads only the status cell, and the `mark T065 done` commit was redone before anything was pushed. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |
| 4 | Conflict in `DESIGN.md`: §12.1 `autopilot next` and `autopilot lane` rows, §12.4 `discarded-branch` and `discarded` bullets | stop · keep each task's line | **T064's `autopilot next` row and `discarded` bullet with T065's `autopilot lane` row and `discarded-branch` bullet** | Each task changed a different line of the two adjacent pairs. Decided under the human's delegation. |

`status.py` merged without conflicts beside T064's `_on_mainline`. After the rebase: `taskrail checks
T065 --stage implement`: `test` 948 passed, `lint` not configured; `taskrail validate` 0 errors, 0
warnings.
