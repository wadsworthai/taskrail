# T101 — Give `next --limit` a help string so it is discoverable from `--help`

Kind: chore · Epic: E08 · Status: implemented

## Goal

`taskrail next --help` prints the bare line `--limit LIMIT`: the argument carries no `help=`, so
the only option of `next` that shapes its output is invisible to anyone reading `--help`. T088 and
T095 found it absent from every skill, test and document as well; T098 closed the documentation
half by giving `DESIGN.md` §7 a `--limit` clause. This chore closes the code half: one `help=`
string on the argument in `src/taskrail/cli.py`, in the voice of its neighbours.

## Grounding: what is measured on this branch

Base `origin/main`, `5d605ca`.

- `src/taskrail/cli.py:1483` — `nxt.add_argument("--limit", type=int, default=5)`, the only
  argument of `next` with neither `help=` nor `metavar=` (`--fetch` at `:1481` has help;
  `--backlog` at `:1482` has none either — see *Out of scope*).
- `taskrail next --help` ends with `--backlog BACKLOG` and `--limit LIMIT`, both unexplained.
- `DESIGN.md:654` already documents the flag: `` `taskrail next [--limit N] [--fetch]` `` … "
  `--limit` keeps the first N of them". Nothing is left to say there, so `DESIGN.md` is not touched.
- `grep -rn -- "--limit" src/taskrail/skills/ src/taskrail/integrations/ README.md tests/` matches
  nothing: the flag is named in no skill, no integration note, no README line and no test.
- The nearest sibling, `validate --history-limit` (`cli.py:1459–1465`), is the house style for a
  limit flag: `metavar="N"`, and `help="examine at most N commits changing backlog files (default
  500)"` — terse, lower case, no full stop, default stated.

## Change set

| File | Change |
|---|---|
| `src/taskrail/cli.py:1483` | The `--limit` argument of `next` gains `metavar="N"` and `help="show at most N eligible tasks (default 5)"`. One argument, one line. |
| `tests/test_cli.py` | `test_next_limit_says_what_it_does_in_help`, beside the existing `next` tests: the `--limit` action of the `next` subparser has a non-empty `help`, and its help text spells the flag `--limit N`. |
| `docs/chores/T101-give-next-limit-a-help-string-so-it-is-d.md` | This artifact. |
| `docs/chores/README.md` | Index row for T101, added at implement. |
| `TODO.md` | Only the row's `✅` at close, through `taskrail done`. |

## Decisions — answered at the `scope` gate

**1. The exact wording, and whether `metavar="N"` comes with it.** — **Answered: both.**
Recommended and taken: `nxt.add_argument("--limit", type=int, default=5, metavar="N", help="show at most N
eligible tasks (default 5)")`, printing `--limit N   show at most N eligible tasks (default 5)`.
It matches `--history-limit`'s voice and shape, and `metavar="N"` also makes `--help` agree with
`DESIGN.md` §7, which writes the flag as `[--limit N]` while `--help` says `--limit LIMIT`.
Alternative: help only, no metavar — `help="show at most this many tasks (default 5)"` — strictly
one added keyword, but leaves `--help` reading `LIMIT` where the design document says `N`.

**2. Whether a test is warranted, and how wide.** — **Answered: a test for this flag only.**
Recommended and taken: a test for this flag only — one assertion beside the existing `next` tests in
`tests/test_cli.py`, that `next`'s `--limit` has a help string. It costs three lines, needs no new
convention, and pins exactly what this task fixes.
Alternatives: (a) no test — the flag would again be one careless edit from silent; (b) a
parser-wide test that every argument of every command has `help=`. (b) is measured to be far wider
than this task: walking `build_parser()` reports **65 arguments with no `help=`**, across
`list`, `show`, `claim`, `release`, `reserve-id`, `unreserve-id`, `upgrade`, `new`, `workspace`,
`done`, `discard`, `reopen`, `edit`, `branch`, `review`, `checks`, `epic`, `kind` and nine
`autopilot` subcommands. It could only land with a 64-entry exemption list, or by writing 64 more
help strings — a new rule for the whole CLI, which KISS and YAGNI in `CLAUDE.md` put outside a
1-point chore. If the rule is wanted, it belongs in its own task.

**3. Whether this needs a `CHANGELOG.md` entry.** — **Answered: no; a help string is not a
behaviour change.**
Recommended and taken: no. `CHANGELOG.md` is not in this lane's touch map, and the *Unreleased* entries are
behaviour changes (T094, T091), while T095–T098's documentation and audit work added none. If the
answer is yes, the entry would be one bullet under *Unreleased*.

## Out of scope

