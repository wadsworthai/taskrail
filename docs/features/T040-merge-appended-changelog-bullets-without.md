# T040 — Merge appended changelog bullets without duplicating moved ones

Kind: feature · Epic: E02 · Status: verified

Source: T004's plan-gate decision Q7
([decisions](../autopilot/decisions/T004-add-a-git-merge-driver-for-status-cells.md)), which
left changelog bullets out of the merge driver because "keep both" duplicates a bullet one side
moved; `DESIGN.md` §7.4 (the driver) and §12.8 (conflict class 2: "changelog
bullets by hand until T040"). Stacked on T004, which is done on its unmerged branch; this branch
starts from `origin/T004-add-a-git-merge-driver-for-status-cells`. No prior work: `show` reported
no artifact, branch or commit for T040.

## Behaviour

Today two branches that each append one bullet at the end of `## Unreleased` in a changelog
conflict every time (*Evidence* E1, case 1), even with T004's driver installed: the changelog is
not in the driver's `.gitattributes` block, and the driver only understands tables. Worse, the
by-hand rule "keep both" is wrong when one side **moved** a bullet: a branch commit that moves
its own bullet from the top of the section to the end, replayed by a rebase onto a mainline that
added a bullet at the top, conflicts at the top; keeping both leaves the moved bullet twice
(E1, case 2).

After this change, in a clone with the driver installed, git merges bullet lists the way the
driver already merges table rows: bullets both sides add are all kept, a bullet one side moved
appears once at its new place, and conflict markers remain only around a bullet both sides
changed differently.

### What gets list merging

- **Every file the driver receives** has its bullet lists merged, after its tables (backlog files,
  epic files and artifact indexes included — a bullet list in an epic's introduction merges the
  same way). The driver does not look at the path.
- **`init --merge-driver` adds changelogs to the block.** Every file named `CHANGELOG.md`
  (case-insensitive) that `git ls-files` reports — tracked, or untracked and not ignored — outside
  the configured `worktree_dir` gets a `/<path> merge=taskrail` line in the block, next to the
  backlog, epic and index files. `upgrade` and `init` refresh it while the extra is recorded, so a
  changelog created later is picked up by the next `upgrade`. In this repository that would list
  `/CHANGELOG.md` (this task does not install the block here — see *Out of scope*).
- **Any other file** (a `CHANGES.md`, `HISTORY.md`, release notes) opts in with its own
  `merge=taskrail` line written **outside** the marked block, which taskrail never touches. This
  needs no code: the attribute is what routes a file to the driver.

### The unit: a bullet in a list under a heading

1. **Headings.** ATX headings (`#` to `######`) outside fenced code define a heading path: a
   heading of level *L* replaces every open heading of level *L* or deeper. The text before the
   first heading has the empty path. `## Unreleased` › `### Added` is a different path from
   `## 0.1.0` › `### Added`.
2. **Bullet.** A line outside fenced code starting at column 0 with `- `, `* ` or `+ `, plus every
   following non-blank line that starts with whitespace (wrapped text, nested bullets, indented
   code). Ordered items (`1.`) are not bullets: their numbers change when items are added.
3. **List.** A maximal run of consecutive bullets with no blank line between them (a tight list).
   A blank line, a heading, or any non-indented line that is not a bullet ends it.
4. **Identity.** A list is identified by its heading path and its position among the lists under
   that path. A list is merged only when the path has the **same number of lists** in every version
   that has the path, and the path exists on both the current and the other side; the base's list
   is empty when the base lacks the path. Otherwise the lists under that path are left to
   `git merge-file` untouched.
5. **Key.** A bullet's key is its text, every line with its trailing whitespace and line ending
   removed — so a CRLF file and its LF copy have equal keys. A list whose keys are not unique in
   any version is left to git.

### How a list is merged

1. **Edits are paired.** For each side, `difflib.SequenceMatcher` over base keys and that side's
   keys (`autojunk=False`). In every `replace` block, the base bullets whose key the side no longer
   has anywhere are *removed*, the side's bullets whose key the base has nowhere are *added*; when
   both counts are equal and non-zero they pair up in order as **edits** of the base bullet (its
   identity stays the base key). When both are non-zero and differ, the list is left to git. A
   bullet whose text is present in the base and in the side is never an edit, wherever it sits.
2. **Each identity is merged three-way**, like a table row:
   - in the base and on both sides: equal texts are kept; a side that left it as in the base takes
     the other side's text; two different edits are **unresolved**;
   - in the base and on one side only: removed when that side left it unchanged; **unresolved**
     when that side edited it (modify/delete);
   - only in the base: removed by both;
   - not in the base: added once, whether one side or both added it.
3. **Moves are recognised**, never duplicated. Among the bullets present in the base and on both
   sides, a side **moved** a bullet when it is outside the matching blocks of `SequenceMatcher`
   over the base's order and that side's order of those bullets. A bullet moved on one side takes
   that side's position; moved on both sides, the current side's.
4. **Order**, extending the table rule: the current side's surviving bullets, without those only
   the other side moved; then, walking the other side's order, each bullet not yet placed (added
   by the other side, moved by it, or an unresolved one only the other side has) goes right after
   its nearest predecessor there that is already placed, past bullets new on the current side that
   follow it. Both sides appending therefore gives the current side's bullets first, then the
   other's — in a rebase, the mainline's first. Prototype results over bullet keys
   (*Evidence* E2): base `XY`, current `XYA`, other `XYB` → `XYAB`; base `NXY`, current `MNXY`,
   other `XYN` → `MXYN`.
