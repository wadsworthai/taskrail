# T040 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

T040's row exists only on T004's branch, which is finished and published but not merged, so the lane
branched from `origin/T004-add-a-git-merge-driver-for-status-cells`; its claim records the stacked
base with dependency T004.

## plan gate

Reviewed: the plan in `docs/features/T040-merge-appended-changelog-bullets-without.md` (commit
`a214fbf`), its fourteen acceptance criteria, and the lane's probes: `git merge-file` conflicts when
both sides append a bullet, and "keep both" duplicates a bullet one side moved — the exact failure
this run's orchestrator hit — while the prototyped ordering rule gives the expected lists.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Which files | every `CHANGELOG.md` in the block, others opt in by hand · config key · manual only · `init --changelog` | **as recommended** | No new configuration or installer surface; the driver stays opt-in per clone. |
| Q2 | List merging on every file the driver receives | yes · changelog paths only | **yes** | Index and backlog files hold lists too; ambiguous cases fall back to git. |
| Q3 | Tight lists by heading path and position, equal counts | yes · loose lists too | **yes** | Structure that cannot be matched unambiguously is left to git. |
| Q4 | Moved bullets | moving side's position, current side's when both moved · conflict | **as recommended** | A move is intent; repeating it on both sides agrees. |
| Q5 | Edits | paired inside equal-count replace blocks, different edits and edit/delete marked · no pairing | **as recommended** | Without pairing, two edits of one bullet silently become two bullets. |
| Q6 | Appended order | current side first · other first | **current first** | Same rule as rows. |
| Q7 | Structure | second `merge_lists` stage after unchanged `merge_tables`, driver name unchanged · combined pass · rename | **as recommended** | Leaves T004's code and every clone's config as they are. |
| Q8 | README half-sentence | add · DESIGN and CHANGELOG only | **add** | The README is where a consumer reads what `--merge-driver` does. |

Plan approved.

## implement gate

Reviewed: commits `781e951` (tests against a stub) and `fa7ec7f` (`merge_lists`, `_lists`, `_edits`,
`_moved`, `_merge_bullets` and `changelog_paths` in `mergedriver.py`; DESIGN.md §7.4 and §12.8;
README; CHANGELOG). Re-ran `tests/test_merge_driver.py` in the lane's worktree: 80 passed; the lane's
full suite gave 821. Eighteen tests failed against the stub, including every real git merge and
rebase of bullets; three deliberate breakages (no list stage, ignored moves, no edit pairing) each
failed the tests that cover them. The regression test replays this run's real case with `git rebase`
and fails without the driver. This checkout has no `merge.*` config and no `.gitattributes`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve, with an empty base section merged, a fence inside a bullet left to git, and thematic breaks not bullets | approve · strict equal counts | **approve** | The empty `## Unreleased` after a release is the most common case; the other two keep ambiguous input with git. |
| 2 | `git ls-files` on epic commands; the `X Y P N` ordering asymmetry | keep · change | **keep** | One cheap call per epic command; the order is deterministic and keeps each bullet once. |

## verify and close

The verify stage ran the driver through the wrapper in a throwaway repository: `upgrade` added a new
`CHANGELOG.md` to the block; a merge where both sides appended a bullet came out clean; this run's
real case — a branch that adds its bullet at the top and then moves it to the end, rebased onto a
mainline that added bullets at the top and end — rebased cleanly with the bullet once, and the same
rebase without the driver conflicted; two different edits of one bullet were marked alone. The
branch stays stacked on `origin/T004-add-a-git-merge-driver-for-status-cells` (`8a9a37f`) until T004
merges; then the orchestrator moves it with `git rebase --onto origin/main 8a9a37f`.

## rebase after T004

T004 was squash-merged into `main` as `fff3fe6`. The orchestrator moved the branch off T004's branch
with `git rebase --onto origin/main 8a9a37f`, replaying only this task's eight commits.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How to rebase a stacked branch after its dependency's squash merge | `--onto` the recorded fork point · plain rebase | **`--onto 8a9a37f`** | A plain rebase would replay T004's commits against their squashed copy; the fork point is the claim's recorded `base.commit`. |

No conflicts. After the rebase: `TODO.md` differs from `main` only in T040 `✅`, `pytest -q` passes,
`taskrail validate` 0 errors, `upgrade` reports nothing to create or update, and `show T040` reports
base `origin/main` with no dependency.
