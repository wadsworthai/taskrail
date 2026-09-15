# T077 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The canonical repository, and a `v0.1.0` tag in it | `wadsworthai/taskrail` · `alexkander/taskrail` | **`github.com/wadsworthai/taskrail`; no `v0.1.0` version or tag in this repository** | The human's instruction, with the request to create T076 and T077 and run them at once (run 20260915-6). |
| 2 | Consolidate the Unreleased text the release makes obsolete (scope decision D2) | consolidate · rename the heading only | **consolidate: merge the T072, T073 and T075 bullets into one, drop the "Behaviour change" sentences comparing against behaviour 0.1.0 never had (T030, T049, T051, T065) and T061's "as before"; keep every real behaviour change against 0.1.0; add a lead paragraph and an empty `## Unreleased` above `## 0.2.0`** | Decided by the human. |
| 3 | How the release is carried out (scope decisions D1 and D8) | tag after the merge plus a bump task · two follow-up tasks · the human tags | **this branch carries the version, lock and changelog; after the merge the orchestrator asks the human, then tags `v0.2.0` on T077's squash commit and pushes it; one follow-up chore verifies the install from the tag and bumps `main` to `0.3.0.dev0`; no tag in any scratch clone** | Decided by the human. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Order of T076 and T077 (run decision 1) | parallel, T076 handed off first · serialize | **both lanes work in parallel; T076 is handed off and merged first, T077 is rebased onto it; the `v0.2.0` tag is pushed only after T077 merges, with the human's explicit approval at that moment** | The release must name the canonical repository, and a published tag never moves. |
| 2 | Touch map (run decision 2) | split by scope · serialize | **T076: `install.py` `SOURCE_URL`, the `self upgrade --tag` help in `cli.py`, `test_install.py`'s self upgrade test, the six skill sources and what `taskrail upgrade` regenerates, README's install example and one *History* clause, CHANGELOG's preamble install line, its "taskrail has its own repository" bullet and a note under `## 0.1.0`, DESIGN.md's §4 pin example and §9 install example. T077: `pyproject.toml`, `uv.lock`, CHANGELOG's `## Unreleased` heading, the consolidation of the T072/T073/T075 bullets and the intra-release behaviour-change sentences, DESIGN.md line 3 (the status line), and `TODO.md` through the CLI.** | The lanes then share `CHANGELOG.md` and `DESIGN.md` only on separate lines. |

## scope gate

