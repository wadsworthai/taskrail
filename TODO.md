# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
| E01 | taskrail release | Publish a first version other repositories can install | —    |
| E02 | taskrail phase 2 | Parallel execution and migration from existing backlogs | —    |
| E05 | Adoption | Let a consumer project replace its own task system with taskrail | —    |
| E06 | Repository tooling | How this repository runs its own backlog with taskrail while it is worked on | —    |

## E01 — taskrail release

Done when: v0.2.0 is tagged and a repository installs it with uv and runs it through the wrapper.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T001 | spike   | 3   | —          | Validate the taskrail skills by working a real task end to end | Run one task through every stage with an agent and record what the skills got wrong. |
| ✅ | T002 | chore   | 1   | T001, T013, T015 | Tag and publish v0.1.0 | Set the package version, tag v0.1.0 and verify a clean uv tool install. |
| ⬜ | T003 | chore   | 2   | T002       | Install taskrail in a first consumer project | Run taskrail init in a real project and note any friction. |
| ✅ | T013 | chore   | 2   | T001       | Clarify workspace base, stage commits and agent restart in the taskrail skills | Fix T001 frictions F1-F3: restart note after init, local mainline as base, meaning of commit = false; and creating a task on its own branch without moving the worktree. |
| ✅ | T015 | feature | 5   | —          | Hand closed tasks off for review with a merge request link | After closing: fetch, rebase onto the newer of the local or remote mainline, push, and print a PR/MR link with its title for any git host. |
| ✅ | T016 | chore   | 1   | T002       | Bump taskrail on main to 0.2.0.dev0 after the 0.1.0 tag | Keep builds from main from claiming to be the released 0.1.0. |
| ✅ | T069 | chore   | 1   | —          | Warn in the README that taskrail is experimental and AI-developed | Add a notice near the top of README.md stating that taskrail is experimental and is developed with AI agents. |
| ✅ | T076 | chore   | —   | —          | Name wadsworthai/taskrail as the canonical repository in the CLI, skills and docs | SOURCE_URL, the wrapper's uvx fallback, self upgrade, the installed skills' source, README, CHANGELOG and tests name github.com/alexkander/taskrail, which is not reachable; point them at github.com/wadsworthai/taskrail, and create no v0.1.0 tag in this repository. |
| ✅ | T077 | chore   | —   | —          | Release v0.2.0 from the canonical repository | Set the version to 0.2.0, lock, and turn Unreleased into 0.2.0 in CHANGELOG.md; the tag follows the merge, and T078 records the install from it and bumps main.                                                                |
| ⬜ | T078 | chore   | —   | T077       | Bump main to 0.3.0.dev0 after the v0.2.0 tag | Once v0.2.0 is pushed on T077's squash commit, record the tag and a clean install from wadsworthai/taskrail@v0.2.0, then set 0.3.0.dev0 and lock; stop at scope if the tag does not exist. |

## E02 — taskrail phase 2

