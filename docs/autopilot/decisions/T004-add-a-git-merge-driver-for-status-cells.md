# T004 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T004-add-a-git-merge-driver-for-status-cells.md` (commit
`ecf17ee`), its seventeen acceptance criteria, and the lane's git probes: no `MERGE_HEAD`,
`REBASE_HEAD` or `CHERRY_PICK_HEAD` exists while a driver runs; the `%X`/`%Y` labels resolve to
commits; `git merge-file` stays clean only when the merged tables are placed into the base too; and
a `merge=taskrail` attribute without the config falls back to git's text merge.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Driver contract | options for marker size, path and labels, exit 0/1, internal fallback to `git merge-file` · positional `%O %A %B %L %P %S %X %Y` | **as recommended** | Explicit options are readable in the config line; exit codes stay what git expects. |
| Q2 | Shell fallback when taskrail cannot start | yes · bare command | **yes** | A clone without `uvx` must still get a normal text merge, never a file left conflicted without markers. |
| Q3 | Files listed in `.gitattributes` | backlog, epic files and artifact indexes · backlog and epic files only | **include the indexes** | Appended index rows are this run's most frequent conflict, and the same row merge covers them. |
| Q4 | Per-clone install | opt-in `init --merge-driver`; `upgrade` refreshes the block and only updates an existing config · `upgrade` adds the config wherever recorded | **opt-in** | A driver runs repository code during merges; each clone chooses it. |
| Q5 | Sides for the `Reopens:` check | resolve the labels to commits, symmetric difference, leave the conflict when unresolved · refs or rebase state files | **resolve the labels** | The probes show the refs are absent; an unresolved label is a conflict for a human, not a guess. |
| Q6 | New epic files | `epic add --own-file` and `epic split` update the block, `upgrade` repairs · `upgrade` only | **as recommended** | The block stays correct at the moment a file appears. |
| Q7 | CHANGELOG bullets | follow-up feature in E02 · include here | **follow-up** (opened on this branch with `taskrail new`) | A moved bullet needs history, not a table merge; this run hit that case. |
| Q8 | Validate inside the driver | no · yes | **no** | Other backlog files may still be unmerged when it runs; step 8 validates afterwards. |
| Q9 | Adopt the driver in this repository now | decide after merge · commit a block here | **after merge** | Adopting it changes every clone's merges here and deserves its own small task once the driver is released. |

Plan approved. The lane never installs the driver into this checkout's git config.

## implement gate

Reviewed: commits `125002e` (T040), `db27523` (tests against a raising stub) and `ac74245`
(`mergedriver.py`, `init --merge-driver`, the extras hunk in `install.py`, the `epic add`/`split`
refreshes in `cli.py`, core skill step 8, DESIGN.md §7.4 and §12.8, README, CHANGELOG). Re-ran
`tests/test_merge_driver.py` in the lane's worktree: 47 passed; the lane's full suite gave 688. The
tests failed against the stub, and making `merge_tables` a no-op failed 25 of them, including every
real `git merge`, `rebase` and `cherry-pick` case. The configured fallback line runs
`git merge-file` into `%A` when taskrail cannot start. This checkout has no `merge.*` config and no
`.gitattributes`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve, including the `on_written` refreshes in `cli.py` and the local import in `install()` | approve · changes | **approve** | Both hunks are small and keep clear of T014's and T024's lines. |
| 2 | A clone with `merge.taskrail.name` but no `driver` | documented only · `upgrade` notes it | **documented only** | taskrail never writes that state; §7.4 gives the one-line fix. |
| 3 | T040's scope | 3-point feature in E02 depending on T004 · other | **as opened** | Moved changelog bullets need history, as decided at the plan gate. |

## rebase after T024, T012 and T014

T024 (`977064f`), T012 (`525af38`) and T014 (`9c87bc2`) were squash-merged into `main`. The
orchestrator rebased the branch onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in the docs indexes, CHANGELOG and `TODO.md` | keep both · stop | **keep both** | Rows and bullets added on both sides; T004 `✅`, T040 added, no `Reopens:` commit. |
| 2 | Conflict in the `cli.py` import line | keep both · stop | **keep both** | `history` from T012 and `mergedriver` from this branch. |
| 3 | Conflict in `.taskrail/installed.json` (class 3) | valid manifest, merged sources, `upgrade --force` · hand-merge | **class 3** | Took `main`'s manifest, kept the merged core skill source (step 8 from this branch, T014's "Editing tasks" section), ran `upgrade --force`; the manifest digest matches the installed copy. |

The full suite ran on the conflict-resolved commit before continuing (788 passed). After the rebase:
the only conflict markers are the quoted verification output in this task's artifact, `pytest -q`
788 passed, `taskrail validate` 0 errors, a second `upgrade` reports nothing to create or update, and
this checkout still has no `merge.*` config and no `.gitattributes`.
