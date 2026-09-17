# T086 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Create and push `v0.3.0` on T085's squash commit before this task | create and push · the human tags · do not publish yet | **create and push**: `git tag -a v0.3.0 dbc49d7 -m "taskrail 0.3.0"` and `git push origin v0.3.0` by the orchestrator | The human's explicit approval after merging T085 (#18), with the instruction to work T086 (run 20260917-1). |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope artifact `docs/chores/T086-bump-main-to-0-4-0-dev0-after-the-v0-3-0.md` (commit
`3591756`, the artifact and its index row only, clean worktree); `git ls-remote --tags origin` shows
the annotated `v0.3.0` (`8fde8af`) peeling to `dbc49d7`, this branch's base; T078's commit changed
only `pyproject.toml`, `uv.lock`, `TODO.md` and its documents. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Change set | `pyproject.toml`, `uv.lock`, artifact, index and done row · wider | **as recommended** | Exactly T078's change set and T085's *After the merge*. |
| 2 | `.taskrail/installed.json` | leave · `taskrail upgrade` | **as recommended** | As T078; rewriting it would record a tag that does not exist. |
| 3 | CHANGELOG entry | none · a bullet | **as recommended** | As T016 and T078; a dev bump changes no behaviour. |
| 4 | E01's *Done when* naming v0.2.0 | leave · edit | **as recommended** | The condition is met as written. |
| 5 | Pull request title | `chore(release): bump main to 0.4.0.dev0 after the v0.3.0 tag (T086)` · `--scope repo` | **as recommended** | As T078 and T085. |
| 6 | Verification plan, 12 checks in scratch environments | approve · change | **approve** | Mirrors T078 with v0.3.0; never touches the human's installed CLI or any tag. |

## implement gate

Reviewed: `git diff e4468b1..e63c714` (one version line each in `pyproject.toml` and `uv.lock`, and the
artifact's results), the lane's 12 checks with their real output; the scratch venv installed from
the tag prints `taskrail 0.3.0` and the branch's wrapper prints `taskrail 0.4.0.dev0`; the checks
re-run with `taskrail checks T086 --stage implement` (1183 passed, lint not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | approve · request changes | **approve** | Exactly the approved change set, and the install from `v0.3.0` is verified. |
