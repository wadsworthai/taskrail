# T022 — Use each mainline's own remote in review

Kind: feature · Epic: E05 · Status: verified

## Behaviour

Today every git operation taskrail makes against a remote uses one configured name,
`[review].remote`: the base a task branches from (`show`'s `base`, `new --workspace`), and in
`review` the fetch, the rebase base (`<remote>/<mainline>` against the local mainline), the push
of the task branch and the host and repository path of the pull request link.

That breaks a repository with several backlogs whose mainlines live on different remotes. For
example, a project built from a template keeps two backlogs: `main` tracks the template
repository's remote (`upstream`), and `dev` tracks `origin`. With `[review].remote = "origin"`,
tasks of the `main` backlog are compared against `origin/main` — missing, stale or diverged —
pushed to the wrong repository, and linked to a pull request on the wrong repository.

After this change, each mainline resolves its own remote, in this order:

1. `branch.<mainline>.remote` from git config — the remote the local mainline tracks, as set by
   `git clone`, `git branch --set-upstream-to` or `git push -u` — when it names a configured
   remote;
2. otherwise `[review].remote`, which keeps its default `origin`.

A value that is not a configured remote name (`.`, meaning a local upstream, or a URL, which has
no remote-tracking branches) is ignored and the fallback applies.

The resolved remote is the single remote for that mainline, used for everything:

- **Base selection** in `show`, `new --workspace` and `review`: the local mainline against
  `<resolved remote>/<mainline>`.
- **Fetch** in `review`: `git fetch <resolved remote>`.
- **Push** of the task branch in `review --publish`: to the resolved remote. The pull request is
  opened on the repository that hosts the mainline, and a same-repository compare link only
  works when the head branch lives there too.
- **Link** in `review`: host and repository path parsed from the resolved remote's URL.
  `[review].provider`, `web_url` and `url_template` stay repository-wide.

Where the remote came from is visible: `show --json`'s `base` and `review --json` gain a
`remote` (`base.remote` in `show`) and a `remote_source` field, either
`branch.<mainline>.remote` or `[review].remote`. `review --json` already has `remote`; it now
holds the resolved name.

A repository whose mainline tracks the same remote as `[review].remote` — or tracks nothing —
behaves exactly as before.

## Acceptance criteria

1. With `branch.<mainline>.remote` set to a configured remote other than `[review].remote`,
   `show <ID> --json` reports `base.onto` from that remote (`<remote>/<mainline>` when it is up to
   date or ahead), `base.remote` equal to it and `base.remote_source` equal to
   `branch.<mainline>.remote`.
2. Without `branch.<mainline>.remote`, or with it set to `.`, a URL or a name that is not a
   configured remote, `show` resolves `[review].remote` and reports `remote_source`
   `[review].remote`; existing base tests keep passing unchanged.
3. `new --workspace` branches from the base chosen against the resolved remote: with the
   mainline's own remote ahead, the new branch starts at that remote's commit.
4. `review <ID> --json` fetches the resolved remote (a fetch of it that fails exits 2 and names
   it), picks `rebase.onto` against it, and reports `remote` and `remote_source`.
5. `review <ID> --publish` pushes the task branch to the resolved remote, and the lease check and
   the returned push command name it; nothing is pushed to `[review].remote` when it differs.
6. The pull request link's host and repository path come from the resolved remote's URL: with
   the mainline tracking a `github.com` remote other than `[review].remote`, the link points at
   that repository.
7. In a repository with two backlogs whose mainlines track different remotes, `show` and
   `review` resolve each task's remote from its own backlog's mainline.
8. `DESIGN.md` (§4 config comment, §7 `show`, §7.1), `README.md` where it describes the base or
   review, the default config written by `init`, and the core skill's workspace and close steps
   describe the resolution; the installed skill copies match their sources after
   `taskrail upgrade`.

## Test coverage

In `tests/test_mainline_remote.py`, against two local bare repositories as
`origin` and `upstream`; the link test only rewrites remote URLs and never fetches.

| Criterion | Tests |
|---|---|
| 1. `show` uses the tracked remote | `test_show_uses_the_remote_the_mainline_tracks` |
| 2. Fallback to `[review].remote` | `test_show_falls_back_to_the_review_remote[None, ., url, nosuch]`, `test_resolve_remote_uses_the_configured_fallback`, `tests/test_workspace.py::test_show_reports_the_base` |
| 3. `new --workspace` | `test_workspace_branches_from_the_mainline_remote` |
| 4. `review` fetch and rebase base | `test_review_fetches_and_rebases_against_the_mainline_remote`, `test_a_failed_fetch_names_the_mainline_remote` |
| 5. Push to the resolved remote only | `test_publish_pushes_to_the_mainline_remote` |
| 6. Link on the resolved remote's repository | `test_link_points_at_the_mainline_remote_repository` |
| 7. Two backlogs, two remotes | `test_each_backlog_resolves_its_own_mainline_remote` |
| 8. Documentation and skill | reviewed at the implement gate: `DESIGN.md` §4, §7, §7.1; `README.md`; the `[review]` comment in `install.py`; core skill steps 3 and 8, installed with `taskrail upgrade` |

Deviation from criterion 2's wording: the existing base tests keep passing, but
`test_show_reports_the_base` compares the whole `base` object, so its expected value gained the
two new keys (`"remote": "origin"`, `"remote_source": "[review].remote"`). No other existing test
changed.

## Affected areas

- `src/taskrail/review.py` — a `resolve_remote(root, mainline, fallback)` helper
  returning the name and its source.
- `src/taskrail/query.py` — `base_dict` resolves the remote and adds `remote` and
  `remote_source`.
- `src/taskrail/cli.py` — `_open_workspace` and `cmd_review` use the resolved
  remote for base, fetch, push and link; the text output of `show` if it prints the base.
- `src/taskrail/install.py` — the comment on `[review].remote` in the default
  config: it is the fallback.
- `src/taskrail/skills/taskrail/SKILL.md` — step 3 fetches the mainline's remote
  rather than a bare `git fetch`; step 8's "fetches the review remote" wording. Installed copies
  under `.claude/skills/` refreshed with `taskrail upgrade`.
- `tests/test_review.py`, `tests/test_workspace.py` — tests with two local bare
  repositories as remotes; no network.
- `DESIGN.md`, `README.md`, `CHANGELOG.md` (one line under `## Unreleased`).
- No change to the config schema or to `config.py`.

## Out of scope

- **A separate push remote** (`branch.<name>.pushRemote`, `remote.pushDefault`, or pushing to a
  fork while the base lives upstream). Cross-repository pull requests need an `owner:branch` head
  in the link, which is a distinct feature.
- **An upstream branch whose name differs from the mainline** (`branch.<mainline>.merge`, such
  as local `main` tracking `upstream/master`). The target branch stays the mainline's name.
- **A per-backlog `remote` key in config** as an explicit override above git's tracking config.
- **Per-remote `provider`, `web_url` or `url_template`**, for mainlines hosted on different kinds
  of host that are not auto-detected.
- **`claim_remote`** and the ID scan over its remote-tracking branches, which are unrelated to a
  mainline.

## Open questions and risks

- **Behaviour change for an explicit `[review].remote`.** A repository that set
  `[review].remote = "mirror"` while its mainline tracks `origin` would start using `origin`.
  The config loader cannot tell an explicit `origin` from the default. Git's tracking config is
  the more specific statement about a mainline, which is why it wins; a per-backlog override
  (out of scope above) is the escape hatch if a consumer needs one.
- **Fetch before `show`.** The core skill tells the agent to run `git fetch` and then `show`.
  A bare `git fetch` fetches the current branch's upstream remote, which may not be the task's
  mainline remote. Proposed wording: step 2's `show` already reports `base.remote`, so step 3
  becomes `git fetch <base.remote>`, then `show` again.
- **Worktree-scoped config.** With `extensions.worktreeConfig`, `git config --get` in a worktree
  reads the worktree's view, which is what an agent working there sees; no special handling.
- **Parallel work.** `show`'s output is also touched by T023, and config loading by T018 and
  T021; this plan leaves `config.py` alone and keeps `query.py` edits inside `base_dict`.

## Decisions at the plan gate

Recorded in `docs/autopilot/decisions/T022-use-each-mainline-s-own-remote-in-review.md`.

- The plan is approved as written.
- The task branch is pushed to the resolved remote.
- Tracking config wins over `[review].remote`, and the changelog line says so as a behaviour
  change.
- Core skill step 3 fetches `<base.remote>`; the close step names the mainline's remote.
- No follow-up tasks: a separate push remote and `branch.<mainline>.merge` stay out of scope.

## Verification

Run with this branch's CLI (`uv run taskrail --root <scratch>`) in a
scratch repository with two backlogs — `template` on `main`, `product` on `dev` — and two local
bare remotes: `main` tracking `upstream`, `dev` tracking `origin`, `[review].remote = "origin"`.
`upstream/main` and `origin/dev` were each one commit ahead of the local branches.

- `show T002 --json` reported `base` `upstream/main` with `remote` `upstream` and
  `remote_source` `branch.main.remote`; `show A001 --json` reported `origin/dev` with `origin` and
  `branch.dev.remote`. The text form printed `base upstream/main (…)`.
- `new --backlog product … --workspace` created `A002-log-in` from `origin/dev` (at the `dev`
  commit), and `new --backlog template … --workspace` created `T003-negative-totals` from
  `upstream/main` (at the `up` commit).
- With both bare remotes advanced again, `review T003 --json` in T003's worktree reported
  `remote` `upstream`, `remote_source` `branch.main.remote`, `fetched` true and
  `rebase.onto` `upstream/main` with `needed` true. `upstream/main` moved to the bare's new commit,
  while `origin/dev` stayed at its old commit: only the mainline's remote was fetched.
- After `git rebase upstream/main`, `review T003 --publish` printed
  `pushed T003-negative-totals to upstream`. The `upstream` bare held the branch at HEAD; the
  `origin` bare still had only `dev` and `main`.
- With the remote URLs set to `git@github.com:acme/template.git` (upstream) and
  `git@github.com:acme/product.git` (origin), `review T003 --no-fetch --json` returned provider
  `github` and `https://github.com/acme/template/compare/main...T003-negative-totals?quick_pull=1&…`.
- With `branch.main.remote` set to `.`, `show T002` fell back to `origin/main` with
  `remote_source` `[review].remote`.

No difference from the plan was found.
