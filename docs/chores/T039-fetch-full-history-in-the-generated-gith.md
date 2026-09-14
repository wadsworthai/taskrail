# T039 — Fetch full history in the generated GitHub workflow

Kind: chore · Epic: E02 · Status: documented

## Goal

The workflow `taskrail init --github-workflow` writes must give `taskrail validate` the git
history its reopen check (T012, DESIGN §7 "Reopens in history") reads.

Today the template in `install.workflow()` uses `actions/checkout` with its defaults, which fetch
a single commit (`fetch-depth: 1`). In such a clone the only commit has no parents, so it
reopens nothing, and the check examines one commit and never warns. Reproduction in a throwaway
repository (a task marked done, then reopened in a commit without a `Reopens:` trailer, then three
unrelated commits), cloned with `--depth 1` and in full:

```text
$ git log --oneline
17267ec unrelated 3
700d251 unrelated 2
b15c363 unrelated 1
6b28e10 reopen T001 without trailer
cbc944e done T001
f889442 init
--- shallow clone: taskrail validate
history: shallow clone; examined 1 commit(s), so older reopens are not checked
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
history: {'examined': 1, 'limit': 500, 'truncated': False, 'shallow': True, 'skipped': None}
issues: []
--- full clone: taskrail validate
TODO.md:13: warning: T001 went from ✅ done to ⬜ pending in 6b28e10 ("reopen T001 without trailer") without a `Reopens: T001` trailer; ... [reopen-untraced]
1 task(s) in 1 backlog(s): 0 error(s), 1 warning(s)
history: {'examined': 3, 'limit': 500, 'truncated': False, 'shallow': False, 'skipped': None}
```

## Change set

1. `src/taskrail/install.py` — in `workflow()`, give the checkout step
   `with: fetch-depth: 0`:

   ```yaml
         - uses: actions/checkout@v7
           with:
             fetch-depth: 0
   ```

   Nothing else in the template changes; `validate` keeps running without flags.
2. `tests/test_install.py` — two tests:
   - the generated workflow's checkout step requests full history (`fetch-depth: 0` in the
     `with:` block directly under `actions/checkout`);
   - `upgrade` rewrites a workflow an earlier template wrote and nobody edited: the test writes
     the previous template's text and records its digest in `installed.json`, as an older
     install would have, runs `upgrade`, and checks the file is reported `updated` and now
     requests full history. (A locally edited workflow is skipped — existing managed-file
     behaviour, already covered for skills; not re-tested here.)
3. `DESIGN.md` §9, *Extras* bullet — say the workflow checks out full history,
   because `validate`'s reopen check (§7) sees nothing past a shallow clone's boundary.
4. `README.md` — the `--github-workflow` bullet: runs `validate` with full git
   history, so the reopen check sees every commit. (It also runs on pushes to the mainlines;
   the bullet says only "on pull requests" — fix that in the same sentence.)
5. `CHANGELOG.md` — one bullet at the end of `## Unreleased`: the generated
   workflow fetches full history; `upgrade` updates an existing, unedited workflow, and one
   edited locally is reported as skipped (add `fetch-depth: 0` by hand or pass `--force`).
6. This document, and its row in `docs/chores/README.md`.

## Decisions needed

1. **`fetch-depth: 0` or a bounded depth?** Recommendation: `0`. A bounded depth cannot be matched
   to `--history-limit`: the limit counts commits that *change backlog files*, while
   `fetch-depth` counts all commits, so any finite depth can still cut the window short and turn
   a reopen's parent into a shallow boundary (which then reopens nothing, silently). The cost of
   full history is one larger fetch; the check itself stays bounded by `--history-limit`.
   Alternative: a large fixed depth such as `fetch-depth: 1000`, cheaper on huge repositories but
   still incomplete by construction.
2. **Should `validate` in the workflow pass any flag?** Recommendation: no. The default limit
   (500) applies to CI as it does locally; `--no-history` would defeat the change. The
   `reopen-untraced` warning does not change the exit code, so the job still passes and the
   warning shows in its log. Alternative: `--history-limit N` — rejected, it would hard-code a
   policy the repository can already choose by editing (and then owning) the workflow.
3. **`upgrade` and existing workflows.** No code change needed: the workflow is a *managed*
   file (digest in `installed.json`, extra remembered in `extras.github_workflow`), so `upgrade`
   rewrites an unedited one and reports an edited one as skipped. Recommendation: rely on that,
   pin it with the test in change 2, and state it in the changelog bullet. Alternative: drop the
   upgrade test and keep only the template test.

## Out of scope

- Adding a workflow to this repository (explicitly excluded).
- Surfacing `reopen-untraced` as a GitHub annotation, or failing the job on warnings.
- Pinning or bumping the action versions (`actions/checkout@v7`, `astral-sh/setup-uv@v10`).
- The pre-commit hook (local clones already have their history) and anything in `install()`'s
  extras or `cli.py` (T004 touches those).
- Any change to `history.py` or `validate`.

## Verification

Scope approved as proposed (decisions: `fetch-depth: 0`; no flags for `validate`; include the
upgrade test; the README wording fix is in scope).

**Tests, failing first.** With only the two new tests added and the template unchanged:

```text
$ uv run pytest -q tests/test_install.py -k "full_history or earlier_template"
FAILED tests/test_install.py::test_github_workflow_checks_out_full_history - AssertionError: assert '      - uses: actions/checkout@v7\n        with:\n ...
FAILED tests/test_install.py::test_upgrade_rewrites_an_unedited_workflow_from_an_earlier_template - AssertionError: assert '.github/workflows/taskrail.yml' in []
2 failed, 55 deselected in 0.59s
```

After the template change: `2 passed, 55 deselected in 0.54s`; the whole suite,
`uv run pytest -q`: `743 passed in 89.71s`. No `lint` check is
configured in this repository.

**`upgrade` on real installs.** Two throwaway repositories initialised with
`init --github-workflow` by the `origin/main` code (exported with `git archive`), so their
workflow has no `fetch-depth`; one then gets a local edit (`# local tweak` appended). `upgrade`
run with this branch's code:

```text
=== unedited: upgrade with this branch's code
updated   .github/workflows/taskrail.yml
exit 0
--- unedited workflow now:
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v10
      - run: .taskrail/bin/taskrail validate
=== edited: upgrade with this branch's code
skipped   .github/workflows/taskrail.yml (edited locally; --force replaces it)
exit 0
=== edited: upgrade --force
updated   .github/workflows/taskrail.yml
15:          fetch-depth: 0
```

**What each depth gives `validate`.** A repository with a task done, then reopened in a commit
without a trailer, then three unrelated commits, fetched into two fresh repositories the way
`actions/checkout` does: `git fetch --depth=1 origin +<sha>:refs/remotes/origin/main` (its
default) and `git fetch origin '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'`
(`fetch-depth: 0`), then `validate` with this branch's CLI:

```text
--- depth1 (is-shallow: true)
history: shallow clone; examined 1 commit(s), so older reopens are not checked
1 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit 0
history: {'examined': 1, 'limit': 500, 'truncated': False, 'shallow': True, 'skipped': None}
--- depth0 (is-shallow: false)
TODO.md:13: warning: T001 went from ✅ done to ⬜ pending in eb0cf71 ("reopen T001 without trailer") without a `Reopens: T001` trailer; ... [reopen-untraced]
1 task(s) in 1 backlog(s): 0 error(s), 1 warning(s)
exit 0
history: {'examined': 3, 'limit': 500, 'truncated': False, 'shallow': False, 'skipped': None}
```

GitHub Actions itself was not run. All temporary repositories were deleted.
