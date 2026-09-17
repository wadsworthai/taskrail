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

## implement gate

Reviewed: `git diff 0f51096..b091e95` — every `src/` hunk (`COMMIT_POLICIES` and `Config.commit`,
`Kind.commit`/`commit_source`, the top-level `commit` check and the post-loop effective policy in
`_parse`, which receives the loaded config, `commit_policy` and `commit_source_label`, `cmd_show`'s
`close` and text line, `_change_status`, `_on_done_refusal` and its three call sites), the DESIGN.md
hunks (§4, §5.1, §7, §12.1, §12.2, §13 marks) and the CHANGELOG bullet; the new
`tests/test_commit_policy.py` reported 25 failing before the code, including the config-level path
of criterion 4; the checks re-run with `taskrail checks T081 --stage implement` (1079 passed, lint
not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | §13.3's pointer is four lines, keeping `close.review` planned | four lines · one line with `close.review` moved | **as recommended** | §13.5 and T083's §13.8 row cite §13.3 for `close.review`; the pointer keeps T083's contract reachable. |
| 2 | The refusal call is two physical lines | keep · one line | **as recommended** | The file's style; still one self-contained hunk after the `enabled` check. |
| 3 | Approve the implement stage | approve · change | **approve** | The diff matches the plan and the touch map; every criterion has a test observed failing first. |
| 4 | (orchestrator) Wording of the §13 marks | T082's published form · keep this branch's | **T082's form** | The in-place lines end "— *implemented (T081)*, now §x.y" instead of leading "*Implemented (T081; …):*" or "(*implemented, T081*)", and the §13.8 row ends "; *implemented (T081)*" instead of a leading "*Implemented.*"; §13.3's pointer paragraph stays. The three branches then mark §13 alike. |

## close gate

Reviewed: the §13 mark rewording (`83d790b`), the verify section (`a96685a`) and `taskrail done`
committed on its own in `0263903` (only T081's status cell); no upstream on the branch; clean
worktree; `review --json` reports no rebase needed onto `origin/main` at close. Exercised with this
branch's CLI on a copy of the lane's scratch repository: with `[git] commit = "later"`, every command
exits 2 naming `git.commit`; with `"on-done"` and no override, `kind list --json` reports every core
kind `on-done` from `config` with every stage's `commit` false.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request title's type and scope | `feat(cli)` · other | **`feat(cli)`** | New CLI behaviour; CLAUDE.md asks for a scope. |
| 2 | Hand-off timing | now · after T082 and T080 | **after T082 and T080, in that order** | One branch at a time; T081 is rebased then, keeping both halves where it meets T080 (config load, `cmd_show`, the autopilot call lines, §4 and §12.2 notes) and T082 (§5.1 note, §13 lines), and the changelog. |

## rebase after T082 and T080

T082 (`49ccec0`) and T080 (`456f3bc`) were merged into main. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/features/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Known class 2: appended index rows and changelog bullets, one per task. |
| 2 | Conflict in `TODO.md` (status cells of T080, T081, T082) | ✅ wins per ID · stop | **✅ wins per ID** | Known class 1; no `Reopens:` commit on either side; `taskrail validate` clean. |
| 3 | Conflicts in `autopilot/commands.py` (the refusal call after `enabled`, ×3) and `cli.py` (`cmd_show`'s `searched` and `close` lines) | keep both · stop | **keep both: the `task_branch` refusal first, then the on-done refusal; both `cmd_show` lines** | Outside the known classes, so escalated; the human chose "the orchestrator combines both". Independent adjacent hunks the touch map predicted; §13.7 lists the `task_branch` refusal first. |
| 4 | Conflicts in DESIGN.md §4 (example lines, config-check paragraphs), §5.1, §7 `show` row, §12.2, §13.6, §13.7, §13.8 | combine · stop | **combine: keep each side's implemented text and marks, drop the "Planned" notes each side left for the other; §7's `show` row names `task_branch` and `close.commit` as current and only `close.review` as planned** | Same escalation and answer; each side had marked its own part implemented and the other's planned. |

Answered by the human (repository owner), in the orchestrator session, for items 3 and 4.

After the rebase: no conflict markers (`git diff --check` clean); `taskrail validate` reports no
errors or warnings; `taskrail checks T081` re-run: 1118 passed (lint not configured). Exercised the
combined CLI in a scratch repository with `worktree = "never"`, `task_branch = "current"` and
`commit = "on-done"`: `autopilot start --count 1` exits 5 with the `task_branch` message first, and
`show --json` reports `task_branch` `current`, `branch_source` `current` and `close` `{"commit": "on-done"}`.
