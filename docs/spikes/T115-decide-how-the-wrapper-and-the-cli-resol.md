# T115 — Decide how the wrapper and the CLI resolve the repository root when the cwd is another checkout

**Verdict** — The wrapper already computes its own checkout's root, uses it to read the version pin
and to select the `local:` source, and then **does not pass it to the CLI**. So *the wrapper's
location decides which taskrail runs, and the cwd decides which repository it acts on.* That split
is the defect; it is not a missing feature. **Recommendation: close the split** — have the wrapper
pass `--root "$root"`, which is three lines in the template `install.py` writes. It is measured
below to fix both observed incidents, to keep every legitimate case working, and to leave the
caller a working escape hatch, because `--root` is a global flag whose **last occurrence wins**, so
an explicit `--root` still overrides the injected one. **A second, separate warning is not
recommended**: with the split closed there is nothing left for it to warn about that is not also
legitimate. What the split does *not* cover — an agent typing a relative `.taskrail/bin/taskrail`
from the wrong cwd, where the wrapper and the cwd agree and are both the wrong repository — is
covered today by `claim`'s branch warning and by **nothing at all** on `done`, which writes a `✅`
into the wrong checkout's backlog and exits 0 in silence. Extending that existing warning to `done`
is proposed as a second, small follow-up. `DESIGN.md` §9's sentence about `local:<path>` is
currently true of the code and silent about the target repository, and is the likely source of the
wrong mental model; a replacement is proposed below.

**The maintainer answered on 2026-09-18: yes to question 1, no new disagreement warning but yes to
2C for question 2, and the proposed §9 wording for question 3.** The wording is applied in this
task; the two behaviour changes are [T118](../../TODO.md) (the wrapper passes its own root, all
three `exec` paths) and [T119](../../TODO.md) (`done` warns like `claim`). The full result is in
*Outcome*.

This spike changed no code, no test, no configuration and no skill; the one file it changed outside
`docs/` is `DESIGN.md` §9's last paragraph, which the `decide` gate approved. Everything measured
below was run in a throwaway clone under the scratchpad, with its remote removed; the patched
wrapper used in the P-series is a sandbox-only copy named `taskrail-patched` and exists nowhere in
this repository.

## Question

Three, from the task row:

1. Should the wrapper derive `--root` from its own path?
2. Should the CLI warn when the wrapper's location and the cwd disagree?
3. What should `DESIGN.md` §9 say?

## Evidence

Paths below are written `<primary>` for a repository's primary checkout, `<lane>` for a task
worktree and `$SB` for the sandbox; commands and output are otherwise verbatim.

### E1 — The wrapper computes its own root and then throws it away

`.taskrail/bin/taskrail`, written by `src/taskrail/install.py`:

```sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ -n "${TASKRAIL_BIN:-}" ]; then
  exec "$TASKRAIL_BIN" "$@"
fi
pin=$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$root/.taskrail/config.toml" | head -n 1)
case "$pin" in
  local:*)
    exec uv run --quiet --project "$root/${pin#local:}" taskrail "$@"
    ;;
esac
```

`$root` reaches the pin and the `local:` project and stops there. The CLI then takes its root from
the cwd — `src/taskrail/cli.py:41` and five sibling lines:

```python
root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
```

and `src/taskrail/config.py:202`:

```python
def find_root(start: Path) -> Path:
    """Walk up from `start` to the directory holding `.taskrail/config.toml`."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / CONFIG_PATH).is_file():
            return directory
```

`init` is the one exception (`cli.py:1428`, `_install_root`): `--root`, else the cwd's git
toplevel, else the cwd.

**The shortest demonstration of the split is this task's own claim.** The agent's shell starts in
the primary checkout and its cwd resets between commands, so recording the right branch needed
*both* halves — the worktree's wrapper path *and* an explicit `--root`:

```
$ <lane>/.taskrail/bin/taskrail --root <lane> claim T115 --run 20260918-1 --json
{"claimed": true, "created": true,
 "claim": {"id": "T115", "branch": "T115-decide-how-the-wrapper-and-the-cli-resol",
           "worktree": ".../.worktrees/T115-decide-how-the-wrapper-and-the-cli-resol", ...},
 "branch_recorded": true, "warning": null, "record_remote": null}
```

