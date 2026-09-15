# T060 — Remove DESIGN.md and CLAUDE.md from the autopilot's governing paths

## Goal

`[autopilot].governing` in `.taskrail/config.toml` listed `CLAUDE.md` and
`DESIGN.md`. The key has two roles (DESIGN.md §12.6 and the `taskrail-autopilot`
skill): the documents the orchestrator reads first to answer gates, and paths whose change
escalates to the human. In the T033 trial the `governing` flag also stayed on after the human had
approved the edit (F9). The human decided that edits to both documents are decided by the
orchestrator at the gate and reviewed by the human in the pull request, permanently.

This chore empties `governing` in this repository's config and keeps both documents named as what
the orchestrator reads first.

## Change set

Approved at the scope gate, with changes: no repository-level test file and no *Commands* line
(decision record: `docs/autopilot/decisions/T060-remove-design-md-and-claude-md-from-the.md`).

- `.taskrail/config.toml` — `governing = []`, with a comment saying why it is empty and where the
  read-first documents are named:

  ```toml
  # Nothing escalates by path: the orchestrator decides lane edits to CLAUDE.md and
  # DESIGN.md at the gate and the human reviews them in the pull request.
  # The orchestrator still reads both first; CLAUDE.md (Backlog) names them.
  governing = []
  ```

- `CLAUDE.md` — one bullet at the end of the *Backlog* section, the place every agent working on
  this repository reads, whatever the agent:

  ```markdown
  - The autopilot is enabled here (`[autopilot]` in `.taskrail/config.toml`). Its orchestrator
    answers lane gates from this file and `DESIGN.md` first. Neither is a
    `governing` path: a lane may change them when its task needs it, the orchestrator decides that
    change at the gate, and the human reviews it in the pull request.
  ```

- `TODO.md` — T060's description now says it is verified by `taskrail validate` and
  `autopilot status` loading the empty key, instead of promising a pytest; and a follow-up row,
  T061 (below).
- This artifact and its row in `docs/chores/README.md`.

## Decisions needed

Decided at the scope gate:

1. The read-first role is kept by the `CLAUDE.md` *Backlog* bullet plus the comment on the empty
   key. `CLAUDE.md` is loaded by Claude Code and read by OpenCode, so the orchestrator sees both
   documents named without relying on the skill's pointer to the key.
2. No new test file. The change is verified by `taskrail validate` and `taskrail autopilot status
   --json` loading the empty key. A test under `tests` reading this repository's
   config was rejected: items must stay self-contained.
3. Follow-up opened: T061 (feature, E02), *Separate the documents the orchestrator reads first
   from the paths that escalate* — a key for the read-first documents that the skill reads,
   leaving `governing` for escalation only, verified by pytest.

## Out of scope

- Any taskrail file (code, DESIGN.md, CHANGELOG, the autopilot skill sources) and
  the installed copies under `.claude/skills/`: the default `governing = []` already exists, and
  lanes of run 20260914-1 are editing those files.
- The `escalate_gates`, `max_lanes` and `enabled` values, which stay as T058 set them.
- The T058 artifact, which records what was decided then.
- F9 itself (the lasting `governing` flag), which T049 fixes; T061 separates the two roles.

## Verification

All commands run with the worktree as `--root` (`<worktree>` below).

- Before the change, `taskrail --root <worktree> autopilot status --json`, reduced to each task's
  `id`, `state`, `governing_touched`, `escalate_gate` and `escalation` for run `20260914-1`:

  ```
  T049 done-branch  governing_touched ["DESIGN.md"]  escalate_gate null  escalation ["governing"]
  T050 done-merged  governing_touched []                            escalate_gate null  escalation []
  T053 done-branch  governing_touched ["DESIGN.md"]  escalate_gate null  escalation ["governing"]
  T054 running      governing_touched []                            escalate_gate null  escalation []
  T056 running      governing_touched []                            escalate_gate null  escalation []
  T048 running      governing_touched []                            escalate_gate null  escalation []
  ```

- After the change, the same command exits 0 and reports:

  ```
  T049 done-branch  governing_touched []  escalate_gate null  escalation []
  T050 done-merged  governing_touched []  escalate_gate null  escalation []
  T053 done-branch  governing_touched []  escalate_gate null  escalation []
  T054 running      governing_touched []  escalate_gate null  escalation []
  T056 running      governing_touched []  escalate_gate null  escalation []
  T048 running      governing_touched []  escalate_gate null  escalation []
  ```

  T049 and T053 still list `DESIGN.md` in `touched` after the change, so the flag
  disappears because of the empty key, not because the lanes stopped touching the file.
- `taskrail --root <worktree> validate`: `58 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`,
  exit 0.
- `test` (`uv run pytest -q`): `828 passed in 86.82s`. `lint` is not
  configured.
