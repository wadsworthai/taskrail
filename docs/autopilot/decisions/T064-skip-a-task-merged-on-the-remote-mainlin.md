# T064 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Launch the follow-ups T064 and T065 | — | **run 20260915-1 with T064 and T065** | The human's instruction ("lanza T063, T064 y T065"; T063 was already finished and in review). |

Answered by the human (repository owner), in the orchestrator session.

## diagnose gate

Reviewed: the diagnosis in `docs/bugs/T064-skip-a-task-merged-on-the-remote-mainlin.md` (commit
`7a90c44`) with its scripted reproduction (after a merge into `origin/main` that was not pulled,
`status` reads the task `done-merged` or `discarded` while `autopilot next --run` dispatches it again;
the same for a task closed from another clone), and on `origin/main` (`33f3531`) `next_lanes`, which
takes candidates from `query.eligible` and never consults `done_on_mainline`, and `_on_mainline`,
which has no reopen rule across the two mainline refs. The root cause is located. No code changed, so
no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Diagnosis and fix 1–4, reported in `skipped` | skip with a reason · drop silently | **as recommended (skip with a reason)** | Plain `next` still offers the task, so the reason tells the orchestrator its local mainline is behind. |
| 2 | Reopen rule in `_on_mainline` | include · accept the gap · follow-up | **as recommended (include)** | Without it the new skip would hide a task reopened locally and not yet pushed, which `next` offers correctly today. |
| 3 | Plain `next`, `show` and `claim` | record only · follow-up bug | **as recommended (record only)** | They read the checkout by design (§7), and a workspace started from `base.onto` refuses the claim. |
| 4 | DESIGN.md (a)–(c) and the CHANGELOG bullet | approve as written · change | **approve as written** | Decided under the human's delegation of DESIGN.md decisions. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T064 owns the candidate loop and cache warm-up in `dispatch.py` `next_lanes`, `_on_mainline` in `status.py`, and two tests in `tests/test_autopilot_next.py`. T065 owns `WITH_BRANCH`, `_handoff` and `_closed_time` in `status.py`, `MOVED_ON`, `cmd_lane`'s `handed-off` check, `cmd_review`, and T062's two assertions in `tests/test_autopilot_next.py`. T063 (in review) edits only skill text and the lane brief.** | Built from the plans reached so far; a conflict between the two test edits in one file keeps both. |
| 2 | CHANGELOG, TODO.md, index READMEs, same-line DESIGN rows | resolve at hand-off · serialize | **resolve at hand-off, keeping every phrase** | Known conflict classes 1–2. |

## fix gate

Reviewed: commit `4cba750` (range `5ef7cef..4cba750`): the new first skip reason and cache warm-up in
`dispatch.py` `next_lanes`, `_reopened_elsewhere` and its use in `_on_mainline`, three new tests in
`tests/test_autopilot_next.py` shown failing on the unfixed code (the preview dispatching `T001`, and a
local reopen still reading `done-merged`), the approved DESIGN.md (a)–(c) and CHANGELOG bullet. Re-ran
`taskrail checks T064 --stage fix` in the lane's worktree: 937 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · changes | **approve** | The tests cover both closings, a removed lane branch, the pull and the reopen rule; the diff stays inside the touch map. |
| 2 | Follow-ups for an uncommitted reopen or a recorded merge after a reopen | none · bug in E02 | **as recommended (none)** | A reopen is committed by procedure, and a recorded merge only counts while its commit stays on the mainline. |

## close gate

Reviewed: `bffa248` (`taskrail done T064` on its own, changing only T064's row). Impact had nothing to
open. No code changed after the checks re-run at the fix gate (937 passed). `taskrail validate`: 0
errors. No upstream is configured. `review --json`: `rebase.needed` false.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Queue the branch for hand-off | queue · changes | **queue, as `fix(taskrail)`, after T063** | Every close check holds; T063 is in review. |

## rebase after T063

T063 (`8555317`) was merged into `main` since the branch started. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1; the backlog differs from `origin/main` only in T064's row. |

After the rebase: `taskrail checks T064 --stage fix`: `test` 940 passed, `lint` not configured;
`taskrail validate` 0 errors, 0 warnings.
