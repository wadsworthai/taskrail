# T070 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Create and run this task | — | **create it with `taskrail new --workspace` and run it in autopilot run 20260915-2, joined with `claim --run`** | The human asked for the task and then to raise the autopilot to three tasks including it. No command raises a run's count and `autopilot next` cannot select a task whose row is only on its branch, so a second run with `--count 2` was started (run decision 1). |
| 2 | Name of the command that carries a row into its workspace (plan D1) | `taskrail workspace <ID>` · `taskrail carry <ID>` · `new --from <ID> --workspace` | **`taskrail workspace <ID>`** | A public command name. |
| 3 | Conflicts with T071 outside the known classes at rebase | resolve textual ones and report · escalate every one | **keep both sides of a textual conflict, re-run every check and report it at hand-off; escalate a conflict in logic** | Recorded as run decision 3. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files or sections (run decision 2) | split by plan · serialize the lanes | **T070: `query.base_dict` (`base.row`), `writer.remove_task`, `ids.keep_reservation`, `cli.cmd_workspace` (new) and its parser entry, `cmd_next`'s suffix, `cmd_show`'s missing-row line, `cmd_new`'s warning and `_open_workspace`; in `dispatch.next_lanes` only the missing-row skip in the candidate loop's final `else`; the `taskrail` skill's step 3 and *Creating tasks*; DESIGN.md §6.3, the §7 rows for `show`, `next`, `new` and `workspace`, §7 *Dependencies and the base*; one README *Use* line; one CHANGELOG bullet. T071: the autopilot command modules, a new `branchrows.py`, `prior.py`, the rest of `dispatch.py`, a new `autopilot extend`; in `cli.py` only `cmd_new`'s `record_branch` closure, `cmd_show`'s `prior_work` call and `cmd_checks`' lookup; the `taskrail` skill's step 2; the `taskrail-autopilot` skill and lane brief; DESIGN.md §6.4, the §7 autopilot rows, §7.2 and §12, including the §12.1 `autopilot next` cell with T070's clause; README autopilot lines; one CHANGELOG bullet. Neither lane moves or renames code the other edits.** | Both plans name small, separable areas; this keeps their overlap to independent hunks. |

## plan gate

Reviewed: the plan in `docs/features/T070-detect-a-task-whose-row-is-missing-from.md` (commit
`7cf246e`, the artifact and its index row only), its ten acceptance criteria, the reproduction in a
scratch repository (an uncommitted row on `main`, `show` reporting `pending` on base `origin/main`,
and `claim` exiting 3 in a worktree created from that base), and `_open_workspace` in `cli.py` on
`fb9a26b`. The premise holds. No code changed, so no checks were re-run. T071's plan, at its plan gate
at the same time, covers the `on-branch` case this plan leaves to it.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | D1 Command name and interface | `taskrail workspace <ID>` · `carry` · `new --from` | **`taskrail workspace <ID> [--branch NAME] [--owner O] [--json]`** | Decided by the human. |
| 2 | D2 How `--json` reports the absence | `base.row` enum · boolean `base.has_row` · top-level field | as recommended | `next` and `autopilot next` need to tell `missing` from `on-branch`; a plain enum keeps the CLI contract explicit for any agent. |
| 3 | D3 Keep listing a `missing` task in `next` | list with a marker · omit | as recommended | It is still pending; the marker says what to do. |
| 4 | D4 `autopilot next` on a `missing` task | skip with reason · dispatch | as recommended | A lane must not edit the orchestrator's checkout; T071 dispatches the prepared workspace once the row is carried. |
| 5 | D5 When `new` warns | on the mainline only · also `push_task_branch` · whenever absent from base · config opt-out | as recommended | The case that has no path to the mainline; elsewhere the warning would be noise. |
| 6 | D6 Keep the carried ID reserved | keep · rely on a commit | as recommended | Closes the race in which another `new` reuses the ID. |
| 7 | D7 Narrow or general command | narrow · general | as recommended | The general form would overlap T071 and the skill's workspace step. |
| 8 | D8 Skill text | as proposed · amend | as recommended | It states the case and the command in the step where an agent meets it. |
| 9 | D9 DESIGN.md changes | as proposed · fewer | **as proposed, except the §12.1 `autopilot next` cell: T071 writes it, with T070's clause ("skips a task whose `base.row` is `missing`, with the reason")** | That cell is a single line both lanes would edit (touch map). |
| 10 | D10 CHANGELOG bullet | as proposed · amend | as recommended | An appended bullet, a known conflict class. |
| 11 | Branch record for `taskrail workspace` (orchestrator's addition) | record the branch · leave it unrecorded | **`taskrail workspace` records the branch it creates, as `new --workspace` will under T071** | T071 finds a task whose row lives only on its branch through the branch record; a carried row must be findable the same way. |

Instructions given with the answers: keep `cmd_new`'s `record_branch` closure where and as it is (T071
edits it), and leave the §12.1 `autopilot next` cell to T071.
