# Changelog

Releases are tagged `vX.Y.Z`. Install one with:

```bash
uv tool install taskrail --from "git+https://github.com/alexkander/taskrail.git@vX.Y.Z"
```

## Unreleased

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
