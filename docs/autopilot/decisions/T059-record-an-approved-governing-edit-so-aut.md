# T059 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Continue the autopilot with the follow-up tasks | — | **run 20260914-2 with T059, T061, T062 and T063, each dispatched once its row reaches `main`** | The human's instruction. |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T059-record-an-approved-governing-edit-so-aut.md` (commit
`a0c0f17`), its eleven acceptance criteria, and on `origin/main` (`ff8e4e6`) `escalation.flags()`,
which adds `governing` whenever `governing_touched` is not empty before `done-branch`, with no way to
record an approval. The premise holds for any repository that lists governing paths, although this
one no longer does (T060), so the lane tests on the `pilot` fixture. No code changed, so no checks
were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Command shape | `autopilot approve-governing` in a new module · `lane --approve-governing` · `autopilot approve` | **as recommended (`approve-governing`)** | Keeps `cmd_lane`, which T048 edits, untouched, and names what is approved. |
| 2 | Blob ID source | worktree file, else branch tip, else `null` · branch tip only | **as recommended (worktree first)** | Approvals happen at gates, often before a commit; a later uncommitted change must flag. |
| 3 | Refusals | exit 5 for nothing to approve, exit 2 for an unknown path · exit 0 | **as recommended (refuse)** | An approval that recorded nothing must not look like success. |
| 4 | Closed runs (T048, unmerged) | do not refuse · follow-up · stack on T048 | **do not refuse, and say so in the artifact** | Harmless while closed runs are hidden; a follow-up for one refusal is not worth its cost now. |
| 5 | DESIGN.md (a)–(e) | approve as written · other wording · no change | **approve as written** | Decided by the orchestrator under the human's delegation; each is a phrase-level addition kept at hand-off. |
| 6 | Skill *Escalate* condition 1, the new *Escalate* sentence, gate-review *Close* bullet | approve as written · no change | **approve as written** | The orchestrator must know when to record an approval. T048 adds a paragraph at the end of *Escalate*; both are kept at hand-off. |
| 7 | Approve the plan | as written · changes | **approve as written** | Criteria cover recording, re-flagging on change, partial approvals and refusals. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T059 owns the new `autopilot/approve.py`, its import lines and `add("approve-governing", …)` block after `decision` in `commands.py` `register()`, `_escalation_text()`, `flags()`'s `approved` argument, `current_blobs()` and the `governing_approved` key in `status.py` `_lane_details()`/`_flag_escalations()`, `tests/test_autopilot_governing.py`, one test at the end of `tests/test_autopilot_skill.py`, and the approved DESIGN and skill text. T061 (planning) owns the new read-first configuration key and must leave governing matching to T059. Unmerged run 20260914-1 branches keep their areas (T048 `cmd_lane`/`cmd_close`/`runs.py`, T051 `status()`, T054 `task_state`, T055 other skill sections, T052 `taskrail checks`).** | Built from the plans reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs, same-line DESIGN rows | resolve at hand-off · serialize | **resolve at hand-off, keeping every phrase** | Known conflict classes 1–3; row edits apply phrase by phrase as at T054's rebase. |

## implement gate

Reviewed: commits `2583371`, `7df2e32` and `7b25ab9` (range `8a592d6..7b25ab9`): the new
`autopilot/approve.py` (run, task and membership checks, refusals, blob IDs merged into
`governing_approved` under the lock), `current_blobs` and `_approved` in `status.py` feeding
`_lane_details` and `_flag_escalations`, `flags(…, approved=())` in `escalation.py`,
`_escalation_text` naming only unapproved files, the `approve-governing` registration after
`decision`, the approved skill and DESIGN.md text with installed copies, and
`tests/test_autopilot_governing.py` plus one skill test, 20 shown failing before the code. The lane
also broke the branch-tip lookup on purpose and saw two tests fail. Re-ran
`uv run pytest -q` in the lane's worktree: 860 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Criteria 1–11 map to tests seen failing first; the diff stays in the named areas. |
| 2 | Skill test placed after T049's; `approve.py` reuses `status._branch_ref` | accept · move the test / copy the helper | **as recommended (accept both)** | An appended function conflicts only in the append class; one branch-ref rule is better than two. |

## close gate

Reviewed: `93a68dd` (verification in a scratch repository: a governing edit flagged, cleared by
`approve-governing` with the worktree's blob ID, re-flagged after an uncommitted change and a new
file, partially approved with `--path`, the three refusals exiting 2, 3 and 5, and both approvals
holding from the branch tip at `done-branch` after the worktree was removed) and `be5e809`
(`taskrail done T059` on its own). No code changed after the checks re-run at the implement gate (860
passed). `taskrail validate`: 0 errors. No upstream is configured. `review --json`: `rebase.needed`
true onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Queue the branch for hand-off | queue · changes | **queue, as `feat(taskrail)`** | Every close check holds; the verification covers recording, re-flagging and refusals. |
| 2 | Expected rebase conflicts | known classes, keeping every phrase in the DESIGN rows · stop | **as recommended** | As at earlier hand-offs in these runs. |

## rebase after the merged tasks

T060, T054, T055, T052, T053, T056, T048, T051, T047 and T061 (`152120a`) were merged into `main`
since the branch started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |
| 4 | Conflict in `tests/test_autopilot_skill.py` | keep both · stop | **keep both** | T055's test section and T059's new test were added at the same place. |
| 5 | Conflict in `DESIGN.md` §12.1: the new `approve-governing` row beside the `autopilot status` row | stop · keep every change | **T059's new row, then `main`'s status row with T059's `governing_approved` and `escalation` phrases applied** | The status row carries T051, T053, T054 and T061's phrases; T059's replacement covers only the escalation fields. Decided under the human's delegation. |
| 6 | Conflict in DESIGN.md §12.4 key list | stop · keep both | **`main`'s line (T048's `closed`) with `governing_approved` added to the lane keys** | Both tasks added keys to one sentence. |

After the rebase: no conflict markers, `taskrail checks T059 --stage implement`: `test` 927 passed,
`lint` not configured; `taskrail validate` 0 errors.
