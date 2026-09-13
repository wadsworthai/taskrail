# T023 — Report signs of prior work on a task in show

Kind: feature · Epic: E05 · Status: implemented

## Behaviour

Before starting a task, an executor should notice when someone may already have worked on it:
a document left behind, a branch, or commits. Today it only finds out when `git worktree add`
fails on an existing branch, and never finds out about an artifact or commits on another
branch or already on the mainline.

After this change, `taskrail show <ID>` reports these mechanical signals in a new
`prior_work` object. They are informational only: `show` still exits 0 and the task's `state`
does not change. The executor mentions them at its first gate; judging whether the
description's premises still hold stays with the agent.

```json
"prior_work": {
  "artifact": ["working tree", "main", "origin/main"],
  "branches": ["T012-round-totals", "origin/T012-round-totals"],
  "commits": [
    {"sha": "d3d308e…", "subject": "fix(billing): round totals half-up (T012) (#4)", "match": "suffix"},
    {"sha": "2feba88…", "subject": "chore(T012): mark done", "match": "scope"}
  ],
  "commits_total": 2
}
```

- **`artifact`** — where the task's artifact file (the `artifact` path `show` already reports)
  exists: `"working tree"` for the current checkout, then each local branch and
  remote-tracking branch whose tip contains it. All tips are read through one
  `git cat-file --batch` process.
- **`branches`** — the task's branch (the `branch` field) as a local branch and on every
  remote-tracking namespace, e.g. `origin/<branch>`.
- **`commits`** — commits reachable from `HEAD`, local branches and remote-tracking branches
  (not tags, stashes or the `refs/taskrail/` claim refs) whose **subject** names the task in
  one of these forms, newest first:
  - `prefix` — the subject starts with the ID: `T012 round totals`, `T012: …`;
  - `scope` — the ID is, or is part of, a Conventional Commits scope: `chore(T012): …`,
    `fix(billing,T012)!: …`;
  - `suffix` — a squash-merge title ending in `(T012)`, optionally followed by a pull or merge
    request number: `feat(taskrail): … (T012) (#4)`, `… (T012) (!4)`;
  - `branch` — the subject contains the task's branch name, as in
    `Merge pull request #1 from owner/T012-round-totals`.

  A subject that only mentions the ID elsewhere (`chore(T001): open follow-ups T012 and T013`)
  is not reported: backlog maintenance names task IDs all the time. The ID is matched
  case-sensitively and as a whole word, so `T012` never matches `T0123`. At most 10 commits
  are listed; `commits_total` gives the full count.

The text output of `show` adds one `prior work:` line per signal, only when there is one.
Outside a git repository only the working-tree artifact check runs, and the lists are empty.

`list` and `next` do not compute `prior_work`: they cover many tasks and the history search
would run once per task.

The core skill's step 2 (Inspect) gains one sentence: if `prior_work` reports anything, look
at it, mention it at the first gate, and check that the description's premises still hold;
the signals never block on their own.

## Acceptance criteria

1. In a repository with no artifact, branch or matching commit, `show <ID> --json` returns
   `prior_work` with empty `artifact`, `branches` and `commits`, and `commits_total` 0.
2. An artifact file present only in the working tree is reported as `["working tree"]`; one
   committed on a local branch and on a remote-tracking branch lists both refs; the check
   reads branch tips, not history.
3. The task branch existing locally, on a remote-tracking branch, or both is listed in
   `branches`; another task's branch that merely shares a prefix is not.
4. A commit on any local or remote-tracking branch, including one not merged into the current
   branch, is reported with `match` `prefix`, `scope`, `suffix` or `branch` for each of the
   forms above; a subject that only mentions the ID elsewhere, names a longer ID (`T0123`), or
   carries the ID only in the message body is not.
5. Commits reachable only from `refs/taskrail/claims/*` or tags are not reported, and a commit
   reachable from several branches appears once.
6. With more than 10 matching commits, `commits` holds the 10 newest and `commits_total` the
   full count.
7. `show` still exits 0 and reports the same `state` whatever `prior_work` contains, and
   outside a git repository `prior_work` is present with empty git-derived lists.
8. The text output of `show` includes a `prior work:` line for each kind of signal present and
   none when there is none.
9. `list --json` and `next --json` do not contain `prior_work`.
10. The core skill's step 2 tells the agent what to do with the signals; installed copies are
    refreshed with `taskrail upgrade`, and `DESIGN.md`, `README.md` and `CHANGELOG.md` describe
    the field.

## Test coverage

In `tests/test_prior.py`, against temporary git repositories and a bare local
remote.

