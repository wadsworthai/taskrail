# T050 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T050-accept-gate-close-for-the-stop-after-don.md` (commit
`43df757`), its six acceptance criteria, the lane's reproduction of F10 (`--gate close` exits 2
with `` `close` is not a stage of kind feature (plan, implement, verify) ``), and
`_gate_problem` in `src/taskrail/autopilot/commands.py` on `origin/main`
(`b184707`). No code changed yet, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §12.1 and §12.6 text (governing) | approve as written · leave DESIGN.md unchanged | **taken to the human; implement without editing DESIGN.md until answered** | DESIGN.md is a governing path; its changes reach the human. The code does not depend on the text, so the lane is not held. |
| 2 | Accept `close` when the task's kind is not defined | yes, check `close` before the kind lookup · keep exit 2 | **as recommended** | `close` does not depend on the kind's stages. |
| 3 | Require `done-branch` for `--gate close` | no · exit 5 unless `done-branch` | **as recommended (no)** | The gate review of the close already checks that `done` is committed; a state check would add a git read to `lane`. |
| 4 | Reserve `close` as a stage name | no · `validate` rejects it | **as recommended (no)** | Rejecting it would break any custom kind using the name, for no gain. |
| 5 | `<kind>:close` in `escalate_gates` | keep "moved-on tasks are not flagged" and document it · flag it | **as recommended (keep)** | §12.6 already says tasks past `done-branch` are not flagged; flagging would change `escalation.py` and `status.py`, which T049 owns in this run. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T050 owns `autopilot/commands.py` (`_gate_problem`, `--gate` help), its `--gate` tests in `tests/test_autopilot_notify.py`, and the *Close and hand off* section of the `taskrail-autopilot` skill source. T049 owns `autopilot/escalation.py` `flags()`, `_escalation_text()` in `autopilot/commands.py`, its governing tests, condition 1 of the skill's *Escalate* section and the *Close* section of `references/gate-review.md`. T053 owns the hand-off queue in `autopilot/status.py`. Each lane leaves the others' functions and sections alone; edits in different functions of one file are merged at hand-off.** | Built from the plans reached so far; extended as other lanes reach their first gate. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off by the known classes · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commit `bd1ae29` (range `26036d1..bd1ae29`): `_gate_problem` accepts `close` before the
kind lookup, the `--gate` help, one sentence in the skill's *Close and hand off*, the installed copy
and its digest, one CHANGELOG bullet, and two tests in `test_autopilot_notify.py` plus one in
`test_autopilot_skill.py`, which the lane showed failing before the code. Re-ran
`uv run pytest -q` in the lane's worktree: 831 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Tests cover criteria 1–5 and the shipped half of 6; the diff stays inside the touch map. |
| 2 | DESIGN.md §12.1 and §12.6 text (plan-gate question 1) | approve as written · no change | **approve as written, in its own commit, then re-run the checks** | Decided by the orchestrator under the human's delegation below; the text matches the CLI. At hand-off, T049 edits the §12.6 *Governing paths* bullet just above T050's sentence; both edits are kept. |
| 3 | Where the new skill test sits | keep · move to the end | **as recommended (keep)** | Adds a function without editing others. |

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing`** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.


## close gate

Reviewed: commits `25c7a53` (DESIGN.md §12.1 `autopilot lane` row and §12.6 *Escalated gates*,
exactly the approved text), `a935b69` (verify record: `lane --gate close` exit 0, `--gate nope` exit 2
naming `close`, `status` showing `done-branch`, `gate: close`, `escalation: []` in a scratch
repository) and `2332637` (`taskrail done T050` on its own, changing only T050's row). No code
changed after `bd1ae29`, whose checks passed when re-run (831 passed). `taskrail validate`: 0
errors. No upstream is configured. `review --json`: `rebase.needed` false onto `origin/main`.
`autopilot status` flags `governing` for `DESIGN.md`, covered by the human's
delegation. `overlaps` match the touch map.

The main checkout's CLI predates this task, so the close stop was recorded as `--state gate`
without `--gate close`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and hand the branch off | hand off · changes | **hand off, as `feat(taskrail)`** | Every close check holds; first in `handoff.next`. |
