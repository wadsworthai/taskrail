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
taskrail show T012 --json              # kind, stages, branch, artifact path, blockers
taskrail claim T012                    # reserve it; fails if someone else holds it
taskrail new --epic E01 --kind bug --title "Round totals half-up" --pts 2
taskrail done T012                     # needs your claim; releases it
taskrail epic add --name Auth --objective "Sign in without passwords" --own-file
taskrail epic split E01                # move an inline epic to todo/E01-<slug>.md
taskrail upgrade                       # re-install skills for this CLI version and pin it
taskrail self upgrade                  # update the CLI to the latest release
```

Every command accepts `--json`. Exit codes are listed in DESIGN.md.

## Task kinds

The core kinds are `bug`, `chore`, `feature` and `spike`, each with its executor skill. A
repository adds its own under `.taskrail/types/<kind>/kind.toml`, or adjusts a core kind under
`.taskrail/overrides/<kind>/kind.toml`. [examples/spec-kit](examples/spec-kit) shows a `spec`
kind that routes to a project's own Spec Kit skills.

## Development

```bash
uv run pytest                                   # all tests
uv run pytest tests/test_validate.py -k cycle   # a single test
uv run taskrail --root <repo> validate          # run the CLI against a repository
```

Before a release tag exists, point the wrapper at a development build with
`TASKRAIL_BIN=/path/to/taskrail`.
