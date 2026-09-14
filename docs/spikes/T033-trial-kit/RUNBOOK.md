# T033 trial runbook

Step by step for the person who plays the human in the T033 trial: one autopilot run on Claude
Code, then one on OpenCode, on the same synthetic backlog. The kit is throwaway tooling for this
spike, not part of taskrail. What is being checked is in the
[spike](../T033-trial-the-autopilot-on-a-real-backlog-wi.md) (checks D1–D12); the answers you give
are in [ANSWERS.md](ANSWERS.md).

## What you need

- About 3 hours per run, plus 15 minutes of setup, with attention at escalations and merges.
- `claude` logged in; `opencode` with GitHub Copilot credentials offering
  `github-copilot/claude-opus-5`; `git` 2.38 or later, `uv` and `python3`.
- Three terminals: **A** for the agent, **B** for the capture loop, **C** for helpers.
- Your normal agent setup. Do not add or remove plugins, hooks or MCP servers between the two runs,
  and write down in the timeline anything unusual you have enabled.
- Never start an agent with a prompt-skipping flag (`--dangerously-skip-permissions`, OpenCode's
  `--auto`), and never with `--continue`, `--resume` or `--session`.

The examples use `K=/var/tmp/taskrail-t033-trial` and the run names `claude` and `opencode`.

## Once: build and check the kit

From a checkout of this repository on the T033 branch:

```bash
docs/spikes/T033-trial-kit/prepare.sh /var/tmp/taskrail-t033-trial 977064f
/var/tmp/taskrail-t033-trial/bin/check-kit.sh      # every line PASS, ends with "removed …/dryrun"
```

`prepare.sh` exports taskrail's source at the pinned commit into `$K/taskrail`, copies the scripts
into `$K/bin`, and bundles one seed repository into `$K/seed/seed.bundle`, so both runs start from
the same commit. `check-kit.sh` exercises the kit through the taskrail CLI alone, with no agent.

## Each run

Four moments are easy to miss; keep this list in view during the run:

- step 6: the disabled refusal is observed before the autopilot is enabled;
- step 10: `/compact` after the first answered gate;
- step 11: the new-session probe at T005's decide gate;
- every hand-off: merge at once, and log whether the orchestrator gave the branch and the title.

Whoever runs the helper scripts and keeps the timeline, every prompt and answer typed in terminal A
goes into the timeline as it happens; the analysis cannot recover an unlogged answer from the
status captures.

Do the Claude Code run first. For the OpenCode run, repeat every step with `opencode` as the run
name; the differences are marked.

1. **Create the run.** In terminal C:

   ```bash
   K=/var/tmp/taskrail-t033-trial
   $K/bin/new-run.sh claude
   ```

   It creates `$K/runs/claude/` with `origin.git` (the trial remote), `repo` (the orchestrator's
   clone, with `.claude/settings.local.json` and `opencode.json` holding the same allowlist) and
   `evidence/`.

2. **Start the capture loop.** In terminal B: `$K/bin/capture.sh claude`. Leave it running.

3. **Open the timeline.** Open `$K/runs/claude/evidence/timeline.md` in an editor and add a first
   row with the time. Every prompt, answer, permission prompt, merge, compaction and surprise gets
   a row.

4. **Start the agent.** In terminal A:
   - Claude Code: `cd $K/runs/claude/repo && claude --permission-mode manual`. Trust the folder
     when asked. Check that the footer shows no permission mode such as *auto* or *accept edits*
     (Shift+Tab cycles it; leave it on manual), run `/model`, and log both; keep the default
     model. Auto mode changes which commands prompt, so the two agents would no longer run under
     the same allowlist.
   - OpenCode: first check that `env | grep OPENCODE_EXPERIMENTAL` prints nothing and that
     `opencode models | grep -x github-copilot/claude-opus-5` prints the model. **If it does not,
     stop here** and tell the T033 lane: the comparison needs the same model on both agents, and a
     substitute is a decision for the spike, not for the run. Otherwise run
     `cd $K/runs/opencode/repo && opencode`, check that the model shown is
     `github-copilot/claude-opus-5` (set by `opencode.json`), and log it.

5. **D1, no count.** Type **P1**. Expected: the orchestrator asks how many tasks and does nothing
   else. Answer **A1**.

6. **D1, disabled.** Expected: it runs `taskrail autopilot start`, gets exit 5, reports that the
   autopilot is disabled, and stops (**A2**). If it works tasks anyway or edits
   `.taskrail/config.toml`, log it, type `Stop.`, run `$K/bin/snapshot.sh claude d1-fail`, and undo
   its changes with `git -C $K/runs/claude/repo checkout -- .` before going on.

7. **Enable and start.** In terminal C: `$K/bin/enable-autopilot.sh claude`. Then type **P2** in
   terminal A as a single line, with nothing before or after it, and log the time: the 3-hour limit
   counts from here.

