# T056 — Add an OpenCode note on escalations during blocking lane batches

## Goal

Fix finding F3 of the [T033 trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md): on
OpenCode, task calls block, so an orchestrator that asks the human at an escalation and then starts
another batch of task calls never ends its turn, and the human has no point at which to answer. In
the trial T004 stayed `escalated` for 57 minutes, T005's `silent` flag went unseen while the
orchestrator was blocked, and handles reached the run file only when a batch returned.

The `taskrail-autopilot` skill's OpenCode note gains three rules: at an escalation, end the turn
with the question instead of starting another blocking batch; when a batch returns, record the
handles first; and run `autopilot status` for `silent` lanes before starting the next batch. A test
asserts the rules in the installed note.

Whether a Claude model on OpenCode would end its turn at an escalation on its own is not known (T033
*What would change the decision*); the rules cost nothing if it would, so the note states them
either way.

## Change set

- `src/taskrail/integrations/opencode.md`, section
  `<!-- taskrail:skill taskrail-autopilot -->` only — the core skill's OpenCode section stays
  unchanged. Insert one bullet after the "Task calls block…" bullet and replace the last sentence
  of the "Lanes cannot ask the human" bullet, giving:

  ```markdown
  - Task calls block until the subagent returns, and lanes started in one message return together.
    You therefore answer gates in waves, once every lane in the batch has stopped: correct, but
    slower. The experimental background subagents (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`)
    notify you when each lane stops instead; use them only when the human has enabled them.
  - While a batch of task calls blocks, you see neither the human nor `autopilot status`. When a
    batch returns, before anything else, record the handle of every lane it started with
    `autopilot lane --handle`, then run `autopilot status --run <R> --json` and deal with every
    `silent` lane before you start the next batch.
  - Lanes cannot ask the human: the `question` permission is denied to the `general` subagent. At
    an escalation, ask the human yourself in plain text and end your turn with that question. Never
    start another batch of blocking task calls in the same turn: it leaves the human no point at
    which to answer. Resume the other lanes in the batch that follows the human's reply; with the
    background subagents, which do not block, resume them before you ask.
  ```

- `tests/test_autopilot_skill.py` — one new test, parametrized over `opencode` alone
  (`.opencode/skills/`) and `claude` plus `opencode` (`.claude/skills/`): it installs with
  `init`, takes the `## On OpenCode` section of the installed `taskrail-autopilot/SKILL.md`, and
  asserts, on whitespace-collapsed text, the phrases of each rule: ending the turn with the
  question, never starting another blocking batch in the same turn, recording every handle when a
  batch returns, and running `autopilot status --run <R> --json` for `silent` lanes before the next
  batch. It also asserts the core `taskrail` skill's OpenCode section does not carry them. The
  existing `CORE_OPENCODE_NOTES` equality tests already keep the core note unchanged.
- `DESIGN.md` (governing) — the exact text is Decision 1 below.
- `CHANGELOG.md` — one entry under *Unreleased*:

  ```markdown
  - **OpenCode note on escalations during blocking batches.** The `taskrail-autopilot` skill's
    OpenCode note has the orchestrator end its turn with the question at an escalation instead of
    starting another blocking batch of task calls, and record handles and check `silent` lanes as
    soon as a batch returns (T056).
  ```

- This artifact and its row in `docs/chores/README.md`.

This repository installs only the `claude` integration (`.taskrail/installed.json`), so its
installed copies under `.claude/skills/` carry no OpenCode note and `taskrail upgrade` changes
nothing; none is run.

## Decisions needed

1. **DESIGN.md text.** Approve these two edits:
   - §8 integration table, the `opencode` row becomes:

     ```markdown
     | `opencode` | `.opencode/skills/` | ask in plain text; a subagent's final message returns to its caller | lanes are task tool calls resumed by `task_id`; gates answered in waves; at an escalation, end the turn with the question; record handles and run `status` when a batch returns |
     ```

   - §12.3, after "Its integration note says so and names the experimental background flag without
     requiring it.", insert:

     ```markdown
     While a batch blocks, the orchestrator sees neither the human nor `status`, so the note also has
     it record the handles and check `status` for `silent` lanes as soon as a batch returns, and end
     its turn with the question at an escalation instead of starting another batch (T033 F3,
     *implemented, T056*).
     ```

   Recommendation: approve. Alternative: leave DESIGN.md unchanged, since the table and §12.3
   already defer agent detail to the integration notes; the design would then not record why the
   OpenCode orchestrator ends its turn.
2. **Other lanes during an escalation.** The portable skill says "Other lanes keep going meanwhile".
   With blocking task calls that is impossible without starting a batch, so the proposed note has
   lanes stopped at gates wait for the human's reply and be resumed in the next batch; with
   background subagents it resumes them before asking. Recommendation: approve this. Alternatives:
   (a) resume the other lanes in a batch first and ask only when it returns — what the trial did,
   and it leaves the question unanswered for as long as lanes keep stopping; (b) ask with
   OpenCode's `question` tool, which waits for the human inside the turn — the core note tells
   agents to ask in plain text, and the trial's first `question` call failed its schema, so it is
   not proposed.
3. **CHANGELOG entry.** Recommendation: add it, as for the T024 notes. Alternative: none, since it
   is skill text only.

## Out of scope

- The portable `taskrail-autopilot` `SKILL.md` and its references: they name no agent, and the
  `test_portable_text_names_no_agent_or_agent_tool` test keeps it so.
- The Claude Code note (T052) and the other skill-text findings (T055).
- The 421-second OpenCode lane write, possibly a pending permission prompt: unverified in T033.
- Making background subagents required, or any CLI change.
- Installed copies in this repository (claude integration only) and `CLAUDE.md`.

## Verification

- The new test, observed failing on the unchanged note before the edit and passing after it.
- `init --integration opencode` in a throwaway directory, reading the installed
  `taskrail-autopilot/SKILL.md` to confirm the rules appear once, under `## On OpenCode`, and that
  the core `taskrail/SKILL.md` OpenCode section is unchanged.
- The `test` check (`uv run pytest -q`); `lint` is not configured.
- `taskrail validate`.

Decisions 1–3 were approved at the scope gate as recommended; see the task's
[decision record](../autopilot/decisions/T056-add-an-opencode-note-on-escalations-duri.md).

Results:

- New test `test_opencode_note_ends_the_turn_at_an_escalation_and_checks_lanes_between_batches`,
  on the unchanged note (the note edit stashed): `2 failed, 24 deselected`, both parameters
  failing on `end your turn with that question`. With the note edit: `tests/test_autopilot_skill.py`
  `26 passed`.
- Throwaway `git init` directory under `/tmp`, `taskrail --root <dir> init --integration opencode`
  from this branch's source: the installed `.opencode/skills/taskrail-autopilot/SKILL.md` has one
  `## On OpenCode` section carrying the new bullets once each; the installed
  `.opencode/skills/taskrail/SKILL.md` OpenCode section is the unchanged two bullets. The directory
  was deleted afterwards.
- `test`: `830 passed in 86.89s`. `lint`: not configured.
- `taskrail validate`: `56 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
