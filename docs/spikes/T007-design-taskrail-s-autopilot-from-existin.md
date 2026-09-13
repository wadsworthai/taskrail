# T007 — Design taskrail's autopilot from existing orchestrators

**Verdict: build the autopilot as one judgement skill (`taskrail-autopilot`) over a thin
`taskrail autopilot` command group. Keep the claims as the lock, derive task state from git, and
keep what git cannot hold in a local run file. Lanes are background subagents on Claude Code
and task-tool subagents on OpenCode. T024 becomes the skill task, after T017 and five smaller
CLI and documentation tasks.**

**Gate outcome:** the human accepted this design at the decide gate
([decision record](../autopilot/decisions/T007-design-taskrail-s-autopilot-from-existin.md)).
They overrode one recommendation: the autopilot skill is installed in every consumer repository,
and `taskrail autopilot start` refuses until the repository enables it (design point 1,
*Installation*).

## Question

What is the smallest agent-agnostic design for a taskrail autopilot — a skill plus CLI support,
installed with the other skills and opt-in per repository — that covers the
[reference behaviour](../research/autopilot-reference-behaviour.md) of two existing
orchestrators and the lessons of this repository's first autopilot run (records under
[`docs/autopilot/decisions/`](../autopilot/decisions/README.md)), and which tasks deliver it?

It settles nine points: (1) the split between skill text and CLI; (2) how orchestrator and
lanes map onto Claude Code and OpenCode; (3) where session state lives; (4) decision records;
(5) escalation and notification; (6) resource arbitration; (7) merge follow-through;
(8) configuration keys; (9) the task breakdown, including T017, T019 and T020.

## Approach

Agreed at the frame gate ([decision record](../autopilot/decisions/T007-design-taskrail-s-autopilot-from-existin.md)):

- A coverage matrix from the reference behaviour, the four first-run decision records, the
  lessons of that run, `DESIGN.md` and the CLI sources at `ee38f5b`.
- Measurements of the current CLI in throwaway repositories under `/tmp`.
- Squash-merge detection tried against this repository's real pull requests #8–#11, read-only,
  in a temporary clone.
- Agent capabilities from primary documentation first, plus a handful of minimal runs in a
  temporary directory, never with a flag that skips permission prompts.

## Limits

- Time box: 3 points. No production code, no change to `DESIGN.md` or the skills.
- No live autopilot run exercised this design; the first run's records stand in for one.
- Claude Code (2.1.270) and OpenCode (1.15.13) only. **No Claude Code run was spent**: its
  subagent behaviour is documented, and this spike itself ran as a resumed background subagent.
  One OpenCode run verified subagent resumption. OpenCode's background subagents, an
  experimental flag, were **not** run.
- No host APIs: follow-through starts from the human saying a branch is merged, verified with
  git.

## Evidence

Versions: taskrail `0.2.0.dev0` from this branch's source (`ee38f5b` plus this spike's commits),
git 2.55.0, uv 0.11.16, Python 3.14.7, Claude Code 2.1.270, OpenCode 1.15.13. Commands are in
*How to reproduce*.

### E1 — A task finished on its unmerged branch looks pending again from the mainline

Throwaway repository with T001 (2 pts), T002 (1 pt, depends on T001), T003 (3 pts) and T004
(1 pt, depends on T001 and T003). A lane claimed T001 in its worktree, ran `taskrail done T001`
and committed. From the main checkout:

```
$ taskrail next                     # before the lane
T001   ⬜ pending   feature   2pt  E01   Base task
T003   ⬜ pending   bug       3pt  E01   Independent
$ taskrail next                     # after `done T001` was committed on T001's branch
T001   ⬜ pending   feature   2pt  E01   Base task
T003   ⬜ pending   bug       3pt  E01   Independent
$ taskrail claims
no claims
$ taskrail show T001 --json   → state pending, claim None,
  prior_work {'artifact': [], 'branches': ['T001-base-task'], 'commits': [], 'commits_total': 0}
$ taskrail show T002 | head -5
  ... state blocked ... blocked by T001
$ (cd .worktrees/T001-base-task && taskrail next)
T002   ⬜ pending   feature   1pt  E01   Depends on base  ← T001
T003   ⬜ pending   bug       3pt  E01   Independent
```

`done` releases the claim, and state is read from the current checkout's backlog, so an
orchestrator on the mainline would dispatch T001 a second time. Only `prior_work.branches`
hints at it. The reference `done-branch` state does not exist today. This is the gap T017 must
close anyway, since a stacked base needs "done only on its branch".

