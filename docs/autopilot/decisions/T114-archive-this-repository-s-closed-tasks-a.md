# T114 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T114-archive-this-repository-s-closed-tasks-a.md` and its commit
`d9a4b14` (artifact and index row alone, the backlog untouched); the dry run and its JSON; and the
full write-preview the lane ran against a scratch copy **outside** the worktree, with `validate`,
the re-run dry run and the resulting document's structure.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | Correct T114's own description to the real figures | **yes** · leave it as the intent it was written with · drop the numbers | **yes** | After the archive, T114's row is the whole of `TODO.md`, so its description is the only sentence a reader of the backlog sees — and it would say 84 rows, one epic and nine held back, wrong in all three. The artifact keeps the original figures in context either way. |
| D2 | The archive's path | **the default, `docs/archive.md`** · `docs/backlog/archive.md` · `docs/archive/2026.md` | **the default** | It reads as the document *about the backlog* beside the documents about tasks, and it gives §7.6's documented default its first real exercise. A directory for one file is machinery; a dated path pre-commits to a policy T107 deliberately left out of scope. |
| D3 | Order at the close | **archive in `implement`, `done` at the close, and no second archive run** · close first | **as recommended** | The lane worked out the consequence before acting, which is what this question was for: closing first would archive 109 rows and **six** epics, because with no row staying behind E06 archives whole — leaving `TODO.md` with an empty `## Epics` table and no sections, so the next `taskrail new --epic E06` would fail and a human would have to re-add an unfinished epic. Not running `archive` again after `done` is part of the decision, not an omission. |
| D4 | Documentation | **one `CLAUDE.md` pointer, in *Backlog* and the *Layout* block; nothing else** · a `CHANGELOG.md` bullet · `README.md`/`DESIGN.md` | **the `CLAUDE.md` line** | It answers the lane's own third finding: fifteen lines of `TODO.md` give no sign that 108 tasks and five epics of history exist, and `docs/archive.md` is named in no index or instruction file. The changelog is taskrail's user-facing history and `archive` is already in it from T107; running it here changes nothing for an installing repository. `CLAUDE.md` is `read_first` and not `governing`, so this is the orchestrator's call and the human sees it in the pull request. |
| D5 | The change set and boundary as scoped | **approved** | **approved** | `TODO.md` and `docs/archive.md` through the command, the `CLAUDE.md` pointer, the artifact and its index row. |

Given with the answers: the task row's figures were T107's, measured before this run closed twenty
more tasks, and the lane was asked not to repeat them as current. It did the opposite of repeating
them — it tabled old against new and explained why the nine held-back rows are now zero: the rule
holds a closed row only while a row *staying behind* depends on it, and T003, T109 and T110 have
since closed and archive themselves. The one-line output is correct, not truncated.
