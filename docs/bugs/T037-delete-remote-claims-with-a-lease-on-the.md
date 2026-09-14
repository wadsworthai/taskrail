# T037 — Delete remote claims with a lease on their recorded commit

Kind: bug · Epic: E02 · Status: fixed

## Symptom

With `[git].claim_remote` set, every command that releases a remote claim with `force=True`
fails to delete `refs/taskrail/claims/<ID>` and exits 2:

- `taskrail release <ID> --force` — even by the claim's own owner — prints
  `! [rejected] (delete) -> refs/taskrail/claims/<ID> (stale info)`, exits 2 and keeps both the
  remote ref and the local claim.
- `taskrail done <ID>` and `taskrail discard <ID>` release with `force=True` after writing the
  row: the row is changed and the JSON result is printed, but the command then exits 2 and leaves
  both claims behind. Running `done` again exits 5 (`is done, not pending`).
- `taskrail claim <ID> --takeover` of a stale claim releases the old claim with `force=True`
  first, so the takeover exits 2 and nothing is replaced.

A plain `taskrail release <ID>` by the owner works, also after `taskrail branch` renamed the task
branch and re-pushed the claim.

Expected, as DESIGN.md §6.2 states: "Releasing deletes the ref with a lease on the commit that
was pushed" — whether or not `--force` is given. `--force` only waives the owner check.

First reported by the T036 lane while reproducing its own feature against a bare remote.

## Reproduction

Throwaway repositories under `mktemp -d /tmp/t037-repro.XXXXXX`, deleted afterwards: a bare
`origin.git` and a clone `first` holding the test suite's `BASE_CONFIG` and `BASE_TODO` plus
`[git] claim_remote = "origin"`, committed and pushed to `origin`. The CLI runs from this branch
(base `2312a2a`) as `uv run taskrail --root <repo> …`.

```bash
git init -q --bare -b main origin.git
git init -q -b main first && cd first
# .taskrail/config.toml = BASE_CONFIG + [git] claim_remote = "origin"; TODO.md = BASE_TODO
git add -A && git commit -qm init && git remote add origin ../origin.git && git push -q origin main
taskrail claim T002 --owner alice
taskrail release T002 --owner alice --force
git -C ../origin.git for-each-ref refs/taskrail/claims
```

Each scenario below starts from a fresh pair of repositories.

## Evidence

### `release --force` by the owner

```
$ taskrail claim T002 --owner alice
taskrail: warning: T002 was claimed on branch main, but its branch is T002-repricing; work on that branch, or run `taskrail branch T002 <NAME>` to name the branch the task is worked on
claimed T002 as alice
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
df45ed99643b39e1de3d2a8130d181e809711c9f commit	refs/taskrail/claims/T002
$ cat .git/taskrail/claims/T002.json
{
  "id": "T002",
  "owner": "alice",
  "branch": "main",
  "created": "2026-09-13T22:47:42+00:00",
  "worktree": "/tmp/t037-repro.q6ANXu/first",
  "host": "archlinux",
  "remote": {
    "name": "origin",
    "ref": "refs/taskrail/claims/T002",
    "commit": "df45ed99643b39e1de3d2a8130d181e809711c9f"
  },
  "base": {
    "onto": "origin/main",
    "commit": "ed72cb33311f27536658722ee9bbe60019f3f515",
    "dependency": null
  },
  "run": null
}
$ taskrail release T002 --owner alice --force
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.q6ANXu/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.q6ANXu/origin.git'
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
df45ed99643b39e1de3d2a8130d181e809711c9f commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
```

The recorded `remote.commit` equals the remote ref, so a lease on it would have succeeded.

### Plain `release` (control)

```
claimed T002 as alice
$ taskrail release T002 --owner alice
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
```

### `done`

