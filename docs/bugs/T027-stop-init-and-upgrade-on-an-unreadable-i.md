# T027 — Stop init and upgrade on an unreadable installed.json

Kind: bug · Epic: E02 · Status: fixed

## Symptom

When `.taskrail/installed.json` cannot be parsed — typically because it holds merge-conflict
markers after merging two branches that ran `init` with different options — taskrail treats
the manifest as if it had never been written:

- `taskrail upgrade` (with or without `--force`) says the manifest is **not found** and exits 3,
  although the file is right there.
- `taskrail init` exits 0 and **overwrites** the manifest, dropping the recorded integrations,
  the `github_workflow` extra and every managed file's digest. Nothing on screen says so.

Other unreadable shapes crash with a Python traceback (exit 1) instead: valid JSON that is not
an object, bytes that are not UTF-8, and a manifest path that cannot be read (a directory, no
read permission).

Expected: both commands stop before writing anything, exit 2 and name the unreadable manifest.
A missing manifest (taskrail never installed) keeps its current behaviour: `upgrade` exits 3
with "not found", `init` installs.

First reported as evidence E3 of
[T007](../spikes/T007-design-taskrail-s-autopilot-from-existin.md).

## Reproduction

A throwaway git repository under a temporary directory, using the CLI from this branch
(`uv run taskrail --root <repo> …`):

```bash
git init -b main && git commit --allow-empty -m root
taskrail init --integration claude && git add -A && git commit -m "init claude"
git switch -c a    && taskrail init --integration opencode && git add -A && git commit -m "init opencode"
git switch main && git switch -c b && taskrail init --github-workflow && git add -A && git commit -m "init workflow"
git merge a        # conflicts in .taskrail/installed.json
taskrail upgrade; taskrail upgrade --force; taskrail init
cat .taskrail/installed.json
```

## Evidence

Run at `dd646f5` (origin/main).

The merge:

```
$ git merge a
Auto-merging .taskrail/installed.json
CONFLICT (content): Merge conflict in .taskrail/installed.json
Automatic merge failed; fix conflicts and then commit the result.
$ git status --short
M  .claude/skills/taskrail/SKILL.md
UU .taskrail/installed.json
```

The conflicted manifest:

```
     1	{
     2	  "version": "v0.2.0",
     3	  "integrations": [
     4	    "claude",
     5	    "opencode"
     6	  ],
     7	  "extras": {
     8	    "github_workflow": true
     9	  },
    10	  "files": {
    11	    ".claude/skills/taskrail-bug/SKILL.md": "6ac6d1f8f7fbbe12403bcd0e537d209bb1c22b544e8faa23193c23e6d5ade234",
    12	    ".claude/skills/taskrail-chore/SKILL.md": "a9bb64718816008d4185eb64d0e95a7759f537a2631d678d9987f6e2c962b880",
    13	    ".claude/skills/taskrail-feature/SKILL.md": "93aefeb985279c1d0b094bca45850d9a64ed23d8756029ed3202fb8e2becb9f8",
    14	    ".claude/skills/taskrail-spike/SKILL.md": "1e7ba5592f0597806d66064e9ef9c6e2ca9a083dfe9b738070dfdcd1db6a4399",
    15	<<<<<<< HEAD
    16	    ".claude/skills/taskrail/SKILL.md": "9ae9e3caa5ef2be0c3b4a7d86d7773b5cc66f8c721b2f37c37c6771a33e00d9e",
    17	    ".github/workflows/taskrail.yml": "2ea4e98069cccbffa72f49add5c64dc9a4059aad8d5ec7864bd36fb07df57c29",
    18	=======
    19	    ".claude/skills/taskrail/SKILL.md": "849ca713feed4b00bc6454973e9c3409c722b375fa52aeb9c6270e7cdecfaf4a",
    20	>>>>>>> a
    21	    ".taskrail/bin/taskrail": "3d28495e28f640bc63eefa2d40edcfe04642691dd520ee4556797595c788f10d"
    22	  }
    23	}
```

Both sides were readable (`git show :2:` / `:3:`): ours `['claude'] {'github_workflow': True}`
with 7 files, theirs `['claude', 'opencode'] {}` with 6 files. Then:

```
$ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
$ taskrail upgrade --force
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
$ taskrail init
note      no agent integration installed; pass --integration claude or --integration opencode
3 file(s) already up to date
exit=0
$ cat .taskrail/installed.json
{
  "version": "v0.2.0",
  "integrations": [],
  "extras": {},
  "files": {
    ".taskrail/bin/taskrail": "3d28495e28f640bc63eefa2d40edcfe04642691dd520ee4556797595c788f10d"
  }
}
```

