# T074 — Refuse merged --cleanup for a worktree that contains other registered worktrees

Kind: bug · Epic: E02 · Status: fixed

Source: found in T073 (see the *Impact* section of
[T073's document](T073-create-a-task-worktree-under-the-main-ch.md)). Before T073, `new --workspace`
and `workspace <ID>` run inside a lane created the new worktree below that lane, in its ignored
`worktree_dir`. T073 stopped that, but worktrees nested by earlier versions, or by hand, remain.

## Symptom

`taskrail autopilot merged <ID> --cleanup` removes a task's worktree even when another registered
worktree lives inside it. When the nested worktree sits under a directory the outer worktree ignores
(such as its `.worktrees/`), the cleanup exits 0 with `worktree_removed: true`, the nested worktree's
directory is deleted with its uncommitted and untracked work, and its entry is left
`prunable gitdir file points to non-existent location`; its branch survives.

Expected: the cleanup refuses, removes nothing, and names the worktrees inside, as it already does
for a worktree with modified or untracked files, a locked one, or one that holds the current
directory or `--root`.

## Reproduction

A throwaway script outside the repository (`repro_t074.py`, run with this branch's source as
`uv run --project <worktree> python repro_t074.py <scratch>/t074-repro`) builds a repository under a
scratch directory: `.taskrail/config.toml` with one backlog, `TODO.md` with one pending task
`T001 Lane`, `.gitignore` with `.worktrees/`, one commit on `main`. It then:

1. adds the lane worktree `repo/.worktrees/T001-lane` (branch `T001-lane`), claims and closes `T001`
   there through `taskrail.cli.main`, commits, and fast-forwards `main` to the lane;
2. adds a worktree nested inside the lane with `git -C <lane> worktree add`, at
   `<lane>/.worktrees/T002-nested` — where `new --workspace` put it before T073 — and writes an
   untracked `WORK.md` in it;
3. prints the lane's and the nested worktree's `git status`, and `git worktree list --porcelain`;
4. runs `taskrail --root repo autopilot merged T001 --cleanup --no-fetch --json` from the main
   checkout;
5. prints `git worktree list --porcelain`, whether `WORK.md` still exists, and the nested branch.

Paths are printed relative to the scratch directory. The script is the one T073 used for its impact
finding, with the lane's `git status --ignored` and the worktree list before the cleanup added.

A second throwaway script (`t074_git_remove.py`, plain `python`, no taskrail) checks what
`git worktree remove` without `--force` does with what lies inside a worktree, in four fresh
repositories (`a` to `d`), each with `.gitignore` holding `.worktrees/` and `*.local` and a linked
worktree `repo/.worktrees/lane` to remove.

## Evidence

### `autopilot merged --cleanup` (taskrail at fd4290b, git 2.55.0)

```text
== the lane, finished and merged
$ git -C repo worktree add -q repo/.worktrees/T001-lane -b T001-lane
$ taskrail --root repo/.worktrees/T001-lane claim T001
exit 0
$ taskrail --root repo/.worktrees/T001-lane done T001
exit 0
$ git -C repo/.worktrees/T001-lane commit -q -am done T001
$ git -C repo merge -q --ff-only T001-lane

== a worktree nested inside the lane, as new --workspace/workspace placed it before the fix, with uncommitted work
$ git -C repo/.worktrees/T001-lane worktree add -q repo/.worktrees/T001-lane/.worktrees/T002-nested -b T002-nested
$ git -C repo/.worktrees/T001-lane status --porcelain --untracked-files=all
(lane: git status --porcelain --untracked-files=all is empty)
$ git -C repo/.worktrees/T001-lane/.worktrees/T002-nested status --porcelain --untracked-files=all
?? WORK.md
$ git -C repo/.worktrees/T001-lane status --porcelain --ignored
!! .worktrees/
$ git -C repo worktree list --porcelain
worktree repo
HEAD de07b3a7b285014362fdeef5ad8cdcfc8626fddf
branch refs/heads/main

worktree repo/.worktrees/T001-lane
HEAD de07b3a7b285014362fdeef5ad8cdcfc8626fddf
branch refs/heads/T001-lane

worktree repo/.worktrees/T001-lane/.worktrees/T002-nested
HEAD de07b3a7b285014362fdeef5ad8cdcfc8626fddf
branch refs/heads/T002-nested


== cleanup of the lane from the main checkout
$ taskrail --root repo autopilot merged T001 --cleanup --no-fetch --json
exit 0
{
  "id": "T001",
  "branch": "T001-lane",
  "remote": "origin",
  "fetched": false,
  "mainline": {
    "ref": "main",
    "commit": "de07b3a7b285014362fdeef5ad8cdcfc8626fddf",
    "diverged": false
  },
  "head": {
    "ref": "T001-lane",
    "commit": "de07b3a7b285014362fdeef5ad8cdcfc8626fddf",
    "local": "de07b3a7b285014362fdeef5ad8cdcfc8626fddf",
    "remote": null
  },
  "done_at_head": true,
  "closed": "done",
  "merged": true,
  "via": "ancestor",
  "commit": "de07b3a7b285014362fdeef5ad8cdcfc8626fddf",
  "recorded": false,
  "reason": null,
  "checks": {
    "ancestor": true,
    "tree": null,
    "patch-id": null,
    "merge-tree": null
  },
  "confirmations": {
    "row_done_on_mainline": true,
    "row_discarded_on_mainline": false,
    "title_commit": null
  },
  "runs": [],
  "cleanup": {
    "worktree": "repo/.worktrees/T001-lane",
    "worktree_removed": true,
    "branch_deleted": true,
    "claim_released": false,
    "remote_branch": null,
    "refused": null
  },
  "dependents": []
}

== afterwards
$ git -C repo worktree list --porcelain
worktree repo
HEAD de07b3a7b285014362fdeef5ad8cdcfc8626fddf
branch refs/heads/main

worktree repo/.worktrees/T001-lane/.worktrees/T002-nested
HEAD de07b3a7b285014362fdeef5ad8cdcfc8626fddf
branch refs/heads/T002-nested
prunable gitdir file points to non-existent location

repo/.worktrees/T001-lane/.worktrees/T002-nested/WORK.md exists: False
$ git -C repo branch --list T002-nested
branch T002-nested: + T002-nested
```

The worktree list before the cleanup already names the nested worktree: taskrail had the information
it needed to refuse.

### Plain `git worktree remove`, without `--force`

```text
== A: registered worktree nested under the lane's ignored .worktrees/, with untracked work
$ (a/repo/.worktrees/lane) git worktree add -q a/repo/.worktrees/lane/.worktrees/nested -b nested
exit 0
$ (a/repo/.worktrees/lane) git status --porcelain --untracked-files=all
exit 0
$ (a/repo/.worktrees/lane) git status --porcelain --ignored
exit 0
!! .worktrees/
$ (a/repo) git worktree remove a/repo/.worktrees/lane
exit 0
nested/WORK.md exists: False
$ (a/repo) git worktree list --porcelain
exit 0
worktree a/repo
HEAD cfb4f2c1c416115897b825a2019bc65d0bebc50c
branch refs/heads/main

worktree a/repo/.worktrees/lane/.worktrees/nested
HEAD cfb4f2c1c416115897b825a2019bc65d0bebc50c
branch refs/heads/nested
prunable gitdir file points to non-existent location

== B: registered worktree nested under a lane directory that is NOT ignored
$ (b/repo/.worktrees/lane) git worktree add -q b/repo/.worktrees/lane/sub/nested -b nested
exit 0
$ (b/repo/.worktrees/lane) git status --porcelain --untracked-files=all
exit 0
?? sub/nested/
$ (b/repo) git worktree remove b/repo/.worktrees/lane
exit 128
fatal: 'b/repo/.worktrees/lane' contains modified or untracked files, use --force to delete it
nested exists: True

== C: nested worktree locked, under ignored .worktrees/
$ (c/repo/.worktrees/lane) git worktree add -q c/repo/.worktrees/lane/.worktrees/nested -b nested
exit 0
$ (c/repo) git worktree lock c/repo/.worktrees/lane/.worktrees/nested
exit 0
$ (c/repo) git worktree remove c/repo/.worktrees/lane
exit 0
nested exists: False

== D: an ignored plain file and an ignored standalone repository (not registered) in the lane
$ (d/repo/.worktrees/lane) git status --porcelain --untracked-files=all
exit 0
$ (d/repo) git worktree remove d/repo/.worktrees/lane
exit 0
secrets.local exists: False; standalone exists: False
```

In the same scratch repository `b`, `git worktree move` takes the nested worktree out of the lane:

```text
$ git -C b/repo worktree move b/repo/.worktrees/lane/sub/nested b/repo/.worktrees/nested
(no output, exit 0)
```

## Root cause

`_cleanup` in `src/taskrail/autopilot/merged.py` decides whether the worktree is safe to remove with
one content check, then removes it with plain `git worktree remove`:

```python
dirty = gitutil.run(path, "status", "--porcelain", "--untracked-files=all", check=False).stdout.strip()
if dirty:
    return refuse(f"the worktree {path} has uncommitted or untracked changes")
...
gitutil.run(root, "worktree", "remove", str(path))  # _remove_worktree
```

Both the check and git's own refusal in `git worktree remove` look at the outer worktree's status,
which never reports ignored paths: a nested worktree under an ignored directory is invisible to them
(evidence A), and `git worktree remove` deletes ignored content recursively, other worktrees and
repositories included (evidence A, C, D). Nothing in `_cleanup` asks git which *other* worktrees
live below the path, although `_worktree_entries` — which `_cleanup` already calls to find the task's
own entry — lists them (the list before the cleanup names `T002-nested`). The guard that would have
caught it, "no registered worktree inside the one to remove", does not exist.

## Ruled out

- **`--force`.** `_remove_worktree` runs `git worktree remove <path>` without `--force`; evidence A
  shows the unforced command alone deletes the nested worktree, and B shows it still refuses
  untracked, non-ignored content.
- **A nested worktree under a directory that is not ignored.** The outer status reports it as
  `?? sub/nested/` (evidence B), so taskrail's dirty check already refuses (exit 5, "uncommitted or
  untracked changes"), and git would refuse too. Only the ignored case slips through — but the guard
  should not depend on that.
- **A lock on the nested worktree.** It does not protect it: git deletes a locked nested worktree
  with its container (evidence C). taskrail's own `locked` refusal checks only the worktree being
  removed.
- **Cleanup started from inside the nested worktree.** `_inside(path, Path.cwd())` already refuses a
  current directory anywhere under the worktree to remove, the nested one included.
- **Other commands that remove worktrees.** `grep -rn '"remove"\|worktree remove\|rmtree' src` finds
  only `_remove_worktree` in `merged.py` and `_close_workspace` in `cli.py`. `_close_workspace` runs
  `git worktree remove --force` on a workspace that `new --workspace` or `workspace` created moments
  earlier in the same command, at a path `_workspace_target` refused if it already existed, to undo
  it when a later step of that command fails (the epic is missing on the base, or writing the row
  fails); nothing else can be registered inside it. `autopilot close`
  removes no worktree.
- **Worktree listing.** `_worktree_entries` parses every registered worktree, the nested one
  included, with resolved paths; it needs no change, and no helper in `gitutil.py` is needed.

## Affected areas

- `src/taskrail/autopilot/merged.py` — `_cleanup` (the missing guard). `_worktree_entries` and
  `_inside` are reused unchanged.
- `tests/test_autopilot_merged.py` — a regression test beside `test_cleanup_refusals_change_nothing`.
- `DESIGN.md` — the `autopilot merged` row of the command table lists the cleanup's exit-5 refusals;
  it gains this one.
- `CHANGELOG.md` — an Unreleased entry.
- Not affected: `gitutil.py` (no change, so no overlap with T075), `cli.py` (`_close_workspace`, see
  *Ruled out*), the skills (`taskrail-autopilot` already says exit 5 names what stopped the cleanup).

## Proposed fix

In `_cleanup`, read `_worktree_entries(root)` once, and after the `locked` refusal and before the
dirty check, refuse when any other registered worktree's path is inside the one to remove:

```python
contained = [str(e["path"]) for e in entries if e["path"] != path and e["path"].is_relative_to(path) and e["path"].exists()]
if contained:
    return refuse(
        f"the worktree {path} contains other worktrees: {', '.join(contained)}; "
        "move them out with git worktree move, or remove them, first"
    )
```

- **What counts as "contains":** any registered worktree, other than the one being removed, whose
  resolved path is below it — ignored directory or not, locked or not. The check comes before the
  dirty check so a nested worktree under a directory that is not ignored gets this precise reason
  rather than "uncommitted or untracked changes".
- **Entries whose directory is gone** (git lists them as `prunable`) do not count: removing the
  outer worktree cannot lose anything of theirs, and refusing would only demand a
  `git worktree prune` first.
- **Exit code and effect:** exit 5, like the other cleanup refusals; `cleanup.refused` carries the
  message, stderr repeats it, and nothing is removed — no worktree, branch or claim.
- **Ignored files that are not worktrees still do not block.** T031 decided that ignored files do not
  refuse, as for `git worktree remove`, and `test_cleanup_refusals_change_nothing` asserts it: a lane
  almost always holds ignored `.venv/`, `__pycache__/` or build output (this worktree has `.venv/`
  and two `__pycache__/` directories after one test run), so refusing on them would make cleanup
  refuse nearly every time. A standalone repository placed by hand in an ignored directory (evidence D)
  is deleted as before; taskrail never creates one, and it is not a registered worktree.

The regression test builds a merged, closed lane, adds a worktree under the lane's ignored directory
with an untracked file, runs `autopilot merged --cleanup`, and asserts exit 5, a refusal naming the
nested path, and that the lane, its branch, the nested worktree and its file all remain; then it
moves the nested worktree out and asserts the cleanup succeeds.

## Decision at the diagnose gate

The diagnosis was approved as proposed (see the
[decision record](../autopilot/decisions/T074-refuse-merged-cleanup-for-a-worktree-tha.md)): "contains"
means any other registered worktree whose resolved path is inside the one being removed and whose
directory still exists, ignored or not, locked or not; the refusal is exit 5 with the message only, in
`cleanup.refused` and on stderr, with no new JSON field; ignored content that is not a worktree does
not block, and no follow-up is opened for it.

## Fix

### Regression test, observed failing first

`test_cleanup_refuses_a_worktree_that_contains_other_worktrees` in `tests/test_autopilot_merged.py`
builds a lane for `T001`, finishes it and squash-merges it on the host, ignores `.worktrees/` through
the common `info/exclude`, and adds inside the lane:

- `.worktrees/T003-nested`, a worktree with an untracked `WORK.md`, locked;
- `.worktrees/gone`, a worktree whose directory is then deleted, so it stays registered but has
  nothing to lose.

It asserts the lane's `git status --porcelain --untracked-files=all` is empty, then runs
`autopilot merged T001 --cleanup --owner lane --json` and expects exit 5, a `cleanup.refused` that
starts with `the worktree <lane> contains other worktrees: `, names `T003-nested` and not `gone`, is
repeated on stderr, and leaves `WORK.md`, the lane and its local branch in place. It then adds
`sub/T004-nested`, a worktree in a directory that is not ignored, and expects the same refusal naming
both — this reason, not "uncommitted or untracked changes". Finally it unlocks and moves both nested
worktrees out with `git worktree move` and expects the cleanup to exit 0, remove the lane and its
branch, and leave the moved `WORK.md` intact.

Run against the unfixed code (fd4290b plus the test):

```text
$ uv run --project <worktree> pytest <worktree>/tests/test_autopilot_merged.py -q -k contains_other_worktrees
F                                                                        [100%]
=================================== FAILURES ===================================
________ test_cleanup_refuses_a_worktree_that_contains_other_worktrees _________
...
>       refused_naming(nested)
...
    def refused_naming(*inside):
        code, out, err = run(pilot.root, "autopilot", "merged", "T001", "--cleanup", "--owner", "lane", "--json", capsys=capsys)
>       assert code == 5, err
E       AssertionError: 
E       assert 0 == 5
=========================== short test summary info ============================
FAILED .worktrees/T074-refuse-merged-cleanup-for-a-worktree-tha/tests/test_autopilot_merged.py::test_cleanup_refuses_a_worktree_that_contains_other_worktrees
1 failed, 38 deselected in 0.64s
```

It fails at the first cleanup, with only the ignored nested worktree present: exit 0 and an empty
stderr, so the cleanup went on and removed the lane — the root cause. The test imports this
worktree's source (`uv run --project <worktree> python -c "import taskrail; print(taskrail.__file__)"`
prints `<worktree>/src/taskrail/__init__.py`).

### Change

`_cleanup` in `src/taskrail/autopilot/merged.py` reads `_worktree_entries(root)` once and, after the
`locked` refusal and before the dirty check, refuses when another entry lies inside the worktree to
remove and its directory exists:

```python
entries = _worktree_entries(root) if local else []
entry = next((e for e in entries if e["branch"] == branch), None)
...
# git worktree remove deletes ignored content, and a worktree nested in an ignored directory is invisible to status (T074).
contained = [str(e["path"]) for e in entries if e is not entry and _inside(path, e["path"]) and e["path"].exists()]
if contained:
    return refuse(
        f"the worktree {path} contains other worktrees: {', '.join(contained)}; move them out with git worktree move, or remove them, first"
    )
```

`refuse` exits 5 and `cmd_merged` prints the reason on stderr, as for the other refusals. Nothing
else in the cleanup changed; ignored files alone still do not refuse.

Documentation: the `autopilot merged` row of `DESIGN.md`'s command table lists the new refusal and
that ignored files alone do not refuse; `CHANGELOG.md` has an Unreleased entry.

## Verification

The regression test after the fix:

```text
$ uv run --project <worktree> pytest <worktree>/tests/test_autopilot_merged.py -q -k contains_other_worktrees
.                                                                        [100%]
1 passed, 38 deselected in 1.39s
```

The reproduction script (`repro_t074.py`) after the fix, cleanup and afterwards sections:

```text
== cleanup of the lane from the main checkout
$ taskrail --root repo autopilot merged T001 --cleanup --no-fetch --json
exit 5
stderr: taskrail: cleanup refused: the worktree repo/.worktrees/T001-lane contains other worktrees: repo/.worktrees/T001-lane/.worktrees/T002-nested; move them out with git worktree move, or remove them, first
{
  ...
  "merged": true,
  "via": "ancestor",
  ...
  "cleanup": {
    "worktree": "repo/.worktrees/T001-lane",
    "worktree_removed": false,
    "branch_deleted": false,
    "claim_released": false,
    "remote_branch": null,
    "refused": "the worktree repo/.worktrees/T001-lane contains other worktrees: repo/.worktrees/T001-lane/.worktrees/T002-nested; move them out with git worktree move, or remove them, first"
  },
  "dependents": []
}

== afterwards
$ git -C repo worktree list --porcelain
worktree repo
HEAD c103f8c6cc28e3f9d648b9521898e9a1e3dcdc95
branch refs/heads/main

worktree repo/.worktrees/T001-lane
HEAD c103f8c6cc28e3f9d648b9521898e9a1e3dcdc95
branch refs/heads/T001-lane

worktree repo/.worktrees/T001-lane/.worktrees/T002-nested
HEAD c103f8c6cc28e3f9d648b9521898e9a1e3dcdc95
branch refs/heads/T002-nested

repo/.worktrees/T001-lane/.worktrees/T002-nested/WORK.md exists: True
$ git -C repo branch --list T002-nested
branch T002-nested: + T002-nested
```

The fix stage's checks:

```text
$ taskrail --root <worktree> checks T074 --stage fix
== test: uv run pytest -q
...
1037 passed in 150.69s (0:02:30)
== lint: not configured
passed test
not configured lint
T074 in <worktree>: passed
```

`lint` is listed for the fix stage but not defined in the `checks` map.
