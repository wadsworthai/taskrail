# T083 — Close a current-branch task without fetch, rebase or publish

Kind: feature · Epic: E07 · Status: verified

Contract: DESIGN.md §13.5 (its CLI part) and the `close.review` part of §13.3, with the T083 row of
§13.8. Prior work: none (`show` lists no artifact, branch or commit naming the task).

## Premise, checked on the current mainline

On `59adba0`, in a scratch repository with `[git] worktree = "never"`, `task_branch = "current"`, a
bare `origin` that `main` tracks, and T001 claimed, committed and marked done on `main`:

- `taskrail review T001 --json` fetches `origin`, then exits 2 with
  `taskrail: could not determine the base of main`, because `base_dict` returns `None` under
  `"current"`;
- `taskrail review T001 --publish --json` exits 2 with the same message;
- `show T001 --json` reports `"close": {"commit": "stages"}`, without `review`.

The premise holds.

## Behaviour

With `[git].task_branch = "current"`, `taskrail review <ID>` is a report:

- **Order.** Load and the invalid-backlog check as today; exit 3 for an unknown ID; then `--publish`
  exits **5** with
  `taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves`;
  then exit 5 unless the task is `done` or `discarded` in the checkout (the existing message).
- **Nothing on the network or the branch.** No branch-record fetch, no `git fetch`, no base choice,
  no rebase suggestion, no push, and no refusal because of which branch is checked out.
- **`--json` keeps every key** it has under `"task"`: `id`; `head` the checked-out branch (`null` on
  a detached `HEAD`); `target` the mainline; `remote` and `remote_source` resolved as today, without
  fetching; `fetched` `false`; `rebase` `{enabled: false, onto: null, diverged: false, needed: false,
  reason: "[git].task_branch is \"current\": review does not rebase", dependency: null}`; `push`
  `{enabled: false, pushed: false, command: null, error: null}`; `pull_request` with `provider`,
  `title` and `body` rendered as today (`--type`, `--scope`, `--breaking` and the discard rule apply)
  and `url` `null`; `published` `false`.
- **Adds** `commits`: commits reachable from `HEAD` only whose subject names the task in the `prefix`,
  `scope` or `suffix` form of §7.2, newest first, at most 10, each `{sha, subject, match}`, with
  `commits_total`; and `upstream`: `{ref, ahead}` — the checked-out branch's upstream as git
  abbreviates it (`origin/main`) and `git rev-list --count <upstream>..HEAD` — or `null` when the
  branch has no upstream, the upstream ref does not exist, or `HEAD` is detached.
- **Text.** One line `<ID> <status> on <head>; review reports only ([git].task_branch is "current")`,
  the commits naming the task (`<sha7> <subject>`), the upstream line
  (`upstream <ref>: <n> commit(s) not pushed` or `no upstream`), the reference title, and
  `push with git once the human approves`.
- **Under `"task"`** `review` is unchanged.

`show --json`'s `close` gains `review`: `"publish"` under `task_branch = "task"`, `"report"` under
`"current"`.

## Acceptance criteria

1. Under `"current"`, `review <ID> --json` on a done task exits 0 and reports `head` = the checked-out
   branch, `target` = the mainline, `fetched` `false`, `rebase.enabled` `false` with a `reason`
   containing `[git].task_branch`, `push.enabled` `false`, `pull_request.title` rendered as under
   `"task"`, `pull_request.url` `null`, `published` `false`.
2. It fetches nothing and pushes nothing: with a remote whose `main` has a commit the clone lacks,
   `origin/main` is unchanged after `review`, and the remote's `main` is unchanged too.
3. It works on the mainline itself and on a non-task branch (no "run review on the task branch"
   refusal).
4. `commits` lists only commits on `HEAD` whose subject names the task in `prefix`, `scope` or
   `suffix` form, newest first, capped at 10 with `commits_total` holding the full count; a commit
   on another branch naming the task, and a subject mentioning the ID elsewhere, are not listed.
5. `upstream` is `{ref: "origin/main", ahead: N}` with N the commits `HEAD` has that the upstream
   lacks; `null` for a branch without an upstream.
6. `--publish` exits 5 with the message above, also for a pending task and before any other check
   after the task is found (a pending task gets the publish refusal, not the status one); nothing is
   pushed.
7. A pending task without `--publish` exits 5; an unknown ID exits 3.
8. The text output names the commits, the upstream and the reference title.
9. `show --json` reports `close.review` `"report"` under `"current"` and `"publish"` under `"task"`.
10. Under `"task"`, the existing `review` tests pass unchanged.

