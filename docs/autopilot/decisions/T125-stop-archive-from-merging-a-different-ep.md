# T125 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T125-stop-archive-from-merging-a-different-ep.md` and its commit
`9831736`; the reproduction by hand edit in a scratch clone at `5215682` (T122 now refuses the
`epic add` route), which stacks two objectives under `## E07 — Current-branch workflow`; the
contrasting legitimate rename; and the root cause in `_ensure_section`, which matches an archive
section by ID and ignores the heading's name.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Refuse, or keep apart? | **refuse: move nothing in any backlog, exit 5, message naming the epic, the heading, the file and both ways out** · keep apart with a second section · refuse with exit 2 | **refuse, exit 5** | Keeping apart makes the duplicate permanent and turns every later lookup by ID ambiguous. Exit 5 matches T122's refusal of an archived `--id`, and a data conflict should not share the usage-error code. The message tells the human how to get unstuck either way: renumber the live epic, or — for a rename — edit the one heading. |
| 1a | Should `--dry-run` refuse the same way? | **yes** · only the real run | **yes** | A dry run that promises a move the real run refuses is worse than no dry run. |
| 2 | What counts as the same epic | **the name alone, exact equality** · a section holding `Objective:` counts as closed · either | **the name** | It is what the row says and it rests on nothing that is not validated — the objective is not required to be non-empty, and a partly archived section has none. Its cost is that a legitimate rename between two archive runs is refused too; that is rare, and the message says exactly which line to edit. |
| 3 | Can it fire on this repository or on a normal second run? | — | **no, and prove it** | The lane showed both: this repository's live E06 matches its heading exactly, E09 has no section, and T107's second-run test stays unchanged. Show the fixed source's dry run on a clone of `origin/main` exiting 0 at the fix gate. |
| 4 | The regression test | **Payments under an archived Auth refused, both files byte-identical, `--dry-run` refused; negative control with the name matching** | **as recommended** | The control proves the name is what the check keys on, not the ID's mere presence. |
| 5 | Documentation, and the `cmd_archive` edit | **one §7.6 sentence; T122's §7.6 clause corrected; one changelog bullet; a small `except` and dry-run call in `cmd_archive`** | **as recommended** | T122's bullet says a later `archive` files the new epic's rows in the old section — that stops being true, so it must say `archive` refuses instead. `cmd_archive` is this lane's: it is the only caller of the write path, and T124 is in `epic add`, not there. |
