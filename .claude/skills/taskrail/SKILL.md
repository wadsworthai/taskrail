---
name: taskrail
description: Work a taskrail backlog (TODO.md grouped by epics) through the taskrail CLI — find, claim, create and close tasks, and follow the procedure every task kind shares. Use whenever a task ID such as T012 is mentioned, when asked what to work on next, when adding tasks or epics, and before running any taskrail-* executor skill.
license: MIT
metadata:
  source: https://github.com/alexkander/taskrail
---

# taskrail

The backlog is Markdown: `TODO.md` holds an `## Epics` table and one section per epic, and an
epic may live in its own file instead. Each task is a table row with a status (`⬜` pending,
`✅` done, `❌` discarded), an ID, a kind, dependencies and a title.

**The CLI owns IDs and statuses.** Never invent an ID, never type a status emoji into a row,
and never reformat a table. Create tasks with `taskrail new`, close them with `taskrail done`
or `taskrail discard`, and bring a closed one back with `taskrail reopen`. Editing a title or
description by hand is fine; run `taskrail validate` afterwards.

## Running the CLI

Run `.taskrail/bin/taskrail <command>` from anywhere in the repository or a task worktree. Add
`--json` whenever you need to read the result, and act on the exit code:

| Exit | Meaning | What to do |
|---|---|---|
| 0 | success | continue |
| 1 | the backlog fails validation | run `taskrail validate`, report the errors, stop |
| 2 | usage, configuration or git error | read the message; fix the invocation or report it |
| 3 | not found | re-check the ID or name |
| 4 | conflict: claimed by someone else | stop and report who holds it |
| 5 | refused: not pending, or blocked | stop and report why |

Useful commands: `next`, `list [--epic E01] [--state pending]`, `show <ID>`, `claims`,
`kind list`.

## Working a task

Follow these steps for every kind. The executor skill for the kind (named in the `skill` field
of `taskrail show`) supplies what happens inside each stage.

1. **Identify.** Use the ID the human gave. If none was given, run `taskrail next --json` and
   propose the first candidate; do not start one on your own.
2. **Inspect.** Run `taskrail show <ID> --json`. Stop if `state` is not `pending` and report
   the claim or `blocked_by`. If the `skill` field names a different executor than the one you
   are running, stop and name the right one. If `prior_work` lists an artifact, the task's
   branch or commits naming the task, someone may already have worked on it: look at them,
   check that the description's premises still hold, and mention both at your first gate.
   These signals never block on their own.
3. **Workspace.** Run `git fetch` first, then `taskrail show <ID> --json` again: its `base.onto`
   is the ref to branch from — the local or the remote mainline, whichever is further ahead.
   If `base.diverged` is true, stop and ask which one to use. If `worktree` is set, create it:
   `git worktree add <worktree> -b <branch> <base.onto>`; otherwise
   `git switch -c <branch> <base.onto>`. If the branch already exists, stop and ask — someone
   may have started this task. If a dependency is finished only on an unmerged branch, ask
   which base to use. From here on, work only inside that workspace. A task created with
   `taskrail new --workspace` already has its workspace: skip to claiming.
4. **Claim.** From inside the workspace, run `taskrail claim <ID>` before any edit.
5. **Stages.** Take `kind_descriptor.stages` in order. For each stage: do its work, run each of
   its `checks` with the command from the `checks` map (say so if a check is not configured),
   commit when `commit` is true, then apply its gate. `commit = false` means a commit is not
   required at that point, not that one is forbidden.
6. **Scope.** Never edit the areas in `never_edit`. Work you discover outside the task's scope
   becomes a follow-up task (see *Creating tasks*); mention it at the next gate. Only fix
   something directly on the way when it is small and inseparable from the task.
7. **Artifact.** Write the kind's document at `artifact`, and add a row for it to
   `artifact_index`, creating that index as a heading plus a table if it does not exist.
