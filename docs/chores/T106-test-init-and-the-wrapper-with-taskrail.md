# T106 — Test init and the wrapper with taskrail absent from PATH

Kind: chore · Epic: E05 · Status: implemented

## Goal

T100 made the no-global-install route the documented default: bootstrap with `uvx`, then call
taskrail through the committed wrapper `.taskrail/bin/taskrail`, whose only prerequisite is `uv`.
Nothing in `tests/` runs that route with `taskrail` absent from `PATH` — proving it during T100
needed a purpose-built `PATH` by hand, which is exactly what this chore turns into a test, so the
documented default cannot break unnoticed.

## Grounding: what is measured on this branch

Base `origin/main`, `5dfcd8e`. Commands run in this worktree.

- `grep -n "wrapper\|TASKRAIL_BIN\|uvx\|PATH" tests/test_install.py` — the wrapper's whole test
  coverage today:

  | Test | What it runs the wrapper with | What it proves |
  |---|---|---|
  | `test_wrapper_runs_the_cli` (`:187`) | `env = {**os.environ, "TASKRAIL_BIN": <shim>}` | the `TASKRAIL_BIN` override, which short-circuits the wrapper's first branch and never consults `PATH` |
  | `test_wrapper_without_cli_or_uvx_explains_what_is_missing` (`:195`) | `env = {"PATH": "/usr/bin:/bin", …}` | the *failure* message when neither a matching CLI nor `uvx` is there — and `pytest.skip`s when either is installed system-wide. `uv` is absent from that `PATH` too, so no successful route is exercised |
  | `test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout` (`:290`) | the inherited environment | that a `local:` pin runs the checkout's source — but with the developer's whole `PATH`, so it says nothing about a `taskrail` being absent from it |

  No test runs `init` in a process of its own at all: every `init` in `tests/test_install.py` goes
  through `main([...])` in-process, where `PATH` cannot matter.
- This machine is the case the test must survive: `command -v taskrail` → `/home/abigail/.local/bin/taskrail`,
  `command -v uv` → `/home/abigail/.local/bin/uv`. The installed CLI and `uv` share one directory,
  so dropping that directory from `PATH` drops `uv` with it. That is why T100's manual proof needed
  a *built* `PATH` rather than a trimmed one, and why the test must build one too.
- The route under test, from `README.md` *Install* and `DESIGN.md` §9: `uvx --from "git+…@<tag>"
  taskrail init …`, then `.taskrail/bin/taskrail …`, with `uv` as the only prerequisite. The
  wrapper (`src/taskrail/install.py:219–252`) resolves `local:<path>` with
  `uv run --quiet --project "$root/<path>" taskrail`, and otherwise falls back to
  `uvx --quiet --from "git+${TASKRAIL_SOURCE:-<url>}@$pin" taskrail`.
- Probe of the proposed test, run by hand in the scratchpad (a `PATH` of a directory holding a
  symlink to `uv` only, plus `/usr/bin:/bin`):

  ```
  taskrail on PATH? NO
  init exit: 0
  version = "local:vendor-taskrail"
  taskrail 0.4.0.dev0
  history: not checked (no commits)
  0 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
  wrapper exit: 0
  ```

  So the route works today and the test would pass — it pins behaviour rather than reporting a
  defect. The two subprocesses cost about 0.3 s once `uv`'s environment for this project exists,
  which running the suite already creates.

## Change set

| File | Change |
|---|---|
| `tests/test_install_without_path.py` | New file, one test: `test_init_and_the_wrapper_run_with_taskrail_absent_from_path`. It builds a `PATH` whose only taskrail-related tool is `uv` (a `tmp_path` directory holding a symlink to the real `uv`, followed by `/usr/bin:/bin`), asserts `shutil.which("taskrail", path=…)` is `None` — `pytest.skip` if some other `taskrail` is there — then (1) runs `uv run --directory <project> taskrail --root <repo> init` in a subprocess with that `PATH` and asserts it exits 0 and wrote an executable `.taskrail/bin/taskrail`, (2) points the repository's pin at the checkout's source (`version = "local:vendor-taskrail"`, a symlink, as `test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout` already does), and (3) runs the wrapper itself under the same `PATH` and asserts it exits 0 and prints `0 error(s)`. Module-level `pytest.mark.skipif(shutil.which("uv") is None)`, as `tests/test_json_through_uv_run.py` has. Both subprocesses run without `TASKRAIL_BIN` and without `VIRTUAL_ENV` — the two other ways taskrail could reach them; see *Verification* for why `VIRTUAL_ENV` had to go. |
| `docs/chores/T106-test-init-and-the-wrapper-with-taskrail.md` | This artifact. |
| `docs/chores/README.md` | Index row for T106. |
| `TODO.md` | Only the row's `✅` at close, through `taskrail done`. |

No change to `src/` is planned: the probe above shows the route works. If the finished test proves
a real defect, the fix is the minimum in `src/taskrail/install.py` or the wrapper template, and I
stop and report it before writing it.

## Decisions — answered at the `scope` gate

All three were answered as recommended: **1** cover the `local:` pin only and name the fallback's
transport in the docstring as what is not covered, with neither alternative and no network of any
kind; **2** run `init` as a subprocess through `uv run`; **3** `pytest.skip` with a message when a
`taskrail` turns up in `/usr/bin` or `/bin`, and do not seal the PATH with a symlink per tool. The
tabled change set is the contract: one new test file, no `src/` change.

