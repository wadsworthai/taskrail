# T055 — Fix the autopilot skill text found wrong in the T033 trial

## Goal

Fix the skill-text findings of the [T033 trial](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md)
in the portable `taskrail-autopilot` skill, and assert each rule with tests on the skill sources and
on the copies `init` installs:

- **F4** — the first hand-off, on both agents, reached the human without the branch or the title.
  The skill asks only for "the exact pull request title and link".
- **F5** — the refill waited 13 minutes: the skill refills when a lane is "handed off, failed,
  discarded", but a lane is already free at `done-branch` (DESIGN §12.7).
- **F6** — a run decision rested on the false premise that "each branch allocates IDs from its own
  TODO.md", so lanes were forbidden `taskrail new`. IDs are reserved under a lock in the git common
  directory, above every ID on any local branch and every pending reservation (DESIGN §6.3,
  `ids.py`); the skill never says so.
- **F7, skill half** — the skill does not say that a dispatch nobody claims expires after
  `[git].claim_grace_minutes` (15). The CLI half, abandoning a run, is T048 and is not named here.
- **F2** — a new Claude Code session restarted a lane from its branch rather than resuming it by
  its handle, while DESIGN §12.3 claims "a compacted or new orchestrator session can resume the
  lanes". The skill has no procedure for continuing a run from another session.

Premises checked on the base (`1631ab8`):

- F5: `autopilot/dispatch.py` `OCCUPYING = ("running", "gate", "escalated", "dispatched")`, so
  `done-branch` holds no lane; release of its resource values is lazy, on the next `next`.
- F6: `ids.reserve` takes `id_lock` in the common directory and numbers above `used_ids` (working
  tree, every `refs/heads` branch, remote-tracking branches with `claim_remote`) and pending
  reservations; `tests/test_ids.py` covers other branches, the working tree and concurrency.
- F7: `runs.dispatch_live` compares `dispatched` with `claim_grace_minutes`;
  `tests/test_autopilot_next.py::test_a_dispatch_holds_its_lane_until_it_is_claimed_or_expires`
  shows an expired dispatch released and dispatched again.
- F2: `claims.create` treats a claim by the same owner on the same branch as a no-op, so a lane
  restarted in the existing worktree can claim again.

`prior_work` in `taskrail show T055` was empty.

## Change set

### `src/taskrail/skills/taskrail-autopilot/SKILL.md`

Areas: *Dispatch* step 6, a new step 7 and a new closing paragraph; *Close and hand off* steps 1
and 4; *After a merge* step 2; a new section *Resume a run* between *After a merge* and *Known
conflict classes*. Nothing in *Escalate* (T049, T048) and not the `--gate close` sentence of *Close
and hand off* (T050).

*Dispatch* step 6 is replaced, and step 7 and a paragraph follow it (F5, F7, F6):

```markdown
6. Refill as soon as a lane frees, without waiting for its hand-off: once you have reviewed a
   lane's close (its task is `done-branch`), recorded it failed, or its task was discarded, run
   `next --run <R>` again. The run's count caps what starts; never start more tasks than the human
   asked for.
7. A dispatch expires. A task `next` dispatched that no lane has claimed within
   `[git].claim_grace_minutes` (15 by default) reads `pending` again: it no longer holds a lane or
   its resource values, and a later `next`, in any run, may dispatch it again. So launch each lane
   as soon as `next` returns, and let it claim before anything else. A lane launched after its
   dispatch expired can find its branch already created by another lane; it then stops and
   reports, as its brief says. A run a lost session left behind stops holding the lanes it
   dispatched but never claimed in the same way; lanes that claimed keep theirs.

**Task IDs across lanes.** `taskrail new` reserves each ID under a lock shared by every worktree of
the clone, above every ID on any local branch and every reservation not yet used, so two lanes
never receive the same ID: a branch does not allocate from its own backlog alone. A lane may open
a follow-up task with `taskrail new` on its own branch when a gate approves it. Never forbid lanes
to create tasks, or defer follow-ups to the hand-off, for fear of colliding IDs.
```

*Close and hand off* step 1 gains its last sentence, and step 4 is replaced (F5, F4):

```markdown
1. In the lane's worktree, run `taskrail review <ID> --json`. If `rebase.needed` is true, run
   `git rebase <rebase.onto>`, resolve only the known classes, re-run the checks and
   `taskrail validate`, record the rebase in the task's record and commit it. The refill after the
   close may have released the lane's resource values: run the checks with values that no lane in
   use holds in `status`.
```

