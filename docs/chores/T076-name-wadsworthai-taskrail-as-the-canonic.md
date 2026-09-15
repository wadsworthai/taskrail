# T076 — Name wadsworthai/taskrail as the canonical repository in the CLI, skills and docs

## Goal

taskrail's code, skills and documentation name `github.com/alexkander/taskrail` as the repository
to install and upgrade from. That repository cannot be read anonymously:

```
$ GIT_TERMINAL_PROMPT=0 git ls-remote --heads https://github.com/alexkander/taskrail.git
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

The canonical repository is `github.com/wadsworthai/taskrail`, this clone's `origin`
(`git@github.com:wadsworthai/taskrail.git`), and it can:

```
$ GIT_TERMINAL_PROMPT=0 git ls-remote --heads https://github.com/wadsworthai/taskrail.git
d904d11054a6ebb77309ef6d564b4510294fce2f	refs/heads/main
```

So the wrapper's `uvx` fallback, `taskrail self upgrade` and every install instruction point at a
repository a consumer cannot fetch. This chore points them at `wadsworthai/taskrail`.

The human also decided that no `v0.1.0` tag exists in this repository (`git ls-remote --tags origin`
prints nothing today). 0.1.0 was released from the repository taskrail was extracted from, tagged
`taskrail-v0.1.0` there (commit `3e64e63`, "tag and publish taskrail-v0.1.0 (T002)"). Text that
presents `v0.1.0` as installable from this repository must stop doing so. The first release from
this repository is T077's 0.2.0.

## Inventory

`grep -rn alexkander` over the worktree, excluding `.venv`, `.worktrees`, `.git` and caches:

| Class | Occurrence | Action |
|---|---|---|
| code | `src/taskrail/install.py:20` `SOURCE_URL` (feeds the wrapper template line 252, `latest_tag`, `self_upgrade_command`, `self_upgrade`) | change |
| tests | `tests/test_install.py:283` the `self upgrade --dry-run` command | change |
| skills, sources | `src/taskrail/skills/{taskrail,taskrail-autopilot,taskrail-bug,taskrail-chore,taskrail-feature,taskrail-spike}/SKILL.md:6` `metadata.source` | change |
| skills, installed copies | `.claude/skills/<same six>/SKILL.md:6` | regenerate with `taskrail upgrade` |
| managed wrapper | `.taskrail/bin/taskrail:32` (this repository's installed wrapper) | regenerate with `taskrail upgrade` |
| README | `README.md:17` install example (`@v0.1.0`) | change |
| CHANGELOG | `CHANGELOG.md:6` preamble install line; `CHANGELOG.md:41` the Unreleased "taskrail has its own repository" bullet | change |
| DESIGN.md | `DESIGN.md:1009` §9 install example (`@v0.1.0`) | change |
| backlog | `TODO.md:25`, T076's own description | leave: it describes this task |
| past task artifacts | `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md:564` (a clone command in a recorded experiment); `docs/features/T015-hand-closed-tasks-off-for-review-with-a.md:162` (the remote a verification ran against) | leave: they record what was run then |

`grep -rn 0.1.0` (same exclusions, and `uv.lock`) adds, beyond the lines above:

| Occurrence | Action |
|---|---|
| `README.md:182-186` *History*: tags were `taskrail-vX.Y.Z` there; an install of 0.1.0 from the earlier repository keeps working; reinstall from this repository to move on | keep, one clarifying clause (decision 3) |
| `CHANGELOG.md:277` `## 0.1.0` section | keep, with a note (decision 1) |
| `DESIGN.md:3` status line "v1 released as `v0.1.0`" | reword (decision 4) |
| `DESIGN.md:112` config example `version = "v0.1.0"` | `v0.2.0` (decision 2) |
| `src/taskrail/cli.py:1448` `self upgrade --tag` help "e.g. v0.1.0" | `v0.2.0` (decision 2) |
| `tests/test_install.py:280` `--tag v0.1.0` | `v0.2.0`, with the URL on line 283 (decision 2) |
| `tests/test_install.py:287` `release_tag("0.1.0.dev0") == "v0.1.0"` | leave: tests string handling, names no tag |
| `tests/conftest.py:12` fixture pin `version = "v0.1.0"` | leave: an in-process fixture, never fetched |
| `tests/test_merge_driver.py:594,736` `## 0.1.0` in changelog fixtures | leave: fixture text |
| `DESIGN.md:899` `## 0.1.0` › `### Added` as a merge-driver path example | leave: an example path |
| `TODO.md:14,19,23` E01's *Done when*, T002 and T016 rows | leave: closed backlog history |
| `docs/chores/T002-*`, `T016-*`, `T013-*`, `docs/chores/README.md`, `docs/features/T040-*`, `docs/bugs/T026-*`, `T053-*`, `docs/autopilot/decisions/T017-*` | leave: past task artifacts |

