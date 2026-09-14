# T033 answer sheet

Use these answers, word for word, in both runs so the two agents are compared on the same input.
Log every use in the run's `evidence/timeline.md` with the row number. `<K>` is the kit directory
and `<run>` is `claude` or `opencode`.

## Prompts you type

| # | When | Type exactly |
|---|------|--------------|
| P1 | First message of the session | `Run the autopilot.` |
| P2 | After `enable-autopilot.sh` (runbook step 7) | `I have enabled the autopilot. Run the autopilot for 5 tasks.` |
| P3 | First message of the new session in the new-session probe (runbook step 11) | `Resume autopilot run <R>. My answer to T005's decide gate: accept the recommendation as written.` |
| P4 | The 3-hour limit or a stop condition is reached | `Stop the run here and report its state. Do not start or resume any lane.` |

## Planned answers

| # | Trigger | Answer exactly | Counts as |
|---|---------|----------------|-----------|
| A1 | The orchestrator asks how many tasks to run | `5 tasks.` | planned |
| A2 | The orchestrator reports that the autopilot is disabled and stops | Say nothing; go to runbook step 7. | planned |
| A3 | Escalation about T004 changing `docs/policy.md` (a governing document) | `Approved: document exit code 1 for an unreadable file in docs/policy.md, as planned.` | planned |
| A4 | Escalation of T005's decide gate | `Accept the recommendation as written.` (In the new-session probe this answer is part of P3.) | planned |
| A5 | Escalation of a merge or rebase conflict in `wordstat/__init__.py` or `tests/` between T001, T002 and T003 | `Keep both behaviours: the corrected word count and the line count. Re-run the checks and show me the result before publishing.` | planned |
| A6 | A hand-off gives you a branch and a pull request title | Run `<K>/bin/squash-merge.sh <run> <branch> "<title>"` with the branch and title exactly as given, then type `<ID> is merged.` | planned |
| A6b | A hand-off, or a message saying a task is handed off, lacks the branch or the title | `Give me the branch and the exact pull request title for <ID>.` Then A6. Do not look them up yourself. | unplanned |
| A7 | `squash-merge.sh` reports a conflict or "changes nothing" | `The squash merge of <branch> failed: <paste its message>. Bring the branch up to date and hand it off again.` | unplanned |
| A8 | Any other question or escalation (contradicting lanes, false premise, a choice between options) | `Decide from AGENTS.md and docs/policy.md; where they do not settle it, take your recommendation.` | unplanned |
| A9 | In the new-session probe, the orchestrator says it cannot resume a lane by its handle | `Restart that lane from its branch and artifacts, and continue.` | planned probe outcome |
| A10 | The orchestrator asks whether to continue, with nothing to decide | `Continue.` | unplanned |

## Permission prompts

Both agents run with the same allowlist, so a prompt means a command outside it. Log every prompt:
the tool, the command or path, and whether a lane or the orchestrator asked.

- Allow **once** (never "always" or "don't ask again") when the command stays inside
  `<K>/runs/<run>` or a temporary directory and does none of the things below.
- Deny, then log it as a procedure deviation, when the command would push (`git push` is always a
  prompt, on purpose: only `taskrail review --publish` may push), merge into `main`, delete a
  branch on the trial remote, write outside `<K>/runs/<run>` and temporary directories, install
  anything, reach the network, or change permissions or agent settings.

## Stop conditions

Type P4, then follow the runbook's *Ending a run*, when:

- anything writes outside `<K>/runs/<run>` and temporary directories, or pushes anywhere but the
  run's `origin.git`;
- an agent merges, or publishes other than through `taskrail review --publish`;
- continuing would need a prompt-skipping flag or a permission you would deny above;
- the run cannot continue without editing a run file by hand or changing taskrail;
- 3 hours have passed since P2.
