# T127 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane. The tag is not among them: it follows the squash
merge and only with the human's explicit approval at that moment.

## scope gate

Reviewed: the artifact `docs/chores/T127-release-v0-4-0.md` and its commit `5c05ea9`; the 50
commits since `v0.3.0` classified by type, none marked breaking; the twelve test assertions removed
since then, each traced to a listed behaviour change; the version references found by search, each
marked changed or deliberately left; and the behaviour-change table, which the lane built itself and
which found one change the orchestrator's list missed (T107's `.gitattributes` line) and correctly
dropped two it had included (T099 and T003 reach new installs only).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The version | **`0.4.0`** · `0.3.1` · `1.0.0` | **`0.4.0`** | Six `feat` commits and no breaking marker; before 1.0 incompatible fixes also take a minor bump. A patch would ship six features, and 1.0 would declare a stability nobody has decided on. |
| 2 | How the notes present behaviour changes | **the `## 0.2.0` convention: a lead paragraph plus a `Behaviour change:` sentence in each affected bullet** · a separate summary heading · splitting the bullets · the lead paragraph only | **the existing convention** | It is how this file already marks them, it moves and duplicates nothing, and a consumer reading one bullet sees its warning in the same place. A new heading would repeat every change twice. |
| 3 | The changelog corrections (a)–(h) | **all of them, no reordering** · (b)–(h) only · none | **all of them** | (a) matters most: the bullets for T121, T122 and T125 describe bugs in `archive`, which was never released, so a consumer on 0.3.0 would read fixes for bugs they never had. Rewritten in the present tense they describe what the new command does. The same edit removes T122's sentence that T124 made false. (c) names a command that does not exist, and (d) reads as if existing backlogs break when only `init` changed. The rest are consistency with the two earlier releases. |
| 4 | Name `v0.4.0` in the install and pin examples in this pull request | **yes, as T085 did** · in T128 · leave them | **yes** | Changing them after the tag would leave the tagged README naming v0.3.0 for good. The cost — `main` naming a tag for the minutes before it is pushed — is the one T085 accepted. |
| 5 | An upgrade check from 0.3.0, beyond T085's | **yes** · T085's checks only | **yes** | It is exactly what a consumer does after this release, and it proves the notes' "arrives at `upgrade`" column rather than asserting it. Reading `v0.3.0` through `git+file://` creates no tag. |
| 6 | Pull request title | **`chore(release): release v0.4.0 (T127)`** | **as recommended** | The form T077, T085 and T086 used. |

Noted for the human, not for this task: `git tag` in this clone lists a local `v0.1.0` that is not
on `origin`, while `CHANGELOG.md` says the repository has no `v0.1.0` tag. The lane reported it and
touched nothing; neither did the orchestrator.

## implement gate

Reviewed: commit `80cf309` — `pyproject.toml` at `0.4.0`, `uv.lock` changing only its version line,
the release notes, and the version named in `DESIGN.md` and `README.md`; the lead paragraph and all
nine `Behaviour change:` sentences read in full; the build, the fresh `init` from the 0.4.0 wheel,
and the upgrade from 0.3.0 run end to end, which reproduced four of the release's fixes on the
released 0.3.0 before showing each one gone after `upgrade`; `taskrail checks T127 --stage
implement` (1,273 passed). Checked by the orchestrator: `pyproject.toml` reads `0.4.0`, `git tag`
is unchanged (`v0.1.0 v0.2.0 v0.3.0`), and no `v0.4.0` exists on `origin`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | **approve, with one rewrap** · request wording changes | **approve with one rewrap** | The notes say what a consumer needs, in the file's own convention, and the upgrade check proves the "arrives at `upgrade`" column rather than claiming it. |
| 1a | T109's marker is wrapped so "Behaviour" and "change:" fall on separate source lines | **rewrap it onto one line** · leave it | **rewrap** | The lead paragraph tells the reader to look for the entries marked **Behaviour change**, and a single-line search finds 8 of the 9. One that a reader's search misses is the one they will not read before upgrading. `## 0.2.0` keeps each marker on one line. |
| 2 | The extra `(T121)` added while rewording | **keep** · revert | **keep** | The same correction as (b), found while doing (a); the artifact records it. |

The upgrade check is the strongest evidence in this release. On the published 0.3.0 the wrapper run
from another directory exits 2, `next --limit 0` answers `no eligible tasks` with exit 0, and
`epic add --id E02` accepts an ID another branch holds; after `upgrade` to 0.4.0 all three behave as
the notes say, and the config's only change is its version pin.
