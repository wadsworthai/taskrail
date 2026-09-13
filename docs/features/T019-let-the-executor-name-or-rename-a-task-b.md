# T019 — Let the executor name or rename a task branch

Kind: feature · Epic: E05 · Status: verified

Source: the accepted autopilot design, `docs/spikes/T007-design-taskrail-s-autopilot-from-existin.md`
(*T017 and T019 should not run in parallel*), and `DESIGN.md` §6–§7 as of T017.

## Behaviour

Today a task's branch is always rendered from its kind's `branch` template (`{id}-{slug}` for
the core kinds), separately in five places: `task_dict` (`show`, `list`, `next`),
`_open_workspace` (`new --workspace`), `cmd_review`, `stack.task_branch` (`done-branch` and the
dependency's branch in `base`) and, through `show`, `prior_work`. A task worked on any other
branch is invisible to all of them, and so is a template branch after its title is edited by
hand, since the slug changes. Reproduced on this branch's base (see *Evidence*).

After this change:

- **One resolver.** A task's branch is its **recorded branch** when one exists, otherwise the
  name rendered from the kind's template, as today. Every lookup above goes through that one
  function; nothing else renders `kind.branch`.
- **Branch records.** A recorded branch lives in a small file next to the claims,
  `$(git rev-parse --git-common-dir)/taskrail/branches/<ID>.json`, holding `id`, `branch` and
  `recorded` (a timestamp) — no host, owner or path. It is shared by every worktree of the clone,
  is never committed or pushed, and is **not** removed by `done`, `discard`, `release`, `reopen`
  or the deletion of the branch, so `review`, `done-branch` detection and dependents still find
  the branch after the claim is gone. Outside git, or without a record, the template applies.
- **`taskrail branch <ID> <NAME> [--force] [--owner O] [--local-only]`** names or renames the
  task's branch. With the task's current branch (as resolved before the call) called `OLD`:
  - `OLD` exists locally and differs from `NAME` → taskrail runs `git branch -m OLD NAME`. Git
    moves the branch's config (upstream included) and updates the `HEAD` of whichever worktree
    has it checked out; the worktree directory is **not** moved.
  - `OLD` does not exist locally → nothing is renamed; the name is only recorded. This covers
    naming a task before its workspace exists, and adopting a branch already renamed with plain
    `git branch -m`.
  - The record is written, and a claim on the task whose `branch` is `OLD` is updated to `NAME`;
    when the claim is mirrored to `claim_remote`, its remote copy is re-pushed with a lease on the
    commit recorded for it (`--local-only` skips that).
  - JSON result: `id`, `branch`, `previous`, `renamed` (whether git renamed a branch),
    `claim_updated`, `worktree` (where the branch is checked out, or `null`) and `remote_copies`.
  - Refusals, each writing and renaming nothing:
    - exit 3 — no such task;
    - exit 2 — `NAME` is not a valid branch name (`git check-ref-format --branch NAME` fails or
      rewrites it, which rejects `-x`, `HEAD`, `a..b`, `@{-1}` and the like), or it is the
      mainline of any backlog;
    - exit 5 — `NAME` is the resolved branch of another task (recorded, or rendered from its
      template);
    - exit 5 — `OLD` exists locally and so does `NAME`;
    - exit 5 — without `--force`: `<remote>/OLD` exists (the branch was pushed, and the old
      remote branch and any pull request from it would stay behind), or `<remote>/NAME` exists
      while local `NAME` does not (a later `review --publish` would overwrite it), `<remote>`
      being the mainline's remote as resolved for `review`; refs are read locally, never fetched;
    - exit 4 — without `--force`: the task is claimed by another owner.
  - taskrail never pushes, deletes or renames a remote branch. With `--force`, `remote_copies`
    lists `<remote>/OLD` so the executor can report it.
- **`new --workspace --branch NAME`** creates the new task's branch (and worktree, at
  `<worktree_dir>/NAME`) under that name instead of the template's, and records it. `NAME` is
  validated as above before an ID is written; a refusal leaves no branch, worktree or record, and
  frees the reserved ID. `--branch` without `--workspace` exits 2: naming an existing task is
  `taskrail branch`'s job.
