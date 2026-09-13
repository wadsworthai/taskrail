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
| ⬜ | T005 | feature | 5   | —          | Import tasks from table-based backlogs without epics | Convert an existing backlog into epics and rows taskrail validates, keeping IDs, row order, prose and escaped pipes. |
| ✅ | T006 | feature | 2   | —          | Add a reopen command for tasks marked done by mistake | Move a task from done back to pending, leaving a trace of why. |
| ⬜ | T007 | spike   | 3   | —          | Design taskrail's autopilot from existing orchestrators | Turn [the reference behaviour](docs/research/autopilot-reference-behaviour.md) into an agnostic design and a task breakdown. |
| ⬜ | T012 | feature | 2   | T006       | Flag reopened tasks committed without a Reopens trailer | Have validate read git history and warn when a status went from done to pending without a Reopens: <ID> commit. |
| ⬜ | T014 | feature | 3   | T001       | Add an edit command for existing task rows | Fix T001 friction F4: change dependencies, points, title, description or custom columns without hand edits. |
| ⬜ | T024 | feature | 8   | T007, T017 | Implement taskrail's autopilot and install it with the other skills | An agent-agnostic orchestrator skill with CLI support, installed by init; each repository decides whether to use it. |

## E05 — Adoption

Done when: a consumer project runs its backlog through taskrail with its own kinds and orchestrator, and has retired its previous pipelines.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T017 | feature | 3   | —          | Branch a task from its single unmerged dependency | Stacked base for show, new --workspace and review: one dependency done only on its branch sets the base; two or more make the task ineligible. |
| ✅ | T018 | feature | 2   | —          | Restrict the task kinds a repository allows | Let config disable core kinds, so a repository whose rules name a closed set of kinds can reject the rest in validate. |
| ⬜ | T019 | feature | 3   | —          | Let the executor name or rename a task branch | For branches that depend on facts known only once work starts; claims and review must follow the renamed branch. |
| ⬜ | T020 | feature | 3   | —          | Run stages conditionally on a column or the executor's judgement | Declare stages that apply only when a column matches or when the executor judges them relevant, instead of duplicating kinds. |
| ⬜ | T021 | feature | 2   | —          | Map a repository's column names onto taskrail's columns | Column aliases in config, such as Size for Pts, so a backlog keeps its established headers. |
| ✅ | T022 | feature | 2   | —          | Use each mainline's own remote in review | Resolve the remote from branch.<mainline>.remote before [review].remote, for repositories whose mainlines live on different remotes. |
| ✅ | T023 | feature | 2   | —          | Report signs of prior work on a task in show | Informational only: an existing artifact, or commits whose subject names the task ID. |
| ⬜ | T025 | feature | 2   | T018       | Skip installing skills for kinds a repository does not allow | init and upgrade should not install executor skills for kinds outside [kinds].allowed. |
