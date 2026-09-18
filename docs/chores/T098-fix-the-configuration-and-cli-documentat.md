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

### 5. `docs/chores/T098-…md` and `docs/chores/README.md`

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

## Out of scope

- **Any behaviour.** No code, no tests, no CLI surface, no skills, no `CLAUDE.md`.
- **The error message at `backlog.py:240`** that quotes the prefix's value and never names
  `epic_prefix`. It is code. Worth a follow-up only if the human wants it; §4 now carries the
  answer either way.
- **Flags that exist but §7 never mentions** — `epic add --id`, `epic add --file`, `next --limit`,
  `list --backlog/--kind/--allow-invalid`. Verified present in the parser, but they are T088's
  fifth-and-beyond finding, and **T095** (open, at its own gate) is the task that asks the human
  whether those options are wanted at all. Documenting them now could document something the human
  is about to retire, so no follow-up is opened here: T095 owns the question.
- **Rewording anything in §4 or §7 that is merely terse but true**, including the `list` row's
  "computed blocked and eligible state" and the paragraphs T094 and T096 added to §4 and §12.10.
- **The reading map** at the top of the file: it stays untouched, as the task's row asks.

## Verification

This is a documentation change, so verification is that the document now matches the program:

1. `grep -n "epic_prefix\|id_digits" DESIGN.md` shows both keys in §4's example and in the new
   sentence.
2. `grep -n "kind add\|--eligible" DESIGN.md` returns nothing.
3. Each value the new text asserts is checked against the source it describes: defaults and ranges
   against `src/taskrail/config.py:247-254`, the `--state` values against `taskrail list --help`,
   the local-kind route against §5.2 and `src/taskrail/kinds.py`.
4. `taskrail checks T098` (the `test` check, `uv run pytest -q`) passes, and `taskrail validate`
   reports no errors — neither can see the prose, but both prove nothing else was disturbed.
5. `git diff --stat` on the branch shows `DESIGN.md` plus this artifact, its index row and the
   task's own row, and nothing else.

Results are recorded below at the `implement` stage.
