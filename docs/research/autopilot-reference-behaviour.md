# Autopilot: reference behaviour

Input for T007. What the autopilots of two existing projects do today, gathered from their own
agents reading their repositories, and generalised. taskrail's autopilot must cover this
behaviour agnostically — as a skill and CLI support installed with the other skills — while each
repository decides whether to use it.

"Both" marks behaviour the two projects share; otherwise the behaviour is one project's.

## Invocation

- The human gives the number of tasks to complete; without it the autopilot does not start. (both)
- It completes that many tasks, handing each finished branch to the human for review.

## Lanes

- Up to three tasks run in parallel, each in its own lane: a subagent in its own worktree. (both)
- At most one lane at a time works on user-interface tasks. One project derives "UI" from a column
  value, the other from a judgement about the task. (both)
- One project pins lanes to a cheaper model than the orchestrator.
- Lanes gather information and return questions; only the orchestrator talks to the human. (both)
- Lanes never start shared services themselves. (both)

## Eligibility and order

- A task is eligible when it is pending, not failed, and either every dependency is merged — the
  branch then starts from the mainline — or exactly one dependency is finished on an unmerged
  branch, in which case the branch starts from that branch. (both)
- Two or more unmerged dependencies, or a failed dependency, make a task ineligible. (both)
- Order: points ascending, ties broken by position in the backlog file. (both)
- One project's autopilot text drives only specification tasks, yet in practice it also drove bug
  tasks; the kinds an autopilot may drive should be configurable rather than hard-coded.

## Session state

- Per task: `pending`, `running`, `done-branch` (finished on its branch), `failed`, `done-merged`.
  (both)
- Today this state lives only in the orchestrator session's memory, so two sessions cannot see
  each other's lanes; taskrail's claims should become the shared source of truth.
- "Merged" is verified by content, because squash merges break ancestry. (both)

## Answering gates

- At every stop, the orchestrator answers in the human's place, first from the repository's
  governing documents — its constitution or equivalent, architecture decision records — and the
  task row itself. (both)
- Criteria per gate, not a blanket approval:
  - never approve with failing tests;
  - require seeing the regression test fail before the fix;
  - read the diff itself rather than trust the lane's summary;
  - verify in the real runtime, or re-verify in a different environment from the lane's, before
    approving an implementation. (both)
- Conditional gates with nothing to decide do not stop. Some gates are decided by judgement (does
  this amendment change the specification's scope?), and two gates may be merged when both apply.

## Decision records

- Every answer the orchestrator gives is recorded with the options considered and the reason,
  before it is given. (both)
- One file per task (reusing the task's artifact slug), committed on the task branch, plus an
  index; run-level decisions in their own directory. (both)

## Escalation to a human

The orchestrator stops and asks a real human when it meets: a change to the governing documents;
a decision the governing documents reserve to humans; two lanes contradicting each other; a merge
conflict outside the known resolution classes; a false premise in a task row; or a diverged base.
(both)

An optional notification command runs on escalation and when a lane finishes successfully — not
on failure.

## Supervision

- Silent lanes are checked at least every 20 minutes for evidence of progress.
- A failed lane keeps its branch and worktree as evidence and blocks only its own dependents.
  (both)

## Resources

The orchestrator arbitrates what lanes share: a database per lane, ports, device emulators, and
sequential numbers such as task IDs or specification numbers assigned ahead of time to avoid
collisions. (both)

## Hand-off and merge follow-through

- The orchestrator never merges. It hands branches over one at a time, with the exact pull
  request title and link. (both)
- One project never pushes from lanes; the other pushes the lane's own branch with a lease. (both,
  differing)
- When the human says a branch is merged: verify it with `fetch --prune`, delete the branch and
  worktree, name the next branch to review, and rebase stacked dependents onto the mainline with
  `--force-with-lease`.

## Inconsistencies seen in the existing autopilots

Worth not repeating: an autopilot expecting lanes to push while their pipelines forbid it; an
autopilot checking for a version bump that tasks no longer make; and a gate the autopilot
describes that the pipelines only implement as an implicit wait.
