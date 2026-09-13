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
- Importing the source projects' existing backlogs. Phase 2.
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
column through its usual flag (`--pts`). `new --column` is for custom columns only: it refuses
every core column, by core name or alias and in any letter case, naming the flag that fills it
(`ID` and `✓` are set by taskrail). Config is refused when a
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
```

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
  (or `"-"`) an empty one, as in `[[route]]`. Routes themselves still match exactly.

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

## 6. Claims and IDs

### 6.1 Local claim — always on

A claim is a file created atomically (`O_EXCL`) under the git common directory:
`$(git rev-parse --git-common-dir)/taskrail/claims/<ID>.json`, holding owner, branch, worktree,
host, timestamp and `base`. Every worktree of a clone shares that directory, so parallel sessions on
one machine see each other's claims without any network.

`base` records where the claimed branch started: `onto`, the ref `show` reports as the base (§7);
`dependency`, the ID of the unmerged dependency it is stacked on, or `null`; and `commit`, the
fork point `git merge-base HEAD <onto>` at claim time. Once that dependency is squash-merged,
`git rebase --onto <mainline> <base.commit>` replays only the task's own commits. `taskrail done`
releases the claim, so for a finished dependent the fork point is also
`git merge-base HEAD <dependency branch>` while that branch exists: follow-through must compute it
before removing the dependency's branch. `base` is
`null` when no base could be determined. A claim file is read ignoring keys this version does not
know, so a later version can add fields without hiding its claims from this one.

`taskrail claim <ID>` fails if another live claim exists, and refuses a task that is not
pending, is `done-branch`, or is blocked (`--ignore-deps` overrides the last). Claiming again with the same
owner and branch is a no-op. `taskrail release <ID>` removes a claim; releasing someone
else's needs `--force`. The owner defaults to `$TASKRAIL_OWNER`, then `user@host`.

A claim is **stale** when its worktree no longer exists, or when its branch does not exist and
the claim is older than `claim_grace_minutes` — the grace lets an agent claim first and create
the branch right after. The age of the claiming process is deliberately not a criterion: the
CLI exits as soon as the claim is written. A stale claim is only ever reported, never removed
automatically; `--takeover` replaces it explicitly, and never replaces a live one.

### 6.2 Remote claim — optional

With `claim_remote` set, a claim is also pushed as `refs/taskrail/claims/<ID>`: a parentless
commit holding `claim.json` with only `id`, `owner`, `branch`, `created` and `base` — the host and the
worktree path stay in the local claim, since a remote may be public — pushed with `--force-with-lease=<ref>:` so the push fails if the
ref already exists. If the push fails the local claim is rolled back. Releasing deletes the ref
with a lease on the commit that was pushed. `--local-only` skips the remote for one command.

Off by default: it needs network and permission to push, and the server must accept refs
outside `refs/heads` and `refs/tags`.

### 6.3 ID allocation

`taskrail reserve-id` (and `taskrail new`) reserves the next ID under a lock in the
same common directory. The next number is one above the maximum of: IDs in the backlog's files
in the working tree, on every local branch and — with a remote configured — on its
remote-tracking branches, plus IDs reserved but not yet used. A reservation is dropped once
its ID appears in any of those files; `taskrail unreserve-id` cancels one that will not be
used. This replaces "highest plus one", which two agents can compute identically.

Only IDs in the `ID` column of task tables count, so a description that mentions an ID does
not move the counter.

## 7. CLI

| Command | Purpose |
|---|---|
| `taskrail init [--integration NAME]… [--github-workflow] [--pre-commit] [--force]` | Install into a repository; idempotent (§9) |
| `taskrail integration list` | Available agent integrations |
| `taskrail validate` | Check every rule in §3 and §4; non-zero exit on any error. For CI and hooks |
| `taskrail list [--epic E01] [--eligible]` | Tasks, with computed blocked and eligible state |
| `taskrail show <ID>` | One task with everything an executor needs: resolved skill, stages, claim, mainline, `base` (see *Dependencies and the base* below; never fetches), branch, worktree, artifact and index paths, `never_edit`, check commands, and `prior_work` (§7.2) |
| `taskrail next` | Eligible (`pending`) tasks in order: points ascending, then file order; never a `done-branch` task |
| `taskrail claim <ID>` / `taskrail release <ID>` | §6.1, §6.2 |
| `taskrail claims [--remote]` | Claims, each marked live or stale |
| `taskrail reserve-id` / `taskrail unreserve-id <ID>` | §6.3 |
| `taskrail new --epic E01 --kind bug --title … [--workspace]` | Allocate an ID and append a row; with `--workspace`, first create the task's branch and worktree from the base and append the row there |
| `taskrail done <ID>` / `taskrail discard <ID>` | Change status (see the rules below) |
| `taskrail reopen <ID> --reason …` | Move a done or discarded task back to pending |
| `taskrail review <ID> [--publish] [--type] [--scope] [--breaking]` | Hand a closed task off for review (§7.1) |
| `taskrail epic add [--own-file]` / `taskrail epic split <E##>` | Add an epic inline or in `todo/<id>-<slug>.md`; move an inline epic to its own file |
| `taskrail kind list` / `taskrail kind add <dir>` | Inspect resolved kinds; install a local kind |
| `taskrail upgrade` / `taskrail self upgrade` | Re-sync installed skills without touching overrides; update the CLI |

