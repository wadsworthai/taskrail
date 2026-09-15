# taskrail — design

Status: **v1 released as `v0.1.0`.** See CHANGELOG.md.

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

- The autopilot orchestrator (parallel lanes answering gates on the human's behalf). Phase 2;
  its planned design is §12, not yet implemented.
- Importing the source projects' existing backlogs. Phase 2; `taskrail import` (§7.3) now
  converts table-based backlogs.
- Any Spec Kit integration in the core. A `spec` kind is an extension, shipped as an example.
- Merging, or creating pull requests through a host's API. Hand-off ends with a pushed branch and
  a link that opens the pull request with its title filled in (§7.1).

## 2. Concepts

| Concept | Meaning |
|---|---|
| Backlog | A named task list with an ID prefix, a main file, a mainline branch and an artifacts root. |
| Epic | A group of tasks with an objective and a "Done when" criterion. Its status is computed. |
| Task | One table row: status, ID, kind, dependencies, title, short description. |
| Kind | A task type, defined by a descriptor: routing, stages, gates, artifact, branch pattern. |
| Stage | A step of a kind's workflow. `commit = true` requires a commit at its end; `false` means none is required, not that one is forbidden. |
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

A repository with established headers maps them onto the core columns in `[columns].aliases`
instead of renaming them — for example `Pts = "Size"`. Each key is a core column, each value
the header that repository uses; both match case-insensitively. The alias replaces the name:
every command reads and writes the column by its alias, a task table that still uses the core
name of an aliased column fails validation (`column-alias`), and a missing required column is
reported by both names. `--json` output keeps the core field names, and `new` fills an aliased
column through its usual flag (`--pts`). `new --column` and `edit --column` are for custom columns only: they refuse
every core column, by core name or alias and in any letter case, naming the flag that fills it
(`ID` and `✓` are set by taskrail). A custom column named by `edit --column` matches the header in any letter case. Config is refused when a
key is not a core column, an alias is empty or contains `|`, an alias is another core column's
name or a custom column, or two columns share an alias. Aliases apply to task tables only, not
to the `## Epics` table.

### 3.3 Values

- `✓`: `⬜` pending, `✅` done, `❌` discarded. Nothing else is stored. "Blocked" is computed
  from dependencies; "in progress" is the claim (§6) and never touches the file.
- `ID`: backlog prefix + zero-padded number, allocated by the CLI (§6.3), never reused.
- `Kind`: must name a known kind. Empty or unknown is a validation error, never a default. When
  config restricts the allowed kinds (§5.2), a kind outside that set is an error too.
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
aliases = { Pts = "Size" }       # core column -> this repository's header (§3.2)

[points]
scale = [1, 2, 3, 5, 8, 13]

[git]
push_task_branch = true
claim_remote = ""                # e.g. "origin" to also claim across machines (§6.2)
branch_record_remote = ""        # e.g. "origin" to share task branch records across clones (§6.4)
claim_grace_minutes = 15         # how long a claim's branch may be missing before it is stale
worktree = "required"            # "required": one worktree per task; "never": a branch in this checkout
worktree_dir = ".worktrees"

[review]                         # hand-off after closing (§7.1)
remote = "origin"                # for a mainline without branch.<mainline>.remote (§7.1)
fetch = true
rebase = true
provider = "auto"                # auto | github | gitlab | gitea | forgejo | none
web_url = ""
url_template = ""
scope = ""

[kinds]                          # optional; omit to allow every defined kind (§5.2)
allowed = ["spec", "bug", "chore"]

[checks]                         # commands the executors run as quality gates
test = "pnpm test:all"
lint = "pnpm lint"

[autopilot]                      # §12; every key is optional
enabled = false                  # allow `autopilot start`; the skill is installed regardless
max_lanes = 3                    # lanes in use at once, across every run of the clone (§12.7)
kinds = []                       # kinds a run drives; empty means every allowed kind
governing = []                   # read first to answer gates; flagged by `status` from T032
escalate_gates = []              # "kind:stage" always taken to the human; flagged from T032
decisions = "{artifacts}/autopilot/decisions/{id}-{slug}.md"
decisions_index = "{artifacts}/autopilot/decisions/README.md"
silent_minutes = 20              # a running lane idle longer is `silent` in `autopilot status`
handoff = "sequential"           # the only value
notify = ""                      # command run by `autopilot notify` (T032)
notify_on = ["escalation", "lane-done"]   # any of escalation, lane-done, lane-failed

[[autopilot.group]]              # §12.7; at most `limit` lanes at once from this group
name = "ui"
limit = 1
column = "Area"                  # a column predicate (§5.4); omit both for a judgement group
match = ["ui"]

[[autopilot.resource]]           # §12.7; one value per lane, as TASKRAIL_RESOURCE_PORT
name = "PORT"
values = ["5433", "5434"]
```

`[autopilot]` is checked when the config loads: a value of the wrong type, `max_lanes` below 1, a
negative `silent_minutes`, a `kinds` entry that is not a kind name, an `escalate_gates` entry not
shaped `kind:stage`, an unknown `notify_on` event or a `decisions` template with an unknown
placeholder exits 2. So does a malformed `[[autopilot.group]]` — a missing, duplicate or malformed
`name` (lowercase letters, digits and dashes), a `limit` that is not an integer of at least 1, or a
column predicate that §5.4 would refuse, including a column `[columns].custom` does not declare —
and a malformed `[[autopilot.resource]]`: a missing, duplicate or malformed `name` (uppercase
letters, digits and underscores, starting with a letter), or `values` that are not a non-empty
list of unique non-empty strings. Every message names the table entry and the key.

## 5. Kinds

### 5.1 Descriptor — `types/<kind>/kind.toml`

```toml
name = "bug"
summary = "Reproduce, find the root cause, fix under a regression test observed failing."
skill = "taskrail-bug"               # the executor skill for this kind
branch = "{id}-{slug}"
commit_type = "fix"                  # Conventional Commits type of the pull request title
artifact = "{artifacts}/bugs/{id}-{slug}.md"
artifact_index = "{artifacts}/bugs/README.md"
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

A stage may also apply only to some tasks of its kind (§5.4).

Routing on a column, used by a repository-local `spec` kind (§5.5):

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

A repository whose rules name a closed set of kinds lists it in `[kinds].allowed`. The allowlist
is applied after resolution, so it covers core, local and overridden kinds alike: a kind it
leaves out is not resolved at all, and `validate` reports:

- `task-kind-disallowed` (error) — a task, whatever its status, whose kind is defined but not
  allowed; `task-kind-unknown` stays for a kind no layer defines;
- `kind-allowed-unknown` (error) — `allowed` names a kind no layer defines;
- `kind-not-allowed` (warning) — a local kind or an override that `allowed` leaves out. Leaving
  out a core kind is silent, since that is what the setting is for.

Without `allowed`, every defined kind is allowed. An empty list is a configuration error.

Installation follows the resolved set too (§9): an executor skill taskrail ships installs only
when a resolved kind names it.

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

### 5.4 Conditional stages

Every stage applies to every task of its kind unless it says otherwise, so a repository adds or
drops one stage for some tasks without duplicating the kind:

```toml
[[stage]]
name = "visual-check"
gate = "always"
column = "Area"                  # a column predicate: only tasks whose Area cell matches
match = ["ui", "ux"]

[[stage]]
name = "migration-review"
gate = "always"
judgement = true                 # the executor decides whether the stage is relevant
```

The two combine: with both, the stage is left to the executor's judgement only for tasks the
predicate matches.

**The column predicate** is `column` plus `match`. It is defined once, in `predicates.py`, for
every setting with this shape — the autopilot's groups reuse it (§12.7):

- `column` names a custom column from `[columns].custom`, matched case-insensitively. A core
  column, or a core column's alias (§3.2), is refused: predicates read custom columns only. A
  task table without the column reads as empty.
- `match` is a non-empty list of non-empty strings, or a single string. The predicate holds when
  the cell equals any value.
- Values are trimmed and compare case-insensitively. `"*"` matches any non-empty cell and `"—"`
  (or `"-"`) an empty one. Routes match through the same predicate (§5.5).

`validate` reports a malformed predicate or `judgement` as `kind-invalid`, and a `column` that
`[columns].custom` does not declare as `stage-column-unknown` (error), naming the core column when
it is one or an alias of one. That error keeps the kind loaded, so its tasks are not also reported
as `task-kind-unknown`. Predicates behave the same in every layer (§5.2); an override replaces the
whole descriptor, so a conditional stage is added to a core kind by copying it into
`.taskrail/overrides/`, and errors name the layer file that declares the stage.

`show --json` resolves the predicate for its task: each stage in `kind_descriptor.stages` carries
`column` (or `null`), `match`, `judgement` and `applies` — the predicate's result, `true` for a
stage without one. Both flags are booleans. `kind list --json` has no task, so its stages carry no
`applies`. Text `show` marks a stage `— not applicable (<column>)` or `— executor's judgement`.

The core skill skips a stage whose `applies` is false. When `applies` and `judgement` are both
true, the executor decides; a skipped stage and the reason go into the artifact and the next gate
report, and a stage whose gate is `always` is not skipped without asking. A stage the executor
skill does not describe, such as one an override adds, is done as its `summary` says.

### 5.5 Routes

A `[[route]]` hands tasks of its kind to another executor skill. Its `when` is a table of column
predicates (§5.4): each key is a `column` and each value a `match`, a string or a non-empty list of
strings. A route holds when every entry holds:

```toml
[[route]]
when = { Area = ["ui", "ux"], Spec = "—" }   # Area is ui or ux, and Spec is empty
skill = "new-screen-pipeline"
```

- Columns and values follow §5.4: columns resolve case-insensitively to a declared custom column,
  values are trimmed and compare case-insensitively, `"*"` is any non-empty cell and `"—"` or `"-"`
  an empty one.
- Routes are tried in the order the descriptor lists them. The first that holds gives the task's
  `skill` in `show`; when none holds, the kind's `skill` applies, or `null` for a kind without one.
- `validate` reports a malformed route — `when` that is not a non-empty table, a value that is not
  a non-empty string or a non-empty list of them (`""` included), a column named twice in different
  letter case, or a missing `skill` — as `kind-invalid`. A column `[columns].custom` does not
  declare is `route-column-unknown` (error), naming the route and the core column when it is one or
  an alias of one; like `stage-column-unknown`, it keeps the kind loaded.
- A route that an earlier route of the same kind always pre-empts is `route-unreachable`
  (warning), naming both. It is reported only when certain: every entry of the earlier route must
  cover an entry of the later one on the same column — `"*"` covers any literal, an empty marker
  covers the empty markers, a literal covers itself in any letter case. An earlier route with a
  column the later one does not constrain never makes it unreachable.

`show --json` and `kind list --json` report each route as `{"when": {<column>: <value>}, "skill": …}`,
with the declared column name and the trimmed value: a string for one value, a list for several.

## 6. Claims and IDs

### 6.1 Local claim — always on

A claim is a file created atomically (`O_EXCL`) under the git common directory:
`$(git rev-parse --git-common-dir)/taskrail/claims/<ID>.json`, holding owner, branch, worktree,
host, timestamp, `base` and `run`. Every worktree of a clone shares that directory, so parallel sessions on
one machine see each other's claims without any network.

`base` records where the claimed branch started: `onto`, the ref `show` reports as the base (§7);
`dependency`, the ID of the unmerged dependency it is stacked on, or `null`; and `commit`, the
fork point `git merge-base HEAD <onto>` at claim time. Once that dependency is squash-merged,
`git rebase --onto <mainline> <base.commit>` replays only the task's own commits. `taskrail done`
releases the claim, so for a finished dependent the fork point is also
`git merge-base HEAD <dependency branch>` while that branch exists: follow-through must compute it
before removing the dependency's branch. `base` is
`null` when no base could be determined. `run` is the autopilot run that owns the lane, set with
`claim --run R` (exit 3 when that run does not exist, §12.4), or `null`. A claim file is read ignoring keys this version does not
know, so a later version can add fields without hiding its claims from this one.

`taskrail claim <ID>` fails if another live claim exists, and refuses a task that is not
pending, is `done-branch`, or is blocked (`--ignore-deps` overrides the last). Claiming again with the same
owner and branch is a no-op. A held claim also settles the task's branch name (§6.4): claimed on
the name its template renders and with no record yet, `claim` records that name, so a later hand
edit of the title no longer changes the branch; claimed on any other branch — another name, a
mainline or a detached `HEAD` — it records nothing and warns on stderr, naming `taskrail branch`.
`--json` returns `branch_recorded`, the same `warning` (`null` when there is none) and
`record_remote` (§6.4); the exit code stays 0. `taskrail release <ID>` removes a claim; releasing someone
else's needs `--force`. The owner defaults to `$TASKRAIL_OWNER`, then `user@host`.

A claim is **stale** when its worktree no longer exists, or when its branch does not exist and
the claim is older than `claim_grace_minutes` — the grace lets an agent claim first and create
the branch right after. The age of the claiming process is deliberately not a criterion: the
CLI exits as soon as the claim is written. A stale claim is only ever reported, never removed
automatically; `--takeover` replaces it explicitly, and never replaces a live one.

### 6.2 Remote claim — optional

With `claim_remote` set, a claim is also pushed as `refs/taskrail/claims/<ID>`: a parentless
commit holding `claim.json` with only `id`, `owner`, `branch`, `created`, `base` and `run` — the host and the
worktree path stay in the local claim, since a remote may be public — pushed with `--force-with-lease=<ref>:` so the push fails if the
ref already exists. If the push fails the local claim is rolled back. Releasing deletes the ref
with a lease on the commit that was pushed. `--local-only` skips the remote for one command.

Off by default: it needs network and permission to push, and the server must accept refs
outside `refs/heads` and `refs/tags`. A claim's ref is deleted with the claim, so the branch it names
is lost to other clones once the task is done; `branch_record_remote` mirrors the task's branch
record next to it for that (§6.4).

### 6.3 ID allocation

`taskrail reserve-id` (and `taskrail new`) reserves the next ID under a lock in the
same common directory. The next number is one above the maximum of: IDs in the backlog's files
in the working tree, on every local branch and — with a remote configured — on its
remote-tracking branches, plus IDs reserved but not yet used. A reservation is dropped once
its ID appears in any of those files; `taskrail unreserve-id` cancels one that will not be
used. This replaces "highest plus one", which two agents can compute identically.

Only IDs in the `ID` column of task tables count, so a description that mentions an ID does
not move the counter.

### 6.4 Task branches

A task's branch is its **recorded** branch when one exists, otherwise the name its kind's
`branch` template renders. One resolver answers that for every command — `show`, `list`, `next`,
`new --workspace`, `review`, `done-branch` detection, a dependent's base and prior work — and
nothing else renders the template.

A record is a file next to the claims, `$(git rev-parse --git-common-dir)/taskrail/branches/<ID>.json`,
holding `id`, `branch` and `recorded` (a timestamp). Every worktree of the clone sees it; it is
never committed or pushed, and holds no owner, host or path. Unlike a claim it is not removed by
`done`, `discard`, `release`, `reopen` or deleting the branch, so `review` and a dependent still
find a renamed branch after the claim is gone. Records are written by `claim` (§6.1),
`new --workspace --branch` and `taskrail branch`. Outside git, or without a record, the template
applies. Without mirroring, another clone does not see records, so it resolves a renamed task to its
template name.

**Mirroring records.** With `[git].branch_record_remote` naming a remote (off by default; independent
of `claim_remote`, though both usually name the same remote), records are shared across clones:

- *Ref.* A record is pushed as `refs/taskrail/branches/<ID>`: a parentless commit, authored
  `taskrail <taskrail@localhost>` with the message `taskrail branch <ID>`, whose tree holds only
  `branch.json` with `id`, `branch` and `recorded`. A record holds no owner, host or path, so
  nothing is stripped; opting in does publish branch names, even ones `push_task_branch` never pushes.
- *Push.* Every command that writes a record pushes it: `taskrail branch` (also for the name the
  task already has, which is how a failed push is retried), `claim` when it records the template
  name, and `new --workspace --branch`. The push leases on this clone's copy of the ref
  (`--force-with-lease=<ref>:<copy>`, empty when there is none), and moves the copy to the pushed
  commit. `--local-only` on `claim` and `branch` skips the fetch and the push.
- *Fetch.* One `git fetch --prune --no-tags <remote> +refs/taskrail/branches/*:refs/taskrail/remotes/<remote>/branches/*`
  copies the remote records; the copies sit outside `refs/heads` and `refs/remotes`, so no branch
  listing, `done-branch` detection or prior-work search sees them. It runs at the start of `claim`,
  `branch` and `new --workspace`, in `review` before the task branch is resolved (unless
  `--no-fetch` or `[review].fetch = false`), and in `show`, `list` and `next` only with `--fetch`,
  which does nothing while the setting is off.
- *Disagreement.* After a fetch, a remote record replaces the local file when there is no local
  record or its `recorded` is later, keeping its own timestamp; otherwise the local record stays —
  a change made with `--local-only` or offline, pushed with that task's next record write. Clocks of
  different machines decide, so a clone running behind can lose to an older name; running
  `taskrail branch` again restores it. A fetch never deletes a local record and never renames or
  deletes a git branch.
- *Failures.* A failed fetch warns on stderr and the command goes on with the local records. A
  failed push — offline, a server refusing the ref, or a lease rejected because another clone pushed
  that record meanwhile — keeps the local branch, record and claim, warns naming the ref and the
  retry, and leaves the exit code unchanged. `branch`, `claim` and `new --branch` report
  `record_remote` in `--json`: `null` when nothing was mirrored, otherwise `name`, `ref`, `commit`
  (the pushed commit, or `null`), `pushed` and `error`.
- *Deletion.* Nothing deletes a remote record. To clean one up, run
  `git push <remote> --delete refs/taskrail/branches/<ID>`; the next fetch prunes the local copy.

`taskrail branch <ID> <NAME>` names or renames a task's branch. With `OLD` the branch resolved
before the call:

- `OLD` exists locally → `git branch -m OLD NAME`. Git moves the branch's config, upstream
  included, and updates the `HEAD` of the worktree that has it checked out. The worktree directory
  is never moved, since a session may be working inside it.
- otherwise → nothing is renamed and the name is only recorded: naming a task before its workspace
  exists, or adopting a branch already renamed with plain `git branch -m`.
- The record is written, and a claim whose `branch` is `OLD` points to `NAME`; a claim mirrored to
  `claim_remote` is re-pushed with a lease on its recorded commit (`--local-only` skips it).
- With `branch_record_remote` set, the record is pushed as described above.
- `--json` returns `id`, `branch`, `previous`, `renamed`, `claim_updated`, `worktree` (where
  `NAME` is checked out, or `null`), `remote_copies` and `record_remote`.

It refuses, changing nothing: exit 2 for a name `git check-ref-format --branch` rejects or rewrites,
or the mainline of any backlog; exit 5 for the branch of another task, or for `NAME` existing
locally while `OLD` does too; exit 5 without `--force` when `<remote>/OLD` exists (a pushed branch,
and any pull request from it, would stay behind) or `<remote>/NAME` exists without a local `NAME`
(publishing would overwrite it), `<remote>` being the mainline's remote (§7.1) read from local refs;
exit 4 without `--force` when someone else holds the claim. taskrail never pushes, deletes or renames
a remote branch; after `--force`, `remote_copies` names the remote branch left behind.

## 7. CLI

| Command | Purpose |
|---|---|
| `taskrail init [--integration NAME]… [--github-workflow] [--pre-commit] [--merge-driver] [--force]` | Install into a repository; idempotent (§9) |
| `taskrail integration list` | Available agent integrations |
| `taskrail validate [--no-history] [--history-limit N]` | Check every rule in §3 and §4; non-zero exit on any error. For CI and hooks. Also warns about reopens committed without a trailer (*Reopens in history* below) |
| `taskrail list [--epic E01] [--eligible] [--fetch]` | Tasks, with computed blocked and eligible state |
| `taskrail show <ID> [--fetch]` | One task with everything an executor needs: resolved skill, stages, claim, mainline, `base` (see *Dependencies and the base* below; never fetches), `branch` with `branch_source` (`recorded` or `template`, §6.4), `worktree` (the worktree that has the branch checked out, else `<worktree_dir>/<branch>`; `null` unless `worktree = "required"`), artifact and index paths, `never_edit`, check commands, and `prior_work` (§7.2) |
| `taskrail next [--fetch]` | Eligible (`pending`) tasks in order: points ascending, then file order; never a `done-branch` task |
| `taskrail claim <ID> [--run R]` / `taskrail release <ID>` | §6.1, §6.2; `--run` ties the claim to an autopilot run (§12.4) |
| `taskrail branch <ID> <NAME> [--force]` | Name or rename a task's branch (§6.4) |
| `taskrail claims [--remote]` | Claims, each marked live or stale |
| `taskrail reserve-id` / `taskrail unreserve-id <ID>` | §6.3 |
| `taskrail new --epic E01 --kind bug --title … [--workspace [--branch NAME]]` | Allocate an ID and append a row; with `--workspace`, first create the task's branch — without an upstream (`--no-track`) — and worktree from the base and append the row there; `--branch` names that branch instead of the template and records it (§6.4), validated before an ID is reserved |
| `taskrail edit <ID> [--title] [--pts] [--depends-on] [--description] [--kind] [--column NAME=VALUE]… [--force] [--local-only]` | Change cells of an existing task row (see the rules below) |
| `taskrail done <ID>` / `taskrail discard <ID>` | Change status (see the rules below) |
| `taskrail reopen <ID> --reason …` | Move a done or discarded task back to pending |
| `taskrail review <ID> [--publish] [--type] [--scope] [--breaking]` | Hand a closed task off for review (§7.1) |
| `taskrail import <FILE> [--write] [--column CORE=HEADER]… [--status VALUE=STATUS]… [--kind VALUE=KIND]… [--default-kind KIND] [--epic-level N] [--epic-name NAME]` | Convert a table-based Markdown backlog without epics into this backlog; a dry run unless `--write` (§7.3) |
| `taskrail epic add [--own-file]` / `taskrail epic split <E##>` | Add an epic inline or in `todo/<id>-<slug>.md`; move an inline epic to its own file |
| `taskrail kind list` / `taskrail kind add <dir>` | Inspect resolved kinds; install a local kind |
| `taskrail autopilot start` / `next` / `lane` / `decision` / `status` / `merged` / `notify` | Autopilot runs, dispatch and their lanes, and merge follow-through (§12.1, §12.8) |
| `taskrail merge-driver <base> <current> <other> […]` | The git merge driver for backlog tables (§7.4); run by git, not by hand |
| `taskrail upgrade` / `taskrail self upgrade` | Re-sync installed skills without touching overrides; update the CLI |

### 7.1 Review hand-off

Closing a task ends in a pull or merge request on whatever host the repository uses. `taskrail
review` owns the deterministic parts; the agent keeps the rebase and its conflicts.

1. `taskrail review <ID>` runs on the task branch (§6.4), only once the task is done there; the
   branch is `head` in its result, and the one pushed and linked. It fetches
   the mainline's remote (unless `fetch = false` or `--no-fetch`) and picks the rebase base: the
   backlog's `mainline` or its remote-tracking branch, whichever is further ahead, and whichever
   exists if only one does. While the task's single dependency is done only on its unmerged
   branch, the base is that branch instead, and `rebase.dependency` names it; the pull request
   still targets the mainline. Diverged mainlines exit 5. With `rebase = false` no base is chosen.
2. The agent rebases onto that base when `rebase.needed` is true, resolving backlog conflicts as
   the core skill prescribes, and runs `taskrail validate`.
3. `taskrail review <ID> --publish` refuses a branch that still lacks the base, pushes the task
   branch when `push_task_branch` is true — a plain push for a new remote branch, otherwise with
   `--force-with-lease` on the remote's current commit, and always with `--set-upstream`, so the
   task's own remote branch becomes its upstream; a rejected push exits 4 — and returns the pull
   request title, description and link.

**The mainline's remote.** Each mainline uses one remote for its base, fetch, push and link:
`branch.<mainline>.remote` from git config when it names a configured remote, otherwise
`[review].remote`. A repository whose backlogs have mainlines on different remotes — `main`
tracking a template's `upstream`, `dev` tracking `origin` — therefore needs no configuration, and
tracking config wins over `[review].remote` when both are set. A value of `.` or a URL has no
remote-tracking branches and falls back. `show`, `new --workspace` and `review` resolve it the same
way, and `show --json`'s `base` and `review --json` report it as `remote` with `remote_source`
(`branch.<mainline>.remote` or `[review].remote`). The task branch is pushed to that remote, so
the link opens a same-repository pull request there; the provider settings stay repository-wide.

Pull requests are expected to be squash-merged, so the title is the commit that reaches the
mainline. It is rendered as `{type}({scope}): {subject} ({id})`: the type from the kind's
`commit_type` or `--type`, the scope from `--scope` or `[review].scope` (omitted when empty),
`!` with `--breaking`, and the task title as subject with its first letter lowercased unless the
first word is all capitals. The description names the task and its artifact and ends with a
`Reopens: <ID>` trailer for every task the branch reopened, so the trailer survives the squash.

| Provider | Link | Prefilled | Verified against |
|---|---|---|---|
| `github` | `{web}/{repo}/compare/{base}...{head}?quick_pull=1&title=…&body=…` | title, body | GitHub Docs: using query parameters to create a pull request |
| `gitlab` | `{web}/{repo}/-/merge_requests/new?merge_request[source_branch]=…&merge_request[target_branch]=…&merge_request[title]=…&merge_request[description]=…` | title, description | GitLab `Projects::MergeRequests::CreationsController#new` |
| `gitea` | `{web}/{repo}/compare/{base}...{head}?title=…&body=…` | title, body | Gitea `routers/web/repo/compare.go` |
| `forgejo` | `{web}/{repo}/compare/{base}...{head}` | nothing | Forgejo `routers/web/repo/compare.go` reads no such parameters |
| template | `[review].url_template` with `{web_url}` `{repo}` `{base}` `{head}` `{title}` `{body}` | as written | — (for Bitbucket and other hosts) |

`github.com`, `gitlab.com` and `codeberg.org` are detected from the remote URL (scp-like, `ssh://`
and `https://` forms); other hosts need `provider`, plus `web_url` when their web address differs
from the remote's host. The description is dropped from a link longer than 8,000 characters,
since GitHub answers such URLs with 414.

Write commands follow these rules:

- **Minimal diffs.** A status change rewrites one cell; `edit` rewrites only the cells it changes; `new` appends one row. Tables are never
  reformatted, because re-aligning a table turns every change into a conflict with every open
  branch. A row whose values are wider than its columns is left unaligned.
- **Validate before writing.** Every edit is applied in memory and the whole project is
  validated; if the result has errors nothing is written, and an ID reserved for it is
  released. Files are replaced atomically.
- **`done` requires the caller's claim** and releases it; it also refuses a task whose
  dependencies are not done. `discard` needs no claim, since discarding is usually a decision
  about a task nobody took, but refuses one claimed by someone else. `--force` overrides both.
- **`reopen` records its reason in git, not in the backlog.** The backlog holds state, not
  history, so `reopen` changes only the status cell. It requires `--reason` and returns a
  suggested commit message: the reason as the body and a `Reopens: <ID>` trailer. It needs no
  claim, and lists tasks that depend on the reopened one and are already done or claimed.
- **`edit` changes cells, never the status or the ID.** It edits `Title`, `Pts`, `Depends On`,
  `Description`, `Kind` and custom columns (`--column NAME=VALUE`) of one row in the current
  checkout. Each flag replaces the whole cell; `--depends-on` replaces the list. An empty value
  clears the cell, writing what `new` writes for an omitted value (`—`, or an empty
  `Description`); `--pts` takes a whole number or an empty value. Values equal to the current
  ones write nothing and still exit 0. Everything else — unknown or cyclic dependencies, points
  off the scale, an undefined or disallowed kind, an empty title — is left to validation, so it
  exits 1 and writes nothing. Exit 2 for no field flag, a malformed `--column`, a core column
  given to `--column`, a column the task's table lacks, or a line break; exit 3 for an unknown
  ID. It needs no claim, but refuses a task claimed by someone else (exit 4) and one that is
  `done`, `discarded` or `done-branch` (exit 5); `--force` overrides both. `--allow-invalid`
  lets it run on an invalid backlog, and it still writes only a result with no errors, so an
  edit can repair a cycle a merge left behind. A recorded branch (§6.4) keeps its name. When a
  new title or kind changes the name a template-named task resolves to and a local branch with
  the old name exists, `edit` records the old name — mirrored as `claim` mirrors, unless
  `--local-only` — so the work on it stays the task's branch; otherwise the task resolves to the
  new name. It never renames a git branch. `--json` returns `id`; `changes`, holding `from` and
  `to` for each changed field under `show`'s names (`title`, `points`, `depends_on`,
  `description`, `kind`, and `columns` by header); `branch` with `name`, `source`, `previous`
  (the name before the edit when it changed, else `null`) and `recorded`; `record_remote`; and
  `files`.