## Affected areas

- `src/taskrail/cli.py`
  - `cmd_review`: right after the task is found, one branch `if branches.is_current(config): return
    _review_current(args, project, task)`; the rest of the function is untouched.
  - new `_review_current(args, project, task)`: the publish refusal, the status check, the report
    and its text. The title and body come from the same `review.pr_title` / `review.pr_body` calls,
    so a small helper `_review_title_body(args, project, task, kind, since)` is extracted from
    `cmd_review` and used by both (a pure move, no behaviour change).
  - `cmd_show`: `data["close"]` gains `"review"`.
- `src/taskrail/review.py`: `CURRENT_PUBLISH_REFUSAL` message constant; `upstream(root) -> dict | None`.
- `src/taskrail/prior.py`: `matching_commits` gains an optional `revisions` argument (default: today's
  `HEAD`, `--branches`, `--remotes`), so `review` searches `HEAD` alone with the same forms and
  `branch=None` (no `branch` form).
- `tests/test_review_current.py` — new: a current-branch fixture repository with a bare remote.
- `DESIGN.md`
  - §7 table: the `show` row's "planned: `close.review` (§13.3)" becomes the implemented
    `close.review` description; the `review` row's "planned: report only under
    `task_branch = "current"` (§13.5)" becomes implemented, pointing at §7.1.
  - §7.1: the *Planned (§13.5)* sentence of the introduction is replaced by a paragraph
    **On the current branch** holding §13.5's CLI bullets.
  - §5.1: the `close.commit` sentence gains `close.review` (the close in one place).
  - §6.4 (**The current branch**): the bullet ending "No command pushes a branch." names `review`
    as a report (§7.1).
  - §13.3: its "Still planned for T083: …" sentence is dropped.
  - §13.5: the CLI bullets become the one-line pointer
    `*Implemented (T083): now §7.1 (**On the current branch**), with `close.review` in §5.1 and the
    `show` and `review` rows of §7.*`; **The executor's close** (T084) and the workspace sentence stay
    as they are, planned.
  - §13.8: the T083 row ends `; *implemented (T083)*`.
  - Not touched: §13's introduction and summary table, other tasks' lines.
- `CHANGELOG.md` — one bullet under Unreleased.
- `docs/features/README.md` — this artifact's row.

## Out of scope

- The skills, integration notes and README (T084): the executor's close under `"current"` (commit
  per `close.commit`, report, ask before any push) stays planned in §13.5.
- `show`'s text form: no `close.review` line (question 1).
- `list`/`next` entries: `close` stays `show`-only.
- `--no-fetch` and `--no-push` are accepted under `"current"` and change nothing.

## Open questions and risks

1. **`show`'s text form for `close.review`.** §13.3 specifies only JSON. Recommendation: no text
   line; `close.review` follows from `task_branch` alone, and the default output stays unchanged.
   Alternative: a line `review report ([git].task_branch)` under `"current"`, as T081 did for on-done.
2. **Reopens trailers in the reference body.** Under `"task"` the body lists `Reopens:` trailers from
   commits since the rebase base; under `"current"` there is no base. Recommendation: commits since
   the upstream (`<upstream>..HEAD`), i.e. what a push would send; with no upstream, all of `HEAD`
   (what `reopened_ids` does today without a base). Alternative: all of `HEAD` always, which on a
   long-lived mainline lists every reopen ever made.
3. **Detached `HEAD`.** §13.5 says review does not refuse because of the branch. Recommendation: do
   not refuse; `head` and `upstream` are `null`, `commits` still searches `HEAD`. Alternative: exit 5
   asking to check out a branch, as `claim` warns.
4. **`upstream` when the configured upstream ref is gone** (deleted remote branch).
   Recommendation: `null`, as for no upstream, since there is nothing to count against.
   Alternative: `{ref, ahead: null}`.
5. **Rebase reason wording.** §13.5 requires only that it names `[git].task_branch`.
   Recommendation: `[git].task_branch is "current": review does not rebase`.

Answered at the plan gate
([decision record](../autopilot/decisions/T083-close-a-current-branch-task-without-fetc.md)): 1–5 as
recommended; the plan approved.

## Implementation notes

- `cmd_review` branches into `_review_current` right after the task is found, so under `"current"`
  nothing of the task-branch path runs — not even the branch-record fetch. The status check and the
  title and description moved into `_review_closed` and `_review_title_body`, shared by both paths
  without a behaviour change under `"task"`.
