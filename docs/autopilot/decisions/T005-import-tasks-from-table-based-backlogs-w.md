# T005 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: the plan in `docs/features/T005-import-tasks-from-table-based-backlogs-w.md` (commit
`2bdcc2b`), its fifteen acceptance criteria, and the lane's evidence that `validate` today reports
only `epics-missing` for a table-based backlog and does not count its tasks. The orchestrator's
brief placed T005 in E05; the backlog has it in E02, and the lane rightly left the backlog as it is.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Command surface | dry run by default, `--write` replaces the configured file · always in place · `--output PATH` | **as recommended** | An agent iterates on the dry-run report before touching anything; `--write` refuses to overwrite a backlog that already has epics or tasks. |
| 2 | Mapping | flags · mapping file · config sections | **flags** | Iterable from the report; a status alias in config would contradict §3.3, where only ⬜✅❌ are stored. |
| 3 | `--column` direction | `CORE=HEADER` · `HEADER=CORE` | **`CORE=HEADER`** | Same direction as `[columns].aliases`. |
| 4 | Header names | rename mapped headers to the configured name · keep source headers | **rename** | The result validates under the repository's own configuration; keeping a header means configuring its alias first. |
| 5 | Epic grouping | nearest heading, default level, `--epic-level`, `--epic-name`, kept `E07` IDs · drop the extras | **all of it** | Real backlogs nest headings differently; the extras are small and tested. |
| 6 | Default status | none, a status column is required · `--default-status` | **none** | Guessing status silently marks work done or pending by accident. |
| 7 | Scope | 5 points, no follow-ups now · open follow-ups | **as recommended** | `--single-epic` and ID-less tables wait for a consumer that needs them. |

Plan approved. The lane uses invented data only and removes its scratch repositories when done.

## implement gate

Reviewed: commit `0218316` (`importer.py`, one registration hunk in `cli.py`, DESIGN.md §1, §7,
§7.3, §11, README, CHANGELOG, `tests/test_import.py`). Re-ran `uv run
pytest -q` in the lane's worktree: 501 passed. The 32 new tests, on invented data, failed before the
code; the first run with code exposed a real bug (a seeded `# TODO` heading counted as prose), fixed
before commit. The importer reuses the existing cell and ID helpers without changing them.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Changes from the plan: Depends On after Kind; `--write` replaces only a target with nothing but headings and empty tables; only the target file's errors block; `already_imported` and exit 4 for a busy lock | accept · Depends On after ID, whole-project validation | **accept** | Each is safer or more precise than the plan's wording: a target with its own prose is never overwritten, and a broken unrelated backlog does not block adopting another. |
| 2 | Approve the implementation | approve · changes | **approve** | Criteria 1–15 map to tests seen failing. |

## verify, close and rebase after T034, T037, T036 and T030

The verify stage found one gap — a refused import also printed validation errors for the
half-converted text, with its line numbers — and the lane fixed it within scope under a regression
test observed failing first. The lane rebased twice at close; only the docs indexes and CHANGELOG
conflicted, resolved by keeping both with a single T005 bullet last. Checked by the orchestrator
before publishing: `TODO.md` differs from `main` only in T005 `✅`, `pytest -q` 568 passed,
`taskrail validate` 0 errors, `upgrade` reports nothing to create or update, no upstream.

## rebase after T032 and T031

T032 (`151e290`) and T031 (`a41ca8a`) were squash-merged into `main`. The orchestrator rebased the
branch onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/features/README.md`, `docs/autopilot/decisions/README.md`, CHANGELOG | keep both · stop | **keep both** | Rows and bullets added on both sides; one bullet each for T031, T032 and T005. |

No code conflicted. After the rebase: no conflict markers, `pytest -q` passes, `taskrail validate` 0
errors, `upgrade` reports nothing to create or update.
