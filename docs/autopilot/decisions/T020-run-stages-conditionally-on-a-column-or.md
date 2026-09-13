# T020 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T020-run-stages-conditionally-on-a-column-or.md` (commit
`1b0798b`), its fourteen acceptance criteria, affected areas and out-of-scope list.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Letter case of `match` values | case-insensitive, trimmed · exact like `[[route]]` | **case-insensitive, trimmed** | A stage silently skipped over a letter-case typo is the worst failure; headers already resolve case-insensitively. |
| 2 | Columns a predicate may read | custom only · core through aliases too | **custom only** | Only `Pts` would be useful among core columns; an error naming the core column keeps the contract small. |
| 3 | Undeclared `column` | new error keeping the kind loaded · warning · `kind-invalid` | **`stage-column-unknown` error, kind stays loaded** | A predicate that can never hold must not pass quietly, and dropping the kind would bury the cause under `task-kind-unknown` for every task. |
| 4 | Skipping a judgement stage whose gate is `always` | ask first · record and mention | **ask first** | An `always` gate means a human sees that stage; skipping it on the executor's word would remove that. |
| 5 | Stage the executor skill does not describe | follow its `summary` · say nothing | **follow its `summary`** | Otherwise a stage added by override has no instructions at all. |
| 6 | Follow-up to move `[[route]]` onto the shared predicate | open · do not open | **open** | Two matchers with different letter-case rules in one tool is a trap; the follow-up is where the behaviour change for routes is decided. Kind `feature`, epic E02, depends on T020. |
| 7 | Type of `applies` in `show --json` | `true`/`false`/`"judgement"` · boolean `applies` plus the existing `judgement` flag | **boolean `applies` (the column predicate, `true` without one) plus `judgement`** | One field with two JSON types forces every consumer to type-check; the executor skips when `applies` is false and decides when `judgement` is true. Adjust criteria 4 and 13 and the text `show` markers accordingly. |

Plan approved with decision 7. The lane must remove its scratch repositories under a temporary
directory when it no longer needs them.

## implement gate

Reviewed: commits `0495ff7` (T035), `a260e5d` (plan, decision 7) and `dab40e3` (`predicates.py`,
`kinds.py`, `cli.py`, `model.py`, core skill step 5, DESIGN.md §5.1, §5.4, §12.7, README,
CHANGELOG, `tests/test_conditional_stages.py`). Re-ran `uv run pytest -q`
in the lane's worktree: 295 passed. `predicates.py` imports nothing else from taskrail, so
`model.py` re-exporting `NONE_MARKERS` from it adds no import cycle.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | It follows the plan and decisions 1–7; `applies` is a boolean in every case and the kind stays loaded on `stage-column-unknown`. |
| 2 | Text `show` markers | keep `— not applicable (Area)` and `— executor's judgement` · add the match values | **keep** | `--json` carries `match` for anyone who needs it; text lines stay short. |

## rebase after T017 and T027

The lane rebased onto `origin/main` (`a9ae799`) at close, following the orchestrator's conflict
instructions. Checked by the orchestrator before publishing:

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/features/README.md`, `docs/autopilot/decisions/README.md`, `CHANGELOG.md` | keep both · stop | **keep both** | Additive rows and bullets on both sides. |
| 2 | Conflict in `.taskrail/installed.json` | regenerate · hand-merge | **regenerate with `upgrade --force`** | The manifest records digests of rendered files; `upgrade` now reports nothing to create or update. |

After the rebase: the skill source differs from `main` in step 5 only, no conflict markers,
`pytest -q` 333 passed, `taskrail validate` 0 errors.
