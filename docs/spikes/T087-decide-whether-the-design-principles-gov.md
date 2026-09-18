# T087 — Decide whether the design principles govern new work only or also what exists

**Verdict.** The design principles are **prospective**: they judge the change a task makes, not
the code that already exists. They reach an executor through `CLAUDE.md` alone — no principle is
stated in the shipped skills — and they let an executor **object, not refuse**: at the task's
first gate it names the principle and proposes the simpler alternative, and then builds what the
answer says. Retroactive application happens only through the backlog, by a task that asks for it,
as E08's own tasks do.

## Question

`CLAUDE.md` gained a `## Design principles` section in commit 5476c00 (PR #20): KISS, YAGNI, the
rule of three, Occam's razor and "premature optimization is the root of all evil". The section
says the principles "govern the CLI, the skills and the work planned in the backlog", but not
what that means for code and options written before the section existed. Three sub-questions make
up the decision:

1. **Scope.** Are the principles prospective (they judge the change a task makes) or also
   retroactive (they judge what the repository already has, so an agent may propose removals as
   part of unrelated work)?
2. **Reach.** Where does an executor read them? Today only the always-loaded root file states
   them; the executor skills do not mention them, and the autopilot lane brief names the
   repository's agent instructions without naming the principles. Is the root file enough, or must
   the shipped skills and the lane brief name them?
3. **Refusal.** May an executor refuse, at the plan gate, a design the task's own description asks
   for, on the strength of a principle? If so, how is that escalated — and how does it interact
   with the autopilot, where the orchestrator answers gates and the human sees the result only at
   the pull request?

## Evidence

All commands were run in this task's worktree, on branch
`T087-decide-whether-the-design-principles-gov` at base `origin/main` = 5476c00.

### E1. The introducing commit states the intent: the principles are for new work

```
$ git show --stat 5476c00 | head -20
commit 5476c00aba04e12560f6a10198fdd57e5164cc50
    docs(repo): add the design principles and the epic that applies them to what exists (#20)

    KISS, YAGNI, the rule of three, Occam's razor and "premature optimization
    is the root of all evil", each stated as a rule for this repository, with
    what to do when two of them conflict or when one argues against a task's
    description.

    The principles are stated for new work, but the repository was built
    before them, so E08 adds three spikes that decide what they mean for what
    exists: their scope and where an executor reads them (T087), the CLI and
    configuration surface that has no consumer (T088), and whether DESIGN.md
    is split by topic for what the orchestrator reads first (T089).

 CLAUDE.md | 17 +++++++++++++++++
```

The commit that introduced the section says in as many words that **"the principles are stated
for new work, but the repository was built before them"**, and that E08 exists to decide the rest.
A retroactive default would make E08 redundant: the epic would already be answered by the section
it was created to interpret.

### E2. The section is ambiguous exactly where the task says it is

`CLAUDE.md` lines 64-80, verbatim, unchanged at the base commit:

> ## Design principles
>
> These govern the CLI, the skills and the work planned in the backlog. When two of them pull in
> different directions, the simpler outcome wins; when one argues against what a task's description
> asks for, say so at the plan gate rather than building around it.

The scope sentence names the whole repository ("the CLI, the skills"), which reads retroactive;
the conflict sentence is about "what a task's description asks for", which is prospective. Neither
says what an executor does about code that predates the section. The conflict sentence also stops
one word short of the refusal question: "say so … rather than building around it" forbids working
around a principle silently, but does not say whether saying so permits building something other
than what the task described.

### E3. The principles appear in no other file

```
$ grep -rn "design principle\|KISS\|YAGNI\|Occam\|rule of three\|premature optim" -i . \
    --include=*.md --include=*.py --exclude-dir=.git --exclude-dir=.worktrees
TODO.md:12, TODO.md:124, TODO.md:128, TODO.md:129      (the E08 epic and task rows)
CLAUDE.md:64,70,72,74,76,78                            (the section itself)
docs/spikes/T087-…, docs/autopilot/decisions/T087-…    (this task's own documents)
```

Nothing in `src/`, nothing in `DESIGN.md`, nothing in the skills. The principles are stated once
and referenced nowhere.

### E4. Every other rule in `CLAUDE.md` is bounded by the diff, and most have mechanical support

| Rule in `CLAUDE.md` | What it judges | Mechanical support |
|---|---|---|
| Language policy | what you commit | none, but binary and visible in the diff |
| Publishing constraint | what you commit | none, but binary and visible in the diff |
| Agent portability | the skill you write | `pytest`: `tests/test_autopilot_skill.py::test_portable_text_names_no_agent_or_agent_tool`, `tests/test_skills_current_branch.py::test_the_portable_core_skill_asks_before_a_push_without_the_agent_notes` |
| Backlog | the row you add or close | the CLI owns IDs and statuses; `taskrail validate` |
| Merging | the pull request you open | `taskrail review --publish` generates the title |
| **Design principles** | **unstated** | **none: no check, no generator, no test, no reviewer hook** |

Each existing rule applies to something the task under way produces. Only the principles have an
unstated object, and only they have no mechanism at all. A retroactive reading would make them the
single rule in the file with unbounded scope and no enforcement — the combination most likely to
produce the "removals nobody asked for" that the task row warns about.

### E5. A retroactive reading contradicts the scope rule the skills already state

`src/taskrail/skills/taskrail/SKILL.md` step 6 (*Scope*):

> Never edit the areas in `never_edit`. Work you discover outside the task's scope becomes a
> follow-up task; mention it at the next gate. Only fix something directly on the way when it is
> small and inseparable from the task.

and `taskrail-chore`'s `implement` stage: "If something outside it turns out to need changing, stop
and ask to amend the scope; never widen it silently." Under the autopilot a touch map narrows this
further. An executor that removed an unused flag while fixing an unrelated bug would be breaking a
rule the skills state plainly, on the strength of a principle that never says it may.

### E6. The refusal vocabulary already exists, twice

`DESIGN.md` §5.6 defines a **decision**:

> A **decision** is a choice that the task, the artifact already written, the repository's
> instructions and the executor skill do not settle, and whose options differ in a way the human
> would care about.

An executor's objection "this task asks for a subsystem where a flag would do" is exactly that: the
task asks for one thing, the repository's instructions argue for another, and neither settles it.
§5.6 also gives the stop for it — `always`/`conditional` stop at the stage's end, `decisions` stops
mid-stage — so the objection already has a route to the human.

`DESIGN.md` §12.6 lists when the orchestrator escalates to the human; reason 6 is **"a task row
rests on a false premise"**, one of the four judgement reasons the skill carries
(`src/taskrail/skills/taskrail-autopilot/SKILL.md:136`). An objection that says the described
design rests on an assumption that no longer holds is that reason, unchanged.

`references/gate-review.md` already groups the stages where such an objection belongs, and calls
them by a name that covers all four kinds:

```
$ sed -n '19,33p' src/taskrail/skills/taskrail-autopilot/references/gate-review.md
## Plan-like gates: `plan`, `scope`, `diagnose`, `frame`, `decide`

- The task row's premise still holds on the current mainline; a false premise escalates. …
```

This matters for the wording: **`CLAUDE.md` says "the plan gate", but `plan` is a stage name only
for `feature`.** The stages are `plan` (feature), `scope` (chore), `diagnose` (bug) and `frame`
(spike):

```
$ grep -n "^## " src/taskrail/skills/taskrail-*/SKILL.md
taskrail-feature: plan / implement / verify
taskrail-chore:   scope / implement / docs
taskrail-bug:     diagnose / fix / impact
taskrail-spike:   frame / investigate / decide
```

Read literally, the sentence in `CLAUDE.md` binds one kind in four.

### E7. How an executor reaches the principles today

- **The lane brief** (`src/taskrail/skills/taskrail-autopilot/references/lane-brief.md`): "Read and
  follow the `taskrail` skill, the `<SKILL>` executor skill and the repository's own agent
  instructions literally." It points at the file without naming its content — which is the only
  portable way to do it.
- **`taskrail-chore`** alone among the executor skills points at the same file, in its `scope`
  stage: "Read the conventions of the area you will touch: nearby code, its README, the
  repository's agent instruction files."

```
$ grep -rn "agent instruction" src/taskrail/skills/ src/taskrail/integrations/
src/taskrail/skills/taskrail-chore/SKILL.md:24-25
```

  `taskrail-feature`, `taskrail-bug` and `taskrail-spike` have no equivalent line, and neither does
  the core `taskrail` skill.
- **The orchestrator** reads it at every gate: `.taskrail/config.toml` line 33,
  `read_first = ["CLAUDE.md", "DESIGN.md"]`, and `gate-review.md` line 8, "Governing documents
  first."
- **Under Claude Code specifically**, `CLAUDE.md` is loaded into every session regardless. That
  guarantee is agent-specific and must not be relied on in the portable core — the same trap
  `CLAUDE.md`'s *Agent portability* section names for `disable-model-invocation`.

### E8. What stating the principles in the shipped skills would cost

`DESIGN.md` §8 makes `src/taskrail/skills/` the portable core — one skill per kind, shipped by the
installer into every consuming repository — with agent-specific text confined to
`src/taskrail/integrations/`. `CLAUDE.md`'s *Agent portability* section requires that text to
assume no particular agent; §8 adds that it assumes no particular repository either ("Skills never
compute paths"; the integrations table is the only place specifics live).

A consumer's design principles are not this repository's. Writing "prefer a flag over a subsystem"
into `taskrail-feature` would ship one repository's taste to every installation, as a rule stated
with the same authority as the procedure, and a consumer that disagreed would have to edit an
installed copy that `taskrail upgrade` overwrites. The cost is therefore not size but
**authority**: it converts a repository preference into a property of the tool.

### E9. The size of what a retroactive reading would open

Re-verified with a script over the live parser (kept out of the repository, in the session
scratchpad; it is reproduced under *How to reproduce* below):

```
$ uv run python <scratchpad>/surface.py
commands (all levels): 42
top-level: 27
distinct long flags: 72
```

Top-level commands: `validate list show next claim release claims reserve-id unreserve-id init
upgrade integration self new workspace done discard reopen edit branch review checks epic kind
autopilot import merge-driver`. The 72 long flags include `--help`; 71 are taskrail's own.

Configuration, from `src/taskrail/config.py`: **9 first-level names** in `.taskrail/config.toml`
— `version`, `[[backlog]]`, `[columns]`, `[points]`, `[git]`, `[review]`, `[kinds]`, `[checks]`,
`[autopilot]` — holding 42 documented keys in total (`backlog` 8, `columns` 2, `points` 1, `git` 8,
`review` 7, `kinds` 1, `autopilot` 14, plus `version`), with `[checks]` a free-form map and
`[[autopilot.group]]` / `[[autopilot.resource]]` repeatable tables.

**These figures do not match T088's row**, which says "18 subcommands, about 66 distinct flags and
19 first-level config keys". The direction holds — the surface is large — but the numbers should be
corrected before T088 is worked; see *Follow-ups* below.

The options T088 names have no consumer visible in this repository: `.taskrail/config.toml` sets
`claim_remote = ""` and does not mention `branch_record_remote`, `autopilot.notify`,
`[[autopilot.group]]` or `[[autopilot.resource]]` at all. Their consumers, if any, are in
repositories the publishing constraint keeps out of this one — a fact T088 must work with rather
than around.

## Options considered

### Sub-question 1 — scope

| Option | What it means | Cost |
|---|---|---|
| **1A. Prospective (recommended)** | The principles judge what the task adds or changes. Existing code is re-examined only when a task asks for it. | An offending part of the base survives until someone writes a task for it. |
| 1B. Also retroactive | An executor may propose and make simplifications anywhere it finds them, as part of any task. | Contradicts the scope rule (E5) and the autopilot touch map; unbounded diffs that a reviewer cannot separate from the task; on a public tool, removals of options private consumers depend on, arriving as a side effect of unrelated work. This is the failure the task row predicts. |
| 1C. Leave it unstated | Today's text. | Each agent decides for itself; the outcome varies by session. The task exists because this is not acceptable. |

### Sub-question 2 — reach

| Option | What it means | Cost |
|---|---|---|
| **2A. Root file only, plus one generic pointer (recommended)** | The principles stay in `CLAUDE.md`. The shipped skills name no principle; the core `taskrail` skill gains one agent-agnostic, repository-agnostic line telling the executor to read the repository's agent instruction files before it plans — generalising `taskrail-chore`'s existing line to every kind. | One line ships to every consumer. It states a habit, not a policy, and repositories without such a file simply have nothing to read. |
| 2B. Name the principles in the executor skills | KISS/YAGNI/… written into `taskrail-feature` and the rest. | Breaks *Agent portability* and §8 (E8): ships one repository's taste to every installation with the authority of the procedure, and a disagreeing consumer must edit copies that `upgrade` overwrites. Also duplicates the text five times for a problem measured at zero. |
| 2C. Change nothing | `CLAUDE.md` is always loaded by this repository's agent and is in `read_first`. | Free, and the fallback if 2A is judged not to earn its line. Leaves three of four executor skills with no pointer, so the guarantee rests on an agent-specific loading rule the portability section itself warns against relying on. |
| 2D. Make `CLAUDE.md` a `governing` path | Every lane that touches it escalates. | Answers a different question (who may edit the principles), not this one. The repository deliberately set `governing = []` with a comment saying why. |

### Sub-question 3 — refusal

| Option | What it means | Cost |
|---|---|---|
| **3A. Objection, through the existing decision path (recommended)** | An executor may not refuse and may not silently build something else. At the task's first gate — `plan`, `scope`, `diagnose` or `frame` — it names the principle, proposes the simpler alternative, and builds what the answer says. The objection is a *decision* in the §5.6 sense and uses that stop; under a `decisions` gate it is asked mid-stage. Under the autopilot the orchestrator answers it from `read_first`, and escalates to the human when the objection says the row's premise no longer holds (§12.6 reason 6) or when it would change what the task delivers. | None beyond wording: no new mechanism, no new CLI surface, no new escalation reason. |
| 3B. A veto | The executor may decline the task and hand it back. | Inverts who owns the design: the human wrote the row. Under the autopilot every aesthetic disagreement becomes an escalation, and a lane can stall a run on taste. |
| 3C. A new mechanism (a "principle objection" state, flag or escalation reason) | A dedicated route for this one case. | Adds a second vocabulary for a stop §5.6 and §12.6 already define, with one known use — refused by the rule of three and by KISS, using the principles on themselves. |
| 3D. Leave it at "say so at the plan gate" | Today's text. | Ambiguous about whether saying so licenses building differently, and binds `feature` only, since `plan` is one stage name in four (E6). |

## Recommendation

**1. Scope: prospective.** The principles judge the change a task makes, not the code that is
already there. An executor applies them to what it adds or changes; it does not open the existing
surface on their strength. When existing code offends a principle, that becomes a task — which is
what E08 is. The evidence is the introducing commit's own statement of intent (E1), the fact that
every other rule in `CLAUDE.md` is bounded by the diff (E4), and the direct contradiction a
retroactive reading would create with the scope rule the skills already state (E5).

Wording to adopt, in a follow-up, as one sentence in the section's opening paragraph:

> They judge the change a task makes, not the code that is already there: apply them to what you
> add or change, and when what exists offends one, open a task rather than widening yours.

**2. Reach: the root file, plus one generic pointer in the core skill.** No principle is named in
`src/taskrail/skills/`. What ships is a pointer, not a policy: generalise `taskrail-chore`'s
existing "read the repository's agent instruction files" to the core `taskrail` skill so every
kind's executor reads them before it plans. That is agent-agnostic and repository-agnostic, costs
one line in the portable core, and closes the only real hole (E7). If that line is judged not to
earn itself, option 2C — change nothing — is an acceptable fallback, because `read_first`
guarantees the orchestrator reads `CLAUDE.md` at every gate; what it does not guarantee is that a
non-Claude executor does.

**3. Refusal: an executor objects, it does not refuse — and never builds around the objection.**
At the task's first gate it names the principle and proposes the simpler alternative as a decision,
with its recommendation and the alternatives, and then builds whatever the answer says. No new
mechanism: §5.6 supplies the stop, §12.6 reason 6 supplies the escalation when the objection
attacks the row's premise. Two wording fixes belong with it: replace "the plan gate" with "the
task's first gate (`plan`, `scope`, `diagnose` or `frame`)", and say explicitly that an executor
never substitutes a simpler design for the described one without an answer — silent substitution is
the dangerous failure, and the current sentence forbids only silent *elaboration*.

### What this gives T088 and T089

- **T088** (measure the CLI and configuration surface against YAGNI): the verdict does **not**
  license removal. T088 remains what its row says — measure, report each option with its known
  consumers and the cost of removing or defaulting it, change nothing. Its findings become tasks,
  and each such task is then a prospective change, judged on its own. Its headline numbers should
  be corrected first (E9): 27 top-level commands, 42 including subcommands, 71 of taskrail's own
  long flags, 9 first-level config names holding 42 documented keys. It should also record that
  `claim_remote`, `branch_record_remote`, `notify`, groups and resources have no consumer visible
  in this repository and that, by the publishing constraint, a private consumer cannot be cited in
  the write-up — so "no known consumer" is the strongest claim available, not "no consumer".
- **T089** (split `DESIGN.md` by topic): the retroactive question does not arise, because the task
  itself asks for the re-examination, which is precisely the route option 1A leaves open. KISS and
  YAGNI apply to the *change* T089 would propose — the cost of rewriting cross-references in
  sections 4, 5.6, 7.1 and 12.8 cited by README, DESIGN itself and 76 historical artifacts is a
  cost of the new structure, weighed against a measured benefit, not an argument about the
  existing file's merit.

## What would change the decision

- **A measured cost of the prospective rule.** If a reviewer finds that offending code accumulates
  because nobody writes the tasks, the answer is a recurring audit task, not a retroactive licence.
  Re-open this decision if two or more such audits are refused or never scheduled.
- **A non-Claude executor missing the principles.** Option 2A rests on the claim that a pointer is
  enough. One observed case of an executor that read the skills, had `CLAUDE.md` available and
  still planned against a principle would justify revisiting 2B — though even then the fix is a
  repository-local skill override, not text in the portable core.
- **A second consumer repository with its own principles.** That would confirm 2A rather than
  change it; the reverse — taskrail growing a first-class "principles" concept requested by
  consumers — would be a feature with its own design, and out of this decision's scope.
- **More than one kind of principle objection in practice.** Option 3A refuses a new mechanism on
  the rule of three. If objections become frequent and the orchestrator cannot answer them from
  `read_first`, a dedicated escalation reason becomes arguable on evidence.
- **The section moving out of `CLAUDE.md`.** If the principles were ever placed in a `governing`
  path, sub-question 2 would need re-reading, since the escalation behaviour would change.

## How to reproduce

From a checkout at 5476c00 or later:

```bash
git show --stat 5476c00                                  # E1: the stated intent
sed -n '64,80p' CLAUDE.md                                # E2: the section verbatim
grep -rn "design principle\|KISS\|YAGNI\|Occam\|rule of three\|premature optim" -i . \
  --include=*.md --include=*.py --exclude-dir=.git --exclude-dir=.worktrees   # E3
uv run pytest tests/test_autopilot_skill.py -k portable_text                  # E4
sed -n '405,435p' DESIGN.md                              # E6: §5.6, the definition of a decision
sed -n '1477,1487p' DESIGN.md                            # E6: §12.6, escalation reason 6
sed -n '19,33p' src/taskrail/skills/taskrail-autopilot/references/gate-review.md  # E6
grep -n "^## " src/taskrail/skills/taskrail-*/SKILL.md   # E6: the stage names per kind
grep -rn "agent instruction" src/taskrail/skills/        # E7
sed -n '1110,1130p' DESIGN.md                            # E8: §8, the portable core
```

For E9, with this script (run from the repository root; keep it outside the repository):

```python
from taskrail.cli import build_parser

def walk(parser, path, cmds, flags):
    for a in parser._actions:
        flags.update(s for s in a.option_strings if s.startswith("--"))
        if a.__class__.__name__ == "_SubParsersAction":
            for name, sub in a.choices.items():
                cmds.append(" ".join(path + [name]))
                walk(sub, path + [name], cmds, flags)

cmds, flags = [], set()
walk(build_parser(), [], cmds, flags)
print(len(cmds), len([c for c in cmds if " " not in c]), len(flags))
```

`uv run python <script>` prints `42 27 72`. The configuration counts are read from the key lists in
`src/taskrail/config.py` (`_config` for the first-level tables, `_autopilot` for `[autopilot]`).

## Follow-ups

Proposed, not opened: the decision is escalated to the human, and these tasks only make sense once
it is accepted.

| Kind | Title | What it does |
|---|---|---|
| `chore` | Record the scope, reach and refusal rules for the design principles in CLAUDE.md | Adds the prospective sentence, replaces "the plan gate" with the four first-gate stage names, and states that an executor objects rather than refusing and never substitutes a design silently. `CLAUDE.md` only. |
| `chore` | Tell every executor to read the repository's agent instruction files before it plans | Generalises `taskrail-chore`'s existing line into the core `taskrail` skill, names no principle and no agent, and runs `upgrade` for the installed copies. Skip this task if option 2C is preferred. |
| `chore` | Correct T088's row with the measured CLI and configuration surface | Replaces "18 subcommands, about 66 distinct flags and 19 first-level config keys" with the figures of E9, through `taskrail edit`. |
