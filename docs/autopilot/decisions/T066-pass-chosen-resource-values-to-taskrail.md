# T066 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Launch T066 | — | **run 20260915-2 with T066, dispatched once T063 merged** | The human's instruction ("agrega la tarea que abrió a la lista"). |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T066-pass-chosen-resource-values-to-taskrail.md` (commit
`bc1f9bd`), its six acceptance criteria, and on `origin/main` (`8555317`) `checks.run_checks`, which
passes only the lane's recorded values (empty after release), and the skill's *Close and hand off*
step 1, which still documents an environment-variable prefix. The premise holds. No code changed, so
no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan | approve · changes · split the skill text | **as recommended (approve)** | One small CLI flag with the text that documents it. |
| 2 | D1: combine with lane values | merge, flag wins per name · replace all · refuse while held | **as recommended (merge)** | Lets the orchestrator replace only the released names. |
| 3 | D2: accepted values | configured name and pool value · any · name only | **as recommended (configured name and pool value)** | The same pool `next` allocates from; a typo fails loudly. |
| 4 | D3: a value another lane holds | exit 4 · exit 5 · no check | **as recommended (exit 4)** | Exit 4 is taskrail's conflict code; reading `next_lanes`'s preview keeps one allocation rule. T064 (unmerged) changes only the candidate loop of `next_lanes`, not the held map. |
| 5 | D4: DESIGN.md §7 row, §7.5 sentences, §12.7 sentence | approve as written · §7 only | **approve as written** | Decided under the human's delegation of DESIGN.md decisions. |
| 6 | D5: skill *Close and hand off* step 1 sentence and gate-review *Rebase* bullet | approve as written · CLI only | **approve as written** | Otherwise the documented procedure keeps the command shape F11 warns against. |
| 7 | D6: CHANGELOG bullet | add · none | **as recommended (add)** | A new CLI flag. |
| 8 | Race between the holder check and the run | accept · record a reservation | **as recommended (accept)** | It needs two orchestrators on one clone; a reservation would widen the task beyond its row. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T066 owns `checks.py`, `cmd_checks` and the `checks` parser in `cli.py`, `tests/test_checks.py`, the named assertions in `tests/test_autopilot_skill.py`, the named skill and gate-review sentences, and the approved DESIGN text. T064 (in review) owns `next_lanes`'s candidate loop and `_on_mainline`; T065 (queued) owns `WITH_BRANCH`, `_handoff`, `_closed_time`, `MOVED_ON`, `cmd_lane`, `cmd_review` and a paragraph above *Close and hand off* step 1.** | T065's paragraph sits above the step-1 sentence T066 edits; both are kept at hand-off. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commit `0339490` (range `b7f8745..0339490`): `chosen_resources` and the `resource_pairs`
merge in `checks.py` (the holder check reads `next_lanes`'s read-only preview), `--resource` in
`cli.py`, the approved DESIGN.md, skill and gate-review text with installed copies, one CHANGELOG
bullet, five `test_checks.py` tests and the skill assertion shown failing before the code, and a
one-line change to T063's skill test that asserted the sentence D5 replaced. Re-ran `taskrail checks
T066 --stage implement` in the lane's worktree: 942 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Criteria 1–6 map to tests seen failing first; `dispatch.py` is untouched. |
| 2 | One-line change to T063's test | accept · revert and drop D5 | **as recommended (accept)** | It asserted the exact sentence the approved D5 text replaces. |
| 3 | `--resource` validated after worktree and stage selection | accept · validate first | **as recommended (accept)** | No check runs in any refusal, and the worktree's own configuration is loaded before the pool is read. |

## close gate

Reviewed: `ef677da` (verification with this branch's CLI on the main checkout: an unconfigured name and
a malformed pair exit 2, plain `checks` reports `"chosen": {}`, `--help` shows the flag; the pool and
holder behaviour is covered by the fixture tests because this repository configures no resources) and
`d9837bb` (`taskrail done T066` on its own). No code changed after the checks re-run at the implement
gate (942 passed). `taskrail validate`: 0 errors. `review --json`: `rebase.needed` true onto
`origin/main` (T064 and T065 merged).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and hand the branch off | hand off · changes | **hand off, as `feat(taskrail)`, after the rebase** | Every close check holds; no other branch is in review. |

## rebase after T064 and T065

T064 (`acec04a`) and T065 (`0404505`) were merged into `main` since the branch started. The branch was
rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID, ✅ by status cell · stop | **unite by ID; the backlog differs from `origin/main` only in T066's row** | Class 1. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |

The skill source (beside T065's paragraph above *Close and hand off* step 1) and DESIGN.md merged
without conflicts. After the rebase: `taskrail checks T066 --stage implement`: `test` 953 passed,
`lint` not configured; `taskrail validate` 0 errors, 0 warnings.