**Reopens in history.** The rebase rule of the core skill and `done-branch` detection find a reopen
only through its `Reopens: <ID>` trailer, so `validate` — and no other command — also reads git
history for reopens committed without one:

- *Window.* The commits reachable from `HEAD` that change a backlog's main file or an epic file the
  working tree names, newest first, at most `--history-limit N` (default 500). The window is the
  same on a task branch and on a mainline. `--no-history` skips the check; so does a directory
  outside git or a repository without commits.
- *Transition.* A commit reopens a task when the task is `⬜` there and `✅` or `❌` at every parent,
  with statuses read across all of the backlog's files at each revision, so a row moved into an
  epic file is no change and a merge counts only when its resolution flipped the cell. Only tasks
  pending in the working tree are considered, and an uncommitted reopen is not reported: the
  pre-commit hook runs before the message exists. The files are read with one
  `git cat-file --batch`, and a revision pair is parsed only when a line holding `✅` or `❌` and a
  pending task's ID disappears.
- *Recorded.* A reopen at `C` is recorded when a commit reachable from `HEAD` but not from every
  parent of `C` carries the trailer (whitespace around the ID tolerated): the reopen commit, a
  squash commit whose message kept the trailer from the pull request description, or any later
  commit — including an empty one written to acknowledge a reopen that can no longer be reworded.
  A trailer older than `C` does not count. This is the test the rebase rule and `done-branch` apply.
