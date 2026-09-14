# T038 — Create task branches without tracking the mainline

Kind: chore · Epic: E02 · Status: implemented

## Goal

A task branch must never have the mainline — or a dependency's branch — as its upstream.

Today both ways of creating a task workspace pass the base as the start point of a new branch:

- the core skill's step 3: `git worktree add <worktree> -b <branch> <base.onto>`, or
  `git switch -c <branch> <base.onto>`;
- `taskrail new --workspace` (`_open_workspace` in `cli.py`): the same two commands.

`base.onto` is usually `<remote>/<mainline>`. With git's default `branch.autoSetupMerge=true`, a
branch started from a remote-tracking branch tracks it, so the task branch gets
`branch.<task>.merge = refs/heads/main`. Under `push.default=upstream` (or `tracking`) a plain
`git push` from the task branch then pushes the task's commits onto the mainline; under the
default `simple` git refuses only because the names differ. The same happens for a stacked base
`<remote>/<dependency-branch>`, which would push onto the dependency's pull request branch, and
with `branch.autoSetupMerge=always` even a local start point is tracked.

`taskrail review --publish` already pushes with an explicit refspec,
`git push --set-upstream <remote> HEAD:refs/heads/<branch>`, so after publishing the upstream is
the task's own remote branch. Nothing in taskrail reads a branch's upstream.

Reproduction, in a throwaway bare `origin` and clone (git 2.55.0):

```text
--- 1. worktree add -b from origin/main (defaults)
origin/main
--- 2. switch -c from origin/main (defaults)
origin/main
--- 3. worktree add --no-track
fatal: no upstream configured for branch 'T3'
--- 4. switch -c --no-track
fatal: no upstream configured for branch 'T4'
--- 5. autoSetupMerge=always, local start point, defaults
main
--- 6. autoSetupMerge=always, local start point, --no-track
fatal: no upstream configured for branch 'T6'
--- 7. plain push from tracking T1 under push.default=upstream
   75131af..6eb477a  T1 -> main
--- 8. plain push from T1 under default simple
fatal: The upstream branch of your current branch does not match
the name of your current branch.
--- 9. plain push from untracked T3 under simple, and with push.autoSetupRemote
fatal: The current branch T3 has no upstream branch.
origin/T3
```

And `taskrail new --workspace` in a throwaway repository with a bare `origin`:

```text
$ taskrail new --epic E01 --kind chore --title "Probe tracking" --workspace --json
  "branch": "T001-probe-tracking", "base": "origin/main"
$ git config --get-regexp '^branch\.T001-probe-tracking\.'
branch.T001-probe-tracking.remote origin
branch.T001-probe-tracking.merge refs/heads/main
```

## Change set

All paths are relative to the repository root unless stated.

| File | Change |
|---|---|
| `src/taskrail/cli.py` | `_open_workspace` only: add `--no-track` to `git worktree add` and to `git switch -c`. |
| `src/taskrail/skills/taskrail/SKILL.md` | Step 3 only: the two commands become `git worktree add --no-track <worktree> -b <branch> <base.onto>` and `git switch --no-track -c <branch> <base.onto>`, with one sentence saying why — the base never becomes the branch's upstream, so a plain `git push` cannot land on it; `review --publish` sets the upstream to the task's own remote branch. |
| `tests/test_workspace.py` | One test, parametrized over `worktree = "required"` and `"never"` and over the start point, on the existing `remote_repo` fixture: `origin/main` with git's defaults, and a local `main` ahead of it with `branch.autoSetupMerge=always`. After `new --workspace` the branch has no `branch.<task>.remote` / `.merge`. Run once against the unchanged code to see it fail. |
| `CHANGELOG.md` | One bullet at the end of `## Unreleased`. |
| `DESIGN.md` | One clause in step 3 of the review hand-off (§7.1): the push sets the task's own remote branch as its upstream; and in the `new --workspace` command-table row: the branch is created without an upstream. (See decision 3.) |
| Repository root | `.claude/skills/taskrail/SKILL.md` refreshed with `.taskrail/bin/taskrail upgrade`; this artifact and its row in `docs/chores/README.md`. |

## Decisions needed

1. **`--no-track` for every base, stacked ones included.** A stacked base `<remote>/<dependency>`
   is tracked exactly like the mainline, and `branch.autoSetupMerge=always` tracks local start
   points as well. Recommended: pass `--no-track` unconditionally, in the CLI and in the skill.
   Alternative: only when `base.onto` is a remote-tracking ref — more code, and it misses
   `autoSetupMerge=always`.
2. **Keep `--set-upstream` in `review --publish`.** After publishing, the upstream is
   `<remote>/<branch>`, the task's own branch, so plain `git push` / `git pull` in the workspace
   target the right place — the state this task wants. Recommended: keep it unchanged.
   Alternative: drop it, leaving published branches with no upstream (plain `git push` refused
   under `simple`); no taskrail code would notice either way.
3. **DESIGN.md.** Recommended: the two one-clause additions above, so the design states the
   invariant. Alternative: leave DESIGN.md alone and let the skill and the changelog carry it.
4. **Existing task branches.** Branches already created with tracking (including open lanes)
   are not touched; `git branch --unset-upstream` fixes one by hand. Recommended: no migration,
   mention it in the changelog bullet only if you want it. Alternative: a `doctor`-style check,
   as a follow-up task.

## Decisions at the scope gate

Recorded in `docs/autopilot/decisions/T038-create-task-branches-without-tracking-th.md`.

