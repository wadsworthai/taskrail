# T033 — Trial the autopilot on a real backlog with each supported agent

**Verdict: the autopilot design works end to end on Claude Code, but it has three structural gaps
and a set of smaller skill-text and CLI defects. The OpenCode run is inconclusive.**

- **Claude Code:** the run merged 5 of 5 tasks in 2 h 57 min. Every planned escalation reached
  the human.
- **Three structural gaps:**
  - A stacked task loses its fork point once the orchestrator rebases the task it depends on at
    hand-off.
  - On Claude Code, a new orchestrator session restarts a lane from its branch. It does not resume
    the lane by its handle.
  - On OpenCode, blocking task calls leave the human no point at which to answer an escalation.
- **Permission prompts:** friction from prompts dominated the Claude Code run.
- **OpenCode run:** it used a different model than planned and stopped at its usage limit with
  0 of 5 merged, so it cannot confirm or refute the design on OpenCode.

**Gate outcome:** the human accepted the verdict and option 2 at the decide gate, and asked for every
proposed follow-up task to be opened
([decision record](../autopilot/decisions/T033-trial-the-autopilot-on-a-real-backlog-wi.md)). T033
closes with this evidence as it is.

## Question

Does the autopilot as designed in [DESIGN.md §12](../../DESIGN.md) — the
`taskrail autopilot` commands (T029–T032) and the `taskrail-autopilot` skill with its Claude Code
and OpenCode notes (T024) — carry a small backlog from "run the autopilot for N tasks" to N
squash-merged tasks on **both** Claude Code and OpenCode, and where does it not?

"What the design got wrong" is made concrete as twelve checks, agreed at the frame gate
([decision record](../autopilot/decisions/T033-trial-the-autopilot-on-a-real-backlog-wi.md)):

| # | Check | Design |
|---|---|---|
| D1 | **Opt-in.** Asked without a count, the orchestrator asks for one and does nothing else. With `[autopilot].enabled` unset, `autopilot start` exits 5 and the orchestrator stops. | §12.1, §12.2 |
| D2 | **Dispatch.** `autopilot next --run R`, lane briefs from its JSON, lanes of one dispatch launched together, handles recorded at once, freed lanes refilled, never more than the count. | §12.1, §12.7 |
| D3 | **Lane contract.** `--no-track`, `claim --run R`, a stop at every `always` gate, a stop after `done` and `review --json` without rebasing or publishing. | §12.3 |
| D4 | **Resume at gates** by handle, with context intact; on OpenCode, what answering in waves costs. | §12.3 |
| D5 | **Handles across compaction**, and whether a new orchestrator session resumes the previous session's lanes. | §12.3, §12.4 |
| D6 | **Gate review and decision records.** Checks re-run by the orchestrator; each decision recorded and committed before the lane resumes; the touch map through `autopilot decision`. | §12.5 |
| D7 | **Escalation.** Governing paths and `escalate_gates` flagged and escalated; judgement escalations raised; other lanes keep going. | §12.6 |
| D8 | **Supervision.** `status` on every wake; `silent` and `overlaps` acted on. | §12.6 |
| D9 | **Hand-off** one branch at a time: rebase, re-run checks, `review --publish`, exact title and link, no merge. | §12.8 |
| D10 | **Merge follow-through.** `merged --cleanup` proves the squash merge, stacked dependents move with `--onto`, known conflict classes resolved, the rest escalated. | §12.8 |
| D11 | **CLI outputs** misread, or needed and missing. | §12.1 |
| D12 | **Friction and cost**, and whether sequential hand-off catches enough to justify its rebases. | §12.8, §12.10 |

Each finding is classed as **design**, **skill text**, **CLI bug**, **CLI gap**, **integration
note** or **agent limitation**. A **model** effect is kept apart: it is a mistake the text already
rules out, or behaviour that may belong to the model rather than the agent.

## Evidence

### What was run

