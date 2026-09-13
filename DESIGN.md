# taskrail — design

Status: **v1 in progress**. Implemented so far: configuration, backlog parsing, kind
resolution, `validate`, `list`, `show`, `next` and `kind list`.

An agent-agnostic backlog tool: a deterministic CLI that owns the backlog files, plus thin
skills that execute tasks by kind. Derived from the task systems of two existing projects,
generalized, and decoupled from GitHub Spec Kit.

## 1. Goals and non-goals

Goals:

- One backlog format, validated by a program instead of interpreted by a model.
- Tasks grouped by epics; `TODO.md` is the main file, and any epic can move to its own file.
- Several backlogs per repository (for example a template backlog and a product backlog), each
  with its own ID prefix, mainline and allowed dependency direction.
- Task kinds as data. The core ships `bug`, `chore`, `feature` and `spike`; a consuming
  repository adds its own kinds — such as a `spec` kind that drives its Spec Kit skills —
  without editing the core.
- A persisted claim, so two agents cannot take the same task, and ID allocation without races.
- Usable by any agent that can run a shell command. Claude Code is the first integration.

Non-goals for v1:

- The autopilot orchestrator (parallel lanes answering gates on the human's behalf). Phase 2.
- Importing the source projects' existing backlogs. Phase 2.
- Any Spec Kit integration in the core. A `spec` kind is an extension, shipped as an example.
- Pushing, merging or opening pull requests. Handoff stops at a local branch plus a report,
  unless a repository enables pushing its own task branch.

## 2. Concepts

| Concept | Meaning |
|---|---|
| Backlog | A named task list with an ID prefix, a main file, a mainline branch and an artifacts root. |
| Epic | A group of tasks with an objective and a "Done when" criterion. Its status is computed. |
| Task | One table row: status, ID, kind, dependencies, title, short description. |
| Kind | A task type, defined by a descriptor: routing, stages, gates, artifact, branch pattern. |
| Stage | A step of a kind's workflow, with optional commit point. |
| Gate | A stop for human approval: `always`, or `conditional` (only when it has content). |
| Artifact | The durable document a kind must produce, e.g. a root-cause write-up for a bug. |
| Claim | An exclusive, persisted reservation of a task by one agent session. |

## 3. File format

### 3.1 Main file

```markdown
# TODO

## Epics

| ID  | Epic    | Objective                          | File                |
|-----|---------|------------------------------------|---------------------|
| E01 | Billing | Charge accurately per session      | —                   |
| E02 | Auth    | Sign-in without passwords          | todo/E02-auth.md    |

## E01 — Billing

Done when: every session has a recomputable cost.

| ✓  | ID   | Kind    | Pts | Depends On | Title                 | Description                        |
|----|------|---------|-----|------------|-----------------------|------------------------------------|
| ⬜ | T008 | feature | 3   | T007       | Retroactive repricing | Recompute cost after price change. |
| ✅ | T007 | chore   | 2   | —          | Versioned price table | [detail](todo/details/T007.md)     |
```

- An epic lives either inline, as a `## E## — Name` section, or in the file its `File` cell
  names. The file holds exactly the same section. `taskrail epic split E01` moves it.
- Completed and discarded tasks stay in their epic's table. There are no separate
  "Completed" or "Discarded" sections, so an epic never appears twice.
- Epic status (`open`, `done`) is computed from its tasks and never stored.

### 3.2 Columns

Required: `✓`, `ID`, `Kind`, `Depends On`, `Title`. Column order is free — the header row
defines it — and names match case-insensitively.
Optional core columns: `Pts`, `Description`.
Custom columns are declared per backlog in config (for example `Owner` or `Spec`). Kinds may
route on them; the core never interprets them.

### 3.3 Values

- `✓`: `⬜` pending, `✅` done, `❌` discarded. Nothing else is stored. "Blocked" is computed
  from dependencies; "in progress" is the claim (§6) and never touches the file.
- `ID`: backlog prefix + zero-padded number, allocated by the CLI (§6.3), never reused.
- `Kind`: must name a known kind. Empty or unknown is a validation error, never a default.
- `Pts`: optional; a backlog may restrict the scale (for example Fibonacci).
- `Depends On`: comma-separated IDs or `—`, checked against the backlog's allowed directions.
- `Description`: one or two lines. Longer detail goes in a linked file, so rows stay short
  and merge conflicts stay small.

## 4. Configuration — `.taskrail/config.toml`

```toml
version = "v0.1.0"          # CLI version the repository is pinned to

[[backlog]]
name = "template"
prefix = "T"
file = "TODO.md"
mainline = "main"
artifacts = "docs"
may_depend_on = []               # T tasks may depend only on T tasks

[[backlog]]
name = "product"
prefix = "A"
file = "APP_TODO.md"
mainline = "dev"
artifacts = "docs"
may_depend_on = ["template"]     # A may depend on T; never the reverse

[columns]
custom = ["Owner"]

[points]
scale = [1, 2, 3, 5, 8, 13]

[git]
push_task_branch = false
claim_remote = ""                # e.g. "origin" to also claim across machines (§6.2)

[checks]                         # commands the executors run as quality gates
test = "pnpm test:all"
lint = "pnpm lint"
```

## 5. Kinds

### 5.1 Descriptor — `types/<kind>/kind.toml`

```toml
name = "bug"
summary = "Reproduce, find the root cause, fix under a regression test observed failing."
skill = "taskrail-bug"               # the executor skill for this kind
branch = "{id}-{slug}"
artifact = "{artifacts}/bugs/{id}-{slug}.md"
artifact_index = "{artifacts}/bugs/README.md"
may_edit = ["code", "tests", "artifact"]
never_edit = ["specs"]           # a needed spec change becomes a follow-up task

[[stage]]
name = "diagnose"
gate = "always"                  # human confirms the diagnosis
commit = true

[[stage]]
name = "fix"
gate = "always"                  # code review
commit = true
checks = ["test", "lint"]

[[stage]]
name = "impact"
gate = "conditional"             # only if follow-up tasks were opened
```

Routing on a column, used by a repository-local `spec` kind:

```toml
name = "spec"
[[route]]
when = { Spec = "—" }
skill = "speckit-new-spec-pipeline"
[[route]]
when = { Spec = "*" }
skill = "speckit-amend-pipeline"
```

### 5.2 Resolution order

Highest wins, as in Spec Kit's layering:

1. `.taskrail/overrides/<kind>/` — one-off adjustments to a core or local kind
2. `.taskrail/types/<kind>/` — the repository's own kinds
3. core kinds shipped with the tool

### 5.3 Core kinds

| Kind | Stages (gate) | Artifact |
|---|---|---|
| `bug` | diagnose (always) → fix, regression test observed failing first (always) → impact (conditional) | root-cause write-up |
| `chore` | scope, no edits (always) → implement and verify (always) → docs sync (conditional) | approved change set |
| `feature` | plan (always) → implement (always) → verify (conditional) | short plan |
| `spike` | question and approach (always) → investigate → decision (always) | evaluation with a decision |

Shared by every kind, and written once in the core skill rather than copied per kind: one
worktree and branch per task, commit points, "reject a kind that is not yours and name the
right one", the gate protocol, rebase onto the mainline the branch came from, marking the
task done, and the handoff report.

## 6. Claims and IDs

### 6.1 Local claim — always on

A claim is a file created atomically (`O_EXCL`) under the git common directory:
`$(git rev-parse --git-common-dir)/taskrail/claims/<ID>.json`, holding owner, branch, host,
process and timestamp. Every worktree of a clone shares that directory, so parallel sessions
on one machine see each other's claims without any network.

`taskrail claim <ID>` fails if another live claim exists. `taskrail release <ID>` removes it. A claim
whose owner process is gone is reported as stale and can be taken over explicitly.

### 6.2 Remote claim — optional

With `claim_remote` set, a claim is also pushed as `refs/taskrail/claims/<ID>` with a lease, so
claims are visible across machines. Off by default: it needs network and permission to push.

### 6.3 ID allocation

`taskrail new` reserves the next ID under a lock in the same common directory. The next number is
one above the maximum of: IDs in the backlog file on every local branch, IDs reserved but not
yet committed, and — with a remote configured — IDs on remote branches. This replaces
"highest plus one", which two agents can compute identically.

## 7. CLI

| Command | Purpose |
|---|---|
| `taskrail init [--integration claude]` | Create `TODO.md`, `.taskrail/config.toml`, and install skills for an agent |
| `taskrail integration list` | Available agent integrations |
| `taskrail validate` | Check every rule in §3 and §4; non-zero exit on any error. For CI and hooks |
| `taskrail list [--epic E01] [--eligible]` | Tasks, with computed blocked and eligible state |
| `taskrail show <ID>` | One task, its kind's resolved stages, and its claim |
| `taskrail next` | Eligible tasks in order: points ascending, then file order |
| `taskrail claim <ID>` / `taskrail release <ID>` | §6 |
| `taskrail new --epic E01 --kind bug --title …` | Allocate an ID and append a row |
| `taskrail done <ID>` / `taskrail discard <ID>` | Change status; refuses without a claim |
| `taskrail epic add` / `taskrail epic split <E##>` | Manage epics; move one to its own file |
| `taskrail kind list` / `taskrail kind add <dir>` | Inspect resolved kinds; install a local kind |
| `taskrail upgrade` / `taskrail self upgrade` | Re-sync installed skills without touching overrides; update the CLI |

Output is human-readable by default and JSON with `--json`, so skills parse results rather
than prose. Exit codes are stable and documented.

## 8. Skills

- `taskrail` — the core skill: what the backlog is, how to call the CLI, and the shared stages
  from §5.3. Executor skills refer to it instead of repeating it.
- `taskrail-bug`, `taskrail-chore`, `taskrail-feature`, `taskrail-spike` — one per core kind, containing only
  what differs.

Agent neutrality: skills describe gates as "stop and return the questions to whoever invoked
you". How that maps to a harness — a subagent in an isolated worktree relaying through an
orchestrator on Claude Code — lives in the integration layer, not in the skill text.

## 9. Distribution

Modeled on Spec Kit: a CLI installed with uv, which writes files into the consuming
repository.

```bash
uv tool install taskrail --from "git+https://github.com/alexkander/taskrail.git@v0.1.0"
taskrail init --integration claude
```

Tags are the plain version, `vX.Y.Z`.

Unlike Spec Kit, the skills call the CLI while they work. `init` therefore also writes a
committed wrapper, `.taskrail/bin/taskrail`: it runs the installed CLI when its version matches
`.taskrail/config.toml`, and otherwise runs the pinned version through `uvx`. The only
prerequisite on any machine, CI runner or agent sandbox is `uv`.

## 10. Layout

```
taskrail/
├── DESIGN.md
├── README.md
├── pyproject.toml
├── src/taskrail/          # parser, validator, claims, CLI
│   └── kinds/             # core kind descriptors, shipped as package data
├── skills/                # taskrail, taskrail-bug, taskrail-chore, taskrail-feature, taskrail-spike
├── integrations/claude/   # agent-specific install mapping
├── examples/spec-kit/     # example repository-local `spec` kind
└── tests/
```

## 11. Phases

1. **v1** — format, config, `validate`, `list`/`next`/`show`, local and remote claims, ID
   allocation, epics, kind resolution, core kinds and skills, the Claude integration, `init`
   and the wrapper.
2. **v2** — autopilot orchestrator, import from existing backlogs, a git merge driver that
   resolves `✓` cell conflicts.
