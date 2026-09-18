# T087 — Decide whether the design principles govern new work only or also what exists

**Verdict:** pending — this document is at the `frame` stage.

## Question

`CLAUDE.md` gained a `## Design principles` section in commit 5476c00 (PR #20): KISS, YAGNI, the
rule of three, Occam's razor and "premature optimization is the root of all evil". The section
says the principles "govern the CLI, the skills and the work planned in the backlog", but not
what that means for code and options written before the section existed. Three sub-questions
make up the decision:

1. **Scope.** Are the principles prospective (they judge the change a task makes) or also
   retroactive (they judge what the repository already has, so an agent may propose removals as
   part of unrelated work)?
2. **Reach.** Where does an executor read them? Today only the always-loaded root file states
   them; the executor skills (`taskrail-feature`, `taskrail-bug`, `taskrail-chore`,
   `taskrail-spike`) do not mention design principles at all, and the autopilot lane brief names
   the governing documents without naming the principles. Is the root file enough, or must the
   shipped skills and the lane brief name them?
3. **Refusal.** May an executor refuse, at the plan gate, a design the task's own description
   asks for, on the strength of a principle? If so, how is that escalated — and how does it
   interact with the autopilot, where the orchestrator answers gates and the human sees the
   result only at the pull request?

## Evidence that would answer it

- The exact text of the principles at the base commit, and how it compares with the other rules
  in `CLAUDE.md` (language policy, publishing constraint, agent portability, merging): which are
  machine-checkable and which are prose the agent must apply by judgement.
- What each executor skill's plan/scope stage already says about disagreeing with a task's
  description, and whether a refusal path already exists under another name.
- What the autopilot does with a lane's objection today: the gate-review reference, the
  escalation list in `taskrail-autopilot/SKILL.md`, and `escalate_gates` in
  `.taskrail/config.toml`.
- The cost of the reach options: `src/taskrail/skills/` is the portable core (DESIGN.md §8), so
  anything added there ships to every consumer repository, whose principles are not this
  repository's. `CLAUDE.md` is repository-local and ships to nobody.
- The size of the retroactive surface, to see what a retroactive reading would license: the CLI's
  subcommand and flag count, the config key count, and the options that exist for a single or
  hypothetical consumer (`claim_remote`, `branch_record_remote`, autopilot resource pools and
  groups, `notify`). These were measured on main and are re-verified here before being relied on.
- How E08's other two tasks (T088, T089) are framed, since both depend on this verdict.

## Approach

1. Re-read the principles section and the rest of `CLAUDE.md` at the base commit; classify each
   rule as checkable or judgement-based.
2. Grep the shipped skills and the autopilot references for the existing vocabulary of
   disagreement (plan gate, scope stage, "stop and ask", decisions) to find where a refusal would
   already land.
3. Re-verify the measured facts about the CLI and configuration surface with commands recorded
   verbatim, so T088 can reuse or correct them.
4. Write up the options for each of the three sub-questions with their costs, and recommend one
   of each, in terms T088 (YAGNI applied to the existing surface) and T089 (splitting DESIGN.md)
   can build on directly.

## Limits

- **Time box:** one working session; 2 points.
- This spike **decides, it does not adopt.** It edits no `CLAUDE.md`, no skill under
  `src/taskrail/skills/` and no code. Whatever the verdict implies becomes follow-up tasks.
- It does not audit the CLI surface against YAGNI — that is T088. It only measures enough to say
  what a retroactive reading would put in scope.
- It does not decide anything about DESIGN.md's structure — that is T089.
- It settles the policy for **this repository**. Whether taskrail should ship a principles
  mechanism to consumers is considered only as a cost, and is out of scope as a design.

## Files this task will touch

- `docs/spikes/T087-decide-whether-the-design-principles-gov.md` (this artifact)
- `docs/spikes/README.md` (index row)
- `TODO.md` (through the CLI only: the status cell on close, and any follow-up rows)