The wrapper path alone would have picked the worktree's *code* and the primary checkout's
*repository*.

### E2 — The visible symptom: a claim against the wrong checkout, and the warning it prints

cwd = the primary checkout (on `main`), wrapper = the lane's own:

```
$ cd $SB/primary && $SB/lane/.taskrail/bin/taskrail claim T116
taskrail: warning: T116 was claimed on branch main, but its branch is T116-pin-a-setup-uv-tag-that-exists-in-the-ge; work on that branch, or run `taskrail branch T116 <NAME>` to name the branch the task is worked on
claimed T116 as <owner>
$ echo $?
0
```

The warning comes from `_freeze_branch` (`cli.py:299`), printed at `cli.py:278`:

```python
    where = f"branch {claimed_on}" if claimed_on else "a detached HEAD"
    return False, (
        f"{task.id} was claimed on {where}, but its branch is {resolved or '—'}; work on that branch, "
        f"or run `taskrail branch {task.id} <NAME>` to name the branch the task is worked on"
    )
```

**What it covers and what it does not.** It fires here, and it fired for T106, T108 and T110. But:
it goes to **stderr** while stdout says `claimed`; the exit code is **0**; the claim is **written
anyway**, into the wrong checkout; under `--json` it is a `warning` field a caller can ignore; it
compares the **branch**, never the **root**, so it is silent whenever the two checkouts agree on
the branch name; and it exists on **`claim` alone**. Claims live in the common git directory
(`$SB/primary/.git/taskrail/claims/T116.json`), shared by every worktree of a repository, so the
damage is confined to the recorded `branch` and `worktree` — which is why release-and-re-claim was
enough for those three lanes.

### E3 — The silent symptom: `done` ticks the wrong backlog, with no warning at all

The lane claims correctly from inside itself, on its own task branch. Then a single later command
is run with the cwd sitting in the primary checkout:

```
$ cd $SB/lane && $SB/lane/.taskrail/bin/taskrail claim T116
claimed T116 as <owner>

$ cd $SB/primary && $SB/lane/.taskrail/bin/taskrail done T116
T116 done
$ echo $?
0
```

```
$ grep -o '^| . | T116 |[^|]*|' $SB/primary/TODO.md
| ✅ | T116 | bug     |
$ grep -o '^| . | T116 |[^|]*|' $SB/lane/TODO.md
| ⬜ | T116 | bug     |

$ git -C $SB/primary status --short
 M TODO.md
$ git -C $SB/lane status --short
(empty)
```

The `✅` lands on **`main`**, in the primary checkout, uncommitted; the branch that will carry the
pull request keeps its `⬜`; the claim is released; nothing is printed but `T116 done`. This is the
answer to "is the `claim` warning enough": it is the only warning there is, and the command with
the worst blast radius has none.

### E4 — The worst instance, reproduced: `upgrade` installs one checkout's sources into another

`upgrade` takes its **target** from the cwd (`cli.py:1454`):

```python
def cmd_upgrade(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
```

while the **content** comes from the running package (`install.py:16`), which under a `local:.` pin
is the *wrapper's* checkout:

```python
PACKAGE = Path(__file__).parent
SKILLS_SOURCE = PACKAGE / "skills"
HARNESS_SOURCE = PACKAGE / "integrations"
```

Reproduced. The lane branch carries its own change to a skill **source**, and upgrades itself
correctly first:

```
$ cd $SB/lane && $SB/lane/.taskrail/bin/taskrail upgrade --force
updated   .claude/skills/taskrail/SKILL.md
note      skills changed: restart the agent session so it loads them
11 file(s) already up to date
$ grep -c LANE-CHANGE-MARKER $SB/lane/.claude/skills/taskrail/SKILL.md
1
```

Now the accident — the **primary** checkout's wrapper, cwd still the lane:

```
$ cd $SB/lane && $SB/primary/.taskrail/bin/taskrail upgrade --force
updated   .claude/skills/taskrail/SKILL.md
note      skills changed: restart the agent session so it loads them
11 file(s) already up to date
$ echo $?
0
$ grep -c LANE-CHANGE-MARKER $SB/lane/.claude/skills/taskrail/SKILL.md
0
```

