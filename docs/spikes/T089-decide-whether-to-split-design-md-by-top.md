# T089 — Decide whether to split DESIGN.md by topic for what the orchestrator reads first

**Verdict** — **do not split `DESIGN.md`.** The measurements contradict two of the premises the
task row rests on, and the option the row proposes is the most expensive one on the table. The
orchestrator reads `read_first` **once before the first dispatch**, not at every gate (E2), so the
1844 lines are a per-run cost, not a per-gate one; and §7 and §12, the two sections a split would
remove first, are the two that past gate answers cite most (E4). A split would rewrite 149
cross-references inside the document and about 80 in maintained files, and strand 1400 citations
in 116 historical documents that are never rewritten (E5), in exchange for a saving that is
negative at this repository's run size (E6). Adopt instead the cheapest thing that answers the
real need — a **reading map at the top of `DESIGN.md`**, one row per section saying what it is for
— opened as **T093**. Keep `read_first = ["CLAUDE.md", "DESIGN.md"]` unchanged.

## Question

`.taskrail/config.toml` sets `[autopilot].read_first = ["CLAUDE.md", "DESIGN.md"]`. `DESIGN.md` is
1844 lines, and §7 (CLI) and §12 (autopilot) are 969 of them. Should the file be split into topic
documents reached through one-line pointers, or left as it is?

Three sub-questions: what does a gate actually need, measured rather than assumed; what would a
split cost; and which option wins on the measured difference.

Per T087's accepted verdict, the design principles are **prospective**: KISS and YAGNI judge the
change this spike would propose, not the merit of the file as it stands. The re-examination is
legitimate because this task asks for it, and the cross-reference cost is a cost of the new
structure weighed against a measured benefit — not evidence that the current file is wrong.

## Evidence

All commands were run in this task's worktree, on branch
`T089-decide-whether-to-split-design-md-by-top`, rebased onto `origin/main` = `4a956c4` (T087
squash-merged), at commit `8d3b00b`. Scripts are reproduced under *How to reproduce* and were kept
in the session scratchpad, outside the repository.

### E1. The file, section by section

```
$ wc -lwc DESIGN.md CLAUDE.md README.md
  1844  22362 142172 DESIGN.md
   121    996   6667 CLAUDE.md
   240   1945  12860 README.md

$ awk '/^## /{if(prev){print prev": "NR-start} prev=$0; start=NR} END{print prev": "NR-start+1}' DESIGN.md
## 1. Goals and non-goals: 24          ## 8. Skills: 63
## 2. Concepts: 13                     ## 9. Distribution: 51
## 3. File format: 63 (incl. the       ## 10. Layout: 18
     worked TODO.md example, whose     ## 11. Phases: 13
     `## Epics` / `## E01` headings     ## 12. Autopilot: 464
     awk counts separately)            ## 13. Current-branch workflow: 126
## 4. Configuration: 96
## 5. Kinds: 234                       numbered sections total: 1836
## 6. Claims and IDs: 166              front matter before §1: 8
## 7. CLI: 505
```

§7 and §12 are **969 lines, 52.8% of the numbered text** — the row's premise that they dominate is
correct. `CLAUDE.md` is 121 lines *including* the design-principles section added by 5476c00.

### E2. The orchestrator reads `read_first` once per run, not at every gate

This is the row's first premise, and it does not hold. The only instruction to read those
documents is under *Before the first dispatch*:

```
$ sed -n '46,52p' src/taskrail/skills/taskrail-autopilot/SKILL.md
## Before the first dispatch

- Run `taskrail autopilot status --json`. …
- Read the governing documents: the paths in `read_first` in that output
  (`[autopilot].read_first`, which falls back to the `governing` entries), the documents they lead
  to, and the backlog rows of the tasks. Answer gates from them first. Tell the human about any
  entry in `read_first_missing`.
