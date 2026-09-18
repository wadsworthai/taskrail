# T105 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan artifact at commit d9099f2, the diff against the base (the artifact and one index
row; no source touched, as `plan` requires), and the five measurements the lane made from a
temporary test rather than from reading — including the stall reproduced with `max_lanes = 3` and two
escalations, which is the failure the human watched happen in this very run.

**The lane disproved the orchestrator's own note.** The brief said `handed-off` might hold a lane for
a different reason; it does not. `handed-off` is in `COUNTED` but not in `OCCUPYING`, and a measured
`next` dispatched two fresh tasks past a handed-off one. The suggestion is withdrawn, and the task
does not grow to cover it.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Name the new state | `queued` · **`parked`** · `ready` · `waiting` | **`parked`, departing from the recommendation** | The lane named the cost itself: `status` already reports `handoff.queue`, the branches waiting to be handed off. Two fields called *queue* in one `--json` output, meaning different things, is a defect waiting to be written into someone's tooling. `parked` is what the lane's own prose reaches for when it describes the state ("parked workspaces"), and it says the thing exactly: the workspace is kept, the lane is not. |
| 2 | Priority against tasks never started | parked first, oldest answer first · interleave in backlog order | **parked first, as recommended** | The work is started, the claim and the worktree are held; finishing beats starting, and oldest-first cannot starve. |
| 3 | Resources | release with the lane, reallocate on redispatch · hold them while parked | **release, as recommended** | Identical to `failed` today. Holding them would turn `limited_by: max_lanes` into `limited_by: resource:<name>` — the same stall with a different label. |
| 4 | What `next` records on redispatch | back to `running` with a live `dispatched` stamp, clearing `gate`/`reason` · keep `parked` recorded | **back to `running`, as recommended** | One rule instead of a conditional in three places. The dispatch-expiry machinery then applies unchanged if the lane is never restarted. |
| 5 | Always through the queue? | yes · let the orchestrator resume directly when a lane is free | **yes, as recommended** | The lane budget is enforced by the CLI rather than by the orchestrator's arithmetic, which is the whole point of the change. One step longer, one fewer thing to get wrong. |
| 6 | `handed-off` | not covered, no follow-up · open a second task | **not covered, no follow-up, on the lane's measurement** | Its place in the run's `count` is §12.7 as written. Revisiting that would let a run start more tasks than it was asked for, which is a different decision and the human's. |
| 7 | Does `gate` also free its lane? | no · yes | **no, as recommended** | The orchestrator answers an ordinary gate within one wake-up; only a stop that waits on a human is worth parking. |

Accepted risk, recorded: with lanes freed, a run may hold `max_lanes` working lanes **plus** any
number of parked workspaces. That is what the row asks for. No `max_parked` limit is added, and
`status`'s `holds_lane` makes it visible — if it ever bites, that is the evidence a limit would need.

Instructions given with the answers: tests first, one per criterion, each observed failing; name every
`DESIGN.md` section touched at the implement gate; and keep the skill's *Escalate* step the single
place that tells an orchestrator what to do, so the procedure has one home.
