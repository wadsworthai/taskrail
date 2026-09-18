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
| `TODO.md` | Through the CLI only: the T115 follow-up row (`taskrail new`, approved at the gate) and this task's own status cell (`taskrail done`). |

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

## Decisions

All four were put at the `scope` gate and answered there; none changes behaviour. Recorded in
`docs/autopilot/decisions/T110-reword-design-md-4-where-it-says-an-id-r.md`.

1. **The wording** — the text above, taken as proposed. The alternatives were *"naming the key
   that would accept it"* without spelling the two keys out, which is shorter but makes the reader
   look them up, and §4 is exactly where they would look; and dropping *"and the value it
   expected"*, which would be incomplete, since both messages still quote the value.
2. **`CHANGELOG.md`: no bullet.** T103 already shipped the bullet for this behaviour
   (*"A refused ID now names the configuration key that would accept it"*, `CHANGELOG.md:66-72`),
   and nothing a consumer installs changes here — `DESIGN.md` is this repository's own design
   document, installed by neither `init` nor `upgrade`. The alternative was a second bullet
   describing a documentation fix for a change already recorded.
3. **The stale line numbers in the task's own description: left as they are.** The row is closed by
   this task, `taskrail edit --description` would rewrite a `TODO.md` cell that three other live
   lanes also append to, and this artifact records the real location.
4. **A follow-up task was opened for the wrapper's root resolution** — see below.

## Follow-up opened

**[T115](../../TODO.md) (E05, spike, 2 pts) — Decide how the wrapper and the CLI resolve the
repository root when the cwd is another checkout.**

`.taskrail/bin/taskrail` resolves the root from the **process cwd**, not from the wrapper's own
path, so running a worktree's own wrapper from a shell sitting in another checkout silently
operates on that other checkout. This lane met it at its first command:

```
$ .../.worktrees/T110-.../.taskrail/bin/taskrail claim T110 --run 20260918-1 --json
taskrail: warning: T110 was claimed on branch main, but its branch is T110-reword-design-md-4-…
  "branch": "main",
  "worktree": "/…/taskrail",
```

Releasing and re-claiming with `--root <worktree>` fixed it here. Three lanes of this one
autopilot run — T106, T108 and T110 — hit the same thing and worked around it the same way, which
is the rule of three met by measurement rather than by argument. The row is written as the design
question it is, not as a fix: whether the wrapper should derive `--root` from its own path,
whether the CLI should warn when the wrapper's location and the cwd disagree, and what `DESIGN.md`
§9 should say are for that task to decide. **Nothing about it is fixed here**, and this task's own
workaround — passing `--root` explicitly — is the documented one.

## Out of scope

- **Everything else in `DESIGN.md`.** T107 edits §3.1, §4's configuration example around line 145,
  §7's command table, §7.4 and a new §7.6 in the same file; none of that is touched here, and
  neither is anything else in §4 outside lines 225-226.
- **Any code, test or message.** The refusals themselves are T103's and stay as they are.
- **`CHANGELOG.md`, `README.md`, the skills and `CLAUDE.md`.** Checked above; none of them carries
  the stale claim, and no changelog bullet is added (decision 2).
- **The wrapper's root resolution.** Recorded as T115 and not touched here (decision 4).
- **`src/taskrail/cli.py`** (T109's file) and `.github/workflows/` (T108's).

## Verification

Run in this worktree after the edit. Every command and its output is real.

**1. The diff is the one hunk that was approved — two lines out, three in, nothing else moved.**

```
$ git diff --unified=0 DESIGN.md
@@ -225,2 +225,3 @@ digits, and `taskrail new` pads the number it allocates to `id_digits`. `validat
-that does not match, quoting the prefix it expected rather than the key, so a repository whose
-epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of renumbering them.
+that does not match, naming the key — `epic_prefix` or `prefix` — and the value it expected, so
+a repository whose epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of
+renumbering them.

$ git status --short
 M DESIGN.md
 M TODO.md
```

`TODO.md` carries the T115 row only; `DESIGN.md` is the single hunk above. The §4 configuration
example, §3.1, §7 and §7.4 are byte-identical.

**2. The paragraph reads as intended, inside the file's wrap.** Lines 222-227, with lengths:

```
95: An entry's `epic_prefix` (default `E`) and `id_digits` (default 3) shape that backlog's IDs: an
96: epic ID is `epic_prefix` plus two or more digits, a task ID is `prefix` plus `id_digits` or more
96: digits, and `taskrail new` pads the number it allocates to `id_digits`. `validate` refuses an ID
95: that does not match, naming the key — `epic_prefix` or `prefix` — and the value it expected, so
86: a repository whose epics are numbered `EP01` sets `epic_prefix = "EP"` here instead of
17: renumbering them.
```

**3. The stale clause is gone from the repository.**

```
$ grep -n "rather than the key" DESIGN.md ; echo "grep exit=$?"
grep exit=1
```

**4. The reworded sentence still describes the observed output**, re-run against this branch after
the edit — the same two reproductions as above, unchanged:

```
$ .taskrail/bin/taskrail --root <scratch> validate
TASKRAIL.md:7: error: epic ID `EP01` does not match epic_prefix `E` plus two or more digits [epic-id]
…
$ .taskrail/bin/taskrail --root <scratch> validate
TASKRAIL.md:15: error: task ID `X001` does not match prefix `T` plus 3 or more digits [task-id]
```

Each message names its key and quotes its value, which is what the new sentence now says.

**5. The suite passes, including the two tests that read `DESIGN.md`.**

```
$ .taskrail/bin/taskrail checks T110
== test: uv run pytest -q
[…]
1221 passed in 157.16s (0:02:37)
== lint: not configured
passed test
not configured lint
T110 in /…/.worktrees/T110-reword-design-md-4-where-it-says-an-id-r: passed
```

`lint` is **not configured** in this repository — `[checks]` defines `test` only — and the CLI
reports it as such rather than passing it silently. `tests/test_config_unknown_keys.py:33` parses
the ```` ```toml ```` fence of §4, which is not touched; `tests/test_autopilot_parked.py:286`
slices §12.7.

**6. The backlog validates, with T115 in it.**

```
$ .taskrail/bin/taskrail validate ; echo "exit=$?"
102 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```
