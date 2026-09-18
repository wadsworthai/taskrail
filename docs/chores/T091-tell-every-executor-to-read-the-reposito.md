# T091 — Tell every executor to read the repository's agent instruction files before it plans

Kind: chore · Epic: E08 · Status: scoped

## Goal

Adopt sub-question 2 of T087's verdict, accepted by the human on 2026-09-18: the design principles
stay in the repository's own instructions, and the portable core gains **one generic pointer** so
that every kind's executor — not only `chore` — reads those instructions before it plans.

Today the pointer exists once, in `taskrail-chore`'s `scope` stage
(`src/taskrail/skills/taskrail-chore/SKILL.md:24-25`), and nowhere else:

```
$ grep -rn "agent instruction" src/taskrail/skills/ src/taskrail/integrations/
src/taskrail/skills/taskrail-chore/SKILL.md:25:   agent instruction files.
```

`taskrail-feature`, `taskrail-bug`, `taskrail-spike` and the core `taskrail` skill have none, so on
an agent that does not load a root instruction file by itself, three kinds in four never look at
what the repository asks of them. That is the hole T087 E7 measured and what this chore closes.

The line ships to every repository that installs taskrail, so it **names no principle and no
agent**: no KISS or YAGNI (those are this repository's taste, not the tool's), no agent name and no
file name, and it must read sensibly in a repository that has no such file at all. `CLAUDE.md`'s
*Agent portability* section and `DESIGN.md` §8 govern: `src/taskrail/skills/` is the portable core,
agent-specific text lives in `src/taskrail/integrations/`, and "the portable text names no agent".

## Change set

| File | Change |
|---|---|
| `src/taskrail/skills/taskrail/SKILL.md` | One sentence added at the start of step 5, **Stages**, of *Working a task* (decisions 1 and 2 fix the wording and the place). Nothing else in the file changes. |
| `tests/test_skills_current_branch.py` | One test that the sentence is in the `Stages` step of the source **and** of both installed copies, and that it names no agent and no agent-specific file (decision 4). |
| `.claude/skills/taskrail/SKILL.md` | Rewritten by `.taskrail/bin/taskrail upgrade`, never by hand: the installed copy of the source above, with this repository's Claude Code notes re-inserted at the harness marker. |
| `.taskrail/installed.json` | Rewritten by the same `upgrade`: the digest recorded for `.claude/skills/taskrail/SKILL.md`. |
| `CHANGELOG.md` | One bullet under `## Unreleased` (decision 5). |
| `TODO.md` | Through the CLI only: T091's row with `taskrail done` at the close. No row or table is edited by hand. |
| `docs/chores/T091-tell-every-executor-to-read-the-reposito.md` | This artifact. |
| `docs/chores/README.md` | One appended row for it. |

### The sentence, as proposed

`src/taskrail/skills/taskrail/SKILL.md` step 5 begins today:

```
5. **Stages.** Take `kind_descriptor.stages` in order. Skip a stage whose `applies` is false: its
   column does not match this task.
```

Proposed (the added sentence is the first one; the rest of the step is untouched):

```
5. **Stages.** Before the first stage, read the repository's own agent instruction files, if it
   has any, and follow what they ask of the work you are about to do. Take
   `kind_descriptor.stages` in order. Skip a stage whose `applies` is false: its column does not
   match this task.
```

Why this wording:

- **"the repository's own agent instruction files"** is the phrase `taskrail-chore` already uses, so
  the core generalises an existing habit rather than inventing vocabulary.
- **"if it has any"** makes the line true in a repository with no such file: there is nothing to
  read and nothing to obey. Without it, the line implies every repository has one.
- **"Before the first stage"** is "before it plans" stated without a stage name: the first stage is
  `plan` for `feature`, `scope` for `chore`, `diagnose` for `bug` and `frame` for `spike`, and
  naming one of them would bind one kind in four — the same mistake T087 E6 found in `CLAUDE.md`'s
  "the plan gate".
- It states a **habit, not a policy**: read what the repository asks. It names no principle, no
  agent, no file name, and no repository layout, so it is portable under `DESIGN.md` §8.

### Why step 5, and why not a new section

`DESIGN.md` §8 fixes the core skill's procedure as nine steps — "identify, inspect, workspace,
claim, stages, scope, artifact, close, hand off". Adding a sentence inside step 5 leaves that list
true, so `DESIGN.md` needs no change; a tenth step or a new section would make §8 wrong and widen
this chore into the design document. Step 5 is also where the executor stops preparing and starts
working: steps 1–4 are the task's own metadata, the workspace and the claim, and step 5 is the
first that runs a stage — the planning one.

## Decisions needed

1. **The wording.** Recommended, as quoted above: *"Before the first stage, read the repository's
   own agent instruction files, if it has any, and follow what they ask of the work you are about to
   do."* Alternatives: (a) drop "if it has any" and say "…, where the repository has them, …";
   (b) end at "and follow them", which is shorter but loses that they bind the work, not the reader;
   (c) say "instructions for the agents that work in it" instead of "agent instruction files", which
   avoids implying a file but breaks the phrase `taskrail-chore` already uses.
