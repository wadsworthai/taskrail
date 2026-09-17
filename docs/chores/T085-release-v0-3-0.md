# T085 — Release v0.3.0

Kind: chore · Epic: E01 · Status: implemented, awaiting review; the tag follows the merge

## Goal

Release taskrail 0.3.0 from `github.com/wadsworthai/taskrail`. `main` reads `0.3.0.dev0`, `v0.2.0`
is the only tag on `origin`, and `## Unreleased` in `CHANGELOG.md` holds the current-branch
workflow (E07): `[git] task_branch = "current"` (T080), `commit = "on-done"` (T081),
`gate = "decisions"` (T082), a report-only `review` under the current branch (T083), and the skills
that follow those settings (T084).

This follows T077 (the v0.2.0 release) and T078 (the install from the tag and the bump). The
README's *Releasing* section has three steps: (1) in a pull request, set `version`, run `uv lock`
and add the changelog entry; (2) after the squash merge, tag the merge commit and push the tag;
(3) verify a clean install from the tag, then bump `main` to the next `.dev0`. This branch carries
step (1). Steps (2) and (3) follow the merge, as described under *After the merge*.

### Semantic versioning

Every change on `main` since `v0.2.0` is a feature, a design document or a backlog or release
chore:

```
$ git log v0.2.0..origin/main --oneline
4a2f15c feat(skills): teach the skills the current-branch workflow, on-done commits and decisions gates (T084) (#17)
befd863 feat(cli): close a current-branch task without fetch, rebase or publish (T083) (#16)
59adba0 feat(cli): commit a task's changes only when it is done with commit = on-done (T081) (#15)
456f3bc feat(cli): work a task on the checked-out branch with task_branch = current (T080) (#14)
49ccec0 feat(cli): add a decisions gate that stops for each decision instead of each stage (T082) (#13)
f0eafa9 docs(repo): write the current-branch workflow into DESIGN.md (T079) (#12)
93823c6 chore(backlog): add the current-branch workflow epic (E07) (#11)
5c77d08 chore(release): bump main to 0.3.0.dev0 after the v0.2.0 tag (T078) (#10)
```

No subject is marked breaking, and `## Unreleased` has no **Behaviour change** entry. Each new
setting defaults to the 0.2.0 behaviour (`task_branch = "task"`, `commit = "stages"`, the kinds'
existing gates), and `show --json` and `kind list --json` only add keys (`task_branch`, `close`,
`commit`, `commit_source`). `git diff v0.2.0 origin/main -- tests` removes no `assert` line.

One edge is worth naming, and is not breaking in practice. A kind descriptor's top-level `commit`
key was ignored in 0.2.0, as unknown keys are, and a value other than `"stages"` or `"on-done"` is
now a `kind-invalid` error. A descriptor that already carried such a key would have had no effect,
and no core or example kind has one.

Pre-1.0, features take a minor bump: the release is `0.3.0`.

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.3.0"` (from `0.3.0.dev0`). |
| `uv.lock` | Regenerated with `uv lock`: the `taskrail` package entry reads `version = "0.3.0"`. No other line changes. |
| `CHANGELOG.md` | `## Unreleased` becomes `## 0.3.0`, with a new empty `## Unreleased` above it and a lead paragraph under `## 0.3.0` (decision 2), plus the corrections in decision 3. No bullet is reordered. The preamble, `## 0.2.0` and `## 0.1.0` are not touched. |
| `DESIGN.md` | Line 3: `Status: **released as `v0.3.0`.** See CHANGELOG.md.` Also the two install and pin examples of decision 4: line 112 `version = "v0.3.0"` and line 1179 `...taskrail.git@v0.3.0"`. |
| `README.md` | Line 17, the *Install* example, names `@v0.3.0` (decision 4). |
| `TODO.md` | Through the CLI only: the follow-up chore (see *After the merge*) with `taskrail new`, T085's description with `taskrail edit` (decision 5), and T085's row with `taskrail done` at close. |
| `docs/chores/T085-release-v0-3-0.md` | This artifact. |
| `docs/chores/README.md` | A row for this artifact. |

Files checked and left unchanged:

- `tests/test_version.py` passes for `0.3.0` as it is: the package version comes from
  `pyproject.toml`, and `release_tag()` of `0.3.0` is `v0.3.0`.
- `.taskrail/installed.json` already records `"version": "v0.3.0"`: T084's `taskrail upgrade` ran
  under `0.3.0.dev0`, whose `release_tag()` is `v0.3.0`. It stays right for `0.3.0`, and this
  repository pins `local:.` anyway.