```markdown
4. Tell the human, in one message: the task ID, the branch and the base it now sits on, the exact
   pull request title (`pull_request.title`), its body (`pull_request.body`), and the link
   (`pull_request.url`) — or that `review --publish` returned none. A hand-off message without the
   branch, the title or the body is incomplete: never send one. Never merge.
```

*After a merge* step 2: "re-run the checks" becomes "re-run the checks with resource values as at
hand-off".

New section (F2, F7):

```markdown
## Resume a run

A run outlives the session that started it: its state is in the run file and on the task
branches. When the human asks a new or compacted session to continue a run, resume it rather than
starting another. Resuming needs the human's request but no new count, and never runs
`autopilot start`.

1. Run `taskrail autopilot status --json` and take the run the human names; if more than one run
   could be it, ask. Read the governing documents, the run's `decisions` and each run task's
   decision record, as before the first dispatch.
2. For each lane that is `running`, `gate` or `escalated`, first try to reach it by the handle
   `status` shows. While the handle reaches it, supervise it and answer its gates as usual.
3. When the handle no longer reaches it, restart the lane from its branch, where everything it
   finished is committed. Restart a `running` lane only once `status` reports it `silent`, so an
   earlier sub-session that may still be working never shares the worktree with a new one. Answer
   a `gate` lane's gate first, and an `escalated` lane's once the human has. Fill
   `references/lane-brief.md` with its restart workspace section, naming the last gate the record
   answers and the answers to apply, launch the lane, and record the new handle:
   `taskrail autopilot lane <ID> --run <R> --handle <H> --state running`.
4. Go on as usual for the rest: a `done-branch` task has its close reviewed and is handed off, a
   `dispatched` task whose lane never started expires as *Dispatch* says, and
   `next --run <R>` fills the lanes that are free.
```

### `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md`

- Header: "Everything below the rule is the brief." becomes "Everything between the two rules is
  the brief. When you restart a lane from its branch (*Resume a run* in `SKILL.md`), use the
  Workspace section after the second rule in place of the brief's own."
- *How to work* gains a bullet (F6): "IDs from `taskrail new` are reserved across every worktree
  and branch of this clone, so a follow-up task you open on your branch never collides with
  another lane's."
- After `<CONTEXT>`, a second rule and the restart section (F2):

```markdown
---

## Workspace (restart from the branch)

- You replace an earlier lane for <ID> that can no longer be resumed. Its branch `<BRANCH>` and
  worktree `<WORKTREE>` already exist, on base `<BASE>`: work inside them; do not create a
  workspace, and do not stop because the branch exists.
- Inside the worktree, claim before any edit: `taskrail claim <ID> --run <RUN>`. The earlier
  lane's claim has the same owner and branch, so this changes nothing; if it exits non-zero, stop
  and report.
- Before any edit, find where the earlier lane stopped: `git status` and `git log <BASE>..HEAD` in
  the worktree, the artifact and the decision record `<DECISIONS>`. Resume point: <RESUME_POINT>.
  Continue from there with the answers the record gives. Report every uncommitted change you found
  at your next gate, and never discard one.
- Resource values reserved for this lane: <ENVIRONMENT>. Set them for every command that runs the
  checks or the application.
- Shared services: <SERVICES>. The orchestrator starts them.
```

### `tests/test_autopilot_skill.py`

New tests, each asserting on whitespace-collapsed text of the section it names, in the source and
in the copy `init` installs with `--integration claude` and with `--integration opencode` (one
parametrized helper yields the three texts):

- `test_hand_off_message_carries_branch_title_body_and_link` — *Close and hand off*: "the branch",
  `pull_request.title`, `pull_request.body`, `pull_request.url`, "never send one" (F4).
- `test_refill_runs_once_a_close_is_reviewed_not_at_hand_off` — *Dispatch*: `done-branch`,
  "without waiting for its hand-off"; *Close and hand off*: "values that no lane in use holds"
  (F5).
- `test_task_ids_are_unique_across_lanes` — *Dispatch*: "lock shared by every worktree of the
  clone", "never forbid lanes to create tasks"; the lane brief: "reserved across every worktree"
  (F6).
