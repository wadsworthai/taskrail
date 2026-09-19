# T123 — Cancel a pull request's superseded workflow runs when a new one is queued

Kind: chore · Epic: E09 · Depends on: — · Branch: `T123-cancel-a-pull-request-s-superseded-workf`

## Goal

Every push to a pull request queues a fresh run of `ci.yml` and `taskrail.yml` while the runs
for the previous push keep going. The superseded runs burn runner time on a commit nobody will
merge, and the checks a reviewer sees race each other. Give the workflows a `concurrency` group
so a new run for a pull request cancels that pull request's older one — without ever cancelling
or dropping a run on the mainline after a merge.

## How GitHub's concurrency behaves (the facts the key rests on)

- `github.ref` is `refs/pull/<number>/merge` for a `pull_request` event — unique per pull
  request, including one opened from a fork whose branch shares a name with another — and
  `refs/heads/main` for a push to `main`.
- `github.head_ref` is set only for `pull_request` events, and holds the head *branch name*, which
  two pull requests from different forks can share.
- In a concurrency group, at most one run is in progress and one is pending. **A newly queued run
  replaces the pending one even when `cancel-in-progress` is false**: the pending run is
  cancelled. `cancel-in-progress: true` additionally cancels the one already running.
- `github.run_id` is unique per workflow run.

The consequence is the trap the row names. With the common `${{ github.workflow }}-${{ github.ref }}`
group, every push to `main` shares one group. Unconditional `cancel-in-progress: true` cancels the
mainline run of merge *n* when merge *n+1* lands. Making `cancel-in-progress` conditional
(`${{ github.event_name == 'pull_request' }}`) does not fully fix it: three merges in quick
succession still leave merge 2's run pending, and merge 3's run then replaces and cancels it. So
merge 2's commit on `main` never gets a result. The only way to guarantee that a mainline run is
never cancelled is to give each push its own group.

## Change set

- `.github/workflows/ci.yml`: a workflow-level block between `permissions:` and `jobs:`:

  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}
    cancel-in-progress: true
  ```

- `src/taskrail/install.py`, `workflow()`: the same four lines in the same position, verbatim
  (decision 2). They are inside an f-string, so the braces are doubled in the source
  (`${{{{ … }}}}`) and render as `${{ … }}`. No new parameter.
- `tests/test_install.py`: one test after
  `test_github_workflow_grants_the_job_only_read_access_to_contents`, asserting the literal block
  in the generated workflow (decision 4).
- `.github/workflows/taskrail.yml`: regenerated with this worktree's own
  `.taskrail/bin/taskrail upgrade`, never hand-edited. The file is unedited today: its sha256
  `eb05606e…181d70f` equals the digest in `.taskrail/installed.json`, so `upgrade` rewrites it
  without `--force`.
- `.taskrail/installed.json`: the workflow's digest, rewritten by the same `upgrade` run.
- `DESIGN.md` §9 *Extras*: one sentence after the permissions clause, recording the group key and
  why it is not the plain ref (decision 4).
- `CHANGELOG.md`: one bullet under *Unreleased* (decision 4).
- `docs/chores/T123-…md` and `docs/chores/README.md`: this write-up and its index row.

## Decisions needed

1. **The group key.** Recommendation:
   `${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}`.
   - Pull request #42 in `ci.yml` → `ci-refs/pull/42/merge`. Every push to that pull request
     shares the group, so the newer run cancels the older one.
   - Push to `main` → `ci-<run_id>`, e.g. `ci-17712345678`. The group is unique to that run, so
     nothing ever cancels it or replaces it while it is pending. A merge is never cancelled by the
     next merge, and every commit on `main` gets its result. That result is what T108's
     required checks and the `taskrail.yml` validate run on the mainline rely on.
   - `github.workflow` keeps `ci` and `taskrail` in separate groups, so a pull request's `ci` run
     never cancels its `taskrail` run.
   - The `a && b || c` form is GitHub's ternary idiom. It is safe here because `github.ref` is
     never empty.

   Alternatives:
   - (a) `github.workflow`-`github.ref` with unconditional `cancel-in-progress: true`: cancels
     mainline runs, which the row forbids.
   - (b) The same group with `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`:
     still cancels a *pending* mainline run on the third quick merge, as shown above. It also
     serialises mainline runs.
   - (c) `github.head_ref || github.run_id`, the idiom most often copied: two pull requests from
     forks with the same branch name (both `main`, say) would share a group and cancel each
     other's runs.
   - (d) `github.event.pull_request.number || github.run_id`: equivalent to the recommendation.
     The ref form is preferred only because the row asks for a key on "the workflow and the ref".

2. **Whether the generated template gets the same block.** Recommendation: **yes, the same four
   lines**. It runs `validate` in every consuming repository, on the same two triggers, and wastes
   runner time the same way. The key names no branch, so it behaves the same in a repository whose
   mainline is `trunk` or `develop`, or one with several backlogs whose mainlines the template
   renders into `branches: [...]`: every push to any of them gets its own `run_id` group, and every
   pull request its own `refs/pull/N/merge` group. The fixed text adds no parameter to
   `workflow()`. Consumers pick it up with `taskrail upgrade`. One whose workflow is edited
   locally is reported `edited locally; --force replaces it` and adds the lines by hand, as the
   CHANGELOG bullet will say.

   Alternative: change `ci.yml` only. This is a smaller diff, but it leaves the waste the row
   points at in every consumer, and the two workflows in this repository would behave differently
   on the same push.

3. **Whether `cancel-in-progress` is unconditional.** Recommendation: **unconditional `true`**.
   Under decision 1's key, a push's group only ever holds that one run, so `true` can never cancel
   a mainline run, and an expression would guard a case that cannot happen (KISS). The mainline
   guarantee lives in the key alone, and the DESIGN.md sentence says so, so a later reader does
   not "simplify" the key back to the plain ref.

   Alternative: `${{ github.event_name == 'pull_request' }}`. It is redundant with the key, and it
   suggests the protection lives in this line rather than in the key.

4. **Documentation and test.** Recommendation:
   - **`DESIGN.md` §9 *Extras***: one sentence beside the `fetch-depth`, tag and permissions
     reasons. The block is the fourth deliberate property of the template, and its key is exactly
     the kind of line someone would "fix" to the common idiom without the reason in front of them.
   - **`CHANGELOG.md`**: one bullet, because the file consumers get changes.
   - **Test**: one offline shape test over `install.workflow(...)` output via `init
     --github-workflow`, asserting the literal four-line block, in the style of T120's
     permissions test. A literal assertion rather than "some concurrency key exists" pins the key
     itself: a regression to `github.ref` alone would still pass a looser test. A second
     assertion renders `workflow(["trunk"])` and checks that the block is identical and names no
     branch, which covers the non-`main` mainline question offline.
   - **No test over `ci.yml`**: it is hand-written, and no existing test reads it. What a test
     cannot check offline is GitHub's runtime cancellation behaviour, and nothing here tries to.

## Out of scope

- Any flag or config key to turn the block off or change its key (YAGNI). The row asks for one
  fixed behaviour.
- Branch protection, required-check settings, or other GitHub-side configuration.
- Other workflow changes: triggers, `paths` filters, timeouts, caching.
- `README.md`: its line says what the extra adds, not how the job is configured.
- Anything else `upgrade` would rewrite. If the run touches a file outside this change set, this
  lane stops and asks.
- `src/taskrail/autopilot/` (T121) and `src/taskrail/ids.py` / `cli.py` (T122).

## Verification

- The new test is observed **failing before the template change** and passing after.
- `init --github-workflow` is run for real into a scratch repository. The file is read back and
  parsed as YAML, to confirm that `concurrency` is top-level with the expected `group` string and
  `cancel-in-progress: true`, and that the rest is unchanged.
- `ci.yml` is parsed as YAML after the edit, to check that it still loads and that the block is
  top-level.
- This repository's copy is regenerated with `.taskrail/bin/taskrail upgrade --json` from the
  worktree. The report and `git status` are recorded, confirming that only the workflow and the
  manifest changed, and the new sha256 is compared with the recorded digest.
- `taskrail checks T123 --stage implement` (`uv run pytest -q`) and `.taskrail/bin/taskrail
  validate`.
- GitHub's runtime cancellation cannot be exercised from a lane (no push). The pull request's own
  runs are the first real exercise. This is stated in the hand-off, not claimed.

The scope gate approved all four decisions as recommended, and added one requirement: the §9
sentence, and any comment above the block, must state the pending-run fact, not only the key.
Without that fact, a later reader could "simplify" the key back to `github.ref`.
A three-line comment above the block in `ci.yml` and in the template states it.

Results:

- **The test was observed failing first.** With
  `test_github_workflow_cancels_a_pull_request_s_superseded_run_but_never_a_mainline_one` added
  and the template untouched, `uv run pytest tests/test_install.py -q -k never_a_mainline_one`
  failed with `AssertionError: assert "\nconcurrency:\n  group: ${{ github.workflow }}-${{
  github.event_name == 'pull_request' && github.ref || github.run_id }}\n  cancel-in-progress:
  true\n" in '# Managed by taskrail: …'` and reported `1 failed, 62 deselected`. After the
  template change, the whole module reported `63 passed in 2.94s`.
