# T057 — Check autopilot compaction and old-lane messaging with a scripted probe

**Frame draft — the verdict is written at the `decide` gate.**

## Question

[T033](T033-trial-the-autopilot-on-a-real-backlog-wi.md) left three things unverified and proposed
this task as "a scripted probe instead of a second trial": **compaction** (check D5), **messaging a
previous session's lane** (finding F2), and **OpenCode on a Claude model** (finding F3). The row
already anticipates that some of them cannot be scripted and are stated as limits.

Since T033 the situation changed: this repository has run its own autopilot repeatedly, and the
current run has been dispatching lanes through one orchestrator session for most of a working day.
So the question this spike answers is not "what does a probe measure?" but:

> **Given the record a long, real autopilot run already leaves behind, what does a scripted probe
> still add for compaction, for messaging a previous session's lane, and for OpenCode on a Claude
> model — and what is the smallest probe that answers something the run's own record does not?**

Concretely, three sub-questions:

- **Q1 — compaction.** Can an orchestrator's behaviour across a compaction be scripted at all
  without a human terminal, and if not, what bounded thing can be scripted that carries the same
  risk? How close does a real run actually get to its context limit, and after how many tasks?
- **Q2 — old-lane messaging.** Can "a new session resumes a previous session's lane by its handle"
  be probed non-interactively, or is it a structural property that can only be observed and stated?
- **Q3 — OpenCode on a Claude model.** Is this reachable at all from a script?

## What would answer it

| # | Answered by | Not answered by |
|---|---|---|
| Q1 | A measured context-growth curve for real orchestrator sessions, with the number of tasks per session and whether any compaction boundary was ever crossed; plus a check of whether the state an orchestrator needs after compaction exists outside the conversation (run file, decision records, `autopilot status`) | Reasoning about what compaction "should" preserve |
| Q2 | Where an agent stores a lane's conversation and what namespace its handle lives in, plus whatever the run's own record shows about resume-by-handle within one session | A claim that resume works, with no attempt recorded |
| Q3 | Evidence that the model can be selected non-interactively on this machine | Anything else |

## Approach

Three parts, all read-only or in a throwaway fixture, all non-interactive, minutes each:

1. **Harvest the finished run (Q1, Q2).** A read-only script, kept in the session scratchpad
   outside the repository, that reads a run file from `.git/taskrail/runs/` together with the
   agent's local session store and reports: the orchestrator's context growth over the run, each
   lane's peak context, any compaction boundary, the number of lane launches and of resumes by
   handle, and how long a handle stayed idle before a successful resume. Run it over every
   autopilot run this repository has recorded, not only the current one.
2. **A CLI-only fixture probe of what survives a lost conversation (Q1).** A temporary repository
   with the autopilot enabled and a run whose lanes are in different states, then a check of
   whether `autopilot status --json`, the run file and the committed decision records supply
   everything the `taskrail-autopilot` skill asks an orchestrator to know when it resumes a run.
   This is the scriptable stand-in for compaction: a compacted orchestrator and a new orchestrator
   need the same things, and only one of the two can be produced without a human terminal.
3. **State the rest as limits (Q2, Q3),** with the reason each one is out of reach rather than a
   bare "not verified", and — where a structural fact decides it — the observation that settles it.

The spike writes no production code and changes no agent setting. Whatever the probe scripts are,
they stay outside the repository; the artifact quotes their commands and output.

## Limits

- **Time box:** 2 points, at most 90 minutes of investigation after the frame gate. If it overruns,
  part 2 is cut first and its question is recorded as still open.
- **No agent session is started**, not even a non-interactive one, so nothing here proves what a
  *second* agent session can reach. That is a limit, not a result.
- **No compaction is forced.** Nothing in the supported commands compacts an orchestrator without a
  human at a terminal.
- **No change to any agent's settings, permissions or models**, and no interactive run.
- **No consumer project and no private data** reach this artifact: the session store is read for
  aggregate numbers only.
- **Adopting anything** — skill text, a CLI change, a shipped script — is follow-up work, opened as
  tasks rather than done here.

## Preliminary evidence gathered at the frame

These are the numbers that made the question above sharper than the row's. Method and full output
belong to the `investigate` stage; they are summarised here because they decide the approach.

**No orchestrator session in this repository has ever compacted.** Three autopilot orchestrator
sessions were measured, all on a 1M-context model, by summing each assistant message's input, cache
read and cache creation tokens:

| Orchestrator session | Runs it drove | Peak context | Compaction boundaries |
|---|---|---|---|
| 2026-09-15, 10:58Z–17:21Z | seven runs, 20 lanes | 722,758 | 0 |
| 2026-09-17, 09:50Z–13:46Z | `20260917-1`, 16 lanes | 438,758 | 0 |
| 2026-09-18, 08:59Z–16:10Z | `20260918-1`, 20 lanes | **900,751** | 0 |

The current run's growth is close to linear in hand-offs: about 150k tokens when the run started,
about 900k after 21 dispatched tasks and 17 hand-offs — on the order of **35k tokens of orchestrator
context per task**, which puts a 1M-context orchestrator at roughly **24 tasks per session** and the
current run within a few hand-offs of its limit.

**Lanes are not where the context goes.** Peak context per lane in `20260918-1` ranged from 70,022
to 190,711 tokens, and no lane crossed a compaction boundary. A lane ends; the orchestrator
accumulates.

**Resume by handle works, repeatedly, inside one session.** In `20260918-1` the orchestrator
launched 20 lanes and sent 38 `continue <ID>` messages to their handles (43 messages in all; five
went to peer sessions outside this run). Handles stayed reachable across idle gaps of up to about an
hour.

**A lane's conversation is stored under the session that launched it**, as
`<session-id>/subagents/agent-<handle>.jsonl`. The handle recorded in the run file is the file name.
That is the structural fact behind T033's F2, and it is what part 3 must state precisely.
