# T089 — Decide whether to split DESIGN.md by topic for what the orchestrator reads first

**Verdict** — pending; this document is the `frame` draft. The investigation is not done.

## Question

`.taskrail/config.toml` sets `[autopilot].read_first = ["CLAUDE.md", "DESIGN.md"]`, so the
orchestrator reads `DESIGN.md` — 1844 lines — whole at every gate it answers. Two sections
dominate it: §7 (CLI, 505 lines) and §12 (autopilot, 464). Should the file be split into topic
documents reached through one-line pointers, or left as it is?

Three sub-questions:

1. **What does a gate actually need?** Which sections does an answer at a gate draw on, measured
   rather than assumed — from what the autopilot skill and its `gate-review.md` reference cite,
   from what past runs' decision records cite, and from the section-level structure of the file.
2. **What would a split cost?** How many cross-references exist, where they live, and how many
   survive a rewrite. `README.md`, `DESIGN.md` itself and the historical artifacts under `docs/`
   cite sections by number (§4, §5.6, §7.1, §12.8 among them); artifacts are never rewritten, so
   any renumbering makes them wrong. A second hand-kept index is also known to drift out of sync
   with the first.
3. **Which option wins on the measured difference?** At least: leave it as one file; split §7 and
   §12 out and leave `DESIGN.md` as a portal with a map; split fully by topic; leave the file
   whole but change what `read_first` names. Each stated with what a gate would then read and
   what breaks.

Per T087's accepted verdict, the design principles are **prospective**: KISS and YAGNI judge the
change this spike would propose, not the merit of the file as it stands. The re-examination is
legitimate because this task asks for it. The cross-reference rewrite is therefore a cost of the
new structure, weighed against a measured benefit — not evidence that the current file is wrong.

## Evidence that would answer it

| # | Evidence | Method |
|---|---|---|
| E1 | Exact section sizes on this branch, and the share of the file each takes | `awk` over `^## ` headings |
| E2 | What the orchestrator is actually instructed to read at a gate, and whether "whole file" is the real behaviour | the shipped `taskrail-autopilot` skill, its `references/gate-review.md`, and `src/taskrail/autopilot/` for how `read_first` is delivered |
| E3 | Which `DESIGN.md` sections the skills and references cite by number | `grep` for `§`/"DESIGN.md §" across `src/taskrail/skills/` and `src/taskrail/integrations/` |
| E4 | Which sections past runs' gate answers actually cited | `grep` over `docs/autopilot/decisions/` and the artifacts of tasks worked under the autopilot |
| E5 | The full cross-reference census: every citation of a `DESIGN.md` section, by file class (code, shipped skills, `README.md`, `CLAUDE.md`, `DESIGN.md` itself, historical artifacts) | `grep -rn` with a section-reference pattern, counted per class |
| E6 | Prior art in this repository: `T060` removed `DESIGN.md` and `CLAUDE.md` from something — what, and why — plus `T028`, which wrote §12 | the artifacts under `docs/chores/` and their commits |
| E7 | What a split would actually look like, built outside the repository, so the rewrite cost is counted rather than estimated | a scratchpad prototype; the number of pointer lines, the number of citations that must change, and what a gate would read under it |
| E8 | Whether a test could hold a split structure together, given the precedent of `tests/test_autopilot_skill.py` asserting shipped prose against `build_parser()` | read that test; judge what an equivalent index test could and could not assert |

## Approach

Measure first, reason second. Every figure in the write-up carries the exact command that
produced it and the commit it was produced at, so a reader can re-run it. Where a count is
sensitive to method — as T087 found for its flag count — the write-up says how it counts before
it gives the number.

The four options are costed side by side on the same three axes: what a gate reads under it,
what breaks in the existing corpus, and what new upkeep it creates. A recommendation follows only
if the measured difference justifies it; "leave it as one file" is a real option and not a
formality.

## Limits

- **Time box:** 2 points, this run's `investigate` and `decide` stages.
- **This spike decides; it does not split.** `DESIGN.md` is not edited by this task. If the
  verdict is to split, the split is follow-up work opened with `taskrail new` on this branch, and
  any demonstration of it lives in the session scratchpad, outside the repository.
- **Out of the touch map:** `DESIGN.md`, `CLAUDE.md`, `.taskrail/config.toml`, anything under
  `src/`, and another task's backlog row. This task edits only this document, one appended row in
  `docs/spikes/README.md`, and its own rows in `TODO.md` through the CLI.
- **No live token measurement.** There is no instrumented record of what an orchestrator loaded
  at a past gate; the evidence for "what a gate needs" is what the skills, references and decision
  records cite, plus this run's own orchestrator report, which is a single data point and is
  labelled as one.
- **Consumers are invisible.** Repositories that install taskrail are private and cannot be cited
  (publishing constraint), so any claim about how a consumer reads `DESIGN.md` is out of scope.

## Evidence

_To be completed in the `investigate` stage._

## Options considered

_To be completed in the `decide` stage._

## Recommendation

_To be completed in the `decide` stage._

## What would change the decision

_To be completed in the `decide` stage._

## How to reproduce

_To be completed in the `decide` stage._
