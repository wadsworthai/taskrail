# T070 — Detect a task whose row is missing from its base and carry the row into its workspace

Kind: feature · Epic: E05 · Status: verified (plan approved: D1–D10 as recommended, except that
DESIGN.md §12.1's `autopilot next` cell is left to T071; decision 11 added: `workspace` always records
its branch; implementation approved, including the two whole-object `base` assertions,
`reservation_added`, the *Creating tasks* paragraph placement and the `worktree = "never"`
limitation for a row committed at `HEAD`). Run `20260915-2`. Record:
`docs/autopilot/decisions/T070-detect-a-task-whose-row-is-missing-from.md`.

## Today

Reproduced with this branch's CLI in a scratch repository (a `main` pushed to a bare `origin`, one
task `T001` committed):

```text
$ taskrail new --epic E01 --kind bug --title "Negative totals" --json
{ "id": "T002", "backlog": "main", "epic": "E01", "files": ["TODO.md"] }      # exit 0, no warning
$ git status --porcelain
 M TODO.md
$ taskrail show T002 --json          # state and base only
{ "state": "pending",
  "base": { "onto": "origin/main", "diverged": false,
            "reason": "origin/main is up to date with or ahead of main", "remote": "origin",
            "remote_source": "branch.main.remote", "commit": "c64cf5a…", "dependency": null } }
$ taskrail next
T001   ⬜ pending     chore     2pt  E01   Price table
T002   ⬜ pending     bug         —  E01   Negative totals
$ git show origin/main:TODO.md | grep -c T002
0
$ git worktree add --no-track .worktrees/T002-negative-totals -b T002-negative-totals origin/main
$ taskrail --root .worktrees/T002-negative-totals claim T002
taskrail: no task `T002`                                                       # exit 3
```

- `new` without `--workspace` writes the row into whatever checkout it runs in. On a mainline
  checkout of a repository where changes reach the mainline only through pull requests, that row
  has no path to the mainline, and nothing says so.
- `show`, `next` and `list` read the working tree; `base.onto` names a ref that lacks the row, and
  nothing reports it. `autopilot next` would dispatch such a task, and its lane's `claim` would exit 3.
- The only recovery is by hand: discard the row and recreate the task with `new --workspace`, which
  gives it a new ID. `ids.reserve` drops a reservation only once its ID appears in a backlog file
  (§6.3), so the first ID is still reserved, and it is lost.

## Behaviour

After this change:

1. **`base.row` reports where the task's row is relative to its base.** `show --json`'s `base` (and
   so every task in `list --json`, `next --json` and `autopilot next --json`) gains `row`:
   - `"on-base"` — the backlog's files at `onto` have a task row with this ID (any status);
   - `"on-branch"` — `onto` lacks it, but the task's branch (§6.4) exists, locally or as
     `<remote>/<branch>`: the task already has its workspace and the row travels on that branch,
     as after `new --workspace` (committed or not yet);
   - `"missing"` — `onto` lacks it and the task has no branch: the row exists only in this checkout
     (uncommitted, or committed on a branch that is not the base), and a workspace created from
     `onto` would not contain it;
   - `null` when `onto` is `null`.
   The backlog files at each distinct `onto` are read once per command with one
   `git cat-file --batch` (the main file and the epic files it names at that revision), cached per
   project as the `done-branch` scan is. Nothing is fetched.
2. **`show` text** adds, for `missing`, the line
   `  row not on origin/main: only this checkout has it; run \`taskrail workspace T002\``.
3. **`next`** keeps listing such a task (it is still `pending`), and its text line ends with
   `  (row not on origin/main)`. `list`'s text is unchanged.
4. **`autopilot next`** skips a candidate whose `base.row` is `missing`, with the reason
   `row not on origin/main: run taskrail workspace T002`, so no lane is dispatched to a task it
   cannot claim. A candidate whose row is `on-branch` is not skipped by this rule (T071 decides how a
   prepared workspace is dispatched).
