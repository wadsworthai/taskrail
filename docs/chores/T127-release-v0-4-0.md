# T127 — Release v0.4.0

Kind: chore · Epic: E10 · Status: implemented, awaiting review; the tag follows the merge

## Goal

Release taskrail 0.4.0 from `github.com/wadsworthai/taskrail`. `main` reads `0.4.0.dev0`, `v0.2.0`
and `v0.3.0` are the tags on `origin`, and `## Unreleased` in `CHANGELOG.md` holds twenty bullets
written by different lanes over two days. Consuming repositories pin a version, so none of these
fixes reach them until a tag exists — in particular T116, which fixes a generated workflow that has
failed in every published version.

This follows T085 (the v0.3.0 release) and T086 (the install from the tag and the bump). README's
*Releasing* has three steps: (1) in a pull request, set `version`, run `uv lock` and add the
changelog entry; (2) after the squash merge, tag the merge commit and push the tag; (3) verify a
clean install from the tag, then bump `main` to the next `.dev0`. This branch carries step (1).
Steps (2) and (3) follow the merge, as described under *After the merge*; T128 already exists for
step (3), in E10, depending on T127.

### Semantic versioning

`git log v0.3.0..origin/main --oneline` lists 50 commits. By type:

- `feat` (6): T107 `archive`, T105 autopilot lanes freed while a task waits, T099 `TASKRAIL.md`
  default, T094 unknown config keys, T003 seeded `[autopilot]` block, T091 the core skill reads the
  repository's instructions.
- `fix` (10): T125, T124, T122, T121, T119, T118, T116, T109, T103, and T113 (`fix(tests)`, tests
  only).