5. **Never twice.** If the merged list would hold two bullets with the same key (for example one
   side adds a bullet whose text equals the other side's edit of an existing one), the list is left
   to git instead.
6. **Placed into all three inputs**, exactly as tables are: every merged list is replaced by its
   merged bullets in the base, current and other texts — identical, so they are context — except
   unresolved bullets, which keep each version's own text at their merged position (absent where
   that version has none). `git merge-file` then merges the rest and marks only the unresolved
   bullets. Line endings and a missing final newline are kept as `_region` keeps them for tables.

### Where it lives in the driver

`merge_text` runs `merge_tables` (unchanged), then a new `merge_lists` over the three texts it
returns, then `git merge-file` once. Tables and bullets never share lines (a table line starts with
`|`), so the two stages are independent; the fallback to `git merge-file` on any exception covers
both. `DRIVER_NAME` stays `taskrail backlog tables`, so no clone's git config changes.

### Documentation

- DESIGN §7.4: a *Bullet lists* paragraph after the tables, the changelog lines of the block, and
  the "outside the block" opt-in. §12.8 class 2: changelog bullets by the driver where the
  changelog has the attribute, by hand otherwise — keeping a moved bullet only at its new place.
- CHANGELOG: one bullet at the end of `## Unreleased`.

## Acceptance criteria

Each criterion is tested against real `git merge` or `git rebase` in a throwaway repository with
the driver installed, unless it says *unit*, which calls `merge_text` on three strings.

1. Both sides append one bullet at the end of `## Unreleased`: `git merge` and `git rebase`
   complete with no conflict, each bullet once, the current side's first (the mainline's first in
   the rebase).
2. **The moved bullet.** A branch adds N at the top of `## Unreleased` in one commit and moves it to
   the end in the next; the mainline meanwhile adds M at the top and P at the end. `git rebase
   main` completes with no conflict, and the section holds M, the old bullets, P and N, each once.
   *Unit:* base `N X Y`, current `M N X Y`, other `X Y N` → `M X Y N`, clean.
3. A move on one side and an append on the other at the move's destination, both ways round
   (*unit*): no duplicate, no conflict, the documented order.
4. A bullet with wrapped continuation lines and a nested sub-bullet merges, moves and conflicts as
   one unit; a bullet added identically on both sides appears once (*unit*).
5. The same bullet edited differently on both sides: markers around that bullet's lines only,
   every other bullet and prose change merged, exit 1. Edited on one side and deleted on the other:
   marked. Edited on one side while the other appends: clean, with the edit.
6. A bullet deleted on one side and unchanged on the other is removed, also when the other side
   appends next to it (*unit*).
7. Lists left to git give exactly the `git merge-file` result of the original inputs (*unit*, byte
   for byte, in a file with no tables): the heading renamed or removed on one side; a different
   number of lists under the heading; a duplicate bullet in one version; a `replace` block with
   unequal removed and added counts; a merge that would hold the same text twice. Ordered items and
   bullets inside a fenced code block are not merged as lists.
8. Lists are told apart by heading path: both sides appending under `### Added` of
   `## Unreleased`, while one also appends under `### Fixed`, merge cleanly, and a bullet under
   `## 0.1.0` › `### Added` is never moved into `## Unreleased` › `### Added` (*unit*).
