# T116 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## diagnose gate

Reviewed: the artifact `docs/bugs/T116-pin-a-setup-uv-tag-that-exists-in-the-ge.md` and its commit
`de8e8b6` (artifact and index row alone); the generated workflow, produced from this branch's source
into a scratch repository rather than quoted from `install.py`; the tag lists, which the lane
queried over the network and which the orchestrator had independently queried before the row was
written — `astral-sh/setup-uv` has `v10.0.0`, `v10.0.1`, `v10.1.0` and no bare `v10`, and its bare
majors stop at `v7`, while `actions/checkout` publishes `v7` pointing at `v7.0.1`; and the blast
radius, `git tag --contains` showing the line unchanged since `30885c3` and shipped in `v0.1.0`,
`v0.2.0` and `v0.3.0`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Which tag to pin, and does `actions/checkout@v7` stay floating? | **pin both exactly: `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0`** · fix setup-uv only, as the row's wording says · SHA pins · `v10.0.1` | **pin both exactly — against the row's wording, deliberately** | The row says to keep `checkout@v7` floating, and the lane was right to ask rather than follow it. A mixed rule needs a per-action allowlist of who publishes a floating major, and that assumption is exactly what caused this bug; a uniform rule — every `uses:` names an exact `vX.Y.Z` — is the only one a network-free test can enforce, which is what makes Q2 possible. It also matches the pair T108 just merged into this repository's own `ci.yml`, so the generated workflow and ours agree. SHA pins are a different convention and out of proportion here. |
| Q2 | Can a test catch this class offline? | **assert every `uses:` names an exact `vX.Y.Z`** · assert the two literal strings · compare against this repository's `ci.yml` · no test | **the shape assertion** | No offline test can prove a tag exists, and one that asks GitHub is unacceptable now that T108 runs the suite on every pull request. Forbidding the shape that caused the bug is the honest thing a test can do, and the docstring must say what it does not prove. Comparing against `ci.yml` couples the packaged template to a repository-local file, which is cleverer than KISS wants. |
| Q3 | `DESIGN.md` §9 and `CHANGELOG.md` | **both** · changelog only · neither | **both** | The bug is user-visible and shipped in three releases, so the changelog owes a reader what failed and how an installed repository picks the fix up — `taskrail upgrade` rewrites an untouched managed workflow and reports a locally edited one as skipped. §9's *Extras* bullet already explains `fetch-depth: 0`; one clause there records the convention the test enforces, so a later edit does not undo it by reflex. |

Given with the answers: the existing `test_github_workflow_checks_out_full_history` asserts the
literal `actions/checkout@v7` line and must be updated with the pin — it is in this lane's half of
`tests/test_install.py`, not T113's. Stop before touching any shared helper or import in that file,
as offered.

## fix gate

Reviewed: commit `f6f97f9` and the diff `5135da9..HEAD` — two refs in `install.py`, the updated
literal and the new shape test in this lane's half of `tests/test_install.py` with no shared helper
and no import touched, the `DESIGN.md` §9 clause, the `CHANGELOG.md` entry and the artifact; the
regression test's recorded failure naming both loose refs; the regenerated workflow with both tags
resolved against the real remotes; and `taskrail checks T116 --stage fix` (1,248 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The three diagnose answers were applied as given and nothing else surfaced. |
| 2 | The judgement the lane made inside the stage — collecting every offending ref and asserting once, instead of asserting per ref in the loop | **accept** | **accept** | The first form stopped at `actions/checkout@v7` and never reached the ref in the root cause, so its failure message would have pointed at the wrong line. The version that names both is what makes the test readable when it fires years from now. |
| 3 | The changelog quoting `edited locally; --force replaces it` verbatim from `Installer.managed` | **accept** | **accept** | A consumer reading the entry can match the string against what their own `upgrade` prints, which is the difference between an announcement and an instruction. |

## close

Reviewed: the whole diff `origin/main..HEAD` — two refs in `install.py`, 15 lines of test, the
`DESIGN.md` §9 clause, the `CHANGELOG.md` entry, the artifact, two index rows and T116's `✅`;
`taskrail checks T116 --stage fix` (1,248 passed) and `taskrail validate` (106 tasks, 0 errors);
working tree clean and the claim released.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `impact` sweep opened nothing — accept? | **accept** | **accept** | It was a real sweep, not an assertion: every `uses:` in the repository was listed, leaving two live sites (the template and this repository's `ci.yml`, already pinned by T108) and some frozen quotations in past tasks' write-ups, which are records and not code. |
| 2 | Pull request type and scope | **`fix` / `install`** · `fix` / `cli` | **`fix` / `install`** | The generated workflow is written by `src/taskrail/install.py`, and CLAUDE.md asks for the affected area as the scope. |

## rebase after seven branches merged

`main` advanced to `f23dac5` (T112). This branch was rebased onto `origin/main`, with two conflicts,
both known classes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2; united by ID, no duplicate. |
| 2 | Conflict in `CHANGELOG.md` | **keep both bullets**, this branch's above the mainline's | **keep both** | Appended changelog bullets, known conflict class 2; *Unreleased* is newest-first and this branch lands after the ones already there. |

After the rebase: both pins in place (`actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.1.0` at
`src/taskrail/install.py:270` and `:273`), `taskrail checks T116` passed with 1,248 tests, and
`taskrail validate` reports 106 tasks, 0 errors.
