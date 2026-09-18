# T057 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: the artifact at commit 81ea34e, the diff against the base (the artifact and one index row),
and `taskrail checks T057 --stage frame`.

The lane answered the sharpened framing question with measurement instead of speculation, and the
answer changes the task: **no orchestrator session in this repository has ever compacted**, across
three sessions and 56 lanes, and the current one is at 900k of a 1M context after 21 dispatches —
about 35k tokens of orchestrator context per task, so roughly 24 tasks per session. Lanes are not
where the context goes: the largest peaked at 191k and none compacted. The thing T033 could not
exercise is about to happen to this run by itself.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Harvest the finished runs as the primary evidence, with the fixture reduced to the CLI-only check? | yes · build the full synthetic probe · harvest only | **yes, as recommended** | Three sessions and 56 lanes of real record answer more than a synthetic probe could, and the reduced fixture covers the one thing the record cannot show: that a run's state survives the loss of the conversation. Building the probe T033 imagined would cost more and prove less. |
| 2 | Read local session transcripts, publishing aggregates only? | yes, aggregates only · restrict to the run files | **yes, with the publishing constraint spelled out** | Token counts, message counts and timestamps are facts about this tool's behaviour and belong in the write-up. No path, no session identifier, no peer-session name and no transcript text may appear in anything committed — the repository is public. The tables already drafted meet that; keep them that way. |
| 3 | Start another agent session to test messaging a previous session's lane? | out of bounds · one bounded headless pair | **out of bounds** | It spends real budget and its answer would be a property of one harness version. State Q2 as a limit plus the storage fact the lane established — a lane's conversation lives under the session that launched it, keyed by the handle in the run file — which is the structural reason T033's F2 happened. |
| 4 | Time box 90 minutes, dropping the fixture first if it overruns | yes · two hours | **yes** | A spike that overruns its box stops being a spike. |

Instructions given with the answers: re-derive every number from the harvest script so the tables are
reproducible rather than transcribed; state each of the three unscriptable items as a limit with the
reason it is out of reach.
