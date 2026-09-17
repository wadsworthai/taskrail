# T086 — Bump main to 0.4.0.dev0 after the v0.3.0 tag

Kind: chore · Epic: E01 · Status: scoped

## Goal

T085 released 0.3.0: its squash commit `dbc49d7` sets `version = "0.3.0"`, and the annotated tag
`v0.3.0` points at it. This chore does step 3 of the README's *Releasing* section, as T078 did after
T077. It records the tag, verifies a clean install from `github.com/wadsworthai/taskrail@v0.3.0`
with the checks T085 deferred to it (T085's *After the merge*, item 2), and then moves `main` to
`0.4.0.dev0`. While `main` reads `0.3.0`, every build of a later commit reports itself as the
release, and a consumer's wrapper pinned to `v0.3.0` would accept it.

### The tag

The task's precondition holds, so the scope stage does not stop. The tag exists on `origin`, and on
the canonical repository read anonymously, and it points at T085's squash commit:

```
$ GIT_TERMINAL_PROMPT=0 git ls-remote --tags origin
308498f6623b17dd7ee22823b8b815e148b5505c	refs/tags/v0.2.0
23e62e88591b082614526a5e295c1b6550c1b0d6	refs/tags/v0.2.0^{}
8fde8af69aff8211477eac9228bf26814531875e	refs/tags/v0.3.0
dbc49d7bad68238b8a8642cad95bc9d7b1ab75ec	refs/tags/v0.3.0^{}

$ GIT_TERMINAL_PROMPT=0 git ls-remote --tags https://github.com/wadsworthai/taskrail.git
308498f6623b17dd7ee22823b8b815e148b5505c	refs/tags/v0.2.0
23e62e88591b082614526a5e295c1b6550c1b0d6	refs/tags/v0.2.0^{}
8fde8af69aff8211477eac9228bf26814531875e	refs/tags/v0.3.0
dbc49d7bad68238b8a8642cad95bc9d7b1ab75ec	refs/tags/v0.3.0^{}

$ git for-each-ref refs/tags/v0.3.0 --format="%(refname) %(objectname) %(objecttype) %(*objectname) %(taggername) %(taggerdate:iso) %(contents:subject)"
refs/tags/v0.3.0 8fde8af69aff8211477eac9228bf26814531875e tag dbc49d7bad68238b8a8642cad95bc9d7b1ab75ec Alexander Rondon (archlinux) 2026-09-17 08:28:16 -0500 taskrail 0.3.0

$ git log --oneline -1 origin/main
dbc49d7 chore(release): release v0.3.0 (T085) (#18)
```

`v0.3.0` is an annotated tag (`8fde8af`) on `dbc49d7`, which is also `origin/main` and this
branch's base. The remote holds two tags, `v0.2.0` and `v0.3.0`.

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.4.0.dev0"` (from `0.3.0`). |
| `uv.lock` | Regenerated with `uv lock`: the `taskrail` package entry reads `version = "0.4.0.dev0"`. No other line changes. |
| `TODO.md` | Through the CLI only: T086's row with `taskrail done` at close. No table or prose line is edited by hand. |
| `docs/chores/T086-bump-main-to-0-4-0-dev0-after-the-v0-3-0.md` | This artifact, with the tag and the install results. |
| `docs/chores/README.md` | A row for this artifact. |

Files checked and left unchanged:

- `tests/test_version.py` passes for `0.4.0.dev0` as it is: the package version comes from
  `pyproject.toml`, and `release_tag()` drops the development suffix, so it expects `v0.4.0`.
- `.taskrail/installed.json` records `"version": "v0.3.0"`. See decision 2.
- `CHANGELOG.md` already has an empty `## Unreleased` above `## 0.3.0` (T085's decision 2). See
  decision 3.
- `README.md` line 17 (*Install* `@v0.3.0`) and `DESIGN.md` lines 3 (`released as v0.3.0`), 112 (pin
  example) and 1179 (install example) already name `v0.3.0`: T085's decision 4 moved them before the
  tag. They stay correct after the bump, now that the tag exists.
- `TODO.md` E01's *Done when* names `v0.2.0`, which is tagged and was installed through the wrapper
  in T078: the condition is met and stays met. See decision 4.
- `src/taskrail/cli.py` (the `--tag` help, `e.g. v0.2.0`) and `tests/test_install.py` use `v0.2.0` as
  an example of an existing tag, which it stays.
- The skills and `src/taskrail/integrations/` name no version.

## Decisions needed

1. **The change set.** Recommended: `pyproject.toml` and `uv.lock` only, which is what T085's
   *After the merge* defines and what T078 did apart from the E01 line it had to correct.
   Alternative: none that the precedent supports.
2. **`.taskrail/installed.json`'s `version`.** It is written only by `init` and `upgrade`, as
   `release_tag()` of the running CLI, and nothing reads it back. For `0.4.0.dev0` that would be
   `v0.4.0`, a tag that does not exist. The files it lists were last installed by a 0.3.0-line
   build, so `v0.3.0` is accurate today. Recommended: leave it, as T078 did; the next
   `.taskrail/bin/taskrail upgrade` on `main` rewrites it. This repository pins `local:.`, so the
   value affects nothing here. Alternative: run `.taskrail/bin/taskrail upgrade` in this change set.
3. **CHANGELOG.** Recommended: no entry. A development version on `main` is not a user-facing
   change, T016 and T078 added none, and `## Unreleased` already exists. Alternative: a bullet under
   `## Unreleased` saying that builds from `main` report `0.4.0.dev0`.
4. **E01's *Done when*.** It names `v0.2.0`. Unlike T078, where the line named a tag that never
   existed, the condition is met as written. Recommended: leave it. Alternative: change `v0.2.0` to
   `v0.3.0` by hand on that prose line, with this task's verification as its evidence.
5. **Pull request title.** Recommended:
   `chore(release): bump main to 0.4.0.dev0 after the v0.3.0 tag (T086)`, made with
   `--type chore --scope release`, as T078 and T085. Alternative: `--scope repo`.

## Out of scope

- Creating, moving, pushing or deleting any tag. `v0.3.0` exists and is only read. This clone also
  holds a local `v0.1.0` tag that is not on the remote; it is not touched either.
- `uv tool install` and `taskrail self upgrade` without `--dry-run`, which would replace the
  human's CLI (`~/.local/bin/taskrail`, which reports `taskrail 0.2.0`). Every install check uses
  `uvx` or a scratch virtual environment and scratch repositories under `/tmp/claude-7932/`.
- What `init` pins from a development build. `0.4.0.dev0` pins `v0.4.0`, a tag that does not exist
  until that release: the known `release_tag()` behaviour that T016 recorded and T078 repeated.
- A GitHub Release page, PyPI, and release automation.
- T003 (installing taskrail in a first consumer project), and every other version reference listed
  above.
- `.taskrail/installed.json` (decision 2).

## Verification

All checks run at the implement stage, with no tag operation and no `uv tool install`. `<wt>` is
this worktree. Scratch paths are `/tmp/claude-7932/T086-*`. Every install from the tag uses a fresh
`UV_CACHE_DIR=/tmp/claude-7932/T086-uv-cache`, so nothing comes from an earlier cache. The human's
`~/.local/bin` holds `taskrail` 0.2.0 as well as `uv` and `uvx`, so the wrapper checks run with a
restricted `PATH`: `/usr/bin:/bin`, plus `/tmp/claude-7932/T086-bin`, which holds only links to
`uv` and `uvx`, when a check needs them. `--root` is a global option and goes before the
subcommand (T078's correction).

The published tag, before the bump:

1. `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.3.0" taskrail --version` prints
   `taskrail 0.3.0`, built from `dbc49d7`.
2. `uv venv /tmp/claude-7932/T086-venv`, then
   `uv pip install --python /tmp/claude-7932/T086-venv "git+https://github.com/wadsworthai/taskrail.git@v0.3.0"`.
   After that, `/tmp/claude-7932/T086-venv/bin/taskrail --version` prints `taskrail 0.3.0`.
3. In a new git repository `/tmp/claude-7932/T086-scratch`,
   `/tmp/claude-7932/T086-venv/bin/taskrail --root /tmp/claude-7932/T086-scratch init --integration claude`
   writes `version = "v0.3.0"` to `.taskrail/config.toml`.
4. With `PATH=/tmp/claude-7932/T086-venv/bin:/usr/bin:/bin`, the scratch wrapper runs `--version`
   (`taskrail 0.3.0`) and `--root /tmp/claude-7932/T086-scratch validate` through the venv's CLI,
   because its version matches the pin. `sh -x` shows the `exec taskrail` branch.
5. With `PATH=/tmp/claude-7932/T086-bin:/usr/bin:/bin`, where no `taskrail` is found, the scratch
   wrapper falls back to
   `uvx --quiet --from git+https://github.com/wadsworthai/taskrail.git@v0.3.0 taskrail`. `sh -x`
   shows that command, and it runs `--version` (`taskrail 0.3.0`) and
   `--root /tmp/claude-7932/T086-scratch validate`, the latter with a second, empty uv cache.
6. `taskrail self upgrade --dry-run`, from the tag's CLI (the venv) and from this branch
   (`uv run --project <wt> taskrail`), resolves the latest tag and prints
   `uv tool install --force taskrail --from git+https://github.com/wadsworthai/taskrail.git@v0.3.0`.

The bump:

7. `uv lock` reports `Updated taskrail v0.3.0 -> v0.4.0.dev0`, `uv lock --check` passes, and
   `git diff uv.lock` is that one line.
8. `uv run --project <wt> taskrail --version` and `<wt>/.taskrail/bin/taskrail --version` (the
   `local:.` pin) print `taskrail 0.4.0.dev0`.
9. `uv build --out-dir /tmp/claude-7932/T086-build` builds `taskrail-0.4.0.dev0-py3-none-any.whl`.
10. The purpose of the bump, exercised: the wheel is installed into
    `/tmp/claude-7932/T086-devvenv`. With
    `PATH=/tmp/claude-7932/T086-devvenv/bin:/tmp/claude-7932/T086-bin:/usr/bin:/bin`, the scratch
    wrapper pinned to `v0.3.0` rejects the development build (`v0.4.0.dev0` ≠ `v0.3.0` in `sh -x`),
    falls back to `uvx` at `v0.3.0`, and prints `taskrail 0.3.0`.
11. `taskrail checks T086 --stage implement` runs `test` (`uv run pytest -q`). The stage's `lint`
    check is not configured in this repository's `checks` map.
12. `taskrail validate` on this branch.