8. **While the run works.** Answer only from ANSWERS.md. Take a snapshot at each of these moments
   with `$K/bin/snapshot.sh claude <label>`, using labels such as `T004-escalation`,
   `T001-handoff`, `T001-merged`:
   - an escalation reaches you;
   - a hand-off reaches you, and again after you report the merge;
   - anything unexpected.

   To look at the run yourself, use `cd $K/runs/claude/repo && .taskrail/bin/taskrail autopilot status`
   in terminal C. Never edit files in the run or its worktrees.

9. **Merges.** For each hand-off, follow **A6**:

   ```bash
   $K/bin/squash-merge.sh claude <branch> "<pull request title>"
   ```

   then type `<ID> is merged.` Merge each branch as soon as it is handed off.

10. **D5, compaction — do not skip.** Put a note next to terminal A before the run starts, since
    this probe comes while you are busy. The first time the orchestrator has answered a lane's
    gate and resumed it (it says so, or `status` shows the lane `running` again after a `gate`),
    wait until the orchestrator is idle — on OpenCode, until its task calls have returned — then
    type `/compact`, take a snapshot labelled `after-compact`, and log the time. If the moment
    passed unnoticed, do it at the next idle moment and log the delay; log "not exercised" only if
    the run ends first.

11. **D5, new session.** When T005's decide gate is escalated to you (**A4**), do not answer in
    that session. Wait until `status` shows no lane `running` (only `gate`, `escalated`,
    `done-branch` or later), then:
    - take a snapshot labelled `before-new-session`, and note the run ID `<R>` from `status`;
    - quit the agent (`/exit` on Claude Code; exit the OpenCode TUI);
    - start a **fresh** session in the same directory as in step 4, without `--continue`;
    - type **P3** with the run ID, and log whether it resumes the waiting lanes by their handles.
      If it says it cannot, answer **A9**.

    If T005 never escalates, do this probe at the first moment when no lane is `running` and one
    is stopped at a gate, with P3's second sentence left out; if there is no such moment, log
    "D5 new-session not exercised".

12. **Ending a run.** The run ends when the orchestrator reports it complete, when 3 hours have
    passed since P2 (type **P4**), or at a stop condition from ANSWERS.md (type **P4**). Then:
    - log the time and the reason;
    - quit the agent;
    - stop the capture loop in terminal B with Ctrl-C;
    - in terminal C: `$K/bin/finish.sh claude`.

    `finish.sh` takes a final snapshot, runs `taskrail validate` and the checks on the remote's
    `main`, copies the decision records, and copies the transcripts: Claude Code's from
    `~/.claude/projects/<this run's directory>/`, OpenCode's through `opencode export` for every
    session in this run's directory.

## After both runs

Tell the orchestrator of the T033 lane: `continue T033 — both runs finished; evidence in
/var/tmp/taskrail-t033-trial/runs/claude and /var/tmp/taskrail-t033-trial/runs/opencode`, with any
run that ended early and why.

The evidence stays on this machine: transcripts contain local paths and account details. The spike
quotes cleaned excerpts only. `/var/tmp` survives a reboot; delete `$K` once the spike is decided.

## What the seed contains

`wordstat`, a Python standard-library tool that counts words, with unit tests, `AGENTS.md` (and a
`CLAUDE.md` importing it), a changelog, an output policy in `docs/policy.md`, and taskrail
installed for both agents with taskrail pinned through `.taskrail/src`. The backlog:

| ID | Kind | Pts | Depends on | Title | Meant to exercise |
|----|------|-----|------------|-------|-------------------|
| T001 | feature | 1 | — | Add a --lines flag that also reports the line count | first dispatch; plan, implement and verify gates; a changelog bullet (conflict class 2); hand-off and merge |
| T002 | feature | 2 | T001 | Add a --json flag that prints the statistics as one JSON object | a stacked base on T001's branch, rebased with `--onto` after T001's squash merge; dispatched when a lane frees |
| T003 | bug | 1 | — | Stop miscounting words around repeated whitespace and newlines | first dispatch; the same function as T001 (touch map, and a conflict outside the known classes unless the touch map avoids it) |
| T004 | chore | 1 | — | Document the exit code for an unreadable file in the output policy | first dispatch; touches the governing `docs/policy.md`, which `status` flags and must escalate |
| T005 | spike | 2 | — | Decide whether word counting should follow Unicode word boundaries | dispatched when a lane frees; `spike:decide` is in `escalate_gates` |

Configuration: `[autopilot]` starts with `enabled = false`; `max_lanes = 3`;
`governing = ["AGENTS.md", "CLAUDE.md", "docs/policy.md"]`; `escalate_gates = ["spike:decide"]`;
`notify` appends each event to `evidence/notify.log`; a `PORT` resource pool of three values that
the tests bind when a lane passes one; checks `python3 -m unittest discover -s tests -q` and
`python3 -m compileall -q wordstat tests`.

The allowlist, the same for both agents: the taskrail wrapper (relative and absolute), `git` with
`git push` always asking, the checks, `python3 -m wordstat`, `cd`, `ls`, `cat`, `head`, `tail`,
`wc`, `grep`, `rg`, `diff`, `sort`, `pwd`, `echo`, `date`, and file edits inside the run's clone.
Web access and paths outside the clone ask.