- `test_a_dispatch_expires_after_the_claim_grace` — *Dispatch*: `[git].claim_grace_minutes`,
  "reads `pending` again", "may dispatch it again" (F7).
- `test_a_new_session_resumes_a_run_by_handle_and_restarts_from_the_branch` — *Resume a run*:
  "never runs `autopilot start`", "by the handle", "restart the lane from its branch", "`silent`",
  "--handle <h> --state running"; the lane brief's restart section: "already exist", "do not stop
  because the branch exists", `<RESUME_POINT>`, "never discard" (F2).

The existing tests keep the portable text free of agent names and check that every `taskrail`
command and flag the skill shows exists.

### `DESIGN.md` (governing)

Exact text in Decision 1.

### `CHANGELOG.md`

One entry under *Unreleased*:

```markdown
- **Autopilot skill text from the T033 trial.** The `taskrail-autopilot` skill hands a branch off
  with its ID, branch, pull request title, body and link; refills a lane once its close is
  reviewed instead of at hand-off; says that `taskrail new` IDs never collide across lanes and that
  an unclaimed dispatch expires after `[git].claim_grace_minutes`; and resumes a run from a new
  session by lane handle, restarting a lane from its branch with a new restart section of the lane
  brief when the handle no longer reaches it (T055).
```

### Installed copies in this repository

`.taskrail/bin/taskrail upgrade`, as CLAUDE.md says, rewrites
`.claude/skills/taskrail-autopilot/SKILL.md`, `.claude/skills/taskrail-autopilot/references/lane-brief.md`
and their digests in `.taskrail/installed.json`.

### This artifact

And its row in `docs/chores/README.md`.

## Decisions needed

1. **DESIGN.md text.** Approve these edits:
   - §12.3, the first paragraph ("**The orchestrator** is the session…") becomes:

     ```markdown
     **The orchestrator** is the session the human talks to. It keeps a lane handle per task in the
     run file, and a lane commits everything it finishes on its branch. A compacted or new
     orchestrator session therefore rebuilds the run from `autopilot status` and the decision
     records, resumes each lane by its handle while the agent can still reach it, and otherwise
     restarts the lane from its branch with the lane brief's restart section, once the lane is
     stopped at a gate or `silent` (T033 F2, *implemented, T055*). In the T033 trial a new Claude
     Code session restarted a lane rather than resuming it; whether an earlier session's handle
     still reaches a lane is not verified.
     ```

   - §12.3, the lane-contract bullet "creates its worktree with git and claims inside it (§8);"
     becomes "creates its worktree with git and claims inside it (§8), or, restarted from its
     branch, works in the existing worktree and claims again;".
   - §12.7, in the `[[autopilot.resource]]` bullet, the sentence "The orchestrator therefore re-runs
     a lane's checks — at a gate or at hand-off (§12.8) — before its next `next`, while the lane's
     values are still its own." becomes:

     ```markdown
     The orchestrator therefore re-runs a lane's checks at each gate, the close review included,
     before its next `next`, while the lane's values are still its own. It refills as soon as a
     close is reviewed, not at hand-off (T033 F5), so the checks it re-runs at hand-off or after a
     merge (§12.8) use values no lane in use holds.
     ```

   - §12.8, in the *Hand-off is sequential* bullet, "each with its exact title and link" becomes
     "each announced to the human with its task ID, branch, exact pull request title and body, and
     link (T033 F4)".

   None of these touches the §12.1 rows (T049, T053, T054, T048), the §12.4 or §12.7 *A lane is in
   use* sentences (T048), the §8 table or the §12.3 sentence after "names the experimental
   background flag without requiring it." (T056). §6.3 and §12.4 already describe ID reservation
   and dispatch expiry, so F6 and F7 need no design text.
   Recommendation: approve. Alternative: leave DESIGN.md unchanged except §12.3's first paragraph,
   which is false as written; §12.7 and §12.8 would then contradict the refill and hand-off rules.
2. **Resource values after an early refill.** Refilling at the close lets `next` release the lane's
   resource values before the hand-off re-runs its checks, which a later lane may then hold.
   Recommendation: (a) the skill rule above — at hand-off and after a merge, run the checks with
   values no lane in use holds in `status`. Alternatives: (b) a CLI follow-up so a `done-branch`
   lane keeps its values until `handed-off`, which changes §12.7's "uses none" and delays reuse;
   (c) keep refilling at hand-off, which leaves F5 unfixed.
