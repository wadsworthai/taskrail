# T113 — Fix the vacuous local-pin wrapper test in test_install.py

Kind: bug · Epic: E05 · Status: diagnosed

## Symptom

`tests/test_install.py::test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout` passes
whatever the `local:` pin points at. It writes `version = "local:vendor-taskrail"` into a fresh
repository's config, points `vendor-taskrail` at this checkout's source, runs the installed
wrapper with `--version`, and asserts only:

```python
assert result.returncode == 0, result.stderr
assert result.stdout.strip().startswith("taskrail ")
```

Nothing in that couples the output to the pinned source, and the subprocess inherits the test
process's environment. Expected: with the pin pointing at a directory that holds no taskrail
source, the test fails.

## Reproduction

A verbatim copy of the test with one line changed — `link.symlink_to(source)` replaced by
`link.mkdir()`, so the pin resolves to an **empty directory** — run in three environments on
`c5d43dc` (`origin/main`) from this task's worktree:

- **A** — verbatim: the wrapper inherits the environment `uv run pytest` gives the test process.
- **B** — same, with `VIRTUAL_ENV` removed from the subprocess environment.
- **C** — same, with `VIRTUAL_ENV` removed **and** `PATH` replaced by a directory holding only a
  `uv` symlink, plus `/usr/bin` and `/bin`, the way
  `tests/test_install_without_path.py::path_with_uv_but_no_taskrail` builds it.
- **D** — the real pin (the source symlink), under C's environment.

The probe file is not committed; it is reconstructible from the description above.

Machine facts, measured first:

```
$ echo "VIRTUAL_ENV=${VIRTUAL_ENV:-<unset>}"; command -v taskrail; taskrail --version; uv --version
VIRTUAL_ENV=<unset>
/home/abigail/.local/bin/taskrail
taskrail 0.3.0
uv 0.11.16 (x86_64-unknown-linux-gnu)
```

```
$ uv run python -c "import os;print(os.environ.get('VIRTUAL_ENV'));print(os.environ['PATH'].split(os.pathsep)[:2])"
/thezone/.../T113-fix-the-vacuous-local-pin-wrapper-test-i/.venv
['/thezone/.../T113-fix-the-vacuous-local-pin-wrapper-test-i/.venv/bin', '/home/abigail/.opencode/bin']
$ uv run python -c "import shutil;print(shutil.which('taskrail'))"
/thezone/.../T113-fix-the-vacuous-local-pin-wrapper-test-i/.venv/bin/taskrail
```

## Evidence

The broken pin, in A, B and C (`uv run pytest tests/test_zz_probe_t113.py -v`):

```
tests/test_zz_probe_t113.py::test_probe_a_verbatim_inherited_env
--- A verbatim (VIRTUAL_ENV inherited from `uv run pytest`): rc=0
    stdout='taskrail 0.4.0.dev0'
    stderr=''
PASSED  [ 33%]
tests/test_zz_probe_t113.py::test_probe_b_without_virtual_env
--- B without VIRTUAL_ENV (taskrail still on PATH): rc=0
    stdout='taskrail 0.4.0.dev0'
    stderr=''
PASSED     [ 66%]
tests/test_zz_probe_t113.py::test_probe_c_without_virtual_env_and_without_taskrail_on_path
--- C without VIRTUAL_ENV and without taskrail on PATH: rc=2
    stdout=''
    stderr='error: Failed to spawn: `taskrail`\n  Caused by: No such file or directory (os error 2)'
FAILED [100%]
...
E       AssertionError: error: Failed to spawn: `taskrail`
E           Caused by: No such file or directory (os error 2)
E         
E       assert 2 == 0
=========================== short test summary info ============================
FAILED tests/test_zz_probe_t113.py::test_probe_c_without_virtual_env_and_without_taskrail_on_path
========================= 1 failed, 2 passed in 1.29s ==========================
```

So the test is vacuous today (A passes with an empty pin), and C is the environment in which it
would have caught this.

The real pin under C's environment still passes, so closing those routes does not break the test
it is meant to be:

```
tests/test_zz_probe_t113.py::test_probe_d_real_pin_under_the_constrained_env
--- D good pin, constrained env: rc=0
    stdout='taskrail 0.4.0.dev0'
    stderr=''
PASSED [100%]
======================= 1 passed, 3 deselected in 1.09s ========================
```

## Root cause

