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