- *Output.* One `reopen-untraced` warning per task, for its latest unrecorded reopen, at the task's
  row, naming the commit; the exit code is unchanged. `--json` adds `history`: `examined`, `limit`,
  `truncated`, `shallow` and `skipped` (`null`, `--no-history`, `not a git repository` or
  `no commits`). The text output adds a `history:` line when the check was skipped for a reason
  other than `--no-history`, ran in a shallow clone — where commits past the boundary have no
  parents and reopen nothing — or was truncated.

Output is human-readable by default and JSON with `--json`, so skills parse results rather
than prose. Exit codes are stable:

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | the backlog fails validation |
| 2 | usage, configuration or git error |
| 3 | task, claim or reservation not found |
| 4 | conflict: claimed by someone else, or a lock could not be acquired |
| 5 | refused: the task is not pending, or is blocked (for `reopen`: it is already pending) |

Task state, as reported by `list`, `show` and `next`, is one of `pending`, `claimed`,
`blocked`, `done-branch`, `done` or `discarded`. Only local claims and local refs are
consulted, so these commands never need the network — except with `--fetch`, which first fetches
mirrored branch records (§6.4).

**Done on its branch.** A task is `done-branch` when its row is `⬜` in the current checkout but
`✅` at the tip of its task branch (§6.4) — the local branch or `<remote>/<branch>` of its mainline's
remote — and `✅` on neither the local mainline nor `<remote>/<mainline>`. It takes precedence
over a claim: the work is finished and only waits to be merged, so `next` never offers it and
`claim` refuses it. "Merged" means `✅` on a mainline ref in every checkout, including a task
worktree whose own row already says `✅`. A tip does not count when a mainline ref has a commit with
a `Reopens: <ID>` trailer (whitespace around the ID tolerated) that the tip lacks: its `✅`
predates the reopen, so a stale branch left from before `taskrail reopen` does not hide the task,
while a branch done again after the reopen contains that commit and counts. The backlog files at
those tips are read with one `git cat-file --batch` per backlog, only for tasks whose branch exists;
the reopen check is one `git log` per remaining `✅` tip of a task not merged, over the mainline
commits that tip lacks.