**1. The `uvx` fallback needs the network, so the test covers the `local:` pin only. Agreed?** —
**Recommendation: yes, cover the `local:` pin and say so in the test's docstring.**
The wrapper's documented default branch is `uvx --quiet --from "git+https://github.com/wadsworthai/taskrail.git@<pin>"`,
which clones over the network on every run; T108 will add CI, where that is unacceptable. The test
would then cover: `init` run as a real process on a `PATH` without `taskrail`, and the wrapper
resolving and running a pinned taskrail on that same `PATH` — the whole route except the transport
of the fallback.
Alternatives: (a) point `TASKRAIL_SOURCE` at a local git repository so the fallback runs as
`uvx --from git+file:///…@<rev>` — it still builds a wheel on every run and still reaches PyPI for
the `uv_build` backend on a cold cache, so it is network-dependent in CI, which the task rules out;
(b) assert the fallback's *command* by stubbing `uvx` with a script on the built `PATH` that
records its argv — offline and cheap, but it tests the shell text of the wrapper rather than that
taskrail runs, and adds a second mechanism for one assertion (KISS). I recommend neither; (b) is
the one to ask for if the fallback branch must be pinned at all.

**2. `init` as a subprocess through `uv run`, or in-process through `main()`?** —
**Recommendation: a subprocess.** `main()` in-process cannot be run "with `taskrail` absent from
`PATH`" in any meaningful sense — the interpreter already holds the code — so only a real process
tests what the row asks. `tests/test_json_through_uv_run.py` is the precedent for spawning
`uv run … taskrail` from the suite, including its `skipif` for a missing `uv`.
Alternative: in-process `main(["--root", repo, "init"])` and a subprocess for the wrapper only —
faster by roughly 0.2 s, and leaves the bootstrap half of the documented route untested.

**3. What to do when some *other* `taskrail` sits in `/usr/bin` or `/bin`?** —
**Recommendation: `pytest.skip` with a message**, the house behaviour of
`test_wrapper_without_cli_or_uvx_explains_what_is_missing`, which skips when the machine has a
system-wide `taskrail` or `uvx`. It cannot happen on a normal machine or on a CI runner, where
`taskrail` is installed, if at all, under `~/.local/bin`.
Alternatives: (a) fail instead of skipping — louder, but it makes an unrelated machine's layout a
red suite; (b) seal the `PATH` completely, symlinking every tool the route needs (`uv`, `git`,
`sed`, `head`, `dirname`, …) into the temporary directory — no skip at all, but it hard-codes a
list of tools that the wrapper's shell text can change out from under, which is more mechanism than
this test needs.

## Out of scope

- **Any change to `src/`**, unless the test proves a defect — and then only the minimum, reported
  before it is written.
- **The `uvx` fallback's transport** (decision 1), and with it `TASKRAIL_SOURCE`.
- **CI**: this test only has to be runnable offline; T108 adds the workflow that runs it.
- **`README.md`, `DESIGN.md` §9, `CHANGELOG.md`**: a test that pins documented behaviour changes
  none of what they say. Re-checked at the `docs` stage.
- **`DESIGN.md` §§3.1, 4, 7**: held by T107 in this autopilot run; if anything there turned out to
  need a change, I would ask at a gate rather than edit it.
- **The existing wrapper tests in `tests/test_install.py`**: left as they are. The new file is
  separate so it cannot collide with T107's tests.

## Verification

Run in this worktree, on the branch.

**The test passes** (`uv run pytest tests/test_install_without_path.py -v`):

```
tests/test_install_without_path.py::test_init_and_the_wrapper_run_with_taskrail_absent_from_path PASSED [100%]

============================== 1 passed in 0.32s ===============================
```

**And it was observed failing for the right reason**, with the pin pointed at a directory that
holds no taskrail source (`(repo / "vendor-taskrail").mkdir()` in place of the symlink), so the
route it protects is really what it asserts:

```
>       assert result.returncode == 0, result.stderr
E       AssertionError: error: Failed to spawn: `taskrail`
E           Caused by: No such file or directory (os error 2)
E
E       assert 2 == 0
FAILED tests/test_install_without_path.py::test_init_and_the_wrapper_run_with_taskrail_absent_from_path
1 failed in 1.00s
```

**The suite passes** — `taskrail checks T106 --stage implement`, 1222 tests where `origin/main`
has 1221:

```
1222 passed in 186.06s (0:03:06)
== lint: not configured
passed test
not configured lint
T106 in …/.worktrees/T106-test-init-and-the-wrapper-with-taskrail: passed
```

`lint` is not configured in this repository — the task's `checks` map defines `test` only.

`taskrail validate` — at close.

### What the first run of the test found: the suite's own virtual environment

The first version of the test passed *even with the pin broken on purpose*. The cause was not
taskrail: pytest itself runs under `uv run`, which exports
`VIRTUAL_ENV=<checkout>/.venv` — an environment that has a `taskrail` entry point — and `uv run`
in the subprocess honours that variable whatever the pin resolves to, so `taskrail` was reachable
without the pin and the assertion proved nothing. The test now drops `VIRTUAL_ENV` from the
subprocess environment, beside the `TASKRAIL_BIN` it already drops, with the reason in a comment.
Both are the same rule: nothing but the built PATH and the pin may supply taskrail. This is a
property of how the suite is run, not a defect in `src/`, so nothing under `src/` was changed and
no follow-up task is opened.
