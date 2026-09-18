# T101 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact at commit 7a4fd3e, the diff against the base (the artifact only), and the
lane's evidence, checked by the orchestrator: `cli.py:1480-1483` is the whole `next` parser and
`--limit` really has no `help=`; `DESIGN.md:654` already documents the flag as `[--limit N]`, so §7
needs nothing.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The wording, and whether `metavar="N"` comes with it | both, matching `--history-limit` · help only | **both, as recommended** | `--history-limit` is the house form for a limit flag: terse, lower case, no full stop, default stated. The metavar matters beyond style — `DESIGN.md` §7 already writes the flag as `[--limit N]` while `--help` prints `LIMIT`, so adding it makes the two agree instead of documenting a third spelling. |
| 2 | A test, and how wide | this flag only · none · every argument must have `help=` | **this flag only, as recommended** | The lane measured the parser-wide option before proposing it: **65 arguments have no `help=` today**, so that test could only land with a 64-entry exemption list or 64 new help strings. That is a new rule for the whole CLI and does not belong in a one-point chore. Three lines beside the existing `next` tests pin exactly what this task fixes. |
| 3 | A `CHANGELOG.md` entry | no · yes | **no** | `## Unreleased` holds behaviour changes; a help string is not one, and `CHANGELOG.md` is outside this lane's touch map. |
| 4 | The 65 help-less arguments | record the finding, open nothing · open a task | **record it in the artifact; the orchestrator carries it to the human** | It is a real, measured finding and the artifact is where it survives. Opening a task would commit someone to writing 64 help strings, or to a rule with a 64-entry exemption list, on the strength of one flag having gone unnoticed. That is the human's call, not the orchestrator's, and it is being put to them. |
| 5 | `--limit` accepts 0 and negatives (`type=int`, then `tasks[: args.limit]`), where the sibling uses `_positive_int` | open a `bug` · report only | **open a `bug`, 1 point** | Unlike the help-string rule, this is a concrete defect with a bounded fix: `--limit 0` prints "no eligible tasks" and a negative value silently drops tasks from the end. The design principles say what exists is reopened by a task that asks for it, and this lane found it on the way — so it becomes a task rather than widening a one-point chore. |

Instructions given with the answers: record the real `next --help` and `next --limit 2` output under
*Verification*; do not touch `--limit`'s type, the other 64 arguments, `DESIGN.md`, `README.md` or
`CHANGELOG.md`.

Noted, no action: the lane's first `claim` ran from the primary checkout and recorded `branch: main`;
it released and re-claimed with `--root <worktree>` before editing anything. That is the CLI
resolving its root from the working directory, and the handling was correct — the second lane in
this run to hit it, which is worth remembering if it happens a third time.

## Conflict handling agreed for all lanes

Run 20260918-1. T099 may change `config.py` and `install.py`; T100 is handed off and waiting to be
merged.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T101: one line of `cli.py`, one test, its own artifact and row** | The smallest change set in the run. It meets T099 only in `cli.py`, and in a different command's parser. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1) and appended index rows (2)** | Resolved by the orchestrator at hand-off. A conflict inside `cli.py` escalates. |
| 3 | May this lane fix what it found on the way? | allow · forbid, open tasks instead | **forbid; open a task for the `--limit` type defect** | The rule the repository adopted in T090: apply the principles to the change a task makes, and open a task for what exists. |