8. **Close.** With every check passing:
   - run `taskrail done <ID>` inside the workspace — it marks the row in this branch and
     releases the claim — and commit that change on its own;
   - run `taskrail review <ID> --json`. It fetches the review remote and reports in
     `rebase.onto` the base to rebase onto: the local or the remote mainline, whichever is
     further ahead. If `rebase.diverged` is true, stop and ask which one to use;
   - if `rebase.needed` is true, run `git rebase <rebase.onto>`. Resolve backlog conflicts
     mechanically: rows added on both sides keep both, and a status cell that is `✅` on either
     side stays `✅`, unless one side has a `Reopens: <ID>` commit the other lacks
     (`git log --grep='^Reopens: <ID>$' <side>`) — then that side's `⬜` stays. Then run
     `taskrail validate`, and stop and ask about any other conflict;
   - choose the pull request title's type and scope. The pull request is squash-merged, so its
     title is the commit that reaches the mainline and drives the next version: use the
     Conventional Commits type of the most significant change (`feat`, `fix`, `docs`, `ci`,
     `refactor`, …; the kind's default fits most tasks) and the affected component as scope, and
     mark incompatible changes as breaking;
   - run `taskrail review <ID> --publish --json [--type <type>] [--scope <scope>] [--breaking]`.
     It pushes the branch when the repository enables it — exit 4 means the push was rejected:
     stop and report — and returns `pull_request.title`, `body` and `url`.
9. **Hand off.** Report the branch and its base, each commit on one line, every check with its
   actual result, the artifact path, any follow-up tasks, whether the branch was pushed, and the
   pull request title and link — with its body too when the link cannot carry it. Never merge,
   never delete the branch, and remove the worktree only when the human asks.

## Gates

A stage's `gate` decides whether you stop after it:

- `always` — stop and wait for explicit approval.
- `conditional` — stop only if there is something to decide or report; otherwise continue.
- `none` — continue.

At a gate, stop editing and report: what the stage did; the evidence, with the exact commands
and the relevant real output; each decision needed, as a direct question; what you will do
next; and what you will not do. Approval covers that stage only.

If you are a delegated agent with no direct channel to the human, end your turn with that
report and resume only when told to continue with the task ID. Never shorten evidence for the
relay: whoever passes it on cannot recover what you leave out.

## On Claude Code

- At a gate, ask the human with the AskUserQuestion tool when it is available; otherwise ask in
  plain text.
- Running as a subagent, you have no channel to the human: end your turn with the gate report
  and wait to be resumed.
- Create task worktrees with git as described above rather than through a subagent's worktree
  isolation, which picks its own branch name and location.

## Creating tasks

```bash
.taskrail/bin/taskrail new --epic E01 --kind bug --title "Short imperative title" \
  [--pts 3] [--depends-on T010,T011] [--description "One line."] [--column Owner=api]
```

Keep the description to one line; put longer detail in a file and link it.

To open a task and start working on it straight away, add `--workspace`. It creates the task's
branch — and worktree, when the repository uses them — from `base.onto` and writes the new row
there instead of in the current checkout, so the task travels with its own pull request rather
than being committed to the mainline first. Commit the row inside that workspace, then claim
the task. It refuses when the mainlines have diverged or the branch already exists. Add epics with
`taskrail epic add --name … --objective … [--done-when …] [--own-file]`, and move a large
inline epic to its own file with `taskrail epic split E01`.

## Reopening a task

When a done or discarded task turns out not to be finished, reopen it only on the human's
say-so:

```bash
.taskrail/bin/taskrail reopen T012 --reason "Totals still round half-down for refunds" --json
```

The reason is not stored in the backlog. Commit the status change on its own, using
`commit_message` from the result — you may adapt its subject line to the repository's
convention, but keep the reason as the body and the `Reopens: <ID>` trailer as its last line.
`taskrail review` repeats that trailer in the pull request description, so it survives a
squash merge.
Report any `dependents`: they are done or claimed on top of a task that is no longer done.

## Commit messages

Pull requests are squash-merged: the title `taskrail review` generates becomes the single
commit on the mainline, in Conventional Commits form. Commits on the task branch exist for
review. Follow the repository's convention for them; if it has none, use one-line Conventional
Commits with the affected component as scope, for example
`fix(billing): round totals half-up`.
