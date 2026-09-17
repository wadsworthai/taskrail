# T079 — Write the current-branch workflow into DESIGN.md

Kind: chore · Epic: E07 · Status: implemented

## Goal

Some repositories are worked by a single maintainer running one agent at a time, straight on the
checked-out branch. Today (v0.2.0) kind overrides already let such a repository set a stage's
`commit = false` and `gate = "conditional"`, but four things cannot be configured:

1. **No branch per task.** `[git] worktree = "never"` still means one branch per task: the
   `taskrail` skill always creates one, and `claim` warns when the checkout is not on it.
2. **Commit only when the task is done**, in one or more logical commits that include the status
   change.
3. **Decisions, not stage approvals.** Stop as soon as a decision appears, never to approve a whole
   stage.
4. **Close without review.** No fetch, rebase or publish, and no push the human did not approve.

E07 builds this in T080–T084. This chore decides the design and writes it into `DESIGN.md`, so
each of those tasks has one contract to build from. It changes no code, skill or configuration.

## Grounding: how things work now

- `[git]` is read in `config.py`. Bad values raise `ConfigError`, so every command exits 2,
  `validate` included. `worktree` is `"required"` or `"never"`.
- Gates are checked in `kinds.py` (`GATES = ("always", "conditional", "none")`). A bad value is a
  `kind-invalid` validation error, which makes `validate` exit 1. A stage's `commit` is a boolean.
  An override replaces the whole descriptor (§5.2).
- `branches.resolve` gives every command a task's branch: the recorded one, or the template's
  (§6.4). `show`, `done-branch` detection, a dependent's stacked base, `prior_work`,
  `new --workspace`, `workspace` and `review` all use it.
- `claim` records the claim's `branch` and `base`. `_freeze_branch` writes a branch record when the
  claim is made on the template's name, and warns on any other branch or on a detached `HEAD`.
- `query.task_dict` builds `show`'s `base` from the mainline, or from a dependency done only on its
  branch, and sets `worktree` and `worktree_base` to `null` unless `worktree = "required"`.
- `review` refuses a checkout not on the task's branch (exit 5). Then it fetches, chooses a rebase
  base, and with `--publish` pushes and returns the pull request link.
- `checks` runs in the claim's worktree, or else in the worktree that has the task's branch checked
  out. Exit 5 means there is neither.
- `autopilot start`, `extend` and `next` refuse with exit 5 unless `[autopilot].enabled` is true.
  `autopilot lane --gate` takes one of the kind's stages, or `close`. `escalate_gates` entries are
  written `kind:stage`.

## Change set