Reviewed: the scope artifact `docs/chores/T077-release-v0-2-0-from-the-canonical-reposi.md` (commit `274a85b`,
the artifact and its index row only); on `d904d11`, `pyproject.toml` at `0.2.0.dev0`, `tests/test_version.py`
(the package version equals pyproject's; `release_tag()` is `v` plus its `X.Y.Z`), which holds for `0.2.0`;
`origin` has no tags. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | The split | this branch plus one follow-up · two follow-ups · no follow-up | **as recommended** | Decided by the human. |
| D2 | Superseded Unreleased text | consolidate · heading only · full regroup | **consolidate, as recommended** | Decided by the human. Do not touch the "taskrail has its own repository" bullet, the preamble or `## 0.1.0` (T076's). |
| D3 | An empty `## Unreleased` above `## 0.2.0` | yes · the bump adds it | as recommended | Pull requests merged between the release and the bump need a place for their bullets. |
| D4 | A lead paragraph under `## 0.2.0`, no URL, no date | yes · none | as recommended | It tells upgraders to read the behaviour changes. |
| D5 | Edit T077's description with `taskrail edit` so it no longer promises the tag and the bump | edit · leave | as recommended | The row should describe what this branch delivers, naming the follow-up. |
| D6 | DESIGN.md line 3 (status) | T077 sets it to `v0.2.0` · T076 owns it | **T077 sets it, touching only that line** | T076 leaves it (its scope decision 4); the status names the release this branch makes. |
| D7 | Pull request title | `chore(release)` · `chore(repo)` | **`chore(release): release v0.2.0 (T077)`** | A release commit; CLAUDE.md's scope list is open-ended. |
| D8 | A tag in a scratch clone for the wrapper-fallback check | defer to the follow-up · local scratch tag | **defer to the follow-up; no tag anywhere** | Decided by the human with D1. |

The change set is approved as listed in the artifact, with D6 applied.

## implement gate

Reviewed: commit `b25ccce` (`git show` of CHANGELOG.md, DESIGN.md, TODO.md, `pyproject.toml` and `uv.lock`):
`version = "0.2.0"` in `pyproject.toml` and the taskrail entry of `uv.lock`; DESIGN.md line 3 only; an
empty `## Unreleased` above `## 0.2.0` and its lead paragraph; the T072, T073 and T075 bullets merged into
one in T075's place; the behaviour-change sentences of T030, T049, T051 and T065 and T061's "as before"
removed, the real ones against 0.1.0 kept; the preamble, the "own repository" bullet and `## 0.1.0`
untouched; T078 (chore, depending on T077) added and T077's description edited, both through the CLI. The
lane built the wheel and sdist, installed the wheel in a scratch virtual environment, and ran `init` and
the wrapper there, with no tag and no `uv tool install`. Re-ran `taskrail checks T077 --stage implement`:
`test` gave `1052 passed in 162.64s`; `lint` is not configured.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The T030 bullet lost the fact that `autopilot lane --group` exits 2 unless the name is a configured judgement group | keep it removed · re-add the fact without the label | **re-add the fact, without "Behaviour change"** | D2 removed labels comparing against unreleased behaviour, not the behaviour itself; the exit code is part of the CLI contract a 0.2.0 reader needs. |
| 2 | Approve the implementation | approve · request changes | **approved, with decision 1 applied** | The diff matches the approved change set, and the checks pass. |

## close

Reviewed: the T030 correction (`b91cabf`: the bullet keeps "`autopilot lane --group` exits 2 unless the
name is a configured judgement group" without the label); the docs stage, which found nothing to change
(`2b8d52e`); `taskrail done` committed on its own (`8cea457`). The backlog differs from the base only in
this task's row (its description, as `✅`) and T078's row. `governing_touched` is empty and the branch has
no upstream. `review --json` then reported no rebase, before T076 merged.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Re-add to the T051 bullet that `overlaps` does not list known-class files (noticed by the lane) | leave it · re-add | **leave it** | "printed under their own heading after the real overlaps" already says it; the T030 fact was an exit code with no such cue. |
| 2 | Pull request title | `chore(release): release v0.2.0 from the canonical repository (T077)` · edit it to `chore(release): release v0.2.0 (T077)` | **the generated title with `--type chore --scope release`** | It keeps the task title `taskrail review` uses, and still names the release. |

## rebase after T076

T076 was merged into `main` (`618474b`). The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `TODO.md` (three commits: rows added on both sides, T077's edited description and T078's row, T077's `✅`) | unite by ID · stop | **unite by ID: T076 `✅`, T077 with its edited description and `✅`, T078** | Backlog rows, a known class; neither side has a `Reopens:` commit. |
| 2 | Conflicts in `docs/chores/README.md` and `docs/autopilot/decisions/README.md` | keep both · stop | **keep both** | Rows appended to an index by both sides, a known class. |

`CHANGELOG.md` and `DESIGN.md` merged without conflict: the preamble names `wadsworthai/taskrail`,
`## Unreleased` is empty above `## 0.2.0`, and `## 0.1.0` carries T076's note. After the rebase:
`git diff --check origin/main` reports nothing, `git diff origin/main --stat` lists only this task's files,
`grep alexkander` finds nothing in CHANGELOG.md, DESIGN.md or README.md, `taskrail checks T077` gave
`1052 passed in 155.63s` (`lint` not configured), and `taskrail validate` reports
`67 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
