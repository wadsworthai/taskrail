# T092 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T092-correct-t088-s-row-with-the-measured-cli.md` at commit 6eeb484, the diff
against the base (the artifact and one index row, `TODO.md` untouched as `scope` requires), and the
lane's two load-bearing claims, both checked by the orchestrator rather than taken from the report:
the merged artifact `docs/spikes/T088-measure-the-cli-and-configuration-surfac.md` names T092 by ID
at lines 45, 685 and 719-720 as the place its row is corrected, and `cli.py:914` is the guard that
makes `edit` exit 5 on a row that is not pending.

The orchestrator had put a third option to the lane — discard the task, since its stated purpose
("before T088 is worked") can no longer be served — and expected that answer. The lane objected with
evidence, at its first gate, which is what the rule merged in T090 asks of it, and the objection is
accepted.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | What is this task still for? | correct the row from T088's artifact · correct it minimally · discard it | **correct the row from T088's artifact, with the closing method clause, as recommended** | Discarding was the orchestrator's own suggestion and the lane overturned it: T088's merged, public write-up names T092 as where the row is corrected, so discarding would strand a forward reference on the mainline, and the row is what a backlog reader meets before the artifact. The method clause stays because the figures are method-sensitive — two honest counts of the same tree gave 70 and 72 — so a figure without its method is not re-checkable. |
| 2 | Write this row's own figures, or T088's? | T088's · this row's ("about 70", "42 documented keys") | **T088's** | This row's figures are less precise than the merged measurement: its "9" counts first-level tables, T088's 46 counts settable names, and the 4-key difference is the two repeatable tables, not a disagreement. Writing them would swap one imprecise sentence for another. |
| 3 | Use `--force` to edit a closed row? | yes, on the description cell only · no | **yes, on T088's description cell only** | `edit` exits 5 on a row that is not pending (`cli.py:914`); `--force` lifts that guard and changes no status. The lane reported it as a decision rather than using it silently, which is what the `taskrail` skill requires. The human approved this correction when accepting T088's follow-ups. |
| 4 | Correct T092's own row too? | leave it · edit it as well | **leave it** | The distinction is what kind of wrongness each row carries. T088's row states *facts* that are false and that a reader will act on. T092's row states an *intention* that has expired ("before T088 is worked"), which is not false, only overtaken — and it is the record of what was planned, which this task's artifact explains was done differently. |

Instructions given with the answers: edit the description cell only, through the CLI, and record
under *Verification* the real output of `show T088 --json`, the one-row `git diff` of `TODO.md`,
`taskrail validate` and `taskrail checks T092`.

## implement gate

Reviewed: the `TODO.md` diff read by commit range in the lane's worktree — one line, one cell, with
the status, ID, kind, points, dependency and title byte-identical on both sides and no other row
touched; the new text against what was approved at `scope`, which it matches verbatim; and
`taskrail checks T092 --stage implement` and `taskrail validate` re-run by the orchestrator in that
worktree (`test` passed, `lint` not configured, 87 tasks and 0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the applied edit what was approved? | accept · amend | **accepted** | One `edit --force` on the description cell, through the CLI, with the approved text verbatim and the method clause intact. `--force` changed no status: `show T088` still reports `done`. |
| 2 | Anything to add at the `docs` stage? | nothing · more | **nothing** | The change is one backlog cell and its explanation is the artifact, already committed. `DESIGN.md`'s configuration documentation defects belong to T098, which T088 opened for them. |

## rebase after T091 merged

T091 was squash-merged into `main` as 5025641 and proved by content with `autopilot merged`. This
branch was rebased at hand-off, while the lane was stopped at the `close` gate: `git rebase
origin/main`. Three conflicts, all of the known classes:

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `docs/chores/README.md` and `docs/autopilot/decisions/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, appended index rows. |
| 2 | `TODO.md`: rows on both sides, including T091's status cell | unite by ID, `✅` wins · keep both lines | **unite by ID: T091 `✅` from the mainline, T092's own rows from this branch** | Known class 1. The rows are united **by ID**, not concatenated — a keep-both resolution duplicates rows, as it did once earlier in this run on T091's branch, where `validate` caught it at once. |

After the rebase the correction this task exists for is intact: T088's row on the branch reads the
measured figures. Five commits ahead of `origin/main`, `git diff --check` clean, `taskrail checks
T092` passed, `taskrail validate` reports 87 tasks and 0 errors.

## Conflict handling agreed for all lanes

Run 20260918-1, extended by the human to T093-T098.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T092 touches `TODO.md` through the CLI and its own artifact; T093 edits `DESIGN.md` and its own artifact** | The two lanes running in parallel share no file of substance. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes only: backlog rows (class 1) and appended index rows (class 2)** | Both are resolved by the orchestrator at hand-off. This task's edit changes a cell of a row that already exists on the mainline rather than adding one, so a rebase applies it cleanly unless another lane edits the same cell, which none may. |
| 3 | May a lane edit `CLAUDE.md` or the shipped skills? | allow · forbid | **forbidden for both lanes** | T090 and T091 adopted those two areas and are merged or in review; neither open task has business there. |
