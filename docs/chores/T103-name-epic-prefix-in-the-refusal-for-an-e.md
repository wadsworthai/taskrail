# T103 — Name `epic_prefix` in the refusal for an epic ID that does not match it

Kind: chore · Epic: E08 · Points: 1 · Depends on: T095

## Goal

`validate` refuses an epic ID that does not match the backlog's `epic_prefix` by quoting the
prefix's **value** and never naming the key, so a repository whose epics are `EP01` is told what
taskrail expected but not which configuration key would accept what it has. T095 ran the failure
for real and T098 has since documented the key in `DESIGN.md` §4; this task puts the key in the
message, where the person who hits the error is looking.

Reproduced in this worktree against a throwaway repository whose epics are `EP01`, default
configuration:

```
$ uv run taskrail --root <tmp>/repro validate
TODO.md:7: error: epic ID `EP01` does not match `E` plus two or more digits [epic-id]
TODO.md:9: error: section `EP01` is not in the Epics table [epic-unlisted]
history: not checked (not a git repository)
0 task(s) in 1 backlog(s): 2 error(s), 0 warning(s)
exit=1
```

## Change set

| File | Change |
|------|--------|
| `src/taskrail/backlog.py` | Line 240, the `epic-id` message: name the key before its value — `` epic ID `EP01` does not match epic_prefix `E` plus two or more digits ``. |
| `src/taskrail/project.py` | Line 43, the `task-id` message, the sibling the task's description names: `` task ID `X001` does not match prefix `T` plus 3 or more digits ``. |
| `tests/test_validate.py` | One test for each message, asserting the **key name** appears — not the full wording. |
| `docs/chores/T103-…md`, `docs/chores/README.md` | This artifact and its index row. |
| `CHANGELOG.md` | One bullet under *Unreleased* (docs stage; see **Decisions needed** 3). |

Nothing else changes: the error codes (`epic-id`, `task-id`), the exit codes, the regexes and the
`--json` shape all stay as they are. This is a message change.

### Why this wording

House style, read before choosing:

| Where | Message | What it does with a key |
|-------|---------|-------------------------|
| `config.py:249` | ``backlog `main`: epic_prefix `EP` must be 1-4 uppercase letters`` | key bare, value in backticks |
| `project.py:63` | ``kind `x` is not allowed (kinds.allowed: a, b)`` | key named with its value |
| `importer.py:366` | ``…; IDs are kept as written, so set id_digits = 4 for backlog `main` `` | key named, actionable |
| `backlog.py:108` | ``[columns].aliases names column(s) differently: use …`` | key named |

`epic_prefix `E`` follows `config.py`'s own shape for this exact key, is the smallest change that
makes the key greppable, and keeps the sentence. Printed with the `file:line:` prefix it is 97
characters against 85 today, next to 93 for the existing `task-status` message — no length
problem.

Rejected: appending `(epic_prefix: E)` (says the value twice); an actionable hint in the
importer's shape, `` set epic_prefix = "EP" `` (it has to *derive* a prefix from the offending ID,
which is new logic in a message-only task, and no sensible suggestion exists for a malformed ID).

## Decisions needed

**1. The sibling message — in this task or a follow-up?**
The task's description in `TODO.md` ends "*and keep the same shape for the prefix refusal in
`project.py` if it has the same defect*", so the sibling is already inside the boundary the row
asks for. It does have the same defect: `project.py:43` quotes `` `T` `` and never names `prefix`.
**Recommendation: fix both here** — two messages of one family, one word each, one reviewer pass.
Alternative: `backlog.py` only and a follow-up task for `project.py`.

A third member exists, `importer.py:362`, which opens with the same clause for `taskrail import`.
Its message already names `id_digits` in the hint it appends, so the prefix half is the only gap.
**Recommendation: leave it out and note it** — it is a different command with its own tested
message, and the row does not name it. (Checked: `tests/test_import.py:463` asserts the substring
`` `T` ``, which the proposed wording would keep, so including it would not break that test
either.) Alternative: include it for a uniform family; or open a follow-up task.

**2. `id_digits` in the `task-id` message.**
`project.py`'s message also quotes the digit count (`3`) without naming `id_digits`.
**Recommendation: leave it.** The row asks for "the prefix refusal", the number is
self-explanatory where the prefix letters are not, and every grammar that names the key reads
badly (`plus id_digits 3 or more digits`). Alternative: name it and reword the whole clause.

**3. A `CHANGELOG.md` entry.**
`CHANGELOG.md` holds user-facing changes and this changes what every reader of a failed
`validate` sees. **Recommendation: one short bullet under *Unreleased*.** Risk: three other lanes
in this run may add their own bullets to the same section, and a prose conflict there is not on
the orchestrator's known-conflict list. Alternative: no entry — there is precedent either way
(T094/T100 got bullets; T098, documentation-only, did not).