5. **`taskrail workspace <ID> [--branch NAME] [--owner O] [--json]`** carries a `missing` row into the
   task's own workspace:
   - it creates the task's branch — without an upstream — and worktree from `base.onto`, exactly as
     `new --workspace` does (the branch in this checkout when `worktree = "never"`);
   - it appends the row, with its ID and every cell as it is here (status, kind, points,
     dependencies, title, description, custom columns), to the same epic in the workspace;
   - it removes the row from the checkout it ran in, deleting only that line;
   - it keeps the ID reserved (re-adding the reservation when an earlier `reserve` dropped it),
     since the row is uncommitted in the workspace and appears in no scanned file until committed;
   - it records the branch it creates (§6.4) — the template's name, or `--branch NAME`, validated as
     for `new --branch` — mirrored to `branch_record_remote` as `claim` mirrors, so a row that lives
     only on its branch is found through that record, as for `new --workspace` (decision 11);
   - like `new --workspace`, it fetches mirrored branch records first and commits nothing: the
     executor commits the row inside the workspace, then claims.
   `--json` returns `id`, `backlog`, `epic`, `branch`, `workspace`, `base`, `files` (written in the
   workspace), `removed_from` (`path` of the origin checkout, `files`, and `uncommitted`: whether
   those files now differ from its `HEAD` — true when the row had been committed there, so the
   deletion needs a commit), `reservation_added` (whether the ID had to be reserved again) and
   `record_remote`.
   Order: every refusal below is checked, and the removal validated in memory, before any branch is
   created; then the workspace is created and its row written (validated; on failure the workspace
   and branch are removed); then the removal is written. With `worktree = "never"` the removal is
   written first, the checkout must then be clean, and the branch is switched to; otherwise the
   removal is undone and the command refuses.
   Refusals, changing nothing: exit 3 for an unknown ID, or for an epic that does not exist on
   `onto`; exit 5 when the task is not pending, is `done-branch` or `discarded-branch`, when
   `base.row` is `on-base` (nothing to carry: create the workspace as the skill says) or
   `on-branch` (the branch exists), when the mainlines have diverged or two or more dependencies are
   unmerged, when the worktree path exists, or, with `worktree = "never"`, when the checkout has
   other uncommitted changes; exit 4 when the task is claimed by someone else, exit 5 when claimed by
   the caller (release it first: its claim names this checkout); exit 1 when writing the row in the
   workspace, or removing it here, would leave that backlog invalid (for example a dependency that
   exists only in this checkout, or another row here that depends on it); exit 2 for a bad
   `--branch` or no base.
6. **`new` without `--workspace` warns on a mainline checkout.** When the checkout's current branch is
   the mainline of the task's backlog, `new` still writes the row and exits 0, and prints on stderr
   `taskrail: warning: T002 was written to this checkout of main, uncommitted; commit it to main, or
   run \`taskrail workspace T002\` to move it into its own branch`. `--json` gains `warning` (that
   text, else `null`; always `null` with `--workspace`). On any other branch — a task branch adding
   a follow-up task, the documented flow — or a detached `HEAD` there is no warning.
7. **The `taskrail` skill** names the case in its workspace step and under *Creating tasks* (text in
   D8).

## Acceptance criteria

