# T027 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: `docs/bugs/T027-stop-init-and-upgrade-on-an-unreadable-i.md` (commit `27c132f`) — the
real merge conflict reproduced, seven kinds of broken manifest, and the root cause in
`install.py` `read_manifest` treating unreadable and missing alike.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Confirm the diagnosis | confirm · rethink | **confirm** | Reproduced end to end, including that no files are deleted and only the recorded state is lost; every observed outcome follows from the one function. |
| 2 | Which broken manifests refuse with exit 2 | all read failures · JSON syntax only | **all**: syntax errors (conflict markers, empty file), non-object values, non-UTF-8 bytes and read errors | Same function, same missing check; leaving tracebacks would fix half the defect. |
| 3 | `upgrade --force` on a broken manifest | refuse · reinstall from nothing | **refuse** | `--force` overwrites managed files; with the digests lost it would overwrite copies it can no longer tell apart from local edits. |
| 4 | A readable `{}` | keep current behaviour · new message | **keep** | taskrail never writes it and there is no state to lose. |

## fix gate

Reviewed independently of the lane's report: the `install.py` diff of `b8a27ba` (only
`read_manifest` and its message), the red run of the 21 regression cases on the unfixed code, and
a re-run of the suite in the lane's worktree (284 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the fix | approve · request changes | **approve** | Every read failure now raises the existing `ConfigError` path (exit 2) before anything is written; a missing manifest and `{}` keep their behaviour. |
| 2 | Keep "or delete it to reinstall from scratch" in the message | keep · drop | **keep** | Checked in a throwaway repository: after deleting the manifest, a plain `init` re-records all five unedited skill copies (their content matches), and only locally edited copies would stay unmanaged — the safe outcome. The advice is accurate. |
| 3 | Follow-ups for the claims and ID-reservation readers | none · open tasks | **none** | That state is local and never committed, so it cannot arrive broken through a merge. |

## rebase after T028

T028 was squash-merged into `main` as `2b617b6`. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | keep both rows · stop | **keep both** | Both sides add an index row; a known additive class. |
| 2 | Conflict in `TODO.md` | union by ID · stop | **union by ID, `✅` wins** | T028 is `✅` on `main`, T027 is `✅` on this branch; no `Reopens:` commit for either. |

After the rebase: no conflict markers, `pytest -q` 284 passed, `taskrail validate` 0 errors, T027 `done`.
