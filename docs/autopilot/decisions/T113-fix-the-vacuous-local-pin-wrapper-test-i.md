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
