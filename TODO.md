# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | taskrail release | Publish a first version other repositories can install | —    |
| E02 | taskrail phase 2 | Parallel execution and migration from existing backlogs | —    |
| E05 | Adoption | Let a consumer project replace its own task system with taskrail | —    |

## E01 — taskrail release

Done when: v0.1.0 is tagged and a repository installs it with uv and runs it through the wrapper.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | spike   | 3   | —          | Validate the taskrail skills by working a real task end to end | Run one task through every stage with an agent and record what the skills got wrong. |
| ✅ | T002 | chore   | 1   | T001, T013, T015 | Tag and publish v0.1.0 | Set the package version, tag v0.1.0 and verify a clean uv tool install. |
| ⬜ | T003 | chore   | 2   | T002       | Install taskrail in a first consumer project | Run taskrail init in a real project and note any friction. |
| ✅ | T013 | chore   | 2   | T001       | Clarify workspace base, stage commits and agent restart in the taskrail skills | Fix T001 frictions F1-F3: restart note after init, local mainline as base, meaning of commit = false; and creating a task on its own branch without moving the worktree. |
| ✅ | T015 | feature | 5   | —          | Hand closed tasks off for review with a merge request link | After closing: fetch, rebase onto the newer of the local or remote mainline, push, and print a PR/MR link with its title for any git host. |
| ✅ | T016 | chore   | 1   | T002       | Bump taskrail on main to 0.2.0.dev0 after the 0.1.0 tag | Keep builds from main from claiming to be the released 0.1.0. |

## E02 — taskrail phase 2

Done when: backlog conflicts resolve automatically, existing backlogs import, and the orchestration model is decided.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T004 | feature | 5   | —          | Add a git merge driver for status cells and appended rows | Resolve the conflicts parallel task branches produce in backlog tables. |
| ✅ | T005 | feature | 5   | —          | Import tasks from table-based backlogs without epics | Convert an existing backlog into epics and rows taskrail validates, keeping IDs, row order, prose and escaped pipes. |
| ✅ | T006 | feature | 2   | —          | Add a reopen command for tasks marked done by mistake | Move a task from done back to pending, leaving a trace of why. |
| ✅ | T007 | spike   | 3   | —          | Design taskrail's autopilot from existing orchestrators | Turn [the reference behaviour](docs/research/autopilot-reference-behaviour.md) into an agnostic design and a task breakdown. |
| ⬜ | T012 | feature | 2   | T006       | Flag reopened tasks committed without a Reopens trailer | Have validate read git history and warn when a status went from done to pending without a Reopens: <ID> commit. |
| ⬜ | T014 | feature | 3   | T001       | Add an edit command for existing task rows | Fix T001 friction F4: change dependencies, points, title, description or custom columns without hand edits. |
| ⬜ | T024 | feature | 5   | T030, T031, T032 | Write the taskrail-autopilot skill with Claude Code and OpenCode notes | Orchestrator procedure, lane brief, gate criteria, decision records and conflict classes per [T007](docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md); init and upgrade install it in every repository, and it stops when autopilot start refuses. |
| ✅ | T026 | bug     | 1   | —          | Refuse --column for core columns in new | new --column ID=T9 exits 0 and silently ignores the value; refuse every core column and name the flag to use. |
| ✅ | T027 | bug     | 1   | —          | Stop init and upgrade on an unreadable installed.json | A manifest with conflict markers makes upgrade report it missing (exit 3) and init silently reset its integrations, extras and digests; stop with exit 2 naming the file (T007 E3). |
| ✅ | T028 | chore   | 2   | —          | Write the autopilot design into DESIGN.md | Move the design accepted in [T007](docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md) into DESIGN.md, so the autopilot tasks build from it. |
| ✅ | T029 | feature | 5   | T017, T028 | Add the autopilot configuration, runs, and the start, lane and status commands | [autopilot] table, local run files beside claims, derived task states; autopilot start refuses with exit 5 until [autopilot].enabled is true. |
| ✅ | T030 | feature | 3   | T029       | Dispatch autopilot lanes with autopilot next | Tasks to start now within max_lanes, allowed kinds, group limits, claims and stacked bases, with resource pool values allocated per lane. |
| ✅ | T031 | feature | 3   | T029       | Detect squash merges by content and follow through with autopilot merged | Ancestor, tree, patch-id, then merge-tree after fetch --prune; --cleanup removes branch and worktree; list rebase --onto for stacked dependents. |
| ✅ | T032 | feature | 2   | T029       | Add autopilot notify and the escalation flags in autopilot status | Run the configured notify command per event; flag governing files touched, escalate_gates and conflicts outside the known classes. |
| ⬜ | T033 | spike   | 2   | T024       | Trial the autopilot on a real backlog with each supported agent | Run the autopilot end to end on Claude Code and OpenCode and record what the design got wrong. |
| ✅ | T035 | feature | 2   | T020       | Match routes through the shared column predicate | Move [[route]] matching onto predicates.py and decide whether route values become case-insensitive (a behaviour change). |
| ✅ | T036 | feature | 3   | T019       | Mirror branch records to a remote ref | Push each task's branch record next to refs/taskrail/claims, so another clone resolves a renamed branch in show, review and done-branch detection. |
| ✅ | T037 | bug     | 1   | —          | Delete remote claims with a lease on their recorded commit | release --force and done exit 2 when claim_remote is set: _delete_remote leases without an expected commit, so git finds no tracking ref and rejects the delete. |

## E05 — Adoption

Done when: a consumer project runs its backlog through taskrail with its own kinds and orchestrator, and has retired its previous pipelines.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T017 | feature | 5   | —          | Branch a task from its single unmerged dependency | Stacked base for show, new --workspace and review: one dependency done only on its branch sets the base; two or more make the task ineligible. Add a done-branch state that next never offers, and record the base commit in the claim. |
| ✅ | T018 | feature | 2   | —          | Restrict the task kinds a repository allows | Let config disable core kinds, so a repository whose rules name a closed set of kinds can reject the rest in validate. |
| ✅ | T019 | feature | 3   | —          | Let the executor name or rename a task branch | For branches that depend on facts known only once work starts; claims and review must follow the renamed branch. |
| ✅ | T020 | feature | 3   | —          | Run stages conditionally on a column or the executor's judgement | Declare stages that apply only when a column matches or when the executor judges them relevant, instead of duplicating kinds. |
| ✅ | T021 | feature | 2   | —          | Map a repository's column names onto taskrail's columns | Column aliases in config, such as Size for Pts, so a backlog keeps its established headers. |
| ✅ | T022 | feature | 2   | —          | Use each mainline's own remote in review | Resolve the remote from branch.<mainline>.remote before [review].remote, for repositories whose mainlines live on different remotes. |
| ✅ | T023 | feature | 2   | —          | Report signs of prior work on a task in show | Informational only: an existing artifact, or commits whose subject names the task ID. |
| ✅ | T025 | feature | 2   | T018       | Skip installing skills for kinds a repository does not allow | init and upgrade should not install executor skills for kinds outside [kinds].allowed. |
| ✅ | T034 | bug     | 1   | T017       | Clear done-branch for a task reopened on its mainline | A stale task branch with ✅ hides a task reopened on the mainline; a mainline Reopens: <ID> commit the branch lacks should clear the state. |
