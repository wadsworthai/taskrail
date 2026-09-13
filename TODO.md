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
| ⬜ | T001 | spike   | 3   | —          | Validate the taskrail skills by working a real task end to end | Run one task through every stage with an agent and record what the skills got wrong. |
| ⬜ | T002 | chore   | 1   | T001       | Tag and publish v0.1.0 | Set the package version, tag v0.1.0 and verify a clean uv tool install. |
| ⬜ | T003 | chore   | 2   | T002       | Install taskrail in a first consumer project | Run taskrail init in a real project and note any friction. |

## E02 — taskrail phase 2

Done when: backlog conflicts resolve automatically, existing backlogs import, and the orchestration model is decided.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ⬜ | T004 | feature | 5   | —          | Add a git merge driver for status cells and appended rows | Resolve the conflicts parallel task branches produce in backlog tables. |
| ⬜ | T005 | feature | 5   | —          | Import tasks from table-based backlogs without epics | Convert an existing single-table TODO into epics and rows taskrail validates. |
| ⬜ | T006 | feature | 2   | —          | Add a reopen command for tasks marked done by mistake | Move a task from done back to pending, leaving a trace of why. |
| ⬜ | T007 | spike   | 3   | —          | Define the autopilot orchestration model | Lanes, gate answering, escalation and decision records for running tasks in parallel. |