- **`claim` freezes the template name.** It still stores the branch it runs on (or `--branch`)
  in the claim as today. Once the claim is held (created or already held):
  - when that branch equals the task's resolved branch and no record exists — the name comes
    from the template — `claim` writes the record, so a later hand edit of the title no longer
    changes the branch;
  - when that branch differs from the resolved branch (another name, a mainline, or a detached
    `HEAD`), `claim` records nothing and warns: `taskrail: warning: …` on stderr, naming
    `taskrail branch`, and the same text in a `warning` field with `--json`. The exit code
    stays 0.

  The `--json` result gains `branch_recorded` (whether this call wrote a record) and `warning`
  (`null` when there is none).
- **`show`** (and `list --json`, `next --json`) reports the resolved `branch`, a new
  `branch_source` (`recorded` or `template`), and `worktree`: the path of the worktree that has
  the branch checked out when one does (relative to the repository root when inside it), else
  `<worktree_dir>/<branch>` as today — still `null` unless `worktree = "required"`. After a
  rename, `worktree` therefore keeps pointing at the directory the work is in.
- **`review`** runs on the resolved branch: the "run review on the task branch …" check, `head`,
  the push and the pull request link all use it.
- **`done-branch` and the stacked base** look for `refs/heads/<branch>` and
  `refs/remotes/<remote>/<branch>` of the resolved branch, so a renamed dependency is found and
  becomes its dependents' base. Records are read once per loaded project.
- **`prior_work`** reports the resolved branch in `branches`, and matches it in commit subjects.
- The core skill says how to use it: in step 3, run `taskrail branch <ID> <NAME>` before creating
  the workspace when the branch needs another name, then `show` again; to rename later, run it
  inside the workspace rather than `git branch -m` (or run it afterwards to adopt a manual
  rename); never rename a pushed branch without saying so at a gate. Step 4 says that a
  `warning` from `claim` means the workspace is not on the task's branch, to resolve before any
  edit. Step 8 uses the resolved branch as today.

## Acceptance criteria

Scenario: a repository with a bare `origin`, tasks T001 (feature), T002 depending on T001, and
T003 independent; lanes in worktrees under a temporary directory; no network.

1. `taskrail branch T001 feature/base` before any workspace exists exits 0 with `renamed`
   `false`; `show T001 --json` then reports `branch` `feature/base`, `branch_source` `recorded`
   and `worktree` `.worktrees/feature/base`. Without a record, `branch_source` is `template` and
   every other field is unchanged.
2. Inside a worktree on `T001-base-task`, claimed there, `taskrail branch T001 feature/base` runs
   the rename: `git branch --show-current` in that worktree prints `feature/base`,
   `T001-base-task` no longer exists, the branch keeps its upstream, the claim's `branch` is
   `feature/base`, `claims` reports the claim `live`, and `show T001 --json` from the main
   checkout reports `worktree` as that worktree's original path.
3. After `done T001` and a commit on the renamed branch, the claim file is gone and, from the main
   checkout: `show T001` is `done-branch`, `next` does not offer T001, `prior_work.branches`
   lists `feature/base`, and T002's `base` has `onto` `feature/base` and `dependency` `T001`.
   With only `origin/feature/base` present (the local branch deleted), the same holds with
   `onto` `origin/feature/base`.
4. `review T001 --json` on the renamed branch reports `head` `feature/base`; on
   `T001-base-task` (re-created) it exits 5 naming `feature/base`. `review --publish --no-push`
   prints a push command for `feature/base`, and the pull request link names it as head.
5. A branch renamed with plain `git branch -m` is adopted: `taskrail branch T001 <new>` exits 0
   with `renamed` `false`, records it, and updates the claim.
6. `new --workspace --branch feature/new` creates `feature/new` at the base, its worktree at
   `.worktrees/feature/new`, the row there, and a record for the new ID. With an invalid name,
   a mainline name, another task's branch or an existing branch it exits 2, 2, 5 and 5, leaves
   no branch, worktree or record, and the next `reserve-id` returns the same ID. `--branch`
   without `--workspace` exits 2.
