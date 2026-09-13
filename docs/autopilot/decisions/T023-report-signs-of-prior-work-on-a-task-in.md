# T023 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T023-report-signs-of-prior-work-on-a-task-in.md` (commit `929e01b`), its ten criteria, and the prototype run against this repository's history.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan? | approve · with changes | **approve** | Informational only, testable, measured against real history, and it keeps out of `task_dict` while other lanes edit it. |
| 2 | Subjects that only mention the ID elsewhere | exclude · report as `mention` | **exclude** | The prototype showed backlog commits opening a task would flag it as already worked on. |
| 3 | Report an existing task branch | include · rely on step 3 | **include** | The most direct signal, for one `for-each-ref`. |
| 4 | Opt-out for the history search | none now · flag · config key | **none now** | Measured in milliseconds here; add a switch only when a consumer needs one. |
| 5 | Skill step 2 also asks to check the description's premises | include · mechanical only | **include** | One clause, and it restores a check a consumer's pipelines already make. |

## Conflict handling agreed for all lanes

T021 and T022 both edit the config template in `install.py` (`[columns]` and `[review]`), T022 and T023 both edit adjacent steps of the core skill, and every lane adds a `## Unreleased` changelog line and a decisions index row. Each lane touches only its own section. When a later rebase conflicts there: keep both sides in sources, changelog and indexes, then regenerate `.claude/skills/` with `taskrail upgrade` instead of merging installed copies by hand.

## implement gate

Reviewed independently of the lane's report: `prior.py`, the two-line hunk in `cmd_show`, the
step 2 change in the skill source, a re-run of the suite in the lane's worktree (181 passed), and
`show` against this repository's real history: T013 reported its squash title (`suffix`), T001 its
`scope` commits and the merge commit naming its branch, T014 nothing, each in about 150 ms.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation? | approve · request changes | **approve** | Matches the approved plan, keeps clear of `task_dict`, and the lane's mutation run showed the tests catch a looser prefix, a missing cap and a wider ref set. |
| 2 | Keep the `installed.json` version and hash change from `upgrade` | keep · revert by hand | **keep** | It is what `upgrade` writes; a rebase conflict there is resolved by re-running `upgrade`, as agreed. |

Observation, not a change request: for a finished task the artifact is found on every branch cut
from `main`, so the text line gets long. It is informational; revisit only if it proves noisy.

## rebase after T018 merged

T018 was squash-merged first (#8), so this branch was rebased onto `origin/main` (`20b624f`).
Every conflict fell in a known class and was resolved without escalation:

| File | Conflict | Resolution |
|---|---|---|
| `docs/features/README.md` | both appended an index row | kept both rows |
| `docs/autopilot/decisions/README.md` | both appended an index row | kept both rows |
| `CHANGELOG.md` | both added an `Unreleased` bullet | kept both bullets |
| `TODO.md` | T018's new T025 row next to this branch's ✅ on T023 | kept T025, kept T023 as ✅ (no `Reopens: T023` on either side) |

After the rebase: no conflict markers left, 200 tests passed, `validate` clean, installed skills
matching their sources, and `review` reporting no further rebase needed.
