# T071 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Create and run this task | — | **create it with `taskrail new --workspace` and run it in autopilot run 20260915-2, joined with `claim --run`** | The human asked for the task and then to raise the autopilot to three tasks including it. No command raises a run's count and `autopilot next` cannot select a task whose row is only on its branch, so a second run with `--count 2` was started (run decision 1). |
| 2 | Extending a live run with more tasks or a higher count (plan Q3) | a follow-up task · include it in T071 | **include it in T071** | The human's own case in this session: they asked to add tasks to a running autopilot. |
| 3 | Conflicts with T070 outside the known classes at rebase | resolve textual ones and report · escalate every one | **keep both sides of a textual conflict, re-run every check and report it at hand-off; escalate a conflict in logic** | Recorded as run decision 3. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files or sections (run decision 2) | split by plan · serialize the lanes | **T070: `query.base_dict` (`base.row`), `writer.remove_task`, `ids.keep_reservation`, `cli.cmd_workspace` (new) and its parser entry, `cmd_next`'s suffix, `cmd_show`'s missing-row line, `cmd_new`'s warning and `_open_workspace`; in `dispatch.next_lanes` only the missing-row skip in the candidate loop's final `else`; the `taskrail` skill's step 3 and *Creating tasks*; DESIGN.md §6.3, the §7 rows for `show`, `next`, `new` and `workspace`, §7 *Dependencies and the base*; one README *Use* line; one CHANGELOG bullet. T071: the autopilot command modules, a new `branchrows.py`, `prior.py`, the rest of `dispatch.py`, a new `autopilot extend`; in `cli.py` only `cmd_new`'s `record_branch` closure, `cmd_show`'s `prior_work` call and `cmd_checks`' lookup; the `taskrail` skill's step 2; the `taskrail-autopilot` skill and lane brief; DESIGN.md §6.4, the §7 autopilot rows, §7.2 and §12, including the §12.1 `autopilot next` cell with T070's clause; README autopilot lines; one CHANGELOG bullet. Neither lane moves or renames code the other edits.** | Both plans name small, separable areas; this keeps their overlap to independent hunks. |

## plan gate

Reviewed: the plan in `docs/features/T071-run-the-autopilot-on-named-tasks-includi.md` (commit
`08a4c62`, the artifact and its index row only), its twelve acceptance criteria, the premise
reproduced in a scratch repository (a count-only run dispatching the cheaper task, `new --workspace`
writing no branch record, `show` and `autopilot lane` exiting 3 from the main checkout, the lane brief
stopping on an existing branch, and lanes in use differing by checkout), and `dispatch.next_lanes` on
`fb9a26b`, where a member whose `project.task()` is `None` gets the state `None`. The premise holds. No
code changed, so no checks were re-run. T070's plan, at its plan gate at the same time, leaves the
`on-branch` case to this task and skips `missing` rows in `autopilot next`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Q1 `--tasks` and `--count` | implied, `--count` must match · mutually exclusive · a pool | as recommended | The human's request names tasks; a matching `--count` stays harmless and a mismatch is a usage error. |
| 2 | Q2 Dispatch order of a named run | the order given · points then file order | as recommended | The human named the order. |
| 3 | Q3 Extend a live run | follow-up task · include | **include: `taskrail autopilot extend <R> [--tasks IDs] [--count N] [--json]`** — `--tasks` appends to a named run's `named` (duplicates and IDs already named dropped) and raises `count` by the number added, with `start`'s refusals; `--count N` on a count-only run sets a count no lower than the tasks already counted toward it (else exit 5); `--count` on a named run, `--tasks` on a count-only run, or neither flag, exit 2; a closed run exits 5. The skill's *When to run* says to extend the run when the human adds tasks to it, and `status`/`next` reflect the new count at once. | Decided by the human; the interface is the orchestrator's, from the plan's own sketch. |
| 4 | Q4 The occupancy bug | include · follow-up bug | as recommended | The same row lookup fixes it, and named tasks on their own branches make it the normal case. |
| 5 | Q5 Finding a task before it is claimed | `new --workspace` records its branch · scan every branch | as recommended | Deterministic and cheap. T070's `taskrail workspace` records its branch the same way. |
| 6 | Q6 Recognising a prepared workspace | by content · a marker | as recommended | It holds whoever made the branch, and cannot go stale. |
| 7 | Q7 The three `cli.py` edits and the `taskrail` skill's step 2 | yes, confined · T070 makes them · leave `checks` out | as recommended, confined to `cmd_new`'s `record_branch` closure, `cmd_show`'s `prior_work` call and `cmd_checks`' lookup | The touch map gives the rest of `cli.py` to T070. |
| 8 | Q8 One task | one · split | **one, including `autopilot extend`** | Decided with Q3. |
| 9 | Relative `worktree` in `next --json` for a worktree not yet created (noticed) | follow-up task · leave | **open a follow-up task (kind bug) on this branch** | Outside this task's scope, and a real inconsistency in the CLI contract. |

