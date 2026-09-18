# T101 — Give `next --limit` a help string so it is discoverable from `--help`

Kind: chore · Epic: E08 · Status: scoped

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
| `src/taskrail/cli.py:1483` | The `--limit` argument of `next` gains `metavar="N"` and `help="show at most N eligible tasks (default 5)"`. One argument, one line (wrapped as the file's style requires). |
| `tests/test_cli.py` | One assertion next to the existing `next` tests: the `--limit` action of the `next` subparser has a non-empty `help`. Subject to decision 2. |
| `docs/chores/T101-give-next-limit-a-help-string-so-it-is-d.md` | This artifact. |
| `docs/chores/README.md` | Index row for T101, added at implement. |
| `TODO.md` | Only the row's `✅` at close, through `taskrail done`. |

## Decisions needed

**1. The exact wording, and whether `metavar="N"` comes with it.**
Recommended: `nxt.add_argument("--limit", type=int, default=5, metavar="N", help="show at most N
eligible tasks (default 5)")`, printing `--limit N   show at most N eligible tasks (default 5)`.
It matches `--history-limit`'s voice and shape, and `metavar="N"` also makes `--help` agree with
`DESIGN.md` §7, which writes the flag as `[--limit N]` while `--help` says `--limit LIMIT`.
Alternative: help only, no metavar — `help="show at most this many tasks (default 5)"` — strictly
one added keyword, but leaves `--help` reading `LIMIT` where the design document says `N`.

**2. Whether a test is warranted, and how wide.**
Recommended: a test for this flag only — one assertion beside the existing `next` tests in
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

**3. Whether this needs a `CHANGELOG.md` entry.**
Recommended: no. `CHANGELOG.md` is not in this lane's touch map, and the *Unreleased* entries are
behaviour changes (T094, T091), while T095–T098's documentation and audit work added none. If the
answer is yes, the entry would be one bullet under *Unreleased*.

## Out of scope

- **`next --backlog` has no `help=` either**, and 63 further arguments across the CLI lack one
  (list above). Reported, not fixed: that is what decision 2 asks about.
- **`--limit` takes any `int`**: `--limit 0` prints "no eligible tasks" and a negative value
  silently drops tasks from the end (`tasks[: args.limit]`), where the sibling `--history-limit`
  uses `type=_positive_int`. Behaviour change, not a help string — a follow-up task if wanted.
- `DESIGN.md` and `README.md`: verified above that §7 already documents `--limit`; T100 is
  rewriting README. Not touched.
- Skills, integration notes and the installed copies under `.claude/`: nothing there names the
  flag, and a help string does not change what they say.

## Verification

- `taskrail next --help` shows the new line (output recorded here at implement).
- `taskrail next --limit 2` still returns two rows, and `--limit` keeps its default of 5.
- `taskrail checks T101 --stage implement` — the repository's full `uv run pytest -q` suite.
- `taskrail validate`.
