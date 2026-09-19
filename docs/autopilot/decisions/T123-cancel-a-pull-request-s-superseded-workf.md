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

## implement gate

Reviewed: commit `e128f30` and the diff `db43d45..HEAD` — the block and its comment in `ci.yml` and
in `workflow()`, one test, the regenerated managed workflow and its digest, the artifact; the test's
recorded failure before the template changed; the real `init` into a scratch repository whose
mainline is `trunk`; the YAML parse of both files; the `upgrade` report touching only the workflow;
`taskrail checks T123 --stage implement` (1,257 passed); and, recomputed by the orchestrator, the
regenerated workflow's sha256 matching its recorded digest (`9877e739…`).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The four scope answers were applied as given. |
| 2 | The three-line comment above the block, in both workflows | **keep it** · drop it | **keep it** | It carries the pending-run fact into every consumer's generated file, which is exactly where someone is most likely to "simplify" the key back to the plain ref. The scope gate required that fact wherever the key is written down; a comment next to the key is the most direct place. The test asserting the block and not the comment is right: the comment's wording can change, the block's cannot. |
| 3 | The `trunk` scratch repository | **accept** | **accept** | `branches: [trunk]` alongside an unchanged concurrency block is the proof, on real output, that the block names no branch. |

## close

Reviewed: the whole diff against the merge base — the block and its comment in both workflows, one
test, the regenerated managed workflow and digest, the §9 sentence carrying the key and the
pending-run fact, one changelog bullet printing the block for locally edited workflows, the artifact,
two index rows and T123's `✅`; `taskrail validate` (4 tasks, 0 errors). No rebase needed: `main`
has not moved since `df31678`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | **`ci` / `install`** · `chore` / `install` · `ci` / `repo` | **`ci` / `install`** | The change is continuous-integration behaviour, and the part that matters beyond this repository is the template every consumer installs, which lives in `src/taskrail/install.py`. T120 was `chore` because it hardened a permission; this changes when runs execute. |
| 2 | What the pull request itself must be watched for | **its own runs** | **recorded** | GitHub's cancellation cannot be tested offline. A second push to this pull request should cancel the first push's `ci` and `taskrail` runs, and each run on `main` after the merge should complete. |

## rebase after T122 merged

`main` advanced to `245f484` (T122) while this branch was in review. It was rebased onto
`origin/main` with three conflicts, all known classes: the decisions index (appended rows), the
`CHANGELOG.md` bullets (kept both, this branch's on top), and `TODO.md` (united by ID, `✅` wins).
`upgrade` re-run in the rebased worktree reports every managed file up to date, so the workflow and
its digest are still consistent. `taskrail checks T123` passed after the rebase and `taskrail
validate` reports 6 tasks, 0 errors. Re-published with a lease.

## rebase after T121 merged

`main` advanced to `0fb3fe0` (T121). Rebased again with two known-class conflicts (the decisions
index and `CHANGELOG.md`); `taskrail checks T123` passed afterwards. Re-published with a lease.

## rebase after T124 merged

`main` advanced to `faad84e` (T124). Rebased with three known-class conflicts (the decisions index,
`CHANGELOG.md`, `TODO.md`); `upgrade` reports every managed file up to date; `taskrail checks T123`
passed with 1,270 tests. Re-published with a lease.

## rebase after T126 merged

`main` advanced to `881ae6f` (T126). Rebased with known-class conflicts only (index rows and
`TODO.md`); T126 changed `src/taskrail/autopilot/merged.py`, which this branch does not touch.
`taskrail checks` passed afterwards. Re-published with a lease.