### 7.1 Review hand-off

Closing a task ends in a pull or merge request on whatever host the repository uses. `taskrail
review` owns the deterministic parts; the agent keeps the rebase and its conflicts.

1. `taskrail review <ID>` runs on the task branch, only once the task is done there. It fetches
   the mainline's remote (unless `fetch = false` or `--no-fetch`) and picks the rebase base: the
   backlog's `mainline` or its remote-tracking branch, whichever is further ahead, and whichever
   exists if only one does. While the task's single dependency is done only on its unmerged
   branch, the base is that branch instead, and `rebase.dependency` names it; the pull request
   still targets the mainline. Diverged mainlines exit 5. With `rebase = false` no base is chosen.
2. The agent rebases onto that base when `rebase.needed` is true, resolving backlog conflicts as
   the core skill prescribes, and runs `taskrail validate`.
3. `taskrail review <ID> --publish` refuses a branch that still lacks the base, pushes the task
   branch when `push_task_branch` is true — a plain push for a new remote branch, otherwise with
   `--force-with-lease` on the remote's current commit; a rejected push exits 4 — and returns the
   pull request title, description and link.

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

Write commands follow three rules:

- **Minimal diffs.** A status change rewrites one cell; `new` appends one row. Tables are never
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
consulted, so these commands never need the network.

