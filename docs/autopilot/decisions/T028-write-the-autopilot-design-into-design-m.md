# T028 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T028-write-the-autopilot-design-into-design-m.md` (commit `f2616b4`) — a
change set confined to `DESIGN.md` §1, §11 and a new planned-autopilot section,
leaving §6 and §7 to T017.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Position of the new section | append as §12 · insert as §11 and renumber | **append as §12** | No heading renumbering while T017 edits the same file. |
| 2 | Rejected alternatives in DESIGN.md | link plus one sentence for the two likeliest · none · full table | **link plus one sentence each** for an agent-launching CLI and enabled-only installation | Stops the two most likely re-proposals without duplicating the spike. |
| 3 | `autopilot lane --group` | add to §12.1 · copy the table as is | **add** | The accepted design point 6 uses it; the table omitted it by oversight. |
| 4 | "Conflicts outside the known classes" as a computed flag | follow design point 5 · computed flag | **follow design point 5** and note that T032 settles it at its own gate | The accepted design keeps conflict classification as judgement; the design document must not quietly amend it. |
| 5 | Changelog bullet | none · one bullet | **none** | `Unreleased` lists behaviour changes; this documents a plan. |
| 6 | README change | none · mention | **none** | README describes current use only. |

Approved: the change set and its boundary as scoped.

## implement gate

Reviewed independently of the lane's report: the DESIGN.md diff (only the §1 non-goal line and the
appended §12), the "planned, not implemented" status at the top of §12, §12.2's wording of the
human's installation decision, the absence of private project names, and the lane's checks (TOML
block identical to the spike's, links resolving, 262 tests passing, `validate` clean).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the design text | approve · request changes | **approve** | Faithful to the accepted design and the human's decisions; clearly marked as planned; stays out of §6 and §7. |
| 2 | `autopilot status [--fetch]` in the signature | keep · drop | **keep** | The spike's own description of the command says it never fetches unless `--fetch`. |
| 3 | §12.1 noting that exit 5 gains "autopilot disabled" | keep · remove | **keep** | Follows from `start` refusing with 5, and tells T029 to widen the §7.1 exit-code table. |
| 4 | The run file holds each lane's group | keep · leave to T030 | **keep** | A group assigned by judgement has nowhere else to live once `lane --group` exists. |