- `src/taskrail/cli.py` line 1531 (`--tag` help, `e.g. v0.2.0`) and `tests/test_install.py`
  (`self upgrade --tag v0.2.0 --dry-run`) use `v0.2.0` as an example of an existing tag, which it
  stays. `tests/test_merge_driver.py` uses `## 0.2.0` as a fixture heading.
- `DESIGN.md` line 1730 ("v0.2.0 cannot switch it off") describes the release before §13 and stays
  true. `README.md` *History* names 0.1.0 and 0.2.0 as history.
- `TODO.md` E01's *Done when* names `v0.2.0`, which is tagged and was installed through the wrapper
  in T078: the condition is met and stays met.
- The skills and `src/taskrail/integrations/` name no version.

## After the merge

1. **Tag.** Only when the human explicitly approves it at that moment, the orchestrator or the
   human runs `git fetch origin`, finds the squash commit of this pull request on `origin/main`,
   then runs `git tag -a v0.3.0 <squash commit> -m "taskrail 0.3.0"` and
   `git push origin v0.3.0`. The tag goes on that commit, not on whatever `main` is by then.
2. **Verify and bump in a follow-up chore, T086**, as T078 did after T077. It is created on this branch
   with `taskrail new` (no `--workspace`), in E01, depending on T085:
   `Bump main to 0.4.0.dev0 after the v0.3.0 tag`, described as "Once v0.3.0 is pushed on T085's
   squash commit, record the tag and a clean install from wadsworthai/taskrail@v0.3.0, then set
   0.4.0.dev0 and lock; stop at scope if the tag does not exist." Its scope stage stops if
   `git ls-remote --tags origin v0.3.0` prints nothing, because the autopilot can offer it as soon
   as T085 is merged, before the tag exists. Its artifact records the tagged commit and the install
   checks T078 made, in a scratch environment with a fresh uv cache and a restricted `PATH`, and
   never with `uv tool install`, which would replace the human's CLI:
   - `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.3.0" taskrail --version`
     prints `taskrail 0.3.0`.
   - A scratch virtual environment with that tag installed runs `taskrail init --integration claude`
     in a new git repository. The resulting pin is `v0.3.0`, and the wrapper runs `validate`
     through the installed CLI.
   - With no `taskrail` on `PATH`, the wrapper falls back to `uvx` for `v0.3.0`.
   - `taskrail self upgrade --dry-run` resolves `v0.3.0` as the latest tag.
   - After the bump, a `0.4.0.dev0` build first on `PATH` is rejected by the `v0.3.0` pin.

   Its change set is `pyproject.toml` set to `0.4.0.dev0` and `uv.lock`. `## Unreleased` already
   exists (decision 2).
3. **What "done" means for T085.** T085's row is marked `✅` on this branch before the merge. It
   means the release commit is prepared, verified locally and reviewed: version, lock, changelog
   and the version references. Tagging stays the human's decision after the merge, and the
   follow-up chore carries the verification against the published tag and the bump.

## Decisions needed

1. **Change set and split.** Recommended: the change set above and the split under *After the
   merge*, both as in T077 and T078. Alternative: add decision 4's files to the follow-up instead
   (see decision 4).
2. **`## 0.3.0` heading, lead paragraph and an empty `## Unreleased` above it.** Recommended, as
   in T077 (no URL, no date):

   > Adds the current-branch workflow (DESIGN.md §13) for a repository worked by a single
   > maintainer: `[git] task_branch = "current"` works a task on the checked-out branch,
   > `commit = "on-done"` commits a task's changes only when it is done, a stage with
   > `gate = "decisions"` stops only for a decision, and `review` closes a current-branch task with
   > a report instead of publishing it. The skills follow each setting. Every setting is off by
   > default, so a repository that sets none of them works as it did in 0.2.0.

   Alternatives: a one-sentence lead without the list; or no lead paragraph.
3. **Corrections so the section reads as one release.** The bullets were written task by task:
   - T083's bullet says `taskrail review <ID>` "no longer exits 2" under `task_branch = "current"`.
     That compares against T080's unreleased state: `task_branch` does not exist in 0.2.0.
     Proposed: "Under `[git] task_branch = "current"`, `taskrail review <ID>` fetches, rebases and
     pushes nothing: it keeps its `--json` keys ..." with the rest of the bullet verbatim.
   - T080's bullet says "`new` no longer warns on the mainline". The setting is new, so a reader
     may take it as a change for every repository. Proposed: "`new` does not warn on the mainline".
   - The `## Unreleased` bullets are separated by blank lines, and every bullet of `## 0.2.0` and
     `## 0.1.0` is not. Proposed: remove the four blank lines between bullets, so the section is
     formatted like the earlier releases. Text is unchanged.

   Recommended: all three. Alternatives: only the two wording corrections; or none. The order of
   the bullets is not changed (T084, T083, T082, T080, T081); regrouping them, for example with
   T080 first, is not recommended, as in T077.
