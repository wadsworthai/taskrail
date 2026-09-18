# T111 — Record the orchestrator's context budget where a run's count is chosen

Documentation only. No code, no configuration, no new test.

## Goal

A run's count is chosen today with no idea of its ceiling.
[T057](../spikes/T057-check-autopilot-compaction-and-old-lane.md) measured that ceiling and it is
the orchestrator's context, not compaction. Write the finding where the count is chosen — `DESIGN.md`
§12 and the `taskrail-autopilot` skill — with its consequence (a backlog longer than one session's
worth goes to a fresh session through the resume path) and with the caveat the finding carries: the
figures are one agent's and one model's.

### The figures, quoted from T057

From `docs/spikes/T057-check-autopilot-compaction-and-old-lane.md`, E1 and E2, and the one-line
finding in `docs/autopilot/decisions/T057-check-autopilot-compaction-and-old-lane.md`:

| | |
|---|---|
| Orchestrator context per dispatched task, the two long runs | **36,728** (21 tasks) and **44,343** (8 tasks) |
| Session overhead before any task | 32,000–39,000 |
| Tasks a 1M-context orchestrator holds | **21 to 26** |
| Lane peaks, 38 lanes over nine runs | 78,404 – 355,752 |
| Compaction boundaries, orchestrators and lanes alike | **0** |
| Provenance | one agent (Claude Code) on one 1M-context model, this repository's own runs |

## Change set

**Amended at the scope gate: the rule and the figures are split.** Decision 1 below was answered
against the recommendation, and the answer is the better one. The portable `SKILL.md` may not name
an agent or a model — `tests/test_autopilot_skill.py::test_portable_text_names_no_agent_or_agent_tool`
enforces it — so a figure placed there can only appear stripped of the one thing that makes it
meaningful, whose it is and on what. "One agent's and one model's" is a disclaimer, not a
provenance, and an unattributed number is read as taskrail's sooner or later, which is what
CLAUDE.md's *Agent portability* section exists to prevent. What every agent must **do** is
identical, so the rule stays in `SKILL.md` carrying no numbers; the figures go where they can be
attributed — `DESIGN.md` §12.1 and the Claude Code integration note. Decisions 2 and 3 were
answered as recommended.

### 1. `DESIGN.md` §12.1 — a new paragraph after the one that says where a count comes from

`§12.1` is the only place in `DESIGN.md` where a count is *chosen* rather than *applied*: the
paragraph below states that the human gives a count, and is already a statement about the skill's
judgement rather than a CLI guarantee, which is exactly the character of this finding. The new
paragraph goes immediately after it, before **Rows on their task's branch**.

Current text, `DESIGN.md:1377-1380`, unchanged:

> The autopilot runs only when the human asks for it and gives a task count or names the tasks, and
> a run is extended only on the human's request. The skill states this in its prose, not only in
> frontmatter, so the rule holds on agents that ignore invocation-control keys (*implemented, T024;
> named tasks and `extend`, T071*).

Added (`DESIGN.md:1382-1396`). It names Claude Code, since it may, and links T057 root-relative, as
`DESIGN.md:1820` does — the scope gate caught a `../../docs/…` link in the proposal, which would not
resolve from a file at the repository root:

> **The orchestrator's context bounds a run, not compaction** (*measured, T057; recorded, T111*). A
> lane is short-lived and ends with its task; the orchestrator accumulates every lane's report,
> every gate answer and every hand-off, so it is the session that fills up. Across the nine runs
> [T057](docs/spikes/T057-check-autopilot-compaction-and-old-lane.md) harvested, no orchestrator
> session and none of the 38 lanes measured had ever compacted — the lanes peaked between 78,404
> and 355,752 tokens — while the two long runs cost 36,728 and 44,343 tokens of orchestrator
> context per dispatched task, over a session overhead of 32,000–39,000: **roughly 21 to 26 tasks
> for a 1M-context orchestrator**. So a count is chosen against that budget, and a backlog longer
> than one session's worth goes to a fresh session through the resume path (§12.3) rather than
> being left to compaction. Nothing enforces it: `count` (§12.7) caps what a run starts, and
> judging it against the context is the orchestrator's, in the skill's prose. **Those figures are
> one agent's and one model's** — Claude Code on a single 1M-context model, in this repository's
> own runs — and the band scales with the window: the same rate against 200k would be four or five
> tasks. So the skill states the rule without them, and the measured constants live in the Claude
> Code integration note (§8), where they can say whose they are. What carries to another agent is
> the shape, not the number.

### 2. `src/taskrail/skills/taskrail-autopilot/SKILL.md` — a new paragraph in *When to run*