### E2 — Claims and ID reservation already hold across lanes

With T003 claimed from its own worktree, `next` in the main checkout listed only T001 and
`claims` showed `T003 … T003-independent live`: claims live in the git common directory. Two
`reserve-id` calls started concurrently from two worktrees returned `T005` and `T006`, and a
third returned `T007`: no collision. The autopilot needs no new locking for tasks or IDs.

### E3 — `upgrade` and `init` on a manifest with conflict markers

Throwaway repository: `init --integration claude`, then branch `a` ran `init --integration
opencode` and branch `b` ran `init --github-workflow`; merging `a` into `b` conflicted in
`.taskrail/installed.json`.

```
$ taskrail upgrade           → taskrail: .taskrail/installed.json not found; run `taskrail init` first   (exit 3)
$ taskrail upgrade --force   → same message, exit 3
$ taskrail init              → note: no agent integration installed; … 3 file(s) already up to date   (exit 0)
$ cat .taskrail/installed.json
{ "version": "v0.2.0", "integrations": [], "extras": {}, "files": { ".taskrail/bin/taskrail": "3d28…" } }
```

`read_manifest` treats unparseable JSON as missing
(`except (FileNotFoundError, json.JSONDecodeError): return {}` in `install.py`). `upgrade`
refuses with a misleading message. `init` exits 0 and **silently overwrites** the manifest,
dropping both integrations, the `github_workflow` extra and every skill digest. No skill was
deleted in this run: with no recorded digests there is nothing to remove, and existing skills
are skipped as "not written by taskrail". The first run's fear, that `upgrade` would delete
skills, was not reproduced. The real defect is silent loss of the manifest's state and a wrong
exit code. Either command should stop with exit 2, naming the unreadable manifest.

### E4 — Squash merges can be detected by content

Temporary clone of `origin` at `ee38f5b`, with `refs/pull/{8,9,10,11}/head` fetched. Squash
commits on `main`: #8 `20b624f` (T018), #9 `e85bcff` (T023), #10 `fa05757` (T022), #11
`ee38f5b` (T021).

| PR | task | head is ancestor of main | `git cherry` +/− | head tree = squash tree | `merge-tree` head into current main is a no-op | row ✅ on main | `(Txxx) (#` title on main |
|---|---|---|---|---|---|---|---|
| 8 | T018 | no | 7/0 | yes | no | ✅ | 20b624f |
| 9 | T023 | no | 7/0 | yes | no | ✅ | e85bcff |
| 10 | T022 | no | 7/0 | yes | no | ✅ | fa05757 |
| 11 | T021 | no | 8/0 | yes | yes | ✅ | ee38f5b |

- **Ancestry and `git cherry` detect nothing** after a squash, as expected.
- **Tree match** — some commit on `git log --first-parent origin/main` has the head's tree —
  found all four, and PRs #2–#7 too (`0e68977`, `024e5e7`, `d3d308e`, `2f8122d`, `411d1e0`,
  `ae6189e`). PR #1, merged with a merge commit, is found both by ancestry and by tree (`f76164b`).
- **`merge-tree` against the current mainline** fails for #8–#10 once later merges touched the
  same append-only files: conflicts in `TODO.md`, `docs/autopilot/decisions/README.md`,
  `docs/features/README.md` and `CHANGELOG.md`. Against the mainline it was
  squashed into (`20b624f`), #8 is contained.
- **Patch-id** of `git diff $(git merge-base head main) head` equals the squash commit's
  patch-id for all four (`5903e3f27000`, `8e7641ba968d`, `72d4b9a891b6`, `8ef75a0ff2ba`).
- **Moved mainline, simulated:** squashing #8 onto `ae6189e` plus an unrelated commit leaves no
  tree match, but patch-id is still equal and `merge-tree` is a no-op. When the intervening
  commit touched `CHANGELOG.md` too, the squash itself conflicts, so a host could not have
  merged it without a rebase.
- **Negative controls:** this unmerged T007 branch is not contained. #8's head plus one extra
  commit has no tree match and `merge-tree` is not a no-op.
- Cost: `merge-tree` about 4 ms. Every check is a local git call after one `fetch --prune`.

Reliable order: ancestor → tree match on the first-parent mainline since the merge-base →
patch-id equal to a first-parent commit since the merge-base → `merge-tree` no-op. The ✅ row
and the `(ID)` title confirm but never prove, since a row can be edited by hand.

### E5 — Claude Code subagents (documentation, and this spike's own run)

