# T118 — Pass the wrapper's own root to the CLI so a wrapper acts on its own checkout

**Symptom in one line** — `.taskrail/bin/taskrail` computes its own checkout's root, uses it to read
the version pin and to select a `local:` source, and then does not pass it on, so *the wrapper's
location decides which taskrail runs and the current directory decides which repository it acts on.*

[T115](../spikes/T115-decide-how-the-wrapper-and-the-cli-resol.md) decided the fix at its `decide`
gate: the wrapper passes `--root "$root"` on all three `exec` paths that run the CLI, `TASKRAIL_BIN`
is left alone, and no new warning is added. This task confirms the defect against the code on this
branch, settles how the regression test builds a two-checkout situation of its own, and applies the
fix. Paths below are written `$SB` for a throwaway sandbox and `<checkout>` for a working copy;
commands and output are otherwise verbatim.

## Symptom

Two consequences were observed in the field and reproduced by T115: a `claim` recorded against the
wrong checkout (three lanes of one autopilot run), and `upgrade` installing one checkout's skill
sources into another. The second is the serious one: it needs no `--force`, because the manifest's
digest guard only skips a file *a human* edited, and it leaves `git status` clean in the damaged
checkout, so it reads as "forgot to run `upgrade`" rather than as an overwrite.

## Reproduction

Two initialised repositories, `alpha` and `beta`, each pinned to this branch's source, neither one a
worktree of the other and neither one this repository:

```sh
for name in alpha beta; do
  mkdir -p "$SB/$name"; git -C "$SB/$name" init -q -b main
  uv run --quiet --directory <checkout> taskrail --root "$SB/$name" init
  ln -s <checkout> "$SB/$name/vendor-taskrail"
  sed -i 's|^version = .*|version = "local:vendor-taskrail"|' "$SB/$name/.taskrail/config.toml"
done
# alpha's backlog gets one task, E01/T001; beta's stays empty.
```

## Evidence

### E1 — The wrapper acts on the current directory, not on itself

`alpha`'s own wrapper, run from `alpha`, reports `alpha`'s one task. The same wrapper, run with the
current directory in `beta`, reports `beta`'s empty backlog:

```
$ cd $SB/alpha && $SB/alpha/.taskrail/bin/taskrail list --json | head -3
[
  {
    "id": "T001",

$ cd $SB/beta && $SB/alpha/.taskrail/bin/taskrail list --json
[]
```

### E2 — The same split on the installed-CLI `exec` path

The `local:` branch is not the only one affected. With a `taskrail` shim on `PATH` and both configs
pinned to `v0.4.0.dev0`, so the wrapper takes its *installed CLI* branch instead:

```
$ PATH=$SB/bin:/usr/bin:/bin $SB/bin/taskrail --version
taskrail 0.4.0.dev0

$ cd $SB/beta && PATH=$SB/bin:/usr/bin:/bin $SB/alpha/.taskrail/bin/taskrail list --json
[]
```

`alpha`'s wrapper again acted on `beta`. This path costs no `uv` invocation and no network, which is
what makes it the cheap one to put a regression test on.

### E3 — `upgrade` writes into the checkout the current directory names

With the same skill file removed from *both* checkouts, `alpha`'s wrapper run from `beta` restores
`beta`'s copy and leaves `alpha`'s missing:

```
$ rm $SB/alpha/.claude/skills/taskrail-spike/SKILL.md $SB/beta/.claude/skills/taskrail-spike/SKILL.md
$ cd $SB/beta && $SB/alpha/.taskrail/bin/taskrail upgrade
created   .claude/skills/taskrail-spike/SKILL.md
note      skills changed: restart the agent session so it loads them
11 file(s) already up to date
$ echo $?
0

alpha/.claude/skills/taskrail-spike: 0 files
beta/.claude/skills/taskrail-spike:  1 file
```

The *target* comes from the current directory; the *content* comes from the running package, which
under a `local:` pin is the wrapper's own checkout. Exit 0, and nothing says which repository was
written. That is T115 §E4's corruption seen from the other side.

### E4 — The escape hatch already works: the last `--root` wins

