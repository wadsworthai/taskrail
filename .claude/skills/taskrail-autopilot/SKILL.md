---
name: taskrail-autopilot
description: Orchestrate a taskrail autopilot run — work several backlog tasks at once in lanes, answer their gates on the human's behalf from the governing documents, record every decision, escalate what the human must decide, and hand finished branches over one at a time. Use only when the human explicitly asks to run the autopilot and gives the number of tasks to complete.
license: MIT
metadata:
  source: https://github.com/alexkander/taskrail
---

# taskrail-autopilot

You are the **orchestrator**: the session the human talks to. Each task of the run is worked in a
**lane**, a sub-session that follows the `taskrail` skill and the task's executor skill for one
task and stops at every gate. You answer those gates on the human's behalf where the governing
documents allow it, and take everything else to the human. The CLI computes — what to dispatch,
each task's state, resources, merge detection; you judge. Use the CLI as the `taskrail` skill
describes, with `--json` and its exit codes.

## When to run

**Run the autopilot only when the human explicitly asks for it and gives a task count.** If they
ask without a count, ask for one and do nothing else. Never start the autopilot on your own
initiative: not because tasks are pending, not from `taskrail next`, and not because this skill is
installed. This rule lives here, in the text every agent reads, not only in metadata.

1. Run `taskrail autopilot start --count <N> --json`, adding `--kinds <kinds>` only when the human
   named kinds. Keep the run ID (`run.id` in the JSON); every later command names it as `<R>`.
2. If it exits 5, the repository has not enabled the autopilot: stop and report its message to the
   human. Never change `[autopilot].enabled` yourself, and do not work the tasks some other way
   instead.
3. Any other failure: act on the exit code as the `taskrail` skill says, and stop.

## Before the first dispatch

- Read the governing documents: the `[autopilot].governing` paths in `.taskrail/config.toml`, the
  documents they lead to, and the backlog rows of the tasks. Answer gates from them first.
- Run `taskrail autopilot status --json`. Another orchestrator may have lanes in this clone; they
  count toward the same limits, and you never touch them.

## Dispatch

1. Run `taskrail autopilot next --run <R> --json`. For each task it dispatches, fill
   `references/lane-brief.md` from that task's entry: branch, worktree, `base`, `environment`,
   `decisions`, the executor skill, the other live lanes and the touch map so far.
2. Start any shared service the lane needs yourself — lanes never do — and launch the lane as a
   sub-session with the brief. Launch the lanes of one dispatch together.
3. Record each lane at once: `taskrail autopilot lane <ID> --run <R> --handle <H> --state running`.
4. A group assigned by judgement (such as "touches the user interface") is set before `next`, with
   `taskrail autopilot lane <ID> --run <R> --group <G>`.
5. `skipped` and `limited_by` say why a task did not start; mention them when they matter.
6. When a lane ends — handed off, failed, discarded — run `next --run <R>` again to fill the free
   lane. The run's count caps what starts; never start more tasks than the human asked for.

## Supervise

Nothing wakes you on a timer. Whenever you wake — a lane stopped, the human wrote — run
`taskrail autopilot status --run <R> --json` and act on it:

- a lane stopped at a gate: answer it (below);
- `silent: true`: read its worktree (`git log`, `git status`, its artifact); if it is stuck,
  escalate;
- `overlaps`: compare them with the touch map; an overlap the map does not cover is a question for
  the lanes involved, or an escalation when they contradict each other;
- `escalation` not empty: escalate.

## Answer a gate

1. Record it: `taskrail autopilot lane <ID> --run <R> --state gate --gate <stage>`.
2. Check the escalation conditions below; if one holds, escalate instead.
3. Review the stage by `references/gate-review.md`.
4. Write your decisions into the task's record as `references/decision-record.md` shows, **before**
   giving them, and commit the record on the task branch, in the lane's worktree, while the lane is
   stopped.
5. Resume the lane with `continue <ID>` plus the answers, numbered as its questions were.
6. Record it: `taskrail autopilot lane <ID> --run <R> --state running`.

A conditional gate with nothing to decide does not stop a lane; if one stops anyway, let it
continue.

**Touch map.** At each lane's first gate, once its plan names the files and sections it will change,
build or extend the touch map: which lane edits what, what each lane leaves alone, and how the
conflicts you expect will be resolved. Record it with
`taskrail autopilot decision --run <R> --question <text> --decision <text> --reason <text>`, copy
it into every affected task's record, and give it to every live lane when you next resume it.

## Escalate

Stop and ask the human when:

1. a lane's branch touches a governing path (`governing_touched` in `status`);
2. the gate is listed in `escalate_gates` (`escalate_gate` in `status`);
3. the governing documents reserve the decision to humans;
4. two lanes contradict each other;
5. a merge conflict falls outside the known classes (below);
6. a task row rests on a false premise;
7. a base has diverged (`base.diverged` or `rebase.diverged`).

