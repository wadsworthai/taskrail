# Changelog

Releases are tagged `vX.Y.Z`. Install one with:

```bash
uv tool install taskrail --from "git+https://github.com/alexkander/taskrail.git@vX.Y.Z"
```

## Unreleased

- **Branch records across clones.** With `[git].branch_record_remote` set, a task's branch record
  is pushed as `refs/taskrail/branches/<ID>` by `branch`, `claim` and `new --workspace --branch`,
  and fetched by `claim`, `branch`, `new --workspace`, `review` and `show`/`list`/`next --fetch`,
  so another clone resolves a renamed branch; the later record wins, and failures only warn (T036).
- **Allowed kinds.** `[kinds].allowed` in config restricts a repository to a closed set of task
  kinds; `validate` rejects tasks of any other kind with `task-kind-disallowed` (T018).
- **Prior work in `show`.** `prior_work` reports an existing artifact, the task branch, and
  commits whose subject names the task, so an executor notices earlier attempts; it never blocks.
- **Each mainline's own remote.** `show`, `new --workspace` and `review` take the base, fetch, push and pull request link from `branch.<mainline>.remote` when it names a configured remote, and report it as `remote` and `remote_source`. Behaviour change: this tracking config now wins over `[review].remote`, which becomes the fallback.
- **Column aliases.** `[columns].aliases` maps a core column onto a repository's own header,
  such as `Pts = "Size"`, so a backlog keeps its established headers (T021).
- **Skills follow the allowed kinds.** `init` and `upgrade` install a shipped executor skill only
  when a kind the repository resolves uses it, and remove unedited copies that are no longer
  used, except while kind resolution reports errors (T025).
- **`new --column` refuses every core column.** `--column` for `✓`, `ID`, `Kind`, `Depends On`,
  `Title`, `Pts` or `Description`, in any letter case and aliased or not, now exits 2 and names
  the flag that fills it. Behaviour change: it used to overwrite `--kind`, `--title` or `--pts`,
  silently drop `ID` and `✓`, or report a missing column for another letter case (T026).
- **An unreadable `installed.json` stops `init` and `upgrade`.** A manifest with merge-conflict
  markers, invalid JSON, a value that is not an object, bytes that are not UTF-8, or that cannot
  be read at all now makes both commands exit 2, name the file and write nothing, `--force`
  included. Behaviour change: `init` used to overwrite it, dropping the recorded integrations,
  extras and digests, and `upgrade` reported it missing (exit 3) or crashed (T027).
- **Stacked bases and `done-branch`.** A task `✅` only at its own branch tip, not on the
  mainline, is `done-branch`: `next` never offers it and `claim` refuses it. A dependent of one
  such task branches from that branch — `show`'s `base` (now with `commit` and `dependency`),
  `new --workspace` and `review`'s `rebase.dependency` — while two or more make it `blocked`.
  Claims record `base` with its fork point, and ignore unknown keys when read (T017).
- **A reopen clears `done-branch`.** A task reopened on its mainline is no longer `done-branch`
  because its old branch, or that branch's remote copy, still says `✅`: a tip counts only if it
  contains every mainline commit with a `Reopens: <ID>` trailer, so `next` offers the task and
  `claim` accepts it again, while a branch done after the reopen is `done-branch` as before (T034).
- **Conditional stages.** A `[[stage]]` with `column` and `match` applies only to tasks whose
  custom column matches, case-insensitively, and one with `judgement = true` is left to the
  executor; `show --json` reports `column`, `match`, `judgement` and a boolean `applies` for each
  stage, and `validate` reports an undeclared column as `stage-column-unknown` (T020).
- **Named and renamed task branches.** `taskrail branch <ID> <NAME>` names a task's branch or
  renames it with `git branch -m`, and `new --workspace --branch NAME` creates one under a chosen
  name. The name is recorded in the git common directory and outlives `done`, so `show`, `review`,
  `done-branch`, a dependent's base, prior work and the claim all follow it; `show` adds
  `branch_source` and reports the worktree the branch is checked out in. `claim` records the
  template name it is claimed on, so a hand-edited title no longer moves the branch, and warns
  when claimed on another branch. A pushed branch is renamed only with `--force`, and the remote
  is never changed (T019).
