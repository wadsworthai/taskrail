# T108 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T108-add-continuous-integration-that-runs-the.md` and its commit
`f45e098` (artifact and index row alone, working tree clean); `requires-python = ">=3.11"` and the
committed `uv.lock`; and the action tags, which the orchestrator re-queried itself rather than
taking from the lane — `astral-sh/setup-uv` has `v10.0.0`, `v10.0.1` and `v10.1.0` and **no bare
`v10`**, while `actions/checkout` has `v7` alongside `v7.0.0` and `v7.0.1`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Does `ci.yml` also run `taskrail validate`? | **leave it out** · add a `validate` step with `fetch-depth: 0` · a second job | **leave it out** | `validate`'s reopen check needs full history, so adding it drags `fetch-depth: 0` into both legs and duplicates what the generated workflow already does. This file's job is to be the suite's gate; one job, one purpose. |
| 2 | The matrix legs | **`["3.11", "3.14"]`** · add 3.12 and 3.13 | **`["3.11", "3.14"]`** | 3.11 is the `requires-python` floor, read from `pyproject.toml`, and 3.14 the latest stable. Intermediate legs cost wall clock for a range the floor and the ceiling already bracket, and the contract names two. |
| 3 | The pins | **`actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`** · SHA pins | **exact release tags, as verified** | Both were checked against GitHub's tag API, by the lane and again by the orchestrator. SHA pins are not in the contract and the sibling repository does not use them. |
| 4 | Is `uv run --locked pytest` the single step? | **yes** · add a fallback | **yes** | `uv.lock` is committed, which is what `--locked` needs; a fallback would defeat the point of failing on a stale lock. |
| 5 | The required check names | **`test (3.11)` and `test (3.14)`** · rename the job | **as recommended** | The matrix key is part of the check name, so branch protection has to follow any rename. The write-up says so, which is the part that matters. |
| 6 | Documentation | **one `CLAUDE.md` *Layout* line, nothing else** · also a changelog bullet · nothing at all | **one `CLAUDE.md` line** | `CLAUDE.md` asks to be kept current as the repository grows, and a new top-level directory is exactly that. No changelog bullet: *Unreleased* records user-facing taskrail changes, and repository-only chores have none. `README.md` and `DESIGN.md` describe the *generated* workflow, which this does not touch. |
| 7 | The two follow-ups | **open both** · only the bug · neither | **open both** | The bug is real and the orchestrator confirmed it: `src/taskrail/install.py:273` generates `astral-sh/setup-uv@v10`, and no such tag exists, so every repository that ran `init --github-workflow` at this version has a workflow that cannot resolve the action. That belongs in the backlog today, and not in this task. The optional chore follows from decision 1: if `validate` is left to the generated workflow, this repository should install it, since it never did. |

Given with the answers: keep the sibling repository's name and path out of everything committed, as
you already did — cite the tag API, not the clone. The `v10` bug's row must name the consumer
impact, since it is the only one of the two that affects anybody's repository but this one.

## implement gate

Reviewed: commit `ef418a8` and the diff `4e9dd46..HEAD` — `.github/workflows/ci.yml` read in full by
the orchestrator, one `CLAUDE.md` *Layout* line, and the artifact; no `setup-python`, no cache
tuning, no `fetch-depth`, no `concurrency`, no lint, type, coverage or build step, and
`src/taskrail/install.py` and `cli.py` untouched. The lane ran the workflow's own command on both
matrix legs for real (`uv run --locked --python 3.11 pytest -q` and `--python 3.14`, 1221 passed
each), checked the lock with `uv lock --check`, and ran `taskrail checks T108 --stage implement`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The seven scope answers were applied as given and the scope did not widen. |
| 2 | Is "the workflow cannot be proven locally" enough? | **accept, with the limit stated in the artifact** · ask for `act` or a trial push | **accept** | A workflow only really runs on GitHub, and the branch's own pull request is where `test (3.11)` and `test (3.14)` first appear. What could be verified locally was: the file's parsed structure, the lock, and the exact command on both interpreters. Saying so rather than claiming more is the right shape for this evidence. |
| 3 | Pull request type and scope | **`ci` / `repo`** · `chore` / `repo` | **`ci` / `repo`** | The change is continuous integration for this repository only. `ci` is a Conventional Commits type, and CLAUDE.md asks for the affected area as the scope; `repo` is the area its own Merging section names for repository-level work. |
