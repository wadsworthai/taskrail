# T108 — Add continuous integration that runs the test suite

## Goal

Run this repository's own test suite on every pull request and on every push to `main`. Today
nothing does: `init --github-workflow` generates `.github/workflows/taskrail.yml` for the
repositories that install taskrail — and this repository never installed that extra
(`.taskrail/installed.json` records `"extras": {}`), so it has no workflow at all, and a pull
request that breaks the suite is caught only by whoever remembers to run `pytest`.

The shape is the one the sibling repository named in the task description merged, so the two stay
recognisable: one workflow, one job, a two-leg Python matrix, actions pinned to exact release
tags, and a single step — `uv run --locked pytest`. The suite is the gate: no lint, type check,
build or coverage, and nothing allowed to fail.

## Change set

- `.github/workflows/ci.yml` — new file, the whole change:

  ```yaml
  name: ci

  on:
    pull_request:
    push:
      branches: [main]

  permissions:
    contents: read

  jobs:
    test:
      runs-on: ubuntu-latest
      strategy:
        matrix:
          python: ["3.11", "3.14"]
      steps:
        - uses: actions/checkout@v7.0.1
        - uses: astral-sh/setup-uv@v10.1.0
          with:
            python-version: ${{ matrix.python }}
        # --locked fails on a stale uv.lock, e.g. a release commit that missed it.
        - run: uv run --locked pytest
  ```

  - `permissions: contents: read` — the job only reads the checkout.
  - `3.11` is the `requires-python` floor in `pyproject.toml` (`requires-python = ">=3.11"`);
    `3.14` is the latest stable release. The two legs run in parallel, so the wall clock stays
    near the suite's own three minutes.
  - `setup-uv` supplies the interpreter, so there is no `setup-python` step and no tuned cache.
  - `uv run --locked pytest` fails on a stale `uv.lock`, which is committed here.
- `CLAUDE.md` — one line in the *Layout* block for `.github/workflows/`, so the repository's own
  CI is visible where the tree is described.
- This artifact and its row in `docs/chores/README.md`.

## Decisions needed

All seven were answered at the scope gate as recommended below: no `validate` step, the two legs
`3.11` and `3.14`, the exact tags, the single `uv run --locked pytest` step, the check names
recorded here, one `CLAUDE.md` line and nothing else, and both follow-up tasks opened.

1. **Does this workflow also run `taskrail validate`, or is that left to the generated
   workflow?** Recommendation: **leave it out**. `validate`'s reopen check needs full history, so
   running it here would pull `fetch-depth: 0` into both matrix legs and diverge from the shape
   this task is asked to follow — and the generated workflow (`init --github-workflow`) already
   does exactly that job, `fetch-depth: 0` included. Alternatives: (a) add a `validate` step plus
   `fetch-depth: 0`; (b) add a second job for it. Either duplicates the generated workflow in a
   file that is supposed to be the suite's gate. Follow-up worth opening either way: this
   repository has never installed the `--github-workflow` extra, so nothing validates its own
   backlog in CI.
2. **The exact Python versions.** `3.11` (read from `pyproject.toml`, not assumed) and `3.14`.
3. **The exact action tags.** `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`, both
   verified against GitHub's tag API, not from memory. `setup-uv` publishes bare major tags only
   up to `v7`, so `@v10` would not resolve — which the generated workflow in
   `src/taskrail/install.py` uses. That is out of this task's scope: a follow-up task, not a
   widening of this one.
4. **`uv.lock`.** Committed and tracked, so `uv run --locked` has what it needs.
5. **The required check names.** The job is `test` with one matrix key, so the checks GitHub
   reports — and the names to configure as required on `main` — are `test (3.11)` and
   `test (3.14)`. Adding, removing or renaming a matrix leg renames the checks, and the branch
   protection has to be updated with it.
6. **Documentation.** Recommendation: the `CLAUDE.md` Layout line above and nothing else. No
   `CHANGELOG.md` bullet — the changelog records user-facing taskrail changes, and earlier
   repository-only chores (T058, T069, T090) have none — and no `README.md` or `DESIGN.md`
   change, since both describe the *generated* workflow, which this does not touch.

## Out of scope

- `src/taskrail/install.py` and the workflow it generates, including its `astral-sh/setup-uv@v10`
  pin and `actions/checkout@v7`.
- `src/taskrail/cli.py`, owned by another task in flight.
- Lint, type checking, coverage, build and release workflows; caching beyond what `setup-uv`
  does by default; `concurrency` and cancel-in-progress.
- Installing the `--github-workflow` extra in this repository.

## Verification

- The workflow parses as YAML and its keys are the ones GitHub expects.
- The step the workflow runs is exercised for real on both matrix legs locally:
  `uv run --locked --python 3.11 pytest -q` and `uv run --locked --python 3.14 pytest -q`.
- `taskrail checks T108` (`test`: `uv run pytest -q`) passes; `lint` is not configured here.
- `taskrail validate` reports no errors.

Results:

- The file parses as YAML and its keys are the ones GitHub expects: `name`, `on`, `permissions`,
  `jobs.test` with `runs-on`, `strategy.matrix.python` and three steps. A YAML 1.1 parser reads the
  `on:` key as the boolean `true`, which is how every GitHub workflow is written and what GitHub
  itself accepts. `yamllint` (default rules, line length and `truthy` key checks off) reports
  nothing, exit 0.
- `uv lock --check`: `Resolved 7 packages in 0.68ms` — the committed `uv.lock` is current, so
  `uv run --locked` will not fail on a stale lock.
- The step both legs will run, exercised for real with the interpreters the matrix names:
  - `uv run --locked --python 3.11 pytest -q` → `1221 passed in 160.92s (0:02:40)`
  - `uv run --locked --python 3.14 pytest -q` → `1221 passed in 164.73s (0:02:44)`

  The legs run in parallel on GitHub, so the wall clock stays near those three minutes.
- `taskrail checks T108 --stage implement`: `passed test` (`1221 passed in 161.79s`),
  `not configured lint` — `lint` is not configured in this repository.
- `taskrail validate`: `101 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.

The workflow itself is only proven once it runs on GitHub: the first pull request that carries
this branch is where `test (3.11)` and `test (3.14)` appear.