- **Autopilot runs.** `[autopilot]` in config (the single-value keys of DESIGN.md §12.9);
  `autopilot start --count N` creates a local run file under the git common directory and is
  refused with exit 5 until `[autopilot].enabled` is true; `claim --run` ties a lane's claim to a
  run; `autopilot lane` and `autopilot decision` record lanes, hand-offs and run-level decisions;
  and `autopilot status` derives every run task's state with idle lanes, files touched by more
  than one lane and the hand-off queue (T029).
- **Routes match like stage predicates.** A `[[route]]`'s `when` values may be lists, and routes
  report `route-unreachable` (warning) when an earlier route always pre-empts them. Behaviour
  change: columns resolve and values compare case-insensitively after trimming, so a task whose
  cell differs from a route value only in letter case or padding now takes that route instead of
  the kind's `skill`, and of two routes differing only in case the first now wins for both; `""` as
  a value is `kind-invalid`; and a route on a column `[columns].custom` does not declare, a core
  column or an alias is the error `route-column-unknown`, which replaces the warning
  `route-column-undeclared` (T035).
- **Forced releases of remote claims.** With `claim_remote` set, `release --force`, `done`, `discard`
  and `claim --takeover` delete the remote claim with a lease on its recorded commit instead of
  exiting 2 with `stale info`. When the delete still fails, `done` and `discard` say the row was
  written and name `taskrail release <ID> --force` as the retry; a claim record without its pushed
  commit is refused with the ref to delete by hand (T037).
- **`autopilot next` dispatches lanes.** `taskrail autopilot next --run R` returns the tasks to start
  now — `taskrail next`'s order, within `max_lanes`, the run's count and kinds, and the
  `[[autopilot.group]]` limits — with `show`'s fields and one value of each `[[autopilot.resource]]`
  per lane, records the dispatch in the run and releases the values of lanes that ended; without
  `--run` it is a preview. `autopilot status` reports a dispatched, unclaimed task as `dispatched`.
  Behaviour change: `autopilot lane --group` exits 2 unless the name is a configured judgement
  group (T030).
- **Autopilot notifications and escalation flags.** `autopilot notify --event … --run R [--task ID]
  [--message …]` runs `[autopilot].notify` through the shell for the events in `notify_on`, with a
  message on stdin and `TASKRAIL_EVENT`, `TASKRAIL_RUN` and `TASKRAIL_TASK` set; a failing or
  hanging command is reported and never blocks (exit 0). `autopilot lane --gate STAGE` records the
  stage a lane is stopped at, and `autopilot status` flags each lane with `governing_touched` (files
  matching `[autopilot].governing` paths or globs), `escalate_gate` (a `kind:stage` listed in
  `escalate_gates`) and `escalation` (T032).
- **Merge detection by content.** `autopilot merged <ID>` runs `git fetch --prune`, then proves a
  finished task branch is in its mainline by ancestry, a first-parent commit with the same tree,
  the same patch-id, or a no-op `git merge-tree`, so squash merges are found; the `✅` row and an
  `(ID)` title are reported only as confirmations. A proven merge is recorded in the runs holding
  the task, and `autopilot status` counts it as `done-merged` while its commit stays on the
  mainline. `--cleanup` then removes the task's worktree and local branch, refusing with exit 5
  when the merge is unproven or the worktree has uncommitted or untracked files, is locked, is the
  main worktree or holds the current directory. Stacked dependents are listed with their
  `git rebase --onto` command (T031).
- **Import a table-based backlog.** `taskrail import <file>` converts a Markdown backlog made of
  task tables under headings, with no `## Epics` table, into one `validate` accepts: headings
  become epics, `--column`, `--status`, `--kind` and `--default-kind` map its headers and values,
  and IDs, row order, prose and escaped pipes are kept byte for byte. It is a dry run printing the
  result unless `--write`, refuses unmapped values with exit 5, and a second run changes nothing
  (T005).
