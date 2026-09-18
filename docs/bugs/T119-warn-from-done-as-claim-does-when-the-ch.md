# T119 — Warn from done, as claim does, when the checked-out branch is not the task's

Kind: bug · Epic: E05 · Status: fixed

## Symptom

`taskrail done <ID>` run against a checkout that is not on the task's branch ticks *that*
checkout's backlog row, releases the claim, prints `<ID> done` and exits 0. The task's own branch
— the one that will carry the pull request — keeps its `⬜`. Nothing is printed on stderr, and
`--json` carries no field a caller could read: the result is `id`, `status`, `commit`, `files`.

`claim` has a warning for the same mistake (`cli.py:299`, printed at `cli.py:278`) and `done`
never consults it, although the task's branch is already recorded in the git common directory by
that very claim.

Expected: `done` says, as `claim` does, that the checkout it just wrote to is not on the task's
branch.

## Reproduction

A scratch repository with one task and one lane worktree, the CLI run from this branch's source
(`uv run --project <T119 worktree> taskrail`), no wrapper involved — the defect does not need one.

```bash
git -C $SB/primary init -q -b main            # TODO.md with one pending task, T001
git -C $SB/primary worktree add -q $SB/lane -b T001-base-task main

cd $SB/lane    && uv run --project $W taskrail claim T001     # correct use: inside the lane
cd $SB/primary && uv run --project $W taskrail done T001      # one later command, wrong checkout
```

```
=== 1. claim T001 from inside the lane (correct use) ===
claimed T001 as abigail@archlinux
exit=0

=== 2. done T001 with the cwd in the primary checkout (on main) ===
T001 done
exit=0

=== 3. where the tick landed ===
primary: | ✅ | T001 | bug     |
lane:    | ⬜ | T001 | bug     |

=== 4. git status ===
primary:
 M TODO.md
lane:

=== 5. the claim ===
no claims
```

This is T115 §E3 reproduced independently: the `✅` lands on `main`, uncommitted, in the wrong
checkout; the task's branch keeps its `⬜`; the claim is gone; the exit code is 0.

## Evidence

**The task's branch is known at the moment `done` writes.** The claim made in the lane froze the
template name into a branch record, and both the claim and the record live in the *common* git
directory, so every worktree of the clone sees them:

```
$ ls $SB/primary/.git/taskrail/claims/ $SB/primary/.git/taskrail/branches/
claims/:   T001.json
branches/: T001.json
$ cat $SB/primary/.git/taskrail/branches/T001.json
{
  "id": "T001",
  "branch": "T001-base-task",
  "recorded": "2026-09-18T22:02:52+00:00"
}
```

**And `done` ignores it, in every channel.** Run from the primary checkout, on `main`, with that
record in place:

```
$ cd $SB/primary && uv run --project $W taskrail done T001 --json
{
  "id": "T001",
  "status": "done",
  "commit": "stages",
  "files": [
    "TODO.md"
  ]
}
exit=0
```

**The contrast: `claim` in the same situation.** Same repository, same wrong checkout:

```
$ cd $SB/primary && uv run --project $W taskrail claim T001
taskrail: warning: T001 was claimed on branch main, but its branch is T001-base-task; work on that branch, or run `taskrail branch T001 <NAME>` to name the branch the task is worked on
claimed T001 as abigail@archlinux
exit=0
```

**`discard` has the identical hole** (probed, §Affected areas): claimed in its lane, discarded
from the primary checkout, `❌` in the wrong checkout, `⬜` on the branch, no warning, exit 0:

```
=== B. discard T002 from the wrong checkout (claimed in its lane first) ===
T002 discarded
exit=0
primary: | ❌ | T002 | bug     |
lane2:   | ⬜ | T002 | bug     |
```

**`reopen` does not** (probed): its shape is different, see *Ruled out*.

## Root cause

`done` and `discard` share `_change_status` (`src/taskrail/cli.py:783`). It loads the project from
the resolved root, checks the claim, and writes the status cell:

```python
    edits = writer.Edits(config)
    writer.set_status(edits, task, status)
```

Nothing between the claim check and the write compares the checked-out branch with the task's.
`cmd_claim` does exactly that comparison, one function away, in `_freeze_branch`
(`cli.py:298-313`), which calls `branches.resolve(task, project)` and warns when the branch it is
on is not the task's. `_change_status` never calls `branches.resolve`.

The guard that *is* applied — the claim — cannot catch the mistake, and this is the mechanism that
makes the bug silent rather than loud: claims live in the git **common** directory
(`claims.py:61`, `gitutil.common_dir`), which every worktree of a clone shares, while backlog rows
live in each **worktree**. So the claim taken in the lane is found, and satisfied, from the primary
checkout; the row that gets written is the primary's. The one piece of state that would distinguish
the two checkouts, `HEAD`, is the one `done` never reads.

