# T073 — Create a task worktree under the main checkout when new or workspace runs inside another worktree

Kind: bug · Epic: E02 · Status: fixed

Source: found in T072 (see the *Impact* section of
[T072's document](T072-report-a-task-s-worktree-path-in-one-for.md)). T072 made `show`, `list`,
`next` and `autopilot next` report a task's `worktree` relative to the repository's main checkout,
the same from every checkout; a worktree not created yet reads `<worktree_dir>/<branch>` against the
main checkout. The commands that create a worktree were left unchanged.

## Symptom

With `worktree = "required"`, `taskrail new --workspace` and `taskrail workspace <ID>` run inside a
task worktree (a lane) create the new worktree **below that lane**, at
`<lane>/<worktree_dir>/<branch>`, instead of at `<main checkout>/<worktree_dir>/<branch>`.

- Before the worktree exists, `show` reports `.worktrees/<branch>` — under the main checkout.
- After it is created, `show` reports `.worktrees/<lane branch>/.worktrees/<branch>`.
- The refusal for an existing worktree path checks the lane-relative path, so a directory already at
  the main checkout's `<worktree_dir>/<branch>` does not stop it.

Expected: the worktree is created at `<main checkout>/<worktree_dir>/<branch>` whichever checkout
runs the command, which is where `show` says it goes, and the existence check looks there.

## Reproduction

A throwaway script outside the repository (`repro_t073.py`, run with this branch's source as
`uv run --project <worktree> python repro_t073.py <scratch>/t073`) builds a repository under a
scratch directory: `.taskrail/config.toml` with one backlog and the default
`worktree = "required"`, `worktree_dir = ".worktrees"`; `TODO.md` with one pending task `T001 Lane`;
`.gitignore` with `.worktrees/`; one commit on `main`. It adds the lane worktree
`repo/.worktrees/T001-lane` (branch `T001-lane`) with `git worktree add`, then calls
`taskrail.cli.main(["--root", <runner>, …])`:

1. `new --workspace` with `--root` at the main checkout (control);
2. `new --workspace` with `--root` at the lane;
3. `new` (row only in the lane), `show` of that task, then `workspace <ID>`, with `--root` at the lane;
4. `show` from inside each workspace created from the lane;
5. `new` in the lane, a directory created at `repo/.worktrees/<ID>-taken`, then `workspace <ID>` from
   the lane;
6. `git worktree list --porcelain`.

Paths are printed relative to the scratch directory.

## Evidence

```text
== control: new --workspace from the main checkout
$ taskrail --root repo new --epic E01 --kind bug --title From main --workspace --json
exit 0
workspace: repo/.worktrees/T002-from-main

== new --workspace from inside the lane
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title From lane --workspace --json
exit 0
workspace: repo/.worktrees/T001-lane/.worktrees/T003-from-lane

== workspace <ID> from inside the lane, for a row only the lane has
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title Moved row --json
exit 0
$ taskrail --root repo/.worktrees/T001-lane show T004 --json
exit 0
T004 worktree before `workspace`: .worktrees/T004-moved-row
$ taskrail --root repo/.worktrees/T001-lane workspace T004 --json
exit 0
workspace: repo/.worktrees/T001-lane/.worktrees/T004-moved-row

== show from each new workspace (its row lives there, uncommitted)
$ taskrail --root repo/.worktrees/T001-lane/.worktrees/T003-from-lane show T003 --json
exit 0
T003 worktree: .worktrees/T001-lane/.worktrees/T003-from-lane
$ taskrail --root repo/.worktrees/T001-lane/.worktrees/T004-moved-row show T004 --json
exit 0
T004 worktree: .worktrees/T001-lane/.worktrees/T004-moved-row

== existence check: a directory already at <main checkout>/.worktrees/<branch> is not seen from the lane
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title Taken --json
exit 0
created directory repo/.worktrees/T005-taken
$ taskrail --root repo/.worktrees/T001-lane workspace T005 --json
exit 0
workspace: repo/.worktrees/T001-lane/.worktrees/T005-taken

== git worktree list --porcelain (worktree lines)
repo
repo/.worktrees/T001-lane
repo/.worktrees/T001-lane/.worktrees/T003-from-lane
repo/.worktrees/T001-lane/.worktrees/T004-moved-row
repo/.worktrees/T001-lane/.worktrees/T005-taken
repo/.worktrees/T002-from-main
```

`T004` is reported at `.worktrees/T004-moved-row` before `workspace` runs and at
`.worktrees/T001-lane/.worktrees/T004-moved-row` after it.

What the nesting costs. The lane's `.gitignore` ignores `.worktrees/`, so the nested worktrees are
invisible to `git status` in the lane, and removing the lane — which is what
`autopilot merged --cleanup` does once the lane's branch is merged, after checking
`git status --porcelain --untracked-files=all` there — deletes them with their uncommitted work. In
the same scratch repository, where `T003-from-lane` holds its new row uncommitted:

```text
$ git -C <scratch>/t073/repo worktree remove .worktrees/T001-lane
(no output, exit 0)

$ git -C <scratch>/t073/repo worktree list
<scratch>/t073/repo                                                d9a413f [main]
<scratch>/t073/repo/.worktrees/T001-lane/.worktrees/T003-from-lane d9a413f [T003-from-lane] prunable
<scratch>/t073/repo/.worktrees/T001-lane/.worktrees/T004-moved-row d9a413f [T004-moved-row] prunable
<scratch>/t073/repo/.worktrees/T001-lane/.worktrees/T005-taken     d9a413f [T005-taken] prunable
<scratch>/t073/repo/.worktrees/T002-from-main                      d9a413f [T002-from-main]
```

## Root cause

`src/taskrail/cli.py`, `_workspace_target`, which both `new --workspace` (through `_open_workspace`)
and `workspace` (directly, for its up-front refusal, and through `_open_workspace`) use:

```python
path = None
if config.worktree == "required":
    path = (config.root / config.worktree_dir / branch).resolve()
    if path.exists():
        raise _WorkspaceRefused(f"{path} already exists")
return branch, base.onto, path
```

`config.root` is the checkout the command runs in: `find_root` walks up to the nearest
`.taskrail/config.toml`, and every worktree has its own copy. Run inside a lane, the worktree path —
and the existence check on the same line — is built under the lane. `_open_workspace` then runs
`git worktree add … <path>` with that absolute path.

The line dates from T013 (commit `f8a1c01`), when `show` also reported
`<worktree_dir>/<branch>` against whichever checkout ran it, so creation and reporting agreed. T072
moved reporting to the main checkout (`query._main_checkout`, the first entry of
`git worktree list --porcelain`) and left this line on `config.root`, which is where they now
disagree.

## Ruled out

Every other place that names or finds a task's worktree was checked; none builds the path from
`config.root` and `worktree_dir` (`grep -rn "worktree_dir" src/` finds only `config.py`, `install.py`,
`mergedriver.py`, `query.py` and this line in `cli.py`):

- **`query.worktree_path`** (`show`, `list`, `next`, `autopilot next`): an existing worktree comes from
  `git worktree list`; one not created yet is the string `<worktree_dir>/<branch>`, read against the
  main checkout since T072. It is correct; the lane's nested worktree above is reported where it
  really is.
- **`taskrail branch` renames** (`cmd_branch`): renames with `git branch -m`, which leaves the worktree
  where it is, and reports `gitutil.worktree_branches(root).get(name)`, git's own list.
- **`autopilot merged --cleanup`** (`autopilot/merged.py`): finds the branch's worktree in
  `git worktree list --porcelain` and removes that path. It does not build a path; it is affected
  only through the nesting (Evidence above).
- **`taskrail checks`** (`checks.worktree`): the claim's recorded worktree, else
  `gitutil.worktree_branches`.
- **Claims' `worktree`** (`cmd_claim`): `--worktree`, else `gitutil.toplevel(config.root)` — the
  checkout the claim is taken in, which is what it is meant to record.
- **`autopilot status`** (`status._lane_details`): the claim's worktree, else `worktree_branches`.
- **`prior_work.prepared`** (`prior.py`): `worktree_branches`.
- **`_close_workspace`**: removes the path `_open_workspace` returned, from `origin`; it follows
  whatever path was created.
- **`mergedriver.changelog_paths`**: uses `worktree_dir` only to skip that directory when listing
  changelog files; it names no task's worktree.
- **`worktree = "never"`**: `_workspace_target` returns no path and `_open_workspace` switches the
  branch in the running checkout; nothing is nested.
- **The skill's manual workspace step**: since T072 it runs
  `git -C <main checkout> worktree add --no-track <worktree> …` with `show`'s relative path, so a
  workspace created by hand from a lane already lands under the main checkout.

## Affected areas

- `taskrail new --workspace` with `worktree = "required"`: where the worktree is created, the
  `workspace` field of `--json` and the text line `workspace <path> on branch …`.
- `taskrail workspace <ID>` with `worktree = "required"`: the same, plus its refusal for an existing
  worktree path (exit 5), which looks under the running checkout.
- Indirectly, `show`/`list`/`next`/`autopilot next` then report the nested path, and
  `autopilot merged --cleanup` of the outer lane deletes the nested worktrees.
- Documentation: `DESIGN.md` §7's rows for `new` and `workspace`, and the paragraph on
  `taskrail workspace` under *A row missing from its base*, do not say where the worktree goes; the
  `taskrail` skill does not either for these two commands (it reads the path from their result).

## Proposed fix

In `_workspace_target`, build the path under the main checkout:
`(<main checkout> / config.worktree_dir / branch).resolve()`, with the main checkout found the way
`show` finds it — `query._main_checkout(project)` (the first entry of
`git worktree list --porcelain`, falling back to the running checkout's root when git cannot list
worktrees), made public as `query.main_checkout` so `cli.py` does not import a private name. The
existence check uses the same path. Nothing else changes: `_open_workspace` already passes an
absolute path to `git worktree add`, and `_close_workspace` removes what was created.

Consequences:

- **`worktree_dir` as an absolute path**: `Path / "/abs"` is `/abs`, so the worktree goes to
  `/abs/<branch>` from every checkout, as today.
- **`worktree_dir` with `..`** (e.g. `../wt`): now resolved against the main checkout, not against the
  lane — the same place from every checkout, which is what `show` already says.
- **The main checkout differs from the checkout whose `.taskrail/config.toml` is read**: `worktree_dir`
  still comes from the running checkout's configuration (as `show` reads it), joined to the main
  checkout. If a branch changes `worktree_dir`, a lane on it uses its own value, under the main
  checkout. The main checkout need not have taskrail installed or the same branch checked out.
  Whether `.worktrees/` is ignored there depends on the main checkout's `.gitignore`, as for a
  worktree created from the main checkout today.
- **A bare repository with worktrees**: `git worktree list --porcelain` lists the bare directory first
  (checked: `worktree <scratch>/bare/repo.git` followed by `bare`), so worktrees would go to
  `repo.git/.worktrees/<branch>`, next to git's own `repo.git/worktrees/`. `show` already reads its
  paths against that directory since T072. This layout is not handled differently by either today.
- **Worktrees already nested by earlier versions** stay where they are; `show` keeps reporting them
  where they are.

Documentation: say in `DESIGN.md` §7's `new` and `workspace` rows, and in the `taskrail workspace`
paragraph, that the worktree is created at `<worktree_dir>/<branch>` under the repository's main
checkout — the path `show` reports — whichever checkout runs the command; add a CHANGELOG entry under
Unreleased. The `taskrail` skill needs no change: its manual step already uses the main checkout, and
after `new --workspace` or `workspace` it works in the `workspace` path those commands return.

Regression test: in a repository with a lane worktree under `.worktrees/`, run `new --workspace` and
`workspace <ID>` with `--root` at the lane and assert the returned `workspace` is
`<main checkout>/.worktrees/<branch>` and matches `show`'s `worktree` joined to the main checkout
(fails today: `<lane>/.worktrees/<branch>`); and assert `workspace <ID>` from the lane refuses with
exit 5 when `<main checkout>/.worktrees/<branch>` already exists (fails today: exit 0).

## Decision at the diagnose gate

Recorded in [the decision record](../autopilot/decisions/T073-create-a-task-worktree-under-the-main-ch.md):

1. Approved as proposed: the worktree goes to `<main checkout>/<worktree_dir>/<branch>`, the
   existence check looks at that path, and the helper becomes public as `query.main_checkout`.
2. Bare layouts get no special case here; a follow-up task at the impact stage covers reporting and
   placement for a bare repository with worktrees.
3. `autopilot merged --cleanup` removing nested worktrees becomes a follow-up bug at the impact stage,
   reproduced again first.
4. Documentation: `DESIGN.md` §7's `new` and `workspace` rows and the `workspace` paragraph, one
   CHANGELOG bullet, no skill change.

## Fix

- `src/taskrail/query.py`: `_main_checkout` is renamed `main_checkout` (public, with a docstring);
  its one caller, `worktree_path`, is updated. Its behaviour is unchanged.
- `src/taskrail/cli.py`: `_workspace_target` builds the worktree path as
  `(main_checkout(project) / config.worktree_dir / branch).resolve()` instead of
  `(config.root / …)`, so both the path `_open_workspace` passes to `git worktree add` and the
  "already exists" refusal use the main checkout.
- `tests/test_workspace_placement.py` (new) is the regression test. Each test runs from the main
  checkout (control) and from a lane at `.worktrees/T002-lane`:
  - `new --workspace` returns `workspace == <main checkout>/.worktrees/<branch>`, and `show` from
    inside it reports `.worktrees/<branch>`;
  - `workspace <ID>` for a row only that checkout has returns the same path, which equals `show`'s
    `worktree` from before the move joined to the main checkout, and `show` from inside it agrees;
  - `new --workspace --branch T004-taken` and `workspace <ID>` exit 5 with "already exists" when
    `<main checkout>/.worktrees/<branch>` is already a directory, and create no branch.
- `DESIGN.md` §7: the `new` and `workspace` rows and the `taskrail workspace` paragraph say where the
  worktree is created.
- `CHANGELOG.md`: one bullet under Unreleased.

## Verification

The regression test against the unfixed code
(`uv run --project <worktree> pytest <worktree>/tests/test_workspace_placement.py -q`; `<tmp>`
abbreviates pytest's temporary directory):

```text
.F.F.F.F                                                                 [100%]
____ test_new_workspace_creates_the_worktree_under_the_main_checkout[lane] _____
>       assert workspace == expected_path(checkouts, result["branch"])
E       AssertionError: assert PosixPath('<tmp>/test_new_workspace_creates_the1/.worktrees/T002-lane/.worktrees/T004-placed') == PosixPath('<tmp>/test_new_workspace_creates_the1/.worktrees/T004-placed')
______ test_workspace_creates_the_worktree_under_the_main_checkout[lane] _______
>       assert workspace == expected_path(checkouts, result["branch"])
E       AssertionError: assert PosixPath('<tmp>/test_workspace_creates_the_wor1/.worktrees/T002-lane/.worktrees/T004-moved') == PosixPath('<tmp>/test_workspace_creates_the_wor1/.worktrees/T004-moved')
____ test_new_workspace_refuses_a_path_taken_under_the_main_checkout[lane] _____
>       assert code == 5, err
E       assert 0 == 5
______ test_workspace_refuses_a_path_taken_under_the_main_checkout[lane] _______
>       assert code == 5, err
E       assert 0 == 5
4 failed, 4 passed in 2.43s
```

Every `[lane]` case fails for the root cause: the path is built under the lane, where nothing exists,
so the worktree nests there and the taken path under the main checkout is not seen. The
`[main checkout]` controls pass.

After the fix, the regression test with the other test files that create workspaces or report the
path:

```text
$ uv run --project <worktree> pytest <worktree>/tests/test_workspace_placement.py <worktree>/tests/test_workspace.py <worktree>/tests/test_row_on_base.py <worktree>/tests/test_worktree_path.py -q
...........................................................              [100%]
59 passed in 11.10s
```

The stage's checks:

```text
$ taskrail checks T073 --stage fix
== test: uv run pytest -q
1036 passed in 157.23s (0:02:37)
== lint: not configured
passed test
not configured lint
T073 in <worktree>: passed
```

`lint` is listed for the fix stage but not defined in the `checks` map.

The reproduction script again, with the fixed source:

```text
== control: new --workspace from the main checkout
workspace: repo/.worktrees/T002-from-main

== new --workspace from inside the lane
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title From lane --workspace --json
exit 0
workspace: repo/.worktrees/T003-from-lane

== workspace <ID> from inside the lane, for a row only the lane has
T004 worktree before `workspace`: .worktrees/T004-moved-row
$ taskrail --root repo/.worktrees/T001-lane workspace T004 --json
exit 0
workspace: repo/.worktrees/T004-moved-row

== show from each new workspace (its row lives there, uncommitted)
T003 worktree: .worktrees/T003-from-lane
T004 worktree: .worktrees/T004-moved-row

== existence check: a directory already at <main checkout>/.worktrees/<branch> is not seen from the lane
created directory repo/.worktrees/T005-taken
$ taskrail --root repo/.worktrees/T001-lane workspace T005 --json
exit 5
stderr: taskrail: repo/.worktrees/T005-taken already exists

== git worktree list --porcelain (worktree lines)
repo
repo/.worktrees/T001-lane
repo/.worktrees/T002-from-main
repo/.worktrees/T003-from-lane
repo/.worktrees/T004-moved-row
```
