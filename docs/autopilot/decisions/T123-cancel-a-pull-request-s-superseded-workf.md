# T123 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T123-cancel-a-pull-request-s-superseded-workf.md` and its commit
`0fe87ca` (artifact and index row alone); both workflows on `main`; `install.workflow()` and how it
renders its branch list from each backlog's `mainline`; the managed copy's sha256 matching its
recorded digest; and the three existing offline shape tests over the generated workflow.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The group key | **`${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref \|\| github.run_id }}`** · `workflow-ref` with `cancel-in-progress: true` · `workflow-ref` with a conditional `cancel-in-progress` · `head_ref \|\| run_id` · `pull_request.number \|\| run_id` | **as recommended** | The lane found the fact that decides this, and it is the one the obvious idiom gets wrong: **a concurrency group holds at most one running and one pending run, and a newly queued run cancels the pending one even with `cancel-in-progress: false`.** So keying pushes on the ref with a conditional cancel still drops a mainline run — after three quick merges, merge 2's pending run is replaced by merge 3's, and that commit never gets a result. Keying a push on `run_id` makes it a group of one, so no mainline run is ever cancelled or replaced. `head_ref` lets two fork pull requests with the same branch name cancel each other. The pull-request-number form is equivalent; the ref form is kept because the row asks to key on the workflow and the ref. |
| 2 | The generated template gets the block too | **yes, the same lines verbatim, no new parameter** · `ci.yml` only | **yes** | The block names no branch, so it behaves the same for a mainline called `trunk` or for several mainlines rendered into `branches: [...]`: every push gets its own `run_id` group and every pull request its own `refs/pull/N/merge` group. The waste the row describes exists in every consumer, and fixing it only here would make this repository's two workflows behave differently for no reason. Consumers pick it up with `upgrade`; one whose workflow was edited locally is told the lines by the changelog, the way T120 did. |
| 3 | `cancel-in-progress` unconditional? | **`true`** · `${{ github.event_name == 'pull_request' }}` | **`true`** | Under decision 1 a push's group only ever holds its own run, so the protection lives in the key alone. An expression here would guard a case that cannot happen, and — worse — would suggest to the next reader that this line, not the key, carries the protection. KISS. |
| 4 | Documentation and tests | **one §9 *Extras* sentence giving the key and why it is not the plain ref; one changelog bullet; one offline test asserting the literal block in `init` output and in `workflow(["trunk"])`** | **as recommended** | §9 already records the template's other deliberate properties with their reasons. The `trunk` case is what makes the test prove the block names no branch. GitHub's runtime cancellation cannot be tested offline or from a lane; the pull request's own runs are its first real exercise, and the write-up should say so rather than claim more. |

Given with the answers: the sentence in §9 must carry the pending-run fact, not only the key. It is
the reason the plain-ref idiom is wrong here, and without it a later reader will "simplify" the key
back to `github.ref` and reintroduce the dropped mainline run.