7. `taskrail branch` refuses as specified: invalid names (`-x`, `HEAD`, `a..b`, `with space`)
   and `main` exit 2; T003's template branch or T003's recorded branch exits 5; an existing local
   `NAME` while `OLD` exists exits 5; `origin/OLD` present exits 5 and, with `--force`, renames
   and lists `origin/OLD` in `remote_copies`; `origin/NAME` present without local `NAME` exits 5;
   a claim held by another owner exits 4 and, with `--force`, succeeds. Each refusal leaves the
   branch, the record and the claim as they were.
8. With `claim_remote` set to a bare remote, a rename re-pushes the remote claim: the claim read
   back from the remote has `branch` `NAME`, and releasing it afterwards still deletes the ref.
9. Editing T001's title by hand after `taskrail branch` does not change `show T001`'s `branch`.
10. `claim T001` on `T001-base-task` with no record exits 0 with `branch_recorded` `true` and
    `warning` `null`; `show T001` then reports `branch_source` `recorded`, and after T001's title
    is edited by hand `show T001` still reports `T001-base-task`, `review` still runs on it, and
    T001 done on that branch is still `done-branch` from the main checkout. Claiming again, or
    claiming a task whose record already names the branch, writes nothing
    (`branch_recorded` `false`).
11. `claim T001` on another branch (`feature/other`, or `main` in the main checkout) exits 0,
    writes no record (`branch_source` stays `template`), prints a warning naming
    `taskrail branch` on stderr, and returns the same text in `warning` with `--json`. A task
    whose record names `feature/base`, claimed on `T001-base-task`, warns the same way and keeps
    its record.
12. Outside git, and in every existing test, behaviour is unchanged apart from the new
    `branch_source`, `branch_recorded` and `warning` keys; no code other than the resolver
    renders a kind's `branch` template.
13. `DESIGN.md` §6 (branch records, `claim` freezing and warning) and §7 (`branch` command,
    `new --branch`, `show`'s `branch`, `branch_source` and `worktree`, `review`, `done-branch`,
    prior work), `README.md` where it lists commands, the core skill's steps 3, 4 and 8, and
    `CHANGELOG.md` (one bullet) describe the behaviour; the installed skill copy matches its
    source after `taskrail upgrade`.

## Test coverage

In `tests/test_task_branch.py`: a repository with a local bare `origin` and lanes
in worktrees under the test's temporary directory; no network. Run against this branch's code
before the implementation — the test file plus `branches.py` alone, not yet wired into any
command — all 35 tests failed (`35 failed in 7.58s`); after it, the whole suite passes
(`335 passed`), with no existing test changed. Verification added a 36th test (see *Verification*),
observed failing (`assert 0 == 5`) before its fix; the suite then gave `336 passed`.

