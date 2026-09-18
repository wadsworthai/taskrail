# T116 — Pin a setup-uv tag that exists in the generated GitHub workflow

Kind: bug · Epic: E05 · Status: fixed

## Symptom

`taskrail init --github-workflow` writes `.github/workflows/taskrail.yml` with
`- uses: astral-sh/setup-uv@v10`. No ref named `v10` exists in `astral-sh/setup-uv`: that project
publishes bare major tags only through `v7`, and its tenth major line exists only as the exact
tags `v10.0.0`, `v10.0.1` and `v10.1.0`. A workflow step whose `uses:` names a ref the action's
repository does not have cannot be resolved, so the job fails before running anything.

Every repository that installed the extra gets a `taskrail` workflow that fails on its first run,
and the failure is in the file taskrail manages, not in anything the consumer wrote. The sibling
step, `actions/checkout@v7`, is fine: `v7` is a real floating major tag there.

Expected: the generated workflow names refs that exist, so the `validate` job runs.

## Reproduction

From the T116 worktree at `c5d43dc` (`origin/main`), generate the workflow the way a consumer
does, into an empty repository, and resolve each `uses:` against the real remote:

```bash
git -C <scratch> init -q -b main
uv run taskrail --root <scratch> init --github-workflow
cat <scratch>/.github/workflows/taskrail.yml
git ls-remote https://github.com/astral-sh/setup-uv 'refs/tags/v10' 'refs/heads/v10' 'refs/*/v10'
```

## Evidence

The generated file today — not `install.py`, the file a consumer ends up with:

```
$ uv run taskrail --root <scratch> init --github-workflow
created   .taskrail/config.toml
created   TASKRAIL.md
created   .taskrail/bin/taskrail
created   .github/workflows/taskrail.yml
created   .gitignore
note      no agent integration installed; pass --integration claude or --integration opencode
0 file(s) already up to date

$ cat <scratch>/.github/workflows/taskrail.yml
# Managed by taskrail: `taskrail init --github-workflow` and `taskrail upgrade` rewrite this file.
name: taskrail

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v10
      - run: .taskrail/bin/taskrail validate
```

`v10` is not a tag, not a branch, not any ref at all in `astral-sh/setup-uv` — `git ls-remote`
prints nothing for all three patterns, while the exact tag does resolve:

```
$ git ls-remote https://github.com/astral-sh/setup-uv 'refs/tags/v10' 'refs/heads/v10' 'refs/*/v10'
(no output, exit 0)

$ git ls-remote https://github.com/astral-sh/setup-uv 'refs/tags/v10.1.0'
bec219d24cd3e171d82865faccec33120bb574f4	refs/tags/v10.1.0
```

The bare major tags that project does publish stop at `v7`:

```
$ curl -sS 'https://api.github.com/repos/astral-sh/setup-uv/git/matching-refs/tags/v' \
    | grep -o '"refs/tags/v[0-9]*"' | sort -u
"refs/tags/v1"
"refs/tags/v2"
"refs/tags/v3"
"refs/tags/v4"
"refs/tags/v5"
"refs/tags/v6"
"refs/tags/v7"
```

The whole `v10` line, as the API reports it:

```
$ curl -sS 'https://api.github.com/repos/astral-sh/setup-uv/git/matching-refs/tags/v10'
  "ref": "refs/tags/v10.0.0",
  "ref": "refs/tags/v10.0.1",
  "ref": "refs/tags/v10.1.0",

$ curl -sS 'https://api.github.com/repos/astral-sh/setup-uv/releases/latest'
  "tag_name": "v10.1.0",
  "name": "v10.1.0 🌈  New output `python-runtime-id`and respect NO_PROXY",
  "published_at": "2026-09-10T19:20:03Z",
```

`actions/checkout` is the contrast that shows the two projects differ in habit, not the workflow
in correctness — there the bare major exists and points at the newest patch:

```
$ git ls-remote https://github.com/actions/checkout 'refs/tags/v7' 'refs/tags/v7.0.1'
3d3c42e5aac5ba805825da76410c181273ba90b1	refs/tags/v7
3d3c42e5aac5ba805825da76410c181273ba90b1	refs/tags/v7.0.1

$ curl -sS 'https://api.github.com/repos/actions/checkout/releases/latest'
  "tag_name": "v7.0.1",
  "published_at": "2026-07-20T15:10:05Z",
```

The pin is as old as the template and has shipped in every release:

```
$ git log --oneline -S 'setup-uv@' -- src/taskrail/install.py
30885c3 feat(taskrail): add skills, agent integrations and idempotent install

$ git tag --contains 30885c3
v0.1.0
v0.2.0
v0.3.0

$ for t in v0.1.0 v0.2.0 v0.3.0; do git show "$t:src/taskrail/install.py" | grep 'setup-uv@'; done
      - uses: astral-sh/setup-uv@v10
      - uses: astral-sh/setup-uv@v10
      - uses: astral-sh/setup-uv@v10
```

## Root cause

`install.py`'s `workflow()` template (`src/taskrail/install.py:273`) writes the action ref as a
bare major, `astral-sh/setup-uv@v10`, on the assumption that every action publishes a floating
major tag. `astral-sh/setup-uv` stopped moving a bare major tag after `v7`, so the reference is
to a ref that has never existed. Nothing in the template, in the test suite or in `DESIGN.md` §9
states which form an action ref must take, so the assumption was never checked and nothing since
could catch it.

## Ruled out

- **A stale copy in the consumer repository.** The evidence above is a workflow generated from
  this branch's source into a fresh repository, not a file written months ago.