- **65 arguments of the CLI carry no `help=`**, `next --backlog` among them. Measured on this
  branch by walking `build_parser()`: `list --backlog --epic --state --kind`, `show id
  --allow-invalid`, `next --backlog --limit` (this task fixes `--limit`), `claim id
  --allow-invalid`, `release id --owner --local-only`, `reserve-id --backlog --owner`,
  `unreserve-id id`, `upgrade --force`, `integration list --json`, `self upgrade --json`,
  `new --epic --kind --title --pts --description --owner --allow-invalid`, `workspace id`,
  `done id --owner`, `discard id --owner`, `reopen id`, `edit id --title --kind`, `branch id
  --allow-invalid`, `review id`, `checks id --allow-invalid`, `epic add --name --objective
  --done-when --backlog --json`, `epic split id --backlog --json`, `kind list --json`, and
  `autopilot extend|lane|decision|approve-governing|notify|status|close|merged` (16 arguments).
  **Recorded here, and no task opened** — by the gate's ruling: opening one would commit someone to
  writing 64 help strings, or to a rule with a 64-entry exemption list, because one flag went
  unnoticed once. Whether the CLI should require `help=` everywhere is the human's call, and this
  record is what it rests on.
- **`--limit` takes any `int`**: `--limit 0` prints "no eligible tasks" and a negative value
  silently drops tasks from the end (`tasks[: args.limit]` in `cmd_next`), where the sibling
  `--history-limit` uses `type=_positive_int`. A concrete defect with a bounded fix, so it is
  **T109** (bug, 1 pt, E08, depends on T101 because the fix edits this same argument). Not fixed
  here: a behaviour change is not this chore's change set.
- `DESIGN.md` and `README.md`: verified above that §7 already documents `--limit`; T100 is
  rewriting README. Not touched.
- Skills, integration notes and the installed copies under `.claude/`: nothing there names the
  flag, and a help string does not change what they say.

## Verification

Run in this worktree, on the branch, with `.taskrail/bin/taskrail` (the CLI from this checkout's
source).

`taskrail next --help` — the flag now explains itself, and the usage line spells it `--limit N`,
as `DESIGN.md` §7 does:

```
usage: taskrail next [-h] [--json] [--fetch] [--backlog BACKLOG] [--limit N]

Eligible tasks in order: points ascending, then file order.

options:
  -h, --help         show this help message and exit
  --json             machine-readable output
  --fetch            first fetch branch records mirrored to
                     [git].branch_record_remote
  --backlog BACKLOG
  --limit N          show at most N eligible tasks (default 5)
```

`taskrail next --limit 2` still keeps the first two, and the default is still 5:

```
$ taskrail next --limit 2
T102   ⬜ pending     chore     1pt  E08   Document --owner and TASKRAIL_OWNER in the claims section of DESIGN.md  ← T095
T103   ⬜ pending     chore     1pt  E08   Name epic_prefix in the refusal for an epic ID that does not match it  ← T095

$ taskrail next
T102   ⬜ pending     chore     1pt  E08   Document --owner and TASKRAIL_OWNER in the claims section of DESIGN.md  ← T095
T103   ⬜ pending     chore     1pt  E08   Name epic_prefix in the refusal for an epic ID that does not match it  ← T095
T104   ⬜ pending     chore     1pt  E08   State in the core skill that show --fetch needs branch_record_remote  ← T097
T003   ⬜ pending     chore     2pt  E01   Install taskrail in a first consumer project  ← T002
T057   ⬜ pending     spike     2pt  E02   Check autopilot compaction and old-lane messaging with a scripted probe
```

The new test was observed failing with only `cli.py` reverted (`git stash push src/taskrail/cli.py`),
so it does pin the fix:

```
>       assert commands["next"]._option_string_actions["--limit"].help
E       AssertionError: assert None
E        +  where None = _StoreAction(option_strings=['--limit'], … help=None, metavar=None).help
FAILED tests/test_cli.py::test_next_limit_says_what_it_does_in_help
1 failed, 8 deselected in 0.08s
```

`taskrail checks T101 --stage implement`:

```
== test: uv run pytest -q
1197 passed in 166.80s (0:02:46)
== lint: not configured
passed test
not configured lint
T101 in …/.worktrees/T101-give-next-limit-a-help-string-so-it-is-d: passed
```

`lint` is not configured in this repository — the task's `checks` map defines `test` only.

`taskrail validate` — at close.

## `docs` stage: nothing to update

Ran and found no documentation to change, re-checked on the finished branch:

- `DESIGN.md:654` already documents the flag (`[--limit N]`, "`--limit` keeps the first N of
  them"), added by T098 — which is why this task was code only.
- `grep -rn -- "--limit" .claude/ README.md CHANGELOG.md src/taskrail/skills/
  src/taskrail/integrations/ examples/` (excluding `--history-limit`) matches nothing: no skill,
  no integration note, no installed copy, no README or example names the flag, so nothing there
  can be out of date with a help string. No `taskrail upgrade` is needed.
- No `CHANGELOG.md` entry, by decision 3: a help string is not a behaviour change.
- Follow-up opened: **T109** (bug, 1 pt) for `--limit`'s type. Nothing opened for the 65
  help-less arguments, by the gate's ruling; the enumeration above is the record.
