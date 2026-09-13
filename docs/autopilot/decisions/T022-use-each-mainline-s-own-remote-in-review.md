# T022 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T022-use-each-mainline-s-own-remote-in-review.md` (commit `92e1e04`) and its eight acceptance criteria.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan? | approve · with changes | **approve** | Criteria cover base, fetch, push, link and two backlogs on different remotes, with local bare remotes only; `config.py` stays untouched while T018 and T021 edit it. |
| 2 | Where to push the task branch | resolved remote · `[review].remote` | **resolved remote** | The consumer that motivated the task asked for push and link on the mainline's own remote; a same-repository compare link needs the branch there. |
| 3 | Tracking config wins over an explicit `[review].remote` | accept · per-backlog override now | **accept**, and state the behaviour change in the changelog line | It is the order the task itself specifies; git's tracking config is the more specific fact about a mainline. An override can follow if a repository needs it. |
| 4 | Core skill step 3: `git fetch <base.remote>` | yes · `--all` · unchanged | **yes** | A bare fetch only updates the current branch's upstream. |
| 5 | Follow-ups for `branch.<mainline>.merge` and fork push remotes | open now · note only | **note only** | No consumer needs them today. |

## Conflict handling agreed for all lanes

T021 and T022 both edit the config template in `install.py` (`[columns]` and `[review]`), T022 and T023 both edit adjacent steps of the core skill, and every lane adds a `## Unreleased` changelog line and a decisions index row. Each lane touches only its own section. When a later rebase conflicts there: keep both sides in sources, changelog and indexes, then regenerate `.claude/skills/` with `taskrail upgrade` instead of merging installed copies by hand.

## implement gate

Reviewed independently of the lane's report: the source diff `80151d1..a0cb76e` (`review.py`
`resolve_remote`, `query.py` `base_dict`, `cli.py` `_open_workspace` and `cmd_review`, one
`install.py` template line) and a re-run of the suite in the lane's worktree (164 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation? | approve · request changes | **approve** | One resolver used consistently for base, fetch, push and link; tests were observed failing first; the template change is confined to `[review]`. |
| 2 | Updating the expected `base` in `test_show_reports_the_base` | accept · report the fields outside `base` | **accept** | The change only adds the two approved keys to an object the test compares whole; moving them would contradict the plan. |
| 3 | Keep the `installed.json` version and hash change from `upgrade` | keep · commit only the hash | **keep** | It is what `upgrade` writes; conflicts are resolved by re-running it. |
| 4 | Unwrapped changelog line | keep · rewrap now | **keep** | Keeps parallel merges trivial; rewrap when the release is prepared. |

## rebase after T018 and T023 merged

This branch was rebased onto `origin/main` (`e85bcff`), which carries T018 (#8) and T023 (#9).
Every conflict fell in a class agreed before the lanes started; none needed escalation:

| File | Conflict | Resolution |
|---|---|---|
| `docs/features/README.md`, `docs/autopilot/decisions/README.md` | appended index rows | kept every row |
| `CHANGELOG.md` | `Unreleased` bullets | kept every bullet |
| `src/taskrail/skills/taskrail/SKILL.md` | T023's step 2 sentence next to this branch's step 3 | kept both edits |
| `DESIGN.md` | the `show` row: this branch's `base` wording and T023's `prior_work` | one row carrying both |
| `.claude/skills/taskrail/SKILL.md`, `.taskrail/installed.json` | installed copy and its hash | manifest made valid first, then regenerated with `taskrail upgrade --force` from the merged source |
| `TODO.md` | status cells of T022 and T023, plus T025 | rows united by ID; T022 and T023 ✅ (no `Reopens:`), T025 kept |

After the rebase: no conflict markers, 212 tests passed, `validate` clean, installed skills and
manifest matching their sources, and `show T022` reporting both its base remote and prior work.
