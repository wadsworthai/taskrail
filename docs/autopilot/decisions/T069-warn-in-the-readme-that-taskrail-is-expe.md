# T069 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where to put the task's row, which was written uncommitted to the `main` checkout while its lane would branch from `origin/main` | commit it on local `main` · recreate it on its own branch · work it without the autopilot | **recreate it with `taskrail new --workspace` and work the task on that branch** | The human's instruction. The row was discarded from `main`; the task was created again as T069, since T068 was still reserved, and run 20260915-1 was started with `--count 1` from its worktree. |
| 2 | Wording of the README notice (scope decision 1) | as proposed · without the upgrade advice · without "under human direction and review" | **as proposed** | Public text that states how the project is developed, so the orchestrator took it to the human. |
| 3 | A CHANGELOG.md entry under Unreleased (scope decision 4) | no entry · one bullet | **no entry** | The notice changes no behaviour. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the change set in `docs/chores/T069-warn-in-the-readme-that-taskrail-is-expe.md` (commit
`56b2ac7`), the range `origin/main..56b2ac7` (the backlog row, the artifact and its index row; no
other file), and `README.md` on `origin/main` (`fb9a26b`), which has no maturity or AI notice, so the
premise holds. `autopilot status` reports no `governing_touched` and no escalation. The stage defines
no checks; none were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Wording | as proposed · without the upgrade advice · without "under human direction and review" | **as proposed** | Decided by the human; see above. |
| 2 | Markup | plain blockquote with a bold lead · `> [!WARNING]` | as recommended | It renders the same on every forge and in package metadata built from `readme = "README.md"`. |
| 3 | Placement | after the introductory paragraph · directly under `# taskrail` | as recommended | The README still opens by saying what taskrail is, and the notice comes before *Install*. |
| 4 | CHANGELOG.md entry | no entry · one bullet | **no entry** | Decided by the human; see above. |

The change set is approved as listed: only the notice in `README.md`, besides the artifact.