1. In a repository whose `main` is pushed to `origin`: `show T00x --json` reports `base.row`
   `on-base` for a committed task; `missing` for a row `new` wrote uncommitted on `main`, and for a
   row committed on a checked-out branch that is not the base; `on-branch` in the workspace
   `new --workspace` created (before and after the row's commit); `null` when the mainlines have
   diverged.
2. `show` text for a `missing` row contains `row not on origin/main` and
   `taskrail workspace <ID>`; for an `on-base` row it has no such line.
3. `next --json` still lists the `missing` task with `base.row` `missing`; `next` text marks it with
   `(row not on origin/main)` and leaves other lines unchanged.
4. `autopilot next --json` (preview and `--run`) skips a `missing` candidate with a reason naming
   `onto` and `taskrail workspace <ID>`, records no dispatch for it, and still dispatches the
   other candidates.
5. `taskrail workspace <ID> --json` with worktrees: creates `.worktrees/<branch>` on the task's
   branch from `origin/main` with no upstream; the workspace's backlog has the row with the same ID
   and cells (points, dependencies, description and a custom column included); the origin
   checkout's backlog no longer has it and `git status --porcelain` there is empty; `reserve-id`
   afterwards returns the next number, not the carried ID; `claim <ID>` inside the workspace exits
   0; `show <ID> --json` there reports `base.row` `on-branch` and `branch_source` `recorded`
   (decision 11). The JSON fields listed in Behaviour 5 are present.
6. With `worktree = "never"`: the checkout is switched to the task's branch with the row written
   there; with another uncommitted change it exits 5, the checkout stays on `main` and still has the
   row.
7. Each refusal of Behaviour 5 exits with its code and changes nothing — no branch, no worktree, the
   row still in the origin checkout, the reservation unchanged: unknown ID (3), `on-base` (5),
   existing branch (5), not pending (5), claimed by someone else (4), diverged mainlines (5), epic
   missing on the base (3), a dependency only in this checkout (1, the workspace and branch
   removed), another row here depending on it (1).
8. `--branch NAME` creates and records that branch (`show` reports `branch_source` `recorded`); an
   invalid name exits 2 before anything is created.
9. `new` without `--workspace` on `main` exits 0, prints the warning naming
   `taskrail workspace <ID>` on stderr and returns it in `warning`; on another branch it exits 0 with
   no warning and `warning: null`.
10. The shipped `taskrail` skill (source and installed copies) names `base.row` and
    `taskrail workspace <ID>` in its workspace step, and the existing test that every command and
    flag a skill shows exists passes with the new command in the parser.

## Tests per criterion

All in `tests/test_row_on_base.py` unless named otherwise. Each was observed failing before the
implementation (28 failed): `KeyError: 'row'` for the `base.row` tests; the `show` text line and the
`autopilot next` skip absent (`assert {'id': 'T004', 'reason': …} in []`); `argparse` exit 2,
`invalid choice: 'workspace'`, for every `workspace` test; `KeyError: 'warning'` for `new`; the
skill phrases absent from the source and both installed copies; `KeyError: 'workspace'` in the parser.

| Criterion | Test |
|-----------|------|
| 1 | `test_base_row_is_on_base_for_a_committed_task_and_missing_for_one_only_this_checkout_has`, `test_a_row_committed_on_a_branch_that_is_not_the_base_is_missing`, `test_base_row_is_on_branch_in_the_workspace_new_created` (before and after the row's commit), `test_base_row_is_null_when_the_mainlines_have_diverged` |
| 2 | `test_show_text_names_the_missing_row_and_the_command` |
| 3 | `test_next_keeps_a_missing_row_and_marks_it` (JSON `row` for both tasks; the marked line; every other line identical to `next` before the row existed) |
| 4 | `test_autopilot_next_skips_a_missing_row_and_dispatches_the_rest` (preview and `--run`; T002 dispatched; T004 absent from the run's tasks) |
| 5 | `test_workspace_carries_the_row_with_its_id_and_cells` (points, dependency, a description with an escaped pipe, a custom column; the whole `--json` result; no upstream; fork point `origin/main`; the origin backlog back to its committed content; T004's reservation dropped by a `reserve-id` while the row sat in the checkout, re-added, so the next `reserve-id` returns T005; `branch_source` `recorded`, `row` `on-branch`, `claim` exit 0 in the workspace), `test_workspace_text_output` |
| 6 | `test_workspace_switches_this_checkout_when_worktrees_are_off`, `test_workspace_refuses_other_uncommitted_changes_when_worktrees_are_off` |
| 7 | `test_workspace_refuses_an_unknown_task`, `…_a_row_already_on_its_base`, `…_a_task_whose_branch_exists`, `…_a_task_that_is_not_pending`, `…_a_claimed_task` (4 for another owner, 5 for the caller), `…_diverged_mainlines`, `…_an_epic_missing_on_the_base`, `…_a_row_whose_dependency_only_this_checkout_has`, `…_a_row_another_row_here_depends_on` — each through a helper asserting the backlog and the reservations are unchanged, and that no branch or worktree is left |
| 8 | `test_workspace_branch_names_and_records_the_branch`, `test_workspace_refuses_an_invalid_branch_name` |
| 9 | `test_new_without_workspace_warns_on_the_mainline`, `test_new_on_another_branch_or_with_a_workspace_does_not_warn` |
| 10 | `test_the_core_skill_names_base_row_and_the_workspace_command` (source, `claude` and `opencode` copies), `test_the_workspace_command_and_its_flags_exist` |

Implementation notes:

- `tests/test_workspace.py::test_show_reports_the_base` and
  `tests/test_mainline_remote.py::test_show_uses_the_remote_the_mainline_tracks` compare the whole
  `base` object; the full run failed on both with `Left contains 1 more item: {'row': 'on-base'}`, and
  each expected object now includes `"row": "on-base"`. Neither file was listed in the affected areas.
- `_open_workspace` now takes a task: `cmd_new` builds its probe with a new `_probe_task`, and the
  checks it made moved into `_workspace_target`, which `cmd_workspace` also runs before changing
  anything. `cmd_new`'s `record_branch` closure is unchanged.
- `writer.row_values` (new, next to `remove_task`) reads the row's cells by its table's header, so a
  cell whose optional column is absent is not invented, and escaped pipes survive the move.
- `--json` gained `reservation_added`, not named in the plan, so the caller can see D6 at work.
- *Creating tasks*: the approved paragraph sits after the `--workspace` paragraph's last sentence
  ("It refuses when the mainlines have diverged or the branch already exists."), not before it, so
  that sentence keeps referring to `--workspace`; "Add epics with …" became its own paragraph.
- `.claude/skills/taskrail/SKILL.md` and `.taskrail/installed.json` were updated with
  `taskrail upgrade`.
- DESIGN.md §12.1 is not edited (decision 9): *A row missing from its base* in §7 only points to it.

## Verify

The real CLI from this branch (`uv run --project <worktree> taskrail`), in two scratch repositories
outside this clone: `main` with `T001` (✅) and `T002` (⬜, depends on `T001`), pushed to a bare
`origin` it tracks, `[autopilot]` enabled, `.worktrees/` ignored. Output trimmed only where marked.

**A. `worktree = "required"`.**

```text
$ taskrail new --epic E01 --kind bug --title "Negative totals" --pts 2 --depends-on T001 --description "Refunds | credits" --json
taskrail: warning: T003 was written to this checkout of main, uncommitted; commit it to main, or run `taskrail workspace T003` to move it into its own branch
{ "id": "T003", "backlog": "main", "epic": "E01",
  "warning": "T003 was written to this checkout of main, uncommitted; commit it to main, or run `taskrail workspace T003` to move it into its own branch",
  "files": ["TODO.md"] }                                                          # exit 0
$ git status --porcelain
 M TODO.md
$ taskrail show T003                                                             # first 6 lines
T003 — Negative totals
  backlog main · epic E01 · kind bug · state pending
  points 2 · depends on T001
  base origin/main (origin/main is up to date with or ahead of main)
  row not on origin/main: only this checkout has it; run `taskrail workspace T003`
  skill taskrail-bug
$ taskrail show T003 --json                                                      # base only
{ "onto": "origin/main", "diverged": false, "reason": "origin/main is up to date with or ahead of main",
  "remote": "origin", "remote_source": "branch.main.remote", "commit": "ac9af54…", "dependency": null, "row": "missing" }
$ taskrail next
T003   ⬜ pending     bug       2pt  E01   Negative totals  ← T001  (row not on origin/main)
T002   ⬜ pending     feature   3pt  E01   Repricing  ← T001
$ taskrail autopilot next --json                                                 # dispatch IDs and skipped
{ "dispatch": ["T002"], "skipped": [{ "id": "T003", "reason": "row not on origin/main: run taskrail workspace T003" }] }
$ taskrail workspace T002
taskrail: T002 is already on origin/main; nothing to carry: create its workspace as the taskrail skill's workspace step says
exit 5
$ taskrail reserve-id                  # drops T003's reservation: T003 is in the working tree
T004
$ taskrail unreserve-id T004
cancelled reservation T004
$ taskrail workspace T003 --json
{ "id": "T003", "backlog": "main", "epic": "E01", "branch": "T003-negative-totals",
  "workspace": "<scratch>/a/.worktrees/T003-negative-totals", "base": "origin/main", "files": ["TODO.md"],
  "removed_from": { "path": "<scratch>/a", "files": ["TODO.md"], "uncommitted": false },
  "reservation_added": true, "record_remote": null }                              # exit 0
$ git status --porcelain
                                                                                  # clean
$ grep T003 .worktrees/T003-negative-totals/TODO.md
| ⬜ | T003 | bug     | 2   | T001       | Negative totals | Refunds \| credits |
$ git -C .worktrees/T003-negative-totals status --porcelain
 M TODO.md
$ taskrail reserve-id                  # T003 is reserved again, so not handed out
T004
$ taskrail --root .worktrees/T003-negative-totals show T003 --json               # branch, branch_source, base.row
T003-negative-totals recorded on-branch
$ taskrail workspace T003              # the row has left this checkout
taskrail: no task `T003`
exit 3
$ git -C .worktrees/T003-negative-totals commit …; taskrail --root .worktrees/T003-negative-totals claim T003
claimed T003 as abigail@archlinux                                                # exit 0
$ git switch -c topic; taskrail new --epic E01 --kind chore --title Follow-up --json
{ "id": "T005", "backlog": "main", "epic": "E01", "warning": null, "files": ["TODO.md"] }   # exit 0, no stderr warning
```

**B. `worktree = "never"`.**

```text
$ taskrail new --epic E01 --kind bug --title "Negative totals"
taskrail: warning: T003 was written to this checkout of main, uncommitted; commit it to main, or run `taskrail workspace T003` to move it into its own branch
T003
$ echo draft > NOTES.md; taskrail workspace T003
taskrail: this checkout has uncommitted changes; commit or set them aside before switching branch
exit 5
$ git branch --show-current; git status --porcelain
main
 M TODO.md
?? NOTES.md
$ rm NOTES.md; taskrail workspace T003
T003
workspace <scratch>/b on branch T003-negative-totals from origin/main
removed from <scratch>/b: TODO.md
$ git branch --show-current; git status --porcelain; git show main:TODO.md | grep -c T003
T003-negative-totals
 M TODO.md
0
```

No gap against the plan.

## Affected areas

Named by file and function, for the touch map.

- `src/taskrail/query.py` — `base_dict` gains `row`; a new cached helper `row_on_base(task, project,
  onto)` (reads the backlog at `onto` through `stack._read_statuses`, and the task branch's refs).
- `src/taskrail/cli.py` — `cmd_show` (one text line), `cmd_next` (text suffix), `cmd_new` (the
  warning and `warning` in the result; the `Task` probe moves out of `_open_workspace`, which then
  takes a task), a new `cmd_workspace` next to `cmd_new`, and its parser registration in
  `build_parser`.
- `src/taskrail/writer.py` — new `remove_task(edits, task)` and `row_values(edits, task)`, sharing
  a `_row_of` lookup.
- `src/taskrail/ids.py` — a new `keep_reservation(config, backlog, task_id, owner)`.
- `src/taskrail/autopilot/dispatch.py` — `next_lanes`, the candidate loop's final `else:` branch
  (one more skip reason after the base check). Shared with T071; my change is those few lines.
- `tests/test_row_on_base.py` (new) — criteria 1–10; `tests/test_workspace.py` and
  `tests/test_mainline_remote.py`, one expected `base` object each (see *Implementation notes*).
- `src/taskrail/skills/taskrail/SKILL.md` — step 3 *Workspace* (one sentence added after the
  `base.onto` is null rule) and *Creating tasks* (one sentence after the `--workspace` paragraph);
  then `taskrail upgrade` for `.claude/skills/taskrail/SKILL.md` and `.taskrail/installed.json`.
- `DESIGN.md` — §6.3 (one sentence on the kept reservation), §7 CLI table (`show`, `next`, `new`
  rows, a new `workspace` row), §7 *Dependencies and the base* (`row` in the field list plus a
  paragraph *A row missing from its base*). §12.1's `autopilot next` cell is T071's (decision 9).
- `README.md` — one line in *Use*: `taskrail workspace T012   # move a row only this checkout has into its own branch and worktree`.
- `CHANGELOG.md` — one *Unreleased* bullet.
- `docs/features/README.md` — index row.

Not touched: `src/taskrail/autopilot/commands.py` (`autopilot start`), the lane brief
(`references/lane-brief.md`), the `taskrail-autopilot` skill, `stack.py`, `claims.py`.

## Out of scope

- `autopilot start --tasks`, and dispatching a task whose prepared workspace `new --workspace`
  created (T071).
- A general `taskrail workspace <ID>` that also creates the workspace for a task whose row is on its
  base, replacing the skill's `git worktree add` commands (a follow-up task if D7 chooses the narrow
  form).
- Committing the row automatically in the workspace or the removal in the origin checkout.
- A row whose cells differ between this checkout and its base (uncommitted edits to an existing
  task), an epic row missing from the base, and rows present only in another clone.
- Changing `list` text or `state`: a `missing` task stays `pending`.

## Open questions and risks

- **D1 — command name and interface.** Recommendation: `taskrail workspace <ID> [--branch NAME]
  [--owner O] [--json]`, the name the task context suggested, which a later generalization (D7) can
  keep. Alternatives: `taskrail carry <ID>` (names the move, not the result); `taskrail new --from
  <ID> --workspace` (reuses `new`'s flags, but `new` allocates IDs and this must not).
- **D2 — how the absence is reported in `--json`.** Recommendation: `base.row` with `on-base`,
  `on-branch`, `missing` or `null`, because `next`'s marker and `autopilot next`'s skip need
  "missing and no branch", which a boolean cannot say without every consumer also reading
  `prior_work.branches`. Alternatives: a boolean `base.has_row` (true/false/null), leaving the
  branch check to consumers; or a top-level `row_on_base` outside `base`.
- **D3 — `next` and a `missing` task.** Recommendation: keep listing it, marked, since it is still
  workable through `taskrail workspace`. Alternative: leave it out of `next` (like `done-branch`),
  which would hide the task from a human who ran `new` on the mainline.
- **D4 — `autopilot next`.** Recommendation: skip with the reason in Behaviour 4; the orchestrator (or
  the human) runs `taskrail workspace <ID>`, and T071's prepared-workspace handling then dispatches
  it. Alternative: dispatch it and have the lane run `taskrail workspace` from the orchestrator's
  checkout, which puts a write to the orchestrator's checkout in the lane's hands (the brief forbids
  touching it).
- **D5 — when `new` warns.** Recommendation: only when the checkout's current branch is the
  backlog's mainline, on stderr with exit 0 and `warning` in `--json`; a row added on a task branch
  is the documented follow-up flow and must stay quiet. Alternatives: warn only when
  `push_task_branch` is true as well (a weak proxy for "pull requests only"; this repository sets
  it); warn whenever the new row is absent from `base.onto` (always true for a new row, so noisy on
  task branches); or a config opt-out (`[git].warn_new_on_mainline`), not proposed until a
  repository that commits straight to its mainline asks.
- **D6 — the reservation.** Recommendation: `workspace` keeps the carried ID reserved, adding the
  reservation back when it was dropped. The ID was reserved by `new`, but any `reserve` run while the
  row sat in a scanned working tree dropped it (§6.3); after the move the row is only in an
  uncommitted worktree, which `used_ids` does not scan, so without this another `new` could reuse the
  ID before the row is committed. This keeps the original ID, which the manual recovery lost.
  Alternative: rely on the executor committing at once (a race while it has not).
- **D7 — refusing an `on-base` row.** Recommendation: narrow — `workspace` refuses exit 5 when the row
  is on its base, so the skill's workspace step keeps its git commands and T071's areas stay
  untouched. Alternative: general — create the workspace in every case and have the skill use the
  command for every task (larger skill and lane-brief change, overlapping T071).
- **D8 — skill text** (source, then `taskrail upgrade`). Recommendation: approve as written.
  - *Working a task*, step 3, after "if `base.onto` is null, stop and report `base.reason`.":
    ```markdown
    If `base.row` is `missing`, the task's row exists only in this checkout, and a workspace
    created from `base.onto` would not contain it: run `taskrail workspace <ID> --json` instead of
    the git commands below. It creates the branch and worktree from `base.onto`, moves the row
    there with its ID and removes it from this checkout; commit the row inside the workspace, and
    the removal here when `removed_from.uncommitted` is true and this checkout's branch needs it.
    ```
  - *Creating tasks*, after the `--workspace` paragraph's "then claim the task.":
    ```markdown
    Without `--workspace` the row is written in the current checkout; on a mainline checkout `new`
    warns, since a repository that merges through pull requests has no path for it there. Move such
    a row into its own workspace with `taskrail workspace <ID>`, which keeps its ID.
    ```
- **D9 — DESIGN.md text.** Recommendation: approve the changes listed under *Affected areas*, worded
  as Behaviour 1, 4, 5, 6 and D6 say; the new §7 table row:
  ```markdown
  | `taskrail workspace <ID> [--branch NAME]` | Create the branch and worktree of a task whose row is missing from its base (`base.row`), from that base, and move the row there with its ID, keeping it reserved (see *A row missing from its base*) |
  ```
  Alternative: the table row and *Dependencies and the base* only.
- **D10 — CHANGELOG.** Recommendation: one *Unreleased* bullet: "**A row missing from its base.**
  `show`, `list` and `next` report `base.row` (`on-base`, `on-branch` or `missing`), `autopilot next`
  skips a task whose row only the checkout has, `taskrail workspace <ID>` moves such a row with its
  ID into the task's own branch and worktree, and `new` without `--workspace` warns on a mainline
  checkout (T070)."
- **Risk — overlap with T071.** `dispatch.py` `next_lanes` (both lanes change the candidate loop),
  DESIGN.md §12.1's `autopilot next` cell (a single table line: a textual conflict is certain if both
  edit it), the `taskrail` skill's step 3 (T071 may reword "A task created with `taskrail new
  --workspace` already has its workspace"), `CHANGELOG.md` and `README.md` (append-only, known
  classes). If the orchestrator prefers, I leave the §12.1 cell to T071 with the exact clause to add.
- **Risk — cost.** `list` computes `base` for every task; the new read is one `git cat-file --batch`
  per distinct `onto` plus one ref listing, cached per command, in addition to the per-task git calls
  `base_dict` already makes.
- **Risk — a row committed on a non-base branch.** Carrying it leaves an uncommitted deletion on that
  branch, reported as `removed_from.uncommitted`; the command does not commit it.
