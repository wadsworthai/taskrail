# T081 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan `docs/features/T081-commit-a-task-s-changes-only-when-it-is.md` (commit
`6837207`, the artifact and its index row only, clean worktree), its 9 acceptance criteria against
DESIGN.md §13.1, §13.3, §13.6, §13.7 and the T081 rows of §13.8 and TODO.md; `dispatch.run_kinds`
reads only a run's stored `kinds`, which a named run leaves empty. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | A text line in `show` under on-done | `commit on-done (<source>)` only under on-done · no text change | **as recommended** | Explains why no stage shows `commit`, and default output stays identical. |
| 2 | Driven kinds of a named run for `extend` and `next --run` | kinds of its named tasks · every allowed kind | **as recommended** | A named run can dispatch only its named tasks; the literal reading would refuse runs that never meet an on-done kind. Say so in §12.1/§13.7. |
| 3 | Wording of the autopilot refusal | as proposed, every offending kind with its source · other | **as recommended** | Names the kind and the source, as §13.7 requires. |
| 4 | Approve the plan and its touch map | approve · change | **approve** | The criteria cover the T081 row. The on-done effective stage `commit` must hold for a `[git].commit` set in config as well as for a descriptor's policy, in both `show` and `kind list` (criterion 4). |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How §13 is marked once a part is implemented (run decision 1) | one-line pointer for a moved subsection, in-place marks for shared bullets and own §13.8 row · keep full text | **one-line pointer for §13.3 and in-place marks; never §13's introduction, summary table or another lane's lines** | Same convention on T080, T081, T082. |
| 2 | Touch map, T081's part (run decision 4) | as planned · narrower | **config.py `COMMIT_POLICIES`, `Config.commit` and its load lines after `push_task_branch`; kinds.py `Kind.commit`/`commit_source`, `to_dict`, top-level `commit` next to `commit_type` in `_parse`, one hunk after the stage loop, `commit_policy`; cli.py one `close` line and text line in `cmd_show`, `_change_status`; autopilot/commands.py `_on_done_refusal` with one call line in `cmd_start`, `cmd_extend`, `cmd_next`; new tests/test_commit_policy.py; DESIGN.md §4 commit parts, §5.1 commit half of the planned note, §7 show and done/discard rows, on-done half of §12.1 rows and §12.2 bullet, §13.3, own bullets of §13.1/§13.6/§13.7, §13.8 T081 row; one CHANGELOG bullet** | From T081's plan. Shared with T080: config load (separate lines), `cmd_show`, the three autopilot call lines, the §4 planned note, the §7 `show` row and the §12.2 bullet — textual conflicts keep both halves. Shared with T082: separate hunks of `kinds.py` and §5.1's planned note, and the changelog. |
