# T128 — Install from the v0.4.0 tag and bump main to 0.5.0.dev0

Kind: chore · Epic: E10 · Status: scoped, awaiting approval

## Goal

T127 released 0.4.0: its squash commit `a0994e3` sets `version = "0.4.0"`, and the annotated tag
`v0.4.0` points at it. This chore does step 3 of the README's *Releasing* section, as T086 did after
T085: verify a clean install from `github.com/wadsworthai/taskrail@v0.4.0`, then move `main` to
`0.5.0.dev0`, so that no build of a later commit reports itself as the release.

T127 could only install from a locally built wheel, because the tag did not exist yet. This task
installs from **the published tag over the network**, by the route README's *Install* documents
and a consumer will take: `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.4.0"
taskrail init` in a fresh repository, then the committed wrapper, which resolves the `v0.4.0` pin
through `uvx`.

### The tag

The task's precondition holds. The tag is on `origin` and on the canonical repository read
anonymously, and it peels to T127's squash commit, which is also `origin/main` and this branch's
base:

```
$ git ls-remote --tags origin
308498f6623b17dd7ee22823b8b815e148b5505c	refs/tags/v0.2.0
23e62e88591b082614526a5e295c1b6550c1b0d6	refs/tags/v0.2.0^{}
8fde8af69aff8211477eac9228bf26814531875e	refs/tags/v0.3.0
dbc49d7bad68238b8a8642cad95bc9d7b1ab75ec	refs/tags/v0.3.0^{}
102c597e93d3acc4f235f69545493b381f738c1b	refs/tags/v0.4.0
a0994e363ea255e90460a7388909245051732071	refs/tags/v0.4.0^{}

$ env GIT_TERMINAL_PROMPT=0 git ls-remote --tags https://github.com/wadsworthai/taskrail.git
(the same six lines)

$ git for-each-ref refs/tags/v0.4.0 --format="%(refname) %(objectname) %(objecttype) %(*objectname) %(taggername) %(taggerdate:iso) %(contents:subject)"
refs/tags/v0.4.0 102c597e93d3acc4f235f69545493b381f738c1b tag a0994e363ea255e90460a7388909245051732071 Alexander Rondon (archlinux) 2026-09-19 05:06:07 -0500 taskrail 0.4.0
```

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.5.0.dev0"` (from `0.4.0`). |
| `uv.lock` | Regenerated with `uv lock`: the `taskrail` package entry reads `version = "0.5.0.dev0"`. No other line changes. |
| `TODO.md` | Through the CLI only: T128's row with `taskrail done` at close. |
| `docs/chores/T128-install-from-the-v0-4-0-tag-and-bump-mai.md` | This artifact, with the install results. |
| `docs/chores/README.md` | A row for this artifact. |

Files checked and left unchanged:

- No other file names the development version. A grep for `0.4.0`, `0.5.0` and `dev0` outside
  `docs/` finds `pyproject.toml` and `uv.lock` (the two lines above); README's *Install* examples
  (`@v0.4.0`, lines 22 and 35) and DESIGN.md's status line (3), pin example (138), its note that
  the backlog `file` key was required before v0.4.0 (221) and install examples (1322, 1331), all naming the release, which stays correct;
  `CHANGELOG.md`; `.taskrail/installed.json`; the T127 and T128 rows in `TODO.md`; and
  `tests/test_install.py:350`, which uses `0.1.0.dev0` as an example.
- `tests/test_version.py` reads the version from `pyproject.toml` and expects `release_tag()` to
  drop the suffix, so it passes for `0.5.0.dev0` unchanged.
- `.taskrail/installed.json` records `"version": "v0.4.0"`. See decision 3.
- `CHANGELOG.md` already has an empty `## Unreleased` above `## 0.4.0`. See decision 4.
- E10's *Done when* ("each version is tagged from a squash-merged release pull request and
  installs cleanly from its tag") names no version, and this task is the evidence for v0.4.0.

## Decisions needed

