# T076 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The canonical repository, and a `v0.1.0` tag in it | `wadsworthai/taskrail` · `alexkander/taskrail` | **`github.com/wadsworthai/taskrail`; no `v0.1.0` version or tag in this repository** | The human's instruction, with the request to create T076 and T077 and run them at once (run 20260915-6). |
| 2 | The CHANGELOG's `## 0.1.0` section (scope decision 1) | keep it with a note · remove it · leave it as is | **keep it, with a note that it was published from the repository taskrail was extracted from as `taskrail-v0.1.0` and that this repository has no `v0.1.0` tag** | Decided by the human. |
| 3 | The version install examples name (scope decision 2) | `v0.2.0` · the placeholder `vX.Y.Z` · leave them to T077 | **`v0.2.0`** | Decided by the human. |

Answered by the human (repository owner), in the orchestrator session.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Order of T076 and T077 (run decision 1) | parallel, T076 handed off first · serialize | **both lanes work in parallel; T076 is handed off and merged first, T077 is rebased onto it; the `v0.2.0` tag is pushed only after T077 merges, with the human's explicit approval at that moment** | The release must name the canonical repository, and a published tag never moves. |
| 2 | Touch map (run decision 2) | split by scope · serialize | **T076: `install.py` `SOURCE_URL`, the `self upgrade --tag` help in `cli.py`, `test_install.py`'s self upgrade test, the six skill sources and what `taskrail upgrade` regenerates, README's install example and one *History* clause, CHANGELOG's preamble install line, its "taskrail has its own repository" bullet and a note under `## 0.1.0`, DESIGN.md's §4 pin example and §9 install example. T077: `pyproject.toml`, `uv.lock`, CHANGELOG's `## Unreleased` heading, the consolidation of the T072/T073/T075 bullets and the intra-release behaviour-change sentences, DESIGN.md line 3 (the status line), and `TODO.md` through the CLI.** | The lanes then share `CHANGELOG.md` and `DESIGN.md` only on separate lines. |

## scope gate

Reviewed: the scope artifact `docs/chores/T076-name-wadsworthai-taskrail-as-the-canonic.md` (commit `7ffe693`,
the artifact and its index row only), and on `d904d11` `grep -rn alexkander` over `src`, `tests`, README,
CHANGELOG and DESIGN.md, which matches the lane's inventory (`install.py:20`, six skill sources,
`test_install.py:283`, `README.md:17`, `DESIGN.md:1009`, `CHANGELOG.md:6` and `:41`). Anonymous
`git ls-remote` succeeds for `wadsworthai/taskrail` and fails for `alexkander/taskrail`; `origin` has no
tags. The stage defines no checks.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `## 0.1.0` in the CHANGELOG | keep with a note · remove · leave | **keep with a note** | Decided by the human. |
| 2 | Version in install examples and help | `v0.2.0` · `vX.Y.Z` · leave to T077 | **`v0.2.0`**; fixture and example `0.1.0` strings that name no fetched tag (`release_tag` test, `conftest.py` pin, merge-driver changelog fixtures, `DESIGN.md:899`) stay | Decided by the human; the fixtures test behaviour, not a release. |
| 3 | One clarifying clause in README *History* | add it · leave the paragraph | as recommended | Otherwise the paragraph implies a 0.1.0 release here. |
| 4 | DESIGN.md's status line | T076 rewords it · leave it to T077 | **leave it to T077**, which sets it to the 0.2.0 release | The status names the current release, which T077 makes; one owner avoids a conflict on a single line. |
| 5 | A code change for consumers pinned to `v0.1.0` | none · map `v0.1.0` to the earlier repository | as recommended: **none** | Their 0.1.0 wrapper points at the earlier repository and keeps working, and `taskrail upgrade` moves the pin; mapping would put the earlier repository's location back into this one. |
| 6 | Past artifacts (`docs/spikes/T007-*`, `docs/features/T015-*`) and T076's own row keep `alexkander` | keep · rewrite | as recommended | They record what was run then. |

The change set is approved as listed in the artifact, with decision 4 applied: T076 does not touch
DESIGN.md line 3.