| Criterion | Tests |
|---|---|
| 1. Naming before a workspace; `branch_source`; record contents | `test_naming_a_task_before_its_workspace_exists` |
| 2. Rename inside the worktree: branch, upstream, claim, `claims`, `show`'s `worktree` | `test_renaming_inside_the_worktree_renames_the_branch_and_follows_the_claim` |
| 3. `done-branch`, `next`, `prior_work`, dependent's base, remote-only copy | `test_a_renamed_task_done_on_its_branch_is_still_found` |
| 4. `review` head, push command, refusal on the old name, pull request link | `test_review_runs_on_the_renamed_branch`, `test_the_pull_request_link_names_the_renamed_branch` |
| 5. Adopting a manual `git branch -m` | `test_a_manual_git_rename_is_adopted` |
| 6. `new --workspace --branch`, its refusals, `--branch` without `--workspace` | `test_new_workspace_with_a_chosen_branch`, `test_new_workspace_refuses_a_bad_branch_and_frees_the_id` (4 cases), `test_new_branch_needs_workspace` |
| 7. `branch` refusals and `--force` | `test_branch_refuses_invalid_names_and_mainlines` (6 cases), `test_branch_refuses_another_tasks_branch`, `test_branch_refuses_the_recorded_branch_of_a_task_created_in_its_own_workspace`, `test_branch_refuses_an_existing_target_while_the_old_branch_exists`, `test_branch_refuses_a_pushed_branch_unless_forced`, `test_branch_refuses_a_name_taken_on_the_remote_unless_forced`, `test_branch_refuses_a_task_claimed_by_someone_else_unless_forced`, `test_branch_on_an_unknown_task`, `test_branch_to_the_same_name_only_records_it` |
| 8. Remote claim re-pushed with a lease; `--local-only` | `test_a_rename_re_pushes_the_remote_claim`, `test_local_only_rename_leaves_the_remote_claim` |
| 9. A record survives a title edit | `test_a_recorded_branch_survives_a_title_edit` |
| 10. `claim` freezes the template name | `test_claim_freezes_the_template_name`, `test_claim_on_a_recorded_branch_writes_nothing` |
| 11. `claim` on another branch warns | `test_claim_on_another_branch_warns_and_records_nothing`, `test_claim_on_the_mainline_warns`, `test_claim_on_the_template_branch_of_a_renamed_task_warns_and_keeps_the_record` |
| 12. Outside git; one resolver | `test_outside_git_the_template_applies`, `test_only_the_resolver_renders_the_branch_template`, and the existing suite unchanged |
| 13. Documentation and skill | reviewed at the implement gate: `DESIGN.md` §6.1, new §6.4, §7 table, §7.1, *Done on its branch*, §7.2; `README.md`; core skill steps 3, 4 and 8, installed with `taskrail upgrade`; `CHANGELOG.md` |

Deviations from the plan's wording:

- `stack.task_branch` is removed rather than delegating: `stack.py` calls
  `branches.task_branch` directly.
- `taskrail branch` returns `worktree` as an absolute path; `show` keeps a path relative to the
  repository root when the worktree is inside it.
- If re-pushing the remote claim fails after the local rename, `taskrail branch` exits 2 with the
  push error; the branch, the record and the local claim already carry the new name.

## Verification

The real CLI from this branch, in a throwaway repository under `/tmp` with a local bare `origin`
(`worktree = "required"`), deleted afterwards:

- `git worktree add .worktrees/T001-base-task -b T001-base-task origin/main`, then `claim T001`
  in it: `"branch_recorded": true, "warning": null`.
- `branch T001 feature/base-task` inside that worktree: `"renamed": true, "claim_updated": true`,
  `worktree` the unmoved directory; `git branch --show-current` printed `feature/base-task`,
  `git worktree list` showed `.worktrees/T001-base-task … [feature/base-task]`, and `claims`
  printed `T001 lane feature/base-task live`.
- `done T001` and a commit there: `claims --json` was empty; `review T001 --no-fetch` printed
  `T001 ready for review against main`.
- After pushing `feature/base-task`: `branch T001 feature/other` exited 5 with
  `origin/feature/base-task exists: the pushed branch and any pull request from it would stay
  behind; pass --force to go ahead (the remote is never changed)`; with `--force` it renamed,
  `"remote_copies": ["origin/feature/base-task"]`, and `git ls-remote --heads origin` still listed
  only `feature/base-task` and `main`.
- From the main checkout: `show T001` gave `done-branch feature/other recorded
  .worktrees/T001-base-task ['feature/other']`, still `feature/other recorded` with the title
  edited by hand; `list` showed T001 `done-branch`; T002's base was `feature/other` with
  dependency `T001`.
- In T001's worktree, `review T001 --json --no-fetch` gave head `feature/other`, and
  `review --publish --no-push` printed `git push --set-upstream origin HEAD:refs/heads/feature/other`
  and the title `feat: base task (T001)`; from another branch `review T001` exited 5 with
  `run review on the task branch feature/other (current: elsewhere)`.
- `claim T002` on branch `elsewhere` exited 0, printed `taskrail: warning: T002 was claimed on
  branch elsewhere, but its branch is T002-depends-on-base; work on that branch, or run
  `taskrail branch T002 <NAME>` to name the branch the task is worked on`, and returned it in
  `warning` with `branch_recorded: false`.