4. **Install and pin examples naming `v0.2.0`.** `README.md` line 17 (`uv tool install ... @v0.2.0`),
   `DESIGN.md` line 112 (`version = "v0.2.0"`, the pin example) and `DESIGN.md` line 1179 (the
   install example). Recommended: name `v0.3.0` in this pull request, so the tree tagged `v0.3.0`
   tells a reader to install `v0.3.0`; T076 did the same for `v0.2.0` before that tag existed.
   Between the merge and the tag, `main` then names a tag that does not exist yet. Alternatives:
   (a) change them in the follow-up chore, once the tag is verified, which leaves the tagged
   `README.md` naming `v0.2.0` for good; (b) leave them.
5. **T085's row.** Its description says "a follow-up chore records the install from the tag and
   bumps main to 0.4.0.dev0". Recommended, as in T077: name the follow-up's ID once it exists,
   `taskrail edit T085 --description "Set the version to 0.3.0, lock, and turn Unreleased into 0.3.0 in CHANGELOG.md with the current-branch workflow (E07); the tag follows the merge with the human's approval, and T0xx records the install from it and bumps main to 0.4.0.dev0."`.
   Alternative: leave the description as it is.
6. **One verification check beyond T077.** Recommended: in the scratch repository initialised from
   the built wheel, also exercise the release's headline feature: set `worktree = "never"` and
   `task_branch = "current"`, then run `new`, `claim`, `done` and `review --json` on a scratch task,
   and check that `review` reports `published: false` and `--publish` exits 5. Alternative: only
   T077's checks.
7. **Pull request title.** Recommended: `chore(release): release v0.3.0 (T085)`, made with
   `--type chore --scope release`, as T077 and T078. It is a release commit, not a feature.

## Decisions at the scope gate

Recorded in `docs/autopilot/decisions/T085-release-v0-3-0.md`. Every decision was taken as
recommended:

1. The change set and the split are as proposed.
2. `## 0.3.0` gets the proposed lead paragraph, with an empty `## Unreleased` above it.
3. Corrections (a), (b) and (c) are applied, and no bullet is reordered.
4. `README.md` line 17 and `DESIGN.md` lines 112 and 1179 name `v0.3.0`.
5. T085's description names the follow-up, T086.
6. The current-branch check on the built wheel is included.
7. The pull request title is `chore(release): release v0.3.0 (T085)`, made with
   `--type chore --scope release`.

## Out of scope

- Creating, moving, pushing or deleting any git tag, locally or remotely: the tag is the human's
  decision after the merge. Pre-merge verification uses no tag, not even one in a scratch clone.
- `uv tool install` and `taskrail self upgrade` without `--dry-run`.
- The bump to `0.4.0.dev0` and the install checks against the published tag: the follow-up chore.
- `.taskrail/installed.json`, E01's *Done when*, `cli.py`'s `--tag` help example and the tests that
  name `v0.2.0` (see *Files checked and left unchanged*).
- A GitHub Release page, PyPI, and release automation.
- Rewording or reordering changelog bullets beyond decision 3.

## Verification

Before merging, entirely local, with no tag and no `uv tool install`. Scratch paths are under
`/tmp/claude-7932/`, and the human's installed `taskrail` is kept off `PATH` in wrapper checks.

1. `taskrail checks T085 --stage implement`, which runs `test` (`uv run pytest -q`). The stage's
   `lint` check is not configured in this repository.
2. `uv run taskrail --version` and `.taskrail/bin/taskrail --version` (local pin) print
   `taskrail 0.3.0`.
3. `uv lock` reports `Updated taskrail v0.3.0.dev0 -> v0.3.0`, `uv lock --check` passes, and
   `git diff uv.lock` is that one line.
4. `uv build --out-dir <scratch>` produces `taskrail-0.3.0-py3-none-any.whl` (`dist/` is not
   ignored, so the build goes to a scratch directory).
