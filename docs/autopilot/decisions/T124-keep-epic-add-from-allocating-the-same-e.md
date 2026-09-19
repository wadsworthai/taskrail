# T124 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T124-keep-epic-add-from-allocating-the-same-e.md` and its commit
`da1fa27` (artifact and index row alone); both probes, each in a fresh scratch clone so the
reservation ledger could not leak between them; the search showing no executor or autopilot skill
mentions epics and that this repository has created nine in its whole history; and the root cause
in `cmd_epic_add` and `ids.archived_epic_ids`, both reading the working tree only.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | Do epics need the ledger and `id_lock` the row asks for? | **no — the branch scan only** · (b) a ledger plus lock in its own file · (c) a lock only | **no ledger** — against the row's wording, deliberately | The lane objected at the first gate with evidence, as CLAUDE.md asks, rather than building around the row: the ledger exists because **lanes allocate task IDs concurrently before either commits**, and nothing allocates epics that way — no skill mentions them, and nine epics in this repository's history were each added one at a time by a person or the orchestrator. Probe 2 shows that once an ID is committed on another branch, the scan alone keeps it apart. A ledger would import T114's stale-reservation behaviour for a race that does not occur, and a lock without a ledger cannot separate two uncommitted scans at all. The remaining window — two uncommitted `epic add` runs in two worktrees of one clone — is narrow and surfaces as a duplicate row at merge. |
| D2 | Reuse `used_ids` or a parallel scan | **a parallel `used_epic_ids`, ~20 lines** · generalise `used_ids` | **parallel** | Second consumer: rule of three says duplicate. Generalising would change `used_ids`' signature for `reserve`, `new` and `workspace` to serve one rare command. |
| D2a | Remote-tracking branches | **the same rule as task IDs — only when `claim_remote` is set** · always scan `refs/remotes/*` | **the same rule** | The row says "every local and remote-tracking branch", but task IDs read remote-tracking branches only with a remote configured (§6.3). Making epics stricter than tasks has no stated reason; matching them is the simpler, consistent rule. |
| D3 | Tests | **branch-held epic moves the counter; archive-only heading on a branch counts; negative control deleting the branch; `--id` of a branch-held epic refused** | **as recommended** | The control — delete the branch and the next ID drops back — proves the branch is what moved the counter. |
| D4 | `--id` for an ID held only on another branch | **refuse with exit 5, naming the reason** · allow as an escape hatch | **refuse** | Accepting it would create exactly the duplicate this task removes. |
| D5 | Documentation | **rewrite §6.3's *Epic IDs* paragraph, the §7.6 bullet and the §7 table row; one changelog bullet** | **as recommended** | T122's §6.3 sentence saying epic IDs are not scanned on other branches becomes false with this fix; the new text must still say they are not *reserved*, so the remaining window stays documented. |

## fix gate

Reviewed: commit `651ab40` — `used_epic_ids` replacing `archived_epic_ids` in `ids.py`, the
allocation and three refusals in `cmd_epic_add`, four tests, the §6.3, §7 and §7.6 lines and the
changelog bullet, with `archive.py`, `src/taskrail/autopilot/` and `validate` untouched; the recorded
failures before the fix — E02 reissued from a branch's Epics table and from a branch's archive, and
`--id E02` accepted — with the negative control passing; the probe re-run giving E11 after a branch
took E10; T122's reproduction still holding; and `taskrail checks T124 --stage fix` (1,263 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Outside a git repository `used_epic_ids` reads only the working tree | **accept** | **accept** | `epic add` has always worked outside git and existing tests depend on it, T122's among them. Adding a git requirement to fix a git-only race would break more than it mends. |
| 2 | The refusal says "on another branch" even when the ref it names is the checked-out branch | **reword to "is already used in `<ref>:<file>`"** · leave it | **reword** | The ref it prints is right and the sentence around it is wrong in that case. A message that misstates where an ID was found sends the reader to look in the wrong place; the fix is one line and costs nothing. |

## close

Reviewed: the reword committed on its own, the refusal now reading ``epic `E02` is already used in
refs/heads/lane-a:TODO.md; pick another ID`` with the test asserting the whole string, the artifact
noting that `new` and `epic add` differ outside git, and `taskrail done T124` on its own commit.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | **`fix` / `cli`** | **`fix` / `cli`** | `epic add` handed out an ID another branch already held. |

## rebase after T121 merged

`main` advanced to `0fb3fe0` (T121). Rebased with three known-class conflicts (two index files and
`CHANGELOG.md`); `DESIGN.md` and `TODO.md` merged cleanly, and none of this branch's source files
overlap T121's. No conflict markers; `taskrail checks T124` passed with 1,269 tests and `taskrail
validate` reports 7 tasks, 0 errors.
