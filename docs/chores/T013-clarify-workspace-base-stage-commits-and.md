# T013 — Clarify workspace base, stage commits and agent restart in the taskrail skills

Kind: chore · Epic: E01 · Status: implemented

## Goal

Remove the four frictions found while validating the skills (T001) and while opening T015,
before `v0.1.0` is tagged:

- **F1** — skills installed or changed during a running agent session are not loaded by it.
- **F2** — the workspace step does not say which base to branch from when the local mainline and
  its remote-tracking branch differ.
- **F3** — a stage's `commit = false` does not say whether a commit is forbidden or merely not
  required; the spike's `frame` draft sits uncommitted while it waits at its gate.
- **F5** — there is no way to create a task and start it without committing the new row to the
  mainline. T015 worked around it by creating the task in a throwaway worktree and moving it,
  which broke that worktree's virtual environment (uv scripts record absolute paths).

## Change set

All paths are relative to the repository root unless stated.

| File | Change |
|---|---|
| `src/taskrail/review.py` | Nothing new; `choose_base` is reused below. |
| `src/taskrail/query.py` | `task_dict` gains `base`: `{onto, diverged, reason}` from `review.choose_base` on `[review].remote` and the backlog's mainline. Read-only — it never fetches. (F2) |
| `src/taskrail/cli.py` | `show` prints the base line. `new` gains `--workspace`: after writing nothing to the current checkout, it creates the task's workspace — a worktree at `worktree`, or a branch in this checkout when `git.worktree = "never"` — from `base.onto`, then writes the new row inside that workspace, uncommitted, and returns `workspace` and `branch`. It refuses (exit 5) when the bases have diverged or the branch already exists. (F5) |
| `src/taskrail/writer.py` | `Edits` accepts a different root, so the row is validated and written in the new workspace. (F5) |
| `src/taskrail/install.py` | When `init` or `upgrade` creates, updates or removes any skill file, the report adds a note: restart the agent session so it loads the changed skills. (F1) |
| `src/taskrail/kinds/spike/kind.toml` | `frame` gets `commit = true`. (F3) |
| `src/taskrail/skills/taskrail/SKILL.md` | Step 3: run `git fetch <remote>`, then branch from `base.onto` — the further-ahead of the local and remote mainline, the same rule `review` uses — and stop and ask when `base.diverged` is true. Step 5: `commit = false` means a commit is not required at that point, not that one is forbidden. *Creating tasks*: to open a task and start it right away, use `taskrail new … --workspace`, then commit the row inside that workspace and claim it. (F2, F3, F5) |
| `src/taskrail/skills/taskrail-spike/SKILL.md` | `frame`: commit the draft. (F3) |
| `DESIGN.md` | §5 stage `commit` semantics; §7 `new --workspace` and `show`'s `base`; §9 the restart note. |
| `README.md` | Install section: restart the agent after `init` or `upgrade`. `new --workspace` in the Use block. (F1, F5) |
| `tests/` | Tests for `base` in `show`, `new --workspace` in both worktree modes, its refusals, the restart note, and the spike's `frame` commit. |
| Repository root | `.claude/skills/` refreshed with `taskrail upgrade`; `docs/chores/README.md` index row. |

## Decisions needed

1. **Base rule for new workspaces.** T001 proposed "always the local mainline". Since T015,
   `review` rebases onto whichever of the local and remote mainline is further ahead. Using the
   same rule when branching keeps start and end consistent, and avoids branching from a stale
   local mainline. Recommended: the further-ahead rule.
2. **`new --workspace` inside this chore.** It is new CLI behaviour, roughly a small feature.
   Keeping it here fixes F5 before the release; splitting it into its own `feature` task keeps
   this chore to wording changes, and the release would ship with F5 documented as a known gap.
   Recommended: keep it here — it is the fix T013's description already names.

## Decisions at the scope gate

- New workspaces branch from the further-ahead of the local and remote mainline, the same rule
  `review` uses.
- `new --workspace` stays in this chore.
- The change set is approved as written.

## Out of scope

- `taskrail edit` (T014) and the merge driver (T004).
- Running `git fetch` from `show` or `new`: fetching stays an explicit step, so read-only
  commands never touch the network.
- Rebuilding a moved worktree's virtual environment: `--workspace` removes the reason to move
  one.

## Verification

- `uv run pytest -q`, including the new tests.
- In this repository, through the wrapper: `taskrail show T013 --json` reports `base`;
  `taskrail new --workspace` against a throwaway epic in a scratch clone creates the worktree,
  writes the row there, leaves the main checkout untouched, and `claim` works from inside it;
  `taskrail upgrade` prints the restart note.

### Results

Automated: `uv run pytest -q` → 150 passed (13 new, in
`tests/test_workspace.py` and `tests/test_install.py`). The stage's `lint` check is not
configured in this repository.

Exercised for real:

- `taskrail show T013` in this repository printed `base origin/main (origin/main is up to date
  with or ahead of main)`.
- `taskrail upgrade` updated the core and spike skills and printed `note skills changed: restart
  the agent session so it loads them`.
- In a scratch clone of this repository, with the wrapper pointed at this branch's build,
  `taskrail new --epic E01 --kind chore --title "Probe the workspace flag" --workspace` created
  `.worktrees/T016-probe-the-workspace-flag` from `origin/main`, wrote the row there, left the
  main checkout on `main` with no changes, and `claim T016` then `validate` succeeded inside the
  new worktree.

Differences from the approved change set:

- `writer.py` did not need to change: the new workspace gets a copy of the configuration with
  its own root, which `Edits` already honours.
- Two small fixes on the way, found by the new tests: a failed `new --workspace` released its ID
  reservation through the configuration of the worktree it had just removed, and git reported
  that missing directory as "git is not installed". The reservation now uses the original
  configuration, and a missing working directory is reported as such.
- `show` returns `base: null` outside a git repository instead of a misleading reason.
