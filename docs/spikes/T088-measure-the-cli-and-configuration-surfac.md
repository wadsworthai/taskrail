# T088 — Measure the CLI and configuration surface against YAGNI and report what has no consumer

**Verdict** — *(pending: written at the `decide` stage)*

*Status: `frame` stage draft. The evidence and the verdict are written at `investigate` and
`decide`.*

## Question

taskrail's command-line and configuration surface is large for a tool with one visible consumer.
The task asks: **for each option in that surface, who consumes it, and what would removing it or
fixing it at a default cost a repository that installed 0.3.0?**

The task row's own figures are wrong and are not used here. T087 re-measured the surface from the
live `argparse` tree and the autopilot orchestrator reproduced the command counts independently;
**the row's figures are superseded by T087 and are corrected by T092** (`chore`, open, not this
task's work — this task must not edit the row). The measured surface is:

- **27 top-level commands**, **42 commands counting every subcommand level** (exact, reproduced
  independently);
- **about 70 distinct long flags** — the figure moves by a unit or two with the counting method,
  so this document states its method with the count;
- **9 first-level names** in `.taskrail/config.toml` — `version`, `[[backlog]]`, `[columns]`,
  `[points]`, `[git]`, `[review]`, `[kinds]`, `[checks]`, `[autopilot]` — holding **about 42
  documented keys**, with `[checks]` a free-form map and `[[autopilot.group]]` /
  `[[autopilot.resource]]` repeatable tables.

The row names five suspects: `claim_remote`, `branch_record_remote`, `[[autopilot.resource]]`,
`[[autopilot.group]]` and `[autopilot].notify`. They are a starting point to verify, not the
answer: the investigation measures the whole surface and reports what it finds, whether or not it
matches that list.

### What this task is not

Bound by the verdict of [T087](T087-decide-whether-the-design-principles-gov.md), accepted by the
human on 2026-09-18:

- **The design principles are prospective.** They judge the change a task makes, not the code that
  already exists. **This task's verdict does not license removing anything.** It measures and
  reports; each finding becomes a task, and each such task is then judged on its own merits as a
  prospective change.
- **"No known consumer" is the strongest claim available.** This repository is public and the
  publishing constraint in `CLAUDE.md` keeps private consumers out of the write-up. Where the
  investigation finds nothing, it says *no consumer visible in this repository* — never *no
  consumer*.
- The task row says **change nothing**: no code, no configuration, no skills, no `DESIGN.md`, and
  not the task row itself.

## Evidence

*(written at the `investigate` stage)*

What would answer the question, per option in the surface:

1. **Its consumers, by class.** Not a yes/no but a ladder, weakest last:
   - **C1 — used by this repository**: set in `.taskrail/config.toml`, or invoked by the shipped
     skills, the autopilot lane brief, or this repository's own workflow.
   - **C2 — seeded by `init`**: written into a fresh consumer's config by `install.py`, so every
     installation has it whether or not anyone chose it. Evidence of what an install actually sets.
   - **C3 — documented for a consumer**: described in `DESIGN.md` §4 (configuration), §7 (the CLI)
     or `README.md`, and reachable by a consumer who reads the documentation, but set nowhere here.
   - **C4 — exercised only by its own test**: `tests/` covers it and nothing else does. *An option
     with a test but no user is still an option with no user*; the report separates C4 from C1-C3
     for exactly that reason.
   - **C5 — nothing but the implementation**: no config, no skill, no seed, no test, no prose
     beyond the key list.
2. **The cost of removing it, and the cost of defaulting it** (keeping the behaviour but dropping
   the option), for a repository that installed 0.3.0: whether the change is silent or loud,
   whether `taskrail validate` or `load_config` would reject an existing config, and whether any
   recovery exists.
3. **A recommendation** per option: keep / default / propose for removal in a follow-up task /
   leave until a second consumer exists.

## Approach

All measurement in this task's worktree, branch `T088-measure-the-cli-and-configuration-surfac`,
base `origin/T087-decide-whether-the-design-principles-gov` = 4513736. Every command and its real
output goes in the write-up, so a reader can recount.

1. **Enumerate mechanically, not by reading.** Walk the live `argparse` tree from
   `taskrail.cli.build_parser()` for the commands and long flags, and the dataclass field lists in
   `src/taskrail/config.py` (`Config`, `BacklogConfig`, `ReviewConfig`, `AutopilotConfig`,
   `GroupConfig`, `ResourceConfig`) plus the parsing in `load_config` for the configuration keys.
   The throwaway script lives in the session scratchpad, outside the repository, and is reproduced
   verbatim in *How to reproduce*.
2. **Classify each item by grep over the named consumers**, in this order: this repository's
   `.taskrail/config.toml`; the config template `install.py` writes on `init`; the shipped skills
   under `src/taskrail/skills/` and the integration notes; `.claude/` (the installed copies and any
   lane material); `tests/`; `DESIGN.md` and `README.md`. Each classification cites the grep that
   produced it.
3. **Cost each weak-class item** by reading what `load_config` does with an unknown key and what
   the option's absence changes at run time — measured where it can be measured (an actual
   `taskrail validate` against a config that sets it) rather than argued.
4. **Report, in two layers.** A full table of every measured item with its class, so the count is
   auditable; then a per-option section — consumers, cost of removing, cost of defaulting,
   recommendation — for every item in the weak classes (C4 and C5) and for anything in C2/C3 whose
   only consumer is the seed or the prose.
5. **Turn the findings into tasks, not edits** — see the open decision below.

## Limits

- **Time box: this task's 3 points, one pass over the surface.** If classification of the full
  ~110 items runs long, the full table is completed first (it is what makes the count auditable)
  and the per-option detail is written for the weak classes only, with the rest listed by class.
- **The report does not remove, default, rename or deprecate anything**, and does not edit
  `TODO.md` beyond this task's own rows through the CLI. No code, no `DESIGN.md` (T089's subject),
  no skills, no `CLAUDE.md`.
- **Private consumers are invisible and stay invisible.** The publishing constraint forbids naming
  them, so no finding can be stronger than *no consumer visible in this repository*. Any
  recommendation that would remove an option is therefore a recommendation to *open a task* that
  asks the human, who can see the private consumers, not a recommendation to remove.
- **Git history is evidence of intent, not of use.** A commit that added an option says why it was
  added; it does not say whether anyone set it afterwards. History is used to date an option and to
  find whether a consumer was ever named, and its limits are stated where it is used.
- **The kind descriptors' own surface** (`kinds/*.toml` keys, stage fields) is measured only where
  it is reachable from `.taskrail/config.toml` or the CLI. A repository-local kind file is a
  consumer-authored document, not an option this repository ships to be set.

## Options considered

*(written at the `decide` stage)*

## Recommendation

*(written at the `decide` stage)*

## What would change the decision

*(written at the `decide` stage)*

## How to reproduce

*(written at the `investigate` stage, with the exact commands and the throwaway script)*