Other shapes, each in a fresh repository after `init --integration claude --github-workflow`,
running `upgrade` then `init` (last lines of output):

```
--- [empty file]            $ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
--- [empty file]            $ taskrail init
note      no agent integration installed; pass --integration claude or --integration opencode
3 file(s) already up to date
exit=0
manifest after: integrations=[] {} 1
--- [[]]                    $ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
--- [[]]                    $ taskrail init
AttributeError: 'list' object has no attribute 'get'
exit=1
--- ["x"]                   $ taskrail upgrade
AttributeError: 'str' object has no attribute 'get'
exit=1
--- ["x"]                   $ taskrail init
AttributeError: 'str' object has no attribute 'get'
exit=1
--- [byte 0xff, not UTF-8]  $ taskrail upgrade
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 13: invalid start byte
exit=1
--- [byte 0xff, not UTF-8]  $ taskrail init
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 13: invalid start byte
exit=1
--- [{}]                    $ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
--- [{}]                    $ taskrail init
note      no agent integration installed; pass --integration claude or --integration opencode
3 file(s) already up to date
exit=0
manifest after: integrations=[] {} 1
--- [a directory]           $ taskrail upgrade
IsADirectoryError: [Errno 21] Is a directory: '<tmp>/directory/.taskrail/installed.json'
exit=1
--- [a directory]           $ taskrail init
IsADirectoryError: [Errno 21] Is a directory: '<tmp>/directory/.taskrail/installed.json'
exit=1
--- [mode 000, non-root]    $ taskrail upgrade
PermissionError: [Errno 13] Permission denied: '<tmp>/perm/.taskrail/installed.json'
exit=1
--- [mode 000, non-root]    $ taskrail init
PermissionError: [Errno 13] Permission denied: '<tmp>/perm/.taskrail/installed.json'
exit=1
```

Baseline, no manifest at all (must not change):

```
--- [missing] $ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
--- [missing] $ taskrail init --integration claude
created   .gitignore
note      skills changed: restart the agent session so it loads them
0 file(s) already up to date
exit=0
```

## Root cause

`read_manifest` in `src/taskrail/install.py` folds "the file does not exist"
and "the file is not valid JSON" into the same result, an empty dict:

```python
def read_manifest(root: Path) -> dict:
    try:
        return json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```

Both callers then act on that empty dict as "never installed":

- `upgrade` checks `if not manifest:` and raises `FileNotFoundError("… not found; run
  `taskrail init` first")`, which `cmd_upgrade` maps to exit 3.
- `install` (behind `init`) builds `Installer(root)`, whose `manifest` is `{}` and whose
  `files` digests are therefore empty; it selects only the integrations passed on the command
  line, keeps no extras, and `save_manifest` writes that back over the unreadable file. Skills
  are not deleted only because, with no recorded digests, `remove_managed` finds nothing to
  remove and `managed` skips existing skills as "not written by taskrail".

The same function lets every other failure escape unhandled: `UnicodeDecodeError` and `OSError`
subclasses other than `FileNotFoundError` are not caught, and a JSON value that is not an
object is returned as is, so the first `manifest.get(...)` raises `AttributeError`. These
reach `main`, which only maps `ConfigError` and `GitError` to exit 2, hence the tracebacks.

The pattern dates from the commit that introduced the installer (`473f784`); nothing in
`DESIGN.md` or the README says an unreadable manifest should be treated as missing.

## Ruled out

- **Git merge driver or `.gitattributes` for the manifest.** A merge driver could avoid the
  conflict, but a hand edit, a truncated write or a bad checkout produces the same unreadable
  file; the defect is in how taskrail reacts, not in how the file got there. (T007 lists an
  optional merge driver separately, T004.)
- **`init` deleting skills.** Checked in the reproduction after `init`: `.claude/skills` still
  holds all five skills and `.github/workflows/taskrail.yml` is still there; `git status --short`
  shows only `M  .claude/skills/taskrail/SKILL.md` (from the merge) and `UU
  .taskrail/installed.json`. With an empty `files` map `remove_managed` has no recorded path to
  remove. The loss is the manifest's state, not files.
- **`--force` changing the outcome.** `upgrade --force` fails identically (exit 3) because the
  check happens before `force` is used; `init --force` would additionally overwrite existing
  skills whose digests are no longer known — the same root cause, worse effect.
