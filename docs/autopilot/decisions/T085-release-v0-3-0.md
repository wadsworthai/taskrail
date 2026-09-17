# T085 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Prepare the next version after E07 merged | release task now · wait | **prepare it** | The human asked to prepare the next version once T084 was merged; the task was created with `taskrail new --workspace` and added to run 20260917-1. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope artifact `docs/chores/T085-release-v0-3-0.md` (commit `611e417`, the artifact and
its index row only, clean worktree); `git log v0.2.0..origin/main` shows only `feat`, `docs` and
`chore` subjects with no breaking mark; the `## 0.2.0` section of CHANGELOG.md has blank lines only
around its lead paragraph and heading, none between bullets; the T077 and T078 precedent. The stage
defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Change set and split | as proposed, as T077 and T078 · move references to the follow-up | **as recommended** | Same release process as v0.2.0. |
| 2 | Lead paragraph under `## 0.3.0` | proposed text · one sentence · none | **as recommended** | Summarises E07 and says every setting defaults to 0.2.0's behaviour. |
| 3 | Corrections so the section reads as one release | (a), (b) and (c) · (a) and (b) · none | **all three, no reordering** | Unreleased must not describe intra-release states; (c) matches the `## 0.2.0` layout. |
| 4 | Install and pin examples naming v0.2.0 | change to v0.3.0 here · in the follow-up · leave | **as recommended** | The tagged tree should tell readers to install the release it is; T076 did the same before v0.2.0. |
| 5 | T085's description names the follow-up's ID | edit · leave | **as recommended** | As T077 named T078. |
| 6 | The extra current-branch check on the built wheel | include · T077's checks only | **as recommended** | The release's main feature is exercised from the built package, not only from source. |
| 7 | Pull request title | `chore(release): release v0.3.0 (T085)` · other | **as recommended** | As T077 and T078. |

## implement gate

Reviewed: `git diff 1a45bd8..a8b230c` — `pyproject.toml` and `uv.lock` (one version line each), the
CHANGELOG (new empty `## Unreleased`, `## 0.3.0` with the approved lead, D3 (a)–(c) with no bullet
reordered or reworded otherwise), DESIGN.md lines 3, 112 and 1179, README line 17, and TODO.md
(T085's description naming T086, and T086's row depending on T085); the lane's build, wheel install,
wrapper and current-branch checks from the built wheel; the checks re-run with
`taskrail checks T085 --stage implement` (1183 passed, lint not configured).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | approve · request changes | **approve** | The diff is the approved change set; the release was exercised from the built package. |
| 2 | A long line in the artifact's *After the merge* | leave · reflow | **reflow it in the docs stage** | Cheap, and it keeps the artifact's wrap. |