```
claimed T002 as alice
$ taskrail done T002 --owner alice --json
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.dxAaPv/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.dxAaPv/origin.git'
{
  "id": "T002",
  "status": "done",
  "files": [
    "TODO.md"
  ]
}
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
0f2aaad2aae3e3afd559071f02ca0d398e794eb9 commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
$ grep T002 TODO.md
| ✅ | T002 | feature | 3   | T001       | Repricing      | Recompute   |
| ⬜ | T003 | bug     | 1   | T002       | Rounding error | Off by one  |
$ taskrail done T002 --owner alice   (retry)
taskrail: T002 is done, not pending
exit=5
$ taskrail release T002 --owner alice   (retry without --force)
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
```

(The stderr lines come first because stdout is block-buffered through the pipe; in the code the
JSON result is emitted before the release runs.)

### `discard`

```
claimed T002 as alice
$ taskrail discard T002 --owner alice
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.4bamq6/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.4bamq6/origin.git'
T002 discarded
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
42ee5a7b8087c95c798eb54945febe4c4ca0f35b commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
```

### `claim --takeover` of a stale claim

The claim is taken in a lane worktree on `T002-repricing`, and the worktree is then removed
(`git worktree remove`), which makes the claim stale.

```
claimed T002 as alice
$ taskrail claim T002 --owner bob --takeover
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.KW1p5Y/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.KW1p5Y/origin.git'
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
f3a1b14e7ba78c9d975ea2a9c6ac7cfdeae1b13f commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
```

### `branch` rename, then `release --force`, then plain `release`

```
claimed T002 as alice
$ taskrail branch T002 T002-renamed --owner alice
T002 branch renamed from T002-repricing to T002-renamed
exit=0
$ taskrail release T002 --owner alice --force
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.0e287J/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.0e287J/origin.git'
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
a3d39ab05b8e182386478c73ada04c67562f9dcb commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
$ taskrail release T002 --owner alice
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
```

### A claim record without `remote.commit`

`remote.commit` was removed from `.git/taskrail/claims/T002.json` by hand after claiming.

```
claimed T002 as alice
$ jq .remote   (python3 equivalent)
{'name': 'origin', 'ref': 'refs/taskrail/claims/T002'}
$ taskrail release T002 --owner alice
taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-repro.tLutWa/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-repro.tLutWa/origin.git'
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
b4d8392115e17f79da536ca3843e5d15b6efe23a commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
```

And `taskrail branch` on such a claim (lane worktree on `T002-repricing`):

```
claimed T002 as alice
$ taskrail branch T002 T002-renamed --owner alice
taskrail: could not update the remote claim refs/taskrail/claims/T002 on origin: error: failed to push some refs to '/tmp/t037-repro.VACvEd/origin.git'
exit=2
$ git -C lane branch --show-current
T002-renamed
$ local claim branch/remote
T002-renamed {'name': 'origin', 'ref': 'refs/taskrail/claims/T002'}
$ published claim branch
  "branch": "T002-repricing",
```

### git's lease semantics on a ref outside `refs/heads`

A bare `origin.git` and a clone `c` (no fetch refspec covers `refs/taskrail/*`, so there is no
remote-tracking ref for the claim), with two parentless commits `C1` = `37aed2b…` and `C2` =
`1197895…`:

