# T093 — Add a reading map to the top of DESIGN.md so a gate can read only what it needs

## Goal

Adopt option 1+ of the [T089 spike](../spikes/T089-decide-whether-to-split-design-md-by-top.md),
whose verdict the human accepted in full on 2026-09-18: **do not split `DESIGN.md`; add a reading
map at its top instead.** One table, one row per numbered section, saying what that section is
for, so a reader who wants one section finds it in thirteen rows instead of scanning 1844 lines.

What the map is **not** for: it does not reduce a per-gate read. E2 of the spike established that
the orchestrator reads `read_first` **once before the first dispatch**, not at every gate, so the
document's size is a per-run cost. The map serves a reader — human or agent — looking for a
section, at any time.

The task is the whole of the adoption, and it is deliberately the cheapest thing that answers the
need: **one table, inside the file being changed, one reversible diff.** A map that grew into a
map of separate documents would be the split the spike rejected, arriving by another route.

## Change set

### 1. `DESIGN.md` — insert the reading map (the only substantive change)

The file opens with a title (line 1), a status line (line 3), a three-line summary paragraph
(lines 5–7), then `## 1. Goals and non-goals` on line 9. There is no table of contents today.

The map goes **after the summary paragraph and before `## 1.`**, so the document still opens by
saying what it is, and only then says how to navigate it. Nothing above it moves; nothing below it
changes. The insertion is pure addition: about 20 lines, one hunk.

Proposed text, verbatim:

```markdown
**Reading map.** What each numbered section is for, so a reader after one thing finds it without
reading the rest. It is read when someone needs a section, not on a schedule: the orchestrator
reads this file once before a run's first dispatch (§12.6), not at every gate. When a numbered
section is added, add its row here.

| What you need | Section |
|---|---|
| What taskrail is for, and what it deliberately is not | §1 Goals and non-goals |
| The vocabulary: backlog, epic, task, kind, claim, stage, gate | §2 Concepts |
| How `TODO.md` is written: the epics table, task rows, columns, values | §3 File format |
| Every key of `.taskrail/config.toml` and its default | §4 Configuration |
| Kind descriptors, resolution order, the core kinds, conditional stages and routes — and the gates in §5.6 | §5 Kinds |
| Claims, ID allocation, and how a task gets a branch and a worktree in §6.4 | §6 Claims and IDs |
| Every command and flag, what it reads and what it writes — and the review hand-off in §7.1 | §7 CLI |
| The skills shipped with the CLI and the agent integration notes | §8 Skills |
| How the CLI is installed and what `init` writes into a repository | §9 Distribution |
| This repository's own directory tree | §10 Layout |
| The delivery phases and which tasks delivered them | §11 Phases |
| The autopilot: lanes, state, decision records, resources — and escalation in §12.6, merge follow-through in §12.8 | §12 Autopilot |
| What changes when tasks are worked on the checked-out branch instead of a branch each | §13 Current-branch workflow |
```

Shape of the table, and why:

- **Two columns, purpose on the left, `§N` plus the section's name on the right.** The spike's
  form is *what you need it for* → *§N*. Rows are in section order, so the eye scans the left
  column for a need and takes the number from the right. Keeping the section's name beside the
  number means the row carries the number, the name and the purpose without a third column.
- **Thirteen rows, one per numbered section.** No row for the front matter, none for anything
  outside the file.
- **No new heading.** The map is a bold lead-in and a table, not `## Reading map`. A heading there
  would make the file's first `##` an unnumbered one, ahead of §1, which is a structural change to
  a document whose whole point here is that nothing is restructured. (Decision 1 below.)
- **Five sub-sections named inside four rows** — §5.6, §6.4, §7.1, §12.6, §12.8, the sub-sections
  the citation corpus names by number. (Decision 2 below.)
- **`§N` bare, not a link.** 81% of the 1728 citations in this repository are bare `§N`; the map
  writes citations the way the corpus does, and a bare number cannot rot when a heading is
  reworded. (Decision 3 below.)

### 2. `docs/chores/T093-add-a-reading-map-to-the-top-of-design-m.md` — this artifact

