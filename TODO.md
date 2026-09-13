# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | taskrail release | Publish a first version other repositories can install | —    |
| E02 | taskrail phase 2 | Parallel execution and migration from existing backlogs | —    |

## E01 — taskrail release

Done when: v0.1.0 is tagged and a repository installs it with uv and runs it through the wrapper.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | spike   | 3   | —          | Validate the taskrail skills by working a real task end to end | Run one task through every stage with an agent and record what the skills got wrong. |
| ⬜ | T002 | chore   | 1   | T001, T013, T015 | Tag and publish v0.1.0 | Set the package version, tag v0.1.0 and verify a clean uv tool install. |
| ⬜ | T003 | chore   | 2   | T002       | Install taskrail in a first consumer project | Run taskrail init in a real project and note any friction. |
| ⬜ | T013 | chore   | 2   | T001       | Clarify workspace base, stage commits and agent restart in the taskrail skills | Fix T001 frictions F1-F3: restart note after init, local mainline as base, meaning of commit = false; and creating a task on its own branch without moving the worktree. |
| ✅ | T015 | feature | 5   | —          | Hand closed tasks off for review with a merge request link | After closing: fetch, rebase onto the newer of the local or remote mainline, push, and print a PR/MR link with its title for any git host. |

## E02 — taskrail phase 2

Done when: backlog conflicts resolve automatically, existing backlogs import, and the orchestration model is decided.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T004 | feature | 5   | —          | Add a git merge driver for status cells and appended rows | Resolve the conflicts parallel task branches produce in backlog tables. |
| ⬜ | T005 | feature | 5   | —          | Import tasks from table-based backlogs without epics | Convert an existing single-table TODO into epics and rows taskrail validates. |
| ✅ | T006 | feature | 2   | —          | Add a reopen command for tasks marked done by mistake | Move a task from done back to pending, leaving a trace of why. |
| ⬜ | T007 | spike   | 3   | —          | Define the autopilot orchestration model | Lanes, gate answering, escalation and decision records for running tasks in parallel. |
| ⬜ | T012 | feature | 2   | T006       | Flag reopened tasks committed without a Reopens trailer | Have validate read git history and warn when a status went from done to pending without a Reopens: <ID> commit. |
| ⬜ | T014 | feature | 3   | T001       | Add an edit command for existing task rows | Fix T001 friction F4: change dependencies, points, title, description or custom columns without hand edits. |