3. **Which installed copies the tests read.** Recommendation: copies installed by `init` into a
   fixture repository with each integration, as T056's test does, so the tests hold for any
   consumer. Alternative: also compare this repository's own `.claude/skills/taskrail-autopilot`
   with the sources, which would tie the tool's tests to this checkout's layout.
4. **When a `running` lane is restarted.** Recommendation: only once `status` reports it `silent`
   (20 idle minutes by default), so a sub-session still at work never shares the worktree.
   Alternative: restart as soon as the handle fails, which is faster but risks two writers in one
   worktree when an agent keeps sub-sessions alive after its parent session ends.
5. **Hand-off body.** Recommendation: always include the body, as the task row says ("branch, title
   and body"). Alternative: only when there is no link, as the skill says today — which is how the
   trial's messages came to omit it.
6. **CHANGELOG entry.** Recommendation: add it, as for T024 and T056. Alternative: none, since it is
   skill text only.

## Out of scope

- `taskrail autopilot close` and any other CLI change (T048, T047, T049, T051, T053, T054).
- The integration notes: the OpenCode note (T056) and the Claude Code note and command shape (T052).
- `references/gate-review.md` and `references/decision-record.md`, and the *Escalate* section.
- Verifying whether a new Claude Code session can message an earlier session's lane (T057).
- CLAUDE.md.

## Verification

- Each new test observed failing on the unchanged skill text, then passing after the edit.
- `init --integration claude --integration opencode` in a throwaway repository, reading the
  installed `taskrail-autopilot/SKILL.md` and `references/lane-brief.md` for the new rules.
- A scripted F6 check in a throwaway repository with two worktrees on different branches: an
  uncommitted `taskrail new` in each yields two different IDs.
- `.taskrail/bin/taskrail upgrade`, then the installed copies equal the sources plus the Claude Code
  note.
- The `test` check (`uv run pytest -q`); `lint` is not configured.
- `taskrail validate`.

Decisions 1–6 were approved at the scope gate as recommended; see the task's
[decision record](../autopilot/decisions/T055-fix-the-autopilot-skill-text-found-wrong.md). The
orchestrator's touch map also leaves the *Supervise* `overlaps` bullet to T051; this change does not
touch it.

Results:

- The five new tests, before any skill edit: `15 failed, 25 deselected` — each test failing for the
  source, the `claude` copy and the `opencode` copy, on `the branch` (F4),
  `without waiting for its hand-off` (F5), `` `taskrail new` reserves each id `` (F6),
  `a dispatch expires` (F7) and `no section 'Resume a run'` (F2). After the edits:
  `tests/test_autopilot_skill.py` `40 passed`, including the existing check that every `taskrail`
  command and flag the skill shows exists.
- Throwaway `git init` repository under `/tmp`, `taskrail --root <dir> init --integration claude
  --integration opencode` from this branch's source: the installed
  `.claude/skills/taskrail-autopilot/SKILL.md` has `## Resume a run` between `## After a merge` and
  `## Known conflict classes`, and the five new rules once each; the installed
  `references/lane-brief.md` has its two rules (lines 9 and 68), the ID bullet under
  `## How to work`, and `## Workspace (restart from the branch)` after the second rule.
- F6, in the same repository with an epic committed and two worktrees on branches `lane-a` and
  `lane-b`: `taskrail new --epic E01 --kind chore` in lane A returned `T001` and in lane B `T002`,
  with both rows still uncommitted (`TODO.md | 4 ++++` in each). The repository and worktrees were
  deleted afterwards.
- `.taskrail/bin/taskrail upgrade --json`: `updated` `.claude/skills/taskrail-autopilot/SKILL.md` and
  `references/lane-brief.md`, nothing skipped. The installed `lane-brief.md` is identical to the
  source; the installed `SKILL.md` differs from it only where the harness marker becomes the Claude
  Code note.
- `test`: `846 passed in 110.02s`. `lint`: not configured.
- `taskrail validate`: `56 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.

## Docs

The skill, its installed copies, DESIGN.md and the CHANGELOG changed in the implement stage. The
taskrail README describes the autopilot only at a level these fixes do not contradict, and the
T007 and T033 spike documents keep their historical wording. No follow-up tasks were opened.