| Criterion | Tests |
|---|---|
| 1. Nothing found | `test_nothing_found_reports_empty_signals` |
| 2. Artifact in the working tree and on branch tips | `test_artifact_in_the_working_tree_only`, `test_artifact_on_local_and_remote_tracking_branch_tips`, `test_artifact_check_reads_branch_tips_not_history` |
| 3. Task branch locally and on remotes | `test_task_branch_locally_and_on_a_remote`, `test_a_branch_sharing_the_prefix_is_not_the_task_branch` |
| 4. Subject forms, unmerged branches, non-matches | `test_commit_subject_forms` (8 cases), `test_subjects_that_do_not_name_the_task` (6 cases), `test_commits_on_unmerged_local_and_remote_branches` |
| 5. Claim refs and tags excluded; no duplicates | `test_claim_refs_and_tags_are_not_searched_and_commits_appear_once` |
| 6. Cap and total | `test_commits_are_capped_newest_first` |
| 7. Exit code and state unchanged; outside git | `test_signals_never_change_exit_code_or_state`, `test_state_is_the_same_with_and_without_signals`, `test_outside_git_only_the_working_tree_is_checked`, `test_repository_without_commits` |
| 8. Text output | `test_text_output_lists_each_kind_of_signal` |
| 9. Not in `list` and `next` | `test_list_and_next_do_not_search_for_prior_work` |
| 10. Skill and documentation | reviewed at the implement gate; `test_skills_have_only_frontmatter_every_agent_accepts` still passes |

## Affected areas

- `src/taskrail/prior.py` — new module: artifact, branch and commit signals.
- `src/taskrail/cli.py` — `cmd_show` adds `prior_work` to its JSON and text
  output (a small hunk after `kind_descriptor`; `task_dict` in `query.py` is not changed).
- `src/taskrail/skills/taskrail/SKILL.md` — step 2; installed copies under
  `.claude/skills/` refreshed.
- `tests/test_prior.py` — new tests against temporary git repositories.
- `DESIGN.md` (§7 `show` row), `README.md` (`show` line), `CHANGELOG.md`
  (`## Unreleased`).

## Out of scope

- Blocking, warning exit codes or a changed `state` because of prior work.
- Judging whether the description's premises still hold: that stays with the agent.
- Fetching: like `base`, `show` reads remote-tracking branches as they are and never touches
  the network.
- Searching message bodies, trailers (`Reopens:`), tags, pull requests on the host, or other
  clones' worktrees on disk.
- Reporting which branches contain each commit: the executor can run
  `git branch -a --contains <sha>` when it matters.
- A configuration switch or flag to disable the history search.

## Open questions and risks

- **Cost on large histories.** The commit search is one `git log HEAD --branches --remotes
  -F --grep=<ID>` process: git walks the union of all branch histories and pre-filters in C,
  and Python classifies only the subjects that contain the ID. On this repository it takes
  about 4 ms; on a repository with around a million commits it can take seconds on every
  `show`. A switch to turn it off could follow if a consumer needs it.
- **Many remote branches.** The artifact check reads one blob per branch tip in a single
  process; with thousands of remote-tracking branches it still reads them in one pass.
- **Custom commit conventions.** Repositories that name tasks differently (for example
  `[T012]`) get no `commits` signal. The four forms cover the conventions this repository and
  the motivating consumer use; more can be added later.
- **Expected signals once work starts.** After the claim, `show` run from the task's own
  worktree reports its own branch, and later its artifact and commits. The skill places the
  check at step 2, before the workspace exists, so these do not read as someone else's work.

## Verification

Run through this repository's wrapper (`.taskrail/bin/taskrail show <ID>`, text and `--json`)
in the task worktree, against the real history with the `main`, `origin/main` and four task
branches present:

- `T013` (done, squash-merged): `artifact` lists the working tree, every task branch, `main` and
  `origin/main`; one commit, `d3d308e … (T013) (#4)`, matched as `suffix`. The T015 squash
  commit, whose body mentions T013, is not reported.
- `T001` (done, merged with a merge commit): four commits — `f76164b Merge pull request #1 from
  …/T001-validate-the-taskrail-skills-by-working` as `branch`, and three `chore(T001)` /
  `docs(T001)` subjects as `scope`.
- `T014` (pending): all lists empty and no `prior work:` line, although the subject
  `chore(T001): open follow-ups T013 and T014, …` mentions it.
- `T023` (claimed, from its own worktree): its artifact in the working tree and on its branch,
  its branch, and its two commits ending in `(T023)` as `suffix`; the orchestrator's
  `docs(taskrail): record the autopilot's T023 …` commits only mention the ID and are not
  reported.

No difference from the plan was found.