1. `--no-track` unconditionally, in the CLI and in the skill, stacked bases included.
2. `review --publish` keeps `--set-upstream`.
3. The two DESIGN.md clauses are added.
4. No migration; the CHANGELOG bullet names `git branch --unset-upstream` for existing branches.

The change set is approved as written. The branch was then rebased onto `origin/main` (`591fa5b`,
T036), so the step 3 edit sits on T036's `show --json --fetch` wording.

## Out of scope

- Any other command, `review.py`, and the push logic.
- Changing git configuration (`push.default`, `branch.autoSetupMerge`) for the user.
- Other hunks of step 3 or `cli.py` touched by open branches (T036's `show --fetch`, T030/T032
  autopilot, T005's importer registration).
- Unsetting upstreams on branches that already exist.

## Verification

- The new test fails on the unchanged `_open_workspace` (the branch tracks `origin/main`, or
  `main` under `autoSetupMerge=always`) and passes after the change.
- `uv run pytest -q`: the full suite passes. `lint` is listed by the
  stage but not configured in `.taskrail/config.toml`.
- In a throwaway repository with a bare `origin`: `taskrail new --workspace` in both worktree
  modes leaves `git config --get-regexp '^branch\.<task>\.'` empty; then
  `git -c push.default=upstream push` from the workspace is refused instead of pushing onto
  `main`; `taskrail review <ID> --publish` sets the upstream to `origin/<task-branch>`.
- The skill's step 3 commands, copied literally, create an untracked branch in the same
  throwaway repository.
- `.taskrail/bin/taskrail validate` passes.

## Verification results

**Failing test first.** `uv run pytest -q tests/test_workspace.py -k no_upstream` on the unchanged
`_open_workspace`:

```text
E         + branch.T004-negative-totals.remote origin
E         + branch.T004-negative-totals.merge refs/heads/main
E         + branch.T004-negative-totals.remote origin
E         + branch.T004-negative-totals.merge refs/heads/main
E         + branch.T004-negative-totals.remote .
E         + branch.T004-negative-totals.merge refs/heads/main
E         + branch.T004-negative-totals.remote .
E         + branch.T004-negative-totals.merge refs/heads/main
FAILED tests/test_workspace.py::test_workspace_branch_has_no_upstream[remote-required]
FAILED tests/test_workspace.py::test_workspace_branch_has_no_upstream[remote-never]
FAILED tests/test_workspace.py::test_workspace_branch_has_no_upstream[local-required]
FAILED tests/test_workspace.py::test_workspace_branch_has_no_upstream[local-never]
4 failed, 13 deselected in 0.87s
```

After adding `--no-track`: `4 passed, 13 deselected in 0.47s`.

**Checks.** `uv run pytest -q`: `504 passed in 41.73s`. `lint` is
listed by the stage but not configured in `.taskrail/config.toml`. `.taskrail/bin/taskrail upgrade`
updated `.claude/skills/taskrail/SKILL.md`.

**`new --workspace` and publishing, in a throwaway repository with a bare `origin`.**

```text
=== new --workspace, worktree = required
  "branch": "T001-probe-tracking", "base": "origin/main"
$ git config --get-regexp '^branch\.T001-probe-tracking\.'
exit=1
$ git -c push.default=upstream push          (from the workspace, after a task commit)
fatal: The current branch T001-probe-tracking has no upstream branch.
exit=128
$ git ls-remote origin
9c5ce7f67b131e7874fc738eb4964e371a1bbc59	HEAD
9c5ce7f67b131e7874fc738eb4964e371a1bbc59	refs/heads/main
$ taskrail review T001 --publish --json      (after done and a rebase onto origin/main)
exit=0
push: {"enabled": true, "pushed": true, "command": "git push --set-upstream origin HEAD:refs/heads/T001-probe-tracking", "error": null}
$ git config --get-regexp '^branch\.T001-probe-tracking\.'
branch.T001-probe-tracking.remote origin
branch.T001-probe-tracking.merge refs/heads/T001-probe-tracking
=== new --workspace, worktree = never
  "branch": "T002-probe-never", "workspace": "<tmp>/work", "base": "origin/main"
$ git config --get-regexp '^branch\.T002-probe-never\.'
exit=1
```

**The skill's step 3 commands, copied literally, in a second throwaway repository.** T002 depends
on T001, which was finished and published on its own branch, whose local copy was then deleted.

```text
$ taskrail show T001 --json --fetch   -> base.onto "origin/main"
$ git worktree add --no-track .worktrees/T001-base-task -b T001-base-task origin/main
$ git config --get-regexp '^branch\.T001-base-task\.'
exit=1
$ taskrail show T002 --json --fetch   -> base.onto "origin/T001-base-task", dependency "T001"
$ git worktree add --no-track .worktrees/T002-stacked-task -b T002-stacked-task origin/T001-base-task
$ git config --get-regexp '^branch\.T002-stacked-task\.'
exit=1
--- control: the command before T038, same base
$ git worktree add <tmp>/ctl -b CTL origin/T001-base-task
branch.CTL.remote origin
branch.CTL.merge refs/heads/T001-base-task
$ git switch --no-track -c SW origin/main                                  -> no branch.SW.* config
$ git -c branch.autoSetupMerge=always switch --no-track -c SW2 main        -> no branch.SW2.* config
```

Both throwaway repositories were deleted afterwards.

## Docs

DESIGN.md, the CHANGELOG and the core skill were updated in the implement stage. A search of every
Markdown file for `worktree add` and `switch -c` finds only past task write-ups under `docs/`,
which record the commands as they ran then and stay unchanged. No follow-up tasks.