## Ruled out

- **The wrapper's root resolution (T115 §E1, T118).** Not the cause: the reproduction above uses no
  wrapper at all — `uv run --project <worktree> taskrail` with a plain cwd — and reproduces in full.
  T118 makes the wrapper pass its own root, which removes one *route* into the wrong checkout and
  leaves this one open: when the wrapper path and the cwd agree and are both the wrong checkout
  (T115 §E7), no root-resolution rule can tell it from correct use. This fix must not assume T118.
- **A stale, missing or foreign claim.** The claim was live, owned by the same owner, found by
  `done` (it was released, `claims` prints `no claims` afterwards) and never reported as a problem.
  `done`'s claim requirement is working as designed; it simply does not discriminate by checkout.
- **`writer.set_status` writing the wrong file.** It wrote `TODO.md` of the root it was given, which
  is what `--json` reports in `files`. The file choice is correct for the root; the root is what is
  wrong, and nothing checks it.
- **A missing branch record.** The record existed and named `T001-base-task` (see *Evidence*).
  `branches.resolve` would have returned it; no caller in `_change_status` asks.
- **`reopen` having the same hole.** Probed, and it does not have this one. Run from the wrong
  checkout on a task done only on its branch, it exits 5 (`T003 is already pending`) — it cannot
  even see the status it would revert. On a task done in *both* checkouts (branch merged) it writes
  `⬜` in the checkout it was given — but that is the documented case: a task is reopened on the
  mainline, after the merge, and T034 exists to handle exactly that. Telling a reopener to "work on
  that branch" would name the finished branch of the work being reopened, which is wrong advice.
  `reopen` is out of scope here and needs no follow-up.

## Affected areas

- `src/taskrail/cli.py`, `_change_status` — the fix.
- `discard` shares that function and the defect (probed above). Whether the fix covers it or a
  follow-up task does is the decision below.
- `DESIGN.md` §7, the `done` bullet of *Writing* — one sentence, if the warning is documented there.
- `CHANGELOG.md` — a command that printed one line now prints two.
- Out of scope: the wrapper and `DESIGN.md` §9 (T118), `reopen` (ruled out above).

## Proposed fix

In `_change_status`, after the claim checks and before the write, resolve the task's branch and
compare it with the checked-out one, printing to stderr and returning the text in `--json` the way
`claim` does, keeping exit 0:

```python
    warning = _branch_mismatch(task, project, status)   # None when it matches, or outside git
    if warning:
        print(f"taskrail: warning: {warning}", file=sys.stderr)
```

