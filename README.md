# taskrail

An agent-agnostic backlog tool. A deterministic CLI owns the backlog files — IDs, statuses,
claims, validation — and a set of skills tells an agent how to execute each kind of task.
See [DESIGN.md](DESIGN.md) for the full model.

> **Experimental.** taskrail is under active development and not yet stable: commands, flags,
> file formats and skills may change incompatibly between releases, so pin a release and read
> [CHANGELOG.md](CHANGELOG.md) before upgrading. It is developed with AI coding agents, under
> human direction and review.

## Install

The only prerequisite is [uv](https://docs.astral.sh/uv/) — on your machine, on a CI runner and
in an agent sandbox alike. Nothing needs to be installed on the machine itself.

**Recommended: no global install.** Bootstrap the repository with `uvx`, then call taskrail
through the wrapper `init` commits:

```bash
cd your-repository
uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.3.0" \
  taskrail init --integration claude          # or --integration opencode; repeatable
.taskrail/bin/taskrail validate
```

`init` pins the version it ran as in `.taskrail/config.toml`, and the committed wrapper
`.taskrail/bin/taskrail` runs exactly that version through `uvx`. So the tag you bootstrap with
becomes the pin, and every later call — yours, another clone's, CI's, an agent's — reproduces the
taskrail that wrote the repository.

**Or install the CLI on your machine**, to type `taskrail` instead of the wrapper's path:

```bash
uv tool install taskrail --from "git+https://github.com/wadsworthai/taskrail.git@v0.3.0"
```

Both routes are supported, and they agree: the wrapper uses an installed CLI when its version
matches the pin and falls back to `uvx` when it does not, so a repository is never worked with a
taskrail it did not pin.

**Upgrading.** Without a global install, the pin *is* the version, and moving it is the upgrade:

```bash
uvx --from "git+https://github.com/wadsworthai/taskrail.git@vX.Y.Z" taskrail upgrade
```

That re-installs the skills for `vX.Y.Z` and writes the new pin. `taskrail self upgrade` replaces
a globally installed CLI and never touches a repository's pin, so it has no part in this route.

Restart the agent session after `init` or `upgrade`: agents load skills when a session starts,
so one already running does not see new or changed skills.

`init` is safe to run again. It creates `.taskrail/config.toml` and `TODO.md` when missing, and
installs the skills and the wrapper. Three optional flags:

- `--github-workflow` adds `.github/workflows/taskrail.yml`, running `taskrail validate` on
  pull requests and pushes to the mainlines, with full git history so its check for reopens
  without a `Reopens:` trailer sees every commit.
- `--pre-commit` adds a git hook that runs `taskrail validate` before commits that touch
  Markdown or `.taskrail/`.
- `--merge-driver` lets git resolve the conflicts parallel branches make in backlog tables and
  in bullets appended to changelogs: rows and bullets both sides add are kept, a bullet one side
  moved is not duplicated, and a `✅` wins unless the other side reopened the task. It writes a
  block of `.gitattributes` to commit, and defines the driver in this clone's git config, which
  each clone opts into by running `taskrail init --merge-driver` once.

Commit `.taskrail/`, `TODO.md` and the installed skills. Skills and managed files you edit are
never overwritten silently; `--force` replaces them.

## Use

A repository calls taskrail through the wrapper `init` commits: `.taskrail/bin/taskrail <command>`.
The examples below are written short so they fit; with the CLI installed on your machine they work
as typed.

```bash
taskrail validate                      # check the backlog; non-zero on errors
taskrail validate --no-history         # …without reading git history for reopens lacking a Reopens trailer
taskrail next                          # eligible tasks, smallest first
taskrail show T012 --json              # kind, stages, base, branch, artifact path, blockers, prior work
taskrail show T012 --json --fetch      # …after fetching branch names other clones recorded
taskrail claim T012                    # reserve it; fails if someone else holds it
taskrail branch T012 fix/rounding      # name or rename the task's branch; claims, show and review follow it
taskrail new --epic E01 --kind bug --title "Round totals half-up" --pts 2
taskrail new --epic E01 --kind bug --title "Round totals half-up" --workspace   # …in its own branch and worktree
taskrail workspace T012                # move a row only this checkout has into its own branch and worktree
taskrail edit T012 --depends-on T010,T011 --pts 3   # change cells of an existing row; validated first
taskrail checks T012 --stage fix       # run the stage's checks in the task's worktree; exit 6 when one fails
taskrail done T012                     # needs your claim; releases it
taskrail review T012                   # fetch the mainline's remote and pick the rebase base (a report only under task_branch = "current")
taskrail review T012 --publish --scope billing   # push and print the PR/MR title and link
taskrail reopen T012 --reason "…"       # back to pending; prints a commit message to use
taskrail epic add --name Auth --objective "Sign in without passwords" --own-file
taskrail epic split E01                # move an inline epic to todo/E01-<slug>.md
taskrail autopilot start --count 3     # start an autopilot run; refused until [autopilot].enabled = true
taskrail autopilot start --tasks T012,T015   # …or a run that works only these tasks, in this order
taskrail autopilot extend 20260913-1 --tasks T017   # add a task to a named run (--count N for a count-only run)
taskrail autopilot next --run 20260913-1   # tasks to dispatch now, with each lane's resource values
taskrail claim T012 --run 20260913-1   # …a lane claims inside the run
taskrail autopilot lane T012 --run 20260913-1 --handle <agent-id> --state gate --gate plan
taskrail autopilot status              # run tasks' states, idle lanes, overlaps, escalation flags, hand-off queue
taskrail autopilot merged T012 --cleanup # prove the squash merge by content, remove worktree and branch, list rebases
taskrail autopilot notify --event escalation --run 20260913-1 --task T012   # run [autopilot].notify; never blocks
taskrail upgrade                       # re-install the skills for the running version and pin it
taskrail self upgrade                  # update a globally installed CLI; not needed without one
```

Every command accepts `--json`. Exit codes are listed in DESIGN.md.

## Adopting an existing backlog

A Markdown backlog made of task tables under headings converts with `taskrail import`. It is a
dry run until `--write`: read the report, add a flag for each value it cannot map, and run it
again.

```bash
taskrail import TODO.md --column "✓=Status" --column Kind=Type --status "in progress=pending" \
  --kind "tech debt=chore" --default-kind feature          # prints the converted file
taskrail import TODO.md <the same flags> --write
taskrail validate
```

Headings that hold task tables become epics (`--epic-level` picks the heading level), tables
under no heading go to one `Backlog` epic, and IDs, row order, prose and escaped pipes are kept.
A table needs an ID and a status column to be imported. To keep a header such as `Status`, add it
to `[columns].aliases` first; otherwise mapped headers take taskrail's names. See DESIGN.md §7.3.

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
and not edited locally. The core `taskrail` skill and the `taskrail-autopilot` skill always install.

## Working on the checked-out branch

By default every task gets its own branch and worktree, commits at stage boundaries, stops for
approval at each `always` gate, and ends in a pull request. A repository worked by a single
maintainer, one agent at a time, straight on the checked-out branch, can switch each of those off
in `.taskrail/config.toml`:

```toml
[git]
worktree = "never"        # required by task_branch = "current"
task_branch = "current"   # no branch per task: work on whatever branch is checked out
commit = "on-done"        # commit nothing at stage boundaries; commit everything once the task is done
```

- `task_branch = "current"` — the skills skip the workspace step and claim in the checkout.
  `new --workspace`, `workspace` and `branch` exit 5, and `taskrail review` only reports: it
  fetches, rebases and pushes nothing, and `--publish` exits 5. The skills then **ask the human
  before any push**, and push with git only once approved.
- `commit = "on-done"` — after `taskrail done`, the skills make one or more logical commits of
  everything the task changed, the status change included. A kind descriptor may set `commit`
  too, and its value wins over `[git]`.

Each setting works on its own. To stop only for decisions rather than to approve each stage, give
a kind's stages `gate = "decisions"` in an override. An override replaces the whole kind, so copy
the core descriptor and change its gates — for example `.taskrail/overrides/chore/kind.toml`:

```toml
name = "chore"
summary = "Maintenance work whose change set and boundary are approved before anything is edited."
skill = "taskrail-chore"
commit_type = "chore"
artifact = "{artifacts}/chores/{id}-{slug}.md"
artifact_index = "{artifacts}/chores/README.md"

[[stage]]
name = "scope"
gate = "decisions"        # stop as soon as a decision appears, never to approve the stage

[[stage]]
name = "implement"
gate = "decisions"
checks = ["test", "lint"]

[[stage]]
name = "docs"
gate = "decisions"
```

A `decisions` stage stops when the executor meets a choice the task and its instructions do not
settle, and carries everything else it would report to the next stop or the close. The autopilot
needs a branch per task and commits per stage, so `taskrail autopilot start` refuses a repository
configured this way. See DESIGN.md §4, §5.6, §6.4, §7.1 and §8.

## Autopilot

The `taskrail-autopilot` skill runs several tasks at once, one lane per task, when the human asks
for it with a task count or names the tasks, and extends a live run when the human adds tasks to
it. The agent the human talks to orchestrates: it dispatches lanes with
`taskrail autopilot next`, answers their gates from the repository's governing documents, records
each decision on the task branch, escalates what the human must decide, and hands finished
branches over one at a time. A repository opts in with `[autopilot].enabled = true`; until then
`taskrail autopilot start` refuses with exit 5 and the skill stops. See DESIGN.md §12.

## Development

```bash
uv run pytest                                   # all tests
uv run pytest tests/test_validate.py -k cycle   # a single test
uv run taskrail --root <repo> validate          # run the CLI against a repository
```

To run taskrail from source in a repository that contains it, pin its path instead of a
release in `.taskrail/config.toml`. This repository pins its own root; one that keeps taskrail
in a subdirectory names that directory:

```toml
version = "local:."                # or "local:vendor/taskrail"
```

The wrapper then runs `uv run --project <checkout>/<path> taskrail`, so each worktree
uses its own branch's code, and `taskrail upgrade` leaves the pin alone. Elsewhere,
`TASKRAIL_BIN=/path/to/taskrail` points the wrapper at any build.

## Releasing

Releases are tagged `vX.Y.Z`. See [CHANGELOG.md](CHANGELOG.md).

`pyproject.toml` is the only place the version is written, and it must equal the tag without its
`v`: the wrapper accepts an installed CLI only when `v$(taskrail --version)` matches
the pin, so a mismatched build is never taken for the release.

1. In a pull request: set `version` in `pyproject.toml`, run `uv lock`, add the changelog entry.
2. After it is squash-merged: `git tag -a vX.Y.Z <merge commit> -m "taskrail X.Y.Z"`
   and `git push origin vX.Y.Z`. A published tag never moves.
3. Verify a clean install from the tag, on both routes, then bump `main` to the next `.dev0`
   version, so builds from `main` never claim to be the release.

## History

taskrail began as one tool inside a larger repository of agent skills and tools, and was extracted
into this repository with its history: authors, dates and commit messages are kept, while every
commit was rewritten to hold only taskrail, at the root. Pull request numbers in commit subjects
from before the extraction, such as `(#61)`, refer to pull requests in that earlier repository, not
in this one.

Release tags were `taskrail-vX.Y.Z` there and are `vX.Y.Z` here. 0.1.0 was released only there,
as `taskrail-v0.1.0`; the first release from this repository is 0.2.0. An install of 0.1.0 made
from the earlier repository keeps working, but its `taskrail self upgrade` and its wrappers look
for releases there. To move to a later release, reinstall from this repository as shown under
*Install*, then run `taskrail upgrade` in each repository that uses taskrail, so its wrapper and
version pin follow this repository.