Taskrail was pinned at `977064f` and the seed repository was at commit `c7836e0` for every run.
The human rebuilt the kit with the same `prepare.sh` at another local path, and the kit built at
the frame was not used. The trial's coordinator, not the human, ran the helper scripts (enable,
snapshot, squash merge, finish) and kept the timelines from the human's reports. The raw evidence
stays on the trial machine under `<kit>/runs/<run>/evidence/`: status captures, snapshots, run
files, `notify.log`, `merges.log`, timelines and transcripts. This document quotes only
excerpts, cleaned of anything private.

| Run | Agent and model | Outcome | Time from P2 | Merged |
|---|---|---|---|---|
| `claude` | Claude Code 2.1.270, Opus 5 (1M context) | **aborted**: P2 was pasted with an extra line. The orchestrator dispatched T001, T003 and T004, the human stopped the lanes and rewound the conversation, and the rewound session found the first run holding all lanes. The human stopped. | 8 min | 0/5 |
| `claude2` | Claude Code 2.1.270, Opus 5 (1M context) | **complete** | 2 h 57 min (13:53:39Z → `complete` at 16:50:29Z) | 5/5 |
| `opencode` | OpenCode 1.15.13, **`opencode-go/glm-5.3`** | **partial**: stopped by the human's OpenCode plan usage limit (the last task calls aborted at 18:25:08Z); P4 was not sent | 1 h 13 min to the last capture | 0/5 |

Deviations from the runbook:

- **`claude2` started in Claude Code's auto permission mode.** The classifier approved early
  commands on its own and blocked the first `review --publish` push (`[Blind Apply]`). The human
  switched to manual mode at that point, 14:08Z. The runbook did not name a permission mode.
- **`claude2` skipped the compaction step (`/compact`),** so D5 compaction was not exercised.
- **The OpenCode run used a different model.** The human's OpenCode setup had no
  `github-copilot/claude-opus-5`, so the coordinator edited the run's `opencode.json` to
  `opencode-go/glm-5.3`. The comparison therefore mixes agent and model.
- **Human slips in the OpenCode run:**
  - a first session answered the count question with "2", met the exit-5 refusal, and was left;
  - the second session began with a typo ("exith");
  - the human worked this run mostly without relaying to the coordinator, so its timeline is thin.
- **`finish.sh` exported only OpenCode's top-level sessions,** because `opencode session list`
  does not show child sessions. The five lane sessions were exported afterwards with
  `opencode export <handle>`, using the handles in the run file.

### Checks

