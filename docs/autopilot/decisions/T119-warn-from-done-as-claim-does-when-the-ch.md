# T119 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T119-warn-from-done-as-claim-does-when-the-ch.md` and its commit
`e6cfe5a` (artifact and index row alone); the reproduction, run **without the wrapper**, which shows
the defect needs neither the wrapper nor T118; the probes of `discard` and `reopen`; and
`_change_status` against `_freeze_branch` in `src/taskrail/cli.py`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Warn, or refuse? | **warn, exit 0** · refuse with exit 5 | **warn** | The human decided this at T115's `decide` gate, in those words: no new disagreement warning, and `done` warns *as `claim` does*. The lane's case for refusing is genuinely good and is recorded here for whoever revisits it — `done` already has `--force` as its escape hatch, and exit 5 is what the skills stop on — but it is a behaviour change to a command every skill, the autopilot and every consuming repository call, and `--force` is blunt: it would waive the claim and dependency guards too, so an override of the branch check alone is not expressible today. |
| 2 | Wording, and one builder or two? | **two messages, no shared builder; keep `<root>`** · one parameterised builder | **two messages** | Rule of three: this is the second use, and the two sentences differ in more than a word. `claim`'s is prospective and fires before any edit; this one is retrospective and must name the checkout that was written and what to undo. Unifying the prose would force one of them to say something slightly wrong. Keep `<root>`: the whole value of a retrospective warning is telling the reader *where* the damage is. |
| 3 | `_change_status` (covering `discard`) or guarded to `done`? | **`_change_status`, covering both** · guard to `Status.DONE` and open a follow-up | **`_change_status`** | The orchestrator's brief told this lane to probe `discard` and, if it had the same hole, to open a task rather than widen. That instruction assumed `discard` was a separate site; it is the **same function**. Scoping to `done` would mean writing an *extra* condition specifically to leave a known, reproduced, identical defect in place, plus a follow-up task to delete that condition later. The widening is smaller than the narrowing, and CLAUDE.md's rule about fixing what is small and inseparable covers it. Say so in the pull request, since the task's title names `done` alone. |
| 4 | A `CHANGELOG.md` bullet | **yes, covering both commands** · none | **yes** | A command that printed one line now prints a second on stderr, and `--json` grows a `warning` key consumers may read. |
| 5 | `DESIGN.md` §7 | **add the sentence to the *Writing* bullet** · leave the file alone | **add it** | `claim`'s equivalent warning is documented at §7 already; an undocumented warning in the same family would be the odd one out. §7 is not §9, so there is no collision with T118. |

Given with the answers: the reproduction's most useful property is that it used no wrapper at all.
That is what proves this is not a duplicate of T118 and that closing T118's route leaves this one
open — which is the whole reason the human asked for both.
