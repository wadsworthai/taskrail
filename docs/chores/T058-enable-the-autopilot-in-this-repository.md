# T058 — Enable the autopilot in this repository

## Goal

Let an agent session run `taskrail autopilot` on this repository's backlog. Until now
`.taskrail/config.toml` had no `[autopilot]` table, so `autopilot start` refused with exit 5 and the
`taskrail-autopilot` skill stopped, although the skill and the CLI are installed.

## Change set

- `.taskrail/config.toml` — add an `[autopilot]` table:
  - `enabled = true`;
  - `max_lanes = 3`, the default, stated so the limit is visible;
  - `governing = ["CLAUDE.md", "DESIGN.md"]`, the documents the orchestrator reads
    first to answer gates; `autopilot status` flags a lane that touches them, so a change to either
    reaches the human;
  - `escalate_gates = ["spike:decide"]`, so a spike's decision always goes to the human.
- This artifact and its row in `docs/chores/README.md`.

## Decisions needed

Approved by the human before implementation: enable the autopilot with exactly the table above.

## Out of scope

- Groups, resources and `notify`: no task here needs a shared service or an exclusive area yet.
- The merge driver for this clone and the agent's command allowlist.
- CLAUDE.md: it already points agents at the taskrail skills, and the autopilot skill says when it
  may run.

## Verification

- `taskrail validate` loads the new table without errors.
- In a throwaway clone of the task branch, outside this repository, `taskrail autopilot start
  --count 1 --json` exits 0 and creates a run, where before the change it exited 5. The clone keeps
  the run state away from this repository's git directory.
- The `test` check (`uv run pytest -q`) passes; `lint` is not configured.

Results:

- `taskrail validate`: `56 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- Throwaway clone of `main` before the change: `autopilot start --count 1 --json` exited 5 with
  `the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow
  \`autopilot start\``.
- Throwaway clone with the change applied: `autopilot start --count 1 --json` exited 0 and wrote a
  run file under that clone's `.git/taskrail/runs/`; `autopilot next --run <run> --json` exited 0
  and dispatched one pending task. The clone was deleted afterwards.
- `test`: `828 passed in 95.04s`.
