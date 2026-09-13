# T002 — Tag and publish v0.1.0

Kind: chore · Epic: E01 · Status: implemented, awaiting merge and tag

## Goal

Publish the first taskrail release, so other repositories can install a pinned version with
`uv tool install … @v0.1.0` and run it through the committed wrapper without
`TASKRAIL_BIN` or a local pin.

The version must read `0.1.0` exactly: the wrapper accepts an installed CLI only when
`v$(taskrail --version)` equals the pin, so a `0.1.0.dev0` build would never match and
every call would fall back to `uvx`.

## Change set

This branch prepares the release; the tag is created only after it is merged.

| File | Change |
|---|---|
| `pyproject.toml` | `version = "0.1.0"`. |
| `uv.lock` | Regenerated with `uv lock` for the new version. |
| `src/taskrail/__init__.py` | `__version__` read from the installed package metadata (`importlib.metadata`), so `pyproject.toml` is the only place the version is written; falls back to `0.0.0+unknown` when the package is not installed. |
| `CHANGELOG.md` | New: a `0.1.0` entry summarising what the release contains. |
| `README.md` | A short *Releasing* section: tag format, the version rule above, and the steps below. |
| `DESIGN.md` | Status line: released as `v0.1.0`. |
| `tests/` | A test that `__version__` matches `pyproject.toml`. |

After the pull request is merged, and only with explicit confirmation at that point:

1. Create the annotated tag `v0.1.0` on the squash commit on `main`.
2. Push the tag.
3. Verify a clean install from GitHub (see *Verification*).

## Decisions needed

1. **Single version source.** Reading `__version__` from package metadata removes a second
   literal that can drift from `pyproject.toml`. Recommended. The alternative keeps both
   literals and a test that they match.
2. **Version on `main` after the tag.** If `main` keeps `0.1.0` while new changes land, a build
   from `main` claims to be `0.1.0` and the wrapper would accept it as the release. Recommended:
   a follow-up task bumps `main` to `0.2.0.dev0` right after tagging. Alternative: bump only when
   the next release is prepared.
3. **Changelog.** CLAUDE.md says a tool usually needs none, but this one is now versioned and
   tagged. Recommended: a short `CHANGELOG.md` per release. Alternative: rely on the squash
   commit titles between tags.
4. **Who creates and pushes the tag.** It is a publication others will pin, and it must never
   move. Recommended: I do it after the merge, once you confirm in chat; if the auto-mode
   classifier blocks it, you run the two commands I give you.

## Decisions at the scope gate

- The version is written only in `pyproject.toml`; `__version__` reads the package metadata.
- A follow-up task bumps `main` to `0.2.0.dev0` right after the tag is pushed.
- `CHANGELOG.md` gets a short entry per release.
- The change set is approved as written; the tag waits for the merge and an explicit
  confirmation.

## Out of scope

- A GitHub Release page: it needs the API or `gh`, neither available here. The tag alone is
  what `uv tool install` and the wrapper use.
- Publishing to PyPI.
- Automating releases (release-please or similar): worth a later task once there is a second
  release to compare against.
- Moving this repository off `version = "local:."`: it keeps running from source.

## Verification

Before merging, entirely local:

- `uv run pytest -q`.
- `uv build` produces `taskrail-0.1.0-py3-none-any.whl`, and the installed CLI prints
  `taskrail 0.1.0`.
- In a scratch clone of this branch carrying a local, unpublished `v0.1.0` tag:
  - `uv tool install` from that clone and tag, into a temporary tool directory, installs
    `taskrail 0.1.0`;
  - `taskrail init --integration claude` in a scratch repository pins `v0.1.0`, and the
    wrapper runs the installed CLI because the versions match;
  - with no `taskrail` on `PATH` and `TASKRAIL_SOURCE` pointing at the clone, the wrapper falls
    back to `uvx` for the pinned tag, and `validate` succeeds.

After tagging: `uv tool install` from GitHub at `v0.1.0`, into a temporary tool
directory, prints `taskrail 0.1.0`, and `taskrail self upgrade --dry-run` resolves
`v0.1.0` as the latest tag.

### Results before merging

Automated: `uv run pytest -q` → 152 passed, including
`tests/test_version.py`. The stage's `lint` check is not configured in this repository.

Local, with a `v0.1.0` tag that existed only in a scratch clone of this branch
(`c3d6ff9`) and a temporary uv tool directory:

1. `uv build` produced `taskrail-0.1.0-py3-none-any.whl`.
2. `uv tool install` from `git+file://<clone>@v0.1.0`
   installed a CLI printing `taskrail 0.1.0`.
3. In a new git repository, `taskrail init --integration claude` pinned
   `version = "v0.1.0"`. With only that CLI on `PATH` and no `uvx`, the wrapper ran
   `validate` successfully — so it used the installed CLI, whose version matched the pin.
4. With no `taskrail` on `PATH` and `TASKRAIL_SOURCE=file://<clone>`, the wrapper fell back to
   `uvx` for the pinned tag: `--version` printed `taskrail 0.1.0` and `validate` succeeded.
5. `taskrail self upgrade --dry-run` resolved `v0.1.0` as the latest tag.

The checks against GitHub itself wait for the published tag.
