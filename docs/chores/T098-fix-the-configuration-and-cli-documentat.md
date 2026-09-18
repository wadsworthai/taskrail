# T098 — Fix the configuration and CLI documentation defects DESIGN.md carries

## Goal

`DESIGN.md` is the reference for taskrail's configuration and CLI. Its reading map promises
"Every key of `.taskrail/config.toml` and its default" for §4 and "Every command and flag" for §7.
The [T088 spike](../spikes/T088-measure-the-cli-and-configuration-surfac.md) measured both against
the live parser and found four places where the document and the program disagree (E6, E7): two
configuration keys the document never shows, and two commands the document offers that the parser
refuses.

This chore fixes exactly those four, in the file as it stands. [T089](../spikes/T089-decide-whether-to-split-design-md-by-top.md)
decided `DESIGN.md` is **not** split, and T093 added the reading map at its top, so the file being
edited is the file that stays. Nothing behavioural changes: no code, no tests, no CLI surface.

## The four defects, verified in this worktree

Every command below was run from
`/thezone/shared/repositories/utils/taskrail/.worktrees/T098-fix-the-configuration-and-cli-documentat`
at `464b958` (the branch's base), after T094 and T096 had already merged into it.

**1. `[[backlog]].epic_prefix` is absent from the whole document.** Confirmed, as stated:

```
$ grep -c "epic_prefix" DESIGN.md
0
```

It is real and parsed: `src/taskrail/config.py:247-251` reads it with the default `"E"`, requires
1–4 uppercase letters and refuses `epic_prefix == prefix`; `src/taskrail/config.py:128` lists it
among the known `[[backlog]]` keys; `src/taskrail/backlog.py:200,240` builds the epic-ID pattern
from it and `src/taskrail/cli.py:1327` uses it when `epic add` allocates an ID.

**2. `id_digits` — the row says "omits", and the truth is narrower.** It is *not* absent from the
document; it appears exactly once, and only in §7.3's account of what `taskrail import` refuses:

```
$ grep -n "id_digits" DESIGN.md
982:  `id_digits` is refused, with the `id_digits` value that would keep it when only padding differs.
```

(T088 recorded it as "not in §4", which is accurate; the backlog row's "omits ... id_digits"
reads as "absent from the document", which is not. The defect stands as *§4's example omits it and
nothing says it sets the width of generated IDs* — `src/taskrail/ids.py:148`
pads to `id_digits`, `src/taskrail/project.py:36,43` validates task IDs against it, and
`src/taskrail/config.py:252-254` defaults it to 3 and requires 1–6.)

**3. `taskrail kind add <dir>` does not exist.** Confirmed:

```
$ .taskrail/bin/taskrail kind add x
usage: taskrail kind [-h] {list} ...
taskrail kind: error: argument kind_command: invalid choice: 'add' (choose from list)
exit=2
```

§5.2 documents the real route: a repository's own kind lives in `.taskrail/types/<kind>/`, an
override in `.taskrail/overrides/<kind>/`. Installing one is a file copy, not a command.

**4. `taskrail list --eligible` does not exist; the flag is `--state`.** Confirmed:

```
$ .taskrail/bin/taskrail list --eligible
taskrail: error: unrecognized arguments: --eligible
exit=2

$ .taskrail/bin/taskrail list --help
usage: taskrail list [-h] [--json] [--fetch] [--backlog BACKLOG] [--epic EPIC]
                     [--state {pending,claimed,blocked,done-branch,discarded-branch,done,discarded}]
                     [--kind KIND] [--allow-invalid]
```

## Change set

Two files, plus this artifact and its index row. Both `DESIGN.md` hunks are far from the reading
map at the top of the file.

### 1. `DESIGN.md` §4 — the example config's first `[[backlog]]` entry (lines 135–141)

Two lines added after `prefix = "T"`, with comments in the block's existing style (comments start
at column 34):

```toml
[[backlog]]
name = "template"
prefix = "T"
epic_prefix = "E"                # epic IDs: 1-4 uppercase letters, different from `prefix`
id_digits = 3                    # digits an allocated ID is padded to: T001; 1 to 6
file = "TODO.md"
mainline = "main"
artifacts = "docs"
may_depend_on = []               # T tasks may depend only on T tasks
```

The second `[[backlog]]` entry (`product`) is left untouched, so the example also shows that both
keys are optional.

### 2. `DESIGN.md` §4 — one sentence of prose after the example block

Inserted immediately after the closing ``` of the example and before the `[autopilot]` paragraph,
so it does not touch the paragraphs T094 and T096 added at the end of §4:

> An entry's `epic_prefix` (default `E`) and `id_digits` (default 3) shape that backlog's IDs: an
> epic ID is `epic_prefix` plus two or more digits, a task ID is `prefix` plus `id_digits` or more
> digits, and `taskrail new` pads the number it allocates to `id_digits`. `validate` refuses an ID
> that does not match, quoting the prefix it expected rather than the key, so a repository whose
> epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of renumbering them.

Why prose and not only the two lines: the message a repository actually hits
(`epic ID \`EP01\` does not match \`E\` plus two or more digits`, `backlog.py:240`) quotes the
prefix's *value* and never names the key, so a reader cannot search for the fix. Fixing that
message is code and out of scope; making §4 carry the answer is not.

