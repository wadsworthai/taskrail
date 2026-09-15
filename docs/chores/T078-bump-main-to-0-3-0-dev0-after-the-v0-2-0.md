# T078 — Bump main to 0.3.0.dev0 after the v0.2.0 tag

Kind: chore · Epic: E01 · Status: scoped, awaiting approval

## Goal

T077 released 0.2.0: its squash commit `23e62e8` sets `version = "0.2.0"`, and the annotated tag
`v0.2.0` points at it. This chore does step 3 of the README's *Releasing* section. It records the
tag, verifies a clean install from `github.com/wadsworthai/taskrail@v0.2.0` with the checks T077
deferred, and then moves `main` to `0.3.0.dev0`. While `main` reads `0.2.0`, every build of a later
commit reports itself as the release, and a consumer's wrapper pinned to `v0.2.0` would accept it.

### The tag

The task's precondition holds, so the scope stage does not stop. The tag exists on the canonical
repository, which can be read anonymously, and it points at T077's squash commit:

```
$ GIT_TERMINAL_PROMPT=0 git ls-remote --tags https://github.com/wadsworthai/taskrail.git
308498f6623b17dd7ee22823b8b815e148b5505c	refs/tags/v0.2.0
23e62e88591b082614526a5e295c1b6550c1b0d6	refs/tags/v0.2.0^{}

$ git for-each-ref refs/tags/v0.2.0 --format="%(refname) %(objectname) %(objecttype) %(*objectname) %(taggername) %(taggerdate:iso) %(contents:subject)"
refs/tags/v0.2.0 308498f6623b17dd7ee22823b8b815e148b5505c tag 23e62e88591b082614526a5e295c1b6550c1b0d6 Alexander Rondon (archlinux) 2026-09-15 11:53:53 -0500 taskrail 0.2.0

$ git log --oneline -1 origin/main
23e62e8 chore(release): release v0.2.0 from the canonical repository (T077) (#9)
```

`v0.2.0` is an annotated tag (`308498f`) on `23e62e8`, which is also `origin/main` and this
branch's base. It is the only tag on the repository.

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.3.0.dev0"` (from `0.2.0`). |
| `uv.lock` | Regenerated with `uv lock`: the `taskrail` package entry reads `version = "0.3.0.dev0"`. No other line changes. |
| `TODO.md` | E01's *Done when* line only, if decision 3 is approved: `Done when: v0.2.0 is tagged and a repository installs it with uv and runs it through the wrapper.` Also, through the CLI, T078's row with `taskrail done` at close. No table is edited by hand. |
| `docs/chores/T078-bump-main-to-0-3-0-dev0-after-the-v0-2-0.md` | This artifact, with the tag and the install results. |
| `docs/chores/README.md` | A row for this artifact. |

Files checked and left unchanged:

- `tests/test_version.py` passes for `0.3.0.dev0` as it is. The package version comes from
  `pyproject.toml`, and T016 made the release-tag test drop the development suffix, so it expects
  `v0.3.0`.