| Check | `claude` (aborted) | `claude2` | `opencode` |
|---|---|---|---|
| D1 | pass | pass: asked for the count with `AskUserQuestion`; exit 5 reported, config untouched | pass: exit 5 reported, config untouched. It read `TODO.md` and suggested "All 5 tasks (Recommended)" before the count was given (model) |
| D2 | pass: three lanes in one message, handles recorded | pass: lanes of each dispatch launched in one message, handles recorded within a minute, ports passed and used, count respected. The refill started 10–13 min after lanes freed (F5) | pass, with a gap: the three lane calls ran concurrently, but handles reached the run file only when the batch returned, 8 min after dispatch (F3) |
| D3 | not exercised | pass: all five lanes branched `--no-track`, claimed `--run`, stopped at every `always` gate, stopped after `done` and `review --json`; none rebased, pushed or published | pass for the stages reached |
| D4 | not exercised | pass: 10 resumes with `SendMessage`, context intact | pass: 5 resumes with `task_id`, context intact. Waves cost 1–4 min per gate (a lane that stopped first waited for the slowest) |
| D5 | not exercised | compaction **not exercised**. New session **partial**: the new orchestrator rebuilt the run from `status` and the records, but started a fresh lane for T005 from its branch instead of resuming the old handle (F2) | not exercised |
| D6 | not exercised | pass: checks re-run with each lane's port, deliberate breakages, the CLI exercised, every record committed before its `SendMessage`, 5 run decisions through `autopilot decision`, copied into the records. One run decision rested on a false premise (F6); `lane --gate close` was refused (F10) | pass for the gates reached: records committed before each resume, checks re-run, touch map recorded |
| D7 | — | pass: T004's policy edit escalated at its scope gate, the T001/T003 `stats()` conflict raised before it happened, T005's decide gate escalated; `notify` each time; other lanes kept working. The `governing` flag stayed on after approval until the merge (F9) | **fail**: T004 was recorded `escalated` and notified at 17:23Z, but the question reached the human at 17:45Z just before a new blocking batch, and was never answered before the stop (F3) |
| D8 | the rewound session found the other run and asked | pass: `status` on every wake; the touch map built from `overlaps`. One transient `silent` flag (T005, 14:49Z) came while the orchestrator had no reason to wake. `overlaps` were dominated by known-class files (F12) | partial: T005 was `silent` at 18:20Z while the orchestrator was blocked in its batch and could not see it (F3) |
| D9 | — | pass with friction: one branch at a time, rebase, re-run checks, publish. The first hand-off (T003) gave no branch or title (F4). `handoff.next` changed while the orchestrator rebased (F8) | partial: T003 published one at a time and recorded `handed-off`, but its title and body never reached the human (F4) |
| D10 | — | pass, by judgement: all five merges proved by content (`via: tree`) and cleaned up. T002, stacked on T001, was reported `stacked: false` with no command, and the orchestrator worked out `rebase --onto` itself (F1). The one conflict outside the known classes was handled as the human had decided | not exercised |
| D11 | — | misread: IDs per branch (F6). Refused: `--gate close` (F10). Misleading output: `dependents` (F1), `handoff.next` (F8), the lasting `governing` flag (F9) | none seen in the orchestrator |
| D12 | the rewind left a run nobody can close (F7) | dominated by permission prompts (F11); sequential hand-off caught one real conflict before review | stopped by the usage limit; model substitution |

### Findings

