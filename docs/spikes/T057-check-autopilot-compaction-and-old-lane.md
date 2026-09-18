# T057 — Check autopilot compaction and old-lane messaging with a scripted probe

**Verdict — the probe the row asked for should not be built. A long autopilot run already answers
more than a synthetic probe could, and it answers something this project did not know: an
orchestrator session holds about 20–26 tasks. No orchestrator session in this repository has ever
compacted; the one driving the current run reached 914,741 tokens of a 1,000,000-token context after
21 dispatched tasks and 17 hand-offs, at 36,700–44,300 tokens of orchestrator context per task. The
limit is the orchestrator's alone: the 38 lanes measured across nine runs peaked between 78,404 and
355,752 tokens and not one of them compacted. Of the row's three unverified things, one —
compaction — was replaced by the cheaper question its risk really poses, and the answer is
reassuring: `autopilot status` derives every lane state from git except `gate`, `escalated` and
`failed`, and those, with the handle, the gate name, the reason and the resources, live in the run
file under `.git/`, outside the conversation. The other two cannot be scripted at all and are stated
as limits — with, for old-lane messaging, a structural reason rather than a shrug: on this agent a
lane's conversation is stored under the session that launched it, keyed by the handle the run file
records, and across nine runs all 38 handles belonged to exactly one session each.**

This spike changed no code, no configuration, no skill, `DESIGN.md`, `CLAUDE.md` or `CHANGELOG.md`,
and no other task's row. Its scripts are throwaway and were kept outside the repository.

## Question

[T033](T033-trial-the-autopilot-on-a-real-backlog-wi.md) left three things unverified and proposed
this task as "a scripted probe instead of a second trial": **compaction** (its check D5), **messaging
a previous session's lane** (its finding F2), and **OpenCode on a Claude model** (its finding F3).
The row already anticipates that some of them cannot be scripted and are stated as limits.

Since T033 this repository has run its own autopilot nine times, and the current run has dispatched
21 tasks through one orchestrator session in a single working day. So the question is not "what does
a probe measure?" but:

> **Given the record a long, real autopilot run already leaves behind, what does a scripted probe
> still add for compaction, for messaging a previous session's lane, and for OpenCode on a Claude
> model — and what is the smallest probe that answers something the run's own record does not?**

- **Q1 — compaction.** Can an orchestrator's behaviour across a compaction be scripted at all
  without a human terminal, and if not, what bounded thing can be scripted that carries the same
  risk? How close does a real run get to its context limit, and after how many tasks?
- **Q2 — old-lane messaging.** Can "a new session resumes a previous session's lane by its handle"
  be probed non-interactively, or is it a structural property that can only be observed and stated?
- **Q3 — OpenCode on a Claude model.** Is it reachable at all from a script?

## Approach

As agreed at the frame gate:

1. **Harvest the finished runs (Q1, Q2)** with a read-only script, kept outside the repository, that
   reads the run files under `.git/taskrail/runs/` together with the agent's local session store and
   reports aggregates only.
2. **A CLI-only fixture probe (Q1)**: a throwaway repository with the autopilot enabled, one run
   driven into mixed lane states through the CLI, and a check of what a session that has lost its
   conversation can still read. A compacted orchestrator and a new orchestrator need the same
   things, and only this half can be produced without a human terminal.
3. **State the rest as limits (Q2, Q3)** with the reason each is out of reach, and, where a
   structural fact decides it, the observation that settles it.

## Evidence

### E1 — No orchestrator session has ever compacted, and context is the binding limit

Method: the harvest script identifies an orchestrator session without any hard-coded name — it is
the session whose stored lane conversations carry the handles a run file records. For each assistant
message it sums `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`, which is the
context that message was served, and counts every record marked as a compaction summary, a
compaction boundary or carrying compaction metadata.

| Orchestrator session | Runs it drove | Lanes | Peak context | Compaction boundaries |
|---|---|---|---|---|
| 2026-09-15, 10:58Z–17:18Z | `20260915-1` … `-7` | 10 | 722,758 | 0 |
| 2026-09-17, 09:50Z–13:46Z | `20260917-1` | 8 | 438,758 | 0 |
| 2026-09-18, 09:05Z–16:15Z | `20260918-1` (open) | 20 | **914,741** | 0 |

All three ran on the same 1M-context model. The growth of the current run, sampled from the curve
the script prints:

```
09:05:49Z    31,922      12:19:41Z   369,003      15:08:48Z   682,548
09:44:57Z    93,867      12:54:31Z   435,051      15:27:52Z   759,415
10:25:41Z   134,587      13:52:44Z   475,304      15:48:48Z   830,219
10:42:23Z   198,375      14:26:16Z   550,431      16:11:33Z   904,749
10:59:19Z   255,993      14:43:06Z   609,688      16:15:42Z   914,741
12:02:45Z   310,363
```

Per-task cost, measured between the context at the run's first message and the last message inside
the run's own window, so a session that drove several runs is not counted twice:

| Run | Dispatched | Hand-offs | Context at start | at end | per dispatched task |
|---|---|---|---|---|---|
| `20260915-1` | 1 | 1 | 94,756 | 190,323 | 95,567 |
| `20260915-2` | 2 | 2 | 131,833 | 319,720 | 93,943 |
| `20260915-3` | 1 | 1 | 325,863 | 376,767 | 50,904 |
| `20260915-4` | 1 | 1 | 380,512 | 424,405 | 43,893 |
| `20260915-5` | 2 | 2 | 426,260 | 534,483 | 54,111 |
| `20260915-6` | 2 | 2 | 561,493 | 677,506 | 58,006 |
| `20260915-7` | 1 | 1 | 681,389 | 721,140 | 39,751 |
| `20260917-1` | 8 | 8 | 83,315 | 438,066 | 44,343 |
| `20260918-1` | 21 | 17 | 143,161 | 914,459 | **36,728** (45,370 per hand-off) |

The short runs cost more per task because each run pays a fixed price — reading the governing
documents, the backlog, `status` — over one or two tasks. The two long runs give the marginal rate:
**36,728 and 44,343 tokens per task**. Against a session that starts at roughly 32,000–39,000 tokens
of its own overhead, that is **21 to 26 tasks before a 1M-context orchestrator reaches its limit**.
The current run asked for 24.

### E2 — Lanes are not where the context goes

| Run | Lanes | Lane peak context: min / median / max | Lane compactions |
|---|---|---|---|
| `20260915-2` | 2 | 299,009 / 355,752 / 355,752 | 0 |
| `20260917-1` | 8 | 116,397 / 201,427 / 236,547 | 0 |
| `20260918-1` | 20 | 78,404 / 135,132 / 190,711 | 0 |

Across all nine runs, no lane crossed a compaction boundary. A lane ends when its task closes; the
orchestrator accumulates every lane's report, every gate answer and every hand-off. That is a
property of the design — one supervising session, many short-lived lanes — not of these runs.

### E3 — Resume by handle works inside one session, repeatedly

In `20260918-1` the orchestrator made 20 lane launches and 44 messages, 38 of them `continue <ID>`
to this run's lane handles; in `20260917-1`, 8 launches and 17 messages, all 17 to lane handles.
Every lane in `20260918-1` was resumed twice (three times for one), and handles stayed reachable
across idle gaps of up to 60.0 minutes. No resume by handle failed in any measured run.

### E4 — A lane's conversation belongs to the session that launched it

The store keeps each lane conversation under its orchestrator session's own directory, named by the
handle the run file records. Across the nine runs:

```
lane handles recorded across all runs : 38
handles with a transcript in the store: 38
handles owned by more than one session: 0
sessions holding lane transcripts     : 3
transcripts stored outside a session  : 0
```

There is no shared namespace a second session could address. This is the structural reason behind
T033's F2 — a new session restarted a lane from its branch instead of resuming it — and it means
that outcome was not an accident of one probe on one day.

### E5 — What survives the loss of the conversation (the fixture probe)

A throwaway repository, the autopilot enabled, four tasks, one run, three lanes driven into
different states through the CLI only, then read back as a new session would read them:

```
### status after the lane claimed (state derived from git, not from the run file)
  task   status.state   runfile.state  handle  gate      claim
  T001   gate           gate           h-001   scope     -
  T002   running        running        h-002   -         <owner>
  T003   escalated      escalated      h-003   implement -
```

Before that lane claimed its task, the same run file already said `running` for it, and
`autopilot status` reported `dispatched`. The reason is in the CLI: `status` recomputes each state
from git — the mainline, the task branch, the claim, the live dispatch record — and takes only three
states from the run file:

```
RECORDED = ("failed", "escalated", "gate")  # lane states only the run file knows
```

So a compacted or new orchestrator loses none of a run's state. What it needs that git cannot give —
the lane handle, the stage a lane is stopped at, an escalation's reason, the chosen resources, the
run's own decisions — is in the run file, which lives under `.git/taskrail/runs/` and is touched by
neither compaction nor a new session. The gate answers themselves are in the decision records, which
the skill requires committed before a lane is resumed. Two corollaries worth naming:

- **A lane recorded `running` whose claim is gone reads as `dispatched`, then as `pending` once the
  dispatch grace expires.** That is what makes a dead lane re-dispatchable, and it is also why the
  resume procedure keys on `silent` rather than on the run file's word.
- **The run file is the only state that is neither in git history nor in the working tree.** A
  conversation rewind does not restore it (T033 F7, answered by `autopilot close`), and a fresh
  clone does not carry it.

### E6 — What could not be probed

- **Compaction itself.** Nothing in the supported commands compacts an orchestrator without a human
  at a terminal, so no script can produce a compacted orchestrator and watch it keep dispatching.
- **Messaging a previous session's lane.** Testing it needs a second agent session, which the frame
  gate put out of bounds; E4 gives the structural reason instead of an experiment.
- **OpenCode on a Claude model.** T033 recorded that the model was unavailable in that setup; a
  script cannot conjure model access, and this spike started no agent.

### Correction to an earlier count

An interim report of this spike said three sessions and 56 lanes. That number came from counting
files in the store, where each lane has a transcript and a metadata file beside it. The measured
figure is **38 lanes** over nine runs: 10, 8 and 20 for the three sessions.