- **Task branches without an upstream.** `new --workspace` and the core skill's workspace step
  create the task branch with `--no-track`, so it no longer tracks the mainline or a dependency's
  branch it started from, and a plain `git push` cannot land on them; `review --publish` still
  sets the task's own remote branch as upstream. A branch created earlier keeps tracking its base
  until `git branch --unset-upstream` is run on it (T038).
- **The `taskrail-autopilot` skill.** `init` and `upgrade` install it in every repository, whatever
  `[kinds].allowed` says. It makes the agent the orchestrator of a run the human asked for with a
  task count, and stops when `autopilot start` exits 5: dispatch with `autopilot next`, a lane brief
  template, gate criteria per gate type, decision records written before each answer, escalation,
  the three known conflict classes, sequential hand-off and follow-through with `autopilot merged`.
  Installed skills now include every file of a skill directory, such as `references/`, as managed
  files, and the agent notes in `integrations/<agent>.md` are split per skill by
  `<!-- taskrail:skill <name> -->`, so the core skill's notes are unchanged and the autopilot skill
  gets its own Claude Code and OpenCode notes (T024).
- **Reopens without a trailer.** `validate` reads the latest 500 commits that change backlog files
  and warns with `reopen-untraced` for a task pending in the working tree whose latest move from
  `✅` or `❌` back to `⬜` no commit since records with a `Reopens: <ID>` trailer, since the rebase
  rule and `done-branch` detection cannot see such a reopen. The exit code is unchanged;
  `--history-limit N` and `--no-history` bound or skip the check, and `--json` reports what was
  examined in `history` (T012).
- **Edit existing task rows.** `taskrail edit <ID>` changes a task's title, points, dependencies,
  description, kind or custom columns, one cell each and validated before anything is written.
  It refuses closed, `done-branch` and someone else's claimed tasks without `--force`, keeps a
  recorded branch name, and records the old template name when a title change would move a branch
  that exists. The core skill points to it instead of hand edits (T014).
- **A git merge driver for backlog tables.** `init --merge-driver` marks the backlog, epic and
  artifact index files in `.gitattributes` and defines `taskrail merge-driver` in the clone's git
  config, so `git merge`, `rebase` and `cherry-pick` unite table rows by ID, merge a row's cells
  three-way, keep `✅` unless the other side has a `Reopens:` commit, and leave markers only around
  rows and text that really conflict; everything else merges as git would. `upgrade`, `epic add
  --own-file` and `epic split` keep the block current (T004).
- **Changelog bullets in the merge driver.** The driver also merges tight bullet lists under the
  same heading bullet by bullet: bullets both sides add are all kept, current side first; a bullet
  one side moved appears once, where it moved; markers remain only around a bullet edited
  differently on both sides, or edited on one and deleted on the other; lists it cannot match are
  left to git. `init --merge-driver` and `upgrade` add every `CHANGELOG.md` to the `.gitattributes`
  block, and any file with its own `merge=taskrail` line gets the same merge (T040).
- **The GitHub workflow fetches full history.** The workflow `init --github-workflow` writes now
  checks out with `fetch-depth: 0`, so `validate`'s reopen check examines the history instead of
  a single commit. `upgrade` rewrites an unedited workflow; one edited locally is reported as
  skipped — add `fetch-depth: 0` to its checkout step by hand, or pass `--force` (T039).
- **`autopilot lane --gate close`.** `close` names the stop after `taskrail done` for a task of any
  kind, even one whose kind is not defined, so the orchestrator can record the close it reviews;
  the other `--gate` rules are unchanged, and an unknown stage's message now lists `close` too. The
  `taskrail-autopilot` skill records the close stop this way (T050).
