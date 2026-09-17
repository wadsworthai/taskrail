# T084 — Teach the skills the current-branch workflow, on-done commits and decisions gates

Kind: chore · Epic: E07 · Status: done

Contract: DESIGN.md §13.5's *The executor's close* and its workspace sentence, the skills' part of
§5.6 (decisions gates) and §12.6, the T084 row of §13.8 and the T084 row of TODO.md. Prior work:
none (`show` lists no artifact, branch or commit naming the task).

## Goal

T080–T083 made the CLI report a repository's workflow; the skills still follow the pull-request
workflow whatever it reports. A single maintainer working tasks straight on the checked-out branch
needs the skills to read that workflow from `taskrail show --json` and follow it:

- `task_branch` `"current"` — skip the workspace step and claim in the checkout the agent is in;
- `close.commit` `"on-done"` — commit nothing at stage boundaries; after `taskrail done`, make one or
  more logical commits of everything the task changed, the status change included;
- a stage `gate` `"decisions"` — stop as soon as a decision appears, never to approve the stage;
  carry reports to the next stop or the close;
- `close.review` `"report"` — after `done`, run `review --json` for a report and **ask the human
  before any push**; never rebase, publish or merge.

The rule that matters for safety (asking before a push) goes in the portable skill prose every agent
reads, not only in an integration note.

## Grounding: what the CLI reports today