Placed after step 4 of the numbered list and before the paragraph about `extend`, so it sits
between "how to start a run" and "how to grow one". **The rule, carrying no figures**: it names no
agent, no model and no constant, so nothing in it can be read as a measurement of taskrail's.

Added (`SKILL.md:39-45`):

> **Plan the count against your own context.** A lane ends with its task; you accumulate every
> lane's report, every gate answer and every hand-off, so your session is the one that fills up —
> and that, not compaction, is what bounds a run. Measure the cost once for yourself: the context
> you are served per dispatched task, over what a session costs before any task starts, against the
> context window you have. That is how many tasks you hold. When the human asks for more than that,
> say so and propose the count you can hold; the rest goes to a fresh session through *Resume a
> run*, which is the planned path for a long backlog and not only a recovery from a lost session.

### 2b. `src/taskrail/integrations/claude.md` — the figures, attributed

Appended to the `taskrail-autopilot` section (the `<!-- taskrail:skill taskrail-autopilot -->`
marker at line 22), so the agent that produced the measurement reads it in its own installed copy of
the skill, right where the rule is. The same rule everywhere, the measured constant only where it
applies.

> - **A measured figure for *Plan the count against your own context*.** Nine autopilot runs of
>   taskrail's own repository were harvested on Claude Code, all on one 1M-context model: the two
>   long runs cost their orchestrator 36,728 and 44,343 tokens of context per dispatched task, over
>   a session overhead of 32,000–39,000 — **roughly 21 to 26 tasks in a 1M context**. Lanes were
>   never the constraint: 38 of them peaked between 78,404 and 355,752 tokens, and neither they nor
>   any orchestrator ever compacted. Start from that band, and measure your own if your model or
>   your window differs — the band scales with the window, so the same rate against 200k is four or
>   five tasks.

### 3. `CHANGELOG.md` — one bullet under *Unreleased*

The skill ships to consumers, so its text changing is user-facing, as it was for T104. Appended,
one of the known conflict classes.

### 4. The installed copies

`.claude/skills/taskrail-autopilot/SKILL.md` and `.taskrail/installed.json`, regenerated by running
**this worktree's own** `.taskrail/bin/taskrail upgrade` from inside this worktree, then grepped to
confirm the new text is in the installed copy.

### 5. This artifact and `docs/chores/README.md`

One index row, appended.

## Places considered and rejected

| Place | Why not |
|---|---|
| `DESIGN.md` §12.7 *Resources* | It enumerates what the CLI enforces — `max_lanes`, `count`, groups, resources — and is headed *Implemented (T030) by `autopilot next`*. A limit nothing enforces would misread there. §12.1's new paragraph points at `count` in §12.7 instead. |
| `DESIGN.md` §12.3 | T112 owns it, and it is about orchestrator and lane mechanics, not about choosing a count. The new paragraph only cross-references it. |
| `DESIGN.md` §12.9 *Configuration* / a new `[autopilot]` key such as `max_tasks_per_session` | YAGNI and KISS: a documented convention beats a mechanism, and the CLI cannot know a number that is one agent's and one model's. |
| A warning from `autopilot start --count N` above some N | Same reason, plus it would put an agent-specific constant in an agent-agnostic CLI — the reason T057's harvest script was kept out of the repository. |
| `src/taskrail/integrations/claude.md` | **Not rejected in the end** — decision 1 put the figures here. See the amendment at the top of the change set. |
| `references/lane-brief.md`, `references/gate-review.md` | A lane neither chooses nor reviews a count. |
| `README.md` *Autopilot* | Six lines that say what the skill is and that the human gives a count; sizing guidance does not belong at that altitude. |
| `CLAUDE.md` *Backlog* | It records that the autopilot is enabled here; no count is chosen in it. T108 also owns a line in it. |

## Decisions, as answered at the scope gate

