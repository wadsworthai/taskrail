# T072 — Report a task's worktree path in one form whichever checkout runs the command

Kind: bug · Epic: E02 · Status: fixed

Source: opened during T071, whose plan gate showed `autopilot next --json` reporting a prepared
task's `worktree` as a relative path from one checkout and an absolute one from another. T071's
test `tests/test_autopilot_named.py::test_a_row_only_on_its_branch_is_found_from_the_main_checkout`
asserts the relative form from the main checkout and names this task.

## Symptom

The `worktree` field that `show`, `list`, `next` and `autopilot next` report for a task (with
`worktree = "required"`) comes in two forms for the same worktree, depending on which checkout the
command runs in:

- relative to the running checkout's root (`.worktrees/<branch>`) when the task's worktree does not
  exist yet, or exists strictly below that root;
- absolute when the running checkout *is* that worktree, or when the worktree lies outside the
  running checkout's root — a sibling lane seen from another lane, or a worktree outside the
  repository.

Expected: one form for every case, so a caller can use the value without knowing where the command
ran.

## Reproduction

1. In this clone, with T072's worktree created under `.worktrees/`, run `show T072 --json` once with
   `--root` the main checkout and once with `--root` the worktree.
2. A throwaway script outside the repository (`repro_t072.py`, run with this branch's source as
   `uv run --project <worktree> python repro_t072.py <scratch>/t072`) builds a repository under a
   scratch directory: `.taskrail/config.toml` with one backlog and the default
   `worktree = "required"`, `worktree_dir = ".worktrees"`; `TODO.md` with pending tasks
   `T001 Wanted`, `T002 Nested`, `T003 Outside`; one commit. It adds two worktrees with
   `git worktree add`: `repo/.worktrees/T002-nested` (branch `T002-nested`) and
   `elsewhere/T003-outside` (branch `T003-outside`, outside the repository), and leaves `T001`'s
   worktree uncreated. It then calls `taskrail.cli.main(["--root", <runner>, "show", <task>,
   "--json"])` for each of the three tasks from each of three runners — the main checkout, the T002
   worktree and the T003 worktree — and prints `worktree`.

## Evidence

In this clone (`<clone>` is the main checkout; `worktree` is the only field that differs between the
two documents):

```text
$ <clone>/.taskrail/bin/taskrail --root <clone> show T072 --json
  "worktree": ".worktrees/T072-report-a-task-s-worktree-path-in-one-for",

$ <clone>/.worktrees/T072-…/.taskrail/bin/taskrail --root <clone>/.worktrees/T072-report-a-task-s-worktree-path-in-one-for show T072 --json
  "worktree": "<clone>/.worktrees/T072-report-a-task-s-worktree-path-in-one-for",
```

The scratch matrix (`<scratch>` abbreviates the scratch directory):

```text
main checkout: <scratch>/t072/repo

--root main checkout
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '.worktrees/T002-nested'
  T003 (outside the root)    worktree = '<scratch>/t072/elsewhere/T003-outside'

--root T002 worktree (under .worktrees)
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '<scratch>/t072/repo/.worktrees/T002-nested'
  T003 (outside the root)    worktree = '<scratch>/t072/elsewhere/T003-outside'

--root T003 worktree (outside)
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '<scratch>/t072/repo/.worktrees/T002-nested'
  T003 (outside the root)    worktree = '<scratch>/t072/elsewhere/T003-outside'
```

The same worktree (`T002-nested`) is relative from the main checkout and absolute from itself and
from a sibling worktree; an uncreated one is relative from every runner, though from a lane that
relative path names a directory below the lane, not below the main checkout.

## Root cause

`src/taskrail/query.py`, `worktree_path`, used by `task_dict` for its `worktree` field:

```python
path = _checked_out(project).get(branch)
if path is None:
    return f"{config.worktree_dir}/{branch}"
root = config.root.resolve()
if path != root and path.is_relative_to(root):
    return str(path.relative_to(root))
return str(path)
```