### 3. `DESIGN.md` §7 — the `list` row (line 644)

`[--eligible]` becomes `[--state STATE]`, and the purpose gains a clause naming the values, so the
row still says what `--eligible` used to promise:

> `taskrail list [--epic E01] [--state STATE] [--fetch]` | Tasks, with computed blocked and
> eligible state; `--state` keeps only tasks in that state (`pending`, `claimed`, `blocked`,
> `done-branch`, `discarded-branch`, `done`, `discarded`); each `--json` entry carries `show`'s
> task fields, `worktree` and `worktree_base` included, without `kind_descriptor` and `prior_work`

### 4. `DESIGN.md` §7 — the `kind` row (line 660)

`taskrail kind add <dir>` is removed from the command cell, and "install a local kind" in the
purpose is replaced by a pointer to §5.2's real route:

> `taskrail kind list` | Inspect resolved kinds, each `--json` entry with its effective `commit`
> policy, `commit_source` and effective stage `commit` (§5.1). There is no command that installs a
> kind: copy its descriptor into `.taskrail/types/<kind>/`, or an override into
> `.taskrail/overrides/<kind>/` (§5.2)

### 5. `DESIGN.md` §7 — four flags that exist but the table never mentioned (added at the gate)

Approved as a widening of the scope gate, because **T095's questionnaire came back "route A, keep
and document" for every option**, with "one line in §7's command table, via T098" as the agreed
route for exactly these four. They are documented inside the rows of the commands that own them,
which is the table's form — one row per command, its flags in the command cell — rather than as
four new rows, which would list the same commands twice.

The `next` row gains `[--limit N]` and "`--limit` keeps the first N of them"; the epic row becomes:

> `taskrail epic add [--id E##] [--own-file \| --file PATH]` / `taskrail epic split <E##> [--file PATH]` |
> Add an epic inline or in a file of its own; move an inline epic to its own file. `add` allocates
> `epic_prefix` plus two digits, one above the backlog's highest, unless `--id` names one (exit 5
> if that epic exists); `--own-file` writes `todo/<id>-<slug>.md` and `--file` the path it names.
> `split` writes `todo/<id>-<slug>.md` unless `--file` names another

### 6. `docs/chores/T098-…md` and `docs/chores/README.md`

This artifact and one appended index row.

## Decisions needed

Recorded at the `scope` gate; both were put to the orchestrator with these recommendations.

1. **How much to say about `epic_prefix` and `id_digits`** — recommendation: change set items 1
   *and* 2 (two example lines **and** the one-sentence paragraph). The minimum (item 1 alone)
   leaves a reader who hits the `epic-id` error with a message that never names the key.
   Alternatives: item 1 only; or a fuller per-key table for `[[backlog]]`, which no other table in
   §4 has and which would widen the diff well past this chore.
2. **What to do with `kind add`** — recommendation: delete it and point the `kind list` row at
   §5.2 (item 4), so a reader who came looking for `kind add` is told where the capability lives.
   Alternative: delete the words and add nothing, leaving the reader with silence.

**Answered at the gate** (record: `docs/autopilot/decisions/T098-fix-the-configuration-and-cli-documentat.md`,
commit `fc91969`): both as recommended — items 1 and 2 together, and the §5.2 pointer — plus the
widening in change-set item 5, T095's four flags, which this task had deliberately held back.

## Out of scope

- **Any behaviour.** No code, no tests, no CLI surface, no skills, no `CLAUDE.md`.
- **The error message at `backlog.py:240`** that quotes the prefix's value and never names
  `epic_prefix`. It is code. The human said yes to fixing it when this finding reached them
  through T095, and it gets its own task there, so the document will explain the key and the
  message will name it.
- ~~Flags that exist but §7 never mentions~~ — held back at the scope gate while **T095** was
  still asking the human whether those options are wanted at all. T095 came back "keep and
  document" for all of them, so `epic add --id`, `epic add --file`, `epic split --file` and
  `next --limit` were brought into this task as change-set item 5. Two of T095's answers stay out
  because they are **code**, and T095 is opening its own chores for them: `next --limit`'s missing
  argparse `help=` string, and `--owner`'s sentence, which belongs in §6.2, not §7.
- **`list --backlog`, `--kind` and `--allow-invalid`**, which the `list` row still does not name.
  They were not part of T088's defects nor of T095's four, and the §7 rows are summaries, not
  `--help` output.
- **Rewording anything in §4 or §7 that is merely terse but true**, including the `list` row's
  "computed blocked and eligible state" and the paragraphs T094 and T096 added to §4 and §12.10.
- **The reading map** at the top of the file: it stays untouched, as the task's row asks.

## Verification