The output is **character-for-character the same** as the correct run. Three things make this worse
than E2 and E3:

- **`--force` is not needed.** Repeated without it, the marker is dropped just the same: the
  manifest's digest guard skips a file *a human edited*, and this file was written by taskrail
  itself, so it is considered unedited and is rewritten.
- **It erases its own evidence.** After the accident `git -C $SB/lane status --short` is **empty**:
  the installed copy has been reverted to what `HEAD` holds, so the working tree looks clean and
  the lane sees nothing to investigate.
- The lane's **source** still carries the change, so a reviewer diffing the branch sees the change
  present and the installed copy stale — which reads as "forgot to run `upgrade`", not as
  "something overwrote it".

### E5 — The legitimate cases, measured

| # | Case | Today | Under a location-derived root |
|---|---|---|---|
| L1 | wrapper run from a subdirectory of its own checkout (`cwd=$SB/primary/src/taskrail`) | works — `find_root` walks up | works (P4) |
| L2 | a checkout's wrapper aimed deliberately at another repository | acts on the cwd's repository | acts on the wrapper's; `--root` restores it (P3) |
| L3 | `taskrail checks`, which runs commands in another worktree by design | unaffected | unaffected |

**L3 is not a cost, and this matters because it was the one feared to be decisive.** `checks` never
invokes the wrapper: `checks.run_checks` runs each command with `subprocess.run(..., cwd=path)`
where `path` is the task's worktree, and reads the check definitions from the worktree's own config
(`_worktree_project`). With the sandbox lane's check set to `pwd`:

```
$ cd $SB/primary && $SB/primary/.taskrail/bin/taskrail checks T116
== test: pwd
$SB/lane
passed test
T116 in $SB/lane: passed
```

The root came from the cwd (the primary checkout) and the command ran in the lane — and a
location-derived root would have given the same primary root for that same wrapper. A check command
that calls the wrapper *relatively* resolves to the task worktree's own wrapper either way:

```
$ # lane check set to:  sh -c 'pwd; readlink -f .taskrail/bin/taskrail'
== test: sh -c 'pwd; readlink -f .taskrail/bin/taskrail'
$SB/lane
$SB/lane/.taskrail/bin/taskrail
```

**L2 deserves a second look, because it is already broken in a way nobody has noticed.** The
wrapper reads the version pin from **its own** root, so aiming one checkout's wrapper at another
repository already runs the wrong version for that repository:

```
$ grep '^version' $SB/primary/.taskrail/config.toml
version = "local:."   # run taskrail from this checkout's source
$ grep '^version' $SB/other/.taskrail/config.toml
version = "v0.4.0"

$ cd $SB/other && $SB/primary/.taskrail/bin/taskrail list   # runs primary's local source, not v0.4.0
```

So the wrapper is not, and never was, a general-purpose "aim anywhere" tool. The correct route for
another repository is that repository's own wrapper, or `--root` — which is exactly what `--root`
is documented for.

### E6 — The one-line change, measured

Sandbox-only copy `taskrail-patched`, differing from the installed wrapper by one line:

```
$ diff $SB/primary/.taskrail/bin/taskrail $SB/primary/.taskrail/bin/taskrail-patched
14c14
<     exec uv run --quiet --project "$root/${pin#local:}" taskrail "$@"
---
>     exec uv run --quiet --project "$root/${pin#local:}" taskrail --root "$root" "$@"
```

**P1 — the claim incident is fixed.** cwd = the primary checkout, the lane's patched wrapper, no
`--root` given:

```
$ cd $SB/primary && $SB/lane/.taskrail/bin/taskrail-patched claim T116 --json
    "branch": "T116-pin-a-setup-uv-tag-that-exists-in-the-ge",
    "worktree": "$SB/lane",
  "warning": null,
```

**P2 — the upgrade corruption is fixed.** cwd = the lane, the primary checkout's patched wrapper:

```
$ cd $SB/lane && $SB/primary/.taskrail/bin/taskrail-patched upgrade --force
12 file(s) already up to date
$ grep -c LANE-CHANGE-MARKER $SB/lane/.claude/skills/taskrail/SKILL.md
1
```