`config.root` is the checkout the command runs in (`find_root` walks up to the nearest
`.taskrail/config.toml`, and every worktree has its own), not the repository's main checkout. Two
branches make the form depend on it:

- a worktree that has the branch checked out (`git worktree list --porcelain`, always absolute) is
  made relative only when it lies strictly below `config.root`; `path != root` sends the running
  worktree itself to the absolute branch, and `is_relative_to` sends every worktree outside the
  running checkout — including a sibling under the main checkout's `.worktrees/` — there too;
- a worktree not created yet is the unresolved string `<worktree_dir>/<branch>`, relative to
  whichever checkout runs the command.

T019 introduced the function (commit `cc238cb`): before it, `worktree` was always the template
string `<worktree_dir>/<branch>`; T019 added the lookup of the checked-out worktree and kept the old
relative form for worktrees below the root, falling back to absolute where no relative path exists.

So the rule is **where the command runs**, not whether the worktree exists: an existing worktree
below the running root is relative, the running worktree itself is absolute.

## Ruled out

- **The worktree's existence decides the form.** The matrix shows `T002-nested`, which exists,
  relative from the main checkout and absolute from itself and from `T003-outside`. Existence only
  decides between the lookup and the template string.
- **The autopilot changes the field.** `autopilot/dispatch.py::_entry` takes `worktree` unchanged
  from `query.task_dict`, the same function `show`, `list` and `next` use; the difference shows with
  plain `show`.
- **Symlinks or unresolved paths making `is_relative_to` fail.** `gitutil.worktree_branches` and
  `find_root` both resolve their paths, and the scratch directories contain no symlinks; the
  absolute results above are exactly the running-root and outside-the-root cases the condition
  sends there.
- **A prepared workspace (`new --workspace`, T071) behaves differently.** Its worktree is created
  with `(config.root / worktree_dir / branch).resolve()` in `cli._workspace_target` and listed by
  `git worktree list` like any other; `test_autopilot_named.py` line 193 gets the relative form only
  because it runs from the main checkout.

## Affected areas

Every field and command that exposes the path computed by `query.worktree_path`:

