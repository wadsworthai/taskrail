# T098 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T098-fix-the-configuration-and-cli-documentat.md` at commit 41a7408, the diff
against the base (the artifact and one index row only, `DESIGN.md` untouched as `scope` requires),
and the lane's re-verification of the four defects — the orchestrator confirmed `grep -c
"epic_prefix" DESIGN.md` is 0 and that `id_digits` appears once, at line 982, inside §7.3.

The lane found the task row over-stated defect 2, as the brief warned it might: the row says §4
"omits … `id_digits`", which reads as absent from the document, and it is not. The true defect is
narrower — absent from §4's example, and nowhere stated to govern the width of the IDs `taskrail new`
generates. That correction is accepted and belongs in the artifact.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How much to say about `epic_prefix` and `id_digits`? | the example lines plus the prose sentence · the example lines alone · a per-key table | **the example lines plus the prose sentence, as recommended** | The failure a repository hits is a refusal quoting the prefix's *value* and never the key, so two lines in an example do not tell a reader the key is the fix. §4's own reading-map row promises "every key of `.taskrail/config.toml` and its default", and one sentence discharges it. A per-key table would be a structure no other table in §4 has. |
| 2 | `kind add`: delete and point at §5.2, or delete and say nothing? | point at §5.2 · say nothing | **point at §5.2, as recommended** | The only fact in the removed cell was that installing a local kind is possible. Deleting it without a pointer removes information instead of correcting it, and §5.2 already holds the layering. |
| 3 | The four options the lane deliberately left undocumented, pending T095 | document them now · leave them · open a task | **document them now: the touch map is widened to four more rows in §7** | The lane was right to hold them while T095 was open — documenting an option about to be retired would be waste. The human has now answered T095, and **every answer is route A, document it**: `epic add --id`, `epic add --file`, `epic split --file` and `next --limit` all stay, with "one line in §7's command table, via T098" as the agreed route. Adding them here costs four rows in a table this lane is already editing; a separate task would touch the same table twice. |

Instructions given with the answers: apply (a)-(d) as proposed, plus the four §7 entries; `next
--limit`'s missing `help=` string is **code and stays out** — T095 opens a chore for it. Do not
document the `--owner` flag here: T095 opens a chore for §6.2. Do not touch the reading map or the
paragraphs T094 and T096 merged.

## Conflict handling agreed for all lanes

Run 20260918-1. T095 and T097 are closing after the human answered their questionnaires; neither
touches `DESIGN.md`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T098 is the only lane writing to `DESIGN.md`; T095 and T097 edit their artifacts and open tasks** | T094's and T096's edits are already merged into this lane's base, and the lane verified none of its four hunks overlaps their text. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1) and appended index rows (2)** | Three lanes closing at once will collide in `TODO.md` and in the artifact indexes. A conflict inside `DESIGN.md` is not a known class, and with T098 the only writer there should not arise. |
| 3 | May this lane change behaviour? | allow · forbid | **forbidden** | It is a documentation chore. A fifth defect, or anything needing code, becomes a follow-up task. |
