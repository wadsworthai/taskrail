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

## implement gate

Reviewed: commit `3c51604` by file (`git show`): `query.row_on_base` and `base.row`; `ids.keep_reservation`
with the atomic write factored into `_store_reservations`; `writer.row_values` and `remove_task`; the
three-line missing-row skip in `dispatch.next_lanes`; in `cli.py` the `show` line, `next`'s marker,
`new`'s warning, `_probe_task`/`_workspace_target`/`_open_workspace` (the `record_branch` closure
untouched) and `cmd_workspace` with its refusals, undo and branch record; the `taskrail` skill source
and its installed copy; DESIGN.md §6.3, the §7 rows and *A row missing from its base* (§12.1
untouched); one README line; one CHANGELOG bullet; `tests/test_row_on_base.py`, which the lane
reports as 28 failing before the code. The touched files match the touch map. Re-ran
`taskrail checks T070 --stage implement`: `test` gave `987 passed in 128.68s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Add `"row": "on-base"` to the whole-object `base` assertions in `tests/test_workspace.py` and `tests/test_mainline_remote.py` | keep the one-line change · loosen the assertions | as recommended | The field is approved (D2); the tests keep checking the whole contract. |
| 2 | Keep `reservation_added` in `workspace --json` | keep · drop | as recommended | It makes D6 observable, and DESIGN.md documents it. |
| 3 | Placement of the D8 paragraph in *Creating tasks* | after "It refuses …" as its own paragraph · mid-paragraph | as recommended | The approved text is unchanged, and "It refuses" still refers to `--workspace`. |
| 4 | `worktree = "never"` cannot carry a row committed at the checkout's `HEAD` (exit 5, row restored) | accept, documented · commit or stash the removal | as recommended | The case the task addresses is an uncommitted row; committing or stashing on the user's behalf was ruled out by the plan. |

## close

Reviewed: the verify stage ran the CLI from this branch in two scratch repositories (with and without
worktrees) and recorded the transcript in the artifact (`a7a2596`); nothing differed from the plan.
`taskrail done` is committed on its own (`1b40281`) and the backlog differs from the base only in this
task's row, as `✅`. `governing_touched` is empty, the branch has no upstream, and `review --json`
reported `rebase.needed: true` onto `origin/main`, which had gained T069 (`877f687`).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | `feat(cli)` · `feat(autopilot)` | **`feat(cli)`** | The main change is the CLI's `base.row`, `workspace` command and `new` warning; the autopilot part is a three-line skip. |

## rebase after T069

T069 was merged into `main` (`877f687`). The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |

`README.md` and `TODO.md` merged without conflict. After the rebase: `git diff --check origin/main`
reports nothing, `taskrail checks T070` gave `987 passed in 130.28s` (`lint` not configured), and
`taskrail validate` reports `59 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