9. Prose right after a merged list merges cleanly; two different edits of one prose line conflict
   as git would (*unit*).
10. A backlog file whose epic introduction holds a bullet list: rows and bullets appended on both
    sides merge in one pass (*unit*).
11. CRLF line endings and a missing final newline after a list are kept (*unit*).
12. `init --merge-driver` lists every `CHANGELOG.md` (any directory, any letter case, tracked or
    untracked-not-ignored) in the block and skips ones under `worktree_dir`; a changelog added later
    appears after `upgrade`; outside a git repository the block holds no changelog lines and
    `init` still succeeds.
13. A file outside the block given `merge=taskrail` by its own `.gitattributes` line gets its
    bullets merged by a real `git merge`, and `upgrade` keeps that line.
14. An exception raised inside the list stage makes the driver produce exactly the
    `git merge-file` result, with the warning, exit 0 or 1 (*unit*); every T004 test still passes.

## Affected areas

- `src/taskrail/mergedriver.py`: a list scanner (headings, bullets, lists outside
  fences), `merge_lists` (pairing, three-way identities, move-aware order, rendering into the three
  inputs), `merge_text` calling it after `merge_tables`, and `attribute_paths` adding changelogs
  found with `git ls-files -z --cached --others --exclude-standard`.
- `tests/test_merge_driver.py`: unit and real-git cases above, plus install cases.
- `DESIGN.md` §7.4 and §12.8; `CHANGELOG.md`.
- Reused without change: `_region`'s end-of-line handling (generalised only if it cannot take
  bullets as they are), `_merge_file`, `update_attributes`, `attribute_line`.
- Not touched: `config.py`, `install.py`, `cli.py`, the skills and their installed copies.

## Out of scope

- **Release rotation.** One side renames `## Unreleased` to `## 0.2.0` and opens a new, empty
  `## Unreleased` while the other appends a bullet to the old one: the path has no list on one side,
  so git merges it as today and it conflicts. Where the bullet belongs is a decision.
- **Loose lists** (blank lines between bullets), ordered lists, setext headings and lazy
  continuation lines: left to git.