| # | Class | Agents | What happened | Evidence |
|---|---|---|---|---|
| F1 | design, CLI bug | Claude Code | **A stacked dependent loses its fork point.** T002 branched from T001's tip `6afaec6`. At hand-off the orchestrator rebased T001 onto T003's merge, as §12.8 says, so T001's merged head `313684a` no longer contains `6afaec6`. T002's claim, which held `base.commit`, had been released by `done`. `autopilot merged T001 --cleanup` then fell back to `merge-base` and reported the dependent as not stacked. The orchestrator moved T002 with `git rebase --onto origin/main 6afaec6`, using the `base.commit` it remembered from `next`. DESIGN §12.8 documents this fallback as an edge case, but the design's own hand-off procedure makes it the normal case for every stacked task. | `"dependents": [{"id": "T002", "stacked": false, "fork": "6ac653f…", "fork_source": "merge-base", "command": null}]`; decision record: "T002's copy of T001 ends at 6afaec6, which differs from T001's merged head 313684a only by T003's merged changes" |
| F2 | agent limitation, design | Claude Code | **A new session restarts lanes rather than resuming them.** After `/exit` and a fresh session (P3), the orchestrator said: "the lane that stopped at the decide gate belonged to the earlier session and couldn't be resumed. I started a new one from the same commit." It did not try `SendMessage` to the old ID, so whether that works is unverified. It wrote its own brief ("Workspace — already exists, you are resuming"), and the lane closed T005 correctly because everything up to the gate was committed. §12.3 claims "a compacted or new orchestrator session can resume the lanes"; for a new Claude Code session, the evidence shows a restart from the branch. | new session: `ListAgents` (lists peer sessions, not subagents), then `Agent` "T005 lane: close spike"; `lane T005 --handle <new> --state running` |
| F3 | integration note, possible model effect | OpenCode | **Blocking waves leave no point to answer the human.** The orchestrator recorded T004 `escalated` and notified at 17:23Z, resumed T001 and T003 in a blocking batch, asked the human in plain text at 17:45Z, and immediately started another blocking batch. It never ended its turn, so T004 stayed escalated for 57 min until the stop. The same blocking hid T005's `silent` flag (18:20Z), and handles could only be recorded when a batch returned. In that time a lane write to `/tmp/opencode` took 421 s, consistent with a pending permission prompt (unverified). Whether a Claude model on OpenCode would end its turn at an escalation is not known. | `17:23:37 lane T004 --state escalated … && notify`; `17:45:08` question text, then `17:45:22` task calls; status `T004:escalated@scope` from 17:24Z to 18:20Z |
| F4 | skill text | both | **The first hand-off lacked the branch and title on both agents.** Claude Code: "T003 is handed off and waiting for you to review and merge it", without branch or title; the coordinator looked them up with `taskrail review T003 --json --no-fetch`. OpenCode: "I'll relay the title and body", which never happened. Later Claude Code hand-offs gave title, branch and body. | transcripts at 14:20Z (Claude Code) and 17:49Z (OpenCode) |
| F5 | skill text | Claude Code | **The refill waited.** T001 became `done-branch` at 14:04Z and T003 was handed off at 14:07Z, but `next --run` ran at 14:17Z. The skill's refill trigger lists "handed off, failed, discarded" but not `done-branch`, which already frees a lane (§12.7). | status captures 14:04Z–14:18Z |
| F6 | skill text | Claude Code | **A false premise about IDs.** Run decision 4: "Each branch allocates IDs from its own TODO.md", so other lanes were told not to run `taskrail new`, and T005's follow-ups were deferred until hand-off. `taskrail new` reserves IDs under a common-directory lock across worktrees and branches (DESIGN §6.3), and the autopilot skill does not say so. | run decision 4; T005 decision record |
| F7 | CLI gap, skill text | Claude Code | **A run cannot be abandoned.** A conversation rewind restores the conversation, not the run file. After the rewind, run `20260914-1` still recorded three dispatched tasks holding all three lanes, and the rewound session started `20260914-2` and had to ask. The run offers no close or abandon command, and the skill does not say that a dispatch expires after `[git].claim_grace_minutes` (15). | final snapshot: `T001/T003/T004 dispatched` in run 1; run 2 decision 1 "Stop run 20260914-2; dispatch nothing" |
| F8 | CLI bug | Claude Code | **`handoff.next` is unstable.** The queue is ordered by the branch tip's commit time (`status.py` `_handoff`), and the orchestrator's own rebases and decision-record commits move a task to the back. `next` went T001 → T004 during T001's rebase (14:40Z → 14:41Z), and T004 → T002 during T004's rebase (15:29Z → 15:30Z). The orchestrator kept its own order, which matched the design's "completion order". | status captures |
| F9 | CLI gap | Claude Code | **The `governing` flag cannot be acknowledged.** T004 kept `escalation: ["governing"]` from 14:03Z through `done-branch` and `handed-off` until its merge at 16:32Z, after the human had approved the edit. `escalate_gate` is dropped once a task moves on, but `governing` is not. | status captures |
| F10 | CLI gap | Claude Code | **The close stop has no gate name.** `autopilot lane T003 --state gate --gate close` failed: `` `close` is not a stage of kind bug (diagnose, fix, impact) ``, exit 2. The skill and gate review treat the stop after `done` as a gate to review, but no stage names it. | transcript 14:03Z |
| F11 | integration note, CLI gap | Claude Code | **Permission prompts dominated.** Orchestrator and lanes used compound commands (`cd … &&`, shell variables, `$?`, heredocs, `git -C` sequences) that the shared allowlist cannot match, and Claude Code checks them part by part. The human approved dozens of prompts; one orchestrator command waited 50 min for its result (15:30Z → 16:20Z), consistent with a pending prompt. Some prompts seemed not to register until the number key was pressed. Neither agent records prompts in its transcripts, so the count is the timeline's estimate. | timeline; long waits: orchestrator 11 tool calls over 45 s in session 1 and 10 in session 2 |
| F12 | CLI gap | both | **`overlaps` is dominated by known-class files.** `CHANGELOG.md`, `TODO.md` and the index READMEs overlap between every pair of lanes, which buries the one real overlap (`wordstat/__init__.py`, T001 and T003). | status captures |
| F13 | CLI bug (unconfirmed) | Claude Code | **A brief `pending` window.** Between `taskrail done` (claim released) and its commit, T002 showed `pending` and dropped out of `touched` (14:39:22Z). Its dispatch was older than the claim grace, so a `next --run` in that window could offer T002 again. Seen once in a capture; not reproduced. | status capture 14:39:22Z |

