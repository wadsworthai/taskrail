# T006 — Add a reopen command for tasks marked done by mistake

Kind: feature · Epic: E02 · Status: implemented

## Behaviour

`taskrail reopen <ID> --reason "<why>"` moves a task that is `✅` done or `❌` discarded back to
`⬜` pending. Today the only way back is typing the status emoji by hand, which the core skill
forbids, and which leaves no record of why a closed task came back.

The backlog records state, not history, so the reason is **not** written to the backlog: the
command changes the status cell and nothing else. The trace lives in git instead. The command
returns a suggested commit message — a subject naming the task, the reason as the body, and a
`Reopens: <ID>` trailer — for whoever commits the change to use. `--reason` is required so that
message can never be empty.

The command follows the existing write rules: one cell changes, the edit is validated in memory
before anything is written, and `--json` returns the result. It needs no claim, since a closed
task has none, and it does not claim the task for the caller.

Tasks that depend on the reopened one and are already done or claimed may now rest on an
unfinished dependency. The command does not refuse for that; it lists them, in the text output
and as `dependents` in the JSON, so the caller can decide whether they need reopening too.

## Acceptance criteria

1. `reopen <ID> --reason R` on a done task sets its status cell to `⬜`; the file diff is
   exactly that one cell.
2. The same works on a discarded task.
3. On a pending task it exits 5 (refused) and writes nothing.
4. An unknown ID exits 3; a missing or blank `--reason` is a usage error (exit 2) and writes
   nothing.
5. An invalid backlog is refused with exit 1, as for every other write command.
6. The output includes a suggested commit message whose body is the reason and whose last line
   is the trailer `Reopens: <ID>`; `--json` returns it as `commit_message`, alongside `id`,
   `status` (`pending`) and `reason`.
7. The output lists done or claimed tasks that depend on the reopened one; `--json` returns
   them as `dependents`.
8. After reopening, `taskrail show` reports the task as `pending` (or `blocked`) and it can be
   claimed again.

## Test coverage

All in `tests/test_write.py`.

| Criterion | Tests |
|---|---|
| 1. One cell changes on a done task | `test_reopen_changes_only_the_status_cell_and_suggests_a_commit_message` |
| 2. Discarded tasks | `test_reopen_accepts_a_discarded_task` |
| 3. Pending task refused | `test_reopen_refuses_a_pending_task` |
| 4. Unknown ID; missing or blank reason | `test_reopen_refuses_an_unknown_task`, `test_reopen_requires_a_reason` |
| 5. Invalid backlog refused | `test_reopen_refuses_an_invalid_backlog` |
| 6. Suggested commit message | `test_reopen_changes_only_the_status_cell_and_suggests_a_commit_message`, `test_reopen_prints_the_suggested_message_in_text_output` |
| 7. Done or claimed dependents | `test_reopen_lists_dependents_that_are_done_or_claimed`, `test_reopen_reports_done_dependents_in_text` |
| 8. Pending again and claimable | `test_a_reopened_task_can_be_claimed_again` |

## Affected areas

- `src/taskrail/cli.py` — the `reopen` subcommand and its handler, reusing
  `writer.set_status`.
- `tests/test_write.py` — tests for the criteria above.
- `DESIGN.md` (§7 command table and write rules) and `README.md` (Use block).
- `src/taskrail/skills/taskrail/SKILL.md` — mention `reopen`, tell the agent to
  commit it on its own with the suggested message, and amend the close-step rule "a status cell
  that is `✅` on either side stays `✅`": a side whose history has a `Reopens: <ID>` commit
  keeps `⬜`. The installed copies under `.claude/skills/` are refreshed with `taskrail upgrade`.

## Out of scope

- Storing the reason in the backlog, a separate log file or a new column.
- `taskrail validate` detecting a reopen committed without the trailer — it has to read git
  history; follow-up task T012.
- Committing from the CLI; taskrail never commits the backlog.
- Reopening dependents automatically.
- Handling reopen in the git merge driver; that belongs to T004, which should honour the same
  rule the skill states here.

## Open questions and risks

- **The trace depends on the committer.** Nothing enforces that the suggested message is used
  until the follow-up validation exists. The skill makes it part of the procedure for agents.
- **Rebase conflicts.** A reopen on one branch against an unchanged `✅` on another merges
  cleanly, but the skill's "`✅` wins" rule would override it whenever the row conflicts for
  another reason. The skill change above addresses that; until T004 lands it relies on the
  agent following it.

Decisions at the plan gate: the reason goes in the commit message rather than the backlog, and
discarded tasks can be reopened too.

## Verification

Run through the real CLI (`uv run taskrail --root <repo>`) against a
throwaway git repository holding two done tasks (T002 depending on T001) and one discarded task:

- `reopen T001 --reason "Prices for refunds were never loaded"` exited 0, printed `T001
  pending`, `T002 depends on T001 and is done` and the suggested message; `git diff
  --word-diff` showed only `[-✅-]{+⬜+}` in T001's row, and `show T001` reported `pending`.
- Committing with the suggested message, `git log --format='%(trailers:key=Reopens,valueonly)'`
  printed `T001` and `git log --grep='^Reopens: T001$'` found the commit — the lookup the skill
  prescribes for rebase conflicts.
- Reopening T001 again exited 5 (`already pending`); a blank reason exited 2; `T099` exited 3;
  omitting `--reason` failed in argparse with `the following arguments are required: --reason`.
- `reopen T003 --reason "Still off by one" --json` on the discarded task exited 0 with
  `dependents: []` and the expected `commit_message`.
- `claim T001` then succeeded, and `validate` reported 0 errors.

In this repository, `.taskrail/bin/taskrail reopen T099 --reason x` exited 3 through the wrapper.
No difference from the plan was found.