- `perf` (1): T126. `ci` (2): T123 (the generated workflow), T108 (this repository's CI).
- `chore` (10): T120 (the generated workflow), T117 (this repository's workflow), T111 (autopilot
  skill), T101 (`next --help`), T114 (archiving this backlog), T086 (the bump), and four that add
  or correct backlog rows.
- `docs` (20) and `test` (1): DESIGN.md, CLAUDE.md, backlog rows and task artifacts, T104's skill
  wording, T106's tests.

No subject carries a `!` breaking marker. Two entries are incompatible for some callers: T109 (a
`next --limit` below 1 now exits 2 where it exited 0) and T118 (a wrapper run without `--root` from
another repository's directory now acts on its own checkout). Pre-1.0, a feature and an
incompatible change both take a minor bump, so the version is `0.4.0` either way, which matches
`pyproject.toml`'s `0.4.0.dev0`. Nothing marks the API stable, so `1.0.0` is not in question.

`git diff v0.3.0 origin/main -- tests` removes twelve `assert` lines, and each belongs to a listed
behaviour change: nine follow the seeded backlog's rename from `TODO.md` (T099), one the
`actions/checkout@v7` pin (T116), and two the escalated lane that now frees its lane (T105, test
`test_a_gate_occupies_a_lane_while_escalated_and_failed_do_not`).

### What changes for an existing repository

Found from the commits, `git diff v0.3.0 origin/main -- src`, the removed test assertions and the
changelog, not only from the orchestrator's list. "At `upgrade`" means it reaches a repository when
it moves its pin to `v0.4.0` and runs `taskrail upgrade`, which rewrites the managed files it has
not edited locally.

| Task | What an existing user sees | When |
|---|---|---|
| T109 | `next --limit 0` or a negative value exits 2 with `argument --limit: expected a whole number of at least 1`; it exited 0. A non-numeric value gets that message instead of `invalid int value`. | at the new pin |
| T118 | The wrapper passes `--root "$root"` to the CLI, so run from another directory it acts on its own checkout. A caller that aimed a wrapper at another repository without `--root` must now pass `--root`. | at `upgrade` (wrapper is managed) |
| T119 | `done` and `discard` print a warning on stderr when the checkout is not on the task's branch, and `--json` gains `warning` (`null` otherwise). Exit code unchanged. | at the new pin |
| T122, T124 | `epic add` allocates above epic IDs held by the archive and by every local branch (remote-tracking with `claim_remote`), and `epic add --id` with such an ID exits 5; in 0.3.0 it read only the working tree's `## Epics` table and accepted it. | at the new pin |
| T094 | `validate` (text and `--json`) warns about a key `.taskrail/config.toml` holds that taskrail does not define. Exit code stays 0. | at the new pin |
| T105 | Autopilot: an `escalated` task keeps its claim and worktree but frees its lane, so `autopilot next` may start another task in its place; new lane state `parked`; `autopilot status` adds `holds_lane` and prints `no lane`; `next --json` adds `parked` and `restart`. The autopilot skill changes with it. | at the new pin; skill at `upgrade` |
| T116, T120, T123 | The workflow `init --github-workflow` writes pins `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0` (the old `setup-uv@v10` never resolved), grants only `contents: read`, and cancels a pull request's superseded runs. | at `upgrade`, for an unedited workflow; an edited one is reported and left alone |
| T107 | With the merge-driver extra, the `.gitattributes` block `upgrade` writes also names the archive document (default `docs/archive.md`), so `upgrade` leaves that one-line diff. | at `upgrade` |
| T091, T104, T111, T105 | The installed skills change: the core skill tells the executor to read the repository's instruction files, and states when `show --fetch` does anything; the autopilot skill budgets the orchestrator's context and parks lanes. | at `upgrade` |
| T103 | The `epic-id` and `task-id` refusals name `epic_prefix` and `prefix`. Codes, exit codes and `--json` shape unchanged. | message text only |

Not a change for an existing repository: T099 and T003 (only what `init` seeds in a new
repository; a config that omits `file` does not load on 0.3.0 or earlier), T107's command itself,
and T121, T122's archive half and T125, which refine `archive` — new in this release, so no 0.3.0
user has an archive. T100 and T101 change documentation and `--help`; T126 only makes
`autopilot status` faster.

## Change set

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.4.0"` (from `0.4.0.dev0`). |
| `uv.lock` | Regenerated with `uv lock`: only the `taskrail` entry's `version` line, to `0.4.0`. |
| `CHANGELOG.md` | `## Unreleased` becomes `## 0.4.0` under a new empty `## Unreleased`, with the lead paragraph of decision 2, the **Behaviour change** markers of decision 2, and the corrections of decision 3. No bullet is reordered. The preamble and `## 0.3.0` and earlier are not touched. |
| `DESIGN.md` | Line 3: `Status: **released as `v0.4.0`.** See CHANGELOG.md.` Line 138, the pin example: `version = "v0.4.0"`. Lines 1322 and 1331, the `uvx` and `uv tool install` examples: `@v0.4.0`. |
| `README.md` | Lines 22 and 35, the *Install* examples (`uvx` bootstrap and `uv tool install`): `@v0.4.0`. |
| `TODO.md` | Through the CLI only: T127's row with `taskrail done` at close. T127's description already names T128, and T128 exists, so no `new` or `edit`. |
| `docs/chores/T127-release-v0-4-0.md` | This artifact. |
| `docs/chores/README.md` | A row for this artifact. |

Files found by `grep -rnI 'v0\.[0-9]\.[0-9]\|0\.4\.0\|0\.3\.0\|dev0'` (outside `docs/`) and left
unchanged:

- `DESIGN.md` line 221 ("because the key was required before v0.4.0") is written for this release
  and becomes true with it. Line 1949 ("v0.2.0 cannot switch it off") describes the release before
  §13 and stays true.
- `README.md` line 265 (*Releasing* step 3, `.dev0`) is the procedure, and line 277 (*History*)
  names 0.1.0 and 0.2.0 as history.
- `CHANGELOG.md` lines 125 (T116: "installed the extra at `v0.1.0`, `v0.2.0` or `v0.3.0`") and 205
  (T099: "will not load on v0.3.0 or earlier") name earlier releases on purpose, and the preamble's
  `vX.Y.Z` is a placeholder.
- `.taskrail/installed.json` already records `"version": "v0.4.0"`: `upgrade` ran under
  `0.4.0.dev0`, whose `release_tag()` is `v0.4.0`. This repository pins `local:.` anyway.
- `src/taskrail/cli.py` line 1623 (`--tag` help, `e.g. v0.2.0`) and `tests/test_install.py` lines
  343 and 346 use `v0.2.0` as an existing tag, which it stays; `tests/conftest.py`,
  `tests/test_config_unknown_keys.py` and `tests/test_backlog_file_default.py` use `v0.1.0` as a
  fixture pin; `tests/test_install.py` line 350 tests `release_tag("0.1.0.dev0")`.
  `tests/test_version.py` reads the version from `pyproject.toml`.
- `TODO.md` rows T127 and T128 name the versions they are about. E10's *Done when* names none.
- The skills and `src/taskrail/integrations/` name no version.

## After the merge

1. **Tag.** Only when the human explicitly approves it at that moment, the orchestrator or the
   human runs `git fetch origin`, finds this pull request's squash commit on `origin/main`, then
   runs `git tag -a v0.4.0 <squash commit> -m "taskrail 0.4.0"` and `git push origin v0.4.0`. The
   tag goes on that commit, not on whatever `main` is by then. This lane creates no tag at any
   stage.
2. **Verify and bump: T128**, already in E10 and depending on T127. It records the tag and a clean
   install from `wadsworthai/taskrail@v0.4.0` the way T086 did for v0.3.0, then sets `0.5.0.dev0`
   and locks. `## Unreleased` already exists (decision 2).
3. **What "done" means for T127.** T127's row is marked `✅` on this branch before the merge: the
   release commit is prepared, verified locally and reviewed. Tagging stays the human's decision
   after the merge.

## Decisions needed

1. **The version: `0.4.0`.** Recommended, from the commits above: six `feat` subjects, no `!`
   marker, and the two incompatible fixes (T109, T118) also take a minor bump before 1.0.
   Alternatives: none that the evidence supports — `0.3.1` would ship six features as a patch, and
   `1.0.0` would declare a stable API nothing has decided.

2. **How the release notes present the behaviour changes.** Recommended: the `## 0.2.0`
   convention, which already exists for exactly this — a lead paragraph that ends "Read the entries
   marked **Behaviour change** before upgrading", and a sentence starting `Behaviour change:` in
   each bullet that has one. No new heading, no bullet moved or duplicated. Proposed lead under
   `## 0.4.0`, no URL, no date:

   > Adds `taskrail archive`, which moves closed tasks and epics out of the backlog into a document
   > of their own, and lets an autopilot task that waits for the human give its lane to another.
   > Fixes the workflow `init --github-workflow` generates, which failed in every earlier release,
   > and makes the wrapper act on the checkout it lives in. New repositories get `TASKRAIL.md` as
   > their backlog; an existing one keeps its file. Fixes to the wrapper, the workflow and the skills
   > reach a repository only when it runs `taskrail upgrade` after moving its pin. Read the entries
   > marked **Behaviour change** before upgrading: `next --limit`, the wrapper, `done` and
   > `discard`, `epic add`, `validate`, the autopilot's lanes and the generated workflow.

   `Behaviour change:` sentences, one per bullet, where the bullet does not already say it in those
   words:
   - T109: the existing bold "**A script passing 0 or a negative `--limit` now fails where it used
     to exit 0**" becomes "Behaviour change: a script passing 0 or a negative `--limit` now fails
     where it used to exit 0".
   - T118: the existing bold "**One caller changes behaviour**:" becomes "Behaviour change:".
   - T119: append "Behaviour change: `done` and `discard` can print to stderr, and `--json` has the
     new `warning` key."
   - T124: append "Behaviour change: `epic add --id` with an ID another branch or the archive holds
     used to succeed; it now exits 5, and `epic add` without `--id` may allocate a higher ID than it
     did."
   - T094: append "Behaviour change: `validate` can print warnings for a config it accepted
     silently; the exit code is still 0."
   - T105: append "Behaviour change: while an escalated task waits, `autopilot next` may start
     another task in its lane."
   - T116, T120, T123: append "Behaviour change: `upgrade` rewrites an unedited generated
     workflow." to each, after its existing sentence on edited workflows. For T123 also: "a pull
     request's older run is cancelled when a newer push queues one."

   Alternatives: (a) a `### Behaviour changes` subsection above the bullets, one line per change
   with its task ID, keeping the bullets as they are — clearer at a glance, but it repeats each
   change and introduces a heading no earlier release has; (b) move the behaviour-changing bullets
   under `### Behaviour changes` and the rest under `### Other changes` — no repetition, but it
   reorders the section, which T085 did not; (c) the lead paragraph only.

3. **Corrections so the section reads as one release.** The bullets were written task by task, and
   several describe states that never shipped, compared with 0.3.0:
   - (a) **T121, T122 and T125 describe bugs in `archive`, which is new in this release.** Their
     leads say "now resolve", "no longer reissues", "no longer files", against states no released
     version had. Proposed rewordings, keeping every fact that holds in 0.4.0 and dropping the
     narrative of the unreleased bug:
     - T125: "**`archive` refuses to file an epic's rows under a different epic's archived
       section.** When the archive already holds a section with a live epic's ID but another name —
       an ID reissued by a hand edit or a merge — `archive` (and `--dry-run`) moves nothing in any
       backlog and exits 5, naming the epic, the heading and the file. Give the live epic an unused
       ID, or, if it was only renamed, rename that heading to match. `validate` still never reads
       the archive (T125)."
     - T122: "**`epic add` never reissues the ID of an archived epic.** `archive` removes a whole
       epic from the `## Epics` table, so `epic add` also counts the epic sections in the
       backlog's archive, and `--id` refuses an archived epic's ID with exit 5, as it refuses a live
       one. `validate` still never reads the archive (T122)." This also removes its last sentence,
       "Epic IDs are still neither scanned across branches nor reserved", which T124 made false.
     - T121: "**`autopilot status` and `autopilot next` resolve a run whose tasks were archived.**
       A member `taskrail archive` has moved out of the backlog is read from the checkout's archive,
       and from the archive at the mainline refs, so it reads `done-merged` or `discarded` with its
       title and kind, with or without a merge record from `autopilot merged`; `done_merged`,
       `complete` and `next --run`'s count stay right. `--json` keeps its shape; `show`, `list`,
       `next` without a run and `validate` do not read the archive." followed by its measurement
       sentences verbatim.
   - (b) **Two bullets have no task ID**: T107's (`taskrail archive` ...) and T123's (the
     `concurrency` group). Append `(T107)` and `(T123)`.
   - (c) **T107's "`ids` counts archived IDs as used"**: there is no `ids` command. Proposed: "task
     ID allocation (`new`, `reserve-id`) counts archived IDs as used".
   - (d) **T099's headline "and taskrail no longer takes `TODO.md`"** reads, to a consumer about to
     upgrade, as if a `file = "TODO.md"` backlog stopped working; the body says the opposite.
     Proposed: "**The backlog file defaults to `TASKRAIL.md`, and `init` no longer seeds
     `TODO.md`.**"
   - (e) **T125's "or by `epic add` before T122"** goes with (a).
   - (f) **"(T120.)" stands as its own paragraph after a code block.** Proposed: move it into the
     sentence before the block, "...has to add the two lines itself (T120):", and likewise T123's
     "its owner adds, at the top level (T123):" with (b).
   - (g) **Layout.** Most bullets are separated by blank lines, three pairs are not (T100/T099,
     T103/T104, T104/T003), and `## 0.3.0` and `## 0.2.0` use none. Proposed: remove the blank
     lines between bullets, keeping the blank lines around the two fenced `yaml` blocks inside the
     T120 and T123 bullets. Text unchanged.
   - (h) **Missing entry: T101** gave `next --limit` a help string (`--limit N`, "show at most N
     eligible tasks (default 5)"). Proposed: one bullet after T109's, "**`next --help` describes
     `--limit N`**, which it listed as a bare `--limit LIMIT` (T101)." T126 (`perf`) is not
     proposed: it changes no output, only the time `autopilot status` takes.

   Recommended: all of (a)–(h). Alternatives: only (b)–(h), the mechanical ones, leaving (a)'s
   bullets as the lanes wrote them; or none. No bullet is reordered.

4. **Install and pin examples.** Recommended, as T085: `README.md` lines 22 and 35 and `DESIGN.md`
   lines 138, 1322 and 1331 name `v0.4.0` in this pull request, so the tree tagged `v0.4.0` tells a
   reader to install `v0.4.0`. Between the merge and the tag, `main` names a tag that does not exist
   yet. Alternatives: change them in T128 once the tag is verified, which leaves the tagged
   `README.md` naming `v0.3.0` for good; or leave them.

5. **One verification check beyond T085's.** Recommended: exercise the path a consumer takes — a
   scratch repository initialised by 0.3.0 (run from the existing `v0.3.0` tag through
   `uvx --from git+file://<this repository>@v0.3.0`, reading the tag, never creating one) with
   `--github-workflow` and `--merge-driver`, then moved to the 0.4.0 wheel and `upgrade`d: check that
   `upgrade` rewrites the wrapper, the workflow (the new pins, `permissions` and `concurrency`), the
   skills and the `.gitattributes` block, leaves `.taskrail/config.toml` and the backlog alone apart
   from the pin, and that `validate` passes; plus, on the built wheel, `next --limit 0` exits 2 and
   the wrapper run from another directory acts on its own checkout. This checks the claims the
   release notes make about `upgrade`. Alternative: only T085's checks.

6. **Pull request title.** Recommended: `chore(release): release v0.4.0 (T127)`, made with
   `--type chore --scope release`, as T077, T085 and T086. It is a release commit, not a feature.

## Out of scope

- Creating, moving, pushing or deleting any git tag, locally or remotely. Pre-merge verification
  reads the existing `v0.3.0` tag and creates none.
- A local-only `v0.1.0` tag exists in this clone (`git tag` lists it, `git ls-remote --tags origin`
  does not, and CHANGELOG says this repository has no `v0.1.0` tag). Not touched, only reported.
- `uv tool install` and `taskrail self upgrade` without `--dry-run`.
- The bump to `0.5.0.dev0` and the install checks against the published tag: T128.
- The files listed as left unchanged above.
- A GitHub Release page, PyPI, and release automation.
- Rewording or reordering changelog bullets beyond decisions 2 and 3.

## Verification

Before merging, entirely local, with no tag created and no `uv tool install`. Scratch paths are
under `/tmp/claude-7932/`, and the human's installed `taskrail` is kept off `PATH` in wrapper
checks.

1. `taskrail checks T127 --stage implement`, which runs `test` (`uv run pytest -q`); `lint` is not
   configured in this repository.
2. `uv run taskrail --version` and `.taskrail/bin/taskrail --version` print `taskrail 0.4.0`.
3. `uv lock` reports `Updated taskrail v0.4.0.dev0 -> v0.4.0`, `uv lock --check` passes, and
   `git diff uv.lock` is that one line.
4. `uv build --out-dir <scratch>` produces `taskrail-0.4.0-py3-none-any.whl`.
5. A scratch virtual environment installs the wheel and prints `taskrail 0.4.0`; in a new git
   repository `taskrail init --integration claude` pins `version = "v0.4.0"` and seeds
   `TASKRAIL.md`; with that environment's `bin` first on a restricted `PATH`, the wrapper runs
   `--version` and `validate` through it.
6. Decision 5's upgrade-path checks.
7. The version `grep` above lists only the references this artifact names, at their new values.
8. `taskrail validate` on this branch, and `git diff --check`.

After the tag, in T128: the install from the published tag, the wrapper's `uvx` fallback and
`self upgrade --dry-run`.

## Decisions at the scope gate

Recorded in `docs/autopilot/decisions/T127-release-v0-4-0.md`. Every decision was taken as
recommended: 0.4.0; the `## 0.2.0` convention (lead paragraph plus a `Behaviour change:` sentence
per affected bullet, no new heading, nothing moved); corrections (a)–(h); `v0.4.0` in the install
and pin examples in this pull request; the upgrade check from 0.3.0, with nothing that creates a
tag and no pin that implies `v0.4.0` exists remotely; the title
`chore(release): release v0.4.0 (T127)`.

One correction of kind (b) was applied beyond the listed ones: T121's bullet also carried no task
ID, found while rewording it under (a), and now ends `(T121)`.

### Results before merging

No tag was created: `git tag` in this clone printed `v0.1.0`, `v0.2.0`, `v0.3.0` before and after
the checks (`diff` of the two listings is empty), and `git ls-remote --tags origin` has no
`v0.4.0`. Nothing ran `uv tool install`. Scratch files are under `/tmp/claude-7932/T127/`. Wrapper
checks ran with `PATH=<scratch venv>/bin:/usr/bin:/bin`, which holds neither the human's
`taskrail` nor `uv`/`uvx`, so the wrapper could only take the scratch environment's CLI and never
fetch a tag.

1. `taskrail checks T127 --stage implement` ran `test` (`uv run pytest -q`): `1273 passed in
   180.79s (0:03:00)`. `lint` is `not configured`, and the overall result was `passed`.
2. `uv run taskrail --version` and `.taskrail/bin/taskrail --version` (the `local:.` pin) printed
   `taskrail 0.4.0`.
3. `uv lock` printed `Resolved 7 packages in 117ms` and `Updated taskrail v0.4.0.dev0 -> v0.4.0`;
   `uv lock --check` printed `Resolved 7 packages in 0.98ms`. `git diff uv.lock` changes only the
   taskrail `version` line.
4. `uv build --out-dir /tmp/claude-7932/T127/build` built `taskrail-0.4.0.tar.gz` and
   `taskrail-0.4.0-py3-none-any.whl`.
5. A scratch venv with the wheel printed `taskrail 0.4.0`. In a new git repository,
   `taskrail --root fresh init --integration claude` wrote `version = "v0.4.0"` as the config's
   first line, `file = "TASKRAIL.md"`, the commented `# [autopilot]` block, and created
   `TASKRAIL.md`. `sh -x fresh/.taskrail/bin/taskrail --version` traced `'[' v0.4.0 = v0.4.0 ']'`
   and `exec taskrail --root /tmp/claude-7932/T127/fresh --version`, then printed
   `taskrail 0.4.0`; `validate` printed `0 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
6. The upgrade path from 0.3.0. A second venv installed
   `taskrail @ git+file://<this repository>@v0.3.0`, which read the existing tag
   (`+ taskrail==0.3.0 (from git+file://...@dbc49d7...)`) and printed `taskrail 0.3.0`.
   - `taskrail --root old init --integration claude --github-workflow --merge-driver` (0.3.0)
     pinned `v0.3.0`, seeded `TODO.md`, and wrote the workflow with `actions/checkout@v7` and
     `astral-sh/setup-uv@v10` and no `permissions` or `concurrency`. An epic E01 and tasks T001 and
     T002 were added and committed.
   - Before upgrading, 0.3.0's own behaviour: its wrapper, run from the scratch parent directory
     without `--root`, exited 2 with `no .taskrail/config.toml found in /tmp/claude-7932/T127 or
     any parent directory` (the T118 defect, reproduced); `next --limit 0` printed
     `no eligible tasks` and exited 0; `epic add --id E02` with E02 committed only on another
     branch printed `E02` and exited 0.
   - `taskrail --root old upgrade` with the 0.4.0 wheel exited 0 and reported `updated` for
     `.taskrail/bin/taskrail`, `.claude/skills/taskrail/SKILL.md`,
     `.claude/skills/taskrail-autopilot/SKILL.md`, `.../references/lane-brief.md`,
     `.github/workflows/taskrail.yml`, `.gitattributes` and
     `.taskrail/config.toml (version pin → v0.4.0)`, `9 file(s) already up to date`.
     `git diff` then showed: the config's only change `version = "v0.3.0"` → `"v0.4.0"` (no
     `[autopilot]` block added); `.gitattributes` gaining `/docs/archive.md merge=taskrail`; the
     workflow gaining `permissions: contents: read` and the `concurrency` group and moving to
     `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`; the wrapper passing
     `--root "$root"` on its three `exec` lines; `.taskrail/installed.json` updated; `TODO.md`
     unchanged.
   - After committing the upgrade, through the upgraded wrapper from the parent directory without
     `--root`: `sh -x` traced `exec taskrail --root /tmp/claude-7932/T127/old validate`, which
     printed `2 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)` — the 0.3.0-seeded config draws
     no unknown-key warning. `next --limit 0` and `next --limit=-1` exited 2 with
     `argument --limit: expected a whole number of at least 1, got \`0\`` (and `` `-1` ``);
     `next --limit 1` exited 0 with T001; `next --help` lists `--limit N  show at most N eligible
     tasks (default 5)`.
   - A typo key `mainlin = "x"` in `[review]` made `validate` print
     `warning: unknown key \`mainlin\` in [review]; taskrail ignores it [config-unknown-key]` and
     `0 error(s), 1 warning(s)`, exit 0.
   - With E02 committed on branch `other`, `epic add --id E02` on `main` printed
     `epic \`E02\` is already used in refs/heads/other:TODO.md; pick another ID` and exited 5, and
     `epic add` without `--id` allocated `E03`.
   - `done T001 --json` on `main`, with T001's branch `T001-scratch-task`, exited 0, printed the
     warning on stderr and returned it as `"warning"` beside `id`, `status`, `commit` and `files`.
   Every scratch change after the upgrade commit was reverted with `git checkout`.
7. The version `grep` lists only the references this artifact names: `README.md:22`, `:35` and
   `DESIGN.md:3`, `:138`, `:1322`, `:1331` at `v0.4.0`, and the unchanged ones at their old values.
   In `CHANGELOG.md`, `0.4.0` appears only as the `## 0.4.0` heading.
8. `git diff --check` reported nothing, and `taskrail validate` on this branch printed
   `9 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.

At the implement gate, the change set was approved as committed, the extra `(T121)` was kept, and
T109's marker was rewrapped so `Behaviour change:` sits on one source line, as every other marker
does: a reader searching for the phrase the lead paragraph names must find all nine. After the
rewrap:

```
$ awk '/^## 0.4.0/,/^## 0.3.0/' CHANGELOG.md | grep -c 'Behaviour change:'
9
```