This is a documentation change, so the verification that matters is that every sentence now
asserts something the program actually does. Each was run, not reasoned about.

**The defects are gone.**

```
$ grep -n "kind add\|--eligible" DESIGN.md
(no output, exit 1)

$ grep -n "epic_prefix\|id_digits" DESIGN.md
138:epic_prefix = "E"                # epic IDs: 1-4 uppercase letters, different from `prefix`
139:id_digits = 3                    # digits an allocated ID is padded to: T001; 1 to 6
211:An entry's `epic_prefix` (default `E`) and `id_digits` (default 3) shape that backlog's IDs: an
212:epic ID is `epic_prefix` plus two or more digits, a task ID is `prefix` plus `id_digits` or more
213:digits, and `taskrail new` pads the number it allocates to `id_digits`. `validate` refuses an ID
215:epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of renumbering them.
667:| `taskrail epic add [--id E##] …
990:  `id_digits` is refused, with the `id_digits` value that would keep it when only padding differs.
```

**The new §4 sentence, exercised in a throwaway repository** (`taskrail init` in a scratch git
repo, then `epic_prefix = "EP"` and `id_digits = 4` written into its config):

```
$ taskrail --root <probe> validate            # after setting epic_prefix = "EP"
TODO.md:7: error: epic ID `E01` does not match `EP` plus two or more digits [epic-id]
...
exit=1

$ taskrail --root <probe2> new --epic E01 --kind chore --title "Probe the pad width" --json
{ "id": "T0001", ...                          # with id_digits = 4
```

Both halves of the sentence hold: the ID width follows `id_digits`, and the refusal quotes the
prefix's **value** (`EP`) and never the key — which is why the sentence exists.

**The §7 rows, exercised against the live CLI:**

```
$ taskrail list --state claimed
T098   ⬜ claimed     chore     1pt  E08   Fix the configuration and CLI documentation defects …

$ taskrail next --limit 2
T003   ⬜ pending     chore     2pt  E01   Install taskrail in a first consumer project  ← T002
T057   ⬜ pending     spike     2pt  E02   Check autopilot compaction and old-lane messaging …

$ taskrail --root <probe> epic add --id E07 --name Reports --objective … --own-file --json
{ "id": "E07", "file": "todo/E07-reports.md", … }

$ taskrail --root <probe> epic add --name Later --objective … --json
{ "id": "E08", …                              # one above the backlog's highest

$ taskrail --root <probe> epic add --id E07 --name Dup --objective x
taskrail: epic `E07` already exists
exit=5                                        # the exit 5 the row now states

$ taskrail --root <probe> epic add --name Custom --objective … --file todo/custom.md --json
{ "id": "E09", "file": "todo/custom.md", … }

$ taskrail --root <probe> epic split E01 --file todo/split-here.md --json
{ "id": "E01", "file": "todo/split-here.md", … }
```

The removed `kind add` route was checked against `src/taskrail/kinds.py:15-17`
(`LOCAL_DIR = .taskrail/types`, `OVERRIDE_DIR = .taskrail/overrides`), and the `--state` values
against `taskrail list --help`.

**The repository is undisturbed.**

```
$ .taskrail/bin/taskrail checks T098
== test: uv run pytest -q
1196 passed in 164.28s (0:02:44)
== lint: not configured
passed test
not configured lint
T098 in …/.worktrees/T098-fix-the-configuration-and-cli-documentat: passed
exit=0

$ .taskrail/bin/taskrail validate
89 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0

$ git diff --stat        # the implement hunks
 DESIGN.md | 16 ++++++++++++----
 1 file changed, 12 insertions(+), 4 deletions(-)
```

Six hunks in `DESIGN.md`, all inside §4's example, the paragraph after it, and four rows of §7's
table. The reading map at the top of the file, the paragraphs T094 and T096 added to §4 and §12.10,
and every other section are untouched.

## Documentation sync (the `docs` stage)

Nothing to change: the change *is* documentation, and no other document in the repository repeats
what it corrects.

```
$ grep -rn -- "kind add\|--eligible" README.md src/ .claude/ .taskrail/ examples/
(no output, exit 1)

$ grep -rln "epic_prefix\|id_digits" README.md src/taskrail/skills src/taskrail/integrations examples/ .claude/
(no output, exit 1)
```

The only other occurrences anywhere are in finished task write-ups under `docs/` — T079's chore and
T088's spike and decision record — which are accounts of what was true when they were written and
are deliberately left alone.

**No `CHANGELOG.md` entry.** Its `Unreleased` section records user-facing behaviour and skill
changes; `DESIGN.md` is a repository document, not shipped. T093 (the reading map) and T096 (§4's
`handoff` line) are the precedent: both changed `DESIGN.md` only and added no entry.

**No follow-up tasks opened here.** The three code items this task uncovered or confirmed — the
`epic-id` message at `backlog.py:240` that never names the key, `next --limit`'s missing argparse
`help=` string, and `--owner`'s sentence, which belongs in §6.2 — are all owned by T095, which is
opening its own chores for them.