- `taskrail show <ID> --json` → `worktree` (documented in `DESIGN.md` §7's command table as "the
  worktree that has the branch checked out, else `<worktree_dir>/<branch>`");
- `taskrail list --json` → each entry's `worktree`;
- `taskrail next --json` → each entry's `worktree`;
- `taskrail autopilot next --json` (preview and `--run`) → each `dispatch` entry's `worktree`.

None of their text forms prints it. No code in `src/` reads the field back.

Callers of the value:

- the `taskrail` skill's workspace step runs `git worktree add --no-track <worktree> -b <branch>
  <base.onto>`, which git resolves against the current directory (or `git -C`'s directory);
- the autopilot skill fills `<WORKTREE>` in `references/lane-brief.md` from the dispatch entry, and
  lanes then use it with `--root <WORKTREE>` and `git -C <WORKTREE>`, which the Claude Code
  integration asks to be absolute;
- tests asserting the relative form: `tests/test_task_branch.py` lines 96 and 103 (not created,
  from the main checkout) and `tests/test_autopilot_named.py` line 193 (prepared, from the main
  checkout). Tests asserting the absolute form for a worktree outside the root:
  `tests/test_task_branch.py` line 126.

Other fields that name a task's worktree are already absolute in every case and are not affected:
`claim.worktree`, `checks --json` → `worktree`, `autopilot status --json` → each task's `worktree`,
`prior_work.prepared.worktree`, `branch --json` → `worktree`, `new --workspace --json` and
`workspace --json` → `workspace`, and `autopilot merged` → each dependent's `worktree`.

Not part of this bug, found on the way: a worktree not created yet is placed under the *running*
checkout's `worktree_dir`, so seen from a lane it is `<lane>/.worktrees/<branch>` — where
`new --workspace` or `workspace` run inside that lane would also create it
(`cli._workspace_target`: `config.root / config.worktree_dir / branch`). Reporting the path in one
form keeps that location and makes it visible; whether a lane should place new worktrees under the
main checkout instead is a separate question.

## Proposed fix

Report the path **absolute** in every case. In `query.worktree_path`, return the checked-out
worktree's path as git lists it, and for a worktree not created yet
`str((config.root / config.worktree_dir / branch).resolve())` — the path `_workspace_target` would
create from that checkout — dropping the relative branch.

Why absolute rather than relative to the repository root:

- a relative path cannot name a worktree outside the root, or the running worktree itself, without
  `..` segments or `.`; relative to the *running* checkout, an existing worktree's value changes
  with the checkout, which is the bug;
- `git worktree add <worktree>` in the skill's workspace step, `--root <worktree>` and
  `git -C <worktree>` all work with an absolute path from any directory; with the relative form
  they only work when the current directory is the checkout the command ran in;
- every other field naming a task's worktree (listed above) is already absolute, so `worktree`
  becomes consistent with them;
- the cost: the JSON carries a machine-specific path, which it already does for claims and
  `checks`, and `list --json` output grows by the root's length per task.

The change is limited to `query.worktree_path`. Also: update `DESIGN.md` §7's `show` row to say the
path is absolute, update the three tests that assert the relative form, and add a CHANGELOG entry
under Unreleased. The skill's workspace step needs no wording change: its command already works with
an absolute path.

For a worktree not created yet this keeps today's location: the path is resolved against the
running checkout, so from a lane it is `<lane>/.worktrees/<branch>`, not the main checkout's. Only
an existing worktree has the same value from every checkout. Resolving an uncreated worktree against
the main checkout instead would give one value everywhere, but would disagree with where
`new --workspace` and `workspace` create it when run inside a lane unless those change too; that
belongs to the separate placement question above (a follow-up at the impact stage).

The regression test, in a repository with a worktree under `.worktrees/` and a task whose worktree
does not exist, run with `show --json` from the main checkout and from inside the existing worktree:

- the existing worktree's `worktree` is the same absolute path from both checkouts (fails today:
  relative from the main checkout, absolute from inside);
- the uncreated one's `worktree` is absolute and equals `<running root>/.worktrees/<branch>` from
  both (fails today: relative).

## Decision at the diagnose gate

The human departed from the proposal above (see
[the decision record](../autopilot/decisions/T072-report-a-task-s-worktree-path-in-one-for.md)):

1. `worktree` is **relative to the repository's main checkout**, computed the same from every
   checkout; a worktree outside it gets `..` segments, and the running checkout's own worktree is
   reported like any other.
2. A worktree not created yet stays `<worktree_dir>/<branch>`, read against the main checkout.
3. The nesting of worktrees that `new --workspace` and `workspace` create from inside a lane becomes
   a follow-up task, opened at the impact stage; it is not changed here.

**Which directory is the main checkout.** The first `worktree` entry of
`git worktree list --porcelain`, rather than the parent of `git rev-parse --git-common-dir`. Git
documents that the main worktree is listed first, and it is right in every layout: the parent of the
common directory is not the main worktree when the repository's git directory lives elsewhere
(`git init --separate-git-dir`, `GIT_DIR`) or for a submodule, whose common directory is
`.git/modules/<name>` inside the superproject. `query.py` already reads the same listing to find the
worktree that has a branch checked out. If git cannot list worktrees, the running checkout's root is
used, as the lookup of checked-out branches already falls back to nothing.

## Fix

- `src/taskrail/gitutil.py`: `main_worktree(root)` returns the first `worktree` entry of
  `git worktree list --porcelain`, resolved.
- `src/taskrail/query.py`: `worktree_path` returns an existing worktree as
  `os.path.relpath(<worktree>, <main worktree>)` in POSIX form (cached per project as
  `main_worktree`), and `<worktree_dir>/<branch>` for one not created yet, unchanged. The only
  exception is a worktree on another drive than the main worktree's (Windows), for which no
  relative path exists: it is reported absolute.
- Tests: `tests/test_worktree_path.py` (new) is the regression test. In
  `tests/test_task_branch.py::test_renaming_inside_the_worktree_renames_the_branch_and_follows_the_claim`,
  `show`'s `worktree` for a lane outside the repository is now checked as a `../` path that
  resolves, from the main checkout, to the lane. The existing relative assertions
  (`test_task_branch.py` lines 96 and 103, `test_autopilot_named.py` line 193) are unchanged.
- Consumers:
  - the `taskrail` skill's workspace step says the path is relative to the main checkout (the first
    `worktree` line of `git worktree list --porcelain`) and runs
    `git -C <main checkout> worktree add --no-track <worktree> -b <branch> <base.onto>`;
  - the lane brief (`references/lane-brief.md`) says the orchestrator fills `<WORKTREE>` as an
    absolute path, the main checkout joined with `worktree`;
  - the installed copies were refreshed with `taskrail upgrade`;
  - `DESIGN.md` §7 describes the form in `show`'s row and says `list` and `next` entries carry the
    same field (`autopilot next` already carries `show --json`'s fields);
  - a CHANGELOG entry under Unreleased.

No consumer needed a new JSON field: the main checkout comes from git.

## Verification

The regression test, run against the unfixed code
(`uv run --project <worktree> pytest <worktree>/tests/test_worktree_path.py -q`; `<tmp>` abbreviates
pytest's temporary directory). It asserts, from the main checkout, a worktree under `.worktrees/`
and one outside the repository, that `show --json` and `list --json` give `T001`
`.worktrees/T001-wanted` (not created), `T002` `.worktrees/T002-nested` and `T003`
`../elsewhere<n>/T003-outside`:

```text
FFFFFF                                                                   [100%]
___ test_show_reports_the_same_worktree_from_every_checkout[main checkout] ___
E         Differing items:
E         {'T003': '<tmp>/elsewhere0/T003-outside'} != {'T003': '../elsewhere0/T003-outside'}
___ test_show_reports_the_same_worktree_from_every_checkout[nested worktree] ___
E         Differing items:
E         {'T002': '<tmp>/test_show_reports_the_same_wor1/.worktrees/T002-nested'} != {'T002': '.worktrees/T002-nested'}
E         {'T003': '<tmp>/elsewhere1/T003-outside'} != {'T003': '../elsewhere1/T003-outside'}
___ test_show_reports_the_same_worktree_from_every_checkout[outside worktree] ___
E         Differing items:
E         {'T002': '<tmp>/test_show_reports_the_same_wor2/.worktrees/T002-nested'} != {'T002': '.worktrees/T002-nested'}
E         {'T003': '<tmp>/elsewhere2/T003-outside'} != {'T003': '../elsewhere2/T003-outside'}
___ test_list_reports_the_same_worktree_from_every_checkout[main checkout] ___
E         Differing items:
E         {'T003': '<tmp>/elsewhere3/T003-outside'} != {'T003': '../elsewhere3/T003-outside'}
___ test_list_reports_the_same_worktree_from_every_checkout[nested worktree] ___
E         Differing items:
E         {'T002': '<tmp>/test_list_reports_the_same_wor1/.worktrees/T002-nested'} != {'T002': '.worktrees/T002-nested'}
E         {'T003': '<tmp>/elsewhere4/T003-outside'} != {'T003': '../elsewhere4/T003-outside'}
___ test_list_reports_the_same_worktree_from_every_checkout[outside worktree] ___
E         Differing items:
E         {'T002': '<tmp>/test_list_reports_the_same_wor2/.worktrees/T002-nested'} != {'T002': '.worktrees/T002-nested'}
E         {'T003': '<tmp>/elsewhere5/T003-outside'} != {'T003': '../elsewhere5/T003-outside'}
6 failed in 1.90s
```

It fails for the root cause: the path is made relative to the running checkout, and only for a
worktree strictly below it.

After the fix, the regression test with the two test files that assert the field:

```text
$ uv run --project <worktree> pytest <worktree>/tests/test_worktree_path.py <worktree>/tests/test_task_branch.py <worktree>/tests/test_autopilot_named.py -q
.......F.........................................................        [100%]
E       At index 1 diff: PosixPath('../lanes0/lane') != PosixPath('<tmp>/lanes0/lane')
FAILED .worktrees/T072-report-a-task-s-worktree-path-in-one-for/tests/test_task_branch.py::test_renaming_inside_the_worktree_renames_the_branch_and_follows_the_claim
1 failed, 64 passed in 16.49s
```

That assertion expected the old absolute form for a lane outside the repository; it was updated as
described in *Fix*. The stage's checks then:

```text
$ taskrail checks T072 --stage fix
== test: uv run pytest -q
1028 passed in 150.55s (0:02:30)
== lint: not configured
passed test
not configured lint
T072 in <worktree>: passed
```

`lint` is listed for the fix stage but not defined in the `checks` map.

The reproduction matrix again, with the fixed source:

```text
--root main checkout
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '.worktrees/T002-nested'
  T003 (outside the root)    worktree = '../elsewhere/T003-outside'

--root T002 worktree (under .worktrees)
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '.worktrees/T002-nested'
  T003 (outside the root)    worktree = '../elsewhere/T003-outside'

--root T003 worktree (outside)
  T001 (not created)         worktree = '.worktrees/T001-wanted'
  T002 (under .worktrees)    worktree = '.worktrees/T002-nested'
  T003 (outside the root)    worktree = '../elsewhere/T003-outside'
```

In this clone, `show T072 --json` with the fixed source gives
`.worktrees/T072-report-a-task-s-worktree-path-in-one-for` from both the main checkout and the task's
worktree.

## Impact

The fix gate approved the change as it stands (see the decision record). One item outside this fix,
decided at the diagnose gate, became a follow-up task:

- **T073 — Create a task worktree under the main checkout when new or workspace runs inside another
  worktree** (bug, E02). `cli._workspace_target` places the worktree at
  `config.root / config.worktree_dir / branch`, `config.root` being the checkout that runs the
  command, so from inside a lane it lands below that lane — not at `<worktree_dir>/<branch>` under the
  main checkout, where `show` now reports a worktree not created yet.

Reproduced with a throwaway script outside the repository (`repro_nesting.py`, run with this branch's
source as `uv run --project <worktree> python repro_nesting.py <scratch>/nesting`). It builds a
repository with one pending task `T001 Lane`, `.worktrees/` ignored and one commit, adds the lane
worktree `repo/.worktrees/T001-lane` with `git worktree add`, and calls `taskrail.cli.main` with
`--root` at the lane; paths are printed relative to the scratch directory:

```text
== new --workspace from inside the lane
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title From lane --workspace --json
exit 0
workspace: repo/.worktrees/T001-lane/.worktrees/T002-from-lane

== workspace <ID> from inside the lane, for a row only the lane has
$ taskrail --root repo/.worktrees/T001-lane new --epic E01 --kind bug --title Moved row --json
exit 0
$ taskrail --root repo/.worktrees/T001-lane workspace T003 --json
exit 0
workspace: repo/.worktrees/T001-lane/.worktrees/T003-moved-row

== show from each new workspace (its row lives there)
$ taskrail --root repo/.worktrees/T001-lane/.worktrees/T002-from-lane show T002 --json
exit 0
T002 worktree: .worktrees/T001-lane/.worktrees/T002-from-lane
$ taskrail --root repo/.worktrees/T001-lane/.worktrees/T003-moved-row show T003 --json
exit 0
T003 worktree: .worktrees/T001-lane/.worktrees/T003-moved-row

== git worktree list --porcelain (worktree lines)
repo
repo/.worktrees/T001-lane
repo/.worktrees/T001-lane/.worktrees/T002-from-lane
repo/.worktrees/T001-lane/.worktrees/T003-moved-row
```

Not changed in T072.