## Change set

Approved at the scope gate as proposed, except for `DESIGN.md`'s status line, which T077 owns
(decision record: `docs/autopilot/decisions/T076-name-wadsworthai-taskrail-as-the-canonic.md`).

| File | Change |
|---|---|
| `src/taskrail/install.py` | `SOURCE_URL = "https://github.com/wadsworthai/taskrail.git"`. The wrapper template, `latest_tag`, `self_upgrade_command` and `self_upgrade` all read it; nothing else changes. |
| `src/taskrail/cli.py` | `self upgrade --tag` help: `e.g. v0.2.0`. |
| `tests/test_install.py` | `test_self_upgrade_dry_run`: `--tag v0.2.0`, and assert the command names `git+https://github.com/wadsworthai/taskrail.git@v0.2.0`. |
| `src/taskrail/skills/*/SKILL.md` (six files) | `metadata.source: https://github.com/wadsworthai/taskrail`. |
| `.claude/skills/*/SKILL.md` (six files), `.taskrail/bin/taskrail`, `.taskrail/installed.json` | Regenerated by `.taskrail/bin/taskrail upgrade`, never edited by hand. The config's `local:.` pin is kept. |
| `README.md` | *Install*: `git+https://github.com/wadsworthai/taskrail.git@v0.2.0`. *History*: add that 0.1.0 exists only as `taskrail-v0.1.0` in the earlier repository, and that this repository's first release is 0.2.0 (decision 3). |
| `CHANGELOG.md` | Preamble install line: `wadsworthai`. Unreleased bullet "taskrail has its own repository": `github.com/wadsworthai/taskrail`. Under `## 0.1.0`, one line: released from the repository taskrail was extracted from, tagged `taskrail-v0.1.0` there; this repository has no `v0.1.0` tag. The `## Unreleased` heading is T077's and is not touched. |
| `DESIGN.md` | §4 config example pin `v0.2.0`; §9 install example `wadsworthai` at `@v0.2.0`. The status line (line 3) is not touched: T077 sets it for the 0.2.0 release (decision 4). |
| `docs/chores/T076-…md`, `docs/chores/README.md` | This artifact and its index row. |