with `_branch_mismatch` skipping the check when `branches.resolve` reports `current`
(`[git].task_branch = "current"`: the checked-out branch *is* the task's) and when the repository
is not a git checkout.

Wording, retrospective where `claim`'s is prospective — the row is already written when it prints:

> `T001 was marked done in <root> on branch main, but its branch is T001-base-task; the row on that branch is unchanged — undo this change and run the command there, or run `taskrail branch T001 <NAME>` to name the branch the task is worked on`

Decisions carried to the gate: warn or refuse; the exact wording; whether the check sits in the
shared `_change_status` (covering `discard` at no cost) or is guarded to `done` with a follow-up
task for `discard`; the `DESIGN.md` sentence; the `CHANGELOG.md` bullet.

The regression test goes in `tests/test_task_branch.py`, beside the `claim` warning tests, using
the existing `lanes` fixture: claim in the lane, `done` against `lanes.root`, and assert the
warning on stderr and in `--json`. It must be observed failing first.

## Decisions taken at the diagnose gate

1. **Warn, exit 0** — not refuse. The human settled it at T115's `decide` gate in those words: no
   new disagreement warning, and `done` warns *as `claim` does*. The case for refusing (`--force`
   is already `done`'s escape hatch; exit 5 is what the skills stop on) is recorded in
   `docs/autopilot/decisions/T119-warn-from-done-as-claim-does-when-the-ch.md` for whoever revisits
   it. Against it today: it changes a command every skill, the autopilot and every consuming
   repository calls, and `--force` is blunt — it waives the claim and dependency guards too, so an
   override of the branch check alone is not expressible.
2. **Retrospective wording, two messages, no shared builder, and the checkout named.** Second use;
   `claim`'s sentence is prospective and this one is not, so unifying them would force one to say
   something slightly wrong. Naming the checkout is the point of a retrospective warning: it tells
   the reader where the damage is.
3. **The check sits in the shared `_change_status`, so `discard` gets it too.** `discard` is not a
   second site, it is the same function; scoping to `done` would mean an extra condition written to
   leave a reproduced, identical defect in place, plus a follow-up task to delete that condition.
   The widening is smaller than the narrowing. The task's title names `done` alone, so the pull
   request says so.
4. **`CHANGELOG.md`: yes**, one bullet covering both commands.
5. **`DESIGN.md` §7: yes**, the sentence goes on the *Writing* bullet where `done` and `discard`
   live, since `claim`'s equivalent warning is documented at §6.1. §9 is T118's and is untouched.

## Fix

`src/taskrail/cli.py`. A new `_closed_elsewhere` beside the status commands, and two lines in
`_change_status`:

```python
def _closed_elsewhere(task, project: Project, status: Status) -> str | None:
    """Why the checkout a status was just written in is not the task's branch, or None (T119)."""
    resolved, source = branches.resolve(task, project)
    if source == branches.CURRENT:  # the checked-out branch is the task's (DESIGN.md §6.4)
        return None
    current = gitutil.current_branch(project.config.root)
    if not current or not resolved or current == resolved:
        return None
    return (
        f"{task.id} was marked {status.label} in {project.config.root} on branch {current}, but its branch is "
        f"{resolved}; the row on that branch is unchanged — undo this change and run the command there, "
        f"or run `taskrail branch {task.id} <NAME>` to name the branch the task is worked on"
    )
```

```python
    warning = _closed_elsewhere(task, project, status)
    ...
    code = _write(edits, args.json, {..., "warning": warning}, text)
    if code == EXIT_OK and warning:  # after the write: the warning says the row has already been written here
        print(f"taskrail: warning: {warning}", file=sys.stderr)
```

The warning is computed before the write, because `writer.set_status` changes the in-memory task,
and printed after it, because it asserts the row *has* been written. It never changes the exit code
and never stops the release of the claim. `not current` keeps it silent where there is no branch to
compare — outside git, and on a detached `HEAD`, which `claim` warns about at claim time.

Also `DESIGN.md` §7 (the `done`/`discard` command row and the *Writing* bullet) and a
`CHANGELOG.md` bullet under *Unreleased*.

## Verification

**The regression test, observed failing first.** `tests/test_task_branch.py`, section `# T119`,
four tests against the unfixed code — the failure is the root cause itself, `done` having no
`warning` in its result because nothing computes one:

```
$ uv run pytest tests/test_task_branch.py -k "done_on_another_branch_warns" -q
    def test_done_on_another_branch_warns(lanes, capsys):
        lane, code, result, err = close_from_the_mainline(lanes, "done", "T001", T001, capsys=capsys)
        assert code == 0
        assert result["status"] == "done"
>       assert "main" in result["warning"] and T001 in result["warning"]
                         ^^^^^^^^^^^^^^^^^
E       KeyError: 'warning'

tests/test_task_branch.py:463: KeyError
1 failed, 39 deselected in 0.20s
```

```
$ uv run pytest tests/test_task_branch.py -k "T119 or warns_about_nothing or on_another_branch_warns" -q
FAILED tests/test_task_branch.py::test_done_on_another_branch_warns - KeyErro...
FAILED tests/test_task_branch.py::test_discard_on_another_branch_warns - KeyE...
FAILED tests/test_task_branch.py::test_done_on_the_task_branch_warns_about_nothing
FAILED tests/test_task_branch.py::test_outside_git_closing_a_task_warns_about_nothing
4 failed, 1 passed, 35 deselected in 1.58s
```

**After the fix:**

```
$ uv run pytest tests/test_task_branch.py -q
40 passed in 5.65s
```

**The stage's checks** (`taskrail checks T119 --stage fix`):

```
1252 passed in 154.90s (0:02:34)
== lint: not configured
passed test
not configured lint
T119 in /thezone/…/.worktrees/T119-…: passed
```

`lint` is a check the `bug` kind's `fix` stage names and this repository does not define; `checks`
reports it as not configured and the stage passes on `test` alone.

**The reproduction, rerun end to end on a fresh scratch repository with the fixed code:**

```
=== 2. done T001 with the cwd in the primary checkout (on main) ===
taskrail: warning: T001 was marked done in $SB/primary on branch main, but its branch is T001-base-task; the row on that branch is unchanged — undo this change and run the command there, or run `taskrail branch T001 <NAME>` to name the branch the task is worked on
T001 done
exit=0
```

**Correct use stays silent**, claim and `done` both inside the lane:

```
$ cd $SB/lane && uv run --project $W taskrail done T001 --json
{
  "id": "T001",
  "status": "done",
  "commit": "stages",
  "warning": null,
  "files": [
    "TODO.md"
  ]
}
exit=0
```

**`discard` is covered by the same line:**

```
$ cd $SB/primary && uv run --project $W taskrail discard T002
taskrail: warning: T002 was marked discarded in $SB/primary on branch main, but its branch is T002-second-task; the row on that branch is unchanged — undo this change and run the command there, or run `taskrail branch T002 <NAME>` to name the branch the task is worked on
T002 discarded
exit=0
```