## Out of scope

- `config.py`, `install.py`, `DESIGN.md`, `README.md`, `CLAUDE.md` and the shipped skills — other
  lanes in run 20260918-1 hold the first three.
- Any change to `epic_prefix`'s behaviour, the `epic-id` / `task-id` codes, the exit codes or the
  ID regexes.
- `cli.py:1327` (`epic add` allocating IDs) and `ids.py` — neither refuses an ID with a message.
- Fixing `epic_prefix`'s wider status as an option (T095's question 1); that was settled by T098.

## Verification

1. Rebuild the throwaway `EP01` repository above and run `validate` against it: the `epic-id`
   line must name `epic_prefix`.
2. Do the same for a task ID that does not match `prefix`: the `task-id` line must name `prefix`.
3. `taskrail checks T103 --stage implement` — the full `uv run pytest -q` suite, plus `lint`
   (not configured in this repository; will be reported as such).
4. `.taskrail/bin/taskrail validate` in this worktree, whose own backlog is `E##`/`T###`, to show
   the valid case is untouched.

Actual results go under **Results** below at the implement stage.

## Decisions taken at the scope gate

| # | Question | Answer |
|---|----------|--------|
| 1 | `project.py:43` here or a follow-up? | **Here** — the row's description asks for it and no other lane holds the file. |
| 2 | `importer.py:362` too? | **No, and no follow-up task** — a different command, not named by the row, and its message already names `id_digits` in the hint it appends. Recorded here so the third member of the family is not lost. |
| 3 | Name `id_digits` in the `task-id` message? | **No** — the row asks for the prefix refusal, and a bare number is self-explanatory where bare letters are not. |
| 4 | A `CHANGELOG.md` bullet? | **Yes**, one short bullet: it changes what every reader of a failed `validate` sees, which a consumer meets after an upgrade. An appended changelog bullet is a known conflict class, so a parallel lane's bullet is not a reason to decline. |

## Results

Both messages changed; nothing else in `src/` was touched.

```
$ git diff --stat 4026b0c -- src          # 4026b0c is the branch's base on origin/main
 src/taskrail/backlog.py | 2 +-
 src/taskrail/project.py | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)
```

**1. The `EP01` repository, the same one as above, after the change:**

```
$ uv run taskrail --root <tmp>/repro validate
TODO.md:7: error: epic ID `EP01` does not match epic_prefix `E` plus two or more digits [epic-id]
TODO.md:9: error: section `EP01` is not in the Epics table [epic-unlisted]
history: not checked (not a git repository)
0 task(s) in 1 backlog(s): 2 error(s), 0 warning(s)
exit=1
```

Then the fix the message now names, `epic_prefix = "EP"` added to `[[backlog]]`, and nothing else:

```
$ uv run taskrail --root <tmp>/repro validate
history: not checked (not a git repository)
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```

The message is now enough to get from the failure to the fix without reading `config.py`.

**2. The `task-id` sibling, the same repository with `T001` renamed `X001`:**

```
$ uv run taskrail --root <tmp>/repro validate
TODO.md:15: error: task ID `X001` does not match prefix `T` plus 3 or more digits [task-id]
history: not checked (not a git repository)
1 task(s) in 1 backlog(s): 1 error(s), 0 warning(s)
exit=1
```

**3. The two new tests fail without the change.** Stashing only the two source files and running
them:

```
$ git stash push -- src/taskrail/backlog.py src/taskrail/project.py
$ uv run pytest tests/test_validate.py -q -k "names_the"
E       AssertionError: assert 'epic_prefix' in 'epic ID `EP01` does not match `E` plus two or more digits'
FAILED tests/test_validate.py::test_task_id_refusal_names_the_prefix_key
FAILED tests/test_validate.py::test_epic_id_refusal_names_the_epic_prefix_key
2 failed, 17 deselected in 0.84s
$ git stash pop
```

They assert only that the key is named, in the style of `tests/test_import.py:462-463`, so a
later rewording that keeps the key will not break them.

**4. The stage's checks:**

```
$ taskrail checks T103 --stage implement
== test: uv run pytest -q
1198 passed in 150.48s (0:02:30)
== lint: not configured
passed test
not configured lint
T103 in <worktree>: passed
exit=0
```

`lint` is declared by the `chore` kind but this repository configures no `lint` command, so it is
reported as not configured — not a failure.

**5. This repository's own backlog, whose IDs are `E##`/`T###`, is unaffected:**

```
$ .taskrail/bin/taskrail validate
97 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```
