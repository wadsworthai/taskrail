# T029 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T029-add-the-autopilot-configuration-runs-and.md` (commit
`0726c56`), its fifteen acceptance criteria, against `DESIGN.md` §12.1, §12.2,
§12.4 and §12.9.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | `[autopilot]` keys parsed now | every single-value key in §12.9 · only the keys T029 uses · also the group and resource tables | **every single-value key; tables stay with T030** | T030–T032 run in parallel, and a code conflict in `config.py` is outside the known classes; the tables need T020's column predicate. §4 says which keys take effect with which task. |
| Q2 | Run ID | `YYYYMMDD-N` · timestamp plus random suffix · clone-wide counter | **`YYYYMMDD-N`** (UTC date) | Short enough to type in `--run`; created exclusively, so two orchestrators starting together take the next free number instead of colliding. |
| Q3 | How `run` reaches the claim | `claim --run R` · `TASKRAIL_RUN` · `lane` writes it | **`claim <ID> --run R`, exit 3 for an unknown run; the remote copy carries `run`** | Explicit in the lane's brief and visible in its transcript; an environment variable leaks into unrelated claims. A run ID names no machine detail. |
| Q4 | Writing `handed-off` and run-level decisions | `lane --state handed-off` · new command · skill edits JSON | **`lane --state handed-off` (exit 5 unless `done-branch`, order kept); plus a minimal `autopilot decision --run R --question … --decision … --reason …` that appends to the run's `decisions`** | State files are written by the CLI only, never by hand; without a writer, the accepted "run-level decisions copied into each record" has nowhere to live. Update §12.1 for both. |
| Q5 | `--reason` | required for `failed` and `escalated` · required for all three · optional | **required for `failed` and `escalated`; optional for `gate`; cleared by `running`** | A failure or escalation without a reason cannot be acted on; a gate's reason is the lane's report. |
| Q6 | `--group` before groups exist | store as given · leave to T030 | **store as given** | §12.7 allows judgement-assigned groups with no configuration; T030 checks names against configured groups. |
| Q7 | Runs listed without `--run` | every run, newest first, `complete` flag · incomplete runs plus `--all` | **every run, newest first, with `complete`** | Follows §12.4; run files are small and local. Pruning waits for a real need. |
| Q8 | States outside the §12.1 list | `discarded` for ❌; stale claim stays `running` with the stale reason · omit discarded · stale as `pending` | **as recommended** | A discarded run task must stay visible to count against the target; a stale claim still blocks dispatch, so calling it `pending` would mislead. Add `discarded` to §12.1's list. |
| Q9 | `touched` | committed since the fork point plus uncommitted · committed only | **committed plus uncommitted; overlaps include backlog files and changelogs** | Lanes stop at gates with work in progress; the skill decides which overlaps are known conflict classes. |

Plan approved with the Q4 addition. The lane must remove its scratch repositories under a
temporary directory when it no longer needs them.

## implement gate

Reviewed: commit `3679fc7` (`autopilot/runs.py`, `status.py`, `commands.py`, `config.py`
`AutopilotConfig`, `claims.py` `run`, `cli.py` wiring, DESIGN.md §4, §6, §7, §12, README,
CHANGELOG, `tests/test_autopilot.py`). Re-ran `uv run pytest -q` in the
lane's worktree: 339 passed. Run files are created by hard-linking a complete temporary file,
changed under `ids.lock`, replaced atomically, and not written when the update block raises.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Deviation: `claim --run` also lists the task in the run file | accept · drop it · have `done` record membership | **accept** | Otherwise a lane that finishes before the orchestrator calls `lane` disappears from `status`; `done` is being changed by T019. |
| 2 | Other deviations: `done_merged`, `fetched`, tasks missing from the backlog, template check at load | accept · drop | **accept** | Small, tested, and each prevents a silent gap. |
| 3 | Deviation: tests written after the implementation, contrary to the executor skill's implement step | accept as is · require evidence the tests detect breakage | **require evidence at verify** | A `ModuleNotFoundError` against the base proves only that the module is new. At the verify stage, break three behaviours one at a time — the exit-5 refusal while disabled, the state precedence (`done-branch` over a recorded `gate`), and `handed-off` without `done-branch` — show the matching tests fail, restore, and record it in the artifact. |
| 4 | Duplicated lookups | keep · align | **align at the close rebase** | `status.py` calls `stack.task_branch`, which T019 removes, and has its own `_worktrees_by_branch`, which T019 adds as `gitutil.worktree_branches`. Once T019 is on `origin/main`, use `branches.task_branch` and `gitutil.worktree_branches`, and drop the local copy. |

Implementation approved with items 3 and 4.

## rebase after T020 and T019

T020 (`155a56c`) and T019 (`1543057`) were squash-merged into `main`. The lane rebased at close
and again after T019, following the orchestrator's instructions. Checked by the orchestrator
before publishing:

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in the docs indexes, CHANGELOG and the DESIGN.md §7 table | keep both · stop | **keep both** | Rows and bullets added on both sides; T019's §6.4 and the §6.1 freeze text are intact. |
| 2 | Conflict at the end of `cmd_claim` | keep both behaviours · stop | **keep both** | T019's branch freeze and warning run first, then the task joins the run; a new test covers `claim --run` on the template branch. |
| 3 | `status` branch lookup | adapt to T019's resolver · keep a local copy | **adapt** | Commit `1b0db75` uses `branches.task_branch` and `gitutil.worktree_branches`; a new test covers a renamed task branch. |

After the rebase: no conflict markers, `pytest -q` 410 passed, `taskrail validate` 0 errors,
`upgrade` reports nothing to create or update.
