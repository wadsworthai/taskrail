# T026 — Refuse --column for core columns in new

Kind: bug · Epic: E02 · Status: fixed

## Symptom

`taskrail new --column NAME=VALUE` is meant for custom columns. Given the name of a core task
column (`✓`, `ID`, `Kind`, `Depends On`, `Title`, `Pts`, `Description`) in a repository where
that column is not aliased, `new` exits 0 and either silently discards the value (`✓`, `ID`) or
silently writes it, overriding the dedicated flag (`Kind` over `--kind`, `Title` over
`--title`, `Pts` over `--pts`, …). The same name in another letter case (`id=T9`) fails with a
misleading message that the table has no such column. Only a core column that is **aliased**
in `[columns].aliases` is refused with a hint naming the flag to use (added by T021).

Expected: every core column is refused, whatever its case and whether or not it is aliased,
exiting 2 with a message naming the flag that fills it (or saying taskrail sets it), and
writing nothing.

## Reproduction

A throwaway git repository with this `.taskrail/config.toml`:

```toml
version = "v0.1.0"

[[backlog]]
name = "main"
prefix = "T"
file = "TODO.md"

[columns]
custom = []
# plain:   no aliases line
# partial: aliases = { Pts = "Size" }
# full:    aliases = { "✓" = "Status", ID = "Key", Kind = "Type", Pts = "Size", "Depends On" = "Blocked By", Title = "Summary", Description = "Notes" }
```

and a `TODO.md` with epic `E01` holding one task table (`| ✓ | ID | Kind | Pts | Depends On |
Title | Description |`, with the `Pts` header renamed `Size` for *partial* and every header
renamed to its alias for *full*) and one row `T001`. A fresh copy per command, then:

```bash
taskrail --root <repo> new --epic E01 --kind bug --title "Negative totals" --column "<pair>"
```

## Evidence

Run at `ee38f5b` (origin/main). `row` is the row `new` appended, or `<none>`:

```
plain   --column "✓=✅"               exit=0 out=T002
        row: | ⬜ | T002 | bug     | —   | —          | Negative totals |             |
plain   --column "ID=T9"              exit=0 out=T002
        row: | ⬜ | T002 | bug     | —   | —          | Negative totals |             |
plain   --column "Kind=feature"       exit=0 out=T002
        row: | ⬜ | T002 | feature | —   | —          | Negative totals |             |
plain   --column "Depends On=T001"    exit=0 out=T002
        row: | ⬜ | T002 | bug     | —   | T001       | Negative totals |             |
plain   --column "Title=Other"        exit=0 out=T002
        row: | ⬜ | T002 | bug     | —   | —          | Other          |             |
plain   --column "Pts=3"              exit=0 out=T002
        row: | ⬜ | T002 | bug     | 3   | —          | Negative totals |             |
plain   --column "Description=Other"  exit=0 out=T002
        row: | ⬜ | T002 | bug     | —   | —          | Negative totals | Other       |
plain   --column "id=T9"              exit=2 out=taskrail: the task table has no column(s): id
        row: <none>
plain   --column "kind=feature"       exit=2 out=taskrail: the task table has no column(s): kind
        row: <none>
plain   --column "pts=3"              exit=2 out=taskrail: the task table has no column(s): pts
        row: <none>
partial --column "✓=✅"               exit=0 out=T002
        row: | ⬜ | T002 | bug     | —    | —          | Negative totals |             |
partial --column "ID=T9"              exit=0 out=T002
        row: | ⬜ | T002 | bug     | —    | —          | Negative totals |             |
partial --column "Kind=feature"       exit=0 out=T002
        row: | ⬜ | T002 | feature | —    | —          | Negative totals |             |
partial --column "Depends On=T001"    exit=0 out=T002
        row: | ⬜ | T002 | bug     | —    | T001       | Negative totals |             |
partial --column "Title=Other"        exit=0 out=T002
        row: | ⬜ | T002 | bug     | —    | —          | Other          |             |
partial --column "Pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
        row: <none>
partial --column "Description=Other"  exit=0 out=T002
        row: | ⬜ | T002 | bug     | —    | —          | Negative totals | Other       |
partial --column "id=T9"              exit=2 out=taskrail: the task table has no column(s): id
        row: <none>
partial --column "kind=feature"       exit=2 out=taskrail: the task table has no column(s): kind
        row: <none>
partial --column "pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
        row: <none>
full    --column "✓=✅"               exit=2 out=taskrail: --column cannot set core column ✓ (named `Status` here); taskrail sets it
full    --column "ID=T9"              exit=2 out=taskrail: --column cannot set core column ID (named `Key` here); taskrail sets it
full    --column "Kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind (named `Type` here); set it with --kind
full    --column "Depends On=T001"    exit=2 out=taskrail: --column cannot set core column Depends On (named `Blocked By` here); set it with --depends-on
full    --column "Title=Other"        exit=2 out=taskrail: --column cannot set core column Title (named `Summary` here); set it with --title
full    --column "Pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
full    --column "Description=Other"  exit=2 out=taskrail: --column cannot set core column Description (named `Notes` here); set it with --description
full    --column "id=T9"              exit=2 out=taskrail: --column cannot set core column ID (named `Key` here); taskrail sets it
full    --column "kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind (named `Type` here); set it with --kind
full    --column "pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
(every full row: <none>)
```