1. **The verification commands, and what counts as a pass.** Recommended: the checks under
   *Verification* below, run at the implement stage. The ones that make this task more than T127's
   local checks are 1–4: `uvx` fetches and builds from the tag over the network, with an empty uv
   cache, a `PATH` that holds `uv`/`uvx` but no `taskrail`, and `VIRTUAL_ENV` unset; `init` runs
   exactly as README shows it, from inside the scratch repository; the wrapper's `sh -x` trace
   shows `installed=` empty and the `exec uvx … @v0.4.0` line, and the output reads
   `taskrail 0.4.0`. Where uvx resolved it from is shown by uv's own `Updated … (a0994e3…)` and
   `Built taskrail @ git+…@a0994e3…` lines, and by the `taskrail` module's path inside the uv
   cache. README's step 3 says "on both routes"; the second route, a global CLI, is exercised with
   `uv pip install` into a scratch virtual environment, since `uv tool install` is out of bounds on
   this machine. Alternatives: the uvx route only (drops checks 5–6), or add `uv tool install` with
   `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` pointed at scratch directories — which I do not recommend, since
   the brief forbids `uv tool install` outright.

2. **The generated workflow from the tag.** Recommended: yes, check it, because a consumer's first
   CI run on `v0.4.0` depends on it and T116 fixed it for every earlier release. What can be
   checked here:
   - `init --github-workflow` from the tag writes `.github/workflows/taskrail.yml`, and it is
     byte-identical to this repository's own `.github/workflows/taskrail.yml` at `a0994e3`;
   - the two actions it pins exist, read anonymously (already run while scoping):
     `git ls-remote --tags https://github.com/actions/checkout.git refs/tags/v7.0.1` →
     `3d3c42e5aac5ba805825da76410c181273ba90b1	refs/tags/v7.0.1`, and
     `git ls-remote --tags https://github.com/astral-sh/setup-uv.git refs/tags/v10.1.0` →
     `bec219d24cd3e171d82865faccec33120bb574f4	refs/tags/v10.1.0`;
   - it parses as YAML (`uv run --no-project --with pyyaml python -c …`, in the scratch directory);
   - its one `run` step, `.taskrail/bin/taskrail validate`, succeeds in the scratch repository after
     `init`'s files are committed, with full history, under the same restricted `PATH` — which is
     what a runner with only `setup-uv` on it does.

   What cannot be checked here: a real GitHub Actions run of the workflow in a consumer on
   `v0.4.0`. The nearest evidence is this repository's own run of the identical file on the push
   of `a0994e3` to `main`; `gh` is not installed on this machine, so reading it would take an
   anonymous `curl` of the public GitHub REST API
   (`/repos/wadsworthai/taskrail/actions/runs?head_sha=a0994e3…`), and that run goes through this
   repository's `local:.` pin, not through `uvx` from the tag. Recommended: include that `curl`
   as supporting evidence, labelled as such. Alternatives: skip the workflow checks (T086 had none,
   but its tag's workflow was the broken one), or skip only the `curl`.

3. **The bump.** Recommended: `pyproject.toml` and `uv.lock` only, as T078 and T086. No other file
   names the development version. `.taskrail/installed.json` stays at `v0.4.0`: it is written only by
   `init` and `upgrade` as `release_tag()` of the running CLI, nothing reads it back, and an
   `upgrade` from `0.5.0.dev0` would record `v0.5.0`, a tag that does not exist; `v0.4.0` is
   accurate for the files installed now, and this repository pins `local:.` so the value affects
   nothing. Alternative: run `.taskrail/bin/taskrail upgrade` in this change set.

4. **CHANGELOG.** Recommended: nothing. `## Unreleased` already exists and is empty (T127), and a
   development version on `main` is not a user-facing change (T016, T078, T086 added none).
   Alternative: a bullet saying builds from `main` report `0.5.0.dev0`.

5. **Pull request title.** Recommended:
   `chore(release): bump main to 0.5.0.dev0 after the v0.4.0 tag (T128)`, with
   `--type chore --scope release`, as T078, T085, T086 and T127. Alternative: `--scope repo`.

## Out of scope

- Creating, moving, pushing or deleting any tag. `v0.4.0` is published and only read. This clone's
  local `v0.1.0` tag is not touched either.
- `uv tool install`, and `taskrail self upgrade` without `--dry-run`, which would replace the
  human's CLI in `~/.local/bin`. Every install uses `uvx` or a scratch virtual environment.
- What `init` pins from a development build: `0.5.0.dev0` pins `v0.5.0`, which does not exist until
  that release — the known `release_tag()` behaviour T016 recorded.
- A GitHub Release page, PyPI, and release automation.
- Any change to README, DESIGN.md, the skills, the integrations or the workflow template.
- `.taskrail/installed.json` (decision 3) and `CHANGELOG.md` (decision 4).

## Verification

All checks run at the implement stage. `<wt>` is this worktree; `<s>` is a scratch directory under
the agent's scratchpad, outside every repository. `<s>/bin` holds only symbolic links to `uv` and
`uvx`, because the human's `~/.local/bin` also holds their global `taskrail`. Unless a check says
otherwise, every command runs under `env -u VIRTUAL_ENV PATH=<s>/bin:/usr/bin:/bin`, where
`command -v taskrail` finds nothing (shown first), and every uv call from the tag uses its own
fresh `UV_CACHE_DIR` under `<s>`, so nothing comes from an earlier build. `--root` goes before the
subcommand.

The published tag, before the bump — the `uvx` route:

1. `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.4.0" taskrail --version`, with
   an empty cache, prints uv's `Updated … (a0994e363ea2…)` and `Built taskrail @ git+…@a0994e3…`
   lines and `taskrail 0.4.0`. The same `uvx --from …` running
   `python -c "import taskrail; print(taskrail.__file__)"` prints a path inside `<s>`'s uv cache,
   not this checkout.
2. In a fresh `git init <s>/repo`, from inside it (`env -C <s>/repo …`), README's command
   `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.4.0" taskrail init --integration claude --github-workflow`
   writes `.taskrail/config.toml` with `version = "v0.4.0"`, `TASKRAIL.md`, the wrapper, the
   skills under `.claude/skills/`, `.gitignore` and `.github/workflows/taskrail.yml`. The files are
   then committed in the scratch repository.
3. With a second empty cache, `sh -x <s>/repo/.taskrail/bin/taskrail --version` traces `pin=v0.4.0`,
   `installed=` (empty) and
   `exec uvx --quiet --from git+https://github.com/wadsworthai/taskrail.git@v0.4.0 taskrail --root <s>/repo --version`,
   and prints `taskrail 0.4.0`.
4. The wrapper runs `validate` from outside the repository (T118's root) and prints
   `0 error(s), 0 warning(s)`, with the history check running over the scratch commit.

The published tag — the installed-CLI route:

5. `uv venv <s>/venv`, then `uv pip install --python <s>/venv "git+https://github.com/wadsworthai/taskrail.git@v0.4.0"`
   prints `+ taskrail==0.4.0 (from git+…@a0994e3…)`, and `<s>/venv/bin/taskrail --version` prints
   `taskrail 0.4.0`. With `PATH=<s>/venv/bin:<s>/bin:/usr/bin:/bin`, `sh -x` of the wrapper shows
   `have=0.4.0`, `'[' v0.4.0 = v0.4.0 ']'` and `exec taskrail --root <s>/repo --version`.
6. `GIT_TERMINAL_PROMPT=0 <s>/venv/bin/taskrail self upgrade --dry-run` prints
   `uv tool install --force taskrail --from git+https://github.com/wadsworthai/taskrail.git@v0.4.0`.

The generated workflow (decision 2):

7. `cmp` of `<s>/repo/.github/workflows/taskrail.yml` against `git show a0994e3:.github/workflows/taskrail.yml`
   reports no difference; it parses as YAML; the two pinned action tags exist (above); its `run`
   step is check 4. If approved, the anonymous `curl` for the `taskrail` workflow's run on
   `a0994e3`, reported as supporting evidence only.

The bump:

8. `uv lock --project <wt>` reports `Updated taskrail v0.4.0 -> v0.5.0.dev0`, `uv lock --check`
   passes, and `git diff` shows one line in each of `pyproject.toml` and `uv.lock`.
9. `uv run --project <wt> taskrail --version` and `<wt>/.taskrail/bin/taskrail --version` (the
   `local:.` pin) print `taskrail 0.5.0.dev0`.
10. `uv build --project <wt> --out-dir <s>/build` builds `taskrail-0.5.0.dev0-py3-none-any.whl`.
    Installed into `<s>/devvenv`, with `PATH=<s>/devvenv/bin:<s>/bin:/usr/bin:/bin`, the scratch
    wrapper pinned to `v0.4.0` rejects it (`'[' v0.5.0.dev0 = v0.4.0 ']'`), falls back to `uvx` at
    `v0.4.0`, and prints `taskrail 0.4.0`.
11. `taskrail checks T128 --stage implement` runs `test` (`uv run pytest -q`); `lint` is not
    configured in this repository.
12. `taskrail validate` on this branch, and `git diff --check`.
