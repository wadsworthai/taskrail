# T049 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T049-stop-flagging-governing-paths-once-a-tas.md` (commit
`eda4c82`), its seven acceptance criteria, and `flags()` in
`src/taskrail/autopilot/escalation.py` and `_escalation_text()` in
`autopilot/commands.py` on `origin/main` (`b184707`): `governing` is computed without looking at
the state, while `escalate_gate` needs `gate` or `escalated`, so the premise (finding F9) holds. No
code changed yet, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §12.4 (`autopilot status` row) and §12.6 (*Governing paths*) text (governing) | approve as written · other wording · no change | **taken to the human; implement without editing DESIGN.md until answered** | DESIGN.md is a governing path; its changes reach the human. The code does not depend on the text, so the lane is not held. |
| 2 | What `status` reports at `done-branch` and `handed-off` | A: keep `governing_touched`, drop `governing` from `escalation` · B: empty both · C: drop only at `handed-off` | **as recommended (A)** | Keeps the evidence for the close review while ending the repeated flag F9 describes; C leaves F9 in the queue. |
| 3 | Change skill condition 1 and the gate review's *Close* section, then `taskrail upgrade` | yes · no | **as recommended (yes)** | Option A moves the post-gate governing edit to the close review, so the skill must say so. |
| 4 | Open a follow-up for recording a human's approval of a governing edit before `done-branch` | open · do not open · widen T049 | **as recommended (open)** | The task row narrows T049 to `done-branch`; the approval half needs its own design. It is verifiable by pytest. Create it with `taskrail new` in this worktree and commit it on this branch. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T049 owns `autopilot/escalation.py` `flags()`, `_escalation_text()` in `autopilot/commands.py`, its governing tests, condition 1 of the skill's *Escalate* section and the *Close* section of `references/gate-review.md`. T050 owns `_gate_problem` and the `--gate` help in `autopilot/commands.py`, its `--gate` tests and the skill's *Close and hand off* section. T053 owns the hand-off queue in `autopilot/status.py`. Each lane leaves the others' functions and sections alone; edits in different functions of one file are merged at hand-off.** | Built from the plans reached so far; extended as other lanes reach their first gate. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off by the known classes · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commits `39cf525` (T059 row) and `5aa1d54` (range `1ccd572..5aa1d54`): `MOVED_ON` in
`escalation.py` `flags()`, `_escalation_text()` built from `escalation`, skill *Escalate* condition 1
and gate-review *Close* bullet with installed copies and digests, one CHANGELOG bullet, and tests the
lane showed failing before the code. Re-ran `uv run pytest -q` in the
lane's worktree: 837 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §12.1 `autopilot status` row and §12.6 *Governing paths* text (plan-gate question 1) | approve as written · other wording · no change | **approve as written, in its own commit, then re-run the checks** | Decided by the orchestrator under the human's delegation below; the text matches the code. T053 edits the `queue` phrase of the same table row and T050 the next §12.6 bullet; the later hand-off keeps every edit. |
| 2 | Approve the implementation | approve · changes | **approve** | Criteria 1–7 map to tests; the diff stays inside the touch map. |
| 3 | Conflicts with other lanes at hand-off | mechanical at hand-off · other | **mechanical at hand-off, with one correction** | Task IDs are not per branch: `taskrail new` reserves them under a common-directory lock across worktrees (DESIGN §6.3), so T059 is unique and no renumbering is needed. `installed.json` is class 3 (`upgrade --force`); CHANGELOG and the index README are class 2; TODO.md class 1. |

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing`** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.


## close gate

Reviewed: commits `7897864` (DESIGN.md: only the `escalation` phrase and text-form clause of the
§12.1 `autopilot status` row, and the approved sentences in §12.6 *Governing paths*), `00e3197`
(verify record: in a scratch repository a lane at `gate` or `running` stays flagged, and at
`done-branch` and `handed-off` keeps `governing_touched` with an empty `escalation`) and `6a6e6d1`
(`taskrail done T049` on its own). The backlog differs from `origin/main` only in T049's row and the
T059 row the task added. No code changed after `5aa1d54`, whose checks passed when re-run (837
passed). `taskrail validate`: 0 errors. No upstream is configured. `review --json`: `rebase.needed`
false onto `origin/main`. The `governing` flag on `DESIGN.md` is covered by the
human's delegation.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch for hand-off | queue · changes | **queue, as `feat(taskrail)`, after T050's pull request is merged** | Every close check holds; hand-off is sequential and T050 is in review. |
| 2 | "running; handed off" wording of `lane --state handed-off` | follow-up · ignore | **ignore for now** | Pre-existing text, outside T049; the state shown is the recorded lane state, and the hand-off is reported in the same line. |

## rebase after T050

T050 was merged into `main` (`1631ab8`). The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md` and `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Class 2: appended index rows, one per task. |
| 2 | Conflict in `CHANGELOG.md` | keep both · stop | **keep both** | Class 2: appended *Unreleased* bullets, T050's then T049's. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s line, then `taskrail upgrade --force`, committed as `3d653d1`** | Class 3; the rewritten digest matches the merged skill source. |
| 4 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID: T049 ✅ and T050 ✅** | Class 1; no `Reopens:` commit on either side. |
| 5 | Conflict in `tests/test_autopilot_skill.py` | keep both · stop | **keep both functions** | T050 and T049 each added a new test function at the same place and changed no existing line; kept as two functions, the same append case as class 2. |

After the rebase: no conflict markers (`git diff --check` clean), DESIGN.md §12.1 and §12.6 carry both
T050's and T049's text, `uv run pytest -q` 840 passed, `taskrail validate`
0 errors.