```
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002: origin 37aed2b21fd202d0f96bffd5270a727b76b7369d:refs/taskrail/claims/T002
To ../origin.git
*	37aed2b21fd202d0f96bffd5270a727b76b7369d:refs/taskrail/claims/T002	[new reference]
Done
exit=0
37aed2b21fd202d0f96bffd5270a727b76b7369d commit	refs/taskrail/claims/T002
--- delete, lease without expected value (release --force today)
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002 origin :refs/taskrail/claims/T002
error: failed to push some refs to '../origin.git'
To ../origin.git
!	(delete):refs/taskrail/claims/T002	[rejected] (stale info)
Done
exit=1
37aed2b21fd202d0f96bffd5270a727b76b7369d commit	refs/taskrail/claims/T002
--- delete, empty expected value (release today when remote.commit is missing)
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002: origin :refs/taskrail/claims/T002
error: failed to push some refs to '../origin.git'
To ../origin.git
!	(delete):refs/taskrail/claims/T002	[rejected] (stale info)
Done
exit=1
37aed2b21fd202d0f96bffd5270a727b76b7369d commit	refs/taskrail/claims/T002
--- delete, lease on a different commit (remote re-claimed by someone else)
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002:1197895e9f6f0a95dd660a889f4498671330f0e4 origin :refs/taskrail/claims/T002
error: failed to push some refs to '../origin.git'
To ../origin.git
!	(delete):refs/taskrail/claims/T002	[rejected] (stale info)
Done
exit=1
37aed2b21fd202d0f96bffd5270a727b76b7369d commit	refs/taskrail/claims/T002
--- delete, lease on the recorded commit
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002:37aed2b21fd202d0f96bffd5270a727b76b7369d origin :refs/taskrail/claims/T002
To ../origin.git
-	:refs/taskrail/claims/T002	[deleted]
Done
exit=0
--- delete of an absent ref, lease on the recorded commit
$ git push --porcelain --force-with-lease=refs/taskrail/claims/T002:37aed2b21fd202d0f96bffd5270a727b76b7369d origin :refs/taskrail/claims/T002
error: failed to push some refs to '../origin.git'
To ../origin.git
!	(delete):refs/taskrail/claims/T002	[rejected] (stale info)
Done
exit=1
$ git for-each-ref refs/remotes (no tracking ref for the claim namespace)
```

Only a lease naming the commit actually on the remote deletes the ref. The last case is what
`_delete_remote` already tolerates: after a failed push it runs `ls-remote`, and an absent ref
counts as released.

## Root cause

`claims._delete_remote` (`src/taskrail/claims.py`, line 157) chooses the lease from
the `force` flag:

```python
lease = f"--force-with-lease={ref}" if force else f"--force-with-lease={ref}:{remote.get('commit', '')}"
```

`--force-with-lease=<ref>` without a value asks git to expect the value of the remote-tracking
ref for `<ref>`. Claims live in `refs/taskrail/claims/*`, which no fetch refspec maps to a
remote-tracking ref, so git has no expectation to check and rejects the push as `stale info`
(evidence above). The push fails, `ls-remote` still lists the ref, and `_delete_remote` raises
`GitError`; `release` raises before it unlinks the local claim, and `cli.main` turns the error into
exit 2.

The `force` flag was meant to waive the **owner** check in `release()` — "release someone else's
claim". It was also, wrongly, used to pick a weaker lease, although the recorded commit is exactly
as valid when someone else owns the claim: the local claim file lives in the git common directory,
so whichever worktree pushed or re-pushed the claim wrote its commit there. The branch has existed
unchanged since the first claims commit (`3eca7af`).

Every path is affected through the one function, because every force caller goes through
`release(force=True)`:

| Path | Code | Remote operation | Lease today | Result |
|---|---|---|---|---|
| `claim` | `claim()` → `_push_remote` | create | `<ref>:` (must not exist) | correct |
| `claim --takeover` | `claim()` → `release(force=True)` → `_delete_remote(force=True)`, then `_push_remote` | delete, then create | `<ref>` (no value) | **rejected, exit 2** |
| `branch` (T019) | `rename_branch` | update | `<ref>:<remote.commit>` | correct while `commit` is recorded |
| `release` | `release()` → `_delete_remote(force=False)` | delete | `<ref>:<remote.commit>` | correct while `commit` is recorded |
| `release --force` | `release(force=True)` → `_delete_remote(force=True)` | delete | `<ref>` (no value) | **rejected, exit 2** |
| `done`, `discard` | `_change_status` → row written → `release(force=True)` | delete | `<ref>` (no value) | **row written, then exit 2** |

### When `remote.commit` is missing