**Dependencies and the base.** A dependency blocks unless it is `done`; one that is done only on
its unmerged branch does not block, and the dependent is stacked on it. Two or more such
dependencies block the task, and `blocked_by` lists them. `show`'s `base` holds `onto`,
`diverged`, `reason`, the mainline's `remote` with its `remote_source`, `commit` (the commit
`onto` names) and `dependency`:

- no unmerged dependency — `onto` is the further-ahead of the local mainline and
  `<remote>/<mainline>`, `null` with `diverged` when they have diverged; `dependency` is `null`;
- exactly one — `onto` is the further-ahead of that dependency's local branch and
  `<remote>/<branch>`, by the same rule, and `dependency` is its ID;
- two or more — `onto` is `null` and `reason` names them.

`new --workspace --depends-on …` branches from the same base, and refuses with exit 5 when two or
more dependencies are unmerged.

### 7.2 Prior work

`show` also reports signs that someone may already have worked on the task, in `prior_work`.
They are informational: they never change the exit code or the task's `state`, and the core
skill asks the agent to look at them and mention them at its first gate.

- `artifact` — where the artifact file exists: `working tree`, then each local and
  remote-tracking branch tip that has it (one `git cat-file --batch` over all tips).
- `branches` — the task branch (§6.4) as a local branch and as `<remote>/<branch>`.
- `commits` — commits reachable from `HEAD`, local and remote-tracking branches (not tags or
  claim refs) whose subject names the task, newest first and capped at 10, with
  `commits_total` for the full count. Each carries the form it matched: `prefix` (the subject
  starts with the ID), `scope` (the ID in a Conventional Commits scope), `suffix` (a squash
  title ending in `(<ID>)`, optionally followed by `(#N)` or `(!N)`) or `branch` (the subject
  contains the task's branch name). A subject that mentions the ID anywhere else is ignored,
  since backlog maintenance names IDs constantly.

The history search is a single `git log --fixed-strings --grep=<ID>` over those refs, so its
cost grows with the history; `list` and `next` do not run it. Like `base`, it never fetches.

### 7.3 Import

`taskrail import <FILE>` converts an existing Markdown backlog — pipe tables of tasks under
headings, prose in between, no `## Epics` table, its own headers and status markers — into the
format of §3, changing as few bytes as possible. `--backlog` picks the target backlog when several
are configured.

**Dry run by default.** Without `--write` nothing is written: the converted file goes to stdout
and a summary to stderr; `--json` returns the summary with the file in `content`. `--write`
replaces the backlog's `file` with the result. The source may be that file (an in-place
conversion, the usual case once `init` has left an existing `TODO.md` alone) or another file,
which is left untouched. A target other than the source is replaced only when it is missing or
holds nothing but headings and empty tables, like the file `init` seeds.

**Task tables.** A table is a task table when, after mapping, its header has an `ID` and a `✓`
column. Other tables stay as they are; one with an `ID` column but no status column is listed in
`tables_skipped`. Tables and headings in fenced code are ignored.

**Headings become epics.** Each task table belongs to the nearest heading above it whose level
lies between 2 and the epic level: `--epic-level N` (2–6), or by default the shallowest level
among the nearest level-2-or-deeper heading of every task table. Each heading that owns a task
table becomes an epic, its line rewritten to `## E01 — <text>`; every other heading is kept, and
level-1 headings never become epics. Task tables under no such heading form one epic named
`--epic-name` (default `Backlog`), whose heading is inserted before its first table. Epic IDs are
numbered in order of appearance, except that a heading already shaped `E07 — Name` with the
backlog's epic prefix keeps its ID. The `## Epics` section, with `—` as objective and file, is
inserted before the first level-2 heading of the result.

**Mapping.** Every flag is repeatable and matches case-insensitively after trimming.

| Flag | Maps |
|---|---|
| `--column CORE=HEADER` | a source header onto a core column, in the direction of `[columns].aliases`; headers equal to a core name or its alias need no flag |
| `--status VALUE=pending\|done\|discarded` | a status value, besides the built-in `⬜ [ ] todo pending open`, `✅ [x] done closed`, `❌ discarded cancelled` |
| `--kind VALUE=KIND` | a kind value onto a kind the repository resolves and allows; a kind name in another letter case maps without a flag |
| `--default-kind KIND` | the kind of rows whose table has no Kind column or whose Kind cell is empty |

- Mapped headers are renamed to the repository's name for the column: its alias, else the core
  name. Unmapped headers stay as custom columns, reported for `[columns].custom`.
- A table without `Kind` gains one after `ID`, filled with `--default-kind`; a table without
  `Depends On` gains one after `Kind`, filled with `—`.
- Status cells become `⬜`, `✅` or `❌`. A `Depends On` cell of task IDs separated by commas,
  semicolons or spaces becomes `T001, T002`, and an empty cell, `-` or `–` becomes `—`.
- IDs are never renumbered, padded or re-prefixed: an ID that does not match the prefix and
  `id_digits` is refused, with the `id_digits` value that would keep it when only padding differs.
- Only cells whose value changes are rewritten, keeping the cell's width when the value fits.
  Every other byte — other cells, escaped pipes, spacing, row order, prose, fenced code, line
  endings — is kept, and inserted lines use the source's line ending.

There is no default status: a status is never guessed.

**Running it twice.** A source that already has an `## Epics` section and validates converts to
itself, so a second in-place run, or importing a previous result, reports `unchanged` and writes
nothing; a target already equal to the result is left alone as well.

**Exit codes.** Every problem is collected before exiting, each with its lines:

| Exit | When |
|---|---|
| 0 | converted, written, or nothing to change |
| 1 | the result fails `validate` in the target file (for example `depends-unknown`); nothing is written |
| 2 | an unreadable source, several backlogs without `--backlog`, a malformed flag, a `--column` key that is not a core column, a `--kind` or `--default-kind` kind that is not allowed, `--epic-level` outside 2–6 |
| 4 | with `--write`, an imported ID is reserved by `reserve-id` and not yet used, or the ID lock is busy |
| 5 | no task table; unmapped statuses, kinds or dependency cells, each distinct value with its count; a missing Title, or a missing Kind without `--default-kind`; an empty title; a row with the wrong number of cells; two columns mapped to one core column; a malformed or duplicated ID; a source with an `## Epics` section that does not validate; with `--write`, a target other than the source that already holds a backlog |

`--json` returns `source`, `target`, `backlog`, `written`, `unchanged`, `already_imported`,
`epic_level`, `epics` (`id`, `name`, source `line`, `tasks`), `tasks`, `mapped` (`columns`,
`statuses` and `kinds` with a count per value, `default_kind`), `custom_columns`,
`tables_skipped`, `problems` (`code`, `message`, `lines`, and `value` and `count` for unmapped
values), `issues` and `content`.

Once written, imported IDs are in the backlog file, so `reserve-id` counts them (§6.3). `--write`
holds the ID lock while it checks reservations and replaces the file. Outside git there is no lock
and no reservation. IDs used on other branches are not checked, since the source itself may be
committed there. Not supported: list-based backlogs, tables without IDs, setext headings, a status
implied by the section, editing the configuration, merging into a backlog that already has tasks,
and epics in their own files (`epic split` moves them afterwards).

### 7.4 Merge driver

Parallel task branches edit the same backlog tables, and git sees adjacent lines, not rows: two
branches appending to one epic, a `✓` flipped next to a row appended by the other, or a rebase
replaying a commit that opens a row already upstream all conflict, as do bullets two branches append
to a changelog. `taskrail merge-driver` resolves those as a git merge driver.

**Contract.** `taskrail merge-driver <base> <current> <other> [--marker-size N] [--path P]
[--base-label L] [--current-label L] [--other-label L]` — git's `%O %A %B %L %P %S %X %Y`. The
result is written over `<current>`; the exit status is 0 for a clean merge and 1 when conflicts are
left with standard markers of `--marker-size` characters and the given labels. Nothing else is
read or written, and no other status is returned: any internal failure, including input that is not
UTF-8, gives exactly what `git merge-file` gives for the same inputs, with a warning on stderr.

