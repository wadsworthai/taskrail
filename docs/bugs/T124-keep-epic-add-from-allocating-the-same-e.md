# T124 — Keep epic add from allocating the same epic ID on two branches

## Symptom

`taskrail epic add` without `--id` allocates one above the highest epic ID in the working tree's
`## Epics` table and in the working tree's archive headings (T122). It reads no other branch. When
an epic is committed on one branch, `epic add` on another branch of the same clone hands out the
same ID. Task IDs do not have this problem: `taskrail new` in the same clone skips an ID that is
committed on another local branch (DESIGN.md §6.3).

## Reproduction

Each probe ran in a fresh scratch clone of this repository at `245f484` (`origin/main`), with the
CLI from this worktree's unfixed source:
`uv run -q --project <worktree> taskrail --root <clone>`. A new clone was used for each probe,
because the reservation ledger in `.git/taskrail/reserved/` survives `git checkout -- TODO.md`
(T114). The real backlog was never touched.

**Probe 1: the defect.** Add an epic on a committed branch, then add one on `main`:

```
$ git switch -q -c lane-a
$ taskrail epic add --name "Lane A epic" --objective "A" --json   (on lane-a)
{
  "id": "E10",
  "backlog": "main",
  "file": null,
  "files": [
    "TODO.md"
  ]
}
exit 0
$ git commit -qam "lane-a epic"
$ git switch -q main
$ taskrail epic add --name "Main epic" --objective "M" --json   (on main)
{
  "id": "E10",
  "backlog": "main",
  "file": null,
  "files": [
    "TODO.md"
  ]
}
exit 0
```

**Expected:** `E11`, because `E10` is committed on `lane-a`.

**Probe 2: the task-ID contrast, with the ledger taken out.** This shows that the branch scan
alone, and not the ledger, is what keeps task IDs apart across branches:

```
$ git switch -q -c lane-b
$ taskrail new --epic E09 --kind chore --title "Probe on lane-b" --json   ->  "id": "T126",
$ git commit -qam "lane-b task"
$ git switch -q main
$ cat .git/taskrail/reserved/main.json
[
  {
    "id": "T126",
    "owner": "abigail@archlinux",
    "created": "2026-09-19T08:31:46+00:00"
  }
]
$ rm .git/taskrail/reserved/main.json
$ taskrail new --epic E09 --kind chore --title "Probe on main" --json    ->  "id": "T127",
```

With no ledger, `new` on `main` still skips `T126`, because `ids.used_ids` read it from
`refs/heads/lane-b:TODO.md`.

## Evidence

- `cmd_epic_add` (`src/taskrail/cli.py:1407-1411`) computes the next ID from
  `backlog.epics`, which is the parsed working tree, and from `ids.archived_epic_ids`. That
  function reads only `config.root / backlog.archive_path`, which is also the working tree.
- `ids.used_ids` (`src/taskrail/ids.py`) reads the working tree first and then every revision in
  `refs/heads`. When `[git].claim_remote` is set, it also reads `refs/remotes/<claim_remote>`. It
  reads each revision's main file, its archive and its epic files in one
  `git cat-file --batch` pass. It collects only the `ID` column of task tables, so epic IDs never
  enter it.