### 3. `docs/chores/README.md` — one row for this artifact, appended to the table

### 4. `TODO.md` — T093's own row, through `taskrail done`, at the close

Nothing else. No `CLAUDE.md`, no skills, no code, no `.taskrail/config.toml`, no other task's row.

## Decisions needed

**1. The map has no heading of its own — a bold lead-in plus the table, sitting between the
summary paragraph and `## 1.`** Recommended as written above. The alternative is `## Reading map`
as an unnumbered `##` before §1: better anchoring and a line in any rendered outline, at the price
of making the file's first section heading an unnumbered one. Nothing in `tests/` or `src/` parses
`DESIGN.md`'s headings, so neither choice breaks anything; the recommendation is the conservative
one, because "the map adds; it does not reorganise" is the guard this task carries.

**2. Name the most-cited sub-sections inside their row's line (§5.6, §6.4, §7.1, §12.6, §12.8).**
Recommended. Reason: without them the map is barely more than the list of headings a reader can
already get from `grep '^## '`. The sub-sections are where the work actually is — §7 is 505 lines,
and a reader sent to "§7 CLI" still has 505 lines to scan, whereas §7.1 is the part gates want; the
same for §12 at 464 lines and §12.6. These five are exactly the ones the citation corpus names by
number, so they are chosen by measurement, not by taste. Against: four of the thirteen rows are
longer than the rest, and each named sub-section is one more thing that could be renumbered later
(nothing in this task renumbers anything, and no past task has renumbered a sub-section). The
alternative is thirteen uniform rows naming top-level sections only.

**3. Bare `§N` rather than Markdown anchor links.** Recommended: matches the house citation style
(1390 of 1728 citations are bare), and a link built from a heading's slug breaks silently if the
heading is ever reworded, while a number does not. The alternative — `[§7 CLI](#7-cli)` — is
clickable in a rendered view and a dead link in a plain-text read.

**4. Drift: one sentence in the map's own text, no test.** Recommended. The map has **no per-task
trigger**: nothing in the skills or the CLI makes anyone update it when a section is added, which
is why the spike's E7 predicted it will drift — E7 also showed that this repository's five
hand-kept indexes have zero drift precisely *because* a per-task skill step writes each of their
rows, and that reason does not transfer here. The cheapest honest guard is the last sentence of the
lead-in, "When a numbered section is added, add its row here", inside the file being changed, so
the diff that adds a section shows the omission to its reviewer. The alternatives:

- **A test** asserting that every `## N.` heading in `DESIGN.md` has a row in the map. It would be
  a repository-level test of this repository's own documents, which T060 rejected ("items must stay
  self-contained"); `DESIGN.md` is not shipped and is invisible to the shipped skills (E3), so such
  a test would guard a private document from the package's test suite. E8 adds that a test can hold
  the links but not the judgement of *what a section is for*, which is the part that decays: a row
  can exist and be wrong, and the test would pass.
- **Nothing at all** — the diff is small and reversible, and a stale row costs a reader one wrong
  jump. Defensible, but a sentence costs nothing.

**Answered at the `scope` gate of run `20260918-1`:** all four as recommended, and the table
accepted as quoted, to be inserted unchanged. Two points the answer asked to keep: the lead-in's
sentence that this file is read once before a run's first dispatch and not at every gate — T089's
most valuable finding, now living where a future reader meets it — and the line-shift note under
*Verification*, so a reviewer who sees `DESIGN.md:<line>` citations in old artifacts move finds the
reason without asking. The decision record is
[`docs/autopilot/decisions/T093-add-a-reading-map-to-the-top-of-design-m.md`](../autopilot/decisions/T093-add-a-reading-map-to-the-top-of-design-m.md).

## Out of scope

- **Splitting `DESIGN.md`, in whole or in part** — refused by the accepted verdict.
- **Renumbering any section or sub-section**, which would break 1728 citations across 153 files.
- **Moving any citation**, adding any new file, or changing `[autopilot].read_first`.
- **Changing the shipped skills' wording** about what the orchestrator reads (that would ship one
  repository's document structure to every installation).