Also observed, not counted as design faults:

- **Merge detection:** the orchestrator detected T003's merge by content before the human said it
  was merged. All five merges were proved by `tree`, because `squash-merge.sh` squashes branches
  already rebased onto `main`; the patch-id and merge-tree checks were not exercised.
- **Sequential hand-off paid for itself:** 4 rebases at hand-off. One conflict outside the known
  classes (`stats()`) was resolved and shown to the human before review; the rest were classes
  1–2. The §12.10 condition for adding `batch` is not met.
- **Notifications:** every `notify` call ran the configured command, 7 in `claude2` and 2 in
  `opencode`.
- **Scope:** a Claude Code lane (T005) read another lane's worktree without editing it.
- **Follow-ups:** T006 was created by the T004 lane with the orchestrator's approval; T007 and T008
  were created by the orchestrator on T005's branch at hand-off.

### Model effects in the OpenCode run

The following are recorded apart from the design findings:

- The first `question` call failed its schema.
- It suggested a count instead of only asking for one.
- A lane edit targeted a mistyped file name.
- There were pauses of 5–9 min between tool calls near the usage limit; the cause is not verified.
- It did not use the `question` tool for the escalation (see F3).

It followed the procedure closely otherwise: decision records before resumes, checks re-run with
the lane ports, handles recorded, no forbidden command in any lane.

### Measures

| Measure | Claude Code (`claude2`) | OpenCode (`opencode`) |
|---|---|---|
| Gates answered by the orchestrator | 11 (incl. T005 decide, escalated) plus 5 close reviews | 6 plus 2 close reviews |
| Escalations | 3 planned (T004 policy, `stats()` conflict, T005 decide); 1 unplanned (publish blocked by auto mode) | 1 planned (T004), unanswered |
| Rebases at hand-off | 4: one conflict outside the known classes, the rest classes 1–2 | 0 |
| Merges proved | 5, all `via: tree` | — |
| Decision records | 5 on `main`; 5 run decisions | 5 on task branches; 1 run decision |
| Human interventions beyond the answer sheet | publish permission question; permission mode switch; T003's title looked up; dozens of permission approvals | model substitution; stop at the usage limit |
| Cost reported by the agent | USD 22.17 and 6.50 for the two orchestrator sessions; whether subagent usage is included is not documented | USD 3.00 for all seven sessions |

The costs are the agents' own estimates for different models and are not comparable.

### Not verified

- **Compaction (D5)** on either agent.
- **Old Claude Code lane IDs from a new session:** whether `SendMessage` still reaches them (F2).
- **Resume from a new OpenCode session.**
- **OpenCode with a Claude model,** or with background subagents.
- **Permission prompts:** the exact count on Claude Code, and whether the 421-s OpenCode write was
  waiting on a prompt.
- **Merge detection by patch-id or merge-tree,** a stacked merge detected with a live claim, and a
  run with a real hosted pull request.
- **F13's re-dispatch window.**

### Environment

Checked at the frame without installing anything:

| Tool | Version |
|---|---|
| Claude Code | 2.1.270 |
| OpenCode | 1.15.13 |
| git | 2.55.0 |
| uv | 0.11.16 |
| Python | 3.14.7 |

At the frame, OpenCode listed `github-copilot/claude-opus-5`; at run time the human reported no
access to it in OpenCode.