From [subagents](https://code.claude.com/docs/en/sub-agents),
[hooks](https://code.claude.com/docs/en/hooks) and
[headless](https://code.claude.com/docs/en/headless):

- Background subagents run concurrently; "a background subagent's results reach Claude as a
  completion notification in a later turn". Permission prompts from background subagents
  surface in the main session.
- Resume: `SendMessage` with the agent's ID or name; "resumed subagents retain their full
  conversation history". **Observed here:** this lane stopped at its frame gate and was resumed
  with "continue T007" plus answers, with its context intact.
- `AskUserQuestion` is removed from every subagent, so a lane must relay gates.
- Model per lane: an invocation `model` parameter, or `model` in an agent definition. Default
  limit: 20 concurrent subagents; nesting up to 3 levels.
- `isolation: worktree` picks its own branch and path, which is why taskrail already says to
  create worktrees with git.
- Hooks: `SubagentStart`, `SubagentStop` (with `agent_id`, `agent_type`,
  `last_assistant_message`) and `Notification`. **No hook fires on a timer.**
- Headless `claude -p … --output-format json` returns `session_id`, and `--resume <id>`
  continues it, but a `-p` run with no permission host denies any prompt. Not a fit for lanes
  that must not skip permissions.

### E6 — OpenCode subagents (documentation, binary, one run)

- [Agents](https://opencode.ai/docs/agents/): subagents are started by the primary agent
  through the task tool, or by `@mention`, and each gets a child session. Per-agent `model`.
  Permissions are `ask`/`allow`/`deny`.
- Task tool schema in the installed 1.15.13 binary: `description`, `prompt`, `subagent_type`,
  and `task_id` ("you can pass a prior task_id and the task will continue the same subagent
  session as before instead of creating a fresh one"). A second schema adds `background`
  ("Run the agent in the background. You will be notified when it completes."), next to an
  `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS` string. Background is experimental and was not
  run. By default a task call blocks until the subagent finishes: parallel lanes are several
  task calls in one message, and the orchestrator continues only when all of them return.
- `opencode debug agent general`: the built-in `general` subagent has
  `{"permission": "question", "action": "deny"}`, so a lane cannot ask the human and must relay
  gates.
- **Run 1** (`opencode run --format json "…"` in `/tmp`): exit 124 after 240 s with no output
  and no prompt. `opencode run` waits on an open stdin. Recorded, not retried as is.
- **Run 2** (same prompt, stdin from `/dev/null`): exit 0.
  ```
  TOOL task {"description": "remember a word", "prompt": "Remember the word PLUM. Reply only READY. Use no tools.", "subagent_type": "general"} -> <task id="ses_f63684ee8ffejaS3ji8qFaDKYK" state="completed"> READY
  TOOL task {"description": "recall the word", …, "task_id": "ses_f63684ee8ffejaS3ji8qFaDKYK"} -> <task id="ses_f63684ee8ffejaS3ji8qFaDKYK" state="completed"> PLUM
  TEXT FIRST=READY SECOND=PLUM ID=ses_f63684ee8ffejaS3ji8qFaDKYK
  ```
  Resuming a subagent with its context through `task_id` works. No login or permission prompt
  appeared.
- The CLI offers `--auto` ("auto-approve permissions that are not explicitly denied"). It was
  not used, and the design must not rely on it.

### E7 — What the first run's orchestrator actually did

From the T018, T021, T022 and T023 records:

- **Gate reviews:** at every implement gate the orchestrator re-ran the suite in the lane's
  worktree (171, 177, 164, 181 passed), read the source diff by commit range, and exercised the
  real CLI in a scratch repository before approving.
- **Records:** each decision was a row of `# | Question | Options | Decision | Reason`, written
  before the answer and committed on the task branch.
- **Touch map:** lanes were told at plan approval which sections other lanes edit ("Conflict
  handling agreed for all lanes", repeated in three records). No code conflict occurred.
- **Rebases:** every rebase after a merge conflicted only in the agreed classes: index rows,
  changelog bullets, backlog rows united by ID, and installed skills regenerated after making
  the manifest valid. After each rebase the orchestrator re-ran the tests, `validate` and the
  combined features.
- **Hand-off:** sequential. T018 merged first (#8), then T023 (#9), T022 (#10) and T021 (#11).
  Each later branch was rebased once, when its turn came, onto a mainline carrying every earlier
  merge (`20b624f`, `e85bcff`, `fa05757`): 3 rebases, each followed by a full retest (200, 212
  and 237 tests passed).

### Coverage matrix

| Reference behaviour or lesson | Covered by |
|---|---|
| Starts only with a task count | `autopilot start --count N` (required); skill prose |
| Up to three lanes, one per worktree | `[autopilot] max_lanes`; `autopilot next`; existing worktree procedure |
| At most one UI lane | `[[autopilot.group]]` with `limit`, matched by column or assigned by judgement |
| Cheaper model for lanes | integration note: model at launch (Claude Code) or a lane agent definition (OpenCode); not core config |
| Lanes return questions; only the orchestrator talks to the human | existing gate relay protocol (E5, E6 confirm lanes cannot ask) |
| Lanes never start shared services | lane brief in the skill |
| Eligibility with a single unmerged dependency; order by points, then file | T017 (stacked base, `done-branch`), existing `next` ordering, `autopilot next` |
| Configurable kinds | `[autopilot] kinds` |
| States pending, running, done-branch, failed, done-merged | derived from backlog, claims and branches (T017, E4), plus the run file for `failed` |
| Shared session state across sessions | claims (existing, E2); run files in the git common directory |
| Merged verified by content | E4 detection in `autopilot merged` |
| Answer gates from governing documents first, with per-gate criteria | skill; `[autopilot] governing`; checks re-run by the orchestrator |
| Conditional gates with nothing to decide do not stop | existing core skill |
| Decision records before answering, one per task, plus an index | skill format; paths rendered by the CLI |
| Escalation conditions | skill list; CLI flags for the deterministic ones (governing files touched, diverged base, conflict outside known classes, `escalate_gates`) |
| Notification on escalation and lane success | `[autopilot] notify` command contract |
| Supervision of silent lanes | `autopilot status` `silent_minutes`, checked whenever the orchestrator wakes (no timer, E5) |
| A failed lane keeps branch and worktree, blocks only dependents | claim kept, `failed` in the run file, dependency still not done |
| Resources: databases, ports, emulators, sequential numbers | `[[autopilot.resource]]` pools; `reserve-id` (E2) |
| Never merge; hand over one at a time with title and link | skill; `review --publish` run by the orchestrator |
| Push policy differs per project | existing `[git] push_task_branch` |
| After merge: fetch --prune, delete branch and worktree, next branch, rebase stacked dependents with lease | `autopilot merged --cleanup`; `rebase --onto` from the recorded base; `review --publish` pushes with a lease |
| Touch map told to lanes | skill (built at each lane's first gate); `autopilot status` overlap report |
| Conflict classes | skill; T004 merge driver optional; E3 guard |
| `installed.json` hazard | bug task (E3) |
| Lanes stop before publishing; orchestrator publishes with component scope | lane brief; skill |
| Avoid repeating inconsistencies (push expected but forbidden, stale checks, implicit gates) | the skill reads `push_branch`, `checks` and `stages` from `show` instead of restating them |

## Design

### 1. Split between skill and CLI

**The CLI owns what can be computed:** which tasks are dispatchable now, the base, branch,
worktree and resources of each lane, the state of every task in a run, silent lanes, overlapping
files, merge detection, cleanup, paths of decision records, and running the notify command.

**The `taskrail-autopilot` skill owns judgement:** answering gates on the human's behalf,
reading diffs, re-running checks and exercising the result, writing decision records, building
the touch map, resolving conflicts in known classes, deciding to escalate, and the hand-off
conversation.

New commands, all under `taskrail autopilot`, all with `--json` and the existing exit codes:

| Command | Does |
|---|---|
| `autopilot start --count N [--kinds …]` | Refuses with exit 5 unless `[autopilot].enabled`; exit 2 without `--count`. Creates a run: `$(git rev-parse --git-common-dir)/taskrail/runs/<run>.json` with target count, kinds and start time. Prints the run ID. |
| `autopilot next [--run R]` | Tasks to dispatch now: free lanes, allowed kinds, group limits, claims, failed runs, stacked base (T017). For each: `show`'s fields plus `base.commit`, allocated resources and the decision-record path. Allocates resources atomically; claiming stays the lane's job. |
| `autopilot lane <ID> --run R [--handle H] [--state running\|gate\|escalated\|failed] [--reason …]` | Records the agent-specific lane handle (subagent ID, `task_id`) and the orchestrator's view of the lane. `failed` keeps the claim, so the task stays ineligible and its dependents blocked. |
| `autopilot status [--run R]` | Every run task with its state: `pending`, `running`, `gate`, `escalated`, `failed`, `done-branch`, `handed-off`, `done-merged`. Also: lane handle, minutes since the last commit on its branch or last worktree change, `silent` past `silent_minutes`, files touched per branch with overlaps between lanes, governing files touched, and the next branch in the hand-off queue. Reads git; never fetches unless `--fetch`. |
| `autopilot merged <ID> [--cleanup]` | `fetch --prune`, then E4 detection. Reports `merged`, `via` and the mainline commit; with `--cleanup`, removes the worktree and deletes the local branch, refusing if unverified or dirty. Lists stacked dependents with `git rebase --onto <base.onto> <recorded base.commit>`. Marks the task `done-merged` in the run. |
| `autopilot notify --event escalation\|lane-done\|lane-failed --run R [--task ID]` | Runs `[autopilot].notify` if the event is in `notify_on`: message on stdin, `TASKRAIL_EVENT`, `TASKRAIL_RUN`, `TASKRAIL_TASK` in the environment. Its failure is reported and never blocks. |

`autopilot` runs only on explicit request. The skill says so in prose, not only in frontmatter,
per this repository's portability rule: never start without the human asking and giving a
count.

**Installation — decided by the human at the decide gate.** `init` and `upgrade` install the
`taskrail-autopilot` skill in every repository, with the other skills and with no filter. Each
repository decides whether to use it through `[autopilot].enabled`. Until that is true,
`taskrail autopilot start` refuses with exit 5 and names the key, and the skill stops when it
sees that refusal. The spike had recommended installing the skill only where the autopilot is
enabled, through T025's filter, so that a repository not using it would never offer it to its
agent. The human chose always-installed: every consumer receives the same skills, and the
refusal is a CLI guarantee that holds on any agent.

### 2. Orchestrator and lanes on each agent

**The lane contract is agent-neutral.** A lane is a sub-session that:

- runs the `taskrail` skill and the task's executor skill for one task ID;
- creates its worktree with git and claims inside it;
- ends its turn at every gate with the full report;
- is resumed with `continue <ID>` plus answers;
- never runs `review --publish`, never merges, never starts shared services, and never touches
  another lane's worktree.

**The orchestrator** is the session the human talks to. It holds a lane handle per task in the
run file, so a compacted or new orchestrator session can resume lanes.

| | Claude Code | OpenCode |
|---|---|---|
| Lane | background subagent (Agent tool), general-purpose | task tool, `general` or a lane agent definition |
| Handle | agent ID | `task_id` (child session ID), verified in E6 |
| Resume after a gate | `SendMessage` to the ID | task tool with the same `task_id` |
| Orchestrator woken when a lane stops | completion notification | default: when the whole batch of task calls returns; with experimental background subagents, a notification |
| Lane asks the human | impossible (`AskUserQuestion` removed) | impossible (`question` denied) |
| Lane model | Agent `model` parameter | `model` in a lane agent definition |
| Timer wake-up | none (no timer hook) | none found |

**OpenCode's blocking default** means the orchestrator answers gates in waves, when every lane
in a batch has stopped. That is correct but slower. The integration note says so, and names the
experimental background flag without requiring it.

Agent-specific text goes in integration notes appended at the skill's harness marker, as
today. Agent definitions (`.claude/agents/`, `.opencode/agents/`) for pinning a lane model are
adapter-layer packaging, deferred until a consumer needs them.

**Rejected: a CLI process that spawns lanes itself** through `claude -p --resume` or
`opencode run --session`:

- unattended runs deny or skip permission prompts (E5), and the human forbade skipping them;
- answering gates still needs an agent;
- run 1 in E6 hung on stdin, which shows how brittle such a driver is.

### 3. Session state

- **Derived, never stored:** `pending`, `running` (a live claim), `done-branch` (✅ at the task
  branch tip, not ✅ on the mainline — added by T017), `done-merged` (E4, or ✅ on the
  mainline). Any session, and with `claim_remote` any machine, sees them.
- **Claims** remain the only lock. Two additions: `base.commit`, the dependency tip a stacked
  branch started from, written at claim time by T017, so `rebase --onto` works after the
  dependency is squashed; and `run`, the ID of the run that owns the lane.
- **Run file**, local, in the git common directory next to claims, never committed: target
  count, kinds, per task the lane handle, `gate`/`escalated`/`failed` with a reason,
  `handed-off` order, allocated resources, and the run-level decisions agreed so far. It holds
  only what git cannot derive and what must survive the orchestrator's context.
- **Two orchestrator sessions** may run at once. They never double-dispatch, because dispatch
  needs a claim. `status` lists every run in the common directory, so each sees the other's
  lanes.

### 4. Decision records

- **Path:** one file per task at `{artifacts}/autopilot/decisions/{id}-{slug}.md`, with an index
  at `{artifacts}/autopilot/decisions/README.md` (Task, Title, Document). Both are rendered by
  `autopilot next` and `status`, and configurable.
- **Where committed:** on the task branch, by the orchestrator, **only while the lane is stopped
  at a gate**, before resuming it, so the record travels with the squash-merged pull request.
- **Format, as in the first run:**
  - an intro stating that decisions are recorded before they are given;
  - one `## <stage> gate` section per gate: a `Reviewed:` paragraph naming the artifact commit,
    diff range, re-run checks and real-runtime verification, then a table
    `# | Question | Options | Decision | Reason`;
  - a `## Conflict handling agreed for all lanes` section when a touch map was given;
  - a `## rebase after …` section with a File / Conflict / Resolution table and the checks re-run
    afterwards;
  - `## escalated to the human` for escalated gates, naming who answered.
- **Run-level decisions** (touch map, conflict classes, order) are copied into each affected
  task's record, and kept in the run file. A separate run directory on the mainline would need
  its own commit or pull request outside any task. See decision 3 at the gate.

### 5. Escalation and notification

The orchestrator stops and asks the human when it meets any of the following:

- a lane branch touches a `governing` path (flagged by `status`);
- a gate listed in `escalate_gates`, such as `spike:decide`;
- a decision the governing documents reserve to humans;
- two lanes contradicting each other;
- a merge conflict outside the known classes;
- a false premise in a task row;
- a diverged base (already reported by `show` and `review`).

The first two are computed by the CLI; the rest are judgement.

**Notification** is a plain command contract (`[autopilot] notify`, events in `notify_on`,
default `["escalation", "lane-done"]`), invoked through `autopilot notify`. Agent hooks such as
Claude Code's `Notification` are agent-specific and fire on the agent's own events, so they
are not the contract.

**Supervision** is event-driven, since neither agent wakes on a timer. Whenever the orchestrator
wakes, it runs `autopilot status`. A lane silent past `silent_minutes` (default 20) is checked
by reading its worktree, and escalated if stuck. An agent that can wait on a condition may run
`status` periodically, but the design does not rely on it.

### 6. Resource arbitration

- **`max_lanes`** (default 3).
- **`[[autopilot.group]]`** `name`, `limit`, and either `column` + `match` (computed) or neither.
  Without a column, the orchestrator assigns membership by judgement at dispatch, with
  `autopilot lane --group`. This generalises "one UI lane". The column predicate uses the same
  shape as T020's conditional stages, so it is defined once.
- **`[[autopilot.resource]]`** `name` and `values`. Each lane gets one free value per resource,
  allocated under the common-directory lock and released when the lane ends. Values are passed
  to the lane as `TASKRAIL_RESOURCE_<NAME>` in its brief (a database name, a port, an emulator).
- **Shared services** are started by the orchestrator, never by lanes (prose).
- **Sequential numbers:** task IDs through `reserve-id`, already safe (E2). Other sequences,
  such as specification numbers, stay out until a consumer needs them; a value pool covers
  small cases.

### 7. Merge follow-through

- **Publishing:** lanes stop after `taskrail done` and `review --json`. The orchestrator rebases
  if needed, re-runs checks, then runs `review --publish --type … --scope …` in the lane's
  worktree. It pushes with a lease when `push_task_branch` is set.
- **Hand-off is sequential:** one branch at a time, dependencies first, then completion order,
  with the exact title and link. In the first run this cost one rebase and retest per later branch,
  each carrying conflicts from every earlier merge (E7). The benefit: every pull request is tested on the real
  mainline before review.
- **When the human says a branch is merged:** `autopilot merged <ID> --cleanup`. Then the
  orchestrator names the next branch and rebases it, and every stacked dependent, onto the new
  mainline with `git rebase --onto <mainline> <base.commit>`. It resolves known classes,
  re-runs checks and publishes again (lease push).
- **Known conflict classes, resolved without a human:**
  1. backlog rows united by ID, ✅ wins unless a `Reopens:` commit exists (core skill today;
     T004's merge driver automates it later);
  2. appended index rows and changelog bullets: keep all;
  3. installed skill copies and `installed.json`: make the manifest valid first, merge the
     sources, then `taskrail upgrade --force`.

  Anything else escalates.
- **The E3 bug is a prerequisite for class 3:** until init and upgrade stop on an unreadable
  manifest, a mistaken `init` silently loses recorded integrations.

### 8. Configuration keys

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

## Options considered

| Point | Option | Verdict |
|---|---|---|
| 1 Split | skill only, over existing commands (as the first run) | rejected: E1 re-dispatch, no merge detection, state lost with the orchestrator's context |
| | **skill plus thin `autopilot` command group** | **chosen** |
| | CLI scheduler that spawns agent CLIs | rejected: permission prompts (E5), judgement still needs an agent, brittle (E6 run 1) |
| 2 Lanes | **subagents, resumed by handle** | **chosen**; verified on both agents |
| | separate headless sessions (`claude -p --resume`, `opencode run --session`) | rejected: unattended permission handling |
| 3 State | everything in claims | rejected: claims are released at `done`; failure and handles would change what a claim means |
| | **derived state + claims + local run file** | **chosen** |
| | committed state file | rejected: conflicts across branches, machine paths and handles in a public tree |
| 4 Records | **per task, on the task branch, plus index** | **chosen**; matches the first run |
| | inside the task's own artifact | rejected: two authors in one file, conflicts with the lane |
| | one run log on the mainline | rejected: needs a mainline commit outside any task |
| 5 Notify | **command contract** | **chosen** |
| | agent hooks | rejected as the contract: agent-specific |
| 6 Resources | **CLI pools and group limits** | **chosen** |
| | orchestrator judgement only | rejected: races between orchestrator sessions |
| 7 Hand-off | **sequential** | **chosen**: every pull request tested on the real mainline |
| | batch | deferred: fewer rebases, untested combinations |
| 1 Installation | install the skill only where `[autopilot].enabled` is true (T025's filter) | recommended by the spike; **overridden by the human** |
| | **install always; `autopilot start` refuses with exit 5 until enabled** | **chosen by the human** at the decide gate |
| 7 Detection | ancestry or `git cherry` only | rejected: blind to squash (E4) |
| | **ancestor → tree → patch-id → merge-tree** | **chosen** (E4) |

## Recommendation

Adopt the design above. Deliver it with these tasks (points are estimates, kinds as in this
backlog):

| # | Task | Kind | Pts | Depends on | Parallel with |
|---|---|---|---|---|---|
| T017 (edited) | Branch a task from its single unmerged dependency: add the `done-branch` state (✅ only at the task branch tip, not eligible in `next`), stacked base in `show`, `new --workspace` and `review`, `base.commit` recorded in the claim | feature | 3 → 5 | — | new bug below |
| new A | Stop init and upgrade on an unreadable installed.json (E3) | bug | 1 | — | T017, B |
| new B | Write the autopilot design into DESIGN.md | chore | 2 | — | T017, A |
| new C | Add the `[autopilot]` configuration, runs and `autopilot start`, `lane` and `status`; `start` refuses with exit 5 until `[autopilot].enabled` | feature | 5 | T017, B | — |
| new D | Dispatch lanes with `autopilot next`: groups, kinds, resource pools | feature | 3 | C | E, F |
| new E | Detect squash merges by content and follow through with `autopilot merged` | feature | 3 | C | D, F |
| new F | Add `autopilot notify` and the escalation flags in `status` | feature | 2 | C | D, E |
| T024 (edited) | Write the taskrail-autopilot skill with Claude Code and OpenCode notes, installed in every repository by init and upgrade | feature | 8 → 5 | D, E, F | — |
| new G | Trial the autopilot on a real backlog with each supported agent | spike | 2 | T024 | — |

**T017 and T019 should not run in parallel.** Both change how a task's branch is found:

- today it is rendered from the kind's template in `task_dict`, `_open_workspace` and
  `cmd_review`;
- T017 adds a fourth lookup, the dependency's branch;
- T019 must replace every lookup with a resolver that survives the claim's release at `done`.

Run T017 first, then T019 against its single lookup. T019 is not needed by the autopilot, and
can run in parallel with C–F if its touch map keeps it out of the new `autopilot` module.

**T020** is not a prerequisite and not needed by the autopilot. It is independent of C–F,
provided whichever lands first defines the column predicate (`column` + `match`) that the other
reuses. **T004** (merge driver) and **T005** (importer) stay independent.

Lower-priority follow-ups **not** proposed now:

- lane agent definitions for pinning a lane model;
- a `batch` hand-off mode;
- named counters beyond task IDs.

## What would change the decision

- **OpenCode's background subagents become default and stable:** drop the "waves" caveat.
  **Claude Code or OpenCode loses resume-by-handle:** lanes would have to restart from the
  branch and artifacts, and the run file would need a stage checkpoint per lane.
- **A consumer needs lanes on several machines:** the run file would need a remote form, like
  `claim_remote`.
- **Hosts squash with a server-side rebase that alters content** (for example, signing or
  trailers inside the tree): tree and patch-id could miss. Detection would then need the host's
  pull-request state, which is currently a non-goal.
- **The trial run (G) shows sequential hand-off costs more than it catches:** add `batch`.
- **Consumers object to an autopilot skill they have not enabled being offered to their
  agent:** install it only where enabled, reusing T025's kind filter.

## How to reproduce

```bash
REPO=/path/to/taskrail                       # a checkout of this branch
TR="uv run --quiet --project $REPO taskrail"

# E1, E2 — eligibility after `done` on a branch; claims and IDs across worktrees
S=$(mktemp -d) && cd $S && git init -q --bare origin.git && git init -q -b main repo && cd repo
git config user.email t@example.com && git config user.name t
git remote add origin ../origin.git && git commit -q --allow-empty -m root && git push -q -u origin main
$TR init --integration claude && $TR epic add --name Demo --objective "Try lanes"
$TR new --epic E01 --kind feature --title "Base task" --pts 2
$TR new --epic E01 --kind feature --title "Depends on base" --pts 1 --depends-on T001
$TR new --epic E01 --kind bug --title "Independent" --pts 3
$TR new --epic E01 --kind chore --title "Two deps" --pts 1 --depends-on T001,T003
git add -A && git commit -q -m backlog && git push -q && $TR next
git worktree add .worktrees/T001-base-task -b T001-base-task origin/main
(cd .worktrees/T001-base-task && $TR claim T001 && $TR done T001 && git commit -qam "done T001")
$TR next; $TR claims; $TR show T001 --json; $TR show T002
git worktree add .worktrees/T003-independent -b T003-independent origin/main
(cd .worktrees/T003-independent && $TR claim T003); $TR next; $TR claims
(cd .worktrees/T001-base-task && $TR reserve-id) & (cd .worktrees/T003-independent && $TR reserve-id) & wait

# E3 — conflicted manifest
S=$(mktemp -d) && cd $S && git init -q -b main && git config user.email t@example.com && git config user.name t
git commit -q --allow-empty -m root && $TR init --integration claude && git add -A && git commit -qm init
git switch -qc a && $TR init --integration opencode && git add -A && git commit -qm a
git switch -q main && git switch -qc b && $TR init --github-workflow && git add -A && git commit -qm b
git merge a; $TR upgrade; echo $?; $TR upgrade --force; echo $?; $TR init; echo $?; cat .taskrail/installed.json

# E4 — squash detection on pull requests #8–#11 (read-only clone)
M=$(mktemp -d) && git clone -q --no-checkout git@github.com:alexkander/taskrail.git $M/repo && cd $M/repo
git fetch -q origin '+refs/pull/8/head:refs/pr/8' '+refs/pull/9/head:refs/pr/9' \
  '+refs/pull/10/head:refs/pr/10' '+refs/pull/11/head:refs/pr/11'
for n in 8 9 10 11; do H=refs/pr/$n
  git merge-base --is-ancestor $H origin/main && echo "$n ancestor"
  git cherry origin/main $H | cut -c1 | sort | uniq -c
  git log --first-parent --format='%T %h' origin/main | awk -v t=$(git rev-parse $H^{tree}) '$1==t{print "tree at", $2}'
  git diff $(git merge-base $H origin/main) $H | git patch-id --stable
  git merge-tree --write-tree origin/main $H | head -1; git rev-parse origin/main^{tree}
done
git show 20b624f | git patch-id --stable   # likewise e85bcff, fa05757, ee38f5b

# E6 — OpenCode subagent resume (stdin must be closed)
D=$(mktemp -d) && cd $D && git init -q && opencode debug agent general
opencode run --format json "Use the task tool twice, sequentially. First call: subagent_type general, \
description 'remember a word', prompt 'Remember the word PLUM. Reply only READY. Use no tools.' \
Second call: the same subagent_type, task_id set to the task id returned by the first call, description \
'recall the word', prompt 'Which word did I ask you to remember? Reply with the word only. Use no tools.' \
Then reply with one line: FIRST=<result of first call> SECOND=<result of second call> ID=<task id>. \
Use no other tools." < /dev/null
```
