# T109 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T109-reject-a-next-limit-that-is-zero-or-nega.md` and its commit
`ba805c0` (the only commit on the branch, artifact and index row alone, working tree clean); the
reproductions, which show `--limit 0` and `--limit=-1` answering with exit 0 instead of refusing;
`_positive_int` at `src/taskrail/cli.py:1435` read by the orchestrator; and the probe table for
every other `type=int` argument, each run against the real CLI rather than read off the source.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is `_positive_int` as it stands right for both call sites? | **use it unchanged** · parameterise it with the option's name · add a second near-identical helper · guard inside `cmd_next` | **use it unchanged** | Its message is written about the value, not about `--history-limit`, and argparse supplies the option name and usage line around it. Two call sites share one helper; splitting them for a difference nobody has asked for is what the rule of three and YAGNI both refuse. A runtime guard would refuse after the project loads and leave the two options behaving differently for the same mistake. |
| 2 | Does any other `type=int` argument have the same defect? | **none — open nothing** · open a chore for the autopilot `--count` guards | **open nothing** | The lane probed every one with `0` and a negative value in the real CLI: `--pts` is caught by the points scale, both `--count` flags refuse in their handlers, `--epic-level` refuses its range. `next --limit` is the only one whose bad value becomes a plausible wrong answer instead of an error. Moving the `--count` guards to `type=` would trade a message that names the run for consistency nobody needs. |
| 3 | A `CHANGELOG.md` bullet? | **yes, one under *Unreleased*** · none | **yes** | A value that exited 0 now exits 2. That is user-visible, and a reader upgrading deserves to find it. |
| 4 | `DESIGN.md` §7's wording | **leave it** · state the minimum there | **leave it** | "`--limit` keeps the first N of them" stays true of every value the CLI will accept after the fix, and §7 states no minimum for `--history-limit` either, so adding one here would make the two rows inconsistent instead of more precise. |

Given with the answers: T108 does not touch `src/taskrail/cli.py` — only T107's finished branch does,
in `cmd_archive` and the `archive` subparser, far from `cmd_next`. Keep the edit to the `--limit`
line as planned.

## fix gate

Reviewed: commit `2cde32d` and the diff `02990a4..HEAD` — one character of behaviour in
`src/taskrail/cli.py` (`type=int` → `type=_positive_int`), 20 lines of test, an 11-line changelog
bullet and the artifact, with nothing else in `cli.py` reformatted; the regression test's recorded
failure against the unfixed code, which fails as `DID NOT RAISE SystemExit` with the wrong answer
captured on stdout — the root cause itself, not a proxy for it; the lane's
`taskrail checks T109 --stage fix` (1224 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** · reopen a diagnose answer | **no** | Every answer from the diagnose gate was applied as given, and nothing surfaced that the task, the artifact or the repository's own instructions do not already settle. |

Noted from the lane, and not a side effect of the change: `next --limit 2` now lists fewer tasks
than the diagnose baseline did, because other lanes of this run claimed T003 and T110 in between and
`eligible()` excludes claimed tasks. The lane recorded that in the artifact so a later reader does
not read it as a consequence of the fix.

## close

Reviewed: the whole diff `origin/main..HEAD` — one line of `src/taskrail/cli.py`, 20 lines of test,
one `CHANGELOG.md` bullet, the artifact, two index rows and T109's `✅`, with nothing else in
`cli.py` touched; the lane's `taskrail checks T109 --stage fix` (1224 passed) and
`taskrail validate` (101 tasks, 0 errors); `git status` clean and the claim released.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `impact` stage opened nothing — accept? | **accept** · ask for a follow-up | **accept** | Its only candidate was settled at the diagnose gate by a probe of every other `type=int` argument in the real CLI, and that table is in the artifact's *Affected areas*, so the reasoning survives the task. |
| 2 | Pull request type and scope | **`fix` / `cli`** · `feat` · `fix!` | **`fix` / `cli`** | It repairs a command that answered a bad value instead of refusing it. Not breaking in the semantic-versioning sense: the accepted range of values is unchanged for every value that was ever meaningful, and the changelog bullet flags in bold that a script passing `0` or a negative now exits 2. |
| 3 | Publish now? | **wait** · publish out of order | **wait** | Hand-off is sequential and the queue is T107 then T109, behind T106 in review. T107 also lands in `cli.py`, so publishing T109 first would only move the rebase from one branch to the other. |

## rebase after T106 and T107 merged

T106 (`33cf1a5`) and T107 (`38bf4f9`) were merged into `main`. The branch was rebased onto
`origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2; united by ID, 89 rows, no duplicate. |
| 2 | Conflict in `CHANGELOG.md` | **keep both bullets** · stop | **keep both**, T109's above T107's | Appended changelog bullets, known conflict class 2. T107's `archive` bullet and this one landed at the same place in *Unreleased*; the section is newest-first and this branch lands after T107, so it goes on top. |

After the rebase: no conflict markers, `type=_positive_int` still on the `next` subparser's
`--limit` (`src/taskrail/cli.py:1539`), `taskrail checks T109` passed with 1,247 tests, and
`taskrail validate` reports 103 tasks, 0 errors.