```

`references/gate-review.md` says only "Answer from the governing documents", which presumes they
were already read:

```
$ sed -n '7,10p' src/taskrail/skills/taskrail-autopilot/references/gate-review.md
- **Governing documents first.** Answer from the governing documents — `read_first` in
  `autopilot status` — the design they lead to and the task row before your own preference. A
  decision they reserve to humans escalates.
```

And `DESIGN.md` §12.6 defines the key the same way:

```
$ sed -n '1493,1495p' DESIGN.md
- **Read-first documents.** `read_first` lists the governing documents: repository-relative files,
  directories or globs the orchestrator reads before the first dispatch and answers gates from.
```

So the cost of the file's size is **one read per run**, amortised over every task and every gate
in it. Whatever re-reading an orchestrator does at a gate is its own judgement, not an instruction,
and cannot be reduced by a split it is equally free to read whole.

Two further facts from the same place, which bear on option 4:

- `read_first` entries are **paths, directories or globs** — never sections
  (`src/taskrail/config.py:79`, `src/taskrail/autopilot/commands.py:416`, "`_matches_anything` —
  whether a `read_first` entry … names anything that exists (T061)"). The key cannot be made to
  point at §12.6.
- The skill already says to read "**the documents they lead to**". A portal whose map leads to nine
  topic documents therefore instructs the orchestrator to read all nine. A split saves nothing
  under the shipped wording; to save anything, the *shipped skill* would have to change — a change
  to the portable core, which would ship one repository's document structure to every installation.

### E3. `DESIGN.md` is invisible to the shipped skills

```
$ grep -rn 'DESIGN' src/taskrail/skills/ src/taskrail/integrations/ | wc -l
0
```

Zero mentions, zero section citations. `DESIGN.md` is this repository's internal design document;
nothing an installer ships depends on its shape. Every cost and every benefit of a split falls
inside this repository — which also means a split cannot be justified by what it does for
consumers.

### E4. What gates actually cite — §7 and §12 most of all

The citation census over the 67 decision records of past runs (this task's own record excluded),
counting the files that cite each top-level section at least once:

| Section | Lines | Records citing it (of 67) | | Section | Lines | Records citing it |
|---|---:|---:|---|---|---:|---:|
| §1 Goals | 24 | 3 | | §8 Skills | 63 | 7 |
| §2 Concepts | 13 | 1 | | §9 Distribution | 51 | 3 |
| §3 File format | 63 | 3 | | §10 Layout | 18 | 1 |
| §4 Configuration | 96 | 9 | | §11 Phases | 13 | 5 |
| §5 Kinds | 234 | 8 | | **§12 Autopilot** | **464** | **36** |
| §6 Claims and IDs | 166 | 13 | | §13 Current branch | 126 | 6 |
| **§7 CLI** | **505** | **28** | | | | |

**The two sections a split would remove first are the two that gate answers cite most**: §12 in 36
of 67 records, §7 in 28. That is not an accident of sampling — this repository builds a CLI with an
autopilot, so most of its tasks are about §7 or §12, and a future backlog will look the same. The
row's implicit argument ("§7 and §12 are big, so move them out of the way") inverts the measured
relation between size and need.

How many sections one gate cluster needs, and which:

```
$ for f in $(ls docs/autopilot/decisions/*.md | grep -v README | grep -v T089); do
    grep -oE '§ ?[0-9]+' "$f" | tr -d ' ' | sort -u | wc -l; done | sort -n | uniq -c
  15 records cite 0 sections    5 cite 4
  19 cite 1                     4 cite 5
  16 cite 2                     2 cite 7
   6 cite 3
```

Median 1, mean 1.8 — but the *union* over all records covers all thirteen sections. No fixed
subset of the document serves gates in general; what varies is which two.

**This census is a proxy, and the write-up says so plainly.** It measures what a gate answer
*referred to*, which is a lower bound on what was *read*: a section can be needed — to establish
that it does not apply, most often — and never cited. There is no instrumented record of what any
orchestrator loaded, and producing one is beyond this spike.

**A second data point, labelled for what it is.** Answering the gates of run `20260918-1` required,
of `DESIGN.md`, §1-§4, §5.6, §8, §9, §10, §11 and §12.6, and not §7's command table or the rest of
§12. That is one orchestrator, one run, four gates (T087 `frame` and `decide`, T088 `frame`, T089
`frame`) — corroboration of the census's shape, never a substitute for it. It points the same way
in one respect that matters: what was needed of §12 was §12.6, a 30-line sub-section, not the
464-line section a split would move.

### E5. The cross-reference census: 1728 citations in 153 files, 81% of them bare

```
$ uv run python <scratchpad>/census2.py .          # excludes this task's own two documents
docs/ artifacts              932 citations   64 files   175 of them name the file
docs/autopilot/decisions     468 citations   52 files   109 of them name the file
DESIGN.md (internal)         248 citations    1 files     0 of them name the file
src/*.py                      48 citations   22 files    34 of them name the file
tests/*.py                    11 citations    8 files     7 of them name the file
README.md                      7 citations    1 files     3 of them name the file
CHANGELOG.md                   5 citations    1 files     4 of them name the file
TODO.md                        5 citations    1 files     5 of them name the file
CLAUDE.md                      2 citations    1 files     0 of them name the file
.taskrail/config.toml          1 citations    1 files     1 of them name the file
other                          1 citations    1 files     0 of them name the file
TOTAL                       1728 citations  153 files   338 name the file
```

Three readings of this table:

1. **The corpus is an order of magnitude larger than the row says.** The row names "76 historical
   artifacts". That figure is reproducible, but for the four sections it lists only: 75 files
   repo-wide cite §4, §5.6, §7.1 or §12.8 (61 of them under `docs/`), which is the row's 76 to
   within one file. The corpus that cites *any* section is **153 files and 1728 citations**.
2. **Bare `§N` is the house style.** Only 338 citations (19.6%) name the document; the other 1390
   are bare `§12.6`, which resolves only because there is exactly one numbered design document.
   Split it, and every bare citation needs a reader who knows which topic file §12.6 landed in.
3. **The document is densely self-referential.** Of its 248 internal citations, 99 stay inside
   their own top-level section and **149 cross section boundaries**, spread over 49 distinct
   section pairs; every top-level section both cites another and is cited by another. Those 149
   are not incidental links — they are the document's connective tissue, and a split converts all
   of them into cross-file links.

Which of the repository's documents are actually *maintained*, and so could be rewritten: `src`
(48), `tests` (11), `README.md` (7), `CHANGELOG.md` (5), `TODO.md` (5), `CLAUDE.md` (2),
`.taskrail/config.toml` (1) — **about 80 citations across 36 files**. The other **1400 citations in
116 documents under `docs/`** are historical artifacts and decision records, which this repository
does not rewrite: they are the record of what was decided and when.

### E6. The prototype: what a split costs and what it saves

A full split by topic, built in the scratchpad (nothing entered the repository), mapping §1-3 →
`overview`, §4 → `configuration`, §5 → `kinds`, §6 → `claims`, §7 → `cli`, §8 → `skills`, §9-11 →
`distribution`, §12 → `autopilot`, §13 → `current-branch`:

```
$ uv run python <scratchpad>/split.py . <scratchpad>/split
documents: 9
  overview.md: 100 lines        skills.md: 63 lines
  configuration.md: 96 lines    distribution.md: 82 lines
  kinds.md: 234 lines           autopilot.md: 464 lines
  claims.md: 166 lines          current-branch.md: 126 lines
  cli.md: 505 lines
preamble lines kept in the portal: 8
cross-document citation rewrites inside the split: 149
```

So the **counted** cost, not an estimate: 149 rewrites inside the split, ~80 in maintained files,
1400 citations stranded in 116 documents nobody will rewrite, 9 new files and a portal to keep
in step with them.

And the saving, measured against the runs that actually happened. For each past run, the lines of
the sections its decision records cite, as a union (what one selective read before the first
dispatch would have cost) against the per-task sum (what selective reading per task would cost):

```
$ uv run python <scratchpad>/runs.py .
run          tasks union lines  sum per task  sections in the union
20260914-1      10        1128          5386  ['4', '7', '8', '12']
20260915-2       2        1135          2270  ['6', '7', '12']
20260915-4       1         505           505  ['7']
20260915-5       2         568           568  ['7', '8']
20260915-6       2         147           294  ['4', '9']
20260918-1       1         761           761  ['5', '8', '12']
(three further runs cite no section at all; run handles appear in 22 of the 67 records,
 so this covers 9 runs, not all of them)
```

The whole numbered document is **1836 lines, read once per run**. The largest run in the record,
ten tasks, would have needed a union of 1128 lines — a 39% saving if the orchestrator could know
that union in advance, which it cannot — and **5386 lines if it read selectively per task, nearly
three times the cost of reading the file once**. Below about three tasks a run, selective reading
is roughly break-even; above it, it loses. This repository's `max_lanes` is 3.

Per-task, the theoretical ceiling of selectivity:

```
$ uv run python <scratchpad>/need.py .
decision records considered: 67
lines of the sections a record cites — min 0, median 505, mean 559, max 1604 (of 1836)
records whose cited sections are <= 25% of the numbered text: 20/67
                                    <= 50%: 49/67    <= 75%: 64/67
```

A perfectly selective reader saves about 70% **per task** and loses at run scale, because the
sections the lanes need overlap heavily (§7 and §12 are in almost every union above).

### E7. The drift argument does not hold in this repository

The comparable repository consulted earlier reported that its second hand-kept index drifted out
of sync with its documentation map. This repository keeps five hand-kept indexes, and at this
commit every one of them is exact:

```
$ for d in bugs chores features spikes; do
    echo "$d: $(ls docs/$d/*.md | grep -v README | wc -l) documents, $(grep -cE '^\| T[0-9]+ ' docs/$d/README.md) rows"; done
bugs: 12 documents, 12 rows
chores: 19 documents, 19 rows
features: 39 documents, 39 rows
spikes: 5 documents, 5 rows
docs/autopilot/decisions: 68 documents, 68 rows
```

143 documents, five indexes, zero drift, and no test enforcing any of it. But the reason is
specific and does not transfer: every one of those rows is written by a **per-task step the skills
state** ("write the kind's document at `artifact`, and add a row for it to `artifact_index`"), so
the habit is exercised on every task. A documentation map has no such trigger — documents would be
added to it once or twice a year — so the drift the other repository saw is the likelier outcome
here, not the sync record above.

### E8. A test could hold the links, not the judgement

The precedent is real: `tests/test_autopilot_skill.py` asserts shipped prose against
`build_parser()` (`test_every_taskrail_command_and_flag_shown_exists`,
`test_every_taskrail_command_and_flag_in_the_claude_notes_exists`), and eight test modules cite
`DESIGN.md` sections in their docstrings. A test could assert that every file under a `docs/design/`
directory is linked from the portal, and that no `§N` citation names a section its own file does
not contain. It could not assert that a map's *when to read it* guidance is still true, which is
the part that decays, and it would be a repository-level test of this repository's own documents —
the kind T060 explicitly rejected ("items must stay self-contained").

## Options considered

What a gate reads is given **per run**, since that is when `read_first` is read (E2).

| | Option | What a gate reads | What breaks | New upkeep |
|---|---|---|---|---|
| **1** | **Leave it as one file** | 1844 lines, once per run | nothing | none |
| **1+** | **Leave it as one file, add a reading map at its top (recommended)** | 1844 lines once per run, and a reader who wants one section finds it in ~13 rows | nothing: no renumbering, no new file, no citation touched | one row when a section is added — inside the file being changed, so the diff shows the omission |
| 2 | Split §7 and §12 out; `DESIGN.md` becomes a portal with a map | the portal plus, under the skill's "the documents they lead to", all three anyway | the §7 and §12 citations: 264 + 663 occurrences repo-wide, 48 of them in maintained files; of the 149 internal cross-references, those into §7 and §12 (29 + 27) become cross-file | a portal and two documents; the worst of both — the two most-needed sections are the ones moved one hop further away |
| 3 | Split fully by topic (9 documents) | the portal plus all nine, unless the shipped skill changes | 149 internal rewrites, ~80 in maintained files, 1400 citations in 116 unrewritten documents left needing a lookup table | 9 documents plus a portal, a map with no per-task trigger to keep it honest (E7), and an optional link test that cannot check the judgement (E8) |
| 4 | Keep one file, remove it from `read_first` and point at sections | nothing before the first dispatch; whatever the orchestrator fetches per gate | gate answers: 52 of 67 past records cite the document. `read_first` cannot name a section (E2), so "point at sections" means prose in `CLAUDE.md` and an orchestrator trusted to fetch well | none, but measured against past runs this is the *most* expensive reading pattern (5386 lines for the ten-task run, E6) |

Option 4 deserves its place — it was kept in scope deliberately, and it attacks the stated problem
most directly — but the measurement turns it down: removing the file from `read_first` does not
stop it being read, it only moves the read from once per run to once per task, and E6 prices that
at up to three times as much.

Adopting option 4 would also change `.taskrail/config.toml`, which is outside this task's touch
map; it could only ever have become a follow-up task.

## Recommendation

**Do not split `DESIGN.md` (option 1), and add a reading map at its top (option 1+), as T093.**

The reasons, in order of weight:

1. **The premise that makes a split urgent is false.** `read_first` is read once before the first
   dispatch (E2, confirmed in the skill, in `gate-review.md` and in §12.6 itself). 1844 lines once
   per run is not a cost worth 1400 stranded citations.
2. **The sections a split would move are the ones gates need most** (E4): §12 in 36 of 67 decision
   records, §7 in 28. Splitting optimises the document against its own usage.
3. **Selective reading is a loss at this repository's run size** (E6): the one ten-task run in the
   record would have read 5386 lines selectively against 1836 whole, and even a perfect union saves
   only 39%.
4. **The cost is counted, not estimated** (E5, E6): 149 internal rewrites, ~80 in maintained files,
   1400 citations in 116 documents this repository does not rewrite, and a house citation style —
   bare `§N`, 81% of all citations — that only works while there is one numbered design document.
5. **KISS and YAGNI, applied prospectively as T087 requires, argue against the split, not for it.**
   The change under judgement is the one this spike would propose. Nine documents, a portal, a map
   with no per-task trigger and a link test exist to serve a saving that measurement puts at or
   below zero. The simplest change that meets the real need — a reader who wants one section
   finding it quickly — is a table of contents.

**What T093 does.** A short table at the top of `DESIGN.md`, one row per numbered section in the
form *what you need it for* → *§N*, in the spirit of the comparable repository's "Documentation
map" but inside the one document, so nothing is renumbered, no file is added, no citation moves
and `read_first` is untouched. It is one file, one diff, and it is reversible.

**What is explicitly not recommended:** changing `[autopilot].read_first`; changing the shipped
skills' wording about what the orchestrator reads; and any renumbering of `DESIGN.md`'s sections,
which would break 1728 citations for no benefit at all.

## What would change the decision

- **`DESIGN.md` roughly doubling.** The per-run read is affordable at 1844 lines; the argument is
  about cost against benefit, not about principle. At about 3500-4000 lines, re-run E6 — if the
  per-run union falls below half the whole for typical runs, splitting starts to pay.
- **A section growing past about 600 lines while staying cohesive** — most plausibly §12. A single
  topic document extracted for *authoring* reasons (one editor, one reviewer, one merge surface)
  is a different case from the reading-cost case this spike rejects, and it would be judged on
  conflict rates between lanes, not on read volume.
- **The shipped skill changing what the orchestrator reads.** If `read_first` ever became a
  per-gate read, or gained a way to name a part of a document, E2 collapses and the whole question
  reopens. That change would have to justify itself in the portable core first.
- **A run size well above three lanes.** E6's crossover is near three tasks. A repository routinely
  running ten lanes has a different answer, and this verdict is stated for *this* repository.
- **A measured instance of the size actually hurting.** One recorded gate where the orchestrator
  demonstrably missed something because it read 1844 lines, or ran out of room to read them, is
  worth more than every line count above. Nothing in the 67 decision records shows one.
- **Someone deciding the bare `§N` citation style should go.** If citations were required to name
  their document, the largest single cost of a split (E5, reading 2) would shrink. That is a
  bigger change than the split, and would want its own spike.

## How to reproduce

From a checkout at `4a956c4` or later:

```bash
wc -lwc DESIGN.md CLAUDE.md README.md                                          # E1
awk '/^## /{if(prev){print prev": "NR-start} prev=$0; start=NR} END{print prev": "NR-start+1}' DESIGN.md
sed -n '46,52p' src/taskrail/skills/taskrail-autopilot/SKILL.md                # E2
sed -n '7,10p' src/taskrail/skills/taskrail-autopilot/references/gate-review.md
sed -n '1493,1498p' DESIGN.md                                                  # E2: §12.6
grep -rn 'DESIGN' src/taskrail/skills/ src/taskrail/integrations/ | wc -l      # E3: 0
for s in $(seq 1 13); do echo -n "§$s: "; ls docs/autopilot/decisions/*.md \
  | grep -v T089 | xargs grep -lE "§ ?$s([^0-9]|\$)" | wc -l; done             # E4
grep -rlE '§ ?(4|5\.6|7\.1|12\.8)([^0-9]|$)' --include='*.md' --include='*.py' \
  --include='*.toml' . | wc -l                                                 # E5: the row's 76 → 75
for d in bugs chores features spikes; do echo "$d: $(ls docs/$d/*.md | grep -v README | wc -l) \
  documents, $(grep -cE '^\| T[0-9]+ ' docs/$d/README.md) rows"; done          # E7
grep -n '^def test_every_taskrail_command' tests/test_autopilot_skill.py       # E8
```

For E5, E6 and the per-task figures, with these scripts — run from the repository root and kept
**outside** the repository, as a spike's throwaway code must be:

`census2.py` — the citation census by file class, excluding this task's own documents:

```python
import re, pathlib, sys, collections
root = pathlib.Path(sys.argv[1])
CITE = re.compile(r"§ ?\d+(?:\.\d+)*"); QUAL = re.compile(r"DESIGN[^§]{0,30}§ ?\d+")
def cls(p):
    s = str(p.relative_to(root))
    if s == "DESIGN.md": return "DESIGN.md (internal)"
    if s in ("README.md", "CLAUDE.md", "CHANGELOG.md", "TODO.md"): return s
    if s.startswith(("src/taskrail/skills", "src/taskrail/integrations")): return "shipped skills"
    if s.startswith("src/"): return "src/*.py"
    if s.startswith("tests/"): return "tests/*.py"
    if s.startswith("docs/autopilot/decisions"): return "docs/autopilot/decisions"
    if s.startswith("docs/"): return "docs/ artifacts"
    if s.startswith(".taskrail/"): return ".taskrail/config.toml"
    return "other"
occ, files, qual = collections.Counter(), collections.Counter(), collections.Counter()
for p in root.rglob("*"):
    if p.suffix not in {".md", ".py", ".toml"} or {".git", ".worktrees"} & set(p.parts): continue
    if "T089-decide-whether-to-split-design-md-by-top" in p.name: continue
    t = p.read_text(); n = len(CITE.findall(t))
    if n: c = cls(p); occ[c] += n; files[c] += 1; qual[c] += len(QUAL.findall(t))
for c in sorted(occ, key=lambda k: -occ[k]):
    print(f"{c:<26} {occ[c]:>5} citations {files[c]:>3} files {qual[c]:>4} name the file")
```

`split.py` — the split prototype and the rewrite count (it writes only into the scratchpad path
given as its second argument):

```python
import re, pathlib, sys, collections
root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
HEAD = re.compile(r"^## (\d+)\. (.*)$"); CITE = re.compile(r"§ ?(\d+)((?:\.\d+)*)")
TOPIC = {"1":"overview","2":"overview","3":"overview","4":"configuration","5":"kinds","6":"claims",
         "7":"cli","8":"skills","9":"distribution","10":"distribution","11":"distribution",
         "12":"autopilot","13":"current-branch"}
cur, buckets, preamble = None, collections.defaultdict(list), []
for line in (root / "DESIGN.md").read_text().splitlines(keepends=True):
    m = HEAD.match(line)
    if m: cur = m.group(1)
    (buckets[TOPIC[cur]] if cur else preamble).append(line)
rewrites = 0
for topic, body in buckets.items():
    def sub(m):
        global rewrites
        if TOPIC[m.group(1)] != topic:
            rewrites += 1
            return f"[{TOPIC[m.group(1)]}.md §{m.group(1)}{m.group(2)}](./{TOPIC[m.group(1)]}.md)"
        return m.group(0)
    (out / f"{topic}.md").write_text(CITE.sub(sub, "".join(body)))
print("documents:", len(buckets), "| portal preamble:", len(preamble), "| rewrites:", rewrites)
for t, b in buckets.items(): print(f"  {t}.md: {len(b)} lines")
```

`runs.py` — the per-run union against the per-task sum (E6); `need.py` is the same idea without the
run grouping, printing the min, median, mean and max of the per-record totals:

```python
import re, pathlib, sys, collections
root = pathlib.Path(sys.argv[1])
SIZE = {"1":24,"2":13,"3":63,"4":96,"5":234,"6":166,"7":505,"8":63,"9":51,"10":18,"11":13,"12":464,"13":126}
RUN, CITE = re.compile(r"(20\d{6}-\d+)"), re.compile(r"§ ?(\d+)")
runs = collections.defaultdict(list)
for p in sorted((root / "docs/autopilot/decisions").glob("*.md")):
    if p.name == "README.md" or "T089" in p.name: continue
    t = p.read_text(); m = RUN.search(t)
    if m: runs[m.group(1)].append({x for x in CITE.findall(t) if x in SIZE})
for r in sorted(runs):
    union = set().union(*runs[r])
    print(r, len(runs[r]), sum(SIZE[x] for x in union),
          sum(sum(SIZE[x] for x in s) for s in runs[r]), sorted(union, key=int))
```

**Sensitivity of the counts.** The citation pattern is `§ ?\d+(\.\d+)*`; counting bare `§N` and
`§N.M` separately, or treating `§12.6` as a citation of §12 as well, moves the occurrence totals by
tens but changes no comparison in this document. Section sizes are lines from one `## N.` heading
to the next, so §3 includes the worked `TODO.md` example whose own `##` headings `awk` counts
separately (63 lines, not 7). The per-run figures rest on run handles that appear in 22 of 67
decision records; they describe 9 runs, and the ten-task run `20260914-1` is the only large one in
the record.

## Follow-ups

Opened on this task's branch, so the verdict and its adoption are reviewed together:

| ID | Kind | Pts | Title | What it does |
|---|---|---|---|---|
| T093 | `chore` | 1 | Add a reading map to the top of `DESIGN.md` so a gate can read only what it needs | One table at the top of `DESIGN.md`, a row per numbered section saying what it is for. No renumbering, no new file, no citation moved, `read_first` untouched. |

Deliberately **not** opened: no task to split the document, none to change `[autopilot].read_first`,
none to change the shipped skills' wording about what the orchestrator reads, and none to rewrite
the bare-`§N` citation style — each is refused by the verdict above, and the last would need its own
spike before anyone costed it.
