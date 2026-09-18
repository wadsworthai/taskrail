# T110 — Reword DESIGN.md §4 where it says an ID refusal quotes the prefix rather than the key

## Goal

[T103](T103-name-epic-prefix-in-the-refusal-for-an-e.md) changed the two ID refusals of
`validate` so each names the configuration key that would accept the ID. `DESIGN.md` §4 still
describes the behaviour T103 replaced: it says the refusal quotes *"the prefix it expected rather
than the key"*, which is now the opposite of what the CLI does. This chore rewords that one
sentence so the design document matches the code, and changes nothing else.

No behaviour, no code, no test and no message changes. `src/taskrail/backlog.py`,
`src/taskrail/project.py` and `tests/test_validate.py` — the files T103 touched — are untouched
here.

## The line numbers in the task row are stale

The row says *§4 (lines 211-215)*. The sentence is at **lines 222-226** on `origin/main` at
`5dfcd8e`, this branch's base: `DESIGN.md` grew by eleven lines between T103 writing the row and
this branch being cut. The text is unambiguous and there is only one such sentence in the file, so
this is a note, not an obstacle.

```
$ grep -n "quoting the prefix" DESIGN.md
225:that does not match, quoting the prefix it expected rather than the key, so a repository whose
```

## What the code does today

Both refusals name the key **and** quote its configured value. Verified twice: in the source, and
by running the CLI.

`src/taskrail/backlog.py:240` — the epic ID:

```python
f"epic ID `{epic_id}` does not match epic_prefix `{backlog_config.epic_prefix}` plus two or more digits",
```

`src/taskrail/project.py:43` — the task ID:

```python
f"task ID `{task.id}` does not match prefix `{backlog.config.prefix}` plus {backlog.config.id_digits} or more digits",
```

Reproduced with this branch's CLI against a scratch repository whose config is the §4 defaults
(`prefix = "T"`, `epic_prefix = "E"`, `id_digits = 3`). An epic numbered `EP01` — the example the
sentence itself uses:

```
$ .taskrail/bin/taskrail --root <scratch> validate ; echo "exit=$?"
TASKRAIL.md:7: error: epic ID `EP01` does not match epic_prefix `E` plus two or more digits [epic-id]
TASKRAIL.md:9: error: section `EP01` is not in the Epics table [epic-unlisted]
history: not checked (no commits)
0 task(s) in 1 backlog(s): 2 error(s), 0 warning(s)
exit=1
```

And a task numbered `X001`, with the epic corrected to `E01` so the section parses:

```
$ .taskrail/bin/taskrail --root <scratch> validate ; echo "exit=$?"
TASKRAIL.md:15: error: task ID `X001` does not match prefix `T` plus 3 or more digits [task-id]
history: not checked (no commits)
1 task(s) in 1 backlog(s): 1 error(s), 0 warning(s)
exit=1
```

So the sentence is wrong in both halves of its contrast: the key **is** named, and the value is
still quoted alongside it.

## Change set

| File | What changes |
|---|---|
| `DESIGN.md` | One sentence of §4: lines 225-226 replaced by three lines, so the paragraph at 222-226 becomes 222-227. Nothing else in the file. |
| `docs/chores/T110-…md`, `docs/chores/README.md` | This artifact and its index row. |
| `TODO.md` | This task's row, through the CLI only (`taskrail done`). |

### `DESIGN.md` — the sentence

Lines 222-226 today. Lines 222, 223 and 224 are **not** touched — the sentence begins at the tail
of line 224, which stays as it is:

```
An entry's `epic_prefix` (default `E`) and `id_digits` (default 3) shape that backlog's IDs: an
epic ID is `epic_prefix` plus two or more digits, a task ID is `prefix` plus `id_digits` or more
digits, and `taskrail new` pads the number it allocates to `id_digits`. `validate` refuses an ID
that does not match, quoting the prefix it expected rather than the key, so a repository whose
epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of renumbering them.
```

Proposed, replacing lines 225-226:

```
that does not match, naming the key — `epic_prefix` or `prefix` — and the value it expected, so
a repository whose epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of
renumbering them.
```

The clause that was false is gone; the `EP01` example the row asks to keep follows unchanged, and
now actually follows from the sentence before it — the message names `epic_prefix`, so the reader
is told which key to set. Naming both keys matches the CHANGELOG bullet T103 already shipped
(*"Both messages now name the key: `epic_prefix` for an epic ID and `prefix` for a task ID"*), and
keeping *"and the value it expected"* keeps the other half true: the value is still quoted.

The new lines are 95, 86 and 17 characters, inside the paragraph's existing 96-column wrap.

## Decisions needed

1. **The wording.** Recommended above. Alternatives: *"naming the key that would accept it"*
   without spelling out `epic_prefix` or `prefix`, which is shorter but makes the reader look the
   keys up; or dropping *"and the value it expected"*, which would be incomplete, since both
   messages still quote the value.
2. **`CHANGELOG.md`: no bullet.** Recommended. T103 already shipped the bullet for this behaviour
   (*"A refused ID now names the configuration key that would accept it"*, `CHANGELOG.md:66-72`),
   and nothing a consumer installs changes here — `DESIGN.md` is this repository's own design
   document and is not installed by `init` or `upgrade`. The alternative is a second bullet
   describing a documentation fix for a change already recorded.
3. **The stale line numbers in the task's own description.** Recommended: leave them. The row is
   closed by this task, `taskrail edit --description` would rewrite a `TODO.md` cell that three
   other lanes in this run also append to, and this artifact records the real location.

## Out of scope

- **Everything else in `DESIGN.md`.** T107 edits §3.1, §4's configuration example around line 145,
  §7's command table, §7.4 and a new §7.6 in the same file; none of that is touched here, and
  neither is anything else in §4 outside lines 225-226.
- **Any code, test or message.** The refusals themselves are T103's and stay as they are.
- **`CHANGELOG.md`, `README.md`, the skills and `CLAUDE.md`.** Checked below; none of them carries
  the stale claim.
- **`src/taskrail/cli.py`** (T109's file) and `.github/workflows/` (T108's).

## Verification

How the change will be proven, at the `implement` stage:

1. `git diff DESIGN.md` is a single hunk covering lines 225-226, two lines out and three in, with
   no line outside them changed.
2. `grep -n "rather than the key" DESIGN.md` finds nothing.
3. The two CLI reproductions above are re-run against the edited branch and still print the same
   messages, so the reworded sentence describes the observed output rather than this brief.
4. `taskrail checks T110` — `uv run pytest -q` — passes. Two tests read `DESIGN.md`:
   `tests/test_config_unknown_keys.py` parses the `toml` fence of §4, and
   `tests/test_autopilot_parked.py` reads §12.7; neither touches this paragraph, and the fence is
   not edited.
5. `taskrail validate` exits 0.