- **`save_manifest` writing a bad file.** It always writes `json.dumps(...)` of a dict with
  `version`, `integrations`, `extras`, `files`; the reproduced files became unreadable through
  git, not through taskrail.
- **`cmd_upgrade` exit-code mapping.** It correctly maps `FileNotFoundError` to exit 3 for a
  missing manifest; it is fed the wrong exception by `upgrade`.
- **`config.toml` handling.** `load_config` already raises `ConfigError` for invalid TOML (exit
  2, naming the file), which is the behaviour this manifest should match; not affected.
- **Similar lenient readers elsewhere** — `claims._load` (claim files) and `ids.reservations`
  (ID reservations) also swallow `JSONDecodeError`. They are local state under the git common
  dir, never committed, so they are not reached by a merge; out of this task's scope and not
  changed here.

## Affected areas

- `src/taskrail/install.py`: `read_manifest`, and through it `Installer.__init__`
  (`install`, i.e. `taskrail init`) and `upgrade` (`taskrail upgrade`). No other module reads
  the manifest.
- Exit codes of `taskrail init` and `taskrail upgrade` for an unreadable manifest.

## Proposed fix

1. In `read_manifest`, keep returning `{}` only for `FileNotFoundError`. For any other failure
   to read it as a JSON object — `OSError`, `UnicodeDecodeError`, `json.JSONDecodeError`, or a
   top-level value that is not an object — raise `ConfigError` naming `.taskrail/installed.json`
   and the reason, and saying how to recover: resolve the conflict or fix the file, or delete it
   to reinstall from scratch. `ConfigError` is already mapped to exit 2 by `main`, so neither
   `cmd_init` nor `cmd_upgrade` needs to change.
2. `Installer.__init__` reads the manifest before `install` seeds or writes anything, so raising
   there leaves the repository untouched. `--force` does not bypass it: it governs overwriting
   managed files, and the manifest's content cannot be recovered by force.
3. A regression test in `tests/test_install.py` that installs, replaces the
   manifest with conflict markers, and asserts `init` and `upgrade` (also `--force`) exit 2 with
   the file named in stderr and the manifest bytes unchanged; plus parametrised shapes (empty,
   non-object, not UTF-8) and a check that a missing manifest still gives `upgrade` exit 3.
4. One bullet under `## Unreleased` in `CHANGELOG.md`.

## Decisions at the diagnose gate

Recorded in [the autopilot decision record](../autopilot/decisions/T027-stop-init-and-upgrade-on-an-unreadable-i.md):
every read failure refuses with exit 2 (syntax errors including conflict markers and an empty
file, non-object values, non-UTF-8 bytes, read errors); `--force` refuses too; a readable `{}`
keeps its current behaviour.

## Fix

### Regression test, observed failing first

Added to `tests/test_install.py`, before touching `install.py`:

- `test_an_unreadable_manifest_stops_init_and_upgrade` — parametrised over `init`,
  `init --force`, `upgrade`, `upgrade --force` × conflict markers, empty file, not an object
  (`[]`), not UTF-8, a directory. After `init --integration claude --github-workflow` it breaks
  the manifest, runs the command and asserts exit 2, `.taskrail/installed.json` in stderr, and
  every file outside `.git` byte-for-byte unchanged.
- `test_a_manifest_without_read_permission_stops_init_and_upgrade` — mode 000; skipped as root.
- `test_an_empty_object_manifest_is_still_treated_as_nothing_installed` — `{}` keeps `upgrade`
  exit 3 and `init` exit 0 (decision 4).
- The existing `test_upgrade_needs_a_previous_init` already pins a missing manifest to exit 3.

Run against the unfixed `install.py` (commit `8fd1e73` plus the tests only):

```
$ uv run pytest -q --tb=line -rfEp tests/test_install.py -k "unreadable or read_permission or empty_object or previous_init"
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init-conflict markers]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init-empty file]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init-not an object]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init-not UTF-8]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init-a directory]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init --force-conflict markers]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init --force-empty file]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init --force-not an object]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init --force-not UTF-8]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[init --force-a directory]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade-conflict markers]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade-empty file]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade-not an object]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade-not UTF-8]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade-a directory]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade --force-conflict markers]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade --force-empty file]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade --force-not an object]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade --force-not UTF-8]
FAILED tests/test_install.py::test_an_unreadable_manifest_stops_init_and_upgrade[upgrade --force-a directory]
FAILED tests/test_install.py::test_a_manifest_without_read_permission_stops_init_and_upgrade
PASSED tests/test_install.py::test_upgrade_needs_a_previous_init
PASSED tests/test_install.py::test_an_empty_object_manifest_is_still_treated_as_nothing_installed
21 failed, 2 passed, 32 deselected in 1.13s
```