- **`init --github-workflow` run for real** into a scratch repository whose branch is `trunk`,
  with this branch's source.
  - `created` listed `.taskrail/config.toml`, `TASKRAIL.md`, `.taskrail/bin/taskrail`,
    `.github/workflows/taskrail.yml` and `.gitignore`.
  - The workflow says `branches: [trunk]`.
  - Parsed with PyYAML, both that file and this repository's `ci.yml` have the top-level
    `concurrency: {"group": "${{ github.workflow }}-${{ github.event_name == 'pull_request' &&
    github.ref || github.run_id }}", "cancel-in-progress": true}` beside
    `permissions: {"contents": "read"}`.
  - Their jobs are unchanged (`['validate']` and `['test']`).
- **This repository's copy was regenerated** with the worktree's `.taskrail/bin/taskrail upgrade
  --json`.
  - `updated` was `.github/workflows/taskrail.yml` alone.
  - The config, `TODO.md`, the wrapper and all nine skill files came back `unchanged`.
  - `created`, `skipped`, `removed` and `notes` were empty.
  - `git status --short` shows only the change set: `ci.yml`, `taskrail.yml`,
    `.taskrail/installed.json`, `install.py` and `test_install.py`.
  - The regenerated file's sha256 `9877e739bc3cf5c43c0dd6a5ad9f67a54c846ebd6d203d85e599f03b2b97a7a9`
    equals the digest `upgrade` recorded.
- `taskrail checks T123 --stage implement`:
  - `test` (`uv run pytest -q`) passed with `1257 passed in 158.73s`.
  - `lint` is not configured.
  - Overall: `passed`.
- `.taskrail/bin/taskrail validate` printed `4 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- **Not tested, and not claimed:** whether GitHub actually cancels the right runs at runtime. That
  cannot be tested offline or from a lane, which never pushes. This pull request's own runs are
  its first real exercise: a second push to it should cancel the first push's `ci` and `taskrail`
  runs, and the runs on `main` after the merge should each complete.
