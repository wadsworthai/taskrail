# T118 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane. The change itself was decided by the human at
T115's `decide` gate, which `escalate_gates` sends to them; these decisions are about how it is
built, not whether.

## diagnose gate

Reviewed: the artifact `docs/bugs/T118-pass-the-wrapper-s-own-root-to-the-cli-s.md` and its commit
`1c8adb9` (artifact and index row alone); the six reproductions, run in a sandbox of two independent
repositories rather than against this repository's worktrees; and the digest check showing this
repository's committed wrapper is unedited.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | How the regression test builds a two-checkout situation | **two repositories under `tmp_path`, driven over the installed-CLI `exec` path with a shim on PATH** · the `local:` path, as the existing wrapper test does · both | **as recommended** | It reproduces the defect (E2), needs neither `uv` nor the network, and cannot flake. The `local:` path costs a `uv run` per invocation and a skip; running both buys nothing, since the injected `--root` is one identical line per branch and decision 3 covers the rest. |
| 2 | How "last `--root` wins" is pinned | **behaviourally: the caller's `--root` beats the injected one** · assert on the parser's action or on the wrapper's text | **behaviourally** | That is the escape hatch as a caller experiences it, and it keeps holding whatever argparse does. Saying in a comment that plain `store` on a global flag is what makes it work is right; asserting on it would pass even if the flag stopped being last-wins for a caller. |
| 3 | Cover for the `uvx` and `TASKRAIL_BIN` lines | **one structural assertion: every `exec … taskrail` line but the `TASKRAIL_BIN` one carries `--root "$root"`** · leave them to review | **the structural assertion** | `uvx` cannot be exercised without the network, and "all three paths" is what the human decided, so something has to hold it. It also pins the `TASKRAIL_BIN` exclusion as deliberate rather than forgotten — which is the part a later reader would otherwise have to guess at. An assertion on generated text is normally the weaker kind; here it is the only kind available, and the behavioural test carries the meaning. |
| 4 | Regenerating this repository's `.taskrail/bin/taskrail` | **yes, with this worktree's own wrapper, and grep the result** · leave it stale | **regenerate** | Otherwise this repository ships a wrapper that does not match its own source, and the next lane in this run is the one who trips over it. Use the worktree's own wrapper from inside the worktree: a lane earlier in this run used the primary checkout's and silently lost its change. It also rewrites the wrapper's digest in `.taskrail/installed.json`, which T117 touches — a known conflict class, resolved at hand-off. |
| 5 | A `CHANGELOG.md` bullet | **yes, in the shape T116's uses** · none | **yes** | The wrapper is a committed managed file in every consuming repository, so this is user-visible at their next `upgrade`. Say what an untouched one does, what an edited one reports, and the one behaviour that changes for a caller — a wrapper deliberately aimed at another repository without `--root` now acts on its own checkout. T115's *What would change the decision* asks for exactly that note. |

Given with the answers: removing `(*planned, T118*)` from `DESIGN.md` §9 is part of this task. Once
the code does it, the sentence is no longer planned, and leaving the marker would be the same class
of inaccuracy the marker was added to prevent.

## fix gate

Reviewed: commit `7ec554c` and the diff `cf2b1fa..HEAD`; the regression tests' recorded failure,
where the behavioural one fails as `['elsewhere'] == ['home']` — the defect itself, the wrapper
reporting the backlog of the directory the shell was in; the structural one's failure naming the
three `exec` lines; `taskrail checks T118 --stage fix` (1,250 passed); and, checked by the
orchestrator rather than taken from the report, `grep -c 'root "$root"'` returning **3** in this
worktree's regenerated wrapper and `grep -c "planned, T118"` returning **0** in `DESIGN.md`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The header comment in the generated wrapper, extended beyond the three `exec` lines | **keep it** · drop it | **keep it** | That file is what a consuming repository reads, and its comment described a behaviour that is now different. Leaving it would ship a wrapper whose own header contradicts what it does — the same class of inaccuracy as the `(*planned, T118*)` marker this task removes. It is inseparable from the change, not a widening of it. |
| 2 | The second behavioural assertion, run from `cwd=home` | **accept** | **accept** | It is non-trivial in both worlds: before the fix the caller's `--root` beats the cwd, after it beats the injected root. An assertion that only meant something after the fix would not have proved the escape hatch survived. |
| 3 | The structural test's four-`exec` shape | **accept** | **accept** | Asserting that exactly one line — the `TASKRAIL_BIN` one — carries no `--root "$root"` pins both halves: the three paths cannot drift, and the exclusion is on record as deliberate. Its docstring saying it is the weaker kind, with the behavioural test carrying the meaning, is what keeps it honest. |

## close

Reviewed: the whole diff against the merge base — `wrapper_script()`'s three `exec` lines and its
header comment, two regression tests, `DESIGN.md` §9's removed marker, one changelog bullet, the
regenerated wrapper and its digest, the artifact and its index row; the `impact` sweep; and
`taskrail validate` (108 tasks, 0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `impact` stage opened nothing | **accept** | **accept** | It was a real sweep of the places the injected root reaches, not an assertion that there are none: the generated workflow's `validate`, the pre-commit hook and the merge driver all invoke the wrapper by a relative path from the checkout's own root, so the injected root is the one they were resolving anyway. The lane also checked the skills for wording the fix would falsify and found none — the cwd discipline still matters for the case no root rule can catch, which is T119's. |
| 2 | Pull request type and scope | **`fix` / `install`** | **`fix` / `install`** | The change is in `src/taskrail/install.py`'s wrapper template. |
| 3 | The lane's note on resolving a `.taskrail/installed.json` digest conflict | **adopt it** | **adopt it** | A digest conflict is not a textual merge: take either side and re-run the rebased worktree's own wrapper with `upgrade`, which rewrites the wrapper and its recorded digest consistently. That is the known conflict class 3 procedure, stated precisely for this case. |

## rebase after T003 and T117 merged

`main` advanced to `6f4037e` (T117). This branch was rebased onto `origin/main`, with two conflicts.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2. |
| 2 | Conflict in `.taskrail/installed.json` — T117 added the generated workflow's hash on the mainline while this branch changed the wrapper's | **take either side, then regenerate with the worktree's own wrapper** · merge the JSON by hand | **regenerate**, as the lane's own note prescribed | A digest conflict is not a textual merge: a hand-merged hash would be a number nobody computed. Known conflict class 3. Taken with `--ours`, then `<worktree>/.taskrail/bin/taskrail --root <worktree> upgrade` from inside the rebased worktree, which rewrites the manifest consistently. |

Verified after the regeneration: the manifest now carries **both** T117's
`.github/workflows/taskrail.yml` hash and this branch's new `.taskrail/bin/taskrail` hash
(`f2af3ecc…`), and that hash equals the `sha256sum` of the wrapper on disk. The wrapper in this
worktree has all three `--root "$root"` lines; the primary checkout's still has none, so nothing
leaked across checkouts.