**Tables merged row by row.** Pipe tables outside fenced code are identified by their section —
the epic ID of a `## E## — …` heading, otherwise the heading, or the text before the first level-2
heading — and their position in it. A table present on both sides with the same header (trimmed,
case-insensitive), rows of the header's width and unique non-empty keys is merged row by row; the
base is the same table in the ancestor when its header matches, else empty (a header change on any
side leaves the table to git). The key column is `ID`, through `[columns].aliases` when the working
tree's config can be read, else the first column, so the `## Epics` table and artifact indexes
merge too.

- A key on both sides: each cell is merged three-way against the base row; a cell both sides
  changed differently leaves the row unresolved, except the `✓` cell below.
- A key on one side: added when the base lacks it, removed when the base has it and the side keeping
  it did not change it, unresolved (modify/delete) otherwise. A key only in the base is removed.
- Order: the current side's rows, each row only the other side has placed after its predecessor
  there, past rows new on the current side — so both sides appending gives the current side's rows
  first. A merged row is the current side's line with only the other side's cells replaced.

**`✓` cells.** In a task table, when the sides' statuses differ and neither equals the base's (or
there is no base row): one `✅` wins, unless the other is `⬜` and its side has a `Reopens: <ID>`
commit the `✅` side lacks; any other pair is unresolved. The sides are found from the labels,
since `MERGE_HEAD`, `REBASE_HEAD` and `CHERRY_PICK_HEAD` do not exist yet while a driver runs: the
first word of `%X` and `%Y` (`HEAD` and the merged name in a merge, `<hash> (<subject>)` in a rebase
or cherry-pick) resolved with `git rev-parse --verify`. One
`git log --left-right --cherry-pick --grep=^Reopens: <current>...<other>` then lists the reopens,
ignoring those patch-equivalent on both sides, as a rebase that already replayed one leaves. When a
label does not resolve — git before 2.44 passes the placeholders literally; a criss-cross merge's
virtual base has no commits — a conflict that needs this check stays marked.

**Everything else.** The merged rows replace each such table in all three inputs — identical, so
they are context — except unresolved rows, which keep each version's own line at their merged
position. `git merge-file` then merges the result, so prose, headings, new sections and tables not
merged by row behave as in an ordinary merge, and markers surround only unresolved rows and truly
conflicting text. Placing the merged table in the base too is what lets a prose edit right after a
table merge cleanly. The driver never validates, since the other backlog files may not be merged
yet; rules across tables or files stay with `taskrail validate`, which the core skill runs after a
rebase.

**Bullet lists merged bullet by bullet** (*implemented, T040*). Changelogs conflict the same way:
two branches appending a bullet to `## Unreleased`, and "keep both" leaves a bullet twice when one
side moved it. After the tables, the driver reads tight bullet lists outside fenced code: a bullet
is a column-0 `- `, `* ` or `+ ` line plus its indented continuation lines; a list is a run of
bullets with no blank line between them; ordered items are not bullets. A list is identified by
its heading path (every ATX heading level, so `## Unreleased` › `### Added` differs from
`## 0.1.0` › `### Added`) and its position under that path. Lists are merged when the path has the
same number of lists on both sides and in the base, or none in the base, and no fence opens
inside one of its bullets; a bullet's key is its text without trailing whitespace, unique within
each version's list.

- Edits: for each side, `SequenceMatcher` over the base's and the side's keys; in a `replace` block,
  base bullets the side no longer has pair in order with side bullets the base never had, as edits
  of the base bullet. Unequal non-zero counts leave the list to git.
- Each bullet is then merged three-way like a row: an edit on one side wins, two different edits
  and an edit against a deletion are unresolved, a bullet unchanged on one side and deleted on the
  other is removed, and a bullet added on either side, or identically on both, appears once.
- Moves: among bullets present everywhere, a side moved one that falls outside the matching blocks
  of the base's order and its own. It takes the moving side's position (the current side's when
  both moved it), so a moved bullet is never kept twice.
- Order: the row rule, with bullets only the other side moved placed like its additions — the
  current side's bullets first when both append.
- A merged list that would hold the same text twice is left to git.

Merged lists are placed into the three inputs as tables are, after them and before
`git merge-file`. `init --merge-driver` adds to the block every `CHANGELOG.md`, in any letter case,
that `git ls-files --cached --others --exclude-standard` lists outside `worktree_dir`, and `upgrade`
picks up new ones; any other file gets the same merge with its own `merge=taskrail` line outside
the block, which taskrail leaves alone.

**Installing.** `init --merge-driver` records the extra and:

- writes a marked block in `.gitattributes`, keeping every other line, with `/<path> merge=taskrail`
  for each backlog file, epic file, artifact index (each kind's `artifact_index` and
  `[autopilot].decisions_index` rendered per backlog, skipping per-task templates) and changelog,
  quoted or escaped so it matches exactly that path. `upgrade` and `init` refresh it while the extra
  is recorded, and `epic add --own-file` and `epic split` refresh an existing block when they create
  an epic file;
- sets `merge.taskrail.name` and `merge.taskrail.driver` in this clone's local config:

  ```
  .taskrail/bin/taskrail merge-driver %O %A %B --marker-size %L --path %P --base-label %S --current-label %X --other-label %Y; rc=$?; [ $rc -le 1 ] && exit $rc; git merge-file --marker-size %L -L %X -L %S -L %Y %A %O %B
  ```

  git runs it from the top of the worktree, so each worktree runs its own pinned taskrail; the tail
  gives an ordinary merge when taskrail cannot start. `upgrade` rewrites an existing definition and
  never adds one: running repository code on merges is each clone's choice.

The block is committed and the definition is not. A clone with no `merge.taskrail` section merges
those files with git's text merge; a section with a `name` but no `driver` makes git fail, so remove
the whole section (`git config --remove-section merge.taskrail`) to opt out.

## 8. Skills

- `taskrail` — the core skill: the backlog model, how to call the CLI and read its exit codes,
  the procedure every kind shares (identify, inspect, workspace, claim, stages, scope,
  artifact, close, hand off) and the gate protocol. Executor skills refer to it instead of
  repeating it.
- `taskrail-bug`, `taskrail-chore`, `taskrail-feature`, `taskrail-spike` — one per core kind,
  containing only what happens inside each stage and what the artifact must hold.
- `taskrail-autopilot` — the orchestrator of an autopilot run (§12): when to run, dispatch,
  supervision, answering gates, escalation, hand-off and follow-through, with its lane brief,
  gate checklist and decision-record template in `references/`.

Skills never compute paths: `taskrail show --json` returns the branch, worktree and artifact
paths rendered from the kind's templates.

Frontmatter is limited to `name`, `description`, `license`, `compatibility` and `metadata`, the
fields every supported agent accepts. Skills describe gates as "ask the human if you can,
otherwise stop and return the report to whoever invoked you".

### Integrations

An integration decides where skills are written and adds short agent-specific notes to a
skill at its `<!-- taskrail:harness -->` marker. `integrations/<integration>.md` holds one
section per skill, each opened by `<!-- taskrail:skill <name> -->`; a skill receives only its own
section, and a marker with no section is dropped. Only `SKILL.md` carries the marker; the
portable text names no agent.

| Integration | Skills directory | Notes in `taskrail` | Notes in `taskrail-autopilot` |
|---|---|---|---|
| `claude` | `.claude/skills/` | ask with AskUserQuestion; create task worktrees with git rather than subagent isolation | lanes are background subagents resumed with `SendMessage`; the model per lane; no timer |
| `opencode` | `.opencode/skills/` | ask in plain text; a subagent's final message returns to its caller | lanes are task tool calls resumed by `task_id`; gates answered in waves |

OpenCode also reads `.claude/skills/` and requires skill names to be unique across every
location it reads. With both integrations installed, the skills are therefore written once, to
`.claude/skills/`, carrying both agents' notes.

## 9. Distribution

Modeled on Spec Kit: a CLI installed with uv, which writes files into the consuming
repository.

```bash
uv tool install taskrail --from "git+https://github.com/alexkander/taskrail.git@v0.1.0"
taskrail init --integration claude
```

Tags are the plain version, `vX.Y.Z`.

`init` is idempotent, and every run adds to what is installed. When it creates, changes or
removes a skill, its report says to restart the agent session, since agents load skills when a
session starts.

`init` adds to what is installed on every run:

- **Seeded files** — `.taskrail/config.toml` and each backlog file — are created only when
  missing and belong to the repository afterwards.
- **Managed files** — the wrapper, every file of each skill directory (`SKILL.md` and, for
  example, `references/`), the optional workflow — are rewritten when they
  change, unless edited locally. `.taskrail/installed.json` records each managed file's digest;
  a file edited since, or one taskrail did not write, is skipped and reported. `--force`
  replaces it. A skill file no longer wanted (for example after adding a second integration, or
  one no longer shipped) is removed under the same rule.
- **Executor skills follow the kinds.** A shipped skill that a core kind names, in `skill` or a
  route, is an executor skill. It installs only when a kind the repository resolves — core,
  local and overrides, after `[kinds].allowed` (§5.2) — names it, so a local kind may pull in a
  shipped executor skill whose own kind is not allowed. Shipped skills no core kind names, such
  as the core `taskrail` skill and `taskrail-autopilot`, always install; skills taskrail does not ship are never written.
  The report notes the executor skills left out. While kind resolution reports errors, such as
  `kind-allowed-unknown`, nothing the kind filter would remove is removed, and a note says so:
  bad input never deletes a skill, and the next run after the fix removes what is not wanted.
- **Extras** — `--github-workflow` is remembered in the manifest, and its workflow checks out full
  history (`fetch-depth: 0`): `validate`'s reopen check (§7) finds nothing past a shallow clone's
  boundary; `--pre-commit` writes a marked block into this clone's git hook, keeping an existing
  shell hook's contents; `--merge-driver` is remembered too, keeps a marked block of
  `.gitattributes` current and defines the driver in this clone's git config (§7.4).

`taskrail upgrade` repeats the install with the recorded integrations and pins the config to
the running CLI version. `taskrail self upgrade [--tag]` reinstalls the CLI from a release tag.