- **No governing escalation after `done-branch`.** `autopilot status` no longer lists `governing`
  in `escalation`, nor prints `ESCALATE: governing …`, for a `done-branch` or `handed-off` task, as
  it already dropped `escalate_gate`; `governing_touched` still lists the paths. The autopilot
  skill's close review escalates a governing path the task's decision record does not show
  escalated. Behaviour change: such a task used to stay flagged until its merge (T049).
- **A closing lane stays `running`.** Between `taskrail done` and its commit, `autopilot status`
  reports the lane `running` — the `✅` in the working tree of its branch's worktree counts once the
  claim is released — with its `touched` files, instead of `pending`. `autopilot next` skips any
  candidate that still occupies a lane (`running`, `gate` or `escalated` without a claim, as well as
  `dispatched`), with the reason `<state> in run R`, so such a task is not dispatched twice (T054).
- **Autopilot skill text from the T033 trial.** The `taskrail-autopilot` skill hands a branch off
  with its ID, branch, pull request title, body and link; refills a lane once its close is
  reviewed instead of at hand-off; says that `taskrail new` IDs never collide across lanes and that
  an unclaimed dispatch expires after `[git].claim_grace_minutes`; and resumes a run from a new
  session by lane handle, restarting a lane from its branch with a new restart section of the lane
  brief when the handle no longer reaches it (T055).
- **`taskrail checks <ID>`.** Runs a task's configured checks — every applying stage's, or those of
  `--stage` or `--check` — in its worktree, found from its claim or its checked-out branch, with
  the worktree's own configuration and its autopilot lane's resources as
  `TASKRAIL_RESOURCE_<NAME>`, from anywhere in the clone; every check runs, `--json` captures each
  one's output, and a failing check exits 6. The core skill runs stage checks this way and lists
  exit 6, and the Claude Code notes describe a command shape an allowlist can match: one command
  per call, absolute paths, `git -C` and `--root` instead of `cd … &&` chains (T052).
- **A stable hand-off queue.** `autopilot status` orders `handoff.queue` by when each task was
  finished — the author time of the commit that turned its row ✅ on its branch — instead of the
  branch tip's commit time, so rebasing a waiting branch or committing a decision record on it no
  longer moves the task to the back, and a branch left only on the remote no longer jumps to the
  front (T053).
- **OpenCode note on escalations during blocking batches.** The `taskrail-autopilot` skill's
  OpenCode note has the orchestrator end its turn with the question at an escalation instead of
  starting another blocking batch of task calls, and record handles and check `silent` lanes as
  soon as a batch returns (T056).

## 0.1.0

First release.

- **Backlog format.** `TODO.md` with an `## Epics` table; each epic inline or in its own file;
  task tables with free column order, custom columns, and `⬜` / `✅` / `❌` statuses. Several
  backlogs per repository, each with its ID prefix, mainline and allowed dependency directions.
- **Validation and queries.** `validate` with file and line for every problem; `list`, `show`
  and `next` with computed `pending`, `claimed`, `blocked`, `done` and `discarded` states, and
  `--json` throughout.
- **Task kinds as data.** Core kinds `bug`, `chore`, `feature` and `spike`, each with stages,
  gates, an artifact and an executor skill; repositories add kinds under `.taskrail/types/` or
  override them under `.taskrail/overrides/`, including routing on a column.
- **Claims and IDs.** Exclusive claims shared by every worktree of a clone, optionally mirrored
  to a remote ref; IDs reserved under a lock across all branches.
- **Write commands.** `new` (with `--workspace` to start the task on its own branch), `done`,
  `discard`, `reopen`, `epic add` and `epic split` — one-cell or one-row diffs, validated before
  anything is written.
- **Review hand-off.** `review` fetches, picks the rebase base, pushes the task branch and
  prints a pull or merge request link with a Conventional Commits title for GitHub, GitLab,
  Gitea, Forgejo or a URL template.
- **Installation.** Idempotent `init` for Claude Code and OpenCode, a committed wrapper that
  runs the pinned version (falling back to `uvx`), `upgrade`, `self upgrade`, and optional
  GitHub workflow and pre-commit hook running `validate`.
