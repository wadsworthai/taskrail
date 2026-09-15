# T072 — Report a task's worktree path in one form whichever checkout runs the command

Kind: bug · Epic: E02 · Status: diagnosed

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
