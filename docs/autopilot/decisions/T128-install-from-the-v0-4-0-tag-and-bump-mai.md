# T128 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T128-install-from-the-v0-4-0-tag-and-bump-mai.md` and its commit
`dfb892d`; the lane's own verification of the precondition — `v0.4.0` annotated, published on
`origin` and on the anonymous HTTPS remote, peeling to `a0994e3`, this branch's base; and the search
for every file that names a version.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The verification commands | **the artifact's twelve checks, both routes, each from an empty uv cache under a PATH with `uv` and no `taskrail`** · the `uvx` route only · `uv tool install` into scratch directories | **as recommended** | It installs from the published tag over the network, the route a consumer takes, and proves which taskrail ran rather than assuming it — including that `import taskrail` resolves inside the scratch cache, not this checkout. `uv pip install` into a scratch venv covers the installed-CLI route without the `uv tool install` the brief forbids. |
| 2 | Checking the workflow generated from the tag | **yes: byte-compare against the release commit, both action tags exist, it parses, its only step runs; plus the Actions API read anonymously, labelled supporting only** · skip · skip the API read | **as recommended** | It is the file T116 fixed for every earlier release, so a consumer's first CI run on `v0.4.0` depends on it. What cannot be checked here — a real run in a consumer pinned to the tag — is said plainly, and the one real run available (this repository's own, through a `local:.` pin) is labelled for what it is. |
| 3 | The bump | **`pyproject.toml` to `0.5.0.dev0` and `uv lock`, one line each; `.taskrail/installed.json` stays at `v0.4.0`** · also run `upgrade` | **as recommended** | As T078 and T086 did. An `upgrade` from `0.5.0.dev0` would record `v0.5.0`, a tag that does not exist; `v0.4.0` is accurate for the files installed now. |
| 4 | `CHANGELOG.md` | **nothing** | **nothing** | T127 left an empty `## Unreleased`, and a development version on `main` is not a user-facing change. |
| 5 | Pull request title | **`chore(release): bump main to 0.5.0.dev0 after the v0.4.0 tag (T128)`** | **as recommended** | The form T078 and T086 used. |

Correction for the artifact: the local `v0.1.0` tag no longer exists. The human asked for it to be
deleted and the orchestrator deleted it before this task started; it was never on `origin`.

## implement gate

Reviewed: commit `8d978c6` — one line each in `pyproject.toml` and `uv.lock`, and the artifact's
results; the twelve checks, run under a scrubbed environment whose `PATH` held only `uv` and `uvx`,
with `command -v taskrail` shown empty first and every install from an empty cache.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implement stage | **approve** | **approve** | Every check passed, and the three that matter most prove rather than assert: `uvx` fetched `v0.4.0` over HTTPS and resolved it to `a0994e3`, and `import taskrail` loaded from the scratch cache, not this checkout; the committed wrapper with an empty `PATH` fell through to `uvx` from the tag; and a `0.5.0.dev0` wheel placed on `PATH` was **rejected** by the `v0.4.0` pin in favour of the tag — the version check in the wrapper doing its job against the exact build this task creates. |

Worth recording beyond this task: the anonymous Actions API shows both workflows — `ci` and the
generated `taskrail` — completing with `success` on `main` at `a0994e3`, the release commit, with
T123's concurrency block in place. It goes through this repository's `local:.` pin and is labelled
supporting only, but it is the first confirmation from GitHub itself that the generated workflow T116
fixed now runs.

## close

Reviewed: the `docs` stage commit, touching only the artifact, which records that no other file names
the development version; `taskrail done T128` on its own commit, changing only T128's status cell;
`taskrail validate`. No rebase is needed: `main` is still at `a0994e3`, this branch's base.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Pull request title | **`chore(release): bump main to 0.5.0.dev0 after the v0.4.0 tag (T128)`** | **as decided at scope** | The form T078 and T086 used. |

With this merged, E10's first release is complete: `v0.4.0` is tagged from a squash-merged release
pull request and was shown to install cleanly from its tag, over the network, on both routes.
