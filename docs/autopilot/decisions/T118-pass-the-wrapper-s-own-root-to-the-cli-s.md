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