Done when: backlog conflicts resolve automatically, existing backlogs import, and the orchestration model is decided.

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T004 | feature | 5   | —          | Add a git merge driver for status cells and appended rows | Resolve the conflicts parallel task branches produce in backlog tables. |
| ✅ | T005 | feature | 5   | —          | Import tasks from table-based backlogs without epics | Convert an existing backlog into epics and rows taskrail validates, keeping IDs, row order, prose and escaped pipes. |
| ✅ | T006 | feature | 2   | —          | Add a reopen command for tasks marked done by mistake | Move a task from done back to pending, leaving a trace of why. |
| ✅ | T007 | spike   | 3   | —          | Design taskrail's autopilot from existing orchestrators | Turn [the reference behaviour](docs/research/autopilot-reference-behaviour.md) into an agnostic design and a task breakdown. |
| ✅ | T012 | feature | 2   | T006       | Flag reopened tasks committed without a Reopens trailer | Have validate read git history and warn when a status went from done to pending without a Reopens: <ID> commit. |
| ✅ | T014 | feature | 3   | T001       | Add an edit command for existing task rows | Fix T001 friction F4: change dependencies, points, title, description or custom columns without hand edits. |
| ✅ | T024 | feature | 5   | T030, T031, T032 | Write the taskrail-autopilot skill with Claude Code and OpenCode notes | Orchestrator procedure, lane brief, gate criteria, decision records and conflict classes per [T007](docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md); init and upgrade install it in every repository, and it stops when autopilot start refuses. |
| ✅ | T026 | bug     | 1   | —          | Refuse --column for core columns in new | new --column ID=T9 exits 0 and silently ignores the value; refuse every core column and name the flag to use. |
| ✅ | T027 | bug     | 1   | —          | Stop init and upgrade on an unreadable installed.json | A manifest with conflict markers makes upgrade report it missing (exit 3) and init silently reset its integrations, extras and digests; stop with exit 2 naming the file (T007 E3). |
| ✅ | T028 | chore   | 2   | —          | Write the autopilot design into DESIGN.md | Move the design accepted in [T007](docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md) into DESIGN.md, so the autopilot tasks build from it. |
| ✅ | T029 | feature | 5   | T017, T028 | Add the autopilot configuration, runs, and the start, lane and status commands | [autopilot] table, local run files beside claims, derived task states; autopilot start refuses with exit 5 until [autopilot].enabled is true. |
| ✅ | T030 | feature | 3   | T029       | Dispatch autopilot lanes with autopilot next | Tasks to start now within max_lanes, allowed kinds, group limits, claims and stacked bases, with resource pool values allocated per lane. |
| ✅ | T031 | feature | 3   | T029       | Detect squash merges by content and follow through with autopilot merged | Ancestor, tree, patch-id, then merge-tree after fetch --prune; --cleanup removes branch and worktree; list rebase --onto for stacked dependents. |
| ✅ | T032 | feature | 2   | T029       | Add autopilot notify and the escalation flags in autopilot status | Run the configured notify command per event; flag governing files touched, escalate_gates and conflicts outside the known classes. |
| ✅ | T033 | spike   | 2   | T024       | Trial the autopilot on a real backlog with each supported agent | Run the autopilot end to end on Claude Code and OpenCode and record what the design got wrong. |
| ✅ | T035 | feature | 2   | T020       | Match routes through the shared column predicate | Move [[route]] matching onto predicates.py and decide whether route values become case-insensitive (a behaviour change). |
| ✅ | T036 | feature | 3   | T019       | Mirror branch records to a remote ref | Push each task's branch record next to refs/taskrail/claims, so another clone resolves a renamed branch in show, review and done-branch detection. |
| ✅ | T037 | bug     | 1   | —          | Delete remote claims with a lease on their recorded commit | release --force and done exit 2 when claim_remote is set: _delete_remote leases without an expected commit, so git finds no tracking ref and rejects the delete. |
| ✅ | T038 | chore   | 1   | —          | Create task branches without tracking the mainline | git worktree add -b <branch> origin/<mainline> sets the task branch to track the mainline, so a plain git push can target it; branch with --no-track in the skill and in new --workspace. |
| ✅ | T039 | chore   | 1   | —          | Fetch full history in the generated GitHub workflow | The workflow init --github-workflow writes checks out one commit, so validate's reopen history check (T012) examines nothing; set fetch-depth: 0. |
| ✅ | T040 | feature | 3   | T004       | Merge appended changelog bullets without duplicating moved ones | Resolve the rest of conflict class 2 (DESIGN §12.8): bullets both sides append to a changelog, without duplicating a bullet one side moved; follows T004's merge driver. |
| ✅ | T047 | feature | 3   | —          | Keep a stacked task's fork point after done | Record base.commit in the run file at claim and use it in autopilot merged before merge-base, so a dependency rebased at hand-off still yields a rebase --onto command; verified by pytest with a scripted git fixture (T033 F1). |
| ✅ | T048 | feature | 2   | —          | Add autopilot close to abandon a run | Release a run's dispatches and resources and hide it from next and status, so a stale orchestrator session leaves nothing holding lanes; verified by pytest on fixture run files (T033 F7). |
| ✅ | T049 | feature | 1   | —          | Stop flagging governing paths once a task is done on its branch | status keeps escalation governing after approval, through done-branch and handed-off; drop it as escalate_gate is dropped; verified by pytest with a fixture repository (T033 F9). |
| ✅ | T050 | feature | 1   | —          | Accept --gate close for the stop after done | autopilot lane --gate close exits 2 because close is not a stage, although the skill reviews the stop after done as a gate; verified by pytest (T033 F10). |
| ✅ | T051 | feature | 2   | —          | Label overlaps in known conflict-class files | Separate backlog, changelog and index files in autopilot status overlaps, so a real overlap between lanes is not buried; verified by pytest with scripted worktrees (T033 F12). |
| ✅ | T052 | feature | 3   | —          | Add taskrail checks for a task and a Claude Code note on command shape | Run a task's configured checks in its worktree with its lane resources as one allowlistable command, and document single commands without cd chains; verified by pytest and a test asserting the note in the installed copy (T033 F11). |
| ✅ | T053 | bug     | 1   | —          | Order the autopilot hand-off queue by completion, not branch tip time | Rebases and decision-record commits move a task to the back of handoff.next; order by the done commit; verified by pytest with a scripted git fixture that rebases a waiting branch (T033 F8). |
| ✅ | T054 | bug     | 1   | —          | Keep a closing lane from reading as pending between done and its commit | status showed a closing lane as pending, so next could offer it again after the claim grace; start from a failing pytest that scripts done without its commit, then fix (T033 F13). |
| ✅ | T055 | chore   | 2   | —          | Fix the autopilot skill text found wrong in the T033 trial | Hand-off message with branch, title and body; refill on done-branch; IDs unique across lanes; dispatch expiry; resuming a run from a new session; verified by tests asserting each rule in the skill sources and installed copies (T033 F2, F4-F7). |
| ✅ | T056 | chore   | 1   | —          | Add an OpenCode note on escalations during blocking lane batches | End the turn with the question instead of starting another blocking batch, record handles when a batch returns, check silent lanes between batches; verified by a test asserting the rules in the installed note (T033 F3). |
| ⬜ | T057 | spike   | 2   | —          | Check autopilot compaction and old-lane messaging with a scripted probe | A small fixture and a bounded non-interactive script, minutes not hours, no human terminals and no change to agent settings; what cannot be scripted (compaction, OpenCode on a Claude model, messaging a previous session's lane) is stated as a limit (T033). |
| ✅ | T059 | feature | 2   | —          | Record an approved governing edit so autopilot status stops flagging it | After the human approves a governing edit, status still flags governing at later gates until done-branch; record the approved paths with their blob IDs so only a later change flags again; verified by pytest with a fixture repository (T033 F9, T049). |
| ✅ | T061 | feature | —   | —          | Separate the documents the orchestrator reads first from the paths that escalate | Add an [autopilot] key for the documents the orchestrator reads first to answer gates, read by the taskrail-autopilot skill, leaving governing for escalation only; verified by pytest on config loading, autopilot status output, and the skill source and installed copies. |
| ✅ | T062 | bug     | —   | —          | Treat a task discarded on its unmerged branch as closed in status and next | A ❌ committed on a task branch reads as pending to autopilot status, autopilot next and next until merged, since done-branch counts only ✅ (T054 impact); verify with a pytest that discards on a branch, commits, and asserts the task is neither pending nor offered. |
| ✅ | T063 | chore   | —   | T052, T055 | Name taskrail checks in the lane brief and the autopilot skill's re-run steps | Replace the lane brief's check commands run from the worktree root, and the autopilot skill's re-run-the-checks steps, with taskrail checks <ID>; verified by a test_autopilot_skill.py assertion on the shipped lane brief and skill text (T052 D7). |
| ✅ | T064 | bug     | —   | —          | Skip a task merged on the remote mainline but not pulled in autopilot next | autopilot next offers a task whose ✅ or ❌ is on the remote mainline but not in the checkout, since its candidates come from query.eligible (T062 impact); verify with a pytest that closes a task on its branch with done and with discard, pushes it to origin/main without pulling, and asserts autopilot next does not offer it. |
| ✅ | T065 | feature | —   | T053       | Hand off a branch whose task was discarded on it | autopilot status leaves discarded-branch out of the hand-off queue and autopilot lane --state handed-off refuses it (T062 impact); queue it by its discard commit, accept handed-off, and report its touched files without a governing flag; verified by pytest that discards on a branch and hands it off. |
| ✅ | T066 | feature | —   | —          | Pass chosen resource values to taskrail checks for a lane whose values were released | Add `taskrail checks <ID> --resource NAME=VALUE` so the orchestrator's hand-off and after-merge re-runs pass values no lane in use holds without an environment prefix; verified by a test_checks.py test. |
| ✅ | T067 | feature | —   | T065       | Detect and clean up a merged branch whose task was discarded on it | autopilot merged needs done_at_head and recorded_merges feed done_on_mainline whatever the row says (T065 out of scope); prove the merge of a discarded branch without it reading done-merged, and let --cleanup remove its worktree and branch; verified by pytest that discards on a branch, squash-merges it and runs merged --cleanup. |
| ✅ | T071 | feature | —   | —          | Run the autopilot on named tasks, including ones whose workspace new --workspace prepared | autopilot start takes --tasks with IDs and dispatches only those; next and the lane brief treat a branch that taskrail new --workspace created, holding only the row's commit, as a prepared workspace rather than prior work. |
| ✅ | T072 | bug     | —   | —          | Report a task's worktree path in one form whichever checkout runs the command | query.worktree_path returns a path relative to the root for a worktree under it or not yet created, but an absolute one when the command runs inside that worktree, as autopilot next --json showed at T071's plan gate; report one form and verify with a pytest on both cases. |
| ✅ | T073 | bug     | —   | —          | Create a task worktree under the main checkout when new or workspace runs inside another worktree | new --workspace and workspace run inside a task worktree place the new worktree below that worktree instead of under the main checkout's worktree_dir, where show reports it (found in T072). |
| ✅ | T074 | bug     | —   | —          | Refuse merged --cleanup for a worktree that contains other registered worktrees | autopilot merged --cleanup removes a task worktree whose ignored worktree_dir holds other worktrees, deleting their uncommitted work (found in T073). |
| ✅ | T075 | bug     | —   | —          | Report and create task worktrees outside the bare directory of a bare repository | In a bare clone with worktrees, git worktree list names the bare directory first, so show reads worktree paths against it and new --workspace places worktrees inside it (found in T073). |

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
| ✅ | T070 | feature | —   | —          | Detect a task whose row is missing from its base and carry the row into its workspace | show, next and autopilot next report a row absent from base.onto (such as one left uncommitted on the mainline checkout); a command moves that row, with its ID, into the task's new branch and worktree; new without --workspace on a mainline warns. |

## E06 — Repository tooling

Done when: this repository's own backlog runs through the taskrail autopilot

| ✓  | ID   | Kind    | Pts | Depends On | Title                          | Description                    |
|----|------|---------|-----|------------|--------------------------------|--------------------------------|
| ✅ | T058 | chore   | 1   | —          | Enable the autopilot in this repository | Add an [autopilot] block to .taskrail/config.toml with CLAUDE.md and DESIGN.md as governing documents and spike decide gates escalated; verified by taskrail autopilot start --count exiting 0 against a scratch clone and by validate. |
| ✅ | T060 | chore   | 1   | —          | Remove DESIGN.md and CLAUDE.md from the autopilot's governing paths | Empty [autopilot].governing in this repository's config so lane edits to DESIGN.md and CLAUDE.md are decided by the orchestrator and reviewed by the human in the pull request; keep both documents named as what the orchestrator reads first; verified by taskrail validate and autopilot status loading the empty key. |