- `new --workspace --branch feature/fresh` created `.worktrees/feature/fresh` on `feature/fresh`
  as T003. `--branch=-x` exited 2 (`` `-x` is not a valid branch name ``), `--branch main` exited 2
  (`` `main` is a mainline, not a task branch ``), `--branch feature/other` exited 5
  (`feature/other is the branch of T001`), `--branch` without `--workspace` exited 2, and
  `reserve-id` then returned `T004`.

**Gap found and fixed:** `branch T002 feature/fresh` from the main checkout exited 0, although
T003 records `feature/fresh`. T003's row exists only in its own workspace, and the uniqueness check
looked only at tasks in the current checkout. `owner_of` now also checks every record; regression
test `test_branch_refuses_the_recorded_branch_of_a_task_created_in_its_own_workspace`.

## Affected areas

- `src/taskrail/branches.py` (new) — the record files (read all, write
  atomically, remove on `new --workspace` rollback), name validation, and the resolver
  `task_branch(task, project)`, with records cached in `project.cache`.
- `src/taskrail/stack.py` — `task_branch` delegates to the resolver.
- `src/taskrail/query.py` — `task_dict`: `branch`, `branch_source`, `worktree`.
- `src/taskrail/prior.py` — unchanged in logic; it receives the resolved branch.
- `src/taskrail/claims.py` — update a claim's `branch`, and re-push its remote
  copy with a lease on the recorded commit.
- `src/taskrail/gitutil.py` — a helper listing worktrees with the branch each has
  checked out.
- `src/taskrail/cli.py` — `cmd_branch` and its parser, `new --branch`,
  `_open_workspace` and `cmd_review` through the resolver.
- `tests/test_task_branch.py` (new).
- Docs: `DESIGN.md` §6–§7, `README.md`, the core skill source
  `src/taskrail/skills/taskrail/SKILL.md` (steps 3 and 8) and its installed copy,
  `CHANGELOG.md`.

## Out of scope

- Moving a task's worktree directory on rename (`git worktree move`).
- Pushing, deleting or renaming a remote branch, or retargeting an open pull request.
- Sharing branch records with other clones — follow-up T036. Another clone finds a renamed
  branch neither through `done-branch` nor in `show`; it sees the template name, as it would for
  a branch named by hand today. With `claim_remote`, only the live claim carries the name.
- Recording a differing branch in `claim`, and refusing a claim made on another branch.
- Validating kind `branch` templates as git ref names, and checking records in `validate`.
- Listing earlier names of a renamed branch in `prior_work`.
- A command to forget a record; naming the task after its template's name records that name.

## Decisions at the plan gate

Recorded in `docs/autopilot/decisions/T019-let-the-executor-name-or-rename-a-task-b.md`. Every
recommendation below was accepted; decision 2 added that `claim` freezes the template name and
warns on another branch (see *Behaviour*), and the cross-clone follow-up was opened as T036.

1. **Where the chosen name is recorded.** Recommended: a per-task file in the git common
   directory, local and never public, surviving `done`, release and branch deletion.
   Alternatives: a git-config key on the branch, such as `branch.<name>.taskrail-task`, which git
   carries through a manual `git branch -m` (verified below) but deletes with `git branch -D` and
   copies with `git branch -c`, making it ambiguous and lost for a branch that remains only on the
   remote; a backlog column, public and visible to other clones but only after the row reaches the
   mainline, and a change to every task table's header; the claim only, lost at `done`.
2. **Command surface.** Recommended: `taskrail branch <ID> <NAME>` for naming and renaming, plus
   `new --workspace --branch`; `claim` unchanged. Alternative: `claim` records its current branch
   whenever it differs from the resolved one and is not a mainline — no extra command at the
   start, but a claim made from the wrong checkout would silently rename the task.
3. **Whether taskrail runs `git branch -m`.** Recommended: yes when the old branch exists
   locally, record only otherwise. Alternative: record only, leaving the rename to the executor,
   which leaves a window where the record and the branch disagree.