The column value wins over the flag, and the kind check can be sidestepped in `--workspace`:

```
$ taskrail new --epic E01 --kind bug --title T --pts 5 --column Pts=3
T002
exit=0
| ⬜ | T002 | bug     | 3   | —          | T              |             |

$ taskrail new --epic E01 --kind bug --title T --column Kind=feature --workspace
T002
workspace /tmp/.../.worktrees/T002-t on branch T002-t from main
exit=0
| ⬜ | T002 | feature | —   | —          | T              |             |
```

The post-write validation still catches a *value* that is invalid on its own:

```
$ taskrail new --epic E01 --kind bug --title T --column Kind=nonsense
TODO.md:14: error: kind `nonsense` is not defined (known: bug, chore, feature, spike) [task-kind-unknown]
taskrail: the change would leave the backlog invalid; nothing was written
exit=1

$ taskrail new --epic E01 --kind bug --title T --column Kind=feature   # kinds.allowed = [bug, chore]
TODO.md:14: error: kind `feature` is not allowed (kinds.allowed: bug, chore) [task-kind-disallowed]
taskrail: the change would leave the backlog invalid; nothing was written
exit=1
```

## Root cause

`cmd_new` in `src/taskrail/cli.py` builds a `values` dict keyed by core column
name and hands it to `writer.add_task`. Its `--column` loop refuses a name only when it matches
an entry of `project.config.column_aliases` (the core name or the alias of an **aliased**
column):

```python
aliased = next(
    (core for core, alias in project.config.column_aliases.items() if name.strip().lower() in (core.lower(), alias.lower())),
    None,
)
if aliased is not None:
    ...refuse, exit 2...
values[name.strip()] = value.strip()
```

Every other name falls through to `values[name.strip()] = value.strip()`, keyed by the user's
spelling. An unaliased core column is therefore never refused, and what happens next depends on
where its key collides in `values`:

- `Kind`, `Title` — set from the flags before the loop, so the column **overwrites** them.
- `Pts`, `Depends On`, `Description` — set before the loop only when their flag is given, so the
  column either fills the cell or **overwrites** the flag.
- `ID`, `✓` — set after the loop (`values["ID"] = task_id`, `values["✓"] = ...`), so the column
  value is **silently discarded**.
- Any other letter case (`id`, `kind`) matches no key; `writer.add_task` compares names against
  the header index, whose keys are canonical core names, and raises `the task table has no
  column(s): id` — refused, but with a message that is false for that table.

With `--workspace`, the kind used to check the kind and render the branch is `args.kind`, while
the row gets the `--column Kind` value, so the workspace can be opened for a different kind than
the row records.

## Ruled out

- **`writer.add_task`'s unknown-column check.** It only rejects names absent from the table's
  header index (`name not in columns`). Core names are always in that index, so it cannot catch
  them; it is where the value lands, not the cause.
- **Post-write validation (`_write` → `writer.apply`).** It rejects a row that is invalid on its
  own (an undefined or disallowed kind, above), but an overridden title, points or kind that is
  itself valid, and a discarded ID or status, leave a valid backlog. It cannot see that a flag
  was overridden.
- **argparse.** `--column` is `action="append"` of free strings; parsing `NAME=VALUE` and
  deciding what a name may be is `cmd_new`'s job by design.
- **Config: a custom column named like a core column.** `[columns].custom = ["Kind"]` validates
  cleanly (`1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`), but the header index maps a
  `Kind` header to the core column regardless, so no repository can have a custom column that a
  core-name refusal would wrongly block.
- **The T021 alias refusal itself.** It behaves as specified for aliased columns (all *full*
  cases, *partial* `Pts`/`pts`); the defect is that its guard is limited to aliased columns.

## Affected areas

- `src/taskrail/cli.py` — `cmd_new`, the `--column` loop (the only code change).
- `DESIGN.md` §3.2 documents the refusal for aliased columns only (“`new` fills
  an aliased column through its usual flag (`--pts`), refusing `--column` for it”).