To escalate: record `taskrail autopilot lane <ID> --run <R> --state escalated --reason <why>`, run
`taskrail autopilot notify --event escalation --run <R> --task <ID>`, and ask the human a direct
question with the options and your recommendation. Record the answer in the task's record, naming
who gave it. Other lanes keep going meanwhile. Reopening a task needs the human's say-so, as the
`taskrail` skill says.

A lane that cannot finish is recorded
`taskrail autopilot lane <ID> --run <R> --state failed --reason <why>` and reported; run
`taskrail autopilot notify --event lane-failed --run <R> --task <ID>`. It keeps its claim, branch
and worktree as evidence, and its dependents stay blocked.

## Close and hand off

Lanes stop after `taskrail done` and `taskrail review <ID> --json`, without rebasing or publishing.
Record that stop as a gate named `close`:
`taskrail autopilot lane <ID> --run <R> --state gate --gate close`. Review the close by
`references/gate-review.md`. Then hand branches off **one branch at a time**:
`status` names the next one in `handoff.next`, and none while `handoff.in_review` is set.

1. In the lane's worktree, run `taskrail review <ID> --json`. If `rebase.needed` is true, run
   `git rebase <rebase.onto>`, resolve only the known classes, re-run the checks and
   `taskrail validate`, record the rebase in the task's record and commit it.
2. Run `taskrail review <ID> --publish --json --type <type> --scope <scope>` there, choosing the
   type and scope as the `taskrail` skill says. Exit 4, a rejected push, escalates.
3. Record `taskrail autopilot lane <ID> --run <R> --state handed-off` and run
   `taskrail autopilot notify --event lane-done --run <R> --task <ID>`.
4. Give the human the exact pull request title and link, and the body when the link cannot carry
   it. Never merge.

## After a merge

When the human says a branch is merged:

1. Run `taskrail autopilot merged <ID> --cleanup --json`. When `merged` is false, report what was
   checked and clean up nothing; exit 5 names what stopped the cleanup.
2. For each stacked dependent it lists, run its `git rebase --onto` command in that dependent's
   worktree, resolve only the known classes, re-run the checks, and record the rebase. A dependent
   already published is published again with `taskrail review <ID> --publish --json`, which pushes
   with a lease.
3. Hand off the next branch.
4. When `status` reports the run `complete`, report what the run delivered and stop.

## Known conflict classes

Resolve these without the human; anything else escalates.

1. **Backlog rows**, united by ID: a status that is `✅` on either side stays `✅`, unless one side
   has a `Reopens: <ID>` commit the other lacks. Run `taskrail validate` afterwards.
2. **Appended index rows and changelog bullets**: keep all of them, one entry per task.
3. **Installed skill copies and `.taskrail/installed.json`**: make the manifest valid first, merge
   the skill sources, then run `taskrail upgrade --force`.

## Several unmerged dependencies

`autopilot next` never offers a task with several unmerged dependencies. Start one only on the
human's explicit instruction: create the lane's workspace from one dependency's branch, without
tracking it, and merge the others into it. That merge commit is the fork point: once the
dependencies merge, the branch moves with `git rebase --onto <mainline> <merge commit>`. The lane
claims with `taskrail claim <ID> --ignore-deps --run <R>`, and the task's record says why.

## Never

- merge, push other than through `review --publish`, or delete a remote branch;
- let a lane publish, merge, start shared services or touch another lane's worktree;
- approve with failing checks, or on the lane's summary alone;
- start more tasks than the count, or start a run nobody asked for;
- edit run files by hand: run state is written only through the `autopilot` commands.

## On Claude Code

- Launch each lane as a background general-purpose subagent with the Agent tool, with the filled
  lane brief as its prompt, and launch the lanes of one dispatch in a single message so they run
  concurrently. The agent ID is the lane's handle for `autopilot lane --handle`.
- Resume a lane after a gate with `SendMessage` to its agent ID: `continue <ID>` plus the answers.
  A resumed subagent keeps its full context.
- A completion notification wakes you when a lane stops; run `autopilot status` then.
- Lanes cannot ask the human: `AskUserQuestion` is removed from subagents. At an escalation, ask
  the human yourself with `AskUserQuestion` when it is available, otherwise in plain text.
- When the human wants lanes on another model than yours, pass it in the Agent tool's `model`
  parameter.
- Lanes create their worktrees with git, as the brief says, never through the Agent tool's
  worktree isolation, which picks its own branch name and location.
- Nothing wakes you on a timer. A tool that waits on a condition may re-run `autopilot status`
  while lanes work, but nothing may depend on it.
