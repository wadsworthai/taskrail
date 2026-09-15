# T077 — Release v0.2.0 from the canonical repository

Kind: chore · Epic: E01 · Status: scope proposed

## Goal

Publish taskrail 0.2.0 from `github.com/wadsworthai/taskrail`, the canonical repository, which has
no release tag yet (`git ls-remote --tags origin` prints nothing). `main` reads `0.2.0.dev0`, and
`## Unreleased` in `CHANGELOG.md` holds the features and behaviour changes merged since 0.1.0.
Pre-1.0, behaviour changes take a minor bump, so the release is `0.2.0`.

The README's *Releasing* section has three steps: (1) in a pull request, set `version`, run
`uv lock` and add the changelog entry; (2) after the squash merge, tag the merge commit and push
the tag; (3) verify a clean install from the tag, then bump `main` to the next `.dev0`. Only step
(1) can live on a task branch. Steps (2) and (3) follow the merge, and pushing a tag cannot be
undone, so they wait for the human's explicit approval at that point. This task's branch carries
step (1). Steps (2) and (3) are split out as described under *After the merge*.

This branch is rebased onto T076 before it is published. T076 renames the repository URLs and
settles the text that presents 0.1.0 as released from this repository, so this change set leaves
every URL and every 0.1.0 reference alone.

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.2.0"` (from `0.2.0.dev0`). |
| `uv.lock` | Regenerated with `uv lock`: the `taskrail` package entry reads `version = "0.2.0"`. |
| `CHANGELOG.md` | `## Unreleased` becomes `## 0.2.0`, with a new empty `## Unreleased` above it (decision 3), a short lead paragraph under `## 0.2.0` (decision 4), and the corrections in decision 2. No other bullet is reordered or reworded, and the preamble, the "own repository" bullet and `## 0.1.0` are not touched. |
| `TODO.md` | Through the CLI only: a follow-up chore (see *After the merge*) with `taskrail new`, T077's description with `taskrail edit` (decision 5), and T077's row with `taskrail done` at close. |
| `docs/chores/T077-release-v0-2-0-from-the-canonical-reposi.md` | This artifact. |
| `docs/chores/README.md` | A row for this artifact. |

Files checked and left unchanged:

- `tests/test_version.py` passes for `0.2.0` as it is: the package version still comes from
  `pyproject.toml`, and `release_tag()` of `0.2.0` is `v0.2.0`.
- `.taskrail/installed.json` already records `"version": "v0.2.0"`, which is `release_tag()` of
  `0.2.0.dev0`. It stays the same for `0.2.0`, and this repository pins `local:.` anyway.
- `README.md`, `DESIGN.md`, `src/` and `tests/` hold version text only as 0.1.0 examples and
  repository URLs, which belong to T076. One of them bears on the release: `DESIGN.md` line 3,
  `Status: **v1 released as `v0.1.0`.**` (see decision 6).

## After the merge

1. **Tag.** Only when the human explicitly approves it at that moment, the orchestrator or the
   human runs `git fetch origin`, finds the squash commit of this pull request on `origin/main`,
   then runs `git tag -a v0.2.0 <squash commit> -m "taskrail 0.2.0"` and
   `git push origin v0.2.0`. The tag goes on that commit, not on whatever `main` is by then.