Instructions given with the answers: add `autopilot extend` to the plan's Behaviour, acceptance
criteria and affected areas before implementing; write the §12.1 `autopilot next` cell with T070's
clause "skips a task whose `base.row` is `missing`, with the reason"; do not touch `_open_workspace`
or other parts of `cli.py`.

## implement gate

Reviewed: the range `c39b5fd..25895c8`: the plan update adding `extend` (`004a149`), the T072 row
(`1efa7d9`), and the implementation (`25895c8`), read in `branchrows.py`, `autopilot/dispatch.py`,
`autopilot/runs.py` and `cli.py` — the latter only in `cmd_show`'s `prior_work` call, `cmd_new`'s
`record_branch` closure and `cmd_checks`' lookup, as approved; `dispatch.next_lanes`' final `else`
untouched for T070. A row adopted from its branch reads `on-branch` under T070's `base.row`, so T070's
missing-row skip does not hide it. The touched files match the touch map. Re-ran
`taskrail checks T071 --stage implement`: `test` gave `994 passed in 142.47s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `status` shows a named task claimed outside its run as `pending`, without the claim | accept · show `running` with a `silent` guard | as recommended | A `running` row could read `silent` and invite restarting another session's work; `next` already says `claimed by <owner>`. |
| 2 | `runs.members` (every task a run holds) beside `dispatch._members` (its lanes) | accept · one function with a flag | as recommended | The two answer different questions, and the docstrings say which. |
| 3 | The integration notes' "Lanes create their worktrees with git" | leave unchanged · "create or use" | **change it to say lanes create or use their worktrees with git, never through the agent's worktree isolation, in `src/taskrail/integrations/claude.md` and `opencode.md` where the sentence appears, then `taskrail upgrade`** | A prepared lane uses an existing worktree, so the sentence is now inaccurate for the case this task adds; the files are outside T070's areas, so the touch map extends to them for T071. |
| 4 | T072 opened on this branch | — | noted | Opened as instructed at the plan gate. |

## close

Reviewed: the integration note change (`8c2154d`: `integrations/claude.md`, its installed copy and the
manifest; `opencode.md` has no such sentence), the verify stage run in a scratch repository and
recorded in the artifact (`14c509e`), with no gap against the plan; `taskrail done` committed on its
own (`f18a653`); the backlog differs from the base only in this task's row, as `✅`, and the T072 row
this task opened. `governing_touched` is empty and the branch has no upstream. `review --json`
reported `rebase.needed: true` onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | `feat(autopilot)` · `feat(cli)` | **`feat(autopilot)`** | The change is the autopilot's named runs, `extend` and prepared workspaces; the CLI edits serve them. |

## rebase after T069 and T070

T069 (`877f687`) and T070 (`9d04f08`) were merged into `main`. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |
| 2 | Conflict in `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |
| 3 | Conflict in `.taskrail/installed.json` (the hash of `.claude/skills/taskrail/SKILL.md`) | make the manifest valid and run `upgrade --force` · stop | **took one side, ran `taskrail upgrade --force`, which rewrote the hash from the merged copy** | The installed-copies class. |

`src/taskrail/cli.py` (`cmd_new` next to T070's warning, `cmd_show`, `cmd_checks`),
`src/taskrail/autopilot/dispatch.py`, DESIGN.md, the `taskrail` skill source and copy, README,
CHANGELOG and TODO.md merged without conflict; the §12.1 `autopilot next` cell carries T070's clause
once. No textual conflict outside the known classes arose, so run decision 3 was not needed. After
the rebase: `git diff --check origin/main` reports nothing, a second `taskrail upgrade` reports every
file up to date, `taskrail checks T071` gave `1022 passed in 154.25s` (`lint` not configured), and
`taskrail validate` reports `61 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
