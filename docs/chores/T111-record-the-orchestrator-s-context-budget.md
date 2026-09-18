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

Proposed addition:

> **The orchestrator's context bounds a run, not compaction** (*measured, T057*). A lane is
> short-lived and ends with its task; the orchestrator accumulates every lane's report, every gate
> answer and every hand-off, so it is the session that fills up. Across the nine runs
> [T057](../../docs/spikes/T057-check-autopilot-compaction-and-old-lane.md) harvested, no
> orchestrator session and none of the 38 lanes measured had ever compacted — the lanes peaked
> between 78,404 and 355,752 tokens — while the two long runs cost 36,728 and 44,343 tokens of
> orchestrator context per dispatched task, over a session overhead of 32,000–39,000: **roughly 21
> to 26 tasks for a 1M-context orchestrator**. So a count is chosen against that budget, and a
> backlog longer than one session's worth goes to a fresh session through the resume path (§12.3)
> rather than being left to compaction. Nothing enforces it: `count` (§12.7) caps what a run
> starts, and judging it against the context is the orchestrator's, in the skill's prose. **The
> figures are one agent's and one model's** — Claude Code on a single 1M-context model, in this
> repository's own runs — and the band scales with the window: the same rate against 200k would be
> four or five tasks. What carries to another agent is the shape, not the number.

### 2. `src/taskrail/skills/taskrail-autopilot/SKILL.md` — a new paragraph in *When to run*

Placed after step 4 of the numbered list and before the paragraph about `extend`, so it sits
between "how to start a run" and "how to grow one". It names no agent and no model, which
`tests/test_autopilot_skill.py::test_portable_text_names_no_agent_or_agent_tool` enforces on this
file.

Proposed addition:

> **Plan the count against your own context.** A lane ends with its task; you accumulate every
> lane's report, every gate answer and every hand-off, so your session is the one that fills up —
> and that, not compaction, is what bounds a run. Measure the cost once for your agent and model.
> This repository's own runs cost their orchestrator about 37,000–44,000 tokens per dispatched task
> over a 32,000–39,000 session overhead, which is roughly 21 to 26 tasks in a 1,000,000-token
> context, while no lane came near its own limit: 38 lanes peaked between 78,000 and 356,000 tokens
> and not one compacted. **Those figures are one agent's and one model's**, so treat them as an
> order of magnitude rather than a rule — yours differ, and the band scales with the context
> window. When the human asks for more tasks than your session holds, say so and propose the count
> you can hold; the rest goes to a fresh session through *Resume a run*, which is the planned path
> for a long backlog and not only a recovery from a lost session.

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
| `src/taskrail/integrations/claude.md` | See decision 1: it is a real option for the figures, and the recommendation is against it. |
| `references/lane-brief.md`, `references/gate-review.md` | A lane neither chooses nor reviews a count. |
| `README.md` *Autopilot* | Six lines that say what the skill is and that the human gives a count; sizing guidance does not belong at that altitude. |
| `CLAUDE.md` *Backlog* | It records that the autopilot is enabled here; no count is chosen in it. T108 also owns a line in it. |

## Decisions needed

1. **Where do the measured figures live: inline in `SKILL.md` with the caveat, or in the Claude
   Code integration note with only the portable rule in `SKILL.md`?**
   *Recommendation: inline in `SKILL.md`, with the caveat, as the change set above has it.*
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
   backlog longer than one session?**
   *Recommendation: no.* The new *When to run* paragraph already ends with that pointer, and a
   second statement of it in the section it points at is duplication for its own sake. If you would
   rather the reader arriving at *Resume a run* see it there too, say so and it becomes one
   sentence.

3. **Is the observation from this very run worth recording?** The orchestrator of run `20260918-1`
   reports that it dispatched roughly twenty lanes before its context compacted, which falls inside
   T057's predicted 21–26 band.
   *Recommendation: no.* This lane cannot verify it, T057's artifact already records `20260918-1`
   at 914,741 tokens after 21 dispatches, and an unverifiable second-hand number in `DESIGN.md`
   would weaken a paragraph whose whole force is that its figures are reproducible from a stated
   method. It belongs in this run's decision record if anywhere.

## Out of scope

- Any code, configuration, CLI or test change. `uv run pytest` is run as the stage's check, not
  extended.
- `DESIGN.md` §12.3 (T112), §4 (T110), §§3.1/7/7.4 and the new §7.6 (T107), `.github/workflows/`
  and the `CLAUDE.md` *Layout* line (T108).
- Re-measuring anything. Every figure is quoted from T057's artifact and decision record.
- Harvesting a run that has actually compacted — proposal C at T057's decide gate, which the human
  did not open.

## Verification

1. `taskrail checks T111` — `uv run pytest -q`, the whole suite, which includes
   `tests/test_autopilot_skill.py` (the portable text names no agent; the installed copy equals the
   source plus the integration note; the manifest digests match) and `tests/test_install.py`.
2. After `upgrade`: `grep -n "Plan the count against your own context"
   .claude/skills/taskrail-autopilot/SKILL.md` must find the new paragraph in the **installed**
   copy, and `diff` of the installed copy against the source must show only the `## On Claude Code`
   note.
3. `taskrail validate` — the backlog stays valid.
4. Read the two changed paragraphs in place, in their sections, to check they read as part of the
   surrounding text and that every number matches the table at the top of this document.

*Results are recorded here at the implement stage.*
