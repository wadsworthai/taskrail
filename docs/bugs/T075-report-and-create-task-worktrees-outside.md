# T075 — Report and create task worktrees outside the bare directory of a bare repository

Kind: bug · Epic: E02 · Status: fixed

Source: found in T073 (see the *Impact* section of
[T073's document](T073-create-a-task-worktree-under-the-main-ch.md)). T072 made `show`, `list`,
`next` and `autopilot next` report a task's `worktree` relative to the repository's main checkout,
the first entry of `git worktree list --porcelain`; T073 made `new --workspace` and `workspace <ID>`
create the worktree at `<main checkout>/<worktree_dir>/<branch>`. Neither is released yet (both are
under *Unreleased* in `CHANGELOG.md`).

## Symptom

In a bare repository with worktrees — a clone made with `git clone --bare`, whose working copies are
all linked worktrees — the first entry of `git worktree list --porcelain` is the bare directory
itself, marked `bare`. taskrail takes that entry as the main checkout, so with
`worktree = "required"`:

- `new --workspace` and `workspace <ID>` create the task's worktree **inside the bare directory**, at
  `<bare dir>/<worktree_dir>/<branch>` (for example `repo.git/.worktrees/T002-placed`, or
  `project/.bare/.worktrees/T002-placed`), next to git's own `worktrees/`, `objects/` and `refs/`;
- `show`, `list`, `next` and `autopilot next` read `worktree` against the bare directory, so an
  existing worktree next to it is `../main` and one not created yet is `.worktrees/<branch>` under it;
- the `taskrail` skill's workspace step and the autopilot lane brief resolve the path against "the
  first `worktree` line of `git worktree list --porcelain`", which is the bare directory too: the
  skill runs `git -C <bare dir> worktree add …`, which puts the worktree there as well and fails
  outright when git is hardened with `safe.bareRepository=explicit`.

Expected: task worktrees are reported against, and created under, a directory outside the bare
directory, the same from every checkout of the clone; which directory is the decision at this gate
(see *Proposed fix*).

## Reproduction

A throwaway script outside the repository (`repro_t075.py`, run with this branch's source as
`uv run --project <worktree> python repro_t075.py <scratch>/t075`). For each layout it builds a
source repository with `.taskrail/config.toml` (one backlog, the default `worktree = "required"` and
`worktree_dir = ".worktrees"`), `TODO.md` with one pending task `T001 First`, `.gitignore` with
`.worktrees/` and one commit on `main`, then:

- **control** — `git clone` to `control/repo`, an ordinary clone;
- **A** — `git clone --bare` to `sibling/repo.git`, and the worktree `sibling/main` added from it;
- **B** — `git clone --bare` to `dotbare/project/.bare`, a file `dotbare/project/.git` containing
  `gitdir: ./.bare`, and the worktree `dotbare/project/main` added from `dotbare/project`;
- **C** — `git clone --bare` to `inside/repo.git`, and the worktree `inside/repo.git/main`.

In each it calls `taskrail.cli.main(["--root", <checkout>, …])` from the layout's working checkout:
`show T001 --json`; `new --epic E01 --kind bug --title Placed --workspace --json`; `show` from inside
the new workspace. It then runs the `taskrail` skill's manual workspace step for `T001`
(`git -C <first worktree line> worktree add --no-track .worktrees/T001-first -b T001-first <base.onto>`),
`show T001` again and the lane brief's join (`<first worktree line>/<worktree>`), and prints the
`worktree` and `bare` lines of `git worktree list --porcelain`. Finally it adds the detached worktree
`sibling/aaa` to layout A and lists again. Paths are printed relative to the scratch directory.

## Evidence

```text
######## control: ordinary clone control/repo
$ git -C control/repo worktree list --porcelain   (worktree/bare lines)
  worktree control/repo
$ taskrail --root control/repo show T001 --json
exit 0
T001 worktree (not created): .worktrees/T001-first   base.onto: origin/main
$ taskrail --root control/repo new --epic E01 --kind bug --title Placed --workspace --json
exit 0
workspace: control/repo/.worktrees/T002-placed
$ taskrail --root control/repo/.worktrees/T002-placed show T002 --json
exit 0
T002 worktree, from inside it: .worktrees/T002-placed
$ taskrail --root control/repo show T001 --json
exit 0
-- the taskrail skill's manual workspace step for T001 (git -C <first worktree line> worktree add ...)
$ git -C control/repo worktree add --no-track .worktrees/T001-first -b T001-first origin/main
exit 0
HEAD is now at 62764d7 init
Preparing worktree (new branch 'T001-first')
$ taskrail --root control/repo show T001 --json
exit 0
T001 worktree after the manual step: .worktrees/T001-first
lane brief <WORKTREE> = <first worktree line>/<worktree>: control/repo/.worktrees/T001-first  exists: True
$ git -C control/repo worktree list --porcelain   (worktree/bare lines)
  worktree control/repo
  worktree control/repo/.worktrees/T001-first
  worktree control/repo/.worktrees/T002-placed

######## A: bare clone sibling/repo.git, worktree sibling/main
$ git -C sibling/main worktree list --porcelain   (worktree/bare lines)
  worktree sibling/repo.git
  bare
  worktree sibling/main
$ taskrail --root sibling/main show T001 --json
exit 0
T001 worktree (not created): .worktrees/T001-first   base.onto: main
$ taskrail --root sibling/main new --epic E01 --kind bug --title Placed --workspace --json
exit 0
workspace: sibling/repo.git/.worktrees/T002-placed
$ taskrail --root sibling/repo.git/.worktrees/T002-placed show T002 --json
exit 0
T002 worktree, from inside it: .worktrees/T002-placed
$ taskrail --root sibling/main show T001 --json
exit 0
-- the taskrail skill's manual workspace step for T001 (git -C <first worktree line> worktree add ...)
$ git -C sibling/repo.git worktree add --no-track .worktrees/T001-first -b T001-first main
exit 0
HEAD is now at 62764d7 init
Preparing worktree (new branch 'T001-first')
$ taskrail --root sibling/main show T001 --json
exit 0
T001 worktree after the manual step: .worktrees/T001-first
lane brief <WORKTREE> = <first worktree line>/<worktree>: sibling/repo.git/.worktrees/T001-first  exists: True
$ git -C sibling/main worktree list --porcelain   (worktree/bare lines)
  worktree sibling/repo.git
  bare
  worktree sibling/main
  worktree sibling/repo.git/.worktrees/T001-first
  worktree sibling/repo.git/.worktrees/T002-placed
$ git -C sibling rev-parse --git-dir
exit 128
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

######## B: dotbare/project/.bare with dotbare/project/.git, worktree dotbare/project/main
$ git -C dotbare/project/main worktree list --porcelain   (worktree/bare lines)
  worktree dotbare/project/.bare
  bare
  worktree dotbare/project/main
$ taskrail --root dotbare/project/main show T001 --json
exit 0
T001 worktree (not created): .worktrees/T001-first   base.onto: main
$ taskrail --root dotbare/project/main new --epic E01 --kind bug --title Placed --workspace --json
exit 0
workspace: dotbare/project/.bare/.worktrees/T002-placed
$ taskrail --root dotbare/project/.bare/.worktrees/T002-placed show T002 --json
exit 0
T002 worktree, from inside it: .worktrees/T002-placed
$ taskrail --root dotbare/project/main show T001 --json
exit 0
-- the taskrail skill's manual workspace step for T001 (git -C <first worktree line> worktree add ...)
$ git -C dotbare/project/.bare worktree add --no-track .worktrees/T001-first -b T001-first main
exit 0
HEAD is now at d35ead7 init
Preparing worktree (new branch 'T001-first')
$ taskrail --root dotbare/project/main show T001 --json
exit 0
T001 worktree after the manual step: .worktrees/T001-first
lane brief <WORKTREE> = <first worktree line>/<worktree>: dotbare/project/.bare/.worktrees/T001-first  exists: True
$ git -C dotbare/project/main worktree list --porcelain   (worktree/bare lines)
  worktree dotbare/project/.bare
  bare
  worktree dotbare/project/.bare/.worktrees/T001-first
  worktree dotbare/project/.bare/.worktrees/T002-placed
  worktree dotbare/project/main
$ git -C dotbare/project rev-parse --is-bare-repository
exit 0
true
$ git -C dotbare/project status --short
exit 128
fatal: this operation must be run in a work tree

######## C: bare clone inside/repo.git, worktree inside/repo.git/main
$ git -C inside/repo.git/main worktree list --porcelain   (worktree/bare lines)
  worktree inside/repo.git
  bare
  worktree inside/repo.git/main
$ taskrail --root inside/repo.git/main show T001 --json
exit 0
T001 worktree (not created): .worktrees/T001-first   base.onto: main
$ taskrail --root inside/repo.git/main new --epic E01 --kind bug --title Placed --workspace --json
exit 0
workspace: inside/repo.git/.worktrees/T002-placed
$ taskrail --root inside/repo.git/.worktrees/T002-placed show T002 --json
exit 0
T002 worktree, from inside it: .worktrees/T002-placed
$ taskrail --root inside/repo.git/main show T001 --json
exit 0
-- the taskrail skill's manual workspace step for T001 (git -C <first worktree line> worktree add ...)
$ git -C inside/repo.git worktree add --no-track .worktrees/T001-first -b T001-first main
exit 0
HEAD is now at d35ead7 init
Preparing worktree (new branch 'T001-first')
$ taskrail --root inside/repo.git/main show T001 --json
exit 0
T001 worktree after the manual step: .worktrees/T001-first
lane brief <WORKTREE> = <first worktree line>/<worktree>: inside/repo.git/.worktrees/T001-first  exists: True
$ git -C inside/repo.git/main worktree list --porcelain   (worktree/bare lines)
  worktree inside/repo.git
  bare
  worktree inside/repo.git/.worktrees/T001-first
  worktree inside/repo.git/.worktrees/T002-placed
  worktree inside/repo.git/main

######## ordering of linked worktrees (A)
$ git -C sibling/main worktree list --porcelain   (worktree/bare lines)
  worktree sibling/repo.git
  bare
  worktree sibling/aaa
  worktree sibling/main
  worktree sibling/repo.git/.worktrees/T001-first
  worktree sibling/repo.git/.worktrees/T002-placed
```

In every bare layout the CLI, the skill's manual step and the lane brief agree with each other, and
all three put the task's worktree inside the bare directory. In the control they put it under the
clone's working tree.

The skill's `git -C <first worktree line>` with git hardened against implicit bare repositories, in
layout A (`<scratch>` is the scratch directory):

```text
$ git -c safe.bareRepository=explicit -C <scratch>/t075/sibling/repo.git worktree list
fatal: cannot use bare repository '<scratch>/t075/sibling/repo.git' (safe.bareRepository is 'explicit')
exit 128

$ git -c safe.bareRepository=explicit -C <scratch>/t075/sibling/repo.git/.worktrees/T002-placed worktree list
<scratch>/t075/sibling/repo.git                        (bare)
<scratch>/t075/sibling/aaa                             62764d7 (detached HEAD)
<scratch>/t075/sibling/main                            62764d7 [main]
<scratch>/t075/sibling/repo.git/.worktrees/T001-first  62764d7 [T001-first]
<scratch>/t075/sibling/repo.git/.worktrees/T002-placed 62764d7 [T002-placed]
```

Run from a worktree, git finds the repository through the worktree's `.git` file and works; run in
the bare directory, the same setting refuses it.

## Root cause

`src/taskrail/gitutil.py`, `main_worktree`:

```python
def main_worktree(root: Path) -> Path:
    """The clone's main worktree: the first entry `git worktree list` gives, from any of its worktrees."""
    output = run(root, "worktree", "list", "--porcelain").stdout
    first = next((line for line in output.splitlines() if line.startswith("worktree ")), None)
    ...
    return Path(first[len("worktree "):]).resolve()
```

It returns the first `worktree` entry without looking at the attribute lines that follow it. Git
lists the main worktree first; in a bare repository there is no main worktree, and git lists the bare
repository's directory in that slot with a `bare` line instead of `HEAD` and `branch`. The function —
and through it `query.main_checkout`, which caches it — therefore returns the bare directory, and
both consumers join `worktree_dir` to it:

- `query.worktree_path` (`show`, `list`, `next`, `autopilot next`): `os.path.relpath(<worktree>, main_checkout(project))`,
  and `<worktree_dir>/<branch>` for one not created yet, read against the same directory;
- `cli._workspace_target` (`new --workspace`, `workspace`): `(main_checkout(project) / config.worktree_dir / branch).resolve()`,
  the path `_open_workspace` passes to `git worktree add` and the "already exists" refusal checks.

The same assumption is written into prose: the `taskrail` skill's workspace step
(`src/taskrail/skills/taskrail/SKILL.md`: "relative to the repository's main checkout — the first
`worktree` line of `git worktree list --porcelain` … run `git -C <main checkout> worktree add …`")
and the lane brief (`src/taskrail/skills/taskrail-autopilot/references/lane-brief.md`: "the entry's
`worktree` is relative to the repository's main checkout (the first `worktree` line of
`git worktree list --porcelain`), so join the two"), and `DESIGN.md` §7's `show`, `new` and
`workspace` rows and its *A row missing from its base* paragraph.

T072 chose the first entry over the parent of `git rev-parse --git-common-dir` because it is right for
`--separate-git-dir` and submodules; the bare case was not considered. T073's diagnosis observed it
and left it to this task.

## Ruled out

- **Git lists linked worktrees before the bare entry in some cases.** In every layout (A, B, C) the
  bare directory is the first entry, followed by `bare`, whichever worktree runs the listing (A lists
  from `sibling/main`, B from `dotbare/project/main`, C from `inside/repo.git/main`, and the
  `safe.bareRepository` run from `repo.git/.worktrees/T002-placed`).
- **The `.git`-file layout (B) turns the project directory into a checkout.** `dotbare/project` is a
  bare repository to git (`rev-parse --is-bare-repository` prints `true`, `status` fails with "must be
  run in a work tree"), and `git worktree list` names `.bare`, not `project`.
- **Other readers of `git worktree list` misread the bare entry.** `gitutil.worktree_branches` (used
  by `query._checked_out`, `checks`, `prior`, `status`, `branch`) maps branches to paths from
  `branch refs/heads/…` lines, which the bare entry has none of; `gitutil.worktrees` (claims' stale
  check) includes the bare path but only compares it with recorded claim worktrees, which are
  checkout top levels (`gitutil.toplevel`), never a bare directory; `autopilot/merged.py`'s
  `_worktree_entries` marks the first entry `main` but only acts on an entry whose branch matches, and
  the bare entry has no branch. None of them uses the bare entry as a place.
- **`cli._workspace_target` builds its own wrong path.** It uses `query.main_checkout` exactly as
  `show` does (T073); the path is wrong only because that helper is.
- **The fallback to the running checkout.** `query.main_checkout` falls back to `config.root` only when
  git fails; in these layouts git succeeds.
- **The installer's `.gitignore` entry for `worktree_dir`.** `install._ensure_gitignore` writes it in
  the checkout being installed; it does not decide where worktrees go.
- **Released users already having worktrees inside a bare directory.** Released versions (before T072
  and T073) created the worktree under the running checkout and reported it relative to it; the
  placement inside the bare directory exists only in unreleased code on `main`.

## Affected areas

- `src/taskrail/gitutil.py` — `main_worktree` (the root cause).
- `src/taskrail/query.py` — `main_checkout` (docstring; behaviour follows `gitutil.main_worktree`),
  `worktree_path` (docstring).
- `src/taskrail/cli.py` — `_workspace_target` (only its comment names the main checkout; the code
  follows `query.main_checkout`).
- Commands: `show`, `list`, `next`, `autopilot next` (`worktree`); `new --workspace`, `workspace`
  (where the worktree is created, their `workspace` result and the "already exists" refusal).
- Skills: the `taskrail` skill's workspace step and the autopilot lane brief's `<WORKTREE>` note, both
  of which define the base directory as "the first `worktree` line", and the skill's
  `git -C <main checkout> worktree add` command, which in layout A cannot run from the directory
  outside the bare repository (`sibling` is not a git repository) and under
  `safe.bareRepository=explicit` cannot run in the bare directory.
- `DESIGN.md` §7: the `show`, `new` and `workspace` rows and the *A row missing from its base*
  paragraph; `CHANGELOG.md`'s T072 and T073 entries describe the main checkout as the first entry of
  `git worktree list`.

Not affected: ordinary clones, `--separate-git-dir` clones and submodules, where the first entry is a
real working tree.

## Proposed fix

### Where task worktrees go in a bare layout

Call the directory that `worktree` is read against and created under the **worktree base**. In an
ordinary clone it stays the main checkout. For a bare layout, the options:

1. **The directory containing the bare repository** (recommended): the parent of the first entry when
   that entry is marked `bare`.
   - A: `sibling/.worktrees/<branch>`, next to `repo.git` and `main`; `main` reads `main`.
   - B: `dotbare/project/.worktrees/<branch>`, next to `.bare` and `main`, in the directory the layout
     treats as the project; `main` reads `main`.
   - C: `inside/.worktrees/<branch>`, beside `repo.git` rather than inside it where `main` was put;
     `main` reads `repo.git/main`.
   - The same from every checkout, and stable: it depends only on where the repository is, not on
     which worktrees exist. Outside every worktree (in A, B and C), so no worktree nests another and
     no `.gitignore` is involved.
   - Cost: a bare repository kept directly in a shared directory (`~/src/repo.git`) puts its task
     worktrees in `~/src/.worktrees/`, a directory not specific to the repository; two such bare
     repositories share it, and a branch name both use is refused there with "already exists" (no
     data is lost). `worktree_dir` can point elsewhere.
   - That directory need not be a git repository (A), so a command that must run inside the clone
     cannot use `git -C <worktree base>`; see *Consumers* below.
2. **The first non-bare worktree in the listing.** Rejected: git sorts linked worktrees by path, so the
   base changes when a worktree is added — the evidence shows `sibling/aaa`, added last, listed before
   `sibling/main` — or removed, including by `autopilot merged --cleanup`; and task worktrees would
   nest inside that worktree, the situation T073 removed and T074 guards against.
3. **The running checkout, in bare layouts only.** Rejected: it brings back T072's per-checkout
   `worktree` values and T073's nesting of worktrees inside a lane, for exactly these layouts.
4. **A configuration value.** `.taskrail/config.toml` is committed and shared by every clone, while
   bare or not is a property of one clone, so a committed key cannot choose it (an absolute
   `worktree_dir` already exists, and applies to every clone). A per-clone setting such as a local git
   config key would work but adds a new contract; it could complement option 1 later if someone needs
   another place, and is not proposed here.
5. **Keep the bare directory** (today's unreleased behaviour). Rejected by the task: worktrees live
   inside git's storage, hidden twice in layout B (`.bare/.worktrees`), copied or deleted with the
   repository directory, and the skill's `git -C <bare dir>` fails under
   `safe.bareRepository=explicit`.

**`worktree_dir` combines as today:** `<worktree base>/<worktree_dir>/<branch>`; an absolute
`worktree_dir` ignores the base, and a relative one with `..` resolves against the base.

### Code

- `src/taskrail/gitutil.py`, `main_worktree` only: after the first `worktree` entry, read its
  attribute lines up to the blank line; if one is `bare`, return the entry's parent directory,
  otherwise the entry, as today. Docstring updated. No other function in `gitutil.py` changes (T074
  may add a worktree-listing helper there; this change stays inside `main_worktree`).
- `src/taskrail/query.py`: docstrings of `main_checkout` and `worktree_path` say what the base is in a
  bare layout. No behaviour change.
- `src/taskrail/cli.py`: `_workspace_target`'s comment, if it needs one. No behaviour change.

### Consumers

The `taskrail` skill's workspace step and the lane brief must stop defining the base as "the first
`worktree` line", and the skill's command must not run `git -C` in a directory that may not be a
repository. Two ways:

- **(a) Prose only** (recommended, the smallest change): the skill says the path is relative to the
  repository's main checkout — the first `worktree` line of `git worktree list --porcelain`, or that
  directory's parent when the entry is followed by a `bare` line — and runs
  `git -C <this checkout> worktree add --no-track <base>/<worktree> -b <branch> <base.onto>` with that
  absolute path from the checkout it is in; the lane brief joins `<WORKTREE>` against the same base.
- **(b) A new JSON field**, for example `worktree_base` (absolute) next to `worktree` in `show`, `list`,
  `next` and `autopilot next`, so skills read the base instead of parsing `git worktree list`. This
  fits `DESIGN.md` §8's "Skills never compute paths" and the CLI's plain contracts, but adds a visible
  field that T072 decided was not needed.

Also: `DESIGN.md` §7's `show`, `new` and `workspace` rows and the *A row missing from its base*
paragraph name the base in a bare layout; one CHANGELOG bullet under Unreleased; `taskrail upgrade`
refreshes the installed skill copies.

### Regression test

A new `tests/test_bare_layout.py`: a bare clone of a source repository with one pending task, a
worktree added next to the bare directory (layout A), and a worktree inside it (layout C) for the
reporting case. It asserts, running from the worktree:

- `show T001 --json` reports `.worktrees/T001-<slug>` and `gitutil.main_worktree` returns the bare
  directory's parent (fails today: the bare directory);
- `new --workspace --json` returns `workspace == <bare dir parent>/.worktrees/<branch>`, not a path
  inside the bare directory, and `show` from inside it reports `.worktrees/<branch>` (fails today:
  `repo.git/.worktrees/<branch>`);
- an existing worktree next to the bare directory reads as its name (`main`), not `../main`
  (fails today);
- `workspace <ID>` refuses with exit 5 when `<bare dir parent>/.worktrees/<branch>` already exists
  (fails today: exit 0, it creates it inside the bare directory);
- the ordinary-clone tests (`test_worktree_path.py`, `test_workspace_placement.py`) keep passing
  unchanged.

## Decision at the diagnose gate

Recorded in [the decision record](../autopilot/decisions/T075-report-and-create-task-worktrees-outside.md):

1. The worktree base of a bare repository is **the directory containing it** (option 1); an ordinary
   clone keeps its main checkout. `worktree_dir` combines as `<base>/<worktree_dir>/<branch>`.
2. Departing from the proposal's consumer option (a): the CLI reports the base as an absolute
   **`worktree_base`** field beside `worktree` in `show`, `list`, `next` and `autopilot next`
   (`null` whenever `worktree` is), because `DESIGN.md` §8 says skills never compute paths. The
   `taskrail` skill creates the worktree with
   `git -C <this checkout> worktree add --no-track <worktree_base>/<worktree> -b <branch> <base.onto>`,
   the lane brief fills `<WORKTREE>` as `worktree_base` joined with `worktree`, and neither reads
   `git worktree list` any more.
3. Touch map as proposed, plus `query.task_dict`; `autopilot/merged.py` belongs to T074.

## Fix

- `src/taskrail/gitutil.py`, `main_worktree`: reads the first block of `git worktree list --porcelain`
  and returns the parent of its path when the block has a `bare` line, else the path as before.
- `src/taskrail/query.py`: `task_dict` adds `worktree_base`, `str(main_checkout(project))` when
  `worktree` is not `null`, else `null`; `list`, `next` and `autopilot next` get it through
  `task_dict`. Docstrings of `main_checkout` and `worktree_path` name the base.
- `src/taskrail/cli.py`: `_workspace_target`'s comment only; creation follows `query.main_checkout`.
- `src/taskrail/skills/taskrail/SKILL.md` (workspace step) and
  `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md` (`<WORKTREE>` note) use
  `worktree_base`; the installed copies were refreshed with `taskrail upgrade`
  (`updated .claude/skills/taskrail/SKILL.md`, `updated .claude/skills/taskrail-autopilot/references/lane-brief.md`).
- `DESIGN.md` §7: `show`'s row documents `worktree_base`, `list`'s names it (and `next` and
  `autopilot next` carry the same fields), and the `new` row and the `taskrail workspace` paragraph
  place the worktree under `worktree_base`.
- `CHANGELOG.md`: one bullet under Unreleased.
- `tests/test_bare_layout.py` (new) is the regression test. The bare fixture clones the repository
  with `git clone --bare` to `layout/repo.git` and adds three worktrees, each used as a runner:
  `layout/main` (sibling, on `main`), `layout/T002-repricing` (next to the bare directory) and
  `layout/repo.git/T003-rounding-error` (inside it). The ordinary fixture is a clone with a lane at
  `.worktrees/T002-repricing`. Tests:
  - `gitutil.main_worktree` from each bare runner is `layout`;
  - `show` and `list` report `T002` as `T002-repricing`, `T003` as `repo.git/T003-rounding-error`, and
    `worktree_base` `layout` for every task;
  - `new --workspace` creates `layout/.worktrees/<branch>`, and `show` from inside it gives
    `.worktrees/<branch>` with `worktree_base` joined to it equal to the workspace;
  - `workspace <ID>` exits 5 with "already exists" and creates no branch when
    `layout/.worktrees/<branch>` exists;
  - an ordinary clone reports `worktree_base` as its main checkout in `show`, `list` and `next`, from
    the main checkout and from the lane;
  - with `worktree = "never"`, `worktree` and `worktree_base` are both `null`.

## Verification

The regression test against the unfixed code
(`uv run --project <worktree> pytest <worktree>/tests/test_bare_layout.py -q --tb=line -p no:cacheprovider`;
`<tmp>` abbreviates pytest's temporary directory, and repeated source locations are omitted):

```text
FFFFFFFFFFFFFFF                                                          [100%]
=================================== FAILURES ===================================
E   AssertionError: assert PosixPath('<tmp>/layout0/repo.git') == PosixPath('<tmp>/layout0')
     +  where PosixPath('<tmp>/layout0/repo.git') = <function main_worktree at 0x7efea2a26700>(PosixPath('<tmp>/layout0/main'))
E   AssertionError: assert PosixPath('<tmp>/layout1/repo.git') == PosixPath('<tmp>/layout1')
     +  where PosixPath('<tmp>/layout1/repo.git') = <function main_worktree at 0x7efea2a26700>(PosixPath('<tmp>/layout1/T002-repricing'))
E   AssertionError: assert PosixPath('<tmp>/layout2/repo.git') == PosixPath('<tmp>/layout2')
     +  where PosixPath('<tmp>/layout2/repo.git') = <function main_worktree at 0x7efea2a26700>(PosixPath('<tmp>/layout2/repo.git/T003-rounding-error'))
E   AssertionError: assert {'T002': '../...unding-error'} == {'T002': 'T00...unding-error'}
      Differing items:
      {'T003': 'T003-rounding-error'} != {'T003': 'repo.git/T003-rounding-error'}
      {'T002': '../T002-repricing'} != {'T002': 'T002-repricing'}
  (the same for the other two runners)
E   AssertionError: assert PosixPath('<tmp>/layout6/repo.git/.worktrees/T004-placed') == ((PosixPath('<tmp>/layout6') / '.worktrees') / 'T004-placed')
E   AssertionError: assert PosixPath('<tmp>/layout7/repo.git/.worktrees/T004-placed') == ((PosixPath('<tmp>/layout7') / '.worktrees') / 'T004-placed')
E   AssertionError: assert PosixPath('<tmp>/layout8/repo.git/.worktrees/T004-placed') == ((PosixPath('<tmp>/layout8') / '.worktrees') / 'T004-placed')
E   AssertionError:
    assert 0 == 5
  (three times, one per runner, at test_bare_layout.py:101)
E   KeyError: 'worktree_base'
  (test_bare_layout.py:110, main checkout and lane)
E   KeyError: 'worktree_base'
  (test_bare_layout.py:120)
15 failed in 2.67s
```

Every bare case fails for the root cause: the base is `repo.git`, so `show` reads `../T002-repricing`
and `T003-rounding-error`, `new --workspace` creates `repo.git/.worktrees/T004-placed`, and `workspace`
does not see the taken path next to the bare repository and succeeds (exit 0). The ordinary-clone and
`worktree = "never"` cases fail because `worktree_base` does not exist yet.

After the fix:

```text
$ uv run --project <worktree> pytest <worktree>/tests/test_bare_layout.py -q -p no:cacheprovider
...............                                                          [100%]
15 passed in 2.65s
```

The stage's checks (no existing assertion compared the whole task dictionary; none needed a change):

```text
$ taskrail checks T075 --stage fix
== test: uv run pytest -q
1051 passed in 143.24s (0:02:23)
== lint: not configured
passed test
not configured lint
T075 in <worktree>: passed
```

`lint` is listed for the fix stage but not defined in the `checks` map.

The reproduction again with the fixed source, following the new skill step
(`repro_t075_fixed.py`: the same layouts as `repro_t075.py`; the manual step now runs
`git -C <this checkout> -c safe.bareRepository=explicit worktree add --no-track <worktree_base>/<worktree> -b T001-first <base.onto>`,
and `show T001` is read from the layout's checkout, the new workspace and T001's own worktree):

```text
######## control: ordinary clone control/repo
T001 worktree (not created): .worktrees/T001-first   worktree_base: control/repo   base.onto: origin/main
workspace: control/repo/.worktrees/T002-placed
T002 worktree, from inside it: .worktrees/T002-placed   worktree_base: control/repo
$ git -C control/repo -c safe.bareRepository=explicit worktree add --no-track control/repo/.worktrees/T001-first -b T001-first origin/main
exit 0
T001 worktree: .worktrees/T001-first   lane brief <WORKTREE> = worktree_base/worktree: control/repo/.worktrees/T001-first  exists: True   (from each of the three runners)

######## A: bare clone sibling/repo.git, worktree sibling/main
T001 worktree (not created): .worktrees/T001-first   worktree_base: sibling   base.onto: main
workspace: sibling/.worktrees/T002-placed
T002 worktree, from inside it: .worktrees/T002-placed   worktree_base: sibling
$ git -C sibling/main -c safe.bareRepository=explicit worktree add --no-track sibling/.worktrees/T001-first -b T001-first main
exit 0
T001 worktree: .worktrees/T001-first   lane brief <WORKTREE> = worktree_base/worktree: sibling/.worktrees/T001-first  exists: True   (from each of the three runners)
$ git -C sibling/main worktree list --porcelain   (worktree/bare lines)
  worktree sibling/repo.git
  bare
  worktree sibling/.worktrees/T001-first
  worktree sibling/.worktrees/T002-placed
  worktree sibling/main

######## B: dotbare/project/.bare with dotbare/project/.git, worktree dotbare/project/main
T001 worktree (not created): .worktrees/T001-first   worktree_base: dotbare/project   base.onto: main
workspace: dotbare/project/.worktrees/T002-placed
T002 worktree, from inside it: .worktrees/T002-placed   worktree_base: dotbare/project
$ git -C dotbare/project/main -c safe.bareRepository=explicit worktree add --no-track dotbare/project/.worktrees/T001-first -b T001-first main
exit 0
T001 worktree: .worktrees/T001-first   lane brief <WORKTREE> = worktree_base/worktree: dotbare/project/.worktrees/T001-first  exists: True   (from each of the three runners)

######## C: bare clone inside/repo.git, worktree inside/repo.git/main
T001 worktree (not created): .worktrees/T001-first   worktree_base: inside   base.onto: main
workspace: inside/.worktrees/T002-placed
T002 worktree, from inside it: .worktrees/T002-placed   worktree_base: inside
$ git -C inside/repo.git/main -c safe.bareRepository=explicit worktree add --no-track inside/.worktrees/T001-first -b T001-first main
exit 0
T001 worktree: .worktrees/T001-first   lane brief <WORKTREE> = worktree_base/worktree: inside/.worktrees/T001-first  exists: True   (from each of the three runners)
```

In this clone, `show T075 --json` with the fixed source reports
`"worktree": ".worktrees/T075-report-and-create-task-worktrees-outside"` and
`"worktree_base": "<clone>"`.

## Impact

The fix gate approved the change as it stands and kept `DESIGN.md` §8 unchanged (see the decision
record). Checked for anything outside this fix that the root cause shows wrong; nothing needed a
follow-up task:

- **Other readers of the base.** `grep -rn "main_worktree\|main_checkout" src/` finds only
  `gitutil.main_worktree`, `query.main_checkout`, `query.worktree_path`, `query.task_dict` and
  `cli._workspace_target`, all covered by the fix.
- **Other prose that derives the base from `git worktree list`.** `grep` over `src/taskrail/skills/`,
  `src/taskrail/integrations/` and `README.md` for "main checkout", "worktree list" and `<WORKTREE>`
  finds only the two places changed here; the autopilot skill fills the lane brief from the dispatch
  entry and defers to the brief.
- **`autopilot merged --cleanup` in a bare layout**, including T074's new refusal for a worktree that
  contains other registered worktrees (merged into `origin/main` while this task ran): its
  `_worktree_entries` lists the bare directory as an entry without a branch, so it never matches a task
  branch, and the bare directory is never inside a task worktree, so it never counts as contained.
- **Tests and docstrings that say "main checkout"** (`test_worktree_path.py`,
  `test_workspace_placement.py`, `test_task_branch.py`) describe ordinary clones, where the base is
  still the main checkout.
- **The T072 CHANGELOG bullet** still says the skill creates a worktree with
  `git -C <main checkout> worktree add` and joins the lane brief's worktree to the main checkout. It is
  an unreleased entry that this task's bullet, listed above it in the same *Unreleased* section,
  supersedes; left as the record of T072 rather than rewritten here.
