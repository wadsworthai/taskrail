# T090 — Record the scope, reach and refusal rules for the design principles in CLAUDE.md

Kind: chore · Epic: E08 · Status: scope proposed

## Goal

Adopt in `CLAUDE.md` the verdict T087 reached and the human accepted on 2026-09-18
([`docs/spikes/T087-decide-whether-the-design-principles-gov.md`](../spikes/T087-decide-whether-the-design-principles-gov.md),
*Outcome*; the answers verbatim in
[`docs/autopilot/decisions/T087-decide-whether-the-design-principles-gov.md`](../autopilot/decisions/T087-decide-whether-the-design-principles-gov.md)).
The `## Design principles` section as it stands leaves three things unsaid, and this chore says
them in the fewest words that carry the meaning:

1. **Scope.** The opening sentence names the whole repository ("the CLI, the skills"), which reads
   retroactive, while the conflict sentence is prospective. The verdict is prospective: the
   principles judge the change a task makes, not the code already there.
2. **The first gate, not the plan gate.** The text says "say so at the plan gate", but `plan` is a
   stage of the `feature` kind only — `chore` has `scope`, `bug` has `diagnose`, `spike` has
   `frame` — so as written the rule binds one kind in four.
3. **Objection, not veto, and no silent substitution.** "Say so … rather than building around it"
   forbids silent *elaboration* but not silent *substitution*, the more dangerous failure, and it
   does not say that the executor then builds what the answer says.

Reach — sub-question 2 of T087, the one generic pointer in the core `taskrail` skill — is **not**
this task: it is T091, which runs in parallel and owns `src/taskrail/`.

## The text today

`CLAUDE.md` lines 64-68, verbatim at this branch's base `origin/main` = 15823fc:

```
$ sed -n '64,68p' CLAUDE.md
## Design principles

These govern the CLI, the skills and the work planned in the backlog. When two of them pull in
different directions, the simpler outcome wins; when one argues against what a task's description
asks for, say so at the plan gate rather than building around it.
```

The five bullets that follow (KISS, YAGNI, rule of three, Occam's razor, premature optimization)
are unchanged by this task.

## Change set

| File | Change |
|---|---|
| `CLAUDE.md` | Replace the section's opening paragraph (lines 66-68) with two paragraphs: the first keeps the existing scope and conflict sentences and adds the prospective sentence; the second states the objection rule. The five principle bullets and every other section are untouched. |
| `TODO.md` | Through the CLI only: this task's row with `taskrail done` at close. No row or table is edited by hand. |
| `docs/chores/T090-record-the-scope-reach-and-refusal-rules.md` | This artifact. |
| `docs/chores/README.md` | One appended row for this artifact. |

### The proposed replacement

```markdown
These govern the CLI, the skills and the work planned in the backlog. They judge the change a task
makes, not the code that is already there: apply them to what you add or change, and when what
exists offends one, open a task rather than widening yours. When two of them pull in different
directions, the simpler outcome wins.

When one argues against what a task's description asks for, object rather than refuse: at the
task's first gate — `plan`, `scope`, `diagnose` or `frame` — name the principle and propose the
simpler alternative as a decision, then build what the answer says. Never build around the
objection, and never substitute a simpler design for the described one without an answer.
```

Where each of the three points lands: the prospective sentence is sentence 2 of the first
paragraph, in the wording T087 proposed; "the plan gate" becomes "the task's first gate" with all
four stage names; the second paragraph adds "object rather than refuse", "then build what the
answer says" and the ban on silent substitution, keeping the existing "rather than building around
it" as "never build around the objection".

The section grows by six lines and loses none of what it says today. The voice is the file's:
plain prose in the paragraph, imperative addressed to the executor, as the surrounding sections
and the bullets below are.

## Decisions needed

1. **Second person, not "an executor".** The task context phrases point 3 as "an executor names the
   principle and proposes the alternative"; the draft says "name the principle and propose", in the
   imperative the rest of `CLAUDE.md` uses ("apply them", "say so", "State such a rule in the
   skill's prose too"). The meaning is identical and the sentence is shorter.
   *Recommendation: keep the imperative.* Alternative: third person — "an executor names the
   principle … and then builds what the answer says" — which matches the spike's wording literally
   but changes voice mid-section.
2. **Two paragraphs rather than one.** The draft splits the objection rule into its own paragraph;
   the section is one paragraph today. Three sentences of conflict handling in a single block read
   as a wall, and the second paragraph is the rule an executor must find at a gate.
   *Recommendation: two paragraphs.* Alternative: one paragraph, which keeps the diff to a
   sentence-level edit but buries the objection rule.
3. **Nothing is said about reach.** The section will still not name where an executor reads the
   principles; T091 adds the pointer in the core skill, and no principle is named in
   `src/taskrail/skills/`. *Recommendation: say nothing here* — a sentence about the skills would
   duplicate T091 and would date if T091's line changes. Alternative: a sentence pointing at the
   skills, which crosses into T091's area.

## Out of scope

- **`src/taskrail/` and the installed copies under `.claude/skills/`** — T091's area, and this task
  touches neither. No `taskrail upgrade` is run.
- **`DESIGN.md`** — T089 decided its structure stays, and T093 will add the reading map.
- **T088's row** — its figures are corrected by T092, not here.
- **Rewriting the five principle bullets, or adding a sixth.** The design principles apply to this
  change: it says the three things the verdict asks for and nothing more.
- **Making `CLAUDE.md` a `governing` path** (T087 option 2D). It answers a different question, and
  the repository set `governing = []` deliberately.
- **Re-opening the verdict.** T087's decision is accepted; this chore adopts it.

## Verification

- `sed -n '64,80p' CLAUDE.md` shows the section with the three points present and the five bullets
  unchanged.
- `git diff --stat origin/main..HEAD` shows `CLAUDE.md` as the only non-artifact, non-backlog file
  changed, and `git diff origin/main..HEAD -- CLAUDE.md` shows no edit outside lines 66-68.
- `taskrail checks T090 --stage implement` (`test`: `uv run pytest -q`) passes. No test reads
  `CLAUDE.md`, so it proves only that a documentation edit broke nothing.
- `.taskrail/bin/taskrail validate` passes.
- `grep -n "plan gate" CLAUDE.md` returns nothing.