5. A scratch virtual environment installs the built wheel, and `taskrail --version` prints
   `taskrail 0.3.0`. In a new git repository, `taskrail init --integration claude` pins
   `version = "v0.3.0"`. With that environment's `bin` first on a restricted `PATH`, the wrapper
   runs `--version` and `validate` through it, because the versions match.
6. Decision 6's check: the current-branch workflow on the built wheel.
7. `grep` for `v0.2.0` and `0.3.0` over `README.md`, `DESIGN.md`, `CHANGELOG.md`, `src/` and
   `tests/` shows only the references listed above.
8. `taskrail validate` on this branch.

After the tag, in the follow-up chore: the checks listed under *After the merge*.

### Results before merging

No tag was created, and nothing ran `uv tool install`. Scratch files are under `/tmp/claude-7932/`.
Wrapper checks ran with `PATH=/tmp/claude-7932/T085-venv/bin:/usr/bin:/bin`, so the human's
installed `taskrail` was never used.

1. `taskrail checks T085 --stage implement` ran `test` (`uv run pytest -q`), with the result
   `1183 passed in 162.78s (0:02:42)`. `lint` is `not configured`, and the overall result was
   `passed`.
2. `uv run taskrail --version` printed `taskrail 0.3.0`, and so did `.taskrail/bin/taskrail --version`,
   through the `local:.` pin.
3. `uv lock` printed `Resolved 7 packages in 138ms` and `Updated taskrail v0.3.0.dev0 -> v0.3.0`.
   `uv lock --check` printed `Resolved 7 packages in 0.84ms`. `git diff uv.lock` changes only the
   taskrail `version` line.
4. `uv build --out-dir /tmp/claude-7932/T085-build` built `taskrail-0.3.0.tar.gz` and
   `taskrail-0.3.0-py3-none-any.whl`.
5. `uv venv /tmp/claude-7932/T085-venv` used CPython 3.12.13, and `uv pip install` of the wheel
   printed `+ taskrail==0.3.0 (from file:///tmp/claude-7932/T085-build/taskrail-0.3.0-py3-none-any.whl)`.
   Its `taskrail --version` printed `taskrail 0.3.0`. In a new git repository
   `/tmp/claude-7932/T085-scratch`, `taskrail --root <scratch> init --integration claude` wrote
   `version = "v0.3.0"` as the config's first line. `sh -x <scratch>/.taskrail/bin/taskrail --version`
   traced `have=0.3.0`, `'[' v0.3.0 = v0.3.0 ']'` and `exec taskrail --version`, then printed
   `taskrail 0.3.0`. The wrapper then ran `--root <scratch> validate`, which printed
   `history: not checked (no commits)` and `0 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
6. In the same scratch repository, `[git]` was set to `worktree = "never"` and
   `task_branch = "current"`, and the setup was committed on `main`. Through the wrapper, on the
   installed 0.3.0 wheel:
   - `epic add` created E01, and `new --epic E01 --kind chore --title "Scratch task"` created T001
     with `"warning": null` on the mainline.
   - `show T001 --json` reported `state` `pending`, `task_branch` `current`, `branch` `main`,
     `branch_source` `current`, `base` and `worktree` `null`, and
     `close` `{"commit": "stages", "review": "report"}`.
   - `claim T001` printed `claimed T001 as abigail@archlinux` with no warning, and `done T001 --json`
     reported `"status": "done"` and `"commit": "stages"`.
   - After a commit `chore(backlog): close scratch task (T001)`, `review T001 --json` exited 0 with
     `fetched` `false`, `rebase.enabled` `false` (`[git].task_branch is "current": review does not
     rebase`), `push` `{"enabled": false, "pushed": false}`, `pull_request.title`
     `chore: scratch task (T001)` with `url` `null`, `published` `false`, one entry in `commits`
     (that commit, matched by `suffix`) and `upstream` `null`.
   - `review T001 --publish --json` exited 5 with
     `taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves`.
   - `validate` printed `1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
7. `grep -rn "v0\.2\.0\|0\.3\.0" README.md DESIGN.md src tests` lists `README.md:17`,
   `DESIGN.md:3`, `:112` and `:1179` at `v0.3.0`, and `v0.2.0` only at `DESIGN.md:1730`,
   `tests/test_install.py:280` and `:283`, and `src/taskrail/cli.py:1531`, as listed above. In
   `CHANGELOG.md`, `0.3.0` appears only as the `## 0.3.0` heading.
8. `taskrail validate` on this branch printed `75 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`,
   and `git diff --check` reported nothing.

The install from the published tag, the wrapper's `uvx` fallback and `self upgrade --dry-run` wait
for the tag. T086 covers them.
