# T109 — Reject a next --limit that is zero or negative

Kind: bug · Epic: E08 · Status: diagnosed

## Symptom

`taskrail next --limit N` declares `type=int`, so argparse accepts any integer, including `0`
and negatives. `cmd_next` then slices `eligible(...)[: args.limit]`, and Python's slice
semantics answer both wrong values instead of refusing them:

- `--limit 0` prints `no eligible tasks` (and `[]` with `--json`) and exits 0 — the same answer
  the CLI gives when the backlog really has nothing eligible. A caller cannot tell the two apart.
- `--limit -N` silently drops the **last** N eligible tasks and exits 0, which is the opposite
  end of the list from the one `--limit` is meant to keep, and is reported as a complete answer.

Expected, as `validate --history-limit` already behaves: argparse refuses the value, prints the
usage line and the reason, and exits 2 without producing any answer.

## Reproduction

In this repository's own backlog, on `5dfcd8e` (`origin/main`), from the T109 worktree:

```bash
.taskrail/bin/taskrail next --limit 5      # baseline: four eligible tasks
.taskrail/bin/taskrail next --limit 0
.taskrail/bin/taskrail next --limit 0 --json
.taskrail/bin/taskrail next --limit=-1
.taskrail/bin/taskrail next --limit=-10
```

## Evidence

Baseline — the backlog has four eligible tasks:

```
$ .taskrail/bin/taskrail next --limit 5
T112   ⬜ pending     chore     1pt  E02   Replace section 12.3's unverified note on old lane handles with the measured reason
T110   ⬜ pending     chore     1pt  E08   Reword DESIGN.md §4 where it says an ID refusal quotes the prefix rather than the key  ← T103
T003   ⬜ pending     chore     2pt  E01   Install taskrail in a first consumer project  ← T002
T111   ⬜ pending     chore     2pt  E02   Record the orchestrator's context budget where a run's count is chosen
exit=0
```

`--limit 0` answers as if nothing were eligible, in text and in JSON, exiting 0:

```
$ .taskrail/bin/taskrail next --limit 0
no eligible tasks
exit=0

$ .taskrail/bin/taskrail next --limit 0 --json
[]
exit=0
```

A negative value drops tasks from the **end** of the list and reports the rest as the answer.
`--limit=-1` returns three of the four (T111, the last, is gone); `--limit=-10` exceeds the list
and empties it:

```
$ .taskrail/bin/taskrail next --limit=-1
T112   ⬜ pending     chore     1pt  E02   Replace section 12.3's unverified note on old lane handles with the measured reason
T110   ⬜ pending     chore     1pt  E08   Reword DESIGN.md §4 where it says an ID refusal quotes the prefix rather than the key  ← T103
T003   ⬜ pending     chore     2pt  E01   Install taskrail in a first consumer project  ← T002
exit=0

$ .taskrail/bin/taskrail next --limit=-10
no eligible tasks
exit=0
```

The same two values on `validate --history-limit`, which already uses `_positive_int`:

```
$ .taskrail/bin/taskrail validate --history-limit 0
usage: taskrail validate [-h] [--json] [--no-history] [--history-limit N]
taskrail validate: error: argument --history-limit: expected a whole number of at least 1, got `0`
exit=2

$ .taskrail/bin/taskrail validate --history-limit=-1
usage: taskrail validate [-h] [--json] [--no-history] [--history-limit N]
taskrail validate: error: argument --history-limit: expected a whole number of at least 1, got `-1`
exit=2
```

`_positive_int` also gives a non-numeric value a better message than bare `int` does, which the
fix picks up for free:

```
$ .taskrail/bin/taskrail next --limit abc
taskrail next: error: argument --limit: invalid int value: 'abc'
exit=2

$ .taskrail/bin/taskrail validate --history-limit abc
taskrail validate: error: argument --history-limit: expected a whole number of at least 1, got `abc`
exit=2
```

## Root cause

`src/taskrail/cli.py:1483` declares the option with argparse's plain `int` converter:

```python
nxt.add_argument("--limit", type=int, default=5, metavar="N", help="show at most N eligible tasks (default 5)")
```

`int` accepts every integer literal, so `0` and negatives reach the handler unchallenged.
`cmd_next` (`src/taskrail/cli.py:206`) then uses the value only as a slice bound:

```python
tasks = eligible(project, args.backlog, claimed)[: args.limit]
```