2. **Verify and bump in a follow-up chore**, like T016 after T002. It is created on this branch
   and depends on T077:
   `Bump main to 0.3.0.dev0 after the v0.2.0 tag`, described as "Once v0.2.0 is pushed on T077's
   squash commit, record the tag and a clean install from wadsworthai/taskrail@v0.2.0, then set
   0.3.0.dev0 and lock." Its scope stage stops if `git ls-remote --tags origin v0.2.0` prints
   nothing, because the autopilot can offer it as soon as T077 is merged, before the tag exists.
   Its artifact records the tagged commit and these install checks, made in a scratch
   environment and never with `uv tool install`, which would replace the human's CLI:
   - `uvx --from "git+https://github.com/wadsworthai/taskrail.git@v0.2.0" taskrail --version`
     prints `taskrail 0.2.0`.
   - A scratch virtual environment with that tag installed runs `taskrail init --integration claude`
     in a new git repository. The resulting pin is `v0.2.0`, and the wrapper runs `validate`
     through the installed CLI.
   - With no `taskrail` on `PATH`, the wrapper falls back to `uvx` for `v0.2.0` from the canonical
     URL (after T076).
   - `taskrail self upgrade --dry-run` resolves `v0.2.0` as the latest tag.

   Its change set is `pyproject.toml` set to `0.3.0.dev0` and `uv.lock`. `## Unreleased` already
   exists (decision 3).
3. **What "done" means for T077.** T077's row is marked `✅` on this branch before the merge. It
   means the release commit is prepared, verified locally and reviewed: version, lock and
   changelog. Tagging stays the human's decision after the merge, and the follow-up chore carries
   the verification against the published tag and the bump. The backlog then never claims that
   T077 did either.

## Decisions needed

1. **Split.** Recommended: the split above. This branch carries version, lock and changelog. The
   tag waits for the human's approval after the merge, and one follow-up chore records the tag
   and the install from it and bumps `main`.
   Alternatives: (a) two follow-ups, one for tag verification and one for the bump; (b) no
   follow-up, with the orchestrator writing the tag and verification into T077's artifact in a
   separate docs pull request, and the bump opened later.
2. **Superseded text in Unreleased.** The section was written task by task, so some bullets
   describe intermediate states of work that never shipped:
   - T072's bullet says `worktree` is relative to "the repository's main checkout (the first
     entry of `git worktree list`)", and that the skill creates a worktree with
     `git -C <main checkout> worktree add`. T073's says the worktree is created "under the
     repository's main checkout". T075, in the same section, replaced both with `worktree_base`,
     and the skill now runs `git -C <this checkout> worktree add --no-track <worktree_base>/<worktree> …`.
   - Several **Behaviour change** notes compare against earlier *unreleased* autopilot behaviour
     that no 0.1.0 user ever had: T030 (`autopilot lane --group`), T049 (governing escalation
     after `done-branch`), T051 (`overlaps`), T065 (discarded branches in the hand-off queue). T061
     also says "as before" about unreleased behaviour. The README tells users to read the
     changelog before upgrading, so a false behaviour change costs them time.

   Recommended: (a) merge the T072, T073 and T075 bullets into one bullet that describes the
   released behaviour against 0.1.0, worded as below; (b) drop the four intra-release
   "Behaviour change: …" sentences and T061's "as before", keeping the rest of those bullets
   verbatim. Every real behaviour change against 0.1.0 stays: `[review].remote`, T026, T027,
   T035, T038, T039 and T062. All other bullets keep their text and order. Proposed bullet, in
   place of T075's bullet, with the T072 and T073 bullets removed:

   > - **A task's worktree is one path from every checkout, created where it is reported.**
   >   `show`, `list`, `next` and `autopilot next` report `worktree` relative to `worktree_base`, an
   >   absolute directory they also report: the main checkout of an ordinary clone, or the
   >   directory holding a bare repository. `new --workspace` and `workspace <ID>` create the task's
   >   worktree at `<worktree_dir>/<branch>` under it from any checkout, and refuse when that path
   >   exists; the `taskrail` skill and the lane brief join the two instead of reading
   >   `git worktree list`. Before, an existing worktree came out absolute when read from inside it
   >   or from another worktree, one created inside another worktree was nested below it, and a
   >   bare repository's worktrees were read against and created in the bare directory itself
   >   (T072, T073, T075).

   Alternatives: only (a); or only rename the heading and leave every bullet as written; or
   reorganise the whole section into groups such as Added, Changed and Behaviour changes. That
   rewrite is not recommended: it would be hard to review against the task history and would
   collide with T076's edit of the "own repository" bullet during the rebase.