1. **Where do the measured figures live: inline in `SKILL.md` with the caveat, or in the Claude
   Code integration note with only the portable rule in `SKILL.md`?**
   **Answered: split them — the rule in `SKILL.md` without numbers, the figures in `DESIGN.md`
   §12.1 and in `src/taskrail/integrations/claude.md`. Against the recommendation below, and
   correctly so**, for the reason recorded at the top of the change set: the portable file's own
   test forbids it from naming the agent and the model, so a figure there cannot carry its
   provenance, and a number that cannot say whose it is is eventually read as taskrail's.
   *Recommendation, not taken: inline in `SKILL.md`, with the caveat.*
   CLAUDE.md's *Agent portability* section reserves the integrations for agent-specific
   **behaviour**; what the orchestrator must *do* here — measure its own cost, plan the count
   against it, resume rather than compact — is identical on every agent, so the rule belongs in the
   portable text. A figure carrying its own provenance is a hint, not a guarantee, and it is what
   makes the rule actionable: another agent can compare its measured per-task cost against a known
   one. The caveat names no agent and no model, which the portable file's test requires anyway.
   *Alternative:* move the numbers to `src/taskrail/integrations/claude.md`, leaving `SKILL.md`
   saying only "measure it for yourself". Cleanest reading of the portability rule, but it strands
   the rule without an anchor and the figures where only one agent ever sees them, while `DESIGN.md`
   would carry them regardless.

2. **Also add a clause to the skill's *Resume a run* section saying it is the planned path for a
   backlog longer than one session?** **Answered: no**, as recommended — the new *When to run*
   paragraph already ends on that pointer, and restating it in the section it points at is
   duplication for its own sake.

3. **Is the observation from this very run worth recording?** The orchestrator of run `20260918-1`
   reports that it dispatched roughly twenty lanes before its context compacted, which falls inside
   T057's predicted 21–26 band. **Answered: not in the shipped text**, as recommended — this lane
   cannot verify it, T057's artifact already records `20260918-1` at 914,741 tokens after 21
   dispatches, and an unverifiable number beside a paragraph whose whole force is reproducibility
   weakens it. The orchestrator recorded it in this task's decision record instead.

## Out of scope

- Any code, configuration, CLI or test change. `uv run pytest` is run as the stage's check, not
  extended.
- `DESIGN.md` §12.3 (T112), §4 (T110), §§3.1/7/7.4 and the new §7.6 (T107), `.github/workflows/`
  and the `CLAUDE.md` *Layout* line (T108).
- Re-measuring anything. Every figure is quoted from T057's artifact and decision record.
- Harvesting a run that has actually compacted — proposal C at T057's decide gate, which the human
  did not open.

## Verification

**1. `upgrade`, run from inside this worktree with this worktree's own wrapper**, which is the step
that matters here: the primary checkout's wrapper would have installed *its* sources and silently
dropped this task's change from the installed copy.

```
$ pwd
/thezone/shared/repositories/utils/taskrail/.worktrees/T111-record-the-orchestrator-s-context-budget
$ .taskrail/bin/taskrail upgrade
updated   .claude/skills/taskrail-autopilot/SKILL.md
note      skills changed: restart the agent session so it loads them
11 file(s) already up to date
```

**2. Both new texts are in the installed copy**, the rule and the attributed figure:

```
$ grep -n 'Plan the count against your own context' .claude/skills/taskrail-autopilot/SKILL.md
39:**Plan the count against your own context.** A lane ends with its task; you accumulate every lane's
299:- **A measured figure for *Plan the count against your own context*.** Nine autopilot runs of
$ grep -n 'A measured figure for' .claude/skills/taskrail-autopilot/SKILL.md
299:- **A measured figure for *Plan the count against your own context*.** Nine autopilot runs of
```

`diff .claude/skills/taskrail-autopilot/SKILL.md src/taskrail/skills/taskrail-autopilot/SKILL.md`
differs only where it should: the source's `<!-- taskrail:harness -->` against the installed copy's
`## On Claude Code` section, the new bullet included. `.taskrail/installed.json` was updated with
the new digest.

**3. The suite**, `taskrail checks T111 --stage implement`:

```
== test: uv run pytest -q
[…]
1221 passed in 172.24s (0:02:52)
== lint: not configured
passed test
not configured lint
T111 in …/.worktrees/T111-record-the-orchestrator-s-context-budget: passed
```

`lint` **is not configured** in this repository — the stage lists it, the config defines only
`test`, and `checks` reports it rather than failing. The suite covers what this change could break:
`tests/test_autopilot_skill.py::test_portable_text_names_no_agent_or_agent_tool` (the portable
`SKILL.md` names no agent or model — it passes because the new paragraph carries no numbers and no
names), the tests that assert the installed copy equals the source with each integration's notes
substituted, and the manifest-digest tests in `tests/test_install.py`.

**4. `taskrail validate`:** `101 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.

**5. Read in place.** Both paragraphs were read in their sections after the edit. The
`DESIGN.md` link `docs/spikes/T057-check-autopilot-compaction-and-old-lane.md` resolves from the
repository root (`test -f` passes). Every figure in `DESIGN.md` and in the integration note matches
the table at the top of this document, which was quoted from T057's artifact; the skill's rule
carries none to match.
