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

## Conflict handling agreed for all lanes

Run 20260918-1, extended by the human to T093-T098.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T093 edits `DESIGN.md` and its own artifact; T092 touches `TODO.md` through the CLI and its own artifact** | The two lanes running in parallel share no file of substance. `DESIGN.md` is this lane's alone; no other open task of the run may touch it. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes only: backlog rows (class 1) and appended index rows (class 2)** | Resolved by the orchestrator at hand-off. |
| 3 | Does this change need a `CHANGELOG.md` entry? | yes · no | **no** | `DESIGN.md` is internal to this repository and ships to nobody — T089's E3 measured that the shipped skills do not even cite it — so no consumer's behaviour changes. The same reasoning excused T090 and required an entry from T091. |