Frame probes in a throwaway repository:

- `init --integration claude --integration opencode` writes both agents' notes into
  `.claude/skills/`, and OpenCode discovers the six skills there.
- The `general` subagent denies `question`.
- `autopilot start` exits 5 until the autopilot is enabled.
- With a local remote, `review --publish` returns no link.
- A relative bare-remote path breaks `review` inside a worktree, so the kit uses an absolute one.

### The trial kit

[`T033-trial-kit/`](T033-trial-kit/RUNBOOK.md) holds everything the trial needs:

- the [runbook](T033-trial-kit/RUNBOOK.md) and the [answer sheet](T033-trial-kit/ANSWERS.md);
- `prepare.sh`, which exports taskrail at a commit and bundles the `wordstat` seed;
- `new-run.sh`, `enable-autopilot.sh`, `squash-merge.sh`, and `capture.sh`, `snapshot.sh`,
  `finish.sh`;
- one allowlist rendered for each agent;
- `check-kit.sh`, the CLI-only dry run;
- `status-timeline.py`, which condenses the status captures.

The seed's five tasks:

| Task | What it exercises |
|---|---|
| T001 `--lines` | first dispatch and hand-off |
| T002 `--json` | stacked on T001 |
| T003 whitespace bug | the same function as T001 |
| T004 policy exit code | a governing path |
| T005 Unicode spike | `spike:decide` escalated |

Fixed after the runs, for the deviations they caused:

- **Runbook:** Claude Code starts with `--permission-mode manual`, and the permission mode is
  logged.
- **Runbook:** the OpenCode model is checked with `opencode models` before starting, and the run
  stops rather than substituting.
- **Runbook:** a checklist of the probes that are easy to miss, a stronger compaction step, and P2
  typed as one line.
- **Answer sheet:** A6b, so the human asks the orchestrator for a missing branch or title instead
  of looking it up.
- **`finish.sh`:** also exports OpenCode lane sessions from the handles in the run files.

After the fixes, `check-kit.sh` still passes every line on a freshly prepared kit.

## Options considered

1. **Accept the design as is** and fix only the skill text. This leaves F1 (every stacked task needs
   judgement at merge), F3 (OpenCode escalations cannot be answered) and F7 (a stale run cannot be
   closed) in place.
2. **Accept the design with targeted changes:**
   - CLI fixes for F1, F7, F8, F9, F10 and F12;
   - skill-text fixes for F2, F4, F5 and F6;
   - an OpenCode integration note for F3;
   - a Claude Code integration note and a command shape that fits allowlists (F11);
   - a second, smaller trial for what this one could not verify.
3. **Rework the lane model:** lanes checkpoint their stage in the run file and are always restartable,
   and OpenCode requires background subagents. Better supported by the evidence only if resume by
   handle fails more widely than one new-session probe shows.

## Recommendation

Option 2. The Claude Code run shows the design's core working without a human supplying steps:
opt-in, dispatch, the lane contract, gate review with records, escalation, sequential hand-off and
merge detection. What went wrong is specific and fixable.

Follow-up tasks, opened in epic E02 after the human accepted them at the decide gate. The human
also decided how they are verified: by short automated tests (pytest with fixture repositories,
scripted git scenarios, tests that assert the rules in the skill sources and installed copies),
never by an end-to-end trial like this one, which is long and needs a human at several terminals.