3. **An empty `## Unreleased` above `## 0.2.0`.** Recommended: add it in this pull request. Any
   pull request merged between this merge and the bump then has a place for its bullet other
   than `## 0.2.0`, and CLAUDE.md describes the changelog as "under Unreleased until a release".
   The tagged `CHANGELOG.md` shows an empty section, which is harmless. Alternative, as in T016:
   the bump chore adds it back.
4. **Lead paragraph under `## 0.2.0`.** Recommended: two sentences with no URL or repository
   name, for example: "Adds the autopilot (DESIGN.md §12), `edit`, `import`, `checks`,
   `workspace`, `branch` and a merge driver for backlog tables and changelogs. Read the entries
   marked **Behaviour change** before upgrading." The upgrade path from an earlier install stays
   in T076's "own repository" bullet. `## 0.1.0` has "First release." as its lead, and a
   release date is not added, matching `## 0.1.0`. Alternative: no lead paragraph.
5. **T077's row.** Its description promises the tag, the install verification and the bump,
   which this task hands to the human and the follow-up. Recommended:
   `taskrail edit T077 --description "Set the version to 0.2.0, lock, and turn Unreleased into 0.2.0 in CHANGELOG.md; the tag follows the merge, and the follow-up records the install from it and bumps main."`,
   with the follow-up's ID filled in. The title stays, and the branch name is recorded, so it does
   not move. Alternative: leave the description as it is.
6. **`DESIGN.md` status line** (`v1 released as v0.1.0`). After the release it should name
   `v0.2.0`, but the line is a 0.1.0 reference and so T076's. Question: does T076 change it?
   If T076 leaves it, may this change set add `DESIGN.md` line 3 ->
   `Status: **released as `v0.2.0`.** See CHANGELOG.md.` after the rebase? Recommended: yes,
   after the rebase, and only that line.
7. **Pull request title.** `taskrail review` uses the kind's default type. Recommended:
   `chore(release): release v0.2.0 (T077)`, with `--scope release`. Alternative: `--scope repo`.
   It is a release commit, not a feature, so `feat` is not proposed.

## Out of scope

- Creating, pushing or deleting any git tag, locally or remotely, in this task: the tag is the
  human's decision after the merge. Pre-merge verification therefore uses no tag, not even one in
  a scratch clone.
- Repository URLs, `SOURCE_URL`, the changelog preamble, the "own repository" bullet, the
  `## 0.1.0` section, README *History* and every other 0.1.0 reference: T076.
- The bump to `0.3.0.dev0`: the follow-up chore.
- A GitHub Release page, PyPI, and release automation (as in T002).
- Reordering or rewording changelog bullets beyond decision 2.

## Verification

Before merging, entirely local, with no tag and no `uv tool install`:

- `taskrail checks T077 --stage implement`, which runs `test` (`uv run pytest -q`). The stage's
  `lint` check is not configured in this repository.
- `uv run taskrail --version` prints `taskrail 0.2.0`.
- `.taskrail/bin/taskrail --version` prints `taskrail 0.2.0` (local pin).
- `uv build --out-dir <scratch>` produces `taskrail-0.2.0-py3-none-any.whl` (`dist/` is not
  ignored, so the build goes to a scratch directory).
- `uv.lock` records `version = "0.2.0"` for taskrail, and `uv lock --check` passes.
- A scratch virtual environment under `/tmp/claude-7932/` installs the built wheel.
  `taskrail --version` prints `taskrail 0.2.0`, and in a new git repository
  `taskrail init --integration claude` pins `version = "v0.2.0"`. With that environment's `bin`
  first on `PATH`, the wrapper runs `validate` through it, because the versions match.
- `taskrail validate` on this repository.

After the tag, in the follow-up chore: the checks listed under *After the merge*.