- **Rewriting the bare-`§N` citation style** — the spike says that would need its own spike.
- **`CHANGELOG.md`**, which records user-facing changes; `DESIGN.md` is this repository's internal
  design document and ships to nobody (E3), so no consumer's behaviour changes. Confirmed at the
  `scope` gate: the same test excused T090 and required an entry from T091.
- **Correcting anything else noticed in `DESIGN.md`** while editing its top. If something needs
  changing, it becomes a follow-up task.

## Verification

Run in this task's worktree, on branch `T093-add-a-reading-map-to-the-top-of-design-m`, after
inserting the map.

**1. The change is 21 lines of pure addition in one file.**

```
$ git diff --stat
 DESIGN.md | 21 +++++++++++++++++++++
 1 file changed, 21 insertions(+)

$ git diff -U0 DESIGN.md | head -6
diff --git a/DESIGN.md b/DESIGN.md
index 366b4c3..3698266 100644
--- a/DESIGN.md
+++ b/DESIGN.md
@@ -8,0 +9,21 @@ generalized, and decoupled from GitHub Spec Kit.
+**Reading map.** What each numbered section is for, so a reader after one thing finds it without

$ git diff -U0 DESIGN.md | grep -c '^-[^-]'
0
```

One hunk, `@@ -8,0 +9,21 @@` — inserted after the summary paragraph and before `## 1.`, with no
removed line anywhere in the diff.

**2. Nothing was renumbered; every section still has exactly one row, in order.**

```
$ grep -c '^## [0-9]\+\.' DESIGN.md
13
$ wc -l DESIGN.md
1865 DESIGN.md

$ grep -oE '\| §[0-9]+ [^|]+ \|$' DESIGN.md | sed -E 's/^\| §([0-9]+) (.*) \|$/\1|\2/' > map.txt
$ grep -E '^## [0-9]+\.' DESIGN.md | sed -E 's/^## ([0-9]+)\. (.*)$/\1|\2/' \
    | sed 's/ — `.taskrail\/config.toml`//; s/ (implemented)//' > heads.txt
$ diff map.txt heads.txt && echo MATCH
MATCH          # 13 rows, 13 headings, same numbers, same names, same order
```

(The two `sed` substitutions only drop the parts of two headings the map's cells deliberately omit:
§4's `— .taskrail/config.toml` and the `(implemented)` status tags on §12 and §13. `map.txt` and
`heads.txt` were written to the scratchpad, not to the repository.)

Each sub-section the map names by number exists exactly once:

```
$ for s in 5.6 6.4 7.1 12.6 12.8; do grep -c "^### ${s} " DESIGN.md; done
1 1 1 1 1
```

**3. The checks pass.**

```
$ .taskrail/bin/taskrail checks T093 --stage implement
== test: uv run pytest -q
[…]
1183 passed in 140.02s (0:02:20)
== lint: not configured
passed test
not configured lint
T093 in …/.worktrees/T093-add-a-reading-map-to-the-top-of-design-m: passed
```

`lint` is not configured in this repository, and `checks` reports it as such rather than failing.

The first run of the suite ended `1 failed, 1182 passed in 150.75s`, on
`tests/test_autopilot_notify.py::test_a_notify_command_past_the_timeout_is_killed_with_its_children`
— a timing test that waits up to 5 s for a killed command's `sleep 60 &` child to disappear
(`AssertionError: child`). It is unrelated to this change, which adds Markdown to a document no
code reads (E3), and it is a load-sensitive test: three lanes of run `20260918-1` were running full
suites on this machine at the time. It passed twice on its own and then in the full suite quoted
above, which is the recorded result.

**4. The backlog still validates.**

```
$ .taskrail/bin/taskrail validate
87 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
```

One known, accepted side effect: the map shifts every line below it, so `DESIGN.md:<line>`
references in *historical* artifacts (T076, T077, T078, T085 cite line 3, 112, 1179, 1730) point
one map-height lower. Those artifacts are the record of what was decided and are never rewritten;
they had already drifted before this task (T085's "line 112" is line 109 today), and future release
chores locate those lines by content, not by number. No code, test or configuration file cites a
line number in `DESIGN.md`.