| Task | Proposal | Kind | Fixes |
|---|---|---|---|
| T047 | Keep a stacked dependent's fork point after `done`: record `base.commit` in the run file at claim and use it in `autopilot merged` before `merge-base` | feature | F1 |
| T048 | Add `autopilot close <run> --reason …` to abandon a run, releasing its dispatches and resources and hiding it from `next` | feature | F7 |
| T053 | Order the hand-off queue by the `done` commit, not the branch tip | bug | F8 |
| T049 | Stop flagging `governing` once a task is `done-branch`, or after a recorded approval | feature | F9 |
| T050 | Accept `--gate close` for the stop after `done` | feature | F10 |
| T051 | Separate known-class files (backlog, changelog, indexes) in `overlaps` | feature | F12 |
| T054 | Fix the `pending` window between `done` and its commit, starting from a failing test that scripts it | bug | F13 |
| T055 | Autopilot skill text: a hand-off message that always carries branch, title and body; refill on `done-branch`; IDs from `taskrail new` are unique across lanes; dispatch expiry; resuming a run from a new session with a restart-from-branch lane brief, and §12.3 reworded to match | chore | F2, F4, F5, F6, F7 |
| T056 | OpenCode integration note: at an escalation, end the turn with the question instead of starting another blocking batch; record handles when a batch returns; check `silent` between batches | chore | F3 |
| T052 | Claude Code integration note on command shape (one command per call, absolute wrapper path, no `cd … &&`), plus a `taskrail checks <ID>` that runs a lane's configured checks in its worktree with its resources, so one allowlist entry covers them | feature | F11 |
| T057 | A scripted probe instead of a second trial: a small fixture and a bounded, non-interactive script for compaction and messaging an old lane, with no human terminals and no change to agent settings; what cannot be scripted (including OpenCode on a Claude model) is stated as a limit | spike | not verified |

## What would change the decision

- **A new Claude Code session can `SendMessage` an old lane ID:** F2 becomes skill text only.
- **Resume by handle fails after compaction too:** option 3, since lanes would need stage
  checkpoints and restart as the only recovery.
- **OpenCode with a Claude model ends its turn at escalations:** F3 becomes a model effect, and the
  OpenCode note shrinks to a warning.
- **A hosted squash merge that alters content defeats `tree`:** merge detection needs the patch-id
  and merge-tree paths tested first, before any F1 work relies on it.
- **The fixed permission guidance still leaves dozens of prompts:** the autopilot needs an
  agent-side permission profile as adapter packaging.

## How to reproduce

```bash
# From a checkout of this branch: build the kit, check it without any agent, create a run.
docs/spikes/T033-trial-kit/prepare.sh /var/tmp/taskrail-t033-trial 977064f
K=/var/tmp/taskrail-t033-trial
$K/bin/check-kit.sh                     # every line PASS
$K/bin/new-run.sh claude                # then follow RUNBOOK.md step by step, ANSWERS.md for input

# Analysis, per run, once finish.sh has closed the evidence:
python3 $K/bin/status-timeline.py $K/runs/claude/evidence/status      # state changes, flags, overlaps
cat $K/runs/claude/evidence/final.txt $K/runs/claude/evidence/notify.log $K/runs/claude/evidence/merges.log
ls $K/runs/claude/evidence/snapshots/*/runs                           # run files at each snapshot
# Claude Code transcripts: evidence/transcripts/claude/<session>.jsonl and <session>/subagents/*.jsonl
# OpenCode transcripts: evidence/transcripts/opencode/<session>.json (orchestrator and lanes)
```

The findings come from reading those files:

- **Tool calls in order:** each `tool_use` block and its `tool_result`, with timestamps. For
  OpenCode, the `parts` of type `tool` with their `state.time`.
- **Output fields quoted above:** from the tool results of `autopilot merged`, `autopilot lane` and
  `autopilot decision`.
- **F8, F9, F12 and F13:** from the status timeline.

## Approach and limits

As agreed at the frame gate:

- **Backlog and roles:** a synthetic public backlog with a local bare remote. The human drove the
  orchestrator sessions and answered from the answer sheet.
- **Allowlist and pinning:** one allowlist on both agents, never a prompt-skipping flag. Taskrail
  was pinned at `977064f` with no patches between runs.
- **Time box:** 2 points of analysis, at most 3 hours per run.
- **Out of scope:** lane model pinning, `batch` hand-off, runs across machines, host APIs,
  OpenCode's background subagents, fixing any finding here, and any consumer project.
