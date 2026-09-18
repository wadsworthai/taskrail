# T090 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T090-record-the-scope-reach-and-refusal-rules.md` at commit 0f5d0c7, the
diff range `origin/main..HEAD` (2 files, 118 insertions — the artifact and one index row, with
`CLAUDE.md` untouched as the `scope` stage requires), `taskrail checks T090 --stage scope`
(`no checks` … `passed`), and the section as it stands at base 15823fc, which matches what the lane
quoted.

`CLAUDE.md` is named in `[autopilot].read_first` but is deliberately not a `governing` path in this
repository, so this edit does not escalate by itself: the orchestrator decides it at the gate and
the human reviews it in the pull request, exactly as the *Backlog* section of `CLAUDE.md` says.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Imperative voice, or "an executor"? | imperative · third person | **imperative, as recommended** | It is the voice of the rest of the file ("apply them", "say so", "State such a rule in the skill's prose too"), and switching voice mid-section would read as a different rule. The lane brief's third person was description, not prescribed wording. |
| 2 | Two paragraphs, or one? | two · one | **two, as recommended** | The objection rule is the one an executor must find at a gate; buried as the third clause of a single block it is easy to miss. Six added lines is a proportionate diff for the three rules being adopted. |
| 3 | Say anything about reach — where an executor reads the principles? | say nothing · add a pointer sentence | **say nothing** | T091 adds the generic pointer in the core skill, in the same run. A sentence here would duplicate it, date if T091's wording changes, and describe an area this lane must not touch. |
| 4 | Is the proposed replacement text accepted as written? | accept · amend | **accepted as written** | It lands all three adopted rules: T087's own prospective sentence; "the task's first gate" naming `plan`, `scope`, `diagnose` and `frame`, which fixes a rule that bound one kind in four; and "object rather than refuse … then build what the answer says" with the ban on silent substitution, while keeping today's ban on building around the objection. Nothing stated today is lost. |

Instructions given with the answers: apply exactly that text at `implement`, verify that
`grep -n "plan gate" CLAUDE.md` returns nothing, run `taskrail checks T090 --stage implement` (the
kind wires `test` to that stage, so the suite runs) and record its real output in the artifact.

Noted for the `implement` gate, needing no change to the text: under a stage whose gate is
`"decisions"` (DESIGN.md §5.6) an executor does not stop at the stage's end, but an objection on a
principle is a decision, so it still stops as soon as it appears. The wording "at the task's first
gate" therefore holds under every gate value this repository uses.

## implement gate

Reviewed: the `CLAUDE.md` diff read by commit range in the lane's worktree, not from the report —
one hunk, 9 insertions and 3 deletions, replacing the section's opening paragraph and stopping
before the `KISS` bullet, with the five bullets untouched; `grep -c "plan gate" CLAUDE.md` returns
0; and `taskrail checks T090 --stage implement` re-run by the orchestrator in that worktree: `test`
passed with 1183 tests in 136.57s, `lint` not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the applied text what was approved? | accept · amend | **accepted; applied verbatim** | The diff is the text approved at the `scope` gate, with nothing added and nothing else touched. |
| 2 | Does this change need a `CHANGELOG.md` bullet? | yes · no | **no** | `CHANGELOG.md` records user-facing changes, and its users are the repositories that install taskrail. `CLAUDE.md` is this repository's own instruction file: it ships to nobody and no consumer's behaviour changes. T091, whose line does ship in the core skill, gets the entry instead. |
| 3 | What does the suite prove here? | that the rules work · that nothing broke | **that nothing broke** | No test reads `CLAUDE.md`. The artifact says exactly that rather than claiming the checks verify the rules, which is the right way to record it. |

The lane's note about `decisions` gates went into the artifact's rationale and not into `CLAUDE.md`,
as instructed: an objection on a principle is a decision in §5.6's sense, so it stops mid-stage
under a `"decisions"` gate, and the sentence needs no clause about gate values.

## Conflict handling agreed for all lanes

Run 20260918-1. T090 and T091 run in parallel and adopt T087's verdict in separate areas.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T090 edits `CLAUDE.md` only; T091 edits `src/taskrail/skills/taskrail/SKILL.md` and what `taskrail upgrade` rewrites** | The two halves of T087's verdict were deliberately opened as separate tasks: one is this repository's own text, the other ships to every consumer. Neither lane enters the other's area. |
| 2 | What do they share? | nothing · the backlog file | **`TODO.md` only** | Each closes its own row; a backlog row conflict is known class 1 and the orchestrator resolves it at hand-off. Each also appends one row to `docs/chores/README.md`, known class 2. |
| 3 | May either touch `DESIGN.md`? | allow · forbid | **forbidden** | T089 decided its structure stays as it is, and T093 will add a reading map to it. |