## Options considered

1. **Build the probe as the row imagined it** — a fixture plus a script for compaction and old-lane
   messaging. Rejected: two of its three targets cannot be reached by a script at all, and the third
   (compaction) can only be approached through its consequence, which is what option 2 does more
   cheaply.
2. **Harvest the finished runs, plus a CLI-only fixture for what survives a lost conversation.**
   Chosen. Minutes of work, real data, and it produced a number — 21 to 26 tasks per orchestrator
   session — that no synthetic probe would have produced.
3. **A second human-driven trial.** Rejected: T033's decide gate already ruled out end-to-end trials
   as the way to verify follow-ups.
4. **Do nothing and leave the three items "not verified".** Rejected once the harvest proved cheap;
   it would also have left the context budget unknown.

## Recommendation

**Accept that the scripted probe is not worth building, and spend the finding instead.** Three
follow-ups, to be opened only if the human approves them at this gate:

| Proposal | Kind | Why |
|---|---|---|
| Record the orchestrator's context budget where a run's count is chosen — `DESIGN.md` §12 and the `taskrail-autopilot` skill: about 35k–45k tokens of orchestrator context per task, so roughly 20–26 tasks per 1M-context session, lanes being no constraint — and tell the orchestrator to plan the count against it and to hand a longer backlog to a fresh session through the resume path rather than relying on compaction | chore | E1, E2 |
| Replace §12.3's "whether an earlier session's handle still reaches a lane is not verified" with the measured structural reason for Claude Code (a lane conversation is stored under the session that launched it, keyed by the run file's handle), keeping restart-from-branch as the only path | chore | E4 |
| When a run does cross a compaction boundary, harvest that run and record what the orchestrator lost — a short task, not a trial, since the harvest already detects the boundary | spike | E1, E5 |

The first is the one that matters: a run's count is currently chosen with no idea of its ceiling,
and the current run shows what that costs — it asked for 24 tasks and its session is at 91% of its
context with tasks still open.

## What would change the decision

- **A run crosses a compaction boundary.** The one thing still unmeasured is what an orchestrator
  actually loses in practice. The harvest script detects the boundary, so the next long run answers
  it at no cost — and the current run may be the one.
- **An agent stores lane conversations outside the session, or documents a cross-session resume.**
  Then old-lane messaging becomes testable, and T033's F2 shrinks to skill text, as T033 itself
  said.
- **The per-task orchestrator cost drops well below 35k** — for example if a gate review reads less
  — and the 20–26 band, and any guidance written from it, moves with it.
- **A different context window.** The band scales with it: the same rate against 200k would mean
  four or five tasks per session, which would make the resume path the normal case rather than the
  exception.
- **Resume by handle starts failing inside a session.** E3 shows 55 successful resumes across two
  runs; if that changes, the lane model needs the stage checkpoints `DESIGN.md` already names as the
  trigger for reworking it.

## How to reproduce

Both scripts are throwaway and live outside the repository, as a spike's code should. They are
short, and the method matters more than the files:

```sh
# 1. Harvest every run this repository has recorded.
harvest.py --runs <checkout>/.git/taskrail/runs --sessions <the agent's project store>
```

- An orchestrator session is found, not named: it is the session holding the lane conversations
  whose names are the handles in the run file.
- Context per message = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.
- A compaction boundary is a record flagged as a compaction summary, a compaction boundary, or one
  carrying compaction metadata.
- A run's window runs from its `started` to the latest timestamp in its own run file, so one session
  driving several runs is measured once per run.

```sh
# 2. The fixture probe: a throwaway repository, one run, three lane states, no agent.
fixture.sh <workdir> <taskrail checkout>
```

It runs `init`, enables `[autopilot]`, creates four tasks, then `autopilot start --count 4`,
`autopilot next --run R`, three `autopilot lane` calls (`--state gate --gate scope`,
`--state running`, `--state escalated --gate implement --reason …`) and one `autopilot decision`,
prints `autopilot status --run R --json` and the run file, then creates the second lane's worktree,
claims the task there and prints the states again. The `RECORDED` tuple quoted in E5 is at
`src/taskrail/autopilot/status.py:20`.

## Limits

- **Time box:** 2 points, and the investigation stayed inside the 90 minutes agreed at the frame.
- **The aggregates in E1–E4 were derived locally from the agent's own session store, and their
  sources are not quotable here.** Token counts, message counts, durations and timestamps are facts
  about the tool's behaviour and belong in this document; no path, session identifier,
  peer-session name or transcript text does, and none appears.
- **No agent session was started**, not even a non-interactive one, so nothing here shows what a
  second session can reach. **No compaction was forced**, and no agent setting, permission or model
  was changed.
- **One agent only.** Everything measured is Claude Code with one model; the storage layout in E4 is
  that agent's, and another agent may differ. OpenCode was not exercised at all.
- **The current run is still open**, so its numbers are a snapshot taken at 2026-09-18T16:15Z and
  will have grown by the time it ends. The run measured itself: this task was one of its lanes.
- **Adopting any of this is follow-up work** — the three proposals above are tasks to open, not
  changes made here.
