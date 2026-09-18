# T096 — Settle whether `autopilot.handoff` is a placeholder or a setting with no settings

Kind: chore · Epic: E08 · Status: scope proposed

## Goal

`[autopilot].handoff` accepts exactly one value, so its whole range is its default: a reader of
`config.py` or of `DESIGN.md` §4 cannot tell whether the key is an extension point with a planned
second value or a setting that was never finished. T088 measured it and asked for this task to
settle it. Settle it by *recording what the key is*, where the reader meets it. T088's own verdict
and T087's prospective principles forbid retiring it here, and this chore does not.

## Grounding: what the key is today

Measured on this branch (base `origin/main`, `0fd8dcb`).

- `src/taskrail/config.py:48` — `HANDOFF_MODES = ("sequential",)`; `:84` — the field default
  `handoff: str = "sequential"`; `:339` — type-checked as a string; `:350–351` — anything else is
  the config error `autopilot.handoff must be one of sequential`.
- The only consumer is `src/taskrail/autopilot/status.py:333`, which echoes it as
  `handoff.mode` in `autopilot status --json`. No code branches on the value.
- No shipped or example configuration writes the key: `grep -rn handoff --include=*.toml` over the
  repository matches nothing. It exists only in the two `DESIGN.md` example blocks.
- `tests/test_autopilot.py:172` already asserts the rejection with the *name of the intended second
  mode*: `('[autopilot]\nhandoff = "batch"', "autopilot.handoff must be one of sequential")`.

## Grounding: the intent is recorded, and the condition was tested

The key is not an unfinished setting. The second mode is named, and the condition for adding it is
written down and has already been measured:

- `DESIGN.md:1722` (§12.10) — "Not planned now: … a `batch` hand-off mode; …".
- `DESIGN.md:1734` (§12.10) — "the trial (T033) shows sequential hand-off costs more than it
  catches: add `batch`".
- `DESIGN.md:1622` (§12.8) and `:1689` (§12.9) both say "the only value **at first**"; only §4's
  copy at `:194` says "the only value" flat, with no pointer — which is the line T088 read.
- `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md:521,529` — the same two entries in
  the design spike that introduced the key.
- `docs/spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md:127–129` — the trial ran the
  condition and answered it: "**Sequential hand-off paid for itself:** 4 rebases at hand-off. One
  conflict outside the known classes (`stats()`) was resolved and shown to the human before review;
  the rest were classes 1–2. **The §12.10 condition for adding `batch` is not met.**"

So: `autopilot.handoff` is a **named extension point whose second value, `batch`, is deferred by
measurement**, not a placeholder and not a half-built setting. What is missing is only that none of
this reaches the reader at §4 or at `config.py`, and that §12.10 still states the `batch` condition
in the future tense although T033 already tested it.

## Change set

| File | Change |
|---|---|
| `DESIGN.md` §4, line 194 | The example config's comment `# the only value` becomes `# the only value; §12.10 on batch`, so the reader of the configuration reference is sent to the record. |
| `DESIGN.md` §12.10, line 1734 | The "the design changes if" entry is rewritten to say the condition was tested and not met, keeping it as a live condition for a future trial: "the trial (T033) shows sequential hand-off costs more than it catches: add `batch`; **it did not (T033), so `sequential` stays the only mode and `handoff` keeps the name for it**" (final wording at implement, one line, same list style). |
| `docs/chores/T096-settle-whether-autopilot-handoff-is-a-pl.md` | This artifact. |
| `docs/chores/README.md` | Index row for T096, added at implement. |
| `TODO.md` | Only the row's `✅` at close, through `taskrail done`. |

Conditional on decision 2 below:

| File | Change |
|---|---|
| `src/taskrail/config.py`, above line 48 | One comment line: `# "batch" is the foreseen second mode, deferred by the T033 trial (DESIGN.md §12.10).` Nothing else in the file changes. |

## Decisions needed

1. **Is documenting the recorded intent the right settlement, rather than escalating to the human?**
   Recommended: **yes, document it**. The task offered escalation as an option because T088 could
   not see an intent; the intent turns out to be recorded twice (§12.10 and T007) and the condition
   for the second mode was already measured by T033. Nothing is left for the human to decide, so
   escalating would spend a human decision on a question the repository has already answered.
   Alternatives: (a) escalate anyway, which costs a round trip and, on this evidence, would come
   back "keep it"; (b) propose a follow-up to retire the key — **not recommended**: the evidence
   says the key is doing its job (naming a policy `status` reports, reserving the name for `batch`),
   and retiring it would be a silent loss for any repository that set it (T088's row at line 454).
   No follow-up task is proposed.

2. **Does the one comment line in `src/taskrail/config.py` belong in this task?** Recommended:
   **yes**. `config.py:47–48` is exactly where T088 hit the question, and a reader of the source
   does not have §4 in front of them. Cost: one added line above `HANDOFF_MODES`, far from the
   `[autopilot]` parsing that **T094** is editing (its work is in the unknown-key warning around
   `_autopilot`/`config` parsing, roughly `:330–360` and the validator), so a conflict is unlikely
   but not impossible. Alternative: leave `config.py` untouched and settle it in `DESIGN.md` only —
   zero conflict risk with T094, but the puzzle stays where it was found.

3. **Is the §12.10 edit (line 1734) inside this lane's touch map?** The brief names `DESIGN.md` §4;
   §12.10 is the place where the intent actually lives, and leaving it in the future tense keeps the
   §4 pointer half-true. Recommended: **include it**, one line. Alternative: restrict the change to
   §4's comment, which then points at a condition the reader cannot tell was already tested.

## Out of scope

- **Removing or deprecating the key**, and adding `HANDOFF_MODES` entries. T087's prospective
  principles, quoted in `CLAUDE.md`, and T088's option B (`docs/spikes/T088…:471`) both forbid it
  here; no evidence in this task calls for it.
- **Implementing `batch`.** §12.10 keeps it out until a trial says otherwise.
- **The unknown-key warning** (T094) and the unconsumed-option sweep (T095).
- `CLAUDE.md`, the shipped skills, `CHANGELOG.md` (no behaviour changes for a consumer), and
  `src/taskrail/autopilot/status.py`.
- §12.8's and §12.9's "the only value at first" lines: already correct, and §12.9 is a copy of the
  §4 block whose comment column differs — left alone to keep the diff to what is wrong.

## Verification

Doc-only change (plus, if decision 2 is approved, one comment line), so the proof is that nothing
moved and the text is right:

- `taskrail checks T096 --stage implement` — the `test` check (`uv run pytest -q`); `lint` is
  expected to report as not configured (the task's `checks` map defines only `test`).
- `git diff --stat` on the branch, to show the change set and nothing else.
- `.taskrail/bin/taskrail validate` at the close.
- Read back `DESIGN.md:194` and the §12.10 entry, and confirm the `batch` name matches
  `tests/test_autopilot.py:172` and §12.10's wording.

## Verification results

To be filled at implement.