Every version of `_push_remote` since `3eca7af` has returned `{"name", "ref", "commit"}`, and
`rename_branch` keeps `commit` up to date, so no claim written by taskrail lacks it. A record
without it is hand-edited or damaged. Today such a claim cannot be released or renamed through
the remote at all: `release` leases on `<ref>:` ("must not exist") and `branch` pushes with the
same empty lease — both rejected, as shown above. `release --local-only` still removes the local
file, leaving the remote ref to be deleted by hand.

### Order in `done` / `discard`

`_change_status` writes the row and prints the result (`_write`), then calls
`claims.release(config, task.id, owner, force=True)` outside any `try`. A `GitError` from the
remote delete escapes to `cli.main`, which prints it and exits 2. The row stays written, the
local claim stays (so a later `release` can still find the recorded commit), and the stdout
result already says `done`. A retried `done` exits 5, so the only way out is `taskrail release`.

### Why the tests did not catch it

The remote-claim tests are `test_remote_claim_blocks_another_clone`,
`test_remote_claim_does_not_publish_machine_details`, `test_releasing_a_remote_claim_deletes_the_ref`
and `test_local_only_claim_skips_the_remote` (`tests/test_claims.py`),
`test_a_rename_re_pushes_the_remote_claim` and `test_local_only_rename_leaves_the_remote_claim`
(`tests/test_task_branch.py`), and `test_the_remote_claim_carries_the_run`
(`tests/test_autopilot.py`). Between them they run `claim`, `claim --local-only`, `branch` and a
**plain** `release` by the owner. None runs `release --force`, `done`, `discard` or
`claim --takeover` with `claim_remote` set, so the `force=True` branch of `_delete_remote` never
executed under test. The takeover test (`test_removed_worktree_makes_a_claim_stale_and_takeover_replaces_it`)
and every `done`/`discard` test use repositories without `claim_remote`.

## Ruled out

- **The recorded commit is outdated after a rename.** `rename_branch` re-pushes and records the
  new commit; the plain `release` after `branch` deletes the ref (evidence), and the `--force`
  release fails the same way with or without a rename.
- **Another clone changed the remote ref.** In every reproduction a single clone pushed the claim,
  and `for-each-ref` on the bare remote shows the same commit the local claim records.
- **Owner mismatch.** `release --force` by the owner (`alice`) fails too, so the owner check
  plays no part; `--force` is the only difference from the passing plain release.
- **The server refusing deletes outside `refs/heads`.** The same remote accepts the delete with a
  lease on the recorded commit (`[deleted]`), from both `git push` and the plain `release`.
- **The git version.** Reproduced on git 2.55.0. git-push documents `--force-with-lease=<refname>`
  as requiring the remote value to match the remote-tracking ref, which cannot exist for this
  namespace, so this is not a git regression.
- **`_delete_remote`'s `ls-remote` fallback.** It only turns a failed push into success when the
  ref is already gone, which is correct; here the ref is present, so it rightly raises.
- **`_push_remote` and `claim`.** Creation leases on `<ref>:` and works (`[new reference]`).

## Affected areas

- `src/taskrail/claims.py` — `_delete_remote` (the bug); `rename_branch` and
  `_delete_remote` again for a record without `remote.commit`.
- `src/taskrail/cli.py` — `_change_status` (`done`, `discard`): exit 2 after a
  written row; `cmd_claim` with `--takeover`; `cmd_release` with `--force`.
- Autopilot lanes on a repository with `claim_remote` set: every lane closes with `done`, so every
  close would exit 2 and leave the claim on the remote, blocking nothing locally but showing the
  task as claimed to every other clone (`claims --remote`) until someone deletes the ref.
