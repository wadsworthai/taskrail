# T106 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T106-test-init-and-the-wrapper-with-taskrail.md` and its commit
`83a5012` (the only commit on the branch, artifact and index row alone, working tree clean); the
lane's probe output, which shows `init` and the wrapper both exiting 0 on a PATH where
`taskrail` is absent and only `uv` is reachable; and the wrapper coverage the lane read out of
`tests/test_install.py`, which confirms no existing test exercises the documented route.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Cover the `local:` pin only, since the `uvx` fallback needs the network? | as recommended · point `TASKRAIL_SOURCE` at a local git repo · stub `uvx` on the built PATH | **as recommended** | A test that clones over the network is unacceptable in the CI T108 adds, and a stub would assert the wrapper's shell text rather than that taskrail runs. Say so in the test's docstring, and name the fallback's transport as what the test does not cover. |
| 2 | Run `init` as a subprocess through `uv run`, or in-process through `main()`? | as recommended (subprocess) · in-process init plus a subprocess wrapper | **as recommended** | "With `taskrail` absent from PATH" has no meaning in-process. `tests/test_json_through_uv_run.py` is the precedent, and the 0.2 s saved would leave the bootstrap half of the route untested. |
| 3 | What if another `taskrail` sits in `/usr/bin` or `/bin`? | as recommended (`pytest.skip` with a message) · fail · seal the PATH with symlinks for every tool | **as recommended** | It is the house behaviour of `test_wrapper_without_cli_or_uvx_explains_what_is_missing`; sealing the PATH hard-codes a tool list the wrapper's shell text can change out from under. |

Given with the answers: keep the new test in its own file so it cannot collide with T107's tests;
leave the existing wrapper tests as they are; and if the finished test proves a real defect, stop
and report before touching `src/`.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits what, with T106 and T107 live | split by area · first come first served | **T106: `tests/` (its own new file) and, only on a proven defect, the minimum in `src/taskrail/install.py` or the wrapper template. T107: the archive feature's own module, its `cli.py`/`config.py`/`ids.py`/`mergedriver.py`/`writer.py` wiring, its own tests, `DESIGN.md` §§3.1/4/7 and a new §7.6, `README.md`.** | The two tasks meet only in `tests/` and `install.py`; separate files and an ask-at-the-gate rule for `install.py` keep them apart. T107 confirmed at its plan gate that it needs no `install.py` change. |
| 2 | The files both lanes append to | resolve at hand-off as known classes · forbid | **resolve at hand-off**: `TODO.md` rows united by ID, `CHANGELOG.md` bullets, `docs/*/README.md` index rows | They are the known conflict classes of the autopilot skill; every lane appends its own entry and none rewrites another's. |
