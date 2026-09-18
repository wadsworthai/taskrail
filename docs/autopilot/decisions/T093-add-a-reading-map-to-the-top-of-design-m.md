# T093 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T093-add-a-reading-map-to-the-top-of-design-m.md` at commit 873bd48, the diff
against the base (the artifact and one index row only — `DESIGN.md` untouched, as `scope`
requires), and the file's front matter and 13 numbered headings as they stand at base b61bd41.

This task is the whole adoption of T089, whose verdict the human accepted on 2026-09-18: do not
split `DESIGN.md`, add a reading map at its top, leave `read_first` alone. The guard the spike wrote
into its own outcome — that a map which grew into an index of separate documents would be the split
it rejected, arriving by another route — held: the lane proposes one table, in one file, in one
reversible diff, and said so.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | A heading of its own, or a bold lead-in plus the table? | bold lead-in, between the summary and §1 · an unnumbered `## Reading map` | **bold lead-in, as recommended** | The conservative form, and this task's guard is that the map adds without reorganising. An unnumbered heading ahead of §1 would make the file's first heading a section that is not a section, for an anchor nothing needs: the lane verified that nothing in `src/` or `tests/` parses these headings. |
| 2 | Name the five most-cited sub-sections inside their rows? | yes: §5.6, §6.4, §7.1, §12.6, §12.8 · thirteen uniform rows | **yes, as recommended** | Without them the map barely improves on `grep '^## '`. §7 is 505 lines and §12 is 464, so "see §7" still leaves a reader 505 lines to scan, while §7.1 is the part gates cite. The five are chosen by measurement — they are the sub-sections the citation corpus names by number — not by taste. |
| 3 | Bare `§N`, or Markdown anchor links? | bare · anchors | **bare, as recommended** | 1390 of this repository's 1728 citations are bare `§N`, so the map writes citations the way the corpus does; a number does not rot when a heading is reworded, and an anchor link is a dead link in plain text, which is how most readers and every agent meet this file. |
| 4 | What guards the map against drift? | one sentence in the map's own text · a test · nothing | **the sentence, and nothing more, as recommended** | T089's E7 measured why this repository's five hand-kept indexes have no drift — a per-task skill step writes each of their rows — and that trigger does not exist for a map touched once or twice a year. A sentence inside the file means the diff that adds a section shows the omission to its reviewer. A test would assert the links and not the judgement of *what a section is for*, so a row could be present and wrong and still pass, and it would be a repository-level test of a document that ships to nobody. |

Instructions given with the answers: insert the table as quoted, verify the diff is one hunk with no
`-` line and that all 13 numbered headings still match exactly one row each, and record the real
output under *Verification*.

The accepted side effect is recorded as the lane wrote it: the insertion shifts every line below it,
so `DESIGN.md:<line>` references in the historical artifacts T076, T077, T078 and T085 point one
map-height lower. Those artifacts are never rewritten and had already drifted; no code, test or
configuration file cites a line number in `DESIGN.md`.

## implement gate

Reviewed: the `DESIGN.md` diff read by commit range in the lane's worktree — one hunk at
`@@ -6,6 +6,27 @@`, 21 insertions and **0 removed lines**, the map sitting after the summary and
before `## 1.`; the file still carries its 13 numbered headings; and `taskrail checks T093 --stage
implement` re-run by the orchestrator in that worktree (`test` passed, `lint` not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the inserted table what was approved? | accept · amend | **accepted; inserted character for character** | The diff adds only the approved block, and the lane's heading-to-row check (13 rows against 13 headings, and each named sub-section present exactly once) was reproduced by the orchestrator's own count. |
| 2 | The `docs` stage | run it as a no-op · stop at its gate | **run it as a no-op, do not stop** | The change is documentation, `CLAUDE.md`'s Layout line for `DESIGN.md` stays accurate, no skill or README mentions the map, and `CHANGELOG.md` is ruled out for the reason recorded at the `scope` gate. |
| 3 | The flaky test the lane reported | open a task from this lane · leave it to the orchestrator | **leave it to the orchestrator; the lane opens nothing** | `tests/test_autopilot_notify.py::test_a_notify_command_past_the_timeout_is_killed_with_its_children` failed once under load — three lanes of this run were executing full suites on one machine — and passed three times afterwards. It is a wall-clock test and cannot be affected by adding Markdown to a document no code reads (T089 E3). It is outside this task's touch map, and reporting it rather than acting on it was the right call. The orchestrator carries it to the human. |

## rebase after T091, T092 and T099 merged

`review T093 --json` reported `rebase.needed: true`. The orchestrator rebased at hand-off, while the
lane was stopped at the `close` gate: `git rebase origin/main`. Three conflicts, all of the known
classes, resolved without the human:

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `docs/chores/README.md` and `docs/autopilot/decisions/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, appended index rows: T091's and T092's rows came from the mainline, T093's from this branch. |
| 2 | `TODO.md`: rows and status cells on both sides | unite by ID, a closed cell wins · keep both lines | **unite by ID** | Known class 1. T091 and T092 arrived `✅` from the mainline, T093 `✅` from this branch, and T099's row — added on the mainline while this lane worked — is kept. No side carries a `Reopens:` commit the other lacks. |

Verified after the rebase: the reading map is intact and the branch still removes no line of
`DESIGN.md`; T099's row survives; `git diff --check` clean; `taskrail checks T093` passed;
`taskrail validate` reports 88 tasks and 0 errors.

## Conflict handling agreed for all lanes

Run 20260918-1, extended by the human to T093-T098.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T093 edits `DESIGN.md` and its own artifact; T092 touches `TODO.md` through the CLI and its own artifact** | The two lanes running in parallel share no file of substance. `DESIGN.md` is this lane's alone; no other open task of the run may touch it. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes only: backlog rows (class 1) and appended index rows (class 2)** | Resolved by the orchestrator at hand-off. |
| 3 | Does this change need a `CHANGELOG.md` entry? | yes · no | **no** | `DESIGN.md` is internal to this repository and ships to nobody — T089's E3 measured that the shipped skills do not even cite it — so no consumer's behaviour changes. The same reasoning excused T090 and required an entry from T091. |