Unlike Spec Kit, the skills call the CLI while they work. `init` therefore also writes a
committed wrapper, `.taskrail/bin/taskrail`: it runs the installed CLI when its version matches
the pin, and otherwise runs the pinned version through `uvx`. The only prerequisite on any
machine, CI runner or agent sandbox is `uv`. A pin of the form `local:<path>` makes the wrapper
run the taskrail source at that path in the current checkout, so a worktree runs its own
branch's code; `upgrade` never replaces such a pin. `TASKRAIL_BIN` overrides the wrapper
entirely; `TASKRAIL_SOURCE` overrides the repository URL.

## 10. Layout

```
taskrail/
├── DESIGN.md
├── README.md
├── pyproject.toml
├── src/taskrail/          # parser, validator, claims, writer, installer, CLI
│   ├── kinds/             # core kind descriptors        ┐
│   ├── skills/            # core, executor and autopilot ├ shipped as package data
│   └── integrations/      # agent-specific skill notes   ┘
├── examples/spec-kit/     # example repository-local `spec` kind
└── tests/
```

## 11. Phases

1. **v1** — format, config, `validate`, `list`/`next`/`show`, local and remote claims, ID
   allocation, epics, kind resolution, core kinds and skills, the Claude integration, `init`
   and the wrapper.
2. **v2** — autopilot orchestrator, import from existing backlogs (§7.3, T005), a git merge driver that
   resolves backlog table conflicts (§7.4, T004). The autopilot is designed in §12 and delivered by T017 (stacked
   base and `done-branch`), T027 (unreadable manifest), T029–T032 (the `autopilot` commands),
   then T024 (the skill), and trialled by T033 (§12.10).

## 12. Autopilot (implemented)

Status: **implemented.** Accepted at the decide gate of the
[T007 spike](../../docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md), with the
human's decisions in its
[decision record](../../docs/autopilot/decisions/T007-design-taskrail-s-autopilot-from-existin.md).
T029 implemented the configuration (§12.9, now in §4), run files and `run` in the claim (§12.4),
and `autopilot start`, `lane`, `decision` and `status` (§12.1); T030 implemented `autopilot next`
with groups and resource pools (§12.7); T031 implemented `autopilot merged` (§12.1, §12.8) and
recorded merges (§12.4); T032 added `autopilot notify`, `lane --gate` and the computed escalation
reasons in `status` (§12.6); T024 wrote the `taskrail-autopilot` skill with its Claude Code and
OpenCode notes and installed it in every repository (§12.2, §12.3, §12.5, §12.6, §12.8). Each part
is marked *implemented*; the end-to-end trial (T033) builds nothing and may change the design
through its findings (§12.10). The evidence (E1–E7) and the full comparison of options stay in the spike.

The autopilot runs several tasks at once, one lane per task, and answers their gates on the
human's behalf where the governing documents allow it. It covers the
[reference behaviour](../../docs/research/autopilot-reference-behaviour.md) of two existing
orchestrators and the lessons of this repository's first autopilot run.

### 12.1 Skill and CLI

One judgement skill, `taskrail-autopilot`, over a thin `taskrail autopilot` command group.

- **The CLI computes:** which tasks are dispatchable now; each lane's base, branch, worktree and
  resources; the state of every task in a run; silent lanes; files touched by more than one
  lane; merge detection; cleanup; the paths of decision records; running the notify command.
- **The skill judges:** answering gates on the human's behalf, reading diffs, re-running checks
  and exercising the result, writing decision records, building the touch map, resolving
  conflicts in the known classes, deciding to escalate, and the hand-off conversation.

Every command takes `--json` and uses the exit codes of §7.1; exit 5 gains one meaning, a
disabled autopilot:

| Command | Does |
|---|---|
| `autopilot start --count N [--kinds …]` | *Implemented (T029).* Exit 5, naming `[autopilot].enabled`, unless it is true — checked first, so the refusal comes even without `--count`; then exit 2 without `--count` or with a count below 1, exit 1 for an invalid backlog, and exit 2 for a kind the project does not define or allow. `--kinds` defaults to `[autopilot].kinds`. Creates a run file (§12.4) with the target count, kinds, owner and start time, and prints the run ID. |
| `autopilot next [--run R]` | *Implemented (T030).* Exit 5, naming `[autopilot].enabled`, unless it is true — checked first, preview included; then exit 1 for an invalid backlog, 3 for an unknown run, 4 when the lock cannot be taken, and 0 otherwise, even when nothing is dispatched. Tasks to dispatch now: `taskrail next`'s eligible tasks in its order (so a single unmerged dependency is a stacked base, and claimed or blocked tasks are not candidates), of the kinds the run drives — the run's `kinds` and `[autopilot].kinds` intersected when both are set, whichever is set otherwise, every allowed kind when neither is. A candidate is skipped, with its reason, when it is recorded `failed` in the run, dispatched in any run, in a group at its limit, or when its base is diverged or missing. Candidates are taken in order while a lane is free (`max_lanes`), the run's count allows more (§12.7) and every resource has a free value; `limited_by` names the limit that stopped it. For each task: `show --json`'s fields (its `base` already carries `commit`), the allocated `resources`, `environment` (`TASKRAIL_RESOURCE_<NAME>`), `groups`, and the decision-record paths; also `lanes`, `remaining`, `groups`, `resources`, `released` and `skipped`. Under the common-directory lock, in one step, it releases the resources of lanes that ended and records `dispatched` and `resources` for each dispatched task in run R. Without `--run` it is a preview for `[autopilot].kinds` with no count, and writes nothing. Claiming stays the lane's job. |
| `autopilot lane <ID> --run R [--handle H] [--group G] [--state running\|gate\|escalated\|failed\|handed-off] [--reason …] [--gate STAGE]` | *Implemented (T029; `--gate` T032; `close` T050).* Records the agent-specific lane handle, a group membership assigned by judgement (§12.7; exit 2 unless `[[autopilot.group]]` has a group of that name without `column` and `match`) and the orchestrator's view of the lane. `--reason` is required with `escalated` and `failed`, optional with `gate`, and cleared by `running`. `failed` keeps the claim, so the task stays ineligible and its dependents stay blocked. `handed-off` appends the task to the run's hand-off order once, and exits 5 unless the task is `done-branch`. `--gate` records the stage whose gate the lane is stopped at, as `gate`: it must be a stage of the task's kind, or `close` for the stop after `taskrail done` that every kind shares, and the lane must be (or be set) `gate` or `escalated`, otherwise exit 2; a move to `gate` or `escalated` keeps it, `running` and `failed` clear it. An unknown run or task exits 3. |
| `autopilot decision --run R --question … --decision … --reason …` | *Implemented (T029).* Appends a numbered run-level decision (touch map, conflict classes, order) to the run file, so run state is written only by the CLI. |
| `autopilot status [--run R] [--fetch]` | *Implemented (T029; `dispatched` T030; escalation flags T032).* Every run, newest first, with `complete` once `count` of its tasks are `done-merged`, its run-level decisions, and every run task with its state: `pending` (with `blocked_by`), `dispatched` (by `next`, not yet claimed, for less than `[git].claim_grace_minutes`; T030), `running`, `gate`, `escalated`, `failed`, `done-branch`, `handed-off`, `done-merged`, `discarded`. Precedence: `done-merged`, `discarded`, `handed-off` or `done-branch`, the recorded `failed`, `escalated` or `gate`, `running` (a claim, stale or not, with its stale reason), `dispatched`, `pending`. Also each lane's handle, group, reason and resources, branch and worktree; `idle_minutes` since the latest of the branch tip's commit, a change in its worktree, the claim and the last `lane` update, and `silent` when a `running` lane is idle past `silent_minutes`; `touched`, the files changed since the fork point plus uncommitted ones, with `overlaps` between lanes across the runs listed; the decision-record paths; and `handoff`: `in_review`, `queue` (dependencies first, then by the branch tip's commit time) and `next`, `null` while a branch is in review. Per task, the escalation reasons of §12.6: `gate` (the recorded stage), `governing_touched` (the `touched` files a `governing` entry matches), `escalate_gate` (`kind:stage` when the task is `gate` or `escalated` at a stage `escalate_gates` lists, else `null`) and `escalation` (`governing` when `governing_touched` is not empty and the task is not yet `done-branch`, `escalate-gate` when `escalate_gate` is set, or empty; T049); the text form adds `ESCALATE: …`, naming the reasons in `escalation`, to a flagged lane. Never runs the notify command. Reads git and never fetches unless `--fetch`; exit 3 for an unknown run. |
| `autopilot merged <ID> [--run R] [--cleanup] [--no-fetch] [--owner O]` | *Implemented (T031).* Runs `git fetch --prune` on the mainline's remote (skipped with `--no-fetch` or when that remote is not configured; a failing fetch exits 2), then the merge detection of §12.8 on the task's branch — the live claim's, else the one §6.4 resolves — checking the local branch when it exists, else `<remote>/<branch>`. Reports `merged`, `via` (`ancestor`, `tree`, `patch-id`, `merge-tree`), the mainline `commit`, each check in `checks`, the `confirmations`, and both heads. A proven merge is recorded as `merged` in the lane of every run holding the task, or only in `--run R` (exit 3 for an unknown run or one that does not hold the task); needs no run and no `enabled`. With no branch left, it reports a merge a run recorded (`recorded: true`), else exits 3. With `--cleanup`, removes the worktree and deletes the local branch with a lease on the checked SHA, and releases the caller's leftover claim; it exits 5 when the merge is unproven or the worktree has modified or untracked files, is locked, is the main worktree, or contains the current directory or `--root`; exit 4 for another owner's claim; the remote branch and the branch record (§6.4) are kept. Lists stacked dependents (§12.8) with `git rebase --onto <onto> <fork>`, run in the dependent's worktree. Exit 0 when the check ran, merged or not. |
| `autopilot notify --event escalation\|lane-done\|lane-failed --run R [--task ID] [--message TEXT]` | *Implemented (T032).* Runs `[autopilot].notify` when it is set and the event is in `notify_on` (§12.6), otherwise reports `skipped`. `--task` is required for `lane-done` and `lane-failed`; an unknown run, an unknown task or a task outside the run exits 3. Needs neither `enabled` nor a valid backlog. A notify command that exits non-zero, times out or cannot start is reported (`sent: false`, `exit_code`, `timed_out`, `error`, and a warning on stderr) and never blocks: `notify` still exits 0. |

The autopilot runs only when the human asks for it and gives a task count. The skill states
this in its prose, not only in frontmatter, so the rule holds on agents that ignore
invocation-control keys (*implemented, T024*).

### 12.2 Installation and opt-in

- `init` and `upgrade` install `taskrail-autopilot` in **every** repository, with the other
  skills. No kind names it, so it is not an executor skill and the kind filter of §9 never
  leaves it out (*implemented, T024*).
- A repository opts in with `[autopilot].enabled = true`. Until then `autopilot start` refuses
  with exit 5 and names the key, and the skill stops when it sees that refusal. The refusal is a
  CLI guarantee, so it holds on any agent (*implemented, T029*).

The spike had recommended installing the skill only where the autopilot is enabled, through the
kind filter. The human chose to install it always, so every consumer receives the same skills.

### 12.3 Orchestrator and lanes

**The orchestrator** is the session the human talks to. It keeps a lane handle per task in the
run file, so a compacted or new orchestrator session can resume the lanes.

**A lane** is a sub-session, and its contract is the same on every agent. The skill's lane brief
(`references/lane-brief.md`), filled from `autopilot next --json`, gives it to each lane
(*implemented, T024*). It:

- runs the `taskrail` skill and the task's executor skill for one task ID;
- creates its worktree with git and claims inside it (§8);
- ends its turn at every gate with the full gate report;
- is resumed with `continue <ID>` plus the answers;
- stops after `taskrail done` and `review --json` without rebasing, since the orchestrator rebases
  once, at hand-off (§12.8);
- never runs `review --publish`, never merges, never starts shared services, and never touches
  another lane's worktree.

| | Claude Code | OpenCode |
|---|---|---|
| Lane | background subagent (Agent tool), general-purpose | task tool, `general` or a lane agent definition |
| Handle | agent ID | `task_id` (the child session ID) |
| Resume after a gate | `SendMessage` to the ID | task tool with the same `task_id` |
| Orchestrator woken when a lane stops | completion notification | when the whole batch of task calls returns; a notification with the experimental background subagents |
| Lane asks the human | impossible: `AskUserQuestion` is removed from subagents | impossible: `question` is denied |
| Lane model | the Agent tool's `model` parameter | `model` in a lane agent definition |
| Timer wake-up | none | none |

OpenCode's task calls block by default, so there the orchestrator answers gates in waves, once
every lane in a batch has stopped: correct, but slower. Its integration note says so and names
the experimental background flag without requiring it. Agent-specific text goes in the
skill's section of the integration notes (§8, *implemented, T024*); agent definitions for pinning a lane model (`.claude/agents/`,
`.opencode/agents/`) are adapter packaging, deferred until a consumer needs them.