The CHANGELOG gets no new bullet. The released 0.1.0 installed from the earlier repository, with
`#subdirectory`; moving to a repository of its own is still Unreleased, in the bullet "taskrail has
its own repository", so no release ever named the `alexkander` URL. That bullet is corrected rather
than contradicted by a second one. (This repository's rewritten history shows the `alexkander` URL
as far back as the 0.1.0 commit, `3e64e63`. The extraction's rewrite evidently put it there: that
commit's subject publishes `taskrail-v0.1.0`, while its README installs `@v0.1.0`.)

## Decisions needed

Decided at the scope gate:

1. `## 0.1.0` is kept, with one note line (the human's decision, option A).
2. Install examples and help text name `v0.2.0` (the human's decision, option A); the fixture and
   example `0.1.0` strings stay.
3. The clarifying clause in README *History* is added.
4. `DESIGN.md`'s status line is not changed here; T077 owns it (option B).
5. No code change for consumers pinned to `v0.1.0`.
6. The two past artifacts and T076's own row keep `alexkander`.

The options that were put forward:

1. **The CHANGELOG's `## 0.1.0` section.**
   - **A (recommended):** keep it as the history of the earlier repository's release, with one
     line under the heading saying it was tagged `taskrail-v0.1.0` there and that this repository
     has no `v0.1.0` tag. The Unreleased entries describe changes against that release, and the
     README's *History* already refers to it.
   - B: remove the section. The changelog would then start at 0.2.0, whose entries describe changes
     from a release it no longer documents.
   - C: leave it unchanged. Under a preamble that says releases are tagged `vX.Y.Z` here, it reads as
     a `v0.1.0` tag in this repository.
2. **Version named by install examples and help text** (`README.md:17`, `DESIGN.md:1009`,
   `DESIGN.md:112`, `cli.py` help, `test_self_upgrade_dry_run`).
   - **A (recommended):** `v0.2.0`. It is the release T077 prepares in this run, merged right after
     this branch; the README example is copy-pasteable once T077's tag is pushed, and names a tag
     that does not exist only between this merge and that tag.
   - B: a placeholder, `@vX.Y.Z` with "the latest release tag", as the CHANGELOG preamble already
     does. Never stale, but not copy-pasteable.
   - C: leave these lines for T077. T077's touch map does not include them, and the URL change makes
     these same lines, so splitting them adds a second pass over one line.
   The fixture `v0.1.0` values listed as "leave" above stay under every option: they name no
   fetchable tag. Change them too only if you want no `0.1.0` string outside history.
3. **README *History*.** Its paragraph is accurate: 0.1.0 was installed from the earlier repository,
   whose wrapper and `self upgrade` look there, and moving on means reinstalling from this one.
   **Recommended:** keep it and add one clause, e.g. "0.1.0 was released only there, as
   `taskrail-v0.1.0`; the first release from this repository is 0.2.0." Alternative: leave it word
   for word.
4. **DESIGN.md status line** "Status: **v1 released as `v0.1.0`.**"
   - **A (recommended):** "Status: **v1 released as 0.1.0** (tagged `taskrail-v0.1.0` in the
     repository taskrail was extracted from). See CHANGELOG.md." True now; T077 may update it when it
     releases 0.2.0.
   - B: leave it to T077, which would rewrite it to name `v0.2.0`. Until then it names a tag this
     repository lacks.
5. **Consumers pinned to `v0.1.0`: no code change (recommended).** A repository installed by 0.1.0
   has 0.1.0's wrapper, which fetches from the earlier repository, and keeps working. Once
   `taskrail upgrade` rewrites its wrapper with a newer CLI, the same command moves its pin to that
   CLI's release, so the new wrapper never looks for `v0.1.0` here. Only a pin hand-edited back to
   `v0.1.0` would fail in `uvx`. Alternative, not recommended: map `v0.1.0` to the earlier
   repository in the wrapper or `self upgrade`, which would put that repository's location back
   into this one.

## Out of scope

- Any tag: none is created, pushed or deleted. The 0.2.0 version, `uv lock`, the `## Unreleased`
  heading and any consolidation of its bullets, and `DESIGN.md`'s status line are T077's.
- `install.release_tag()`, unchanged. It matters here only in this way: a build from `main`
  (`0.2.0.dev0`) pins `v0.2.0` on `init` and `upgrade`, and that pin's `uvx` fallback, now pointed at
  `wadsworthai/taskrail`, resolves only after T077's `v0.2.0` tag is pushed. Likewise
  `taskrail self upgrade` without `--tag` finds no `v*` tag here until then.
- Past task artifacts under `docs/`, the closed rows in `TODO.md`, and T076's own row.
- The git host detection in `review.py`, and the `github.com` URLs of test fixtures that are not
  taskrail's repository.
- `CLAUDE.md`, which names no repository URL.

## Verification

Actual results. `<wt>` is the task's worktree; `uv run --project <wt> taskrail` runs this branch's
code; `<scratch>` is a fresh `git init` repository outside the clone.

- `grep -rn alexkander <wt>` (excluding `.venv`, `.worktrees`, `.git` and caches) prints only
  `TODO.md:25` (T076's row), `docs/spikes/T007-…md:564`, `docs/features/T015-…md:162`, this
  artifact and T076's decision record. Nothing in `src/`, `tests/`, `.claude/`, `.taskrail/`,
  `README.md`, `CHANGELOG.md` or `DESIGN.md`.
- `.taskrail/bin/taskrail upgrade` printed `updated` for `.taskrail/bin/taskrail` and the six
  `.claude/skills/*/SKILL.md` copies, and `5 file(s) already up to date`. The config still reads
  `version = "local:."`. In `git diff`, each installed copy's hunk is the same one-line `source`
  change as its source, and the wrapper's only change is its `uvx` line.
- `uv run --project <wt> taskrail self upgrade --tag v0.2.0 --dry-run` printed
  `uv tool install --force taskrail --from git+https://github.com/wadsworthai/taskrail.git@v0.2.0`.
- `GIT_TERMINAL_PROMPT=0 uv run --project <wt> taskrail self upgrade --dry-run` exited 3 with
  `taskrail: no v* release tag found at https://github.com/wadsworthai/taskrail.git`: the repository
  was read anonymously and has no release tag yet. The same command with
  `TASKRAIL_SOURCE=https://github.com/alexkander/taskrail.git`, the old default, exited 2 with
  `git ls-remote --tags --refs https://github.com/alexkander/taskrail.git v*: fatal: could not read
  Username for 'https://github.com': terminal prompts disabled`.
- `uv run --project <wt> taskrail --root <scratch> init --integration claude` created the config
  (`version = "v0.2.0"`), the wrapper, whose line 32 is
  `exec uvx --quiet --from "git+${TASKRAIL_SOURCE:-https://github.com/wadsworthai/taskrail.git}@$pin" taskrail "$@"`,
  and six `SKILL.md` files with `source: https://github.com/wadsworthai/taskrail`.
- The scratch wrapper, with the installed CLI at `taskrail 0.2.0.dev0`:
  - pin `v0.2.0`: `--version` exited 1 with uv's `Failed to resolve --with requirement` /
    `Git operation failed`, since the tag does not exist yet (the `release_tag()` note under
    *Out of scope*);
  - pin `main`: `sh -x` shows `pin=main`, the installed CLI rejected (`v0.2.0.dev0` ≠ `main`), and
    `exec uvx --quiet --from git+https://github.com/wadsworthai/taskrail.git@main taskrail --version`,
    which printed `taskrail 0.2.0.dev0`. `--root <scratch> validate` through it printed
    `history: not checked (no commits)` and `0 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`;
  - pin `main` with `TASKRAIL_SOURCE=https://github.com/alexkander/taskrail.git`: exited 1 with
    `Git operation failed`.
- `taskrail checks T076 --stage implement`: `test` (`uv run pytest -q`) gave
  `1052 passed in 132.34s (0:02:12)`; `lint` is not configured in the `checks` map.

## Docs

Nothing else to update. The documentation this change affects — `README.md`, `CHANGELOG.md`,
`DESIGN.md` and the skills — was part of the approved change set and changed in the implement
commit. `grep -rn -e alexkander -e v0.1.0 -e github.com/` over `CLAUDE.md`,
`src/taskrail/integrations/`, `examples/` and `pyproject.toml` prints nothing: none of them names
the repository or a release tag. No follow-up tasks were opened.