- **`actions/checkout@v7`.** `git ls-remote` resolves it; that step is not part of the failure.
- **A resolution quirk of GitHub Actions (a branch or a moving ref named `v10`).** `git ls-remote`
  was asked for `refs/tags/v10`, `refs/heads/v10` and `refs/*/v10` and returned nothing, so there
  is no ref of any kind for the runner to resolve.
- **A recent deletion of a `v10` tag that once existed.** `v10.0.0` is the first tag of that
  line and the three `v10.x` tags are all that match; the release list shows `v10.1.0` as the
  latest release, with no bare major among them.
- **`upgrade` already repairing installed repositories.** `Installer.managed` rewrites the
  workflow only when the template changes, and the template has not changed since `30885c3`, so
  every installed copy still holds `@v10`.

## Affected areas

- `src/taskrail/install.py` — `workflow()`, the only place the refs are written.
- `tests/test_install.py` — the generated-workflow tests;
  `test_github_workflow_checks_out_full_history` asserts the literal `actions/checkout@v7` line.
- Released artefacts: `v0.1.0`, `v0.2.0` and `v0.3.0` all ship the broken template. A consumer
  recovers by running `taskrail upgrade` at the fixed release; one that edited the workflow
  locally is skipped and reported by `managed`, and fixes the line itself.
- This repository's own `.github/workflows/ci.yml` (T108) is a separate file and already pins
  `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`; it is not affected.

## Proposed fix

In `workflow()`, pin both steps to exact release tags — `actions/checkout@v7.0.1` and
`astral-sh/setup-uv@v10.1.0` — the same pair this repository's own CI already uses, and add a
regression test asserting that every `uses:` in the generated workflow names an exact `vX.Y.Z`
tag. That test cannot prove a tag exists without reaching the network, which CI (T108) runs on
every pull request and must not do; what it can do is forbid the shape that caused the bug, the
bare major, and so make every ref a form a human can verify once against the action's releases.

## Fix

Decided at the diagnose gate, deliberately against the backlog row's wording, which asked to keep
`actions/checkout@v7` floating: **both** actions are pinned to exact release tags. A mixed rule
would need a per-action allowlist of who publishes a floating major — the very assumption that
caused this bug — and no offline test could enforce it.

- `src/taskrail/install.py`, `workflow()`: `actions/checkout@v7` → `actions/checkout@v7.0.1` and
  `astral-sh/setup-uv@v10` → `astral-sh/setup-uv@v10.1.0`, the pair this repository's own
  `.github/workflows/ci.yml` uses (T108), so the generated workflow and ours agree.
- `tests/test_install.py`, new `test_github_workflow_pins_every_action_to_an_exact_release_tag`:
  every `uses:` in the generated workflow must match `@vX.Y.Z`. It asserts the *shape*, and its
  comment says so: no offline test can prove a tag exists, and one that asked GitHub would reach
  the network on every pull request now that CI (T108) runs this suite. Forbidding the bare major
  leaves every ref in a form a human verifies once against the action's releases.
- `tests/test_install.py`, `test_github_workflow_checks_out_full_history`: its literal now reads
  `actions/checkout@v7.0.1`.
- `DESIGN.md` §9, the *Extras* bullet: records the convention beside the `fetch-depth: 0`
  explanation.
- `CHANGELOG.md`, Unreleased: what failed, that the fix is in the template, and that an installed
  repository picks it up with `taskrail upgrade` — an untouched managed workflow is rewritten, a
  locally edited one is skipped and reported.

## Verification

The regression test, run against the unfixed template, fails naming both loose refs — the
root-cause one among them:

```
$ uv run pytest tests/test_install.py -k pins_every_action
        loose = [ref for ref in refs if not re.fullmatch(r"[^@\s]+@v\d+\.\d+\.\d+", ref)]
>       assert not loose, f"not pinned to an exact release tag: {loose}"
E       AssertionError: not pinned to an exact release tag: ['actions/checkout@v7', 'astral-sh/setup-uv@v10']
E       assert not ['actions/checkout@v7', 'astral-sh/setup-uv@v10']

tests/test_install.py:150: AssertionError
======================= 1 failed, 57 deselected in 0.20s =======================
```

After the fix, the workflow tests pass:

```
$ uv run pytest tests/test_install.py -k "workflow"
tests/test_install.py ....                                               [100%]
======================= 4 passed, 54 deselected in 0.22s =======================
```

The same reproduction as in *Evidence*, on the fixed source, now produces a workflow whose refs
both resolve:

```
$ uv run taskrail --root <scratch> init --github-workflow
$ cat <scratch>/.github/workflows/taskrail.yml
...
      - uses: actions/checkout@v7.0.1
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v10.1.0
      - run: .taskrail/bin/taskrail validate

$ git ls-remote https://github.com/actions/checkout 'refs/tags/v7.0.1'
3d3c42e5aac5ba805825da76410c181273ba90b1	refs/tags/v7.0.1
$ git ls-remote https://github.com/astral-sh/setup-uv 'refs/tags/v10.1.0'
bec219d24cd3e171d82865faccec33120bb574f4	refs/tags/v10.1.0
```

Stage checks — `taskrail checks T116 --stage fix` runs `test` (`uv run pytest -q`); `lint` is not
configured in this repository and is reported as such:

```
$ .taskrail/bin/taskrail checks T116 --stage fix
== test: uv run pytest -q
........................................................................ [  5%]
...
........................                                                 [100%]
1248 passed in 163.48s (0:02:43)
== lint: not configured
passed test
not configured lint
T116 in <worktree>: passed
exit=0
```