**Not a CLI that launches agents itself** (for example through `claude -p --resume` or
`opencode run --session`): unattended agent processes deny or skip permission prompts, which
lanes must not do, and answering gates needs an agent anyway.

### 12.4 State

- **Derived, never stored:**
  - `pending`;
  - `running`, a live claim;
  - `dispatched`, recorded by `autopilot next` less than `[git].claim_grace_minutes` ago with no
    claim yet (*implemented, T030*); once the grace passes without a claim it is `pending` again;
  - `done-branch`, ✅ at the task branch tip but not on the mainline (T017);
  - `done-merged`, ✅ on the local mainline or `<remote>/<mainline>`, or a merge `autopilot merged`
    proved as in §12.8 and recorded in a run, while its mainline commit is still an ancestor of either
    ref. The record — `merged: {via, commit, head, mainline, detected}` in the lane — is evidence, not
    a state: the lane's recorded `state` is left as it was, and a record whose commit left the
    mainline counts for nothing (*implemented, T031*);
  - `discarded`, ❌ in the checkout, so a discarded run task stays visible.

  Any session sees them, and with `claim_remote` any machine.
- **Claims** (§6) remain the only lock, so dispatch needs no new locking for tasks or IDs.
  They gain two fields:
  - `base.commit`, the dependency tip a stacked branch started from, written at claim time by
    T017, so `rebase --onto` still works after the dependency is squash-merged;
  - `run`, the ID of the run that owns the lane, written by `claim <ID> --run R`, which also
    lists the task in the run file so it stays a member after `done` releases the claim
    (*implemented, T029*).
- **Run file** (*implemented, T029*): `$(git rev-parse --git-common-dir)/taskrail/runs/<run>.json`, next to the claims,
  local and never committed. It holds only what git cannot derive and what must survive the
  orchestrator's context:
  - the target count and kinds;
  - per task: the lane handle, the group, `gate`, `escalated` or `failed` with a reason, when
    `next` dispatched it, and the allocated resources;
  - the `handed-off` order;
  - the run-level decisions agreed so far.

  The run ID is `YYYYMMDD-N`: the UTC date and the first number of that day no run holds. The
  file is created exclusively (a fully written temporary file hard-linked into place), changed
  under the common-directory lock `reserve-id` uses, replaced atomically, and read keeping keys
  this version does not know. Its keys are `id`, `started`, `owner`, `count`, `kinds`, `tasks`
  (per task: `handle`, `group`, `state`, `reason`, `gate`, `updated`, `dispatched`, `resources`), `handed_off` and
  `decisions` (each `number`, `question`, `decision`, `reason`, `recorded`). A task belongs to a
  run when the run file lists it or its claim names the run. Runs are never removed.
- **Two orchestrator sessions** may run at once. They never dispatch the same task twice, since
  `next` skips a task dispatched in any run and a lane needs a claim, and `status` lists every run
  in the common directory, so each sees the other's lanes.

### 12.5 Decision records

- **Path:** one file per task at `decisions`, default
  `{artifacts}/autopilot/decisions/{id}-{slug}.md`, indexed at `decisions_index`, default
  `{artifacts}/autopilot/decisions/README.md` (columns Task, Title, Document). `autopilot next`
  and `status` render both paths.
- **Template:** the skill's `references/decision-record.md` (*implemented, T024*).
- **Committed** on the task branch by the orchestrator, **only while the lane is stopped at a
  gate** and before resuming it, so the record travels with the squash-merged pull request.
- **Format:**
  - an introduction stating that each decision is recorded before it is given;
  - one `## <stage> gate` section per gate: a `Reviewed:` paragraph naming the artifact commit,
    the diff range, the re-run checks and the real-runtime verification, then a table
    `# | Question | Options | Decision | Reason`;
  - `## Conflict handling agreed for all lanes`, when a touch map was given;
  - `## rebase after …`, naming the merged tasks, then the same table (one row per conflict and
    how it was resolved) and the checks re-run afterwards;
  - `## escalated to the human` for escalated gates, with the same table, naming who answered.

  Every section uses the one `# | Question | Options | Decision | Reason` table, as this
  repository's own records do (decided at T024's plan gate).
- **Run-level decisions** — touch map, conflict classes, order — are copied into each affected
  task's record, and kept in the run file. No run log lives on the mainline, since it would need
  a commit outside any task.

### 12.6 Escalation, notification and supervision

The orchestrator stops and asks the human when:

1. a lane's branch touches a `governing` path;
2. the gate is listed in `escalate_gates`, such as `spike:decide`;
3. the governing documents reserve the decision to humans;
4. two lanes contradict each other;
5. a merge conflict falls outside the known classes (§12.8);
6. a task row rests on a false premise;
7. the base has diverged, as `show` and `review` already report.

`autopilot status` computes the first two (*implemented, T032*); the rest are judgement, which
the skill lists with how to escalate: `lane --state escalated`, `notify --event escalation`, then
the question to the human (*implemented, T024*).

- **Governing paths.** Each `governing` entry is a repository-relative path or shell-style glob
  that matches a file or any of its leading directories: `docs/adr` and `docs/adr/` cover
  `docs/adr/0001.md`, `*` and `?` stay within one path segment, `**` crosses segments (`**/` also
  matches none), `[…]` is a character class (`[!…]` negated), letter case counts, and a leading
  `./` is ignored. They are matched against the lane's `touched` files, so uncommitted changes
  count. An entry as broad as the backlog file or `docs` flags every lane; that is the
  configuration's choice. A task that has moved on (`done-branch` and `handed-off`) keeps its
  `governing_touched`, but `governing` leaves its `escalation`, as `escalate_gate` does: the edit
  was escalated while the lane worked, and a branch waiting for hand-off would otherwise raise it
  again on every `status` (T033 finding F9; T049). A governing path first changed after the lane's
  last gate is caught by the close review instead, which escalates any `governing_touched` path
  the task's record does not show escalated.
- **Escalated gates.** A lane records the stage it is stopped at with `autopilot lane --gate`;
  `status` flags it when the task is `gate` or `escalated` and `<kind>:<stage>` is in
  `escalate_gates`. A task that has moved on (`done-branch` and later) is not flagged. That
  includes `close`, recorded once the task is `done-branch`, so a `<kind>:close` entry in
  `escalate_gates` never flags.