- **A configurable list of changelog paths** in `.taskrail/config.toml` (see Q1's alternative).
- **Adopting the driver in this repository** (T004's Q9), and installing it into this checkout.
- **The by-hand rule in the skills.** The autopilot skill's class 2 already says "one entry per
  task"; changing skill text means reinstalling copies, which parallel lanes conflict on (class 3).

## Open questions and risks

Decisions for the plan gate, each with a recommendation:

- **Q1 — Which files, and how `init --merge-driver` learns the changelog path.** Recommended: the
  block lists every `CHANGELOG.md` found by `git ls-files` (case-insensitive name, outside
  `worktree_dir`), and any other file opts in with a `merge=taskrail` line outside the block.
  Alternatives: (a) a config key such as `[merge_driver].files = ["CHANGELOG.md"]`
  rendered into the block — explicit and covers any name, but a new config table in `config.py`
  and DESIGN §4, and nothing happens until a repository sets it; (b) no automatic lines at all,
  only the documented manual line; (c) `init --merge-driver --changelog PATH` recorded in
  `installed.json` — touches `install.py` and the manifest.
- **Q2 — Where list merging applies.** Recommended: every file the driver receives, without looking
  at the path. Alternative: only files whose `%P` is named `CHANGELOG.md` or listed — safer for
  backlog files, but a manually opted-in `CHANGES.md` would then need a second mechanism.
- **Q3 — The unit and list boundaries.** Recommended: column-0 `-`/`*`/`+` bullets with indented
  continuation lines, tight lists only, identity by heading path and position with equal list
  counts. Alternative: allow blank lines inside a list — covers loose lists, but a blank line then
  cannot tell a list's end from its next item, and prose after a list is easily swallowed.
- **Q4 — Recognising a move.** Recommended: identical text present in the base and both sides,
  outside the `SequenceMatcher` matching blocks on one side; the moving side's position wins,
  the current side's when both moved it. Alternatives: a bullet moved differently on both sides is
  a conflict (an ordering disagreement in a changelog rarely deserves a human); or detect only
  "removed at one place and added at another by the same side" — the same thing once keys are
  texts, but it misses a move whose surroundings were also edited.
- **Q5 — Edits and what stays a conflict.** Recommended: pair removed and added bullets inside a
  `replace` block of equal counts as edits; two different edits and edit/delete are marked; unequal
  counts, duplicate keys and a result with repeated text leave the list to git. Alternative: no
  edit pairing — simpler, but two different edits of one bullet would then silently become two
  bullets, which is exactly the duplication this task removes.
- **Q6 — Order of bullets both sides append.** Recommended: the current side's first, as for rows.
  Alternative: the other side's first, so a rebase keeps the branch's bullet last — but it would
  differ from rows in the same file and from `git merge-file --union`.
- **Q7 — Structure.** Recommended: a second stage `merge_lists` after the unchanged `merge_tables`,
  each placing its merged regions into all three inputs, then one `git merge-file`; `DRIVER_NAME`
  unchanged. Alternative: one combined region pass (shared line-index bookkeeping, but it rewrites
  T004's tested code), or renaming the driver (every clone's config is rewritten by `upgrade`).
- **Q8 — Documentation reach.** Recommended: DESIGN §7.4 and §12.8 and the CHANGELOG only. The
  README's `--merge-driver` bullet says "conflicts … in backlog tables"; a half-sentence there
  ("and bullets appended to changelogs") is outside this lane's listed files. Recommended: include
  that half-sentence; alternative: leave the README to a later docs pass.

Risks:

- **Merging lists in backlog and index files** changes a result that is today git's: bullets both
  sides add next to each other merge instead of conflicting. Every rule falls back to git where it
  cannot tell, but a list meant to conflict (two people rewording the same checklist differently in
  a `replace` block of unequal size) is left to git, not marked by the driver — same as today.
- **`git ls-files` cost** in `attribute_paths`, which `epic add --own-file` and `epic split` also
  call: one process, bounded by the repository's file list; `--others --exclude-standard` walks
  untracked directories. If that proves slow, tracked files only.
- **Automatic lines for changelogs nobody asked for** — for example a vendored third-party
  `CHANGELOG.md`: its merges become list-aware too. The attribute is still only active in a clone
  that opted in with `init --merge-driver`.
- **Size.** Three points; the list merge is about the size of T004's row merge. If it must shrink,
  drop Q1's automatic changelog lines first (the manual line still works) and keep the merge.
- **Parallel lanes.** T039 edits `install.py` `workflow()` only; T009 is docs only. This task does
  not touch `install.py`. It stacks on T004, so T004's merge will require rebasing this branch.

## Plan-gate decisions

Approved as recommended (Q1–Q8), recorded in
`docs/autopilot/decisions/T040-merge-appended-changelog-bullets-without.md`. Q8: the README's
`--merge-driver` bullet gains the half-sentence on changelog bullets.

## Changes at implementation

- **An empty base section.** The plan merged lists only when every version holding the path had
  the same number of lists. A `## Unreleased` with no bullets in the base (the usual state right
  after a release) while both sides add the first bullet would then conflict. The base may now have
  **no** lists under the path; its list is empty and nothing is placed into the base. Any other
  count mismatch is still left to git. Test:
  `test_the_first_bullets_both_sides_add_to_an_empty_section_are_all_kept`.
- **A fence inside a bullet** (an indented ```` ``` ```` line while a list is open) leaves every list
  under that heading path to git: the fence's lines are not a plain run of indented lines, so the
  bullet's extent is unreliable. Test case `a fence inside a bullet`.
- **Thematic breaks** (`* * *`, `- - -`) are not bullets. Test:
  `test_bullets_lists_and_heading_paths_are_read_as_documented`.
- `changelog_paths(root, worktree_dir)` is a separate public helper that `attribute_paths` calls. It
  runs `git ls-files -z --cached --others --exclude-standard` with `check=False`, so outside a git
  repository it adds nothing.

## Test coverage

All in `tests/test_merge_driver.py`, section *bullet lists* (33 tests, 47 → 80 in the
file).

| # | Criterion | Tests |
|---|---|---|
| 1 | bullets appended on both sides, `merge` and `rebase` | `test_bullets_appended_on_both_sides_are_all_kept_current_first`, `test_git_merge_and_rebase_keep_bullets_appended_on_both_branches[merge/rebase]`, `test_the_first_bullets_both_sides_add_to_an_empty_section_are_all_kept` |
| 2 | the moved bullet, real rebase and unit | `test_a_rebase_replaying_a_move_of_the_branchs_own_bullet_leaves_it_once` (regression; also shows the same rebase conflicts without the driver), `test_a_bullet_moved_to_the_end_while_the_other_side_added_one_at_the_top_is_not_duplicated` |
| 3 | a move and an append at its destination, both ways | `test_a_move_and_an_append_at_its_destination_keep_each_bullet_once` (4 cases, including moved on both sides) |
| 4 | continuation lines as one unit; identical addition once | `test_a_bullet_with_continuation_lines_is_one_unit_and_an_identical_addition_appears_once` |
| 5 | different edits; edit/delete; edit with an append | `test_the_same_bullet_edited_differently_marks_only_that_bullet`, `test_a_real_bullet_conflict_is_marked_around_that_bullet_only`, `test_a_bullet_edited_on_one_side_and_deleted_on_the_other_is_marked`, `test_a_bullet_edited_on_one_side_merges_with_an_append_on_the_other` |
| 6 | deleted bullets | `test_a_deleted_bullet_is_removed_when_the_other_side_appends_next_to_it` |
| 7 | lists left to git equal `git merge-file` | `test_a_list_that_cannot_be_merged_by_bullet_gets_git_merge_file_result` (8 cases), `test_bullets_lists_and_heading_paths_are_read_as_documented` |
| 8 | heading paths | `test_lists_are_told_apart_by_their_heading_path`, `test_bullets_lists_and_heading_paths_are_read_as_documented` |
| 9 | prose after a list | `test_prose_right_after_a_merged_list_merges_cleanly_and_conflicting_prose_is_marked` |
| 10 | rows and bullets in a backlog file | `test_rows_and_bullets_of_a_backlog_file_merge_in_one_pass` |
| 11 | CRLF and no final newline | `test_bullet_line_endings_and_a_missing_final_newline_are_kept` |
| 12 | changelogs in the block; `upgrade`; outside git | `test_init_merge_driver_lists_changelogs_and_upgrade_adds_new_ones`, `test_init_merge_driver_outside_git_lists_no_changelog`, and the `/CHANGELOG.md` assertion in `test_git_merge_and_rebase_keep_bullets_appended_on_both_branches` |
| 13 | a file opted in outside the block | `test_a_file_given_the_attribute_outside_the_block_gets_its_bullets_merged` |
| 14 | failure in the list stage falls back; T004 tests unchanged | `test_the_driver_falls_back_to_git_merge_file_when_the_list_stage_fails`, and the 47 T004 tests |

## Implementation evidence

- **Tests first.** Commit `781e951` added the tests with a `merge_lists` stub that returned its
  inputs and was already called by `merge_text`, and no changelog lines in `attribute_paths`:
  `uv run pytest -q tests/test_merge_driver.py` gave `18 failed, 59 passed`. The new tests that
  already passed describe what git does anyway, and they must keep passing once lists are merged:
  the seven lists-left-to-git cases, different edits and edit/delete marked, both sides moving a
  bullet identically, the fallback when the list stage raises, and `init` outside git.
  Three tests came after that commit, from the changes at implementation: the empty base section,
  which fails with `merge_lists` returning its inputs (first mutation below); the `a fence inside a
  bullet` case, which describes git's own result; and the scanner test, which calls `_lists`
  directly.
- **Mutation checks** on the implementation (restored afterwards):
  - `merge_lists` returning its inputs: 18 failed, including every real `git merge`/`rebase` bullet
    test (`CONFLICT (content): Merge conflict in CHANGELOG.md`);
  - moves on the other side ignored (`moved_other = set()`): 5 failed, including the real-rebase
    regression test;
  - no edit pairing: 4 failed. Two different edits of one bullet became two bullets, and the
    edit/delete case and the repeated-text guard stopped holding.
- **Full suite:** `uv run pytest -q` gave `821 passed in 96.01s`, which is
  788 on T004's branch plus the 33 new tests. The `lint` check has no command configured in
  `.taskrail/config.toml`, so it was not run.

## Verification

A throwaway repository under `/tmp` (deleted afterwards), git 2.55.0, running this branch's code
through the committed wrapper. `taskrail init --integration claude --merge-driver` ran from this
branch's source, then the pin was set to `local:taskrail-src`, a git-ignored symlink to
the checkout's root, so git invoked the real `.taskrail/bin/taskrail merge-driver` with no
`TASKRAIL_BIN`. The changelog was `tools/app/CHANGELOG.md`. The behaviour matched the plan; no gap
was found.

**Install.** `init` reported `created .gitattributes` and `created git config merge.taskrail`, and the
block held `/tools/app/CHANGELOG.md merge=taskrail` after the backlog and index lines. Later,
`libs/core/CHANGELOG.md` was created and `.taskrail/bin/taskrail upgrade` reported
`updated .gitattributes`, adding `/libs/core/CHANGELOG.md merge=taskrail` and keeping the driver
definition.

**1. `git merge`, both sides append one bullet.** `git merge --no-edit a` → `Merge made by the 'ort'
strategy.`, exit 0:

```
- X first change.
- Y second change,
  wrapped.
- B from main.
- A from branch a.
```

**2. The moved bullet, `git rebase`.** Branch `e` added N2 at the top of `## Unreleased`, then moved it
to the very end in a second commit; `main` then added M2 at the top and P2 at the end. On `e`,
`git rebase main` → `Successfully rebased and updated refs/heads/e.`, exit 0, both commits replayed,
N2 once (`grep -c` gives 1):

```
- M2 from main at the top.
- X first change.
- Y second change,
  wrapped.
- A from branch a.
- P2 from main at the end.
- N2 the branch's own bullet,
  on two lines.
```

For comparison, the same rebase after `git config --local --remove-section merge.taskrail` stopped on
the first commit with `CONFLICT (content): Merge conflict in tools/app/CHANGELOG.md` and exit 1:
M2 against N2 at the top. That is the conflict whose "keep both" resolution left the bullet twice
once the move was replayed. An earlier run of the same shape, with the move landing in the middle of
the list, also rebased cleanly with N once, placed after the bullet it followed on the branch.

**3. A real conflict.** Both sides reworded bullet X, and branch `c` also appended C. `git merge
--no-edit c` exited 1 with the changelog unmerged and markers around that bullet only:

```
- M from main at the top.
<<<<<<< HEAD
- X first change, as main says.
=======
- X first change, as branch c says.
>>>>>>> c
- Y second change,
  wrapped.
- B from main.
- P from main at the end.
- C from branch c.
- A from branch a.
```

## Evidence

Throwaway files under `/tmp`, git 2.55.0, deleted afterwards.

**E1 — `git merge-file` on changelog bullets today.** A `# Changelog` with `## Unreleased` and a
`## 0.1.0` section below it:

```
### case 1: both append at the end
# Changelog

## Unreleased

- X one.
- Y two.
<<<<<<< current
- A mine.
=======
- B theirs.
>>>>>>> other

## 0.1.0

- First release.
exit=1
### case 2: other moves N to the end; current added M at the top
# Changelog

## Unreleased

<<<<<<< current
- M mainline.
- N branch bullet,
  wrapped.
=======
>>>>>>> other
- X one.
- Y two.
- N branch bullet,
  wrapped.

## 0.1.0

- First release.
exit=1
### case 2 resolved by keep-both (--union)
# Changelog

## Unreleased

- M mainline.
- N branch bullet,
  wrapped.
- X one.
- Y two.
- N branch bullet,
  wrapped.

## 0.1.0

- First release.
### case 3: other moves N to the end; current appended P at the end
# Changelog

## Unreleased

- M mainline.
- X one.
- Y two.
<<<<<<< current
- P later.
=======
- N branch bullet,
  wrapped.
>>>>>>> other

## 0.1.0

- First release.
exit=1
### case 3 --union
# Changelog

## Unreleased

- M mainline.
- X one.
- Y two.
- P later.
- N branch bullet,
  wrapped.

## 0.1.0

- First release.
```

Case 2 is this run's real duplicate: "keep both" at the top conflict keeps the current side's N,
while the other side's N at the end is already merged in.

**E2 — The ordering rule, prototyped** over one-letter keys (a throwaway script, not committed):

```
both append                                   base=XY current=XYA other=XYB -> XYAB
other moves N to end, current adds M at top   base=NXY current=MNXY other=XYN -> MXYN
other moves N to end, current appends P       base=NXY current=NXYP other=XYN -> XYPN
current moves N to end, other appends P       base=NXY current=XYN other=NXYP -> XYPN
both move N to end                            base=NXY current=XYN other=XYN -> XYN
other deletes X, current appends              base=NXY current=NXYA other=NY -> NYA
```