The upgrade landed on the primary checkout, where that wrapper lives, and the lane's own change
survived. A corrupting operation became a self-consistent no-op.

**P3 — the escape hatch survives, because the last `--root` wins.** cwd = the lane throughout; the
backlogs were made distinguishable (primary 106 rows, lane 107):

```
UNPATCHED primary wrapper, no --root        -> 107 rows  = the lane (today: the cwd decides)
PATCHED   primary wrapper, no --root        -> 106 rows  = primary (the wrapper's own checkout)
PATCHED   primary wrapper, --root $SB/lane  -> 107 rows  = the lane (the caller's --root wins)
```

This is not incidental: `--root` is a global flag on the top-level parser and must precede the
subcommand, so the caller's `--root` always lands after the injected one and argparse keeps the
last.

**P4/P5 — nothing else moves.** The subdirectory case still resolves (`show T116` from
`$SB/primary/src/taskrail`); `--root <dir> init` through the patched wrapper still initialises that
directory; and `--version`, `kind list`, `integration list` and `self upgrade --tag … --dry-run`
all exit 0 unchanged, since subcommands that need no root ignore the flag.

### E7 — What the change would *not* fix

```
$ cd $SB/primary          # the wrong checkout
$ .taskrail/bin/taskrail list          -> 106 rows (primary)
$ .taskrail/bin/taskrail-patched list  -> 106 rows (primary)
```

When an agent types the **relative** path from the wrong cwd, the wrapper and the cwd agree and are
both the wrong repository. No root-resolution rule can distinguish that from correct use. For
`claim` it is still caught by E2's branch warning; for `done` it is caught by nothing (E3).

### E8 — `DESIGN.md` §9 as it stands

> A pin of the form `local:<path>` makes the wrapper run the taskrail source at that path in the
> current checkout, so a worktree runs its own branch's code; `upgrade` never replaces such a pin.

True of the code, silent about the target repository. "a worktree runs its own branch's code" reads
naturally as "a worktree's wrapper operates on that worktree", which is the belief E2, E3 and E4 all
punish. §9 says nothing anywhere about which repository the wrapper acts on.

## Options considered

**Question 1 — should the wrapper derive `--root` from its own path?**

- **1A. Yes, pass `--root "$root"`.** Three lines in the wrapper template (`install.py`), one per
  `exec` path: the `local:` branch, the installed-CLI branch and the `uvx` branch. Fixes E2 and E4
  (P1, P2). Keeps L1 and L3 (P4, E5). Changes L2, where `--root` restores the old behaviour (P3)
  and where today's behaviour already ignores the target repository's pin. Does not fix E7. Cost:
  every consuming repository's wrapper changes at its next `upgrade`, and only if its wrapper is
  unedited; a repository that deliberately relied on cwd-targeting must add `--root`.
- **1B. No, leave it.** Zero change, zero risk to L2. Leaves E4's silent cross-checkout corruption
  in place, since nothing else can catch it.
- **1C. Pass `--root` only for `local:` pins.** Narrower, but it makes the wrapper behave
  differently for developers of taskrail than for its consumers — two rules where one would do.
  Rejected under KISS.
- **1D. Make the CLI itself prefer the wrapper's location** (e.g. via an environment variable the
  wrapper exports). A new mechanism to express what `--root` already expresses. Rejected under
  YAGNI and KISS.

**Question 2 — should the CLI warn when the wrapper's location and the cwd disagree?**

- **2A. No new warning.** With 1A the resolved root *is* the wrapper's, so the only remaining
  disagreement is "the cwd is somewhere else", which is L1 (a subdirectory, legitimate and common)
  and L2 with an explicit `--root` (legitimate and deliberate). A warning would fire on correct use
  and on nothing else.
- **2B. Warn when the cwd is not inside the resolved root.** Coherent only if 1A is rejected: then
  it is the cheapest thing that makes E4 audible. It still cannot see E7, and it fires on every
  `--root` use unless suppressed.
- **2C. Extend the existing branch check to `done`.** Not a new mechanism: `_freeze_branch` already
  computes the task's branch with `branches.resolve`, and `done` simply does not consult it. This
  is the only option that touches E7, and it covers the command with the worst blast radius (E3).
  Distinct from 2A/2B and compatible with either.