`list[:0]` is empty and `list[:-n]` drops the last `n` items, both without raising. The wrong
value therefore never becomes an error anywhere: it becomes a different, plausible-looking
answer with exit 0. The option has no validation of its own, and there is no other code path
between argparse and the slice that could supply one.

The repository already has the guard this option is missing — `_positive_int`
(`src/taskrail/cli.py:1435`), written for `validate --history-limit`:

```python
def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"expected a whole number of at least 1, got `{value}`")
    return number
```

`--limit` was simply never switched to it. `help=` was added to this line in T101, which is
where the defect was noticed; T101 did not change the type.

## Ruled out

- **`eligible()`.** It takes no limit: `cmd_next` calls `eligible(project, args.backlog,
  claimed)` and slices the result afterwards. The baseline run returns the full, correctly
  ordered list, so ordering and filtering are sound; only the slice bound is wrong.
- **`_emit` and the `or "no eligible tasks"` fallback.** The fallback is correct for a genuinely
  empty list — it is what a backlog with nothing eligible should print. It is reached here only
  because the slice already produced an empty list, so it reports the defect rather than
  causing it.
- **A missing runtime guard in `cmd_next`.** Adding an `if args.limit < 1` check in the handler
  would work, but it would be a second way of saying what `_positive_int` already says, and it
  would refuse after the project is loaded rather than at parse time. The defect is that the
  option's `type` does not encode its contract.
- **`argparse` itself.** It behaves as declared; `int` is documented to accept negatives. The
  declaration is what is wrong.
- **Other `type=int` arguments in the codebase.** Reproduced individually; none shares the
  defect — see *Affected areas*.

## Affected areas

- `src/taskrail/cli.py` — the `next` subparser's `--limit` (the only code change). `cmd_next`
  itself needs nothing: once the value is at least 1, `[: args.limit]` is correct.
- **No other `type=int` argument is defective.** Every one was probed with `0` and a negative
  value, not merely read:

  | Site | Probe | Result |
  |------|-------|--------|
  | `cli.py:1541` `new --pts` | `new … --pts 0` | `error: points `0` is not on the scale (1, 2, 3, 5, 8, 13) [task-points-scale]` / `taskrail: the change would leave the backlog invalid; nothing was written`, exit 1, no row written |
  | `cli.py:1541` `new --pts` | `new … --pts=-5` | `error: points `-5` is not a whole number [task-points]` / nothing was written, no row |
  | `autopilot/commands.py:535` `start --count` | `autopilot start --count 0` | `taskrail: --count must be at least 1`, exit 2 |
  | `autopilot/commands.py:542` `extend --count` | handler guard at `commands.py:199` | `--count must be at least 1` before any write |
  | `importer.py:682` `import --epic-level` | `import src.md --epic-level 0` and `--epic-level=-2` | `taskrail: --epic-level must be between 2 and 6`, exit 2 both times |

  Each of these validates in its handler or through backlog validation, so `next --limit` is the
  only `type=int` argument whose bad value becomes a wrong answer. Nothing to open a follow-up
  task for.
- **DESIGN.md §7, line 673** describes `--limit` as “`--limit` keeps the first N of them”, which
  stays true of every value the CLI will accept after the fix. It does not state a minimum for
  `--history-limit` either, so no documentation change is proposed.

## Proposed fix

One line in `src/taskrail/cli.py`: change the `next` subparser's `--limit` from `type=int` to
`type=_positive_int`, leaving `default=5`, `metavar="N"` and the T101 `help=` string as they
are. `_positive_int` is defined above `build_parser()` in the same module, so nothing moves and
no helper is added.

```python
nxt.add_argument("--limit", type=_positive_int, default=5, metavar="N", help="show at most N eligible tasks (default 5)")
```

After it, `--limit 0` and `--limit=-1` exit 2 with
`argument --limit: expected a whole number of at least 1, got `0`` and the `next` usage line,
and nothing is printed to stdout.

Regression test: `tests/test_cli.py`, beside the existing
`test_next_limit_says_what_it_does_in_help`, mirroring
`tests/test_history.py::test_history_limit_must_be_positive` — assert `SystemExit` code 2 for
`--limit 0` and `--limit -1`, and that a valid limit still truncates the list.

Plus one `CHANGELOG.md` bullet under *Unreleased*: a value the CLI accepted is now refused.