- No other command accepts `--column`.

## Proposed fix

In `cmd_new`'s `--column` loop, resolve the name case-insensitively against every core task
column (`CORE_TASK_COLUMNS` from `config.py`) and every alias, instead of the aliases alone, and
refuse any match before an ID is reserved, with exit 2 and a message naming the flag:

- unaliased: `taskrail: --column cannot set core column Kind; set it with --kind`
- aliased (unchanged): `taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts`
- `✓` and `ID`: `...; taskrail sets it`

Regression test: parametrize `new --column <core>=<value>` over all seven core columns (plus a
lower-case spelling) in a repository without aliases, and over an unaliased core column in a
repository that aliases another one; assert exit 2, the flag hint in stderr, `TODO.md`
unchanged, and the next reserved ID not consumed. Add one `CHANGELOG.md` bullet and widen the
DESIGN.md sentence to all core columns.

## Regression test (observed failing first)

Decisions from the diagnose gate: exit code 2; `fix`, not breaking, with the behaviour change
stated in the changelog; DESIGN.md §3.2 updated in the fix commit; the `--workspace` case
included in the tests.

Tests added before touching `cli.py`:

- `tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag` — no
  aliases; the seven core columns plus `id=T9` and ` kind =feature`, each with `--pts 5`; asserts
  exit 2, no stdout, the exact message, `TODO.md` unchanged, and `T004` still the next ID.
- `tests/test_column_aliases.py::test_new_column_for_an_unaliased_core_column_is_refused_when_another_is_aliased`
  — `Pts` aliased to `Size`; `Kind=feature` and `ID=T9` are refused with the plain message.
- `tests/test_workspace.py::test_column_for_a_core_column_is_refused_before_the_workspace_exists`
  — `new --workspace --column Kind=feature` exits 2 with no `.worktrees`, no task branch, a clean
  working tree and `T004` still the next ID.

Run against the unfixed code (`uv run pytest -q --color=no --tb=line -k
"refuses_column_for_a_core_column or refused_before_the_workspace_exists or unaliased_core_column_is_refused"`):

```
FFFFFFFFFFFF                                                             [100%]
E   assert 0 == 2
tests/test_column_aliases.py:183: assert 0 == 2
E   assert 0 == 2
tests/test_column_aliases.py:183: assert 0 == 2
E   AssertionError: 
    assert 0 == 2
tests/test_workspace.py:24: AssertionError:
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert (0, 'T004\n') == (2, '')
      
      At index 0 diff: 0 != 2
      Use -v to get more diff
tests/test_write.py:123: AssertionError: assert (0, 'T004\n') == (2, '')
E   AssertionError: assert 'taskrail: th...column(s): id' == 'taskrail: --...krail sets it'
      
      - taskrail: --column cannot set core column ID; taskrail sets it
      + taskrail: the task table has no column(s): id
tests/test_write.py:124: AssertionError: assert 'taskrail: th...column(s): id' == 'taskrail: --...krail sets it'
E   AssertionError: assert 'taskrail: th...lumn(s): kind' == 'taskrail: --...t with --kind'
      
      - taskrail: --column cannot set core column Kind; set it with --kind
      + taskrail: the task table has no column(s): kind
tests/test_write.py:124: AssertionError: assert 'taskrail: th...lumn(s): kind' == 'taskrail: --...t with --kind'
FAILED tests/test_column_aliases.py::test_new_column_for_an_unaliased_core_column_is_refused_when_another_is_aliased[Kind=feature-Kind---kind]
FAILED tests/test_column_aliases.py::test_new_column_for_an_unaliased_core_column_is_refused_when_another_is_aliased[ID=T9-ID-taskrail sets it]
FAILED tests/test_workspace.py::test_column_for_a_core_column_is_refused_before_the_workspace_exists
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[\u2713=\u2705-\u2713-taskrail sets it]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[ID=T9-ID-taskrail sets it]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[Kind=feature-Kind-set it with --kind]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[Depends On=T001-Depends On-set it with --depends-on]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[Title=Other-Title-set it with --title]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[Pts=3-Pts-set it with --pts]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[Description=Other-Description-set it with --description]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[id=T9-ID-taskrail sets it]
FAILED tests/test_write.py::test_new_refuses_column_for_a_core_column_and_names_the_flag[ kind =feature-Kind-set it with --kind]
12 failed, 237 deselected in 0.83s
```

Each failure matches the root cause: exact-case core names were accepted (exit 0, a row
written as `T004`), other letter cases reached the writer's misleading unknown-column error,
and the workspace was created (exit 0) for `--kind bug` while the row recorded `feature`.