| File | Change |
|---|---|
| `DESIGN.md` new §13 *Current-branch workflow (planned)* | Added after §12. It opens with a status line: planned; implemented by T080–T084; nothing in it describes current behaviour. Subsections: **13.1 Configuration** (the keys, their values and defaults, where each lives, and precedence); **13.2 The current branch** (`show`/`list`/`next` fields, `claim`, branch records, `branch`, `new`, `new --workspace`, `workspace`, `edit`, `done-branch` and stacking, `prior_work`, `checks`, claim and record mirroring); **13.3 On-done commits** (effective stage `commit`, `kind_descriptor.commit`, `close`, `done`'s output); **13.4 Decisions gates** (meaning compared with `conditional`, judgement skips, the autopilot's `lane --gate` and `escalate_gates`); **13.5 Closing on the current branch** (`review` without fetch, rebase or push, its `--json`, `--publish` refused; the skill's close: done, commits, report, ask before any push); **13.6 Validation** (config errors, exit 2; kind errors, exit 1); **13.7 The autopilot** (which commands refuse, with exit code and message); **13.8 Delivery** (which of T080–T084 builds which part). Every decision taken at this gate is written in. |
| `DESIGN.md` §4 | The `[git]` block of the example config gains `task_branch` and `commit` with their defaults and a `§13` pointer. One sentence joins the load checks. |
| `DESIGN.md` §5.1 | The descriptor example names `decisions` among the gate values and shows the optional top-level `commit`, each pointing to §13. |
| `DESIGN.md` §5.3 | The "shared by every kind" paragraph ("one worktree and branch per task", "rebase onto the mainline") gains "unless `[git].task_branch = "current"` (§13)". |
| `DESIGN.md` §6.4 | One sentence: with `task_branch = "current"` the resolver answers the checked-out branch, as §13.2 describes. |
| `DESIGN.md` §7 command table and §7.1 | One pointer each where behaviour differs under §13: `show` (`task_branch`, `close`), `branch`, `new --workspace`, `workspace`, `done`, `review`. |
| `DESIGN.md` §12.2 | One sentence: `autopilot start`, `extend` and `next` also refuse a repository configured as §13.7 describes. |
| `DESIGN.md` §11 | Phases gain a line naming E07 (T079–T084) and §13. |
| `TODO.md` | Only if decision 14 is approved: `taskrail edit --description` on T080, T081, T082 and T083, so each row names the contract §13 assigns to it. The CLI makes the edit; no row is typed by hand. |
| `docs/chores/T079-write-the-current-branch-workflow-into-d.md` | This artifact. |
| `docs/chores/README.md` | Index row for T079, added at implement. |

The style follows `DESIGN.md` as it is: numbered `###` subsections, tables for keys and outputs,
short bullets, `§` cross-references, exit codes spelled out, and parts marked *planned, T0xx*.

## Decisions needed

Each one has a recommendation first, then the alternatives.

1. **Where the design goes.** *Recommended:* a new **§13** at the end, plus the short pointers above
   in §4–§7, §11 and §12.2, as T028 did with §12. Nothing is renumbered, and T080–T084 move text
   into §4–§7 as they implement it. *Alternative:* write it straight into §4–§7 and §12, marked
   planned. That spreads unimplemented behaviour through sections that now describe what the CLI
   does.

2. **The branch setting's name and values.** *Recommended:* `[git] task_branch = "task" | "current"`,
   default `"task"`: `"task"` is one branch per task, as now, and `"current"` is the checked-out
   branch. It is a repository-wide setting only, never per kind, because the workspace belongs to
   the checkout, not to the kind. *Alternatives:* `"per-task"` / `"current"`; or a single mode key
   such as `[git] workflow = "task-branch" | "current-branch"`.

3. **How `task_branch = "current"` combines with `worktree`.** *Recommended:* **require
   `worktree = "never"`**. Loading the config fails (exit 2, every command) with
   `git.task_branch = "current" requires git.worktree = "never"`, and since `worktree` defaults to
   `"required"`, the key must be written. This is explicit, and no key silently overrides another.
   *Alternative:* `"current"` implies `"never"`, and `worktree` is ignored.

4. **What `show`, `list` and `next` report under `"current"`.** *Recommended:*
   - a new top-level `task_branch` field, `"task"` or `"current"`, under every setting, so the skill
     reads its workflow from `show`;
   - `branch` is the checked-out branch (`null` on a detached `HEAD`), with `branch_source` set to
     `"current"`, even while a claim names another branch; `claim.branch` still shows where the
     task was claimed;
   - `base` is `null`: there is no workspace to create, no fork point to rebase, and no `row` check.
     The text omits the base line;
   - `worktree` and `worktree_base` are `null`, as with `worktree = "never"` today;
   - `prior_work.branches` is `[]`, since the checked-out branch is not evidence of earlier work.
     `prepared` is `null`. `artifact` and `commits` are unchanged;
   - `done-branch` and `discarded-branch` are never derived. A task's state comes from the
     checkout's rows and the claims. So a dependency blocks until it is `✅` in this checkout
     (`done` makes it so), and no task is ever stacked.

   *Alternative:* `branch` is the live claim's branch while one exists, and the checked-out branch
   otherwise. That is closer to the claim, but it makes the task's branch depend on who holds it.

5. **Commands that assume a task branch.** *Recommended*, each exiting **5** and naming
   `[git].task_branch`:
   - `new --workspace` refuses before reserving an ID;
   - `workspace <ID>` refuses;
   - `branch <ID> <NAME>` refuses too: there is no task branch to name.

   Without refusals:
   - `claim` records the checked-out branch in the claim and writes no branch record. It gives no
     warning, except on a detached `HEAD`, where it keeps today's warning. The claim's `base` is
     `null`;
   - `new` without `--workspace` stops warning on the mainline checkout, since committing there is
     the workflow;
   - `edit` never records an old branch name;
   - `checks` runs in the claim's worktree, or else in the checkout it runs from, and never exits 5
     for a missing worktree.

   *Alternative:* make `branch` a no-op that exits 0. It is silent, which hides a skill that follows
   the task-branch steps by mistake.

6. **Claims and records mirrored to a remote under `"current"`.** *Recommended:* `claim_remote`
   works unchanged. Setting it is the human's standing approval to push that claim ref, which lives
   outside `refs/heads`. `branch_record_remote` is not an error, but pushes nothing, since no
   records are written. Either way, no branch is ever pushed. *Alternative:* a config error (exit 2)
   when either key is set with `"current"`, which is stricter about the epic's "no push the human
   did not approve".

7. **The commit policy's name, values and where it lives.** *Recommended:*
   `[git] commit = "stages" | "on-done"`, default `"stages"`. A kind descriptor may declare the same
   top-level `commit` key, and so may a local kind or an override. The kind's value wins over the
   config's in both directions. The policy is independent of `task_branch`: `on-done` also works on
   a task branch. *Alternatives:* config only, with no per-kind value; or a `[kinds] commit = {
   chore = "on-done" }` table, which avoids copying a whole descriptor into an override, but puts
   kind data outside the descriptors.

8. **What `on-done` changes in the output.** *Recommended:*
   - in `show --json` and `kind list --json`, every stage's `commit` is reported `false`, because
     the effective policy decides it;
   - `kind_descriptor` gains `commit` (`"stages"` or `"on-done"`) and `commit_source` (`"kind"`,
     `"config"` or `"default"`);
   - `show` gains a top-level `close` object: `{"commit": "stages" | "on-done", "review": "publish" |
     "report"}`. `review` is `"report"` under `task_branch = "current"` (§13.5). Under `on-done`, the
     skill follows `done` with logical commits of everything the task changed, the status change
     included; under `stages` it commits the status change on its own, as now;
   - `done` and `discard` `--json` gain `commit`, the task's effective policy, and under `on-done`
     their text adds one line saying to commit the task's changes now;
   - a descriptor with `commit = "on-done"` whose stages say `commit = true` is not an issue: the
     policy wins.

   *Alternative:* keep each stage's declared `commit` in `show` and let the skill combine it with
   `close.commit`. That leaves the skill to compute an answer the CLI should give it.

9. **What `gate = "decisions"` means.** *Recommended:* it is a per-stage value in descriptors and
   overrides, next to `always`, `conditional` and `none`:
   - the executor stops **as soon as a decision appears** during the stage, asks it with its
     recommendation and alternatives, and continues when answered;
   - it **never** stops at the end of the stage to have the stage approved or to report;
   - what `conditional` would stop to report — opened follow-ups, results — goes to the next stop,
     or to the close hand-off;
   - a decision is a choice that the task, the approved or recorded artifact, the repository's
     instructions and the executor skill do not settle, whose options differ in a way the human
     would care about. Every place an executor skill already says "stop and ask" is one;
   - skipping a `judgement` stage whose gate is `decisions` is recorded in the artifact and
     reported at the next stop, like `conditional`, and is not asked.

   Compared with `conditional`: `conditional` stops at the stage's end when there is something to
   decide *or report*; `decisions` stops mid-stage, only to decide. There is no repository-wide gate
   setting: a repository uses overrides, as it does today to set `conditional`. *Alternative:* also
   a `[kinds] gate = "decisions"` key that maps every `always` and `conditional` stage for all
   kinds.

10. **Decisions gates in the autopilot.** *Recommended:* allowed. A lane stopped at a decision runs
    `autopilot lane --state gate --gate <stage>` with the stage the decision arose in. `status` and
    `escalate_gates` treat it like any gate, so `spike:decide` still escalates when that stage's
    gate is `decisions`. The orchestrator answers from `read_first` as usual. With no stage-end
    stops, its first full review of the diff is the close review. *Alternative:* `autopilot start`
    refuses kinds with `decisions` stages.

11. **Which autopilot commands refuse `task_branch = "current"`.** *Recommended:*
    `autopilot start`, `extend` and `next` (preview included) exit **5** right after the `enabled`
    check, with
    `the autopilot needs a branch per task; [git].task_branch is "current" in .taskrail/config.toml`.
    `status`, `lane`, `decision`, `approve-governing`, `merged`, `notify` and `close` keep working,
    so runs made before the change can be inspected and closed. *Alternative:* only `start` refuses,
    as T080's row says now.

12. **The autopilot and `commit = "on-done"`.** *Recommended:* the same three commands also exit 5
    when the effective policy of any kind the run drives is `on-done`. The message names
    `[git].commit`, or the descriptor path that sets it. Lanes commit what they finish so a lane can
    be restarted from its branch (§12.3), and the orchestrator reviews commit ranges at gates. This
    would be built in T081. *Alternative:* allow it, and accept that a restarted lane loses its
    uncommitted work.

13. **`review` under `"current"`.** *Recommended:*
    - no fetch, no rebase, no push, and no branch-mismatch refusal. It still requires the task to be
      `done` or `discarded` in the checkout (exit 5 otherwise);
    - `--json` keeps its keys: `head` is the checked-out branch, `fetched` is `false`,
      `rebase.enabled` is `false` with a `reason` naming the setting, `push.enabled` is `false`,
      `pull_request` has `title` and `body` for reference and `url` `null`, and `published` is
      `false`. It adds `commits` (the commits on `HEAD` whose subject names the task, in the
      `prior_work` forms, newest first, capped at 10, with `commits_total`) and `upstream` (`ref`
      and `ahead`, the commits `HEAD` has that its upstream lacks, or `null` without an upstream),
      so the executor can report what a push would send;
    - `--publish` exits **5**, checked after the task is found and before anything else, with
      `[git].task_branch is "current": review does not publish; push with git once the human approves`.

    *Alternative:* exit 2 for `--publish`. But the invocation is not malformed; the configuration
    refuses it, which is what 5 means.

14. **Backlog rows.** *Recommended:* at implement, after this gate, run `taskrail edit --description`
    on T080, T081 and T083 where the decisions above widen their rows. T080 would gain `branch`,
    `extend` and `next` refusing, `task_branch` in `show`, and `checks`. T081 would gain the
    autopilot refusal and `done`'s output. T083 would gain `commits` and `upstream`. T082 would only
    change if decision 10 changes. *Alternative:* leave the rows as they are and let §13.8 be the
    contract. The rows would then understate what each task must deliver.

15. **CHANGELOG and README.** *Recommended:* **neither**. `## Unreleased` lists changes to what
    taskrail does, and this adds only planned design (T028 added none either). The README gains the
    single-maintainer configuration in T084. *Alternative:* one changelog bullet noting the planned
    design.

## Decisions at the scope gate

Recorded in [the autopilot decision record](../autopilot/decisions/T079-write-the-current-branch-workflow-into-d.md).
All fifteen were taken as recommended, with one addition to decision 7: §13 states plainly that the
kind's top-level `commit` is a policy string (`"stages"` or `"on-done"`), while a stage's `commit`
stays a boolean. §13 opens with a status line saying it is planned and naming T080–T084, and
describes the need in general terms only. The change set and its boundary were approved as scoped.

## Out of scope

- Any code, test, kind descriptor, skill, integration note or `.taskrail/config.toml` change. Those
  are T080–T084.
- Moving §13 text into §4–§7 as implemented behaviour. Each implementing task does that.
- A repository-wide gate setting (unless decision 9 changes), `task_branch` per kind, and pushing
  from `review` under `"current"`.
- The top-of-file status line, §1–§3, §8–§10 beyond the pointers listed, and §12 beyond §12.2's
  sentence.
- Naming or describing any consuming project. The need is written in general terms only.

## Verification

- `git diff origin/main --stat` shows only `DESIGN.md`, this artifact, `docs/chores/README.md`, the
  orchestrator's decision record and its index, and `TODO.md` if decision 14 is approved.
- `git diff origin/main -- DESIGN.md` changes no existing heading, and outside §13 changes only the
  pointer lines listed in the change set.
- Every open question in the brief has an answer in §13, checked one by one against this list:
  key names and values, and where they live; `task_branch` with `worktree`, claims, `claim_remote`,
  branch records, `done-branch`, stacked dependencies and the base, `new --workspace`,
  `workspace`, `branch` and `prior_work`; `commit = "on-done"` at config and kind level, with stage
  `commit` and `show --json`; `decisions` compared with `conditional`, and in the autopilot's gates
  and `escalate_gates`; `review` and `--publish` with an exit code; `validate`; the autopilot's
  refusal with exit code and message.
- Every contract in the T080–T084 rows (as edited, if they are edited) appears in §13.8, and every
  part of §13 is assigned to one of those tasks.
- `grep -n '13\.' DESIGN.md` resolves every `§13.x` reference to a subsection that exists.
- `grep -rniE` for private names finds none in the diff (publishing constraint).
- `.taskrail/bin/taskrail validate` passes, and `taskrail checks T079 --stage implement` passes
  (`test`; `lint` is not configured).

### Results

- `git diff origin/main --stat` → `DESIGN.md` (269 lines changed), `TODO.md` (6), this artifact,
  `docs/chores/README.md` (1), and the orchestrator's decision record with its index row. No other
  file.
- `git diff -U0 origin/main -- DESIGN.md` → no existing heading changes. Outside the new §13, the
  hunks are only the pointers in the change set:
  - the §4 `[git]` example (two keys) and a load-check paragraph;
  - a §5.1 paragraph and the §5.3 sentence;
  - the §6.4 sentence;
  - the §7 table rows for `show`, `branch`, `new`, `workspace`, `done`/`discard` and `review`;
  - the §7.1 opening sentence;
  - §11's third phase item and a §12.2 bullet.

  The only removed lines are the originals of the table rows and sentences that gained a pointer.
- Open questions from the brief, checked one by one against §13:
  - key names, values and where they live → §13.1;
  - `task_branch` with `worktree` → §13.1 and §13.6;
  - claims, `claim_remote`, branch records, `done-branch`, stacked dependencies and the base,
    `new --workspace`, `workspace`, `branch` and `prior_work` → §13.2;
  - `commit = "on-done"` at config and kind level, with stage `commit` and `show --json` → §13.1
    and §13.3;
  - `decisions` compared with `conditional`, the autopilot's gates and `escalate_gates` → §13.4;
  - `review` and `--publish` with an exit code → §13.5;
  - `validate` → §13.6;
  - the autopilot's refusal, with exit code and message → §13.7.

  Each has an answer.
- Backlog rows: `taskrail edit T080|T081|T083 --description … --json` each returned a
  `changes.description` from/to pair and `files: ["TODO.md"]`. Checked against §13.8, every row
  names what §13.8 assigns to it. T082's row (unchanged, per decision 14) names `kind show`, which
  is not a command (`cli.py` has only `kind list` and `kind add`). §13.4 and §13.8 therefore say
  `show` and `kind list`, and T082 reads its contract from §13.8.
- `grep -on '§13\.[0-9]' DESIGN.md` → references to §13.1–§13.8, and all eight subsections exist
  (`grep -n '^### 13\.'`). Both links in §13's status line resolve to existing files.
- The diff's added lines were searched for URLs, e-mail-like strings, local paths, and the words
  client and employer → no match (publishing constraint).
- `taskrail validate` → `73 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- `taskrail checks T079 --stage implement` → `test: uv run pytest -q` `1052 passed in 149.59s`;
  `lint: not configured`; `passed`.

## Decisions at the implement gate

Recorded in [the autopilot decision record](../autopilot/decisions/T079-write-the-current-branch-workflow-into-d.md).
The implement stage was approved, with two fixes:

1. **T082's row.** `taskrail edit T082 --description` now opens with `DESIGN.md §13.4:` and names
   `show, kind list` instead of `kind show`, which is not a command. This matches §13.8.
2. **`close.review` goes to T083.** T080, T081 and T082 run in parallel, and T083 runs only once all
   three are merged, so T083 is the one task that sees both settings. The following changed:
   - §13.3: T081 adds `close` with `commit`, and T083 adds `review`.
   - §13.8: the T081 row names `close.commit`, and the T083 row adds `show`'s `close.review`. The
     note below the table no longer says "whichever of T080 and T081 lands second"; its conflict
     note about `config.py`/`show` and `kinds.py` stays.
   - `taskrail edit --description`: T081 names `close.commit` instead of `close {commit, review}`,
     and T083 adds "show's close.review reads task_branch".

   Each edit returned its from/to pair and `files: ["TODO.md"]`.

## Docs

- `CLAUDE.md`: the layout line for `DESIGN.md` now names §13, the planned current-branch workflow,
  next to §12.
- `README.md` and `CHANGELOG.md` are unchanged (scope decision 15). The README gains the
  single-maintainer configuration in T084.
- No shipped skill or integration note changes: they describe current behaviour, and T084 teaches
  them the workflow once it is built.
- No follow-up tasks were opened.
