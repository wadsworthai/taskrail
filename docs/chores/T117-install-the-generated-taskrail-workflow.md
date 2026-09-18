# T117 — Install the generated taskrail workflow in this repository

Kind: chore · Epic: E06 · Depends on: T116 · Branch: `T117-install-the-generated-taskrail-workflow`

## Goal

This repository runs taskrail on its own backlog but has never installed the
`--github-workflow` extra: `.taskrail/installed.json` records `"extras": {}`, so
`.github/workflows/taskrail.yml` was never written and nothing runs `taskrail validate` in CI.
T108 added `ci.yml` for the test suite and left `validate` to the generated workflow by decision
(T108 decision 1), opening this task as the follow-up. T116 has since pinned action tags in the
template that actually resolve, which was the precondition for installing it.

Run `taskrail init --github-workflow` in this repository and commit exactly what it writes.

## Change set

- `.github/workflows/taskrail.yml` — **created** by `init`, byte for byte as the template in
  `src/taskrail/install.py` generates it. Managed by taskrail: `init` and `upgrade` rewrite it,
  so it is never hand-edited here.
- `.taskrail/installed.json` — **updated** by `init`: `extras` gains `"github_workflow": true`,
  and `files` gains the workflow's path and content hash.
- `CLAUDE.md` — one Layout line updated (see decision 4).
- `docs/chores/T117-…md` and `docs/chores/README.md` — this write-up and its index row.

No other file changes; the trial run confirmed that (evidence below).

## Decisions needed

1. **Exactly what `init --github-workflow` writes here.** A real run in this worktree created
   one file and updated one, and left everything else — including `.taskrail/bin/taskrail`, which
   T118 owns — unchanged. Nothing unexpected. Recommendation: **commit exactly that, unmodified**.
2. **Two workflows or one.** Recommendation: **keep `ci.yml` and `taskrail.yml` separate**.
   `taskrail.yml` is a managed file that `taskrail upgrade` rewrites from the template, so
   anything merged into it by hand would be lost at the next upgrade, and merging the other way
   would mean hand-editing a managed file. Installing the extra here is also how this repository
   dogfoods what its own consumers get. The overlap is two steps — `actions/checkout` and
   `astral-sh/setup-uv`, both cached, seconds each — and the two jobs differ in what they need
   anyway: `taskrail.yml` needs `fetch-depth: 0` for `validate`'s reopen check, `ci.yml` needs a
   3.11/3.14 matrix that `validate` has no use for. Running them as separate workflows also runs
   them in parallel. Alternatives: (a) add a `validate` job to `ci.yml` and do not install the
   extra — loses the dogfooding and reverses T108 decision 1; (b) install the extra and delete
   `ci.yml`'s test job — not on the table, different jobs.
3. **The required check names.** The generated workflow has one job, `validate`, with no `name:`,
   so the check GitHub reports is **`validate`**, under the workflow named `taskrail`. Together
   with T108's `test (3.11)` and `test (3.14)`, the checks to require on `main` become those three.
   Recommendation: **name them in this write-up, as T108 did, and do not configure branch
   protection** — the check cannot be marked required before the workflow has run once on `main`,
   which is after this merges, and branch protection is the human's to set, not a lane's.
4. **The `CLAUDE.md` Layout line.** T108 added
   `.github/workflows/     # this repository's own CI: the test suite on 3.11 and 3.14`, which
   describes one workflow and will be wrong the moment this merges. Recommendation: **update that
   one line** to name both and mark the generated one as managed, and change nothing else in
   `CLAUDE.md`.
5. **Follow-up: the generated workflow sets no `permissions`.** `ci.yml` sets
   `permissions: contents: read`; the template in `src/taskrail/install.py` sets none, so the
   workflow gets the repository's default `GITHUB_TOKEN` permissions, which are wider than
   `validate` needs. Fixing that means editing the template, which T118 owns right now and which
   is out of this task's scope either way. Recommendation: **open a follow-up task** in the docs
   stage and leave the generated file untouched here.

## Out of scope

- `src/taskrail/install.py` — the workflow template itself and the wrapper template, both
  including the tags T116 pinned and the missing `permissions` block. T118 owns this file.
- `.taskrail/bin/taskrail` — T118 regenerates it; `init` left it unchanged here.
- `.github/workflows/ci.yml` — T108's file, not touched.
- `src/taskrail/cli.py` — T119 owns `cmd_done`.
- Configuring branch protection or required checks on GitHub.
- `CHANGELOG.md` — it records user-facing taskrail changes, and this changes only this
  repository's own installation; earlier repository-only chores (T058, T069, T090, T108) have no
  bullet either.

## Verification

- `init --github-workflow` run for real in this worktree, with its `--json` report and the
  resulting `git status` and `git diff` recorded below.
- The written file matches the template byte for byte: its sha256 equals the hash `init` recorded
  in `.taskrail/installed.json`.
- Re-running `init --github-workflow` reports the workflow as `unchanged`, proving it is
  idempotent and that the committed file is what `upgrade` would keep.
- The workflow parses as YAML and its keys are the ones GitHub expects.
- The command the workflow runs is exercised for real: `.taskrail/bin/taskrail validate` from the
  worktree root, which is what the job's only `run` step does.
- `taskrail checks T117` (`test`: `uv run pytest -q`) passes; `lint` is not configured here.

Results: recorded at the implement stage.