2. **The place.** Recommended: the first sentence of step 5, **Stages**. Alternatives: (a) the end
   of step 4, **Claim**, which keeps step 5 purely about the stage machinery but attaches the line to
   a step about claiming; (b) step 2, **Inspect**, which is about reading `taskrail show`, that is,
   the task rather than the repository; (c) a new short section, refused above because it makes
   `DESIGN.md` §8's list of steps wrong.
3. **`taskrail-chore`'s existing line.** Recommended: **leave it unchanged**. It reads "the
   conventions of the area you will touch: nearby code, its README, the repository's agent
   instruction files" — area conventions at `scope` time, of which the instruction files are one
   item; the core line is the repository-wide habit before any kind plans. The overlap is one clause
   and the diff stays in one skill. Alternative: delete the clause from `taskrail-chore` so the
   instruction files are named once, which removes a duplication but edits a second shipped skill
   and weakens `chore`'s list for no measured gain.
4. **The test.** Recommended: one test in `tests/test_skills_current_branch.py`, whose `skill_copy`
   fixture already reads each shipped skill from the source and from both integrations' installed
   copies, so the assertion covers what consumers receive as well as the source:

   ```python
   def test_the_stages_step_reads_the_repositorys_instructions_first(skill_copy):
       """T091: every kind's executor reads the repository's instructions before the first stage."""
       text = step(skill_copy("taskrail/SKILL.md"), "5. **Stages.**", "6. **Scope.**")
       assert "before the first stage, read the repository's own agent instruction files" in text
       for word in ("claude", "opencode", "agents.md", "kiss", "yagni"):
           assert word not in text, word
   ```

   That module is titled for T084, so the test is a guest there. Alternatives: (a) a new
   `tests/test_skills_repo_instructions.py` holding this one test, which costs a module and a
   fixture import for a single assertion; (b) no test at all, relying on
   `test_the_portable_core_skill_asks_before_a_push_without_the_agent_notes`, which already fails if
   the core skill's portable body names `Claude`, `OpenCode`, `AskUserQuestion` or `subagent` — it
   protects the "names no agent" half, but nothing asserts the line exists or reaches the installed
   copies.
5. **CHANGELOG.** Recommended: one bullet under `## Unreleased`, since the line ships to every
   consumer at the next release and 0.3.0's entries record skill-text changes the same way.
   Alternative: no entry, treating it as an internal editorial change — which T086 did for a change
   that consumers never see, unlike this one.
6. **Pull request title.** Recommended:
   `docs(skills): tell every executor to read the repository's instructions before it plans (T091)`,
   made with `--type docs --scope skills`. Alternative: `--type chore`, which the kind defaults to
   but which undersells a change to shipped skill text.

## Out of scope

- **`CLAUDE.md`.** T090 adopts sub-questions 1 and 3 there, in the same run; this task does not open
  that file.
- **Naming the principles anywhere in `src/taskrail/skills/`.** Refused by the human's answer to
  sub-question 2 and by `DESIGN.md` §8.
- **`taskrail-feature`, `taskrail-bug`, `taskrail-spike` and `taskrail-autopilot`.** The decision
  puts one line in the core skill precisely so the four executor skills need no line of their own.
  `taskrail-chore` is touched only if decision 3 goes the other way.
- **`DESIGN.md`**, `README.md` and the integration notes: the nine-step procedure, the integrations
  table and the "portable text names no agent" rule all stay true as written.
- **The lane brief** (`src/taskrail/skills/taskrail-autopilot/references/lane-brief.md`), which
  already tells a lane to follow "the repository's own agent instructions".
- **Re-opening T087's verdict**, the reach question or the figures in T088's row (that is T092).
- Editing any installed copy under `.claude/skills/` by hand, and any `init`/`upgrade` in a
  repository other than this worktree.

## Verification

At the implement stage, all inside this worktree:

1. `git diff` on `src/taskrail/skills/taskrail/SKILL.md` shows the one added sentence and nothing
   else.
2. `.taskrail/bin/taskrail upgrade` rewrites `.claude/skills/taskrail/SKILL.md` and
   `.taskrail/installed.json`; its report is recorded, and `git diff` shows the same sentence in the
   installed copy, with the `## On Claude Code` notes still in place, and only the digest changed in
   `installed.json`.
3. A second `.taskrail/bin/taskrail upgrade` changes nothing (idempotence), and `git status` is
   clean of it.
4. The new test is observed **failing** against the unchanged skill text first, then passing.
5. `taskrail checks T091 --stage implement` runs `test` (`uv run pytest -q`); `lint` is not
   configured in this repository. The full suite is run and its count recorded.
6. `.taskrail/bin/taskrail validate` on this branch.

### Results

_To be filled at the implement stage._
