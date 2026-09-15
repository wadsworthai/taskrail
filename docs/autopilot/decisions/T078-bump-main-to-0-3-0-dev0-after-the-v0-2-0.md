# T078 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Create and push `v0.2.0` on T077's squash commit before this task | create and push · the human tags · run without the tag | **create and push**: `git tag -a v0.2.0 23e62e8 -m "taskrail 0.2.0"` and `git push origin v0.2.0` by the orchestrator | The human's explicit approval after merging T077 (#9), with the instruction to run T078 (run 20260915-7). |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope artifact `docs/chores/T078-bump-main-to-0-3-0-dev0-after-the-v0-2-0.md` (commit `912cd35`, the
artifact and its index row only); anonymous `git ls-remote --tags` shows the annotated `v0.2.0` (`308498f`) on
`23e62e8`, this branch's base; `install.py` writes `installed.json`'s `version` from `release_tag()` and
nothing reads it back. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Change set | `pyproject.toml` + `uv.lock` + E01's *Done when* · version and lock only | as recommended | As T016 did, plus the line decision 3 settles. |
| 2 | `.taskrail/installed.json`'s `"version": "v0.2.0"` | leave it · run `taskrail upgrade` | as recommended: **leave it** | Nothing reads it, and rewriting it now would record `v0.3.0`, a tag that does not exist; the next `upgrade` rewrites it. |
| 3 | E01's *Done when*, which names `v0.1.0` | change it to `v0.2.0` here · a follow-up · leave it | as recommended: **change that prose line here** | This task's verification is the evidence the line asks for, and no `v0.1.0` tag exists in this repository; it is prose, not a table row, and `validate` checks the file afterwards. |
| 4 | A CHANGELOG entry | none · an Unreleased bullet | as recommended: **none** | A development version on `main` is not a user-facing change, and T016 added none. |
| 5 | Pull request title | `chore(release)` · `chore(repo)` | **`chore(release): bump main to 0.3.0.dev0 after the v0.2.0 tag (T078)`** | It matches T077. |

The verification plan (checks 1–12 in the artifact) is approved as proposed: every install from the tag in a
fresh cache, wrapper checks with a restricted `PATH` so the human's installed CLI is never used, no tag
created, moved or pushed, and no `uv tool install`.