- `prior.matching_commits` takes `head_only=True` instead of the planned `revisions` list: the only
  other caller needs today's refs, and a boolean keeps both call sites obvious. Under `head_only`, a
  repository without commits returns `[]`.
- `review.upstream` resolves `@{upstream}` to its full ref, counts `<ref>..HEAD` against that full ref
  (a local branch named like the remote-tracking one cannot be picked instead), and reports the name
  without `refs/remotes/` or `refs/heads/`. A detached `HEAD`, no upstream, or an upstream whose ref
  is gone all give `null`.
- `tests/test_commit_policy.py` compared `show`'s whole `close` object with `{"commit": …}`; its four
  assertions now read `close.commit`, which is what they test.
- DESIGN.md: §5.1 (`close.review`), §6.4 (the current-branch bullet naming `review`), the `show` and
  `review` rows of §7, and a new paragraph **On the current branch** in §7.1 replacing its *Planned*
  sentence; §13.3 loses its "Still planned for T083" sentence, §13.5's CLI bullets become a pointer
  that also says the executor's close stays planned (T084), and the T083 row of §13.8 is marked.

## Acceptance criteria and tests

All in `tests/test_review_current.py`.

| # | Tests |
|---|---|
| 1 | `test_review_reports_on_the_mainline`, `test_review_title_options`, `test_discarded_task_is_reported` |
| 2 | `test_review_fetches_and_pushes_nothing` |
| 3 | `test_review_reports_on_the_mainline`, `test_review_runs_on_any_branch` |
| 4 | `test_commits_on_head_in_the_three_forms`, `test_commits_are_capped_at_ten` |
| 5 | `test_review_reports_on_the_mainline`, `test_upstream_ahead_after_a_push`, `test_review_runs_on_any_branch` (no upstream), `test_upstream_gone_is_null` (decision 4) |
| 6 | `test_publish_is_refused_before_anything_else` |
| 7 | `test_pending_and_unknown_tasks` |
| 8 | `test_text_output` |
| 9 | `test_show_close_review` |
| 10 | the existing `tests/test_review.py` and the rest of the suite, unchanged |
| decision 2 | `test_reopens_since_the_upstream`, `test_reopens_without_an_upstream_read_all_of_head` |
| decision 3 | `test_detached_head_is_reported` |

Answered at the implement gate
([decision record](../autopilot/decisions/T083-close-a-current-branch-task-without-fetc.md)): the
implementation approved, with both deviations (`head_only`, the narrowed `close.commit` assertions)
accepted.

## Verification

Run with this branch's CLI (`uv run --project <worktree> taskrail --root <scratch>`) against a scratch
repository: `[git] worktree = "never"`, `task_branch = "current"`, a bare `origin` that `main` tracks,
T001 (feature) claimed, committed as `feat(demo): add a (T001)` and `T001 second step`, marked done and
committed; T002 (bug) pending.

| Step | Seen |
|---|---|
| `review T001` | exit 0: `T001 done on main; review reports only ([git].task_branch is "current")`, `2 commit(s) naming T001:` with both commits, `upstream origin/main: 3 commit(s) not pushed`, `reference title: feat: base task (T001)`, `push with git once the human approves` |
| `review T001 --json` | exit 0: `head` `main`, `target` `main`, `remote` `origin` from `branch.main.remote`, `fetched` `false`, `rebase` disabled with reason `[git].task_branch is "current": review does not rebase`, `push.enabled` `false`, `pull_request` title `feat: base task (T001)`, body naming the task and artifact, `url` `null`, `published` `false`, `commits` (`prefix`, `suffix`), `commits_total` 2, `upstream` `{origin/main, 3}` |
| `review T001 --publish` | exit 5: `taskrail: [git].task_branch is "current": review does not publish; push with git once the human approves` |
| `review T002`, `review T002 --publish` (pending) | exit 5 with the done/discard message; exit 5 with the publish refusal |
| `review T999` | exit 3: `taskrail: no task `T999`` |
| origin's `main` and local `origin/main` before and after | both `c1e4481…` throughout: nothing fetched or pushed |
| on a new branch `work` without upstream | exit 0, `T001 done on work; …`, `no upstream` |
| detached `HEAD`, `--json` | exit 0, `head` `null`, `upstream` `null`, `commits_total` 2 |
| `show T001 --json` | `close` `{"commit": "stages", "review": "report"}` |
| `task_branch` removed from the config | `show`: `close.review` `publish`; `review T001` exit 5 `run review on the task branch T001-base-task (current: main)`, as before |

The behaviour matches the plan.