- `.taskrail/installed.json` records `"version": "v0.2.0"`. See decision 2.
- `CHANGELOG.md` already has an empty `## Unreleased` above `## 0.2.0` (T077's decision 3). See
  decision 4.
- `README.md` (*Install* `@v0.2.0`, *History*), `DESIGN.md` (line 3 `released as v0.2.0`, line 112
  pin example, line 1009 install example), `src/taskrail/cli.py` (the `--tag` help, `e.g. v0.2.0`)
  and `tests/test_install.py` all name `v0.2.0`, which is now the published release. They stay
  correct after the bump.
- The skills and `src/taskrail/integrations/` name no version.

## Decisions needed

1. **The change set.** Recommended: `pyproject.toml` and `uv.lock`, as T016 did for 0.2.0.dev0, plus
   decision 3's one line. Alternative: only `pyproject.toml` and `uv.lock`.
2. **`.taskrail/installed.json`'s `version`.** It is written only by `save_manifest()` during
   `init` and `upgrade`, as `release_tag()` of the running CLI, and no code or test reads it back.
   For `0.3.0.dev0` that would be `v0.3.0`, a tag that does not exist. The files it lists were last
   installed by a 0.2.0-line build, so `v0.2.0` is accurate today. Recommended: leave it. The next
   `.taskrail/bin/taskrail upgrade` on `main`, run for a skill change, rewrites it to `v0.3.0`
   together with the files it installs. This repository pins `local:.`, so the value affects
   nothing here. Alternative: run `.taskrail/bin/taskrail upgrade` in this change set, which moves it
   to `v0.3.0` now, without installing any other change.
3. **E01's *Done when*** reads `v0.1.0 is tagged and a repository installs it with uv and runs it
   through the wrapper.` T076 established that no `v0.1.0` tag exists in this repository and never
   will, so the condition can no longer be met as written. E01 is still open (T003 is pending).
   Recommended: change `v0.1.0` to `v0.2.0` in this change set. This task's verification is the
   evidence for that condition, a tag plus a uv install run through the wrapper, so the line and its
   proof travel together. `taskrail` has no command for an epic's *Done when* (`epic` has only `add`
   and `split`), so this is a hand edit of that prose line only, and `taskrail validate` checks it.
   Alternatives: (a) a follow-up chore in E01 that makes the same edit; (b) leave the line as it is,
   as T076 did with the closed rows.
4. **CHANGELOG.** Recommended: no entry. A development version on `main` is not a user-facing
   change, T016 added none, and `## Unreleased` already exists. Alternative: a bullet under
   `## Unreleased` saying that builds from `main` report `0.3.0.dev0`.
5. **Pull request title.** Recommended: `chore(release): bump main to 0.3.0.dev0 after the v0.2.0 tag (T078)`,
   made with `--type chore --scope release`, the same scope as T077. Alternative: `--scope repo`.

## Out of scope

- Creating, moving, pushing or deleting any tag. `v0.2.0` exists and is only read.
- `uv tool install` and `taskrail self upgrade` without `--dry-run`, which would replace the
  human's CLI (`~/.local/bin/taskrail`, which reports `taskrail 0.2.0`). Every install check uses
  `uvx` or a scratch virtual environment and scratch repositories under `/tmp/claude-7932/`.
- What `init` pins from a development build. `0.3.0.dev0` pins `v0.3.0`, a tag that does not exist
  until that release. This is the known `release_tag()` behaviour that T016 recorded and T076
  repeated.
- A GitHub Release page, PyPI, and release automation.
- T003 (installing taskrail in a first consumer project), and every other `v0.2.0` or `0.1.0`
  reference listed above.
- `.taskrail/installed.json`, unless decision 2's alternative is chosen.

## Verification

All checks run at the implement stage, with no tag operation and no `uv tool install`. `<wt>` is
this worktree. Scratch paths are `/tmp/claude-7932/T078-*`. Every install from the tag uses a fresh
`UV_CACHE_DIR=/tmp/claude-7932/T078-uv-cache`, so nothing comes from an earlier cache. The human's
`~/.local/bin` holds `taskrail` 0.2.0 as well as `uv` and `uvx`, so the wrapper checks run with a
restricted `PATH`: `/usr/bin:/bin`, plus `/tmp/claude-7932/T078-bin`, which holds only links to
`uv` and `uvx`, when a check needs them.

The published tag, before the bump:

1. `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.2.0" taskrail --version` prints
   `taskrail 0.2.0`.
2. `uv venv /tmp/claude-7932/T078-venv`, then
   `uv pip install --python /tmp/claude-7932/T078-venv "git+https://github.com/wadsworthai/taskrail.git@v0.2.0"`.
   After that, `/tmp/claude-7932/T078-venv/bin/taskrail --version` prints `taskrail 0.2.0`.
3. In a new git repository `/tmp/claude-7932/T078-scratch`,
   `/tmp/claude-7932/T078-venv/bin/taskrail --root /tmp/claude-7932/T078-scratch init --integration claude`
   writes `version = "v0.2.0"` to `.taskrail/config.toml`.
4. With `PATH=/tmp/claude-7932/T078-venv/bin:/usr/bin:/bin`, the scratch wrapper runs
   `--version` (`taskrail 0.2.0`) and `validate --root /tmp/claude-7932/T078-scratch` through the
   venv's CLI, because its version matches the pin. `sh -x` shows the `exec taskrail` branch.
5. With `PATH=/tmp/claude-7932/T078-bin:/usr/bin:/bin`, where no `taskrail` is found, the scratch
   wrapper falls back to
   `uvx --quiet --from git+https://github.com/wadsworthai/taskrail.git@v0.2.0 taskrail`. `sh -x`
   shows that command, and it runs `--version` (`taskrail 0.2.0`) and
   `validate --root /tmp/claude-7932/T078-scratch`.
6. `taskrail self upgrade --dry-run`, from the tag's CLI (the venv) and from this branch
   (`uv run --project <wt> taskrail`), resolves the latest tag and prints
   `uv tool install --force taskrail --from git+https://github.com/wadsworthai/taskrail.git@v0.2.0`.

The bump:

7. `uv lock` reports `Updated taskrail v0.2.0 -> v0.3.0.dev0`, `uv lock --check` passes, and
   `git diff uv.lock` is that one line.
8. `uv run --project <wt> taskrail --version` and `<wt>/.taskrail/bin/taskrail --version` (the
   `local:.` pin) print `taskrail 0.3.0.dev0`.
9. `uv build --out-dir /tmp/claude-7932/T078-build` builds `taskrail-0.3.0.dev0-py3-none-any.whl`.
10. The purpose of the bump, exercised: the wheel is installed into
    `/tmp/claude-7932/T078-devvenv`. With
    `PATH=/tmp/claude-7932/T078-devvenv/bin:/tmp/claude-7932/T078-bin:/usr/bin:/bin`, the scratch
    wrapper pinned to `v0.2.0` rejects the development build (`v0.3.0.dev0` ≠ `v0.2.0` in `sh -x`),
    falls back to `uvx` at `v0.2.0`, and prints `taskrail 0.2.0`.
11. `taskrail checks T078 --stage implement` runs `test` (`uv run pytest -q`). The stage's `lint`
    check is not configured in this repository's `checks` map.
12. `taskrail validate` on this branch.