The wrapper's `local:` branch (`src/taskrail/install.py`, `wrapper_script()`) is:

```sh
  local:*)
    exec uv run --quiet --project "$root/${pin#local:}" taskrail "$@"
    ;;
```

`uv run --project <dir> taskrail` resolves the command `taskrail` from the ambient environment
before the pinned project ever has to supply it, and the suite runs under `uv run pytest`, which
hands the test process an environment that already provides one:

- `VIRTUAL_ENV=<checkout>/.venv`, which `uv` honours; and
- `<checkout>/.venv/bin` **first on `PATH`**, where this checkout's `taskrail` entry point sits.

Either route alone answers `--version` with `taskrail 0.4.0.dev0` — this checkout's own version,
which is also the version the pin would have produced — so the assertion
`stdout.startswith("taskrail ")` holds with a pin that points at nothing. Only when both are
closed does the pin become the sole supplier, and a broken one then fails with
`error: Failed to spawn: taskrail` (exit 2).

The backlog row named `VIRTUAL_ENV` and a global `taskrail 0.3.0` on `PATH` as the two
mechanisms. Measured here, the second is not the global 0.3.0 but `.venv/bin` on `PATH`: probe B
dropped `VIRTUAL_ENV` and still printed `0.4.0.dev0`, not `0.3.0`. That makes the hole worse than
the row describes, because the fallback prints exactly the version a correct pin would.

## Ruled out

- **`TASKRAIL_BIN` leaking in.** The test already does `monkeypatch.delenv("TASKRAIL_BIN")`, and
  every probe kept that line. The escape is not `TASKRAIL_BIN`.
- **The wrapper reading the pin wrongly.** A logging `uv` shim placed first on `PATH` recorded the
  exact call the wrapper makes, with the pin resolved correctly:
  `uv run --quiet --project /tmp/pytest-of-abigail/pytest-184/test_wrapper_with_a_local_pin_0/vendor-taskrail taskrail --version`.
  The wrapper is not at fault; only the test is.
- **Other tests in `tests/test_install.py` having the same hole.** Probed rather than read: the
  same logging shims for `uv` **and** `taskrail` were put first on `PATH` and the whole file was
  run (`57 passed in 2.27s`). The log holds exactly two lines — the outer `uv run pytest` and the
  one call above. No other test in the file spawns `uv`, and none reaches a `taskrail` on `PATH`:
  `test_wrapper_runs_the_cli` and `test_pre_commit_hook_blocks_an_invalid_backlog` point
  `TASKRAIL_BIN` at a Python shim, and
  `test_wrapper_without_cli_or_uvx_explains_what_is_missing` passes a fully replaced environment
  (`PATH=/usr/bin:/bin`, `HOME` only) and asserts the failure. The fix is one test's.
- **A product bug in the wrapper.** Nothing about `local:` resolution is wrong; `uv`'s own
  precedence is documented behaviour. No change to `src/` is called for.

## Affected areas

`tests/test_install.py`, one test. No product code. `tests/test_install_without_path.py` (T106)
is the worked example that already closes both routes, and it says why in a comment:

```python
    monkeypatch.delenv("TASKRAIL_BIN", raising=False)  # it would bypass the wrapper entirely
    ...
    # The suite itself runs inside this project's virtual environment, which has a taskrail entry
    # point; uv would run that one whatever the pin says, and the route would prove nothing.
    env.pop("VIRTUAL_ENV", None)
```

## Proposed fix

In `test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout` only, run the wrapper with an
explicit environment that leaves the pin as the only possible supplier of `taskrail`:

- drop `VIRTUAL_ENV` from the subprocess environment;
- set `PATH` to `path_with_uv_but_no_taskrail(tmp_path)`, imported from
  `tests/test_install_without_path.py` — cross-module imports between test files are the suite's
  existing habit (`tests/test_row_on_base.py`, `tests/test_autopilot_skill.py` and six others
  already import from `test_install` or `test_autopilot*`);
- carry the reason in a comment, as T106's test does;
- skip the test when `uv` is not on `PATH`, since the helper and the wrapper's `local:` branch
  both need it (`test_install_without_path.py` has that guard at module level; importing the
  helper does not carry the mark).

Verification will re-run probes C and D against the **edited** test: with the pin pointed at an
empty directory it must fail with `Failed to spawn: taskrail`, and with the real pin it must pass.
