# T039 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the scope in `docs/chores/T039-fetch-full-history-in-the-generated-gith.md` (commit
`1d28040`) and the reproduction: the same backlog with an untraced reopen gives no warning in a
`--depth 1` clone and `reopen-untraced` in a full clone. The generated workflow is a managed file,
so `upgrade` already rewrites an unedited copy.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Checkout depth | `fetch-depth: 0` · a fixed depth | **`0`** | `--history-limit` counts backlog-changing commits, `fetch-depth` counts all commits; no fixed depth matches, and a cut parent hides a reopen silently. |
| 2 | Flags for `validate` in the workflow | none · `--history-limit` · `--no-history` | **none** | The default applies in CI as locally, and warnings do not change the exit code. |
| 3 | Test that `upgrade` rewrites an unedited old workflow | include · template test only | **include** | It proves existing installs receive the fix without code changes. |

Change set approved, including the README wording fix for pushes to the mainlines.

## implement gate

Reviewed: commit `badbe16` (`fetch-depth: 0` under `actions/checkout@v7` in `workflow()`, and two
tests in `tests/test_install.py`). Both tests failed on the old template; the lane's full suite gave
743 passed. In throwaway installs made with `main`'s code, `upgrade` with this branch updated an
unedited workflow, skipped an edited one, and replaced it with `--force`; a depth-1 fetch hid an
untraced reopen that a full fetch reported.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Exactly the approved change set. |
| 2 | Pull request type | `fix` · `chore` | **`fix`** | The generated workflow silently defeated an existing check; users should see it in the release notes. |

## docs and close

The docs stage updated the README bullet (pull requests and pushes to the mainlines, full history),
DESIGN.md §9 and the CHANGELOG, with no follow-ups. No rebase was needed (`origin/main` is
`9c87bc2`). Checked before publishing: `TODO.md` differs from `main` only in T039 `✅`, the full
suite passes, `taskrail validate` 0 errors, `upgrade` reports nothing to create or update.

## rebase after T004 and T040

T004 (`fff3fe6`) and T040 (`3f3b8d7`) were squash-merged into `main`. The orchestrator rebased the
branch onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in the decisions index, CHANGELOG and `TODO.md` | keep both · stop | **keep both** | Rows and bullets added on both sides. |
| 2 | Conflict in DESIGN.md §9 *Extras* | merge both sentences · stop | **merge both** | T004 added `--merge-driver` to the bullet and this branch the full-history clause; the bullet now carries both. |

After the rebase: the README and the workflow template keep this branch's change, `pytest -q` 823
passed, `taskrail validate` 0 errors, `upgrade` reports nothing to create or update.
