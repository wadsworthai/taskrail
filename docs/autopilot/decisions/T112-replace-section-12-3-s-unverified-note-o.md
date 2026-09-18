# T112 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T112-replace-section-12-3-s-unverified-note-o.md` and its commit
`d137590` (artifact and index row alone, `DESIGN.md` untouched); §12.3's current text; T057's E4
figures and its *Limits* section, quoted from the merged artifact rather than from the brief; the
grep showing the suite asserts on §12.7 and §4 but nothing in §12.3; and the grep showing the
unverified claim exists in exactly one place.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | The replacement wording | **the two-sentence form** · A, one sentence with a dash-aside · B, ending on "is unmeasured" · C, mechanism without the figures | **the two-sentence form, as recommended** | It names the agent first, gives the mechanism, carries the four figures in one clause and cites `T057 E4` in the style §12.3 already uses for `T033 F2`. A loses the T033 trial and packs the whole finding into one long sentence. B reintroduces the hedging word the task exists to remove — the gap did move rather than close, but "another agent may store lane conversations differently" says that without sounding like the old sentence. C is the one option that defeats the task: the figures are what turn "not verified" into "measured", and they cost a single clause. |
| Q2 | A `CHANGELOG.md` entry | **none** · one bullet | **none** | No behaviour, CLI surface, configuration or skill changes, and the three most recent documentation-only tasks on `main` added none. |

Given with the answers: the demotion of T033's observation to a consequence of the measurement is
the right order and should survive review — the trial is now evidence of the mechanism rather than
the reason to doubt it.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `DESIGN.md` §12 with two lanes in it | **split by subsection** · serialize the lanes | **T112 takes §12.3 and nothing else; T111 takes §12.1 and the count-choosing text, plus the autopilot skill** | The two changes are about different things and sit in different subsections, so both can be written at once and git rebases them without meeting. The skill's restart procedure at `SKILL.md:163` stays correct under this measurement and belongs to T111. |

## implement gate

Reviewed: commit `6757a6c` and the diff `b236700..HEAD` — `DESIGN.md` in one hunk, three lines out
and six in, and the artifact; no `CHANGELOG.md` entry, nothing in the autopilot skill or its
installed copy, no other part of §12; the lane's `taskrail checks T112 --stage implement`
(1221 passed) and `taskrail validate`; and `grep -n "not verified" DESIGN.md`, which now returns
nothing.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The wording was settled at the scope gate and applied word for word, with the approved order kept: mechanism first, T033 demoted to a consequence, portability clause last. |
| 2 | Stop again at `docs`? | **fold it into the close** · stop twice | **fold it into the close** | The change is the documentation, the restart procedure it describes is unchanged, and no follow-up is open. |

## close

Reviewed: the whole diff `origin/main..HEAD` — `DESIGN.md` in one hunk at §12.3, T112's `✅`, the
artifact and two index rows, and nothing else; the lane's `taskrail checks T112 --stage implement`
(1221 passed), `taskrail validate` (101 tasks, 0 errors) and the empty `grep "not verified"`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request type and scope | **`docs` / `repo`**, as the lane recommends · the generated scope-less `chore:` | **`docs` / `repo`** | The change is documentation only, in `DESIGN.md`, and it matches how `main` titles its recent `DESIGN.md`-only tasks (T102, T098). CLAUDE.md asks for the type of the most significant change with the affected area as scope. |

## rebase after T106, T107, T109, T110, T108 and T111 merged

Six branches were merged into `main` (up to `e3f3e9a`). This branch was rebased onto `origin/main`,
with three conflicts, all known classes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/chores/README.md` and `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2; united by ID, no duplicate. |
| 2 | `TODO.md` status cells | **unite by ID, `✅` wins** · stop | **as decided** | Known conflict class 1; the branch was cut before the six merges, so its copies of those rows are older, and no side has a `Reopens:` commit. |

`DESIGN.md` did not conflict: T111 wrote in §12.1 and this branch in §12.3, which is the split the
touch map set at dispatch.

After the rebase: `grep "not verified" DESIGN.md` returns nothing, the replacement sentence and its
`(T057 E4)` citation are in place, `taskrail checks T112` passed on the 1,247 tests the branch now
collects, and `taskrail validate` reports 106 tasks, 0 errors.