- **Conflicts outside the known classes get no computed flag** (decided at T032's plan gate). A
  merge conflict exists only during the rebase the orchestrator itself runs, where git already
  names the files; and the known classes of §12.8 are defined by content — rows added on both
  sides, appended bullets — not by path, so a path-based flag would call a real edit inside a
  backlog file or changelog "known". Predicting conflicts with `git merge-tree` for every lane
  would also cost a merge per lane on every `status`. The end-to-end trial (T033) may reopen this
  with evidence.

**Notification** is a command contract, not an agent hook: hooks such as Claude Code's
`Notification` are agent-specific and fire on the agent's own events. `autopilot notify` runs
`[autopilot].notify` for the events in `notify_on` (default `["escalation", "lane-done"]`), with
the message on stdin and `TASKRAIL_EVENT`, `TASKRAIL_RUN` and `TASKRAIL_TASK` (empty without
`--task`) in the environment (*implemented, T032*):

- the command runs through the platform shell, in the repository root, with a 30-second timeout
  that kills its process group (on POSIX); its stdin, stdout and stderr are temporary files, so a
  command that never reads its input or leaves a child running cannot make taskrail wait, and the
  last 2000 characters of its output are reported;
- the message is plain text: `taskrail autopilot: <event> in run <R>`, then `<ID> <title>` and
  `lane: <state>[ at <gate>][ — <reason>]` for a task, then a blank line and the `--message` text
  when given; taskrail's own stdin is never passed through;
- only `autopilot notify` runs the command: not `status`, which runs on every wake-up and would
  repeat notifications, and not `lane`. Nothing records which notifications were sent.

**Supervision** is event-driven, since neither agent wakes on a timer. Whenever the orchestrator
wakes, it runs `autopilot status`. A lane silent past `silent_minutes` (default 20) is checked by
reading its worktree, and escalated if it is stuck. An agent that can wait on a condition may run
`status` periodically, but the design does not rely on it.

### 12.7 Resources

*Implemented (T030)* by `autopilot next` (§12.1).

- **A lane is in use** while its task is `running` (a claim, stale or not), `gate`, `escalated` or
  `dispatched` in a run. `failed`, `done-branch`, `handed-off`, `done-merged` and `discarded` use
  none: a failed lane keeps its claim, so its task and dependents stay out, but it no longer holds
  a lane. Lanes, group limits and resource values are counted across every run in the clone;
  claims without a run are not lanes.
- **`max_lanes`** (default 3) caps the lanes in use at once.
- **The run's `count`** caps what a run starts: `next --run R` dispatches at most `count` minus the
  run's tasks that are `dispatched`, `running`, `gate`, `escalated`, `failed`, `done-branch`,
  `handed-off` or `done-merged`. A `discarded` task frees its place; a `failed` one keeps it, since
  it waits for a human, and replacing it would start more work than was asked for.
- **`[[autopilot.group]]`** has a `name`, a `limit`, and either `column` plus `match` (membership
  computed from the task's column) or neither (membership assigned by the orchestrator's
  judgement, with `autopilot lane <ID> --run R --group G` — before `next` for a task not yet
  dispatched, and `next` honours it). It generalises "at most one UI lane". `column` plus `match`
  is the column predicate of conditional stages (§5.4), parsed and matched by the same code. A
  task may count toward several groups, and is dispatched only while each has room.
- **`[[autopilot.resource]]`** has a `name` and `values`. Each dispatched lane gets the first free
  value of every resource, in the order `values` lists them, allocated under the common-directory
  lock, and passed to the lane in its brief as `TASKRAIL_RESOURCE_<NAME>` — a database name, a
  port, an emulator. A lane holds its values while it is in use. **Release is lazy**: the next
  `next --run` clears the `resources` of every lane, in any run, that is no longer in use, and
  reports them in `released`, so a lane resumed later or a reopened task never shares a value with
  another lane. The orchestrator therefore re-runs a lane's checks — at a gate or at hand-off
  (§12.8) — before its next `next`, while the lane's values are still its own.
- **Shared services** are started by the orchestrator, never by lanes.
- **Sequential numbers:** task IDs go through `reserve-id` (§6.3), already safe across lanes.
  Other sequences stay out until a consumer needs them; a value pool covers small cases.

### 12.8 Merge follow-through

The skill carries publishing, hand-off, follow-through and the known conflict classes below as its
procedure (*implemented, T024*); detection and cleanup are the CLI's (*implemented, T031*).

- **Publishing.** Lanes stop after `taskrail done` and `review --json`. The orchestrator rebases
  when needed, re-runs the checks, then runs `review --publish --type … --scope …` in the lane's
  worktree, which pushes with a lease when `push_task_branch` is set.
- **Hand-off is sequential** (`handoff = "sequential"`, the only value at first): one branch at a
  time, dependencies first, then in completion order, each with its exact title and link. Every
  later branch costs one rebase and retest onto a mainline carrying every earlier merge; in
  exchange, every pull request is tested on the real mainline before review.
- **When the human says a branch is merged,** the orchestrator runs
  `autopilot merged <ID> --cleanup`, names the next branch, and rebases it and every stacked
  dependent onto the new mainline with `git rebase --onto <mainline> <base.commit>`. It resolves
  the known classes, re-runs the checks, and publishes again with a lease push.
- **Merge detection** is by content, since pull requests are squash-merged and ancestry alone
  sees nothing (*implemented, T031*). After one `git fetch --prune`, and only for a head whose
  task row is ✅ — an unstarted branch is an ancestor of the mainline and its `merge-tree` is a
  no-op, so without that guard checks 1 and 4 would call it merged — in this order, stopping at
  the first that holds:
  1. the task branch head is an ancestor of the mainline; the reported commit is the oldest
     first-parent commit containing it (the merge commit, or the head after a fast-forward);
  2. a commit on `git log --first-parent <mainline>` since the merge-base has the head's tree (the
     oldest such commit is reported);
  3. the patch-id of `git diff <merge-base> <head>` equals that of a first-parent commit since the
     merge-base. The range is bounded by the merge-base, read as one `git log -p | git patch-id`
     stream newest first and stopped at the first match, so an old merge is never missed and a
     recent squash costs little;
  4. `git merge-tree --write-tree` of the head into the current mainline writes the mainline's own
     tree (git 2.38 or later; reported as skipped otherwise).

  The mainline ref is the further-ahead of `<mainline>` and `<remote>/<mainline>`; when they have
  diverged, the remote one is tried first. The ✅ row on the mainline and an `(ID)` pull request
  title confirm a merge but never prove it, since a row can be edited by hand.
- **Stacked dependents** are the tasks listing the merged task in `Depends On`, not ✅ on the
  mainline, with a local or remote branch. Their fork point is the live claim's `base.commit` when
  its `base.dependency` is the merged task and the dependent's head still contains it (a dependent
  already rebased does not, so no second rebase is offered); else `git merge-base <dependent> <dependency head>`
  with the head this call checked, so deleting the dependency's branch afterwards loses nothing
  (§6.1); else the `head` a run recorded. A fork point already on the mainline means the dependent
  branched from the mainline and needs no `--onto`. When a released dependent's dependency was
  rewritten after it branched, `merge-base` falls back to the mainline and the dependent reads as
  not stacked; `fork_source` says which source was used.
- **Known conflict classes,** resolved without a human; anything else escalates:
  1. backlog rows, united by ID, with ✅ winning unless a `Reopens:` commit exists (the merge
     driver, §7.4, where a clone installed it; by hand with the core skill's rule otherwise);
  2. appended index rows and changelog bullets: keep all, each once (by the merge driver when the
     file is in its `.gitattributes` block, where a bullet one side moved stays only at its new
     place; by hand otherwise, taking the same care with moved bullets);
  3. installed skill copies and `.taskrail/installed.json`: make the manifest valid first, merge
     the sources, then run `taskrail upgrade --force`.
- **Class 3 needs T027 first:** until `init` and `upgrade` stop on an unreadable manifest, a
  mistaken `init` silently drops the recorded integrations. T027 is not a backlog dependency of
  the autopilot tasks, but it should land before the skill relies on class 3.

### 12.9 Configuration

The single-value keys joined §4 with T029, and the `group` and `resource` tables with T030:

```toml
[autopilot]
enabled = false                 # allow `autopilot start`; the skill is installed regardless
max_lanes = 3
kinds = []                      # kinds the autopilot may drive; empty means every allowed kind
governing = []                  # read first to answer gates; a lane touching one escalates
escalate_gates = []             # "kind:stage" always taken to the human, e.g. "spike:decide"
decisions = "{artifacts}/autopilot/decisions/{id}-{slug}.md"
decisions_index = "{artifacts}/autopilot/decisions/README.md"
silent_minutes = 20
handoff = "sequential"          # the only value at first
notify = ""                     # command; event in TASKRAIL_EVENT, message on stdin
notify_on = ["escalation", "lane-done"]

[[autopilot.group]]             # at most `limit` lanes at once from this group
name = "ui"
limit = 1
column = "Area"                 # omit column and match to assign membership by judgement
match = ["UI"]

[[autopilot.resource]]          # one value per lane
name = "PORT"
values = ["5433", "5434", "5435"]
```

### 12.10 Delivery

| Task | Kind | Depends on | Builds |
|---|---|---|---|
| T017 | feature | — | `done-branch` (§12.4), the stacked base in `show`, `new --workspace` and `review`, and `base.commit` in the claim (§6, §7) |
| T027 | bug | — | `init` and `upgrade` stop with exit 2 on an unreadable `installed.json`, the prerequisite for conflict class 3 (§12.8) |
| T028 | chore | — | this section |
| T029 | feature | T017, T028 | `[autopilot]` configuration (§12.9), run files and `run` in the claim (§12.4), `autopilot start` with its exit-5 refusal (§12.2), `lane`, `decision` and `status` (§12.1) — implemented |
| T030 | feature | T029 | `autopilot next`: kinds, group limits, resource pools (§12.7) — implemented |
| T031 | feature | T029 | `autopilot merged`: merge detection and cleanup (§12.8) — implemented |
| T032 | feature | T029 | `autopilot notify` and the escalation flags in `status` (§12.6) — implemented |
| T024 | feature | T030, T031, T032 | the `taskrail-autopilot` skill with Claude Code and OpenCode notes, installed in every repository (§12.2, §12.3, §12.5, §12.8) — implemented |
| T033 | spike | T024 | an end-to-end trial on a real backlog with each supported agent |

T019 changes how a task's branch is found, as T017 does, so it runs after T017; it is not needed
by the autopilot. T020 is independent, apart from the shared column predicate (§12.7). T004 and
T005 stay independent.

Not planned now: lane agent definitions for pinning a lane model; a `batch` hand-off mode; named
counters beyond task IDs.

The design changes if:

- OpenCode's background subagents become default and stable: drop the "waves" caveat;
- either agent loses resume-by-handle: lanes restart from their branch and artifacts, and the
  run file needs a stage checkpoint per lane;
- a consumer needs lanes on several machines: the run file needs a remote form, like
  `claim_remote`;
- hosts squash with a rebase that alters content: tree and patch-id could miss, and detection
  would need the host's pull-request state, currently a non-goal (§1);
- the trial (T033) shows sequential hand-off costs more than it catches: add `batch`;
- consumers object to being offered an autopilot skill they have not enabled: install it only
  where enabled, reusing the kind filter of §9.

Rejected alternatives, with their reasons, are in the spike's *Options considered*.