A guard, `tests/test_write.py::test_new_still_fills_a_custom_column`, checks that a declared
custom column is still filled; it passes on both the unfixed and the fixed code (`1 passed`).

## Fix

`cmd_new` in `src/taskrail/cli.py` now builds one case-insensitive lookup of
every core column name (`CORE_TASK_COLUMNS`) and every alias, mapped to its core column, and
refuses any `--column` name found there with exit 2, before an ID is reserved or a workspace
opened. The message names the alias only when the column is aliased:

```
taskrail: --column cannot set core column Kind; set it with --kind
taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
taskrail: --column cannot set core column ID; taskrail sets it
```

Also: one `CHANGELOG.md` bullet under *Unreleased* stating the behaviour change, and DESIGN.md
§3.2 widened from aliased columns to every core column.

## Verification

- Regression tests after the fix, with T021's aliased-column tests:
  `uv run pytest -q --color=no -k "refuses_column_for_a_core_column or
  refused_before_the_workspace_exists or unaliased_core_column_is_refused or
  aliased_core_column_names_the_flag"` → `17 passed, 232 deselected in 1.27s`.
- Check `test`: `uv run pytest -q` → `250 passed in 15.51s`.
- Check `lint`: not configured — `.taskrail/config.toml` `[checks]` defines only `test`.
- `taskrail validate` → `26 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- The reproduction from *Evidence*, re-run after the fix — every case exits 2 and writes no row
  (`row: <none>` for all 30):

  ```
  plain   --column "✓=✅"            exit=2 out=taskrail: --column cannot set core column ✓; taskrail sets it
  plain   --column "ID=T9"              exit=2 out=taskrail: --column cannot set core column ID; taskrail sets it
  plain   --column "Kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind; set it with --kind
  plain   --column "Depends On=T001"    exit=2 out=taskrail: --column cannot set core column Depends On; set it with --depends-on
  plain   --column "Title=Other"        exit=2 out=taskrail: --column cannot set core column Title; set it with --title
  plain   --column "Pts=3"              exit=2 out=taskrail: --column cannot set core column Pts; set it with --pts
  plain   --column "Description=Other"  exit=2 out=taskrail: --column cannot set core column Description; set it with --description
  plain   --column "id=T9"              exit=2 out=taskrail: --column cannot set core column ID; taskrail sets it
  plain   --column "kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind; set it with --kind
  plain   --column "pts=3"              exit=2 out=taskrail: --column cannot set core column Pts; set it with --pts
  partial --column "✓=✅"            exit=2 out=taskrail: --column cannot set core column ✓; taskrail sets it
  partial --column "ID=T9"              exit=2 out=taskrail: --column cannot set core column ID; taskrail sets it
  partial --column "Kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind; set it with --kind
  partial --column "Depends On=T001"    exit=2 out=taskrail: --column cannot set core column Depends On; set it with --depends-on
  partial --column "Title=Other"        exit=2 out=taskrail: --column cannot set core column Title; set it with --title
  partial --column "Pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
  partial --column "Description=Other"  exit=2 out=taskrail: --column cannot set core column Description; set it with --description
  partial --column "id=T9"              exit=2 out=taskrail: --column cannot set core column ID; taskrail sets it
  partial --column "kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind; set it with --kind
  partial --column "pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
  full    --column "✓=✅"            exit=2 out=taskrail: --column cannot set core column ✓ (named `Status` here); taskrail sets it
  full    --column "ID=T9"              exit=2 out=taskrail: --column cannot set core column ID (named `Key` here); taskrail sets it
  full    --column "Kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind (named `Type` here); set it with --kind
  full    --column "Depends On=T001"    exit=2 out=taskrail: --column cannot set core column Depends On (named `Blocked By` here); set it with --depends-on
  full    --column "Title=Other"        exit=2 out=taskrail: --column cannot set core column Title (named `Summary` here); set it with --title
  full    --column "Pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts
  full    --column "Description=Other"  exit=2 out=taskrail: --column cannot set core column Description (named `Notes` here); set it with --description
  full    --column "id=T9"              exit=2 out=taskrail: --column cannot set core column ID (named `Key` here); taskrail sets it
  full    --column "kind=feature"       exit=2 out=taskrail: --column cannot set core column Kind (named `Type` here); set it with --kind
  full    --column "pts=3"              exit=2 out=taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts

  $ taskrail new --epic E01 --kind bug --title T --column Kind=feature --workspace
  taskrail: --column cannot set core column Kind; set it with --kind
  exit=2
  $ git branch
  * main
  $ ls -a <repo>
  .  ..  .git  .taskrail  TODO.md
  ```