**Question 3 — what should `DESIGN.md` §9 say?** Either it keeps quiet about the target repository
(status quo, which misled three lanes), or it states the rule in one sentence. Under 1A the
sentence is a description of what the wrapper does; under 1B it is a convention with nothing behind
it.

## Recommendation

**1A + 2A, with 2C as a separate follow-up, and the §9 wording below.**

1A is recommended not as a new feature but as the removal of a split that should not exist: the
wrapper already knows its root and already uses it for the pin, and the version pin is the proof
that the wrapper is *meant* to be an instrument of one checkout. Making it act on that checkout is
the smaller design, not the larger one — after it, the rule is one sentence ("the wrapper you
invoke is the repository you act on"), and `--root` remains the single documented way to point
elsewhere, with the last occurrence winning (P3).

This is where CLAUDE.md's KISS entry — "a documented convention over a mechanism that enforces it" —
has to be read carefully rather than quoted. It prefers a convention over a *mechanism*. 1A adds no
mechanism: it deletes an inconsistency in three lines and introduces nothing to configure, nothing
to suppress and no new failure mode. 1D and 2B would be mechanisms, and they are the ones the
principle argues against. That is why the recommendation adopts the first and declines the others.

**On "what makes the convention stick", asked of the documentation-only route (1B + §9 wording).**
Honestly: for E2 it could stick, because `claim` already prints a warning and a reader who has read
§9 will recognise it. For E4 nothing would make it stick, and that is the reason to decline 1B.
The instruction "run the wrapper from inside your worktree" is a cwd discipline, and a cwd is
ambient state that resets between commands, is invisible in a transcript, and is not part of the
command an agent copies. Three lanes in one run did not miss a sentence; they were following a rule
whose observable form — the wrapper path they typed — was already correct. A convention can only
stick when the thing the reader controls is the thing the rule is about, and 1A is precisely the
change that makes the wrapper path that thing. The documentation is still worth writing; it is just
not sufficient on its own.

Proposed replacement for §9's last paragraph, final sentence onward — the addition is the second
sentence:

> A pin of the form `local:<path>` makes the wrapper run the taskrail source at that path in its own
> checkout, so a worktree runs its own branch's code; `upgrade` never replaces such a pin. **The
> wrapper also operates on its own checkout: it passes that root to the CLI, so which wrapper is
> invoked decides which repository is acted on, whatever the current directory is. `--root` points
> it at another repository, and overrides that default.** `TASKRAIL_BIN` overrides the wrapper
> entirely; `TASKRAIL_SOURCE` overrides the repository URL.

Under 1B the same paragraph would instead have to read "…the wrapper acts on the repository the
current directory is in, whichever wrapper is invoked; run it from inside the checkout you mean, or
pass `--root`", which is the convention with nothing behind it.

## Outcome

The maintainer accepted the recommendation in full on 2026-09-18:

| Question | Answer |
|---|---|
| 1 — the wrapper passes its own root to the CLI | **yes**, on all three `exec` paths |
| 2 — a warning when the wrapper's location and the cwd disagree | **no**; and **yes** to 2C, `done` warning as `claim` does |
| 3 — `DESIGN.md` §9 | the proposed replacement, **approved and applied in this task** |

Two follow-up tasks carry the behaviour changes; neither is implemented here.

- **T118** (`bug`, 2pt, E05) — *Pass the wrapper's own root to the CLI so a wrapper acts on its own
  checkout.* Its row carries the two findings that only the reproduction could show, because they
  are what justify fixing this rather than documenting it: the `upgrade` accident needs **no
  `--force`**, since the manifest digest guard only skips files a human edited, and it leaves `git
  status` **clean** in the damaged checkout, so it reads as "forgot to run `upgrade`" rather than as
  an overwrite. The row also records that its regression test must pin `--root` being a global flag
  whose **last occurrence wins** — that is what leaves a caller the escape hatch measured in P3 —
  and that **`TASKRAIL_BIN` is deliberately left alone**, since it delegates to a binary of the
  caller's choosing.
- **T119** (`bug`, 1pt, E05) — *Warn from `done`, as `claim` does, when the checked-out branch is
  not the task's.*

§9 now describes the wrapper's behaviour before T118 implements it. That is deliberate and was
approved at this gate: `DESIGN.md` is the design, and §12 and §13 already mark what is implemented
where the distinction matters.

## What would change the decision

- **If an existing consuming repository deliberately runs one checkout's wrapper against another
  repository without `--root`**, 1A is a breaking change for it and needs a release note at least;
  the decision would become 1A plus an explicit note in `CHANGELOG.md`, or 1B. Nothing in this
  repository does it, and E5/L2 shows such a caller is already getting the wrong pinned version.
- **If `--root`'s last-wins behaviour were to change** — for example if `--root` were ever made
  `action="append"` or moved to the subcommands — the escape hatch in P3 disappears and 1A would
  need its own opt-out. It is worth a line in the follow-up task's test.
- **If `TASKRAIL_BIN` users expect cwd-targeting**: the recommendation leaves the `TASKRAIL_BIN`
  branch alone, since that path delegates to a binary of the caller's choosing. If the human wants
  it to behave like the others, say so and the follow-up covers four `exec` paths, not three.
- **If E7 turns out to be the common failure rather than E2/E4**, then 2C rises above 1A in
  priority. The evidence here cannot rank them: the three observed lane failures are E2-shaped and
  the one historical incident is E4-shaped.

## How to reproduce

Everything above runs in a throwaway clone; nothing touches a real checkout. With `$SB` an empty
scratch directory and `<repo>` this repository:

```sh
git clone --no-hardlinks --branch main <repo> "$SB/primary"
git -C "$SB/primary" remote remove origin           # so nothing can be pushed
git -C "$SB/primary" worktree add --no-track "$SB/lane" -b lane HEAD

# E4: give the lane branch its own change to a skill SOURCE
printf '\n## LANE-CHANGE-MARKER\n' >> "$SB/lane/src/taskrail/skills/taskrail/SKILL.md"
git -C "$SB/lane" commit -am "lane: marker"
cd "$SB/lane" && "$SB/lane/.taskrail/bin/taskrail" upgrade --force   # correct: marker installed
grep -c LANE-CHANGE-MARKER "$SB/lane/.claude/skills/taskrail/SKILL.md"   # 1
"$SB/primary/.taskrail/bin/taskrail" upgrade --force                # accident: primary's wrapper
grep -c LANE-CHANGE-MARKER "$SB/lane/.claude/skills/taskrail/SKILL.md"   # 0, exit 0, no warning
git -C "$SB/lane" status --short                                    # empty: the evidence is gone

# E2/E3: claim in the lane, then run done from the primary checkout
cd "$SB/lane" && git switch -c T116-pin-a-setup-uv-tag-that-exists-in-the-ge
"$SB/lane/.taskrail/bin/taskrail" claim T116
cd "$SB/primary" && "$SB/lane/.taskrail/bin/taskrail" done T116     # "T116 done", exit 0
grep -o '^| . | T116 |' "$SB/primary/TODO.md"                       # ✅ on main
grep -o '^| . | T116 |' "$SB/lane/TODO.md"                          # ⬜ on the task branch

# E6: the one-line change, as a sandbox-only copy beside each wrapper (so `dirname $0/../..`
# still resolves to that checkout). Only the `local:` exec path is patched here, which is the
# one this repository's pin takes; the real change would patch all three.
sed 's|exec uv run --quiet --project "$root/${pin#local:}" taskrail "$@"|exec uv run --quiet --project "$root/${pin#local:}" taskrail --root "$root" "$@"|' \
  "$SB/primary/.taskrail/bin/taskrail" > "$SB/primary/.taskrail/bin/taskrail-patched"
chmod +x "$SB/primary/.taskrail/bin/taskrail-patched"   # and the same for "$SB/lane"
```

Measured against taskrail `0.4.0.dev0` at `c5d43dc` ("ci(repo): add continuous integration that runs
the test suite (T108) (#49)"), `uv`-managed, on Linux with `/bin/sh`. Not covered: Windows and
non-POSIX shells; a globally installed CLI, which has no checkout to derive a root from and is
unaffected by question 1; and any change to how the autopilot instructs its lanes.