- DESIGN.md §6.2 already describes the intended behaviour ("a lease on the commit that was
  pushed"); it needs no change.

## Proposed fix

1. **Lease on the recorded commit in every case.** In `_delete_remote`, drop the `force`
   branch: always push `--force-with-lease=<ref>:<remote.commit>`, and drop the now-unused
   `force` parameter (its only caller is `release`). `force` keeps waiving the owner check in
   `release()` and nothing else. A remote ref holding another commit is someone else's claim
   (another clone could only create it after ours was deleted, since creation leases on
   `<ref>:`), so it is never deleted, with or without `--force`; the error stays exit 2 and the
   local claim stays, and `--local-only` remains the way to drop the local record.
2. **A record without `remote.commit`** (decision 1 below). Recommended: resolve the expected
   commit from the remote — `ls-remote` the ref, and lease on that value only when the claim it
   holds is this claim (same `id`, `owner` and `created`); otherwise raise as today. Apply the
   same resolution to `rename_branch`, which shares the lease. Alternatives: refuse with a
   message naming `--local-only` and the ref to delete by hand (smallest change; current exit
   code, better message), or lease on the `ls-remote` value without comparing the content
   (race-free against concurrent changes but can delete a claim another clone pushed after ours
   was removed by hand).
3. **`done` / `discard` order** (decision 2 below). Recommended: keep writing the row first —
   the status change is the command's purpose, and releasing first would drop the claim of a task
   whose row then fails validation, letting another lane take it. When the release fails, catch
   the `GitError` in `_change_status`, keep the local claim, and exit 2 with a message that says
   the row *was* written and names the retry: `taskrail release <ID> --force`. This follows the
   T019 decision for a failed claim re-push after a local rename (accept partial success, exit 2
   naming the ref). Alternatives: leave `_change_status` unchanged (after fix 1 only genuine
   failures remain, but the message still does not say the row was written), or exit 0 with a
   warning (hides a claim still visible to other clones).
4. **Regression tests**, written first and observed failing: with the `remote_pair` fixture,
   `release --force` by the owner deletes the ref; `done` deletes the ref and removes the local
   claim with exit 0; `claim --takeover` of a stale remote claim replaces the ref; and, for
   decision 1, a record without `remote.commit` is released.
5. A `## Unreleased` bullet in `CHANGELOG.md`.

## Fix

Decisions taken at the diagnose gate are recorded in
[docs/autopilot/decisions/T037-delete-remote-claims-with-a-lease-on-the.md](../autopilot/decisions/T037-delete-remote-claims-with-a-lease-on-the.md).
Decision 1 took the smaller refusal instead of the proposed `ls-remote` lookup.

- `claims._delete_remote` always leases on `remote.commit`; its `force` parameter is gone, so
  `release(force=True)` waives only the owner check. A remote ref holding another commit is still
  refused (exit 2, local claim kept).
- A record without `remote.commit` is refused before any push, in both `_delete_remote` and
  `rename_branch`, with a `GitError` naming `--local-only` and `git push <remote> :<ref>`.
  `rename_branch` keeps its T019 order: the local claim already names the new branch when it
  refuses, and the message says so.
- `cli._change_status` (`done`, `discard`) still writes the row first. A `GitError` from the
  release is caught: the local claim stays, stderr says
  `<ID> is marked <status>, but its claim was not released: <reason>; run `taskrail release <ID> --force` to retry`,
  and the command exits 2.
- `CHANGELOG.md` has a bullet under `## Unreleased`.

### Regression tests, run before the fix

Added to `tests/test_claims.py`, all on the `remote_pair` fixture (a bare remote
and two clones with `claim_remote = "origin"`):

| Test | Covers |
|---|---|
| `test_forced_release_deletes_the_remote_claim[alice\|bob]` | `release --force` by the owner and by someone else |
| `test_closing_a_task_deletes_its_remote_claim[done\|discard]` | `done`, `discard` |
| `test_takeover_replaces_a_stale_remote_claim` | `claim --takeover` |
| `test_forced_release_keeps_a_remote_claim_holding_another_commit` | `--force` never deletes another clone's claim (guard; passes before the fix too, by design) |
| `test_a_close_that_cannot_delete_the_remote_claim_says_the_row_was_written[done-done\|discard-discarded]` | decision 2 |
| `test_release_refuses_a_remote_claim_without_its_commit[force0\|force1]` | decision 1, `release` with and without `--force` |
| `test_rename_refuses_to_re_push_a_remote_claim_without_its_commit` | decision 1, `rename_branch` |

On the unfixed code (`uv run pytest -q --color=no --tb=short tests/test_claims.py -k remote`,
failure lines only):

```
_____________ test_forced_release_deletes_the_remote_claim[alice] ______________
E   AssertionError: taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote4/origin.git
E      ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
E     error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote4/origin.git'
E     
E   assert 2 == 0
______________ test_forced_release_deletes_the_remote_claim[bob] _______________
E   AssertionError: taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote5/origin.git
E      ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
E     error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote5/origin.git'
E     
E   assert 2 == 0
______________ test_closing_a_task_deletes_its_remote_claim[done] ______________
E   AssertionError: taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote6/origin.git
E      ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
E     error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote6/origin.git'
E     
E   assert 2 == 0
____________ test_closing_a_task_deletes_its_remote_claim[discard] _____________
E   AssertionError: taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote7/origin.git
E      ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
E     error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote7/origin.git'
E     
E   assert 2 == 0
_________________ test_takeover_replaces_a_stale_remote_claim __________________
E   AssertionError: taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote8/origin.git
E      ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
E     error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote8/origin.git'
E     
E   assert 2 == 0
E   assert 'T002 is marked done, but its claim was not released' in "taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote10/orig...claims/T002 (stale info)\nerror: failed to push some refs to '/tmp/pyte
E   assert 'T002 is marked discarded, but its claim was not released' in "taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote11/orig...claims/T002 (stale info)\nerror: failed to push some refs to '/tmp
________ test_release_refuses_a_remote_claim_without_its_commit[force0] ________
E   assert 'does not record the commit' in "taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote12/orig...claims/T002 (stale info)\nerror: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/
________ test_release_refuses_a_remote_claim_without_its_commit[force1] ________
E   assert 'does not record the commit' in "taskrail: could not delete remote claim refs/taskrail/claims/T002: To /tmp/pytest-of-abigail/pytest-210/remote13/orig...claims/T002 (stale info)\nerror: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/
_______ test_rename_refuses_to_re_push_a_remote_claim_without_its_commit _______
E   AssertionError: Regex pattern did not match.
E     Expected regex: 'does not record the commit'
E     Actual message: "could not update the remote claim refs/taskrail/claims/T002 on origin: error: failed to push some refs to '/tmp/pytest-of-abigail/pytest-210/remote14/origin.git'"
FAILED tests/test_claims.py::test_forced_release_deletes_the_remote_claim[alice]
FAILED tests/test_claims.py::test_forced_release_deletes_the_remote_claim[bob]
FAILED tests/test_claims.py::test_closing_a_task_deletes_its_remote_claim[done]
FAILED tests/test_claims.py::test_closing_a_task_deletes_its_remote_claim[discard]
FAILED tests/test_claims.py::test_takeover_replaces_a_stale_remote_claim - As...
FAILED tests/test_claims.py::test_a_close_that_cannot_delete_the_remote_claim_says_the_row_was_written[done-done]
FAILED tests/test_claims.py::test_a_close_that_cannot_delete_the_remote_claim_says_the_row_was_written[discard-discarded]
FAILED tests/test_claims.py::test_release_refuses_a_remote_claim_without_its_commit[force0]
FAILED tests/test_claims.py::test_release_refuses_a_remote_claim_without_its_commit[force1]
FAILED tests/test_claims.py::test_rename_refuses_to_re_push_a_remote_claim_without_its_commit
10 failed, 5 passed, 13 deselected in 2.86s
```

The first five fail on the `stale info` rejection from the lease without a value — the root
cause. The other five fail because the refused cases had no message naming the row, the retry,
`--local-only` or the ref. The five that pass are the four existing remote-claim tests and the
guard `test_forced_release_keeps_a_remote_claim_holding_another_commit`.

## Verification

After the fix:

```
$ uv run pytest -q tests/test_claims.py
............................                                             [100%]
28 passed in 3.76s
$ uv run pytest -q          # the stage's `test` check
480 passed in 43.25s
```

The stage's `lint` check is not configured in `.taskrail/config.toml` (`[checks]` defines only
`test`), so it was not run.

