# T089 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: `docs/spikes/T089-decide-whether-to-split-design-md-by-top.md` at the lane's frame commit,
the diff range against the base (the artifact and one appended index row), `taskrail checks T089`
re-run in the lane's worktree (`no checks` … `passed`), `taskrail validate` in that worktree (81
tasks, 0 errors), and the task row's premise, which holds: `DESIGN.md` is 1844 lines and
`read_first` names it.

The lane corrected the orchestrator's brief: `CLAUDE.md` is 121 lines *including* the design
principles section, so "121 at the mainline and grew by 17" double-counted. The correction is
accepted and the figure to use is 121.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Does the fourth option — leave the file whole, change what `read_first` names — stay in scope? | keep it, costed like the others · drop it · mention it without a recommendation | **keep it, costed alongside the others, with adoption as follow-up work** | As recommended. It attacks the stated problem — what the orchestrator loads at every gate — at the lowest cost to the existing corpus, and excluding it would bias the comparison toward splitting. Adoption would change `.taskrail/config.toml`, outside the touch map, so it can only become a follow-up task. |
| 2 | How hard is the evidence bar for "what a gate actually needs"? | citation census, labelled a proxy · instrumented measurement · decide on section sizes | **the citation census, stated plainly as a proxy** | As recommended: it measures what gate answers *referred to*, a lower bound on what was read, and a section can be needed and never cited. An instrumented measurement is beyond 2 points and beyond the touch map; deciding on size alone is reasoning instead of measuring, which the frame rules out. |
| 3 | Is the scratchpad prototype worth the time inside a 2-point box? | yes, strictly bounded · skip it, use the citation census | **yes, strictly bounded: build the map and rewrite the citations mechanically in a scratchpad copy for the counts, no polished documents** | As recommended. The size of the rewrite is the number that decides this spike, and estimating it would repeat the error T087 had to correct. Nothing from the prototype enters the repository. |

Instructions given with the answers: continue into `investigate` (gate `none`, no commit). Use 121
for `CLAUDE.md`. Add the orchestrator's own gate reading in this run as a second, labelled data
point for E2-E4: answering the `frame` and `decide` gates of T087 and the `frame` gates of T088 and
T089 required §1-§4, §5.6, §8, §9, §10, §11 and §12.6, and did not require §7's command table or the
rest of §12 — one orchestrator, one run, four gates, not a general measurement.

## escalated to the human

`spike:decide` is in this repository's `[autopilot].escalate_gates`, so the verdict went to the
human. Reviewed before escalating: the artifact at commit 02c1e56, the lane's commits against
`origin/main`, `taskrail checks T089 --stage decide` and `taskrail validate` (82 tasks, 0 errors),
and an independent reproduction of the two load-bearing measurements — `grep -rn 'DESIGN'
src/taskrail/skills/ src/taskrail/integrations/` returns nothing, and the citation census over the
67 past decision records reproduces exactly (§12 in 36, §7 in 28, §6 in 13, §4 in 9, §5 in 8, §8 in
7, §13 in 6). `read_first` is a tuple of paths in `config.py:79`, so it cannot name a section, as
the lane states.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Split `DESIGN.md`, or leave it whole? | accept in full: no split, add a reading map (T093), `read_first` untouched · accept without T093 · split by topic · drop it from `read_first` | **accept in full** | As recommended. Two of the task row's three premises did not survive measurement: `read_first` is read once before the first dispatch, not at every gate, so the cost is per run rather than per gate; and the sections a split would move (§7, §12) are the ones past gate answers cite most. A full split was counted, not estimated: 149 internal rewrites, ~80 in maintained files and 1400 citations stranded in 116 documents this repository does not rewrite, for a saving measured at or below zero at this repository's run size, where the crossover is near three tasks and `max_lanes` is 3. |

Answered by the human (the repository's maintainer), through the orchestrator, at the `decide`
gate of run 20260918-1.

Noted for the record: the task row's premise "the orchestrator reads it whole at every gate" was
written by the orchestrator when the row was created, and the lane disproved it from the shipped
skill, `references/gate-review.md` and §12.6. The row is left as written — it is the question that
was asked — and the artifact records the correction.

## rebase after T087 merged

T087 was squash-merged into `main` as 4a956c4, and `autopilot merged T087 --cleanup` proved the
merge by content and removed its branch and worktree. This branch was stacked on it, so the
orchestrator rebased it while the lane was stopped at the `frame` gate:

```
git rebase --onto origin/main 45137368de55c2d6b55ea62198e0adae1f98af23
```

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts during the rebase | resolve known classes · stop | **none arose** | The lane's single commit touches only its own artifact and one appended index row; `main` already carried T087's rows. |

After the rebase: one commit ahead of `origin/main`, `git diff --check` clean, `taskrail checks T089`
passed, `taskrail validate` reports 81 tasks and 0 errors. Note for the write-up: the base is now
`origin/main`, so `DESIGN.md` on this branch is the merged mainline version.

## Conflict handling agreed for all lanes

Run 20260918-1, extended by the human to T090, T091 and T092 after T087 merged.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | one artifact per lane · shared edits | **Each lane edits only its own `docs/spikes/T0NN-*.md`, one appended row in `docs/spikes/README.md`, and its own rows in `TODO.md` through the CLI** | T088 and T089 run in parallel on the same artifact directory; nothing else is shared. `DESIGN.md` is this task's subject but stays unedited: the spike decides whether to split it, it does not split it. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **Known classes only: appended index rows (class 2) and backlog rows (class 1)** | Both are resolved by the orchestrator at hand-off, and `autopilot status` reports them as known overlaps. |
| 3 | May a lane edit `CLAUDE.md`, `src/taskrail/skills/` or code? | allow · forbid in E08 | **Forbidden for the spikes of this run** | T088 and T089 are spikes: they decide, they do not adopt. Adoption is T090 and T091, which are separate tasks. |