- **Who creates epics.** No skill tells a lane or the orchestrator to run `epic add`
  (`grep -rn -i epic src/taskrail/skills/taskrail-*/SKILL.md` finds nothing). Only the core
  `taskrail` skill mentions the command. This repository has created nine epics in its whole
  history. `git log -S'## E0n '` finds the commit that added each one: backlog commits (`9caa812`,
  #6, #11, #20, #61) and one task (T058, #42). So epics are added rarely, one at a time, by a
  person or by an orchestrator working on the backlog, not by parallel lanes.

## Root cause

Epic allocation never got the cross-branch scan that task IDs have had since §6.3 was written. It
has always been "highest in the working tree plus one", and §6.3 says so plainly since T122:
*"They are **not** scanned on other branches and not reserved, so two branches adding an epic at
once get the same ID."* The code that reads other branches, `used_ids`, collects only task-table
IDs. `epic add` never calls it, and nothing else reads epic IDs from a revision.

## Ruled out

- **A stale build or wrong pin.** The probes ran this worktree's source through
  `uv run --project`. The result matches T122's evidence 4, which was obtained the same way.
- **The ledger as the missing part.** Probe 2 shows the scan alone separates committed IDs. The
  ledger covers a narrower case: two allocations that both happen before either one is
  committed. See decision 1.
- **The archive.** Probe 1 involves no archive. T122 already covers the working-tree archive.
- **The merge driver or `validate` hiding the duplicate.** They come in later, when both
  branches meet. The defect is the allocation itself, which already happens on two branches before
  any merge.

## Affected areas

- `taskrail epic add` without `--id`, in any clone where an epic is committed on another local
  branch (or on a remote-tracking branch, when `claim_remote` is set) and not in the working tree.
- `taskrail epic add --id <ID>` accepts an ID that another branch already holds.
- Not affected: task-ID allocation, `archive`, `validate`, and the autopilot, which does not
  create epics.

## Proposed fix

All five decisions below were approved at the diagnose gate as recommended
(`docs/autopilot/decisions/T124-keep-epic-add-from-allocating-the-same-e.md`).

**This narrows the task row in two places, deliberately.** The row asks for "a reservation under
`id_lock`" and for "every local and remote-tracking branch". There is no reservation (D1): the
ledger covers concurrent allocation by lanes before either commits, and epics are not created that
way. Remote-tracking branches are read only when `claim_remote` is set (D2a), the same rule task
IDs follow (§6.3), because nothing gives a reason to make epics stricter than tasks.


Rename `ids.archived_epic_ids` to `used_epic_ids`, keeping the same signature. It reads, on the
working tree and on the same revisions `used_ids` scans (`refs/heads`, plus
`refs/remotes/<claim_remote>` when that is set):

- the IDs in the main file's `## Epics` table, which lists inline and own-file epics alike, and
- the epic headings in the archive (T122's reader, applied per revision).

`cmd_epic_add` allocates one above the highest of these IDs. It refuses `--id` for an ID that is
live in the working tree or archived, with T122's two messages, and for an ID held only on another
branch, with a third message. There is no ledger and no `id_lock` (decision 1). The scan is a
parallel function, not a generalization of `used_ids` (decision 2). One `git cat-file --batch`
call reads every revision's main file and archive.

## Decisions for the gate

1. **Ledger and lock for epics?** Recommendation: **no, the branch scan only.** The ledger exists
   because lanes allocate task IDs concurrently: two `taskrail new` calls in two worktrees, both
   before either commits. Epics are not created that way (see *Evidence*). The remaining window is
   two uncommitted `epic add` runs in two worktrees of one clone. It is narrow, and a person closes
   it by committing. If it happens, the result is a duplicate row, which the merge exposes. The
   ledger would also bring the stale-reservation behaviour T114 found, and it would need its own
   file, because `reserve` parses every entry with the task prefix. Without a ledger, `id_lock`
   protects nothing, since there is no shared state to update. Alternatives: (b) a ledger under
   `id_lock` in a separate `<backlog>.epics.json`, mirroring `reserve`/`reserved`, about 30 lines
   plus tests; (c) `id_lock` around the scan and write without a ledger. That serializes two
   concurrent `epic add` calls but does not separate them, because the first one's epic is still
   uncommitted when the second one scans.
2. **Reuse `used_ids` or add a parallel scan?** Recommendation: **a parallel `used_epic_ids`**,
   about 20 lines. It repeats `used_ids`'s three-line revision list and its `read_blobs` call. It
   reads only two files per revision (main and archive, no epic files) and one table per file.
   This is the second consumer, so under the rule of three it is duplicated, not extracted.
   Generalizing `used_ids` to return both sets would change the signature for `reserve`, `new`
   and `workspace` to serve one rare command. Cost: one extra `git cat-file --batch` process per
   `epic add`, which is not measurable next to the command's own parse.
   **Sub-question, remote-tracking branches:** the task row says "every local and remote-tracking
   branch", but task IDs read remote-tracking branches only when `claim_remote` is set (§6.3,
   "with a remote configured"). Recommendation: **the same rule as task IDs**, so both guarantees
   read identically. Alternative: always scan `refs/remotes/*` for epics, which would make epics
   stricter than tasks for no stated reason.
3. **Regression test.** Recommendation, in `tests/test_ids.py` with the `git_repo` fixture:
   - `epic add` on `main` after a branch commits `E02` prints `E03` (fails before the fix with
     `E02`);
   - an epic that exists on a branch only as an archive heading still counts (fails before the fix);
   - **a negative control:** the same branch is deleted (`git branch -D`), and `epic add` prints
     `E02`. This proves that the branch, and nothing else in the fixture, is what moved the
     counter;
   - `epic add --id E02` is refused with exit 5 while `E02` is on another branch (fails before the
     fix with exit 0).
4. **`--id` of an ID held only on another branch:** refuse it (exit 5, a message saying another
   branch holds it), as recommended? Alternative: allow it, since `--id` is the explicit escape
   hatch. Recommendation: **refuse**. The set is already computed, and accepting the ID would
   create the same duplicate this task removes.
5. **Documentation.** Recommendation: rewrite §6.3's **Epic IDs** paragraph to say that epic IDs
   are scanned like task IDs (working tree, local branches, and remote-tracking branches with
   `claim_remote`, including archive headings) but not reserved, so two uncommitted `epic add`
   runs in two worktrees can still collide. Update T122's §7.6 bullet if it says "working tree".
   Add one `CHANGELOG.md` bullet under Unreleased.

## Fix

- `src/taskrail/ids.py`: `archived_epic_ids` is replaced by
  `used_epic_ids(config, backlog) -> dict[str, str]`. It reads epic IDs from the `## Epics` table
  of the backlog's main file and from the archive's `## E## — Name` headings. It reads them first
  on the working tree, then on the revisions `used_ids` scans: `refs/heads`, plus
  `refs/remotes/<claim_remote>` when that is set. Each revision's main file and archive come from
  one `git cat-file --batch` call. Each ID maps to the first place it was seen: the file for the
  working tree, `<ref>:<file>` for a revision. That lets `epic add` say where a refused ID is.
  Outside a git repository, only the working tree is read, as before.
  `epic add` has always worked in a directory that is not a git repository. The existing tests
  that call it through the non-git `repo` fixture, T122's three among them, depend on that.
  `used_ids` itself is unchanged (D2).
- `src/taskrail/cli.py`, `cmd_epic_add`: allocates one above the highest of the live epics and
  `used_epic_ids`. `--id` is refused with exit 5 in three cases:
  - the epic is live, with the existing message;
  - the working-tree archive holds the ID, with T122's message;
  - any other place holds it, with
    ``taskrail: epic `E10` is already used in refs/heads/lane-a:TODO.md, on another branch; pick another ID``.
- There is no ledger and no `id_lock` (D1).
- `DESIGN.md` §6.3: the **Epic IDs** paragraph now says epic IDs are read in the same places as
  task IDs, and that they are **not reserved**, which leaves one collision window: two uncommitted
  `epic add` runs in two worktrees of one clone. It says why, and how to avoid it. The §7 CLI
  table row for `epic add` and the §7.6 archive bullet now say the same. `CHANGELOG.md` has one
  bullet under Unreleased.

## Verification

**Before the fix.** The four tests were added to `tests/test_ids.py` and run against the
unfixed code with
`uv run pytest -q tests/test_ids.py -k "epic_committed or epic_archived or without_the_branch or epic_id_on_another"`:

```
>       assert (code, out.strip()) == (0, "E03"), err
E       AssertionError: 
E       assert (0, 'E02') == (0, 'E03')
tests/test_ids.py:99: AssertionError
>       assert (code, out.strip()) == (0, "E03"), err
E       AssertionError: 
E       assert (0, 'E02') == (0, 'E03')
tests/test_ids.py:110: AssertionError
_____ test_an_epic_id_on_another_branch_is_refused_when_passed_explicitly ______
>       assert code == 5
E       assert 0 == 5
tests/test_ids.py:125: AssertionError
FAILED tests/test_ids.py::test_an_epic_committed_on_another_branch_is_not_allocated_again
FAILED tests/test_ids.py::test_an_epic_archived_on_another_branch_is_not_allocated_again
FAILED tests/test_ids.py::test_an_epic_id_on_another_branch_is_refused_when_passed_explicitly
3 failed, 1 passed, 8 deselected in 1.10s
```

Each failure matches the root cause:
- E02, which is committed on `lane-a`, was reissued.
- E02, which is archived on `lane-a` only, was reissued.
- `--id E02` was accepted with exit 0.

The negative control, `test_without_the_branch_the_same_clone_would_allocate_the_epic_id`,
passed, as it must: once `lane-a` is deleted, E02 is free.

**After the fix.** `uv run pytest -q tests/test_ids.py tests/test_archive.py` printed
`36 passed in 1.81s`, which includes T122's three archive tests, unchanged.
`uv run pytest -q -k epic` printed `39 passed, 1224 deselected in 3.80s`.

**The reproduction, rerun with the fixed source** in a fresh scratch clone at `245f484`:

```
$ epic add (lane-a)          ->  "id": "E10",
$ git commit -qam "lane-a epic"; git switch -q main
$ epic add (main)            ->  "id": "E11",     exit 0
$ git checkout -q -- TODO.md
$ epic add --id E10 (main)
taskrail: epic `E10` is already used in refs/heads/lane-a:TODO.md, on another branch; pick another ID
exit 5
```

T122's reproduction, in a fresh clone reset to `5215682` with every other local branch deleted,
still gives `"id": "E09"`. `--id E07` still prints
``taskrail: epic `E07` is archived in docs/archive.md; an archived ID is never reused`` and exits 5.

`taskrail checks T124 --stage fix` printed `1263 passed in 141.60s (0:02:21)`, `passed test`,
`not configured lint` and `T124 in <worktree>: passed`.
