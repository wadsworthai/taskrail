# T001 — Validate the taskrail skills by working a real task end to end

**Verdict: ready to release after three small skill-text fixes; one missing CLI command becomes
a follow-up.**

## Question

Can an agent carry a real task from selection to hand-off using only the taskrail skills and
the CLI, without the human supplying steps, paths or rules the skills left out?

## Approach

Agreed at the frame gate:

- **Task:** T006 — Add a reopen command (`feature`, 2 points). It exercises the plan, implement
  and verify stages, tests and the CLI itself, and is small enough to finish.
- **Executor:** a fresh Claude Code session that did not write the skills, started after the
  skills were installed so they load normally. The author of the skills would fill gaps in the
  text without noticing.
- **Prompt:** only "Work task T006 from the backlog", with no hints. Whether the agent finds the
  `taskrail` skill from that alone is part of the evidence.
- **Observation:** the branch, commits, claims and artifact the session produced, the gate
  questions the human received, and the session transcript.

## Limits

- One kind worked fully (`feature`), plus `spike` through this task. `bug` and `chore` were
  reviewed by reading only.
- Claude Code only; OpenCode was not exercised.
- A single agent: no subagent relay, no parallel lanes, no remote claims, no rebase conflict.
- Findings are recorded, not fixed here.

## Evidence

### What the executor did

From the transcript and the branch `T006-add-a-reopen-command-for-tasks-marked-do`:

1. Its first action on the bare prompt was loading the `taskrail` skill; after
   `taskrail show T006 --json` it loaded `taskrail-feature`. Discovery from a task ID works.
2. It created the worktree and claimed the task in one command, before any edit.
3. **plan** — it read the CLI sources and design, wrote the plan with eight numbered acceptance
   criteria, committed it with the index row, and asked three questions at the gate (where the
   reopen reason is recorded, whether discarded tasks can be reopened, plan approval). It
   committed the answers separately.
4. **implement** — it appended tests first and ran them, observing them fail on
   `invalid choice: 'reopen'`, then implemented. It edited the skill source rather than the
   installed copy and ran `taskrail upgrade`, as this repository's CLAUDE.md requires, and
   unprompted amended the close step's "`✅` wins" conflict rule, which would otherwise undo a
   reopen during a rebase. It opened the out-of-scope work as T012 with `taskrail new`.
5. **verify** — it exercised the command through the real CLI in a throwaway repository and
   through this repository's wrapper, recording each result.
6. **close** — `git fetch`, rebase (already up to date), `taskrail validate`, `taskrail done`
   committed on its own; the claim was released; no push, no merge, worktree kept; a hand-off
   report followed.

Result: 108 tests pass (98 before), `validate` reports no errors, the installed skill matches a
fresh render of its source, and the human reported the gates as adequate.

### Friction

| # | Where | What happened | Class | Proposed fix |
|---|---|---|---|---|
| F1 | Before step 1 | Skills installed by `taskrail init` during a running Claude Code session were not available as skills in that session. A fresh session loaded them normally. | integration | Say in the `init` output and README that the agent must be restarted after `init` or `upgrade`. |
| F2 | 3. Workspace | Local `main` was ahead of `origin/main`. The text does not say whether to base the worktree on the local or the remote mainline; both executors used local. | skill text | State that the base is the local mainline, and to mention it when it differs from its upstream. |
| F3 | Stage commits | A `frame` draft sat uncommitted while waiting at its gate, and T006's `verify` stage committed although its descriptor says `commit = false`. The descriptor does not say whether `false` means "do not commit" or "no commit required". | kind format | Define `commit = false` as "no commit required", and commit the `frame` draft. |
| F4 | T006 `implement` | T012 was created without its dependency, then corrected by editing `Depends On` with `sed`. No command edits an existing row, and the skill only allows hand-editing titles and descriptions. | CLI gap | Add `taskrail edit <ID>` for dependencies, points, title, description and custom columns; until then, allow hand edits of those cells followed by `validate`. |

### Observations

| # | Where | Observation |
|---|---|---|
| O1 | T006 `plan` gate | The executor asked where the reopen reason is recorded, which the task description never said. The gate surfaced an ambiguity in the backlog row instead of the agent guessing. |
| O2 | T006 `implement` | The noticed conflict-rule interaction shows the core skill gave enough context to reason about consequences beyond the task. |
| O3 | T006 overall | Reading the CLI sources and design took a large share of the session's context. Expected for a task that changes the CLI; not a skill defect. |

## Options considered

1. **Release now** and fix everything later. F2 and F3 affect every task, so every early adopter
   would hit them.
2. **Fix F1–F3 before tagging, F4 as a follow-up** — three wording changes; F4 is a new command
   with its own tests.
3. **Hold the release until F4 lands and `bug` and `chore` have been exercised too.** Better
   coverage, but those kinds share the procedure that just worked, and the stage-specific text
   is short.

## Recommendation

Option 2. Open follow-up tasks for F1–F3 (one `chore` changing the skill text, the `init` output
and the README) and for F4 (`feature`: `taskrail edit`), make T002 depend on the chore, and
exercise `bug` and `chore` naturally as the next real tasks of those kinds come up.

## What would change the decision

- A `bug` or `chore` task failing at a step the `feature` run did not reach.
- A rebase with a real backlog conflict going wrong: this run never hit one.
- An OpenCode run that cannot follow the harness-neutral text.

## How to reproduce

1. From `main` with taskrail installed, open a new agent session in the repository root.
2. Prompt only "Work task <ID> from the backlog" for a pending task, and answer its gates.
3. Inspect `git log main..<branch>`, `taskrail claims`, the artifact under `docs/`, and the
   session transcript (for Claude Code, under `~/.claude/projects/`).