`--root` is a global flag on the top-level parser, so a caller's `--root` always lands after one the
wrapper injects, and argparse keeps the last:

```
$ taskrail --root $SB/alpha --root $SB/beta list --json
[]
$ taskrail --root $SB/beta --root $SB/alpha list --json
[
  {
    "id": "T001",
```

### E5 — An injected root costs the rootless subcommands nothing

`--version`, `kind list` and `integration list` all exit 0 with a root injected, and `--version`
exits 0 even when the root holds no `.taskrail/`:

```
$ taskrail --root $SB/alpha --version        -> exit 0
$ taskrail --root $SB/alpha kind list        -> exit 0
$ taskrail --root $SB/alpha integration list -> exit 0
$ taskrail --root /tmp --version
taskrail 0.4.0.dev0
```

### E6 — The wrapper this repository ships is unedited, so `upgrade` rewrites it

```
recorded digest (.taskrail/installed.json): b1ec6706aee3421d343ad16805095c1382fe6ac21d60c3887aeecb8ee7f13be7
current digest  (.taskrail/bin/taskrail):   b1ec6706aee3421d343ad16805095c1382fe6ac21d60c3887aeecb8ee7f13be7
match: True
```

`Installer.managed` (`src/taskrail/install.py:104`) rewrites a managed file whose digest matches the
one it recorded, and skips one that does not with `edited locally; --force replaces it`. So every
consuming repository whose wrapper is untouched picks the fix up with a plain `taskrail upgrade`,
and one that edited its wrapper is told so and left alone.

## Root cause

`wrapper_script()` in `src/taskrail/install.py:220` writes:

```sh
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
```

and then spends `$root` on the pin and the `local:` project only. None of the three `exec` lines that
run the CLI — the `local:` branch, the installed-CLI branch and the `uvx` branch — passes it on. The
CLI therefore falls back to `find_root(Path.cwd())` (`src/taskrail/cli.py:41` and its siblings;
`src/taskrail/config.py:202`), which walks up from the *current directory*. Nothing is wrong in the
CLI: `--root` does exactly what it says, and the wrapper simply never uses it.

## Ruled out

- **The CLI's root resolution.** `find_root` walking up from the cwd is correct and is what makes a
  wrapper work from a subdirectory of its own checkout (T115 §E5/L1). Changing it would break that.
- **A missing warning.** A warning would fire on the legitimate cases too — a subdirectory, and a
  deliberate `--root` — and T115's maintainer answer was explicitly "no new warning" (2A).
- **The claim's branch check.** `_freeze_branch` compares branches, never roots, so it is silent
  whenever two checkouts agree on the branch name, and it exists on `claim` alone. It is not the
  cause and cannot be the cure; `done`'s half of it is T119, not this task.
- **`TASKRAIL_BIN`.** Its `exec` path delegates to a binary of the caller's choosing and is
  deliberately left alone, by the same decision.
- **A `local:`-only fix.** Ruled out at T115 (1C): E2 shows the installed-CLI path has the same
  split, and two rules where one would do offends KISS.
- **An environment variable the wrapper exports.** A new mechanism for what `--root` already
  expresses; ruled out at T115 (1D) under YAGNI.

## Affected areas

- `src/taskrail/install.py` — `wrapper_script()`, three `exec` lines.
- `tests/test_install.py` — the regression test.
- `DESIGN.md` §9 — already describes the fixed behaviour, carrying `(*planned, T118*)`; the marker
  goes once the code does it.
- `CHANGELOG.md` — one bullet under *Unreleased*.
- `.taskrail/bin/taskrail` and `.taskrail/installed.json` in this repository — the wrapper is a
  committed managed file and is regenerated here.

## Proposed fix

Add `--root "$root"` to each of the three `exec` lines in `wrapper_script()` that run the CLI, and
leave the `TASKRAIL_BIN` line untouched:

```sh
exec uv run --quiet --project "$root/${pin#local:}" taskrail --root "$root" "$@"
exec taskrail --root "$root" "$@"
exec uvx --quiet --from "git+${TASKRAIL_SOURCE:-<url>}@$pin" taskrail --root "$root" "$@"
```
