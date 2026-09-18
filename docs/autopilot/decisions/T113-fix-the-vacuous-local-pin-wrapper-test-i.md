# T113 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T113-fix-the-vacuous-local-pin-wrapper-test-i.md` and its commit
`868e641` (artifact and index row alone); the four probes A-D, which reproduce the vacuity with the
pin resolving to an empty directory; the shim log that proves the wrapper passes the pin correctly,
so no `src/` change is called for; and the whole-file probe showing no other test in
`tests/test_install.py` spawns `uv` or reaches a `taskrail` on `PATH`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Fix confined to that test, and one import line in `tests/test_install.py`? | **import `path_with_uv_but_no_taskrail` from `tests/test_install_without_path.py`** · duplicate the six lines inline · move the helper to `conftest.py` | **import it** | Cross-module test imports are this suite's existing habit — eight test modules already import from `test_install` or `test_autopilot*` — and the lane verified the import resolves. Extracting to `conftest.py` on the second use is what the rule of three argues against; duplicating still touches the import block for `shutil`, so it buys nothing. Add the `skipif` on the test, since the module-level guard does not travel with an imported helper. |
| 2 | Write the rule down, and where? | **one bullet in `CLAUDE.md`'s *Commands* section plus the reason in a comment in the test** · the comment only · a new `CONTRIBUTING.md` or `tests/README.md` | **CLAUDE.md bullet plus the comment** | The comment reaches only someone already inside the file, which is exactly how this hole was written. `CLAUDE.md` asks in its own words to be kept current as the repository grows, and one line there reaches the next author *before* they write the test. A new document for a single rule is the YAGNI case. `CLAUDE.md` is `read_first` and not `governing`, so this is the orchestrator's call at the gate and the human reviews it in the pull request. |
| 3 | A `CHANGELOG.md` bullet? | **none** · one under *Unreleased* | **none** | No product code and no behaviour changes, and the precedent is consistent: T106, T108 and T110 all landed without one. |

Given with the answers: the row's account of the second mechanism is refined by this lane's
measurement and the artifact should say so. The row, written from T106's probe, says that with
`VIRTUAL_ENV` unset `uv` falls back to a globally installed `taskrail 0.3.0` on `PATH`. In the
suite's own environment probe B shows it falls back to `<checkout>/.venv/bin/taskrail` and prints
`0.4.0.dev0` — the same version a correct pin would print. Both are "a `taskrail` on `PATH`"; what
matters is the consequence the row does not state: **no version assertion could have caught this,
and dropping `VIRTUAL_ENV` alone is not a sufficient fix.** `PATH` must be constrained too.

## fix gate

Reviewed: commit `48e0a1d` — the whole diff of `tests/test_install.py` and `CLAUDE.md`, with no
product code touched and no `CHANGELOG.md` bullet; the sabotage run, which fails with
`Failed to spawn: taskrail` and exit 2, the failure the task says the test should see; the reverted
state with `grep SABOTAGE` empty; and `taskrail checks T113 --stage fix` (1,247 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The import block grew by two lines, not the one flagged | **accept** | **accept** | `shutil` is needed for the `skipif`, both lines are at the top of the file and both are in this lane's half. T116 has been told to expect a two-line textual conflict there and nothing in the generated-workflow tests. |
| 2 | `path_with_uv_but_no_taskrail(tmp_path)` where `empty_repo` is the same directory | **leave it** · pass `empty_repo` and drop the fixture | **leave it** | The two are the same path, so nothing behavioural turns on it; taking `tmp_path` reads the way the helper's signature intends. Not worth a change. |
| 3 | The assertion left as `stdout.startswith("taskrail ")` | **accept** | **accept** | With no `taskrail` reachable by any other route, a version line can only have come from the pin. A version-equality assertion would have been worthless anyway, since the ambient fallback printed exactly the version a correct pin prints — which is the finding this task added to the row. |

## close

Reviewed: the whole diff `origin/main..HEAD` — the edited test and its two import lines, the
`CLAUDE.md` bullet, the artifact, two index rows and T113's `✅`, with no `src/` change and no
`CHANGELOG.md` bullet; the `impact` sweep, which rests on the diagnose probe's shim log rather than
on a reading; `taskrail checks T113 --stage fix` (1,247 passed) and `taskrail validate` (106 tasks,
0 errors); working tree clean and `grep SABOTAGE` empty.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `impact` stage opened nothing — accept? | **accept** | **accept** | Each of the three candidates was closed by evidence already in hand: the shim log showing no other test in the file spawns `uv`, the same log showing the wrapper passes the pin correctly, and the rule now written in `CLAUDE.md`. |
| 2 | The row's incomplete description, left unedited | **accept; the artifact carries the correction** | **accept** | The row belongs to a closed task and the artifact states the correction against it, which is where a reader meets both. Editing a closed row would also add conflict surface in `TODO.md` for nothing that outlives the task. |
| 3 | Pull request type and scope | **`fix` / `tests`** · the generated scope-less `fix:` | **`fix` / `tests`** | The change is a test that proved nothing; `tests` is the affected area, and CLAUDE.md asks for the area as the scope. |
