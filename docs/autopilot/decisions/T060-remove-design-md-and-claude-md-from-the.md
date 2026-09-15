# T060 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in a lane beside
autopilot run 20260914-1. T060 is not a member of that run: the human added it as a priority during
the run. Each decision is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides them, the human reviews them in the pull request; make it permanent by removing both files from `[autopilot].governing` (this task), worked as a priority** | The human's instruction in the orchestrator session. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope in `docs/chores/T060-remove-design-md-and-claude-md-from-the.md` (commit
`a62d6e8`), the T060 row commit `e16adb0`, `.taskrail/config.toml` on `origin/main`, and line 34 of
the `taskrail-autopilot` skill, which reads "the governing documents" only from the key. Nothing else
is edited yet.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where the "read first" role is kept | `CLAUDE.md` bullet plus config comment · comment only · `CLAUDE.md` only · new taskrail key | **as recommended (`CLAUDE.md` *Backlog* bullet plus the comment on the empty key)** | Every agent reads `CLAUDE.md`; the comment explains the empty key. A new key is a follow-up. |
| 2 | How the change is checked | `.taskrail/tests/test_config.py` · test in `tests/` · extend `[checks].test` · no new test | **no new test: verify with `taskrail validate` and `taskrail autopilot status --json` loading the empty key, and record their output in the artifact; edit T060's description to say so, with `taskrail edit`** | A test that no configured check runs would not be run; a test directory under `.taskrail/` adds a convention nobody else uses; the others were rejected in the scope for good reasons. The change is one configuration value and one paragraph, which the pull request shows. Also drop change 3 (a *Commands* line for that test). |
| 3 | Open a follow-up separating "read first" documents from escalating paths | open · do not open | **as recommended (open)**, feature in E02, with `taskrail new` in this worktree, committed on this branch | The general fix belongs in taskrail itself and is verifiable by pytest; the other lanes are editing that code now. |

## implement gate

Reviewed: commits `32f7789` (T060's description now names `validate` and `autopilot status`),
`a270814` (follow-up T061 in E02) and `5da09de` (`governing = []` with its comment, the `CLAUDE.md`
*Backlog* bullet, the artifact). The lane's `autopilot status --json` before and after shows the
`governing` escalations of T049 and T053 gone while `touched` still lists `DESIGN.md`; `validate`
0 errors; `test` 828 passed. The diff touches no taskrail file (`src/`, `tests/`, `DESIGN.md`, `CHANGELOG.md`, `README.md`) or `.claude/skills/`, so
the checks were not re-run by the orchestrator beyond confirming the diff.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | approve · wording changes | **approve** | Matches the approved scope; the wording states both roles of the key accurately. |
| 2 | T061 has no points | leave unestimated · set points now | **as recommended (leave)** | Estimating belongs to whoever plans it; an unestimated task sorts last in `next`, which suits a follow-up. |

## close gate

Reviewed: `39a3f66` (`taskrail done T060` on its own). The backlog differs from its base only in
T060's row and the T061 row the task added. `taskrail validate`: 0 errors. No upstream is
configured. The `test` check passed at implement (828) and only backlog and record commits followed.
`review --json`: `rebase.needed` true onto `origin/main` (T050 merged).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Hand-off order | next after the branch in review · after the run's queue | **next after T049, ahead of T053, as `chore(repo)`** | The human made T060 a priority; hand-off stays one branch at a time. |

## rebase after T049

T049 was merged into `main` (`ff8e4e6`). The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Class 2: appended index rows. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID: T059 then T061** | Class 1: two rows appended to E02 by different tasks. |

After the rebase: no conflict markers (`git diff --check` clean), `uv run
pytest -q` 840 passed, `taskrail validate` 0 errors. Handed off ahead of the run's queue, as the
human made T060 a priority.
