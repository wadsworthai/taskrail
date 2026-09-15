# T047 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing` (T060)** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T047-keep-a-stacked-task-s-fork-point-after-d.md` (commit
`8795324`), its six acceptance criteria, finding F1 of T033 (`stacked: false`, `fork_source:
merge-base`, no command after the dependency was rebased at hand-off), and on `origin/main`
(`1631ab8`) `_dependents` in `autopilot/merged.py`, which reads `base.commit` only from a live claim,
and `cmd_claim` in `cli.py`, which lists the task in the run without its base. The premise holds. No
code changed, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §12.4 *Claims* `base.commit` sub-bullet and §12.8 *Stacked dependents* bullet | approve as written · also extend §12.4's run-file key list | **approve as written** | Decided by the orchestrator under the human's delegation. The key list is T048's lines; the `lane` key list there can gain `base` in a later documentation pass rather than a hand-off conflict. |
| 2 | Name of the new `fork_source` value | `run-base` · `claim-kept` · reuse `claim` | **as recommended (`run-base`)** | Says where the value came from, and that the claim is gone. |
| 3 | Which runs' kept bases are read | every run, newest first · only runs holding the dependency | **as recommended (every run)** | A dependent may be claimed in a different run from its dependency. |
| 4 | Existing merge-base test claims T002 without `--run` | yes · keep `--run` and add a separate test | **as recommended (yes)** | Keeps coverage of the `merge-base` and `run` sources with one change. |
| 5 | Size | one task · split | **as recommended (one task)** | Two small code areas and their tests. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T047 owns `_dependents` and a helper in `autopilot/merged.py`, one line in the `if created and args.run is not None:` block of `cli.py` `cmd_claim`, its tests in `tests/test_autopilot_merged.py` and one in `tests/test_autopilot.py`, the §12.4 `base.commit` sub-bullet and the §12.8 *Stacked dependents* bullet. T048 (closed) owns the `--run` check earlier in `cmd_claim`, `runs.py` and the other §12.4 lines; T055 the §12.8 *Hand-off is sequential* bullet; T053 `_handoff` in `test_autopilot.py`'s hand-off tests.** | Built from the gates reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off by the known classes · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commit `49ab56e` (range `19a0829..49ab56e`): one line in `cmd_claim` keeping the claim's
`base` in the lane, `_kept_bases` and `_recorded_fork` in `autopilot/merged.py` with `_dependents`
trying the claim, then kept bases newest run first, then `merge-base` and `run`; the two approved
DESIGN.md edits; one CHANGELOG bullet; and four new tests shown failing before the code, the F1 test
with exactly the trial's output (`stacked: False`, `fork_source: merge-base`, no command). Re-ran
`uv run pytest -q` in the lane's worktree: 835 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Criteria 1–6 map to tests; the diff stays inside the touch map. |
| 2 | "no claim or run records it" in the unknown-fork reason | keep · revert | **as recommended (keep)** | The message must name the new source it also checked. |

## close gate

Reviewed: `7659c30` (verification in a scratch repository with a bare origin: after T001 was rebased
at hand-off and squash-merged, this branch's `autopilot merged` reported T002 `stacked: true`,
`fork_source: run-base` and a `rebase --onto` command that left only T002's commits; the base
commit's CLI, as control, reported `stacked: false` with no command) and `aaa13eb` (`taskrail done
T047` on its own, changing only T047's row). No code changed after the checks re-run at the implement
gate (835 passed). `taskrail validate`: 0 errors. No upstream is configured. `review --json`:
`rebase.needed` false.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch | queue · changes | **queue, as `feat(taskrail)`** | Every close check holds; the verification and its control show F1 fixed. |

## rebase after the merged tasks

T050, T049, T060, T054, T055, T052, T053, T056, T048 and T051 (`e7111d9`) were merged into `main`
since the branch started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |

`cli.py` (beside T048's closed-run check and T062's refusal), `merged.py` and DESIGN.md merged without
conflicts. After the rebase: no conflict markers, `taskrail checks T047 --stage implement`: `test` 893
passed, `lint` not configured; `taskrail validate` 0 errors.