The failure reasons match the root cause (distinct lines of `--tb=line`):

```
E   AssertionError: assert 0 == 2                                             (init, init --force: conflict markers, empty file — manifest treated as missing and overwritten)
E   AttributeError: 'list' object has no attribute 'get'                      (init, init --force: not an object — install.py:86, Installer.__init__)
E   AssertionError: taskrail: .taskrail/installed.json not found; run `taskrail init` first
    assert 3 == 2                                                             (upgrade, upgrade --force: conflict markers, empty file, not an object)
E   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 13: invalid start byte   (every command: not UTF-8)
E   IsADirectoryError: [Errno 21] Is a directory: '<tmp>/.taskrail/installed.json'               (every command: a directory)
E   PermissionError: [Errno 13] Permission denied: '<tmp>/.taskrail/installed.json'              (mode 000)
```

### Change

Only `read_manifest` in `src/taskrail/install.py` changed; `cli.py` did not:

- `FileNotFoundError` still returns `{}`, so a never-installed repository behaves as before.
- `OSError` (directory, permission, …), `UnicodeDecodeError` and `json.JSONDecodeError` raise
  `ConfigError`, and so does a top-level JSON value that is not an object. The message names
  `.taskrail/installed.json`, gives the reason, and says how to recover: "resolve any merge
  conflict or fix the file, or delete it to reinstall from scratch".
- `main` already maps `ConfigError` to exit 2. `install` constructs `Installer` — which reads
  the manifest — before seeding or writing anything, and `upgrade` reads it before calling
  `install`, so a refusal writes nothing; `--force` is never consulted.

## Verification

Regression tests after the fix:

```
$ uv run pytest -q --tb=short -rfEp tests/test_install.py -k "unreadable or read_permission or empty_object or previous_init"
23 passed, 32 deselected in 0.90s
```

Stage checks:

```
$ uv run pytest -q
284 passed in 16.07s
```

`lint` is named by the stage but has no command in this repository's `checks` (neither
`.taskrail/config.toml` nor `pyproject.toml` configures one), so it was not run.

End to end, in a throwaway repository with the same merge conflict as in *Reproduction*
(deleted afterwards):

```
$ git merge a
Automatic merge failed; fix conflicts and then commit the result.
$ taskrail upgrade
taskrail: .taskrail/installed.json cannot be read (Expecting property name enclosed in double quotes: line 15 column 1 (char 604)); resolve any merge conflict or fix the file, or delete it to reinstall from scratch
exit=2
$ taskrail upgrade --force
(same message)
exit=2
$ taskrail init
(same message)
exit=2
$ taskrail init --force
(same message)
exit=2
$ taskrail init --integration claude
(same message)
exit=2
$ sha256sum -c before.sum
.taskrail/installed.json: OK
$ git status --short
M  .claude/skills/taskrail/SKILL.md
UU .taskrail/installed.json
```

After resolving the conflict (`git checkout --theirs .taskrail/installed.json`), `init
--github-workflow` succeeds and the manifest keeps what both branches recorded:

```
$ taskrail init --github-workflow
9 file(s) already up to date
exit=0
integrations: ['claude', 'opencode'] extras: {'github_workflow': True} files: 7
```

Other shapes, `upgrade` in a fresh repository each:

```
--- [empty]      taskrail: .taskrail/installed.json cannot be read (Expecting value: line 1 column 1 (char 0)); resolve any merge conflict or fix the file, or delete it to reinstall from scratch   exit=2
--- [[]]         taskrail: .taskrail/installed.json cannot be read (expected a JSON object, found list); …   exit=2
--- [0xff]       taskrail: .taskrail/installed.json cannot be read ('utf-8' codec can't decode byte 0xff in position 13: invalid start byte); …   exit=2
--- [directory]  taskrail: .taskrail/installed.json cannot be read (Is a directory); …   exit=2
--- [mode 000]   taskrail: .taskrail/installed.json cannot be read (Permission denied); …   exit=2
--- [{}]         taskrail: .taskrail/installed.json not found; run `taskrail init` first   exit=3
                 $ taskrail init → 3 file(s) already up to date   exit=0
```

Missing manifest, unchanged:

```
$ taskrail upgrade
taskrail: .taskrail/installed.json not found; run `taskrail init` first
exit=3
$ taskrail init --integration claude
0 file(s) already up to date
exit=0
```
