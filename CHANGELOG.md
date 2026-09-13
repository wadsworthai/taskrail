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