**Done on its branch.** A task is `done-branch` when its row is `⬜` in the current checkout but
`✅` at the tip of its task branch — the local branch or `<remote>/<branch>` of its mainline's
remote — and `✅` on neither the local mainline nor `<remote>/<mainline>`. It takes precedence
over a claim: the work is finished and only waits to be merged, so `next` never offers it and
`claim` refuses it. "Merged" means `✅` on a mainline ref in every checkout, including a task
worktree whose own row already says `✅`. The backlog files at those tips are read with one
`git cat-file --batch` per backlog, only for tasks whose branch exists.

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
- `branches` — the task branch as a local branch and as `<remote>/<branch>`.
- `commits` — commits reachable from `HEAD`, local and remote-tracking branches (not tags or
  claim refs) whose subject names the task, newest first and capped at 10, with
  `commits_total` for the full count. Each carries the form it matched: `prefix` (the subject
  starts with the ID), `scope` (the ID in a Conventional Commits scope), `suffix` (a squash
  title ending in `(<ID>)`, optionally followed by `(#N)` or `(!N)`) or `branch` (the subject
  contains the task's branch name). A subject that mentions the ID anywhere else is ignored,
  since backlog maintenance names IDs constantly.

The history search is a single `git log --fixed-strings --grep=<ID>` over those refs, so its
cost grows with the history; `list` and `next` do not run it. Like `base`, it never fetches.

## 8. Skills

- `taskrail` — the core skill: the backlog model, how to call the CLI and read its exit codes,
  the procedure every kind shares (identify, inspect, workspace, claim, stages, scope,
  artifact, close, hand off) and the gate protocol. Executor skills refer to it instead of
  repeating it.
- `taskrail-bug`, `taskrail-chore`, `taskrail-feature`, `taskrail-spike` — one per core kind,
  containing only what happens inside each stage and what the artifact must hold.

Skills never compute paths: `taskrail show --json` returns the branch, worktree and artifact
paths rendered from the kind's templates.

Frontmatter is limited to `name`, `description`, `license`, `compatibility` and `metadata`, the
fields every supported agent accepts. Skills describe gates as "ask the human if you can,
otherwise stop and return the report to whoever invoked you".

### Integrations

An integration decides where skills are written and adds a short agent-specific section to
the core skill (at its `<!-- taskrail:harness -->` marker):

| Integration | Skills directory | Agent-specific notes |
|---|---|---|
| `claude` | `.claude/skills/` | ask with AskUserQuestion; create task worktrees with git rather than subagent isolation |
| `opencode` | `.opencode/skills/` | ask in plain text; a subagent's final message returns to its caller |

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
- **Managed files** — the wrapper, the skills, the optional workflow — are rewritten when they
  change, unless edited locally. `.taskrail/installed.json` records each managed file's digest;
  a file edited since, or one taskrail did not write, is skipped and reported. `--force`
  replaces it. A skill no longer wanted (for example after adding a second integration) is
  removed under the same rule.
- **Executor skills follow the kinds.** A shipped skill that a core kind names, in `skill` or a
  route, is an executor skill. It installs only when a kind the repository resolves — core,
  local and overrides, after `[kinds].allowed` (§5.2) — names it, so a local kind may pull in a
  shipped executor skill whose own kind is not allowed. Shipped skills no core kind names, such
  as the core `taskrail` skill, always install; skills taskrail does not ship are never written.
  The report notes the executor skills left out. While kind resolution reports errors, such as
  `kind-allowed-unknown`, nothing the kind filter would remove is removed, and a note says so:
  bad input never deletes a skill, and the next run after the fix removes what is not wanted.
- **Extras** — `--github-workflow` is remembered in the manifest; `--pre-commit` writes a
  marked block into this clone's git hook, keeping an existing shell hook's contents.

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
│   ├── skills/            # core and executor skills     ├ shipped as package data
│   └── integrations/      # agent-specific skill notes   ┘
├── examples/spec-kit/     # example repository-local `spec` kind
└── tests/
```

## 11. Phases

1. **v1** — format, config, `validate`, `list`/`next`/`show`, local and remote claims, ID
   allocation, epics, kind resolution, core kinds and skills, the Claude integration, `init`
   and the wrapper.
2. **v2** — autopilot orchestrator, import from existing backlogs, a git merge driver that
   resolves `✓` cell conflicts. The autopilot is designed in §12 and delivered by T017 (stacked
   base and `done-branch`), T027 (unreadable manifest), T029–T032 (the `autopilot` commands),
   then T024 (the skill), and trialled by T033 (§12.10).

## 12. Autopilot (planned)

Status: **planned, not implemented.** Accepted at the decide gate of the
[T007 spike](../../docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md), with the
human's decisions in its
[decision record](../../docs/autopilot/decisions/T007-design-taskrail-s-autopilot-from-existin.md).
Nothing in this section describes what taskrail does today; each part names the task that will
build it (§12.10). The evidence (E1–E7) and the full comparison of options stay in the spike.

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
| `autopilot start --count N [--kinds …]` | Exit 5, naming `[autopilot].enabled`, unless it is true; exit 2 without `--count`. Creates a run file (§12.4) with the target count, kinds and start time, and prints the run ID. |
| `autopilot next [--run R]` | Tasks to dispatch now, within free lanes, allowed kinds, group limits, claims, failed lanes and stacked bases. For each: `show`'s fields plus `base.commit`, the allocated resources and the decision-record path. Allocates resources atomically; claiming stays the lane's job. |
| `autopilot lane <ID> --run R [--handle H] [--group G] [--state running\|gate\|escalated\|failed] [--reason …]` | Records the agent-specific lane handle, a group membership assigned by judgement (§12.7) and the orchestrator's view of the lane. `failed` keeps the claim, so the task stays ineligible and its dependents stay blocked. |
| `autopilot status [--run R] [--fetch]` | Every run task with its state: `pending`, `running`, `gate`, `escalated`, `failed`, `done-branch`, `handed-off`, `done-merged`. Also each lane's handle; minutes since the last commit on its branch or the last change in its worktree, and `silent` past `silent_minutes`; files touched per branch, with overlaps between lanes; governing files touched; the next branch in the hand-off queue. Reads git and never fetches unless `--fetch`. |
| `autopilot merged <ID> [--cleanup]` | Runs `git fetch --prune`, then the merge detection of §12.8. Reports `merged`, `via` and the mainline commit, and marks the task `done-merged` in the run. With `--cleanup`, removes the worktree and deletes the local branch, refusing when the merge is unverified or the worktree is dirty. Lists stacked dependents with `git rebase --onto <base.onto> <recorded base.commit>`. |
| `autopilot notify --event escalation\|lane-done\|lane-failed --run R [--task ID]` | Runs `[autopilot].notify` when the event is in `notify_on` (§12.6). A failing notify command is reported and never blocks. |

The autopilot runs only when the human asks for it and gives a task count. The skill states
this in its prose, not only in frontmatter, so the rule holds on agents that ignore
invocation-control keys.

### 12.2 Installation and opt-in

- `init` and `upgrade` install `taskrail-autopilot` in **every** repository, with the other
  skills. No kind names it, so it is not an executor skill and the kind filter of §9 never
  leaves it out.
- A repository opts in with `[autopilot].enabled = true`. Until then `autopilot start` refuses
  with exit 5 and names the key, and the skill stops when it sees that refusal. The refusal is a
  CLI guarantee, so it holds on any agent.

The spike had recommended installing the skill only where the autopilot is enabled, through the
kind filter. The human chose to install it always, so every consumer receives the same skills.

### 12.3 Orchestrator and lanes

**The orchestrator** is the session the human talks to. It keeps a lane handle per task in the
run file, so a compacted or new orchestrator session can resume the lanes.

**A lane** is a sub-session, and its contract is the same on every agent. It:

- runs the `taskrail` skill and the task's executor skill for one task ID;
- creates its worktree with git and claims inside it (§8);
- ends its turn at every gate with the full gate report;
- is resumed with `continue <ID>` plus the answers;
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
integration notes (§8); agent definitions for pinning a lane model (`.claude/agents/`,
`.opencode/agents/`) are adapter packaging, deferred until a consumer needs them.

**Not a CLI that launches agents itself** (for example through `claude -p --resume` or
`opencode run --session`): unattended agent processes deny or skip permission prompts, which
lanes must not do, and answering gates needs an agent anyway.

### 12.4 State

- **Derived, never stored:**
  - `pending`;
  - `running`, a live claim;
  - `done-branch`, ✅ at the task branch tip but not on the mainline (T017);
  - `done-merged`, detected as in §12.8, or ✅ on the mainline.

  Any session sees them, and with `claim_remote` any machine.
- **Claims** (§6) remain the only lock, so dispatch needs no new locking for tasks or IDs.
  They gain two fields:
  - `base.commit`, the dependency tip a stacked branch started from, written at claim time by
    T017, so `rebase --onto` still works after the dependency is squash-merged;
  - `run`, the ID of the run that owns the lane.
- **Run file:** `$(git rev-parse --git-common-dir)/taskrail/runs/<run>.json`, next to the claims,
  local and never committed. It holds only what git cannot derive and what must survive the
  orchestrator's context:
  - the target count and kinds;
  - per task: the lane handle, the group, `gate`, `escalated` or `failed` with a reason, and
    the allocated resources;
  - the `handed-off` order;
  - the run-level decisions agreed so far.
- **Two orchestrator sessions** may run at once. They never dispatch the same task twice, since
  dispatch needs a claim, and `status` lists every run in the common directory, so each sees the
  other's lanes.

### 12.5 Decision records

- **Path:** one file per task at `decisions`, default
  `{artifacts}/autopilot/decisions/{id}-{slug}.md`, indexed at `decisions_index`, default
  `{artifacts}/autopilot/decisions/README.md` (columns Task, Title, Document). `autopilot next`
  and `status` render both paths.
- **Committed** on the task branch by the orchestrator, **only while the lane is stopped at a
  gate** and before resuming it, so the record travels with the squash-merged pull request.
- **Format:**
  - an introduction stating that each decision is recorded before it is given;
  - one `## <stage> gate` section per gate: a `Reviewed:` paragraph naming the artifact commit,
    the diff range, the re-run checks and the real-runtime verification, then a table
    `# | Question | Options | Decision | Reason`;
  - `## Conflict handling agreed for all lanes`, when a touch map was given;
  - `## rebase after …`, with a File / Conflict / Resolution table and the checks re-run
    afterwards;
  - `## escalated to the human` for escalated gates, naming who answered.
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

`autopilot status` computes the first two; the rest are judgement. T032's backlog description
also mentions flagging conflicts outside the known classes; whether a computed flag helps there
is settled at T032's own gate, and until then conflict classification stays judgement.

**Notification** is a command contract, not an agent hook: hooks such as Claude Code's
`Notification` are agent-specific and fire on the agent's own events. `autopilot notify` runs
`[autopilot].notify` for the events in `notify_on` (default `["escalation", "lane-done"]`), with
the message on stdin and `TASKRAIL_EVENT`, `TASKRAIL_RUN` and `TASKRAIL_TASK` in the environment.

**Supervision** is event-driven, since neither agent wakes on a timer. Whenever the orchestrator
wakes, it runs `autopilot status`. A lane silent past `silent_minutes` (default 20) is checked by
reading its worktree, and escalated if it is stuck. An agent that can wait on a condition may run
`status` periodically, but the design does not rely on it.

### 12.7 Resources

- **`max_lanes`** (default 3) caps the lanes running at once.
- **`[[autopilot.group]]`** has a `name`, a `limit`, and either `column` plus `match` (membership
  computed from the task's column) or neither (membership assigned by the orchestrator's
  judgement at dispatch, with `autopilot lane --group`). It generalises "at most one UI lane".
  `column` plus `match` is the column predicate of conditional stages (§5.4), parsed and matched
  by the same code.
- **`[[autopilot.resource]]`** has a `name` and `values`. Each lane gets one free value per
  resource, allocated under the common-directory lock and released when the lane ends, and passed
  to the lane in its brief as `TASKRAIL_RESOURCE_<NAME>` — a database name, a port, an emulator.
- **Shared services** are started by the orchestrator, never by lanes.
- **Sequential numbers:** task IDs go through `reserve-id` (§6.3), already safe across lanes.
  Other sequences stay out until a consumer needs them; a value pool covers small cases.

### 12.8 Merge follow-through

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
  sees nothing. After one `git fetch --prune`, in this order:
  1. the task branch head is an ancestor of the mainline;
  2. a commit on `git log --first-parent <mainline>` since the merge-base has the head's tree;
  3. the patch-id of `git diff <merge-base> <head>` equals that of a first-parent commit since the
     merge-base;
  4. `git merge-tree` of the head into the current mainline is a no-op.

  The ✅ row on the mainline and an `(ID)` pull request title confirm a merge but never prove it,
  since a row can be edited by hand.
- **Known conflict classes,** resolved without a human; anything else escalates:
  1. backlog rows, united by ID, with ✅ winning unless a `Reopens:` commit exists (the core skill
     today; T004's merge driver automates it later);
  2. appended index rows and changelog bullets: keep all;
  3. installed skill copies and `.taskrail/installed.json`: make the manifest valid first, merge
     the sources, then run `taskrail upgrade --force`.
- **Class 3 needs T027 first:** until `init` and `upgrade` stop on an unreadable manifest, a
  mistaken `init` silently drops the recorded integrations. T027 is not a backlog dependency of
  the autopilot tasks, but it should land before the skill relies on class 3.

### 12.9 Configuration

These keys join §4 when T029 implements them:

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
| T029 | feature | T017, T028 | `[autopilot]` configuration (§12.9), run files and `run` in the claim (§12.4), `autopilot start` with its exit-5 refusal (§12.2), `lane` and `status` (§12.1) |
| T030 | feature | T029 | `autopilot next`: kinds, group limits, resource pools (§12.7) |
| T031 | feature | T029 | `autopilot merged`: merge detection and cleanup (§12.8) |
| T032 | feature | T029 | `autopilot notify` and the escalation flags in `status` (§12.6) |
| T024 | feature | T030, T031, T032 | the `taskrail-autopilot` skill with Claude Code and OpenCode notes, installed in every repository (§12.2, §12.3, §12.5, §12.8) |
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
