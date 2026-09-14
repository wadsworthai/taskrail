# taskrail

An agent-agnostic backlog tool. A deterministic CLI owns the backlog files — IDs, statuses,
claims, validation — and a set of skills tells an agent how to execute each kind of task.
See [DESIGN.md](DESIGN.md) for the full model.

## Install

taskrail needs [uv](https://docs.astral.sh/uv/).

```bash
uv tool install taskrail --from "git+https://github.com/alexkander/taskrail.git@v0.1.0"
cd your-repository
taskrail init --integration claude            # or --integration opencode; repeatable
```

Restart the agent session after `init` or `upgrade`: agents load skills when a session starts,
so one already running does not see new or changed skills.

`init` is safe to run again. It creates `.taskrail/config.toml` and `TODO.md` when missing, and
installs the skills and a committed wrapper, `.taskrail/bin/taskrail`, which runs the version
pinned in the config — through `uvx` if the installed CLI differs. Two optional flags:

- `--github-workflow` adds `.github/workflows/taskrail.yml`, running `taskrail validate` on
  pull requests.
- `--pre-commit` adds a git hook that runs `taskrail validate` before commits that touch
  Markdown or `.taskrail/`.

Commit `.taskrail/`, `TODO.md` and the installed skills. Skills and managed files you edit are
never overwritten silently; `--force` replaces them.

## Use

```bash
taskrail validate                      # check the backlog; non-zero on errors
taskrail next                          # eligible tasks, smallest first
taskrail show T012 --json              # kind, stages, base, branch, artifact path, blockers, prior work
taskrail show T012 --json --fetch      # …after fetching branch names other clones recorded
taskrail claim T012                    # reserve it; fails if someone else holds it
taskrail branch T012 fix/rounding      # name or rename the task's branch; claims, show and review follow it
taskrail new --epic E01 --kind bug --title "Round totals half-up" --pts 2
taskrail new --epic E01 --kind bug --title "Round totals half-up" --workspace   # …in its own branch and worktree
taskrail done T012                     # needs your claim; releases it
taskrail review T012                   # fetch the mainline's remote and pick the rebase base
taskrail review T012 --publish --scope billing   # push and print the PR/MR title and link
taskrail reopen T012 --reason "…"       # back to pending; prints a commit message to use
taskrail epic add --name Auth --objective "Sign in without passwords" --own-file
taskrail epic split E01                # move an inline epic to todo/E01-<slug>.md
taskrail autopilot start --count 3     # start an autopilot run; refused until [autopilot].enabled = true
taskrail autopilot next --run 20260913-1   # tasks to dispatch now, with each lane's resource values
taskrail claim T012 --run 20260913-1   # …a lane claims inside the run
taskrail autopilot lane T012 --run 20260913-1 --handle <agent-id> --state gate --gate plan
taskrail autopilot status              # run tasks' states, idle lanes, overlaps, escalation flags, hand-off queue
taskrail autopilot merged T012 --cleanup # prove the squash merge by content, remove worktree and branch, list rebases
taskrail autopilot notify --event escalation --run 20260913-1 --task T012   # run [autopilot].notify; never blocks
taskrail upgrade                       # re-install skills for this CLI version and pin it
taskrail self upgrade                  # update the CLI to the latest release
```

Every command accepts `--json`. Exit codes are listed in DESIGN.md.

## Task kinds

The core kinds are `bug`, `chore`, `feature` and `spike`, each with its executor skill. A
repository adds its own under `.taskrail/types/<kind>/kind.toml`, or adjusts a core kind under
`.taskrail/overrides/<kind>/kind.toml`. [examples/spec-kit](examples/spec-kit) shows a `spec`
kind that routes to a project's own Spec Kit skills. A `[[route]]` sends a task to another skill
when every column in its `when` matches; values may be lists and compare case-insensitively, as
in a stage's `match` below. The first route that matches wins.

A stage can apply to only some tasks of its kind, so one extra step does not need a copy of the
kind. `column` and `match` limit it to tasks whose custom column matches, case-insensitively;
`judgement = true` leaves it to the executor. `show --json` reports `applies` for each stage:

```toml
[[stage]]
name = "visual-check"
gate = "always"
column = "Area"
match = ["ui"]
```

To accept only a closed set of kinds, list them in `.taskrail/config.toml`; `validate` then
rejects tasks of any other kind:

```toml
[kinds]
allowed = ["spec", "bug", "chore"]
```

`init` and `upgrade` install only the executor skills the allowed kinds use, so the example above
does not install `taskrail-feature` or `taskrail-spike`, and removes them if they were installed
and not edited locally. The core `taskrail` skill always installs.

## Development

```bash
uv run pytest                                   # all tests
uv run pytest tests/test_validate.py -k cycle   # a single test
uv run taskrail --root <repo> validate          # run the CLI against a repository
```

To run taskrail from source in a repository that contains it, pin the path instead of a
release in `.taskrail/config.toml`:

```toml
version = "local:."
```

The wrapper then runs `uv run --project <checkout> taskrail`, so each worktree
uses its own branch's code, and `taskrail upgrade` leaves the pin alone. Elsewhere,
`TASKRAIL_BIN=/path/to/taskrail` points the wrapper at any build.

## Releasing

Releases are tagged `vX.Y.Z`. See [CHANGELOG.md](CHANGELOG.md).

`pyproject.toml` is the only place the version is written, and it must equal the tag without its
prefix: the wrapper accepts an installed CLI only when `v$(taskrail --version)` matches
the pin, so a mismatched build is never taken for the release.

1. In a pull request: set `version` in `pyproject.toml`, run `uv lock`, add the changelog entry.
2. After it is squash-merged: `git tag -a vX.Y.Z <merge commit> -m "taskrail X.Y.Z"`
   and `git push origin vX.Y.Z`. A published tag never moves.
3. Verify a clean install from the tag, then bump `main` to the next `.dev0` version, so builds
   from `main` never claim to be the release.
