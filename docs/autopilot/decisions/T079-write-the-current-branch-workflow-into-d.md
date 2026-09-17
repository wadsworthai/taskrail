# T079 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the scope artifact `docs/chores/T079-write-the-current-branch-workflow-into-d.md` (commit
`9dce296`, the only change in `origin/main..HEAD`, clean worktree); its grounding checked against
the code (`kinds.GATES` is `always`, `conditional`, `none`; `_freeze_branch` warns off the template
branch; `autopilot start` and `extend` refuse with exit 5 on `[autopilot].enabled`); `DESIGN.md`
ends at §12, so a new §13 renumbers nothing. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where the design goes | new §13 plus pointers · straight into §4–§7 | **as recommended** | Same pattern as T028 with §12; keeps §4–§7 describing what the CLI does now. |
| 2 | Branch setting's name and values | `task_branch = "task" \| "current"` · `"per-task"`/`"current"` · `workflow = …` | **as recommended** | Keeps the key the need proposed; repository-wide because the workspace belongs to the checkout. |
| 3 | `"current"` with `worktree` | require `worktree = "never"` · imply it | **as recommended** | Explicit, and no key silently overrides another. |
| 4 | `show`, `list`, `next` under `"current"` | checked-out branch, `base`/`worktree` null, no `done-branch` · claim's branch while claimed | **as recommended** | Matches the need (`show` reports the current branch) and removes stacking, which has no meaning without task branches. |
| 5 | Commands that assume a task branch | `new --workspace`, `workspace`, `branch` exit 5 · `branch` a no-op | **as recommended** | A refusal exposes a skill following task-branch steps by mistake; exit 5 is the repository's refusal code. |
| 6 | `claim_remote` and `branch_record_remote` under `"current"` | work unchanged, records push nothing · config error | **as recommended** | `claim_remote` is an explicit opt-in to push a ref outside `refs/heads`; no branch is ever pushed. |
| 7 | Commit policy name and location | `[git] commit` plus top-level kind `commit` · config only · `[kinds]` table | **as recommended** | Covers "or per kind" from the need through descriptors and overrides, where kind data already lives. §13 must state plainly that the kind's top-level `commit` is a policy string and a stage's `commit` stays a boolean. |
| 8 | What `on-done` changes in the output | effective stage `commit`, `kind_descriptor.commit`/`commit_source`, `close`, `done`'s `commit` · declared values combined by the skill | **as recommended** | The CLI computes and the skill judges (CLAUDE.md: plain contracts for the CLI). |
| 9 | Meaning of `gate = "decisions"` | per-stage value, stop mid-stage for decisions only · also a `[kinds]` gate key | **as recommended** | Matches the need; overrides already carry per-stage gates, so no second mechanism. |
| 10 | Decisions gates in the autopilot | allowed, `--gate <stage>` · `start` refuses | **as recommended** | Nothing in §12 depends on stage-end stops; the close review still reads the full diff. |
| 11 | Autopilot commands refusing `"current"` | `start`, `extend`, `next` · `start` only | **as recommended** | `extend` and `next` can dispatch too; inspection and closing of older runs stay possible. |
| 12 | Autopilot with `commit = "on-done"` | refuse in `start`, `extend`, `next` · allow | **as recommended** | §12.3 restarts lanes from their branch commits and gates review commit ranges; built in T081. |
| 13 | `review` under `"current"` | report only, `--publish` exit 5 · exit 2 | **as recommended** | The invocation is valid and the configuration refuses it, which is what exit 5 means; asking before any push stays with the skill (T084). |
| 14 | Backlog rows | edit T080, T081, T083 descriptions · leave them | **as recommended** | Each row must name what its task delivers; use `taskrail edit` only, and keep each description to one line. |
| 15 | CHANGELOG and README | neither · a changelog bullet | **as recommended** | Planned design changes no behaviour; T028 added none; T084 writes the README. |

§13 opens with a status line saying it is planned and names T080–T084. Keep the need described in
general terms only (publishing constraint).

## implement gate

Reviewed: `git diff origin/main..b7f8e61` in the lane's worktree — §13 read in full, every pointer
hunk in §4, §5.1, §5.3, §6.4, the §7 table, §7.1, §11 and §12.2 (only pointer text added to existing
rows and sentences, no heading changed), the T080, T081 and T083 row edits, and the chores index
row; the checks re-run with `taskrail checks T079 --stage implement` (test passed, lint not
configured) and `taskrail validate` (no errors or warnings). No code changed, so there is no runtime
to exercise.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | T082's row names `kind show`, which does not exist | leave it for T082's plan gate · edit it now | **edit it now** | The row is the contract T082's lane starts from; fixing it here costs one `taskrail edit` and keeps §13.8 and the row consistent. |
| 2 | (orchestrator) §13.8 leaves `close.review` to "whichever of T080 and T081 lands second" | assign `close.review` to T083 · leave it | **assign it to T083** | The human runs T080, T081 and T082 in parallel and T083 after all three merge, so T083 is the one task that sees both settings; T081 adds `close` with `commit` only. Update §13.3's table note, §13.8 and the T081 and T083 rows to match. |
| 3 | The artifact file reported as changed on disk while appending | keep as committed · investigate | **keep as committed** | The committed content is what the lane wrote; the orchestrator did not edit the artifact. |

## close gate

Reviewed: `git diff 2f32ef3..50de538` (the §13.3 and §13.8 fixes, the T081, T082 and T083 row edits,
the `CLAUDE.md` layout line), `taskrail done` committed on its own in `50de538` (only T079's status
cell changed there), `review --json` (rebase not needed onto `origin/main`), no upstream on the
branch, clean worktree, and `taskrail validate` with no errors or warnings.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | T083 builds `close.review` inside T081's `close`, but its row depends only on T080 | depend on T080, T081 · add T082 too · leave it | **depend on T080, T081** | T083 needs both; it does not need T082, whose order the run keeps. Edit the row with `taskrail edit T083 --depends-on T080,T081` and §13.8's cell to match, on this branch before hand-off. |