4. **A pushed branch.** Recommended: refuse with exit 5 unless `--force`, and never touch the
   remote. Alternative: rename with a warning in the result.
5. **The worktree path.** Recommended: never moved; `show` reports where the branch is checked
   out. Alternative: `--move-worktree`, which breaks a session whose working directory is inside.
6. **The remote claim.** Recommended: re-push it on rename. Alternative: leave the remote copy
   with the old name, since only the local claim is used for staleness.

## Open questions and risks

- **Cross-clone visibility** (out of scope above): T036 mirrors records to a remote ref next to
  `refs/taskrail/claims`.
- **Parallel lanes.** T029 adds commands to `cli.py`'s parser and T020 edits the core skill's
  step 5; this task adds one parser block and edits steps 3 and 8, so a rebase conflict, if any,
  is mechanical.
- **Existing template-named branches** keep working with no record, so no migration is needed.
- **Races.** Two `taskrail branch` calls choosing the same name for different tasks at the same
  instant can both pass the uniqueness check; records are written atomically but not locked. The
  second `git branch -m` fails on the existing branch, so only record-only calls can collide.

## Evidence

Throwaway repository under `/tmp` (config: one backlog `main`, `worktree = "required"`), CLI from
this branch's base `a9ae799`, run with `--root` of the directory shown:

```text
$ git worktree add .worktrees/custom -b feature/custom-name main
$ taskrail claim T001 --json   # in the worktree
    "branch": "feature/custom-name",
$ taskrail done T001 && git commit -qam 'chore(T001): mark done'
T001 done
$ taskrail claims --json
{
  "local": [],
  "remote_only": []
}
$ taskrail review T001 --json --no-fetch   # in the worktree
taskrail: run review on the task branch T001-base-task (current: feature/custom-name)
exit=5
$ taskrail show T001 --json   # main checkout: state, branch, worktree, prior_work.branches
pending T001-base-task .worktrees/T001-base-task []
$ taskrail next --json   # main checkout
[('T001', 'pending')]
$ taskrail show T002 --json   # main checkout: state, blocked_by, base.onto, base.dependency
blocked ['T001'] main None
--- control: same flow on the template branch name
$ taskrail show T001 --json   # main checkout
done-branch T001-base-task ['T001-base-task']
--- title edited by hand after branching
$ taskrail show T001 --json   # main checkout, title edited
pending T001-base-task-v2
--- git branch -m inside a worktree: config section and worktree HEAD
branch.feature/renamed.probe yes
/tmp/t019-plan.dSVF/repo                           d186345 [main]
/tmp/t019-plan.dSVF/repo/.worktrees/T001-base-task e49eef2 [T001-base-task]
/tmp/t019-plan.dSVF/repo/.worktrees/custom         fe5fdf2 [feature/renamed]
```

Name validation and renames with git 2.55.0:

```text
feature/ok   refs/heads: ok  --branch: feature/ok
-dash        refs/heads: ok  --branch: bad
HEAD         refs/heads: ok  --branch: bad
a..b         refs/heads: bad  --branch: bad
with space   refs/heads: bad  --branch: bad
@{-1}        refs/heads: bad  --branch: bad
x.lock       refs/heads: bad  --branch: bad
a/           refs/heads: bad  --branch: bad
T001/sub     refs/heads: ok  --branch: T001/sub
$ git branch -m T001-base-task renamed-from-main   # branch checked out in another worktree, run from main checkout
exit=0
/tmp/t019-plan.dSVF/repo                           d186345 [main]
/tmp/t019-plan.dSVF/repo/.worktrees/T001-base-task e49eef2 [renamed-from-main]
/tmp/t019-plan.dSVF/repo/.worktrees/custom         fe5fdf2 [feature/renamed]
$ git branch -m renamed-from-main feature   # while feature/renamed exists
error: 'refs/heads/feature/renamed' exists; cannot create 'refs/heads/feature'
fatal: branch rename failed
exit=128
```

`refs/heads/<name>` alone accepts `-dash` and `HEAD`, which `git branch` refuses, so validation
uses `--branch` and requires its output to equal the input.
