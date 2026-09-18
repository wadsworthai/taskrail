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

## implement gate

Reviewed: commit `9756424` and the diff `073eaea..HEAD` — `TODO.md` down to 15 lines with 148
deletions and nothing added, the new 157-line `docs/archive.md`, seven lines of `CLAUDE.md` and the
artifact; the `git diff --stat` showing deletions only, so rows moved rather than being rewritten;
the exhaustive byte-comparison of all 108 archived rows against `git show HEAD:TODO.md`; the ID
probes; and `taskrail checks T114 --stage implement` (1,256 passed). The orchestrator re-counted the
two files and read the `CLAUDE.md` bullet in place.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The implement stage as committed | **approve** | **approve** | Everything the scope gate settled was applied, and the verification is stronger than what was asked for: 108 of 108 rows compared rather than sampled, and a diff that is deletions only. |
| 2 | The `CLAUDE.md` wording, the one edit a future lane reads as instruction | **keep as written** · reword | **keep** | It answers the question a reader will actually have — *where did the history go* — with the command that finds it, and it closes the door the archive must keep shut: nothing comes back out, and work that must return is a new task. That last sentence is the one that prevents a future lane from inventing an unarchive. |
| 3 | The `T122` probe result | **not a defect; no follow-up** | **not a defect** | Probing twice in the same scratch repository reserved an ID the first time, and `ids.reserve`'s pending-reservation ledger under `.git/taskrail/reserved/` is not reverted by `git checkout -- TODO.md`. Correct race-free behaviour. Recording the trap in the artifact is worth more than a task would be — it is what the next person to run this probe needs. |

The **negative control** in the ID check is the part worth keeping: with `docs/archive.md` absent
from both the working tree and history, the next ID is `T115` — a live reissue of an archived, done
task. With the archive present in either place it is `T121`. That is what turns "the counter looks
right" into "the archive scan is what keeps it right", on this repository's real data, and it is the
guarantee T107 built `ids.used_ids`' revision scan for.

## close

Reviewed: the whole diff against the merge base — `TODO.md` at 15 lines with one row, the new
157-line `docs/archive.md`, seven lines of `CLAUDE.md`, the artifact and its index row; the
`done` commit alone in `TODO.md`; `taskrail validate` (1 task, 0 errors) and `taskrail claims`
(none).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `docs` stage carried rather than stopped at | **accept** | **accept** | Its documentation was inside the approved change set and was applied at `implement`; nothing further needed writing and no follow-up was opened, so the conditional gate had nothing to stop for. |
| 2 | Pull request type and scope | **`chore` / `backlog`** · `chore` / `repo` | **`chore` / `backlog`** | `backlog` is the area CLAUDE.md's *Merging* section names for this work, and the change is this repository's own backlog and nothing else. |

`taskrail done T114` returned `"warning": null` — T119's new key, computed by T119's new code, on a
row written from the task's own branch. The wrong-checkout case was ruled out at the exact point it
would have bitten, by a guard merged four hours earlier in the same session.
