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

## implement gate

Reviewed: commit `fe2cbda` and the diff `7f4aa1e..HEAD` (the new test file and the artifact, nothing
else; `tests/test_install.py` and `src/` untouched, working tree clean); the whole of
`tests/test_install_without_path.py` read by the orchestrator, not its summary; the lane's
broken-pin run, which fails on the bootstrap's exit code; `uv run pytest
tests/test_install_without_path.py -q` re-run by the orchestrator in the lane's worktree
(`1 passed in 1.15s`); and `taskrail checks T106` re-run by the orchestrator.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is dropping `VIRTUAL_ENV` in the subprocess environment inside the approved change set, being one line the scope gate did not name? | inside the contract · a deviation needing a new approval | **inside the contract** | The contract is a test that runs `init` and the wrapper with `taskrail` absent from PATH. The suite runs under `uv run`, which exports `VIRTUAL_ENV` pointing at a `.venv` holding a `taskrail` entry point, and `uv` honours it whatever the pin resolves to; without the line the file passes with the pin broken and tests nothing. A line that makes the approved test test what it says is the contract, not an addition to it. |
| 2 | Open a task about the same leak in the tests that already exist? | measure first, then open it on this branch · open it on the stated risk · leave it | **measure first, then open it** | `tests/test_install.py:291` drops `TASKRAIL_BIN` but not `VIRTUAL_ENV`, so `test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout` may be vacuous for exactly this reason — and it may not. A task row that rests on a theory is the kind of premise the orchestrator has to escalate later; one probe settles it before the row is written. CLAUDE.md's design principles say to open a task rather than widen this one, so the fix itself stays out of T106 either way. |

Given with the answers: run the probe on the existing test without committing the mutation; write
the follow-up task's description from what the probe shows, naming the measurement; if the probe
shows the existing test is sound, open no task and record that instead.