On `befd863`, in a scratch repository (`git init`, `taskrail init --integration claude`, run from
this worktree's source) with `[git] worktree = "never"`, `task_branch = "current"`,
`commit = "on-done"`, one epic and chore T001 committed on `main`:

```
$ taskrail show T001 --json   # selected fields
task_branch "current"
branch "main"
branch_source "current"
base null
worktree null
worktree_base null
close {"commit": "on-done", "review": "report"}
scope always False          # stage, gate, effective commit
implement always False
docs conditional False
$ taskrail claim T001
claimed T001 as abigail@archlinux
$ taskrail done T001 --json
{"id": "T001", "status": "done", "commit": "on-done", "files": ["TODO.md"]}
$ git commit -m "chore(demo): tidy the thing (T001)"   # everything, the status change included
$ taskrail review T001 --json   # exit 0
  "head": "main", "fetched": false,
  "rebase": {"enabled": false, "onto": null, "needed": false,
             "reason": "[git].task_branch is \"current\": review does not rebase", ...},
  "push": {"enabled": false, "pushed": false, ...},
  "pull_request": {"provider": "none", "title": "chore: tidy the thing (T001)", "body": "...", "url": null},
  "published": false,
  "commits": [{"sha": "bdb9952…", "subject": "chore(demo): tidy the thing (T001)", "match": "suffix"}],
  "commits_total": 1, "upstream": null
$ taskrail review T001
T001 done on main; review reports only ([git].task_branch is "current")
1 commit(s) naming T001:
  bdb9952 chore(demo): tidy the thing (T001)
no upstream
reference title: chore: tidy the thing (T001)
push with git once the human approves
$ taskrail review T001 --publish   # exit 5
taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves
```

What the skills say today, file by file:

- `src/taskrail/skills/taskrail/SKILL.md` — step 3 always creates a branch (and worktree); step 4
  claims "from inside the workspace"; step 5 says "commit when `commit` is true" without the policy;
  step 8 always commits `done` on its own, fetches, rebases and publishes; step 9 reports a pull
  request link; *Gates* lists `always`, `conditional` and `none` only; the judgement-skip rule names
  `always` only; *Commit messages* assumes a squash-merged pull request.
- Executor skills (`taskrail-bug`, `-chore`, `-feature`, `-spike`) — every stage says "Commit" and
  "at the gate, the human approves/confirms/agrees/accepts"; their headings name the core kind's gate
  (`## scope — gate: always`), which an override may change.
- `src/taskrail/integrations/claude.md` and `opencode.md` — "At a gate, ask the human…"; nothing
  about a push question. The Claude checks note says checks run "in its worktree".
- `taskrail-autopilot` and its references — silent about `"decisions"` gates, which §12.6 allows in a
  run (the lane stops mid-stage, is recorded at the stage the decision arose in, and the orchestrator's
  first full diff review is the close review). `"current"` and `"on-done"` are refused by
  `autopilot start`, `extend` and `next`, so the autopilot needs nothing for them.
- Tests asserting skill text: `tests/test_autopilot_skill.py` (the core skill's installed copy equals
  the source with `CORE_CLAUDE_NOTES` / `CORE_OPENCODE_NOTES` verbatim, step 2 and step 5 phrases, the
  lane brief, gate review and Claude notes), `tests/test_conditional_stages.py` (step 5 phrases),
  `tests/test_row_on_base.py` (step 3 phrases, in source and installed copies),
  `tests/test_autopilot_read_first.py`, `tests/test_autopilot_overlaps.py`. None asserts the list of
  gate values or the close for `"current"`.

## Change set

| File (section) | Change |
|---|---|
| `src/taskrail/skills/taskrail/SKILL.md` step 2 *Inspect* | One sentence: `task_branch`, `close.commit`, `close.review` and each stage's `gate` and `commit` are the repository's workflow; read them before starting. |
| same, step 3 *Workspace* | Opens with: when `task_branch` is `"current"`, skip this step — the task is worked on the checked-out branch, `base` and `worktree` are `null`, and `new --workspace`, `workspace` and `branch` exit 5; stop and ask only when `branch` is `null` (a detached `HEAD`) or when the task's live claim (`claim.branch`) names another branch than `branch` (scope decision 9); any other checked-out branch is the task's. The rest of the step unchanged. |
| same, step 4 *Claim* | "From inside the workspace — under `"current"`, the checkout you are in —". |
| same, step 5 *Stages* | The judgement-skip rule adds that a `decisions` stage is skipped without asking (§5.6). The commit sentence reads the effective `commit`: under `close.commit` `"on-done"` every stage reports `false`, and nothing is committed before `done`; where an executor skill says to commit, that holds only when the stage's `commit` is `true`. Then "apply its gate (see *Gates*)". |
| same, step 8 *Close* | Split by `show`'s `close`: run `taskrail done <ID>`; commit as `close.commit` says — `"stages"`: the status change on its own; `"on-done"`: one or more logical commits of everything the task changed, the status change included. Then by `close.review`: `"publish"` — the existing fetch/rebase/title/publish bullets, unchanged; `"report"` — run `taskrail review <ID> --json` and read `head`, `commits`, `upstream` and `pull_request.title` for reference; never rebase, never run `--publish` (it exits 5), never merge; **ask the human before any push**, with what `upstream.ahead` and `commits` say it would send, and push with plain `git push` only once approved, never forced. |
| same, step 9 *Hand off* | Under `"report"`: the branch, each commit, checks, artifact, follow-ups, whether the human approved a push and whether it was pushed, and the reference title; no link. |
| same, *Gates* | Adds `decisions` — stop mid-stage as soon as a decision appears, ask it as a direct question with recommendation and alternatives, continue once answered; never stop at the stage's end to approve or report it; carry what `conditional` would report (follow-ups, results, skipped stages) to the next stop or the close hand-off. Defines a decision as §5.6 does, and says that under a `decisions` gate what an executor skill calls "approved" is what the artifact records, which the human sees at the close. The gate report paragraph also covers a decision stop and the push question. Adds: the gate is the one `show` reports, not the one an executor skill's heading names. |
| same, *Commit messages* | Under `"current"` the commits land on the checked-out branch as they are: name the task in each subject — e.g. ending in `(<ID>)` — so `review` lists them in `commits`. |
| `src/taskrail/skills/taskrail-{bug,chore,feature,spike}/SKILL.md` intro | One identical paragraph after "Follow the `taskrail` skill's procedure; this skill defines the stages.": the gate in each heading is the core kind's default and `show` reports the effective one; "Commit" in a stage holds only when that stage's effective `commit` is `true`; under a `decisions` gate, where a stage says the human approves at the gate, record it in the artifact and continue, stopping only for a decision — every "stop and ask" below is one. No stage text changes. |
| `src/taskrail/integrations/claude.md` (`taskrail` section) | "At a gate, **at a decision and before a push**, ask the human with AskUserQuestion…"; subagent bullet: "end your turn with the gate report **or the question**"; checks bullet: "it runs them there — in the checkout under `task_branch = "current"` —". |
| `src/taskrail/integrations/opencode.md` (`taskrail` section) | Same two ask/subagent changes in its words. |
| `src/taskrail/skills/taskrail-autopilot/SKILL.md` *Answer a gate* | One paragraph: a lane at a `"decisions"` stage stops mid-stage, only for a decision; record it with `--gate <stage>` naming the stage the decision arose in; answer the decision; there are no stage-end stops, so review the lane's whole diff at the close by every criterion of `references/gate-review.md`. |
| `src/taskrail/skills/taskrail-autopilot/references/lane-brief.md` *Gates* | One bullet: a stage whose gate is `"decisions"` stops only when a decision appears, as the `taskrail` skill says; carry what you would report to your next stop or the close. |
| `src/taskrail/skills/taskrail-autopilot/references/gate-review.md` *Close* | One bullet: when a stage's gate was `"decisions"`, apply that stage's criteria above to the close review. |
| `.claude/skills/**` and `.taskrail/installed.json` | Refreshed by `.taskrail/bin/taskrail upgrade`; never edited by hand. |
| `tests/test_skills_current_branch.py` (new) | Asserts, in the sources and in the copies `init` installs for `claude` and `opencode`: step 3 skips the workspace under `"current"`; step 4 claims in the checkout; step 5 reads the effective commit and nothing before `done` under `"on-done"`; step 8's `"on-done"` commits including the status change, `"report"` running `review --json`, asking before any push, never rebase/publish/merge; *Gates* lists `decisions` with "as soon as a decision appears", "never … to approve", carrying reports; each executor skill's paragraph; the Claude and OpenCode notes on decisions and push questions; the autopilot's `"decisions"` lines. Also that every `taskrail` command and flag the core skill shows exists in the parser, and that the core skill still has the `"publish"` close. |
| `tests/test_autopilot_skill.py` | `CORE_CLAUDE_NOTES` and `CORE_OPENCODE_NOTES` follow the new note text (they are asserted verbatim). |
| `README.md` new section *Working on the checked-out branch* (between *Task kinds* and *Autopilot*) | The single-maintainer configuration: `[git] worktree = "never"`, `task_branch = "current"`, `commit = "on-done"`, what each does and that each works alone; an override `.taskrail/overrides/chore/kind.toml` — a complete descriptor, since an override replaces the kind (§5.2) — with `gate = "decisions"` on its stages; that the skills then commit after `done`, ask before any push, and the autopilot refuses such a repository. The *Use* block's `review` comment adds "(a report only under task_branch = \"current\")". |
| `DESIGN.md` §8 *Skills* | A new paragraph block **The repository's workflow**, before *Integrations*: the core skill reads `task_branch`, `close.commit`, `close.review` and each stage's `gate` from `show`; the workspace sentence and *The executor's close* moved from §13.5 (its four steps), plus the decisions-gate behaviour of the skills pointing to §5.6. The *Integrations* table's `taskrail` notes cells name the ask-before-push note. |
| `DESIGN.md` §13.5 | The remaining body (*The executor's close* and the workspace sentence) replaced; the pointer becomes `*Implemented (T083): now §7.1 …, with close.review in §5.1 and the show and review rows of §7; implemented (T084): the executor's close and the skipped workspace step, now §8.*` |
| `DESIGN.md` §13.4 | Pointer gains "; the skills' part (T084), now §8". |
| `DESIGN.md` §13.8 | T084 row ends "; *implemented (T084)*". |
| `DESIGN.md` §13 heading, status line, §11, §5.3 | Only as decision 1 says. |
| `CHANGELOG.md` Unreleased | One bullet: the skills follow `task_branch`, `close.commit`, `close.review` and `"decisions"` gates, and the README documents a single-maintainer configuration (T084). T081's bullet only as decision 3 says. |
| `docs/chores/T084-…md`, `docs/chores/README.md` | This artifact; its index row at implement. |
| `TODO.md` | Only through `taskrail done T084` at the close. |

## Decisions needed

1. **§13 is now fully implemented: say so?** After T084 every part of §13 lives elsewhere.
   *Recommendation:* heading `## 13. Current-branch workflow (implemented)` like §12; the status
   line becomes "**implemented.** Decided at T079's scope gate (links) and built by T080–T084
   (§13.8); each part now lives in §4–§8 and §12, and the subsections below point there"; the
   introduction's need and table stay as the rationale; §11's phase 3 reads "(E07, implemented)";
   §5.3's last sentence ("planned to become configurable … (§13)") becomes "are configurable for a
   repository worked on its checked-out branch (§4, §5.6, §6.4, §7.1, §8)". *Alternatives:* leave
   the status line, heading, §11 and §5.3 as they are for a separate docs task; or change only the
   status line.
2. **Where the executor's close moves.** *Recommendation:* §8 *Skills*, a **The repository's
   workflow** block before *Integrations*, since it is skill behaviour and §7.1 already holds the
   CLI's half. *Alternative:* an executor paragraph at the end of §7.1's *On the current branch*.
3. **T081's CHANGELOG bullet** ends "The skills still commit per stage until they learn
   `close.commit` (T081)", which this task makes false before any release. *Recommendation:* delete
   that sentence here. *Alternative:* leave it and let the new bullet supersede it.
4. **Integration notes.** *Recommendation:* extend the Claude and OpenCode `taskrail` notes so the
   ask tool and the subagent hand-back cover a decision stop and the push question, and correct the
   Claude checks note for `"current"`; update the two verbatim test constants. The asking rule itself
   is in the portable prose either way. *Alternative:* no integration change.
5. **Executor skills.** *Recommendation:* one identical paragraph in each of the four (gate and commit
   come from `show`; "approves at the gate" is a record under `decisions`), leaving stage text alone.
   *Alternatives:* rewrite each stage's "Commit" and "the human approves" lines; or rely on the core
   skill alone.
6. **Autopilot skill.** *Recommendation:* the three small `"decisions"` additions above (answer a gate,
   lane brief, gate review), since §12.6 allows such gates in a run and the skill is silent.
   *Alternative:* no autopilot change (the orchestrator treats it like any gate).
7. **Commit subjects under `"current"`.** *Recommendation:* the core skill says to name the task in
   each subject (ending in `(<ID>)`), so `review`'s `commits` lists them for the push question.
   *Alternative:* say nothing; `review` then may list no commits.
8. **The seeded `.taskrail/config.toml`** that `init` writes has no `task_branch` or `commit` line.
   *Recommendation:* leave it; §4 and the new README section document them, and a seeded file is
   code with its own tests. *Alternatives:* add commented lines here (widening into `install.py` and
   its tests); or open a follow-up chore.

## Decisions at the scope gate

Recorded in [the decision record](../autopilot/decisions/T084-teach-the-skills-the-current-branch-work.md):
decisions 1–7 as recommended; 8, leave `init`'s seeded config with no follow-up; 9 (orchestrator),
step 3's stop under `"current"` is concrete — a detached `HEAD` or a live claim on another branch —
and tested. The change set above reads as amended by decision 9.

## Out of scope

- Any CLI behaviour: T080–T083 built it; the skills describe what it reports.
- `.claude/skills/**` by hand — refreshed only by `taskrail upgrade`.
- The seeded config template (decision 8), `examples/`, CLAUDE.md, this repository's own config.
- Rewriting §13.1, §13.6 and §13.7 beyond their existing marks.

## Verification

- `taskrail checks T084` (`uv run pytest -q`) passes, including the new test file, in the sources and
  installed copies for both integrations.
- `.taskrail/bin/taskrail upgrade` refreshes `.claude/skills/`; `diff` of each installed `SKILL.md`
  against its source shows only the integration notes.
- A real walk-through in a scratch repository with the README's configuration and override: `show`
  reports the decisions gates, `on-done` and `report`; following the installed skill text step by
  step (claim in the checkout, no stage commits, `done`, one logical commit, `review --json`,
  `--publish` exit 5) matches what the skill says, and no command the skill shows is refused.
- `taskrail validate` reports no errors; `grep` for private names in the diff finds none.

### Results (implement)

- **Checks.** `.taskrail/bin/taskrail checks T084 --stage implement`: `1180 passed in 170.69s`;
  `lint: not configured`; `T084 in <worktree>: passed`, exit 0. Before the new file, the full suite
  with only the notes constants updated: `1134 passed`. The new file alone:
  `uv run pytest -q tests/test_skills_current_branch.py` → `46 passed` (source, claude and opencode
  copies of each assertion; the notes and portability tests; every `taskrail` command and flag the core
  skill shows exists in the parser, subcommands such as `epic add` included).
- **Installed copies.** `.taskrail/bin/taskrail upgrade` updated `.claude/skills/taskrail`,
  `taskrail-autopilot` (`SKILL.md`, `references/gate-review.md`, `references/lane-brief.md`) and the
  four executor skills, and `.taskrail/installed.json`. `diff` of each source against its copy: the
  executor skills and references are identical; `taskrail` and `taskrail-autopilot` differ only at the
  `<!-- taskrail:harness -->` marker, where the Claude Code notes are inserted.
- **Walk-through.** A scratch repository with a bare `origin` that `main` tracks,
  `taskrail init --integration claude`, the README's `[git]` block and its chore override copied
  verbatim from the README:
  - `validate` → exit 0, `0 error(s), 2 warning(s)` — `kind-check-unknown` for `test` and `lint`,
    which the seeded config leaves undefined, as for any kind;
  - `show T001 --json` → `task_branch "current"`, `branch "main"`, `branch_source "current"`, `base`,
    `worktree`, `worktree_base` `null`, `close {"commit": "on-done", "review": "report"}`, stages
    `scope`, `implement`, `docs` each `gate decisions commit False`, `source override`;
  - step 3 skipped: `workspace T001`, `branch T001 x` and `new … --workspace` each exit 5 with
    `taskrail: [git].task_branch is "current": tasks have no branch of their own; work on the checked-out branch`;
  - step 4: `claim T001` → `claimed T001 as …`, exit 0;
  - decision 9's two stops are visible to the executor: on `main` with its own claim,
    `branch "main" claim.branch "main"` (go on); after `git switch -c topic`,
    `branch "topic" claim.branch "main"` (stop and ask); after `git switch --detach`,
    `branch null claim.branch "main"` (stop and ask);
  - stages: artifact and a change written, nothing committed (`git status`: `?? docs/`, `?? thing.txt`);
  - step 8: `done T001` → `T001 done` / `commit everything T001 changed now, the status change included`;
    one commit `chore(demo): tidy the thing (T001)` left the tree clean;
  - `review T001 --json` → `head "main"`, `fetched false`, `rebase.enabled false`, `push.enabled false`,
    `pull_request.url null`, `published false`, `commits` [the `(T001)` commit, `match "suffix"`],
    `upstream {"ref": "origin/main", "ahead": 2}` — what the push question names; the text ends
    `push with git once the human approves`;
  - `review T001 --publish` → exit 5,
    `taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves`;
  - nothing was pushed: `origin`'s `main` is still `6a4a725`, `HEAD` is `b74600c`.
- **Backlog.** `.taskrail/bin/taskrail validate` → `73 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`.
- **Publishing constraint.** The diff names no host, path, person or project beyond the repository's
  own public URL.

## Decisions at the implement gate

Recorded in [the decision record](../autopilot/decisions/T084-teach-the-skills-the-current-branch-work.md):
the implement stage approved, with fixes applied in `0354fbc` —

- step 4: under `"current"`, where `taskrail branch` exits 5, a claim `warning` means a detached
  `HEAD` (`taskrail: warning: T001 was claimed on a detached HEAD: check out a branch to work the task on`
  in the scratch repository): check out a branch before any edit; tested by
  `test_a_claim_warning_on_the_current_branch_means_a_detached_head`;
- step 8: `done` runs in the checkout under `"current"`, where no branch is recorded; asserted in
  `test_the_close_commits_as_close_commit_says`;
- the lines added in steps 3–5 rewrapped to the file's width; the lines still over 100 columns are
  the ones `befd863` already had (the frontmatter description, the `git worktree add` command and
  two prose lines);

and CLAUDE.md's Layout comment now reads "the current-branch workflow §13" (`927e388`, scope amended).
After `.taskrail/bin/taskrail upgrade` (`updated .claude/skills/taskrail/SKILL.md`),
`.taskrail/bin/taskrail checks T084` → `1183 passed in 166.35s`, `lint: not configured`, passed.

## Docs

README (*Working on the checked-out branch*, the `review` comment), DESIGN.md (§5.3, §8, §11, §13),
CHANGELOG.md and CLAUDE.md were brought in line during implement and the implement gate. The skills
are themselves the documentation this task changes. No follow-up task was opened, and nothing is
left to decide, so the docs gate (conditional) does not stop.
