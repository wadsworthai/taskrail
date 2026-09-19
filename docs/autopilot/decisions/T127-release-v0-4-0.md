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