The CLI end to end, in throwaway repositories under `mktemp -d /tmp/t037-verify.XXXXXX` (same
setup as the reproduction, deleted afterwards):

```
===== release --force by the owner
claimed T002 as alice
$ taskrail release T002 --owner alice --force
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
===== done
claimed T002 as alice
$ taskrail done T002 --owner alice
T002 done
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
===== claim --takeover of a stale claim
claimed T002 as alice
$ taskrail claim T002 --owner bob --takeover
taskrail: warning: T002 was claimed on branch main, but its branch is T002-repricing; work on that branch, or run `taskrail branch T002 <NAME>` to name the branch the task is worked on
claimed T002 as bob
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
059f33e87bb33dc09ee99bc49da6dc2816dfae29 commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
$ published owner
  "owner": "bob",
===== branch rename, then release --force
claimed T002 as alice
$ taskrail branch T002 T002-renamed --owner alice
T002 branch renamed from T002-repricing to T002-renamed
exit=0
$ taskrail release T002 --owner alice --force
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
$ ls .git/taskrail/claims
===== done while the remote ref holds another commit
claimed T002 as alice
$ git -C origin.git update-ref refs/taskrail/claims/T002 $(git -C origin.git rev-parse main)
$ taskrail done T002 --owner alice
taskrail: T002 is marked done, but its claim was not released: could not delete remote claim refs/taskrail/claims/T002: To /tmp/t037-verify.kxTz5z/origin.git
 ! [rejected]        (delete) -> refs/taskrail/claims/T002 (stale info)
error: failed to push some refs to '/tmp/t037-verify.kxTz5z/origin.git'; run `taskrail release T002 --force` to retry
T002 done
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
13ae2aa36bed5d870ff6cf1e14057e24c2cb5dd7 commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
| ✅ | T002 | feature | 3   | T001       | Repricing      | Recompute   |
| ⬜ | T003 | bug     | 1   | T002       | Rounding error | Off by one  |
===== release of a record without remote.commit
claimed T002 as alice
$ taskrail release T002 --owner alice --force
taskrail: the local claim for T002 does not record the commit it pushed to refs/taskrail/claims/T002 on origin, so the remote claim cannot be deleted safely; run `taskrail release T002 --local-only` to drop the local claim, then check the remote claim is this one and delete it by hand with `git push origin :refs/taskrail/claims/T002`
exit=2
$ git -C origin.git for-each-ref refs/taskrail/claims
76a57c9fff7cca36aeb72d021c3fd6ee826edc3a commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
T002.json
$ taskrail release T002 --owner alice --local-only
released T002
exit=0
$ git -C origin.git for-each-ref refs/taskrail/claims
76a57c9fff7cca36aeb72d021c3fd6ee826edc3a commit	refs/taskrail/claims/T002
$ ls .git/taskrail/claims
===== branch rename of a record without remote.commit
claimed T002 as alice
$ taskrail branch T002 T002-renamed --owner alice
taskrail: the local claim for T002 now names branch T002-renamed, but it does not record the commit it pushed to refs/taskrail/claims/T002 on origin, so the remote claim was not updated; pass --local-only to leave the remote claim alone, or check it is this claim and delete it by hand with `git push origin :refs/taskrail/claims/T002`
exit=2
$ published claim branch
  "branch": "T002-repricing",
```

In the "another commit" case the remote ref stands for a claim this clone did not push, so it is
kept even though `done` releases with `force=True`; the row is written, the local claim stays for
the retry, and the message says both.
