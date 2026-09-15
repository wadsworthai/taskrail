# T048 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing` (T060)** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T048-add-autopilot-close-to-abandon-a-run.md` (commit
`69a3a2d`), its ten acceptance criteria, and finding F7 of T033 (a rewound session left a run
holding every lane, with no way to abandon it). On `origin/main`, `runs.py` has no closed state,
`dispatch.py` counts lanes across every run file, and the skill says nothing about abandoning a run,
so the premise holds. No code changed, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan | approve · narrow to hiding only | **as recommended (approve)** | Refusing new work in a closed run keeps a stale session from reviving it; every criterion is testable with fixture run files. |
| 2 | DESIGN.md §12.1 `autopilot close` row | approve as written · also edit `next` and `status` rows | **approve as written** | Decided by the orchestrator under the human's delegation; the new row avoids the phrases T049, T050, T053 and T054 edit. |
| 3 | DESIGN.md §12.4 changes (a)–(d) | approve · no change | **approve as written** | Same delegation; they describe the new `closed` key and the open-runs rule. |
| 4 | DESIGN.md §12.7 sentence | approve · no change | **approve as written** | Same delegation. |
| 5 | Skill command reference paragraph at the end of *Escalate*, then `taskrail upgrade` | add · leave to T055 | **as recommended (add)** | The command must be discoverable where a stale run is noticed; "only on the human's say-so" keeps it a human decision. T049 changed condition 1 of the same section; add only your paragraph. T055 rewrites other skill text later. |
| 6 | Closing a closed run | exit 5 · exit 0 idempotent | **as recommended (exit 5)** | Consistent with other state refusals; the first record stays. |
| 7 | Claims naming the closed run | keep and report · release the caller's · `--release-claims` | **as recommended (keep and report)** | A claim protects work in a worktree; releasing stays an explicit `taskrail release`. |
| 8 | `status --run R` for a closed run | show with `closed` · exit 5 · `--all` | **as recommended (show)** | Evidence stays readable when asked for by name. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T048 owns `runs.py` (`closed`, `is_closed`, `close`), `cmd_close` and the closed-run checks in `commands.py`, the closed-run filter in `dispatch.py` `next_lanes`, the `closed` key in `status.py` `run_status`, the `--run` check in `cli.py` `cmd_claim`, `tests/test_autopilot_close.py`, the new DESIGN rows and sentences it named, and one paragraph at the end of the skill's *Escalate*. T054 owns `task_state`/`_closing` in `status.py` and the candidate skip in `dispatch.py`; T053 `_handoff`/`_done_time`; T049 and T050 `_escalation_text`, `_gate_problem` and `--gate` help. T056 owns the OpenCode note; T060 the repository config and CLAUDE.md.** | Built from the gates reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off by the known classes · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commit `01618b3` (range `be1d295..01618b3`): `close`, `is_closed`, `closed_message` and
`RunClosed` in `runs.py`; `cmd_close` and the closed-run refusals (before and under the lock) in
`commands.py`; closed runs dropped from `every_run` in `dispatch.py` without touching the candidate
loop; the `closed` key in `status.py` `run_status`; the `claim --run` refusal in `cli.py`; the approved
DESIGN.md text; the skill paragraph with its installed copy and digest; one CHANGELOG bullet; and
`tests/test_autopilot_close.py`. The lane's report showed no run of the new tests before the code, so
the orchestrator copied the test file into a scratch worktree at `origin/main` (`1631ab8`): 11 failed.
Re-ran `uv run pytest -q` in the lane's worktree: 839 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Every criterion maps to a test that fails without the code; the diff stays inside the touch map. |

## close gate

Reviewed: `88e642e` (verification in a scratch repository with two runs and a `PORT` resource:
closing the run holding both lanes gave the other run both lanes and ports, kept the claim, hid the
run from `status`, and `lane`, `decision`, `next --run`, `claim --run` and a second `close` exited 5,
an unknown run 3 and a blank reason 2) and `31631c9` (`taskrail done T048` on its own, changing only
T048's row). No code or test changed after the checks re-run at the implement gate (839 passed).
`taskrail validate`: 0 errors. No upstream is configured. `review --json`: `rebase.needed` true onto
`origin/main` (T050 merged).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch | queue · changes | **queue, as `feat(taskrail)`** | Every close check holds; the verification matches the plan. |

## rebase after the merged tasks

T050, T049, T060, T054, T055, T052, T053 and T056 (`1941698`) were merged into `main` since the
branch started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md` and `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |

`dispatch.py`, `status.py`, `commands.py`, `cli.py` and DESIGN.md merged without conflicts beside
T054's candidate skip and T049/T050/T053's phrases. After the rebase: no conflict markers,
`taskrail checks T048 --stage implement`: `test` 883 passed, `lint` not configured; `taskrail
validate` 0 errors.
