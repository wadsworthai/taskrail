# T003 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human — before any lane started

This task asks for `taskrail init` to be run in a real project and the friction noted. No lane can
do that: this repository has no consumer project in it, and the publishing constraint forbids naming
a private one. The task was escalated before any lane claimed it, and the human — who already uses
taskrail in other repositories — answered the orchestrator's five questions directly.

| # | Question | Answer |
|---|---|---|
| 1 | The install route: `uvx`, or a globally installed CLI? | `uvx`, with no global install — T100's documented default worked as documented |
| 2 | What had to be done by hand after `init`? | Nothing except the autopilot |
| 3 | A CLI message that left them not knowing what to do next? | None |
| 4 | Something taskrail assumed about the repository's layout that was not true? | Nothing |
| 5 | Was the autopilot enabled there? | Yes |

Answered by the human (the repository's maintainer), 2026-09-18. Answer 2 is the whole finding, and
the lane is to write it as a property of taskrail — *`init` does not set up the autopilot* — which is
true of every consumer and identifies none.

## scope gate

Reviewed: the artifact `docs/chores/T003-install-taskrail-in-a-first-consumer-pro.md` and its commit
`f5b7427` (artifact and index row alone); the lane's re-verification of both premises the
orchestrator handed it — `init --help` has no autopilot option, and `grep autopilot
src/taskrail/install.py` returns nothing — and two facts the lane found on its own.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | What should T003 build? | **(B) a fully commented `[autopilot]` block in `default_config()`, plus one sentence in README's *Install*** · (A) an `init --autopilot` flag · (C) documentation only · (D) a follow-up task and close on the write-up | **(B), as recommended** | It removes the friction where the friction happens: the consumer is already inside `.taskrail/config.toml` when the question arises, and the seeded config already uses commented examples under `[columns]` and `[checks]`, so this follows the file rather than inventing a shape. CLAUDE.md prefers a documented convention over a mechanism that enforces it, and a comment *is* that convention. (A) adds a flag, an install path and a second question — does it write `enabled = true` or a disabled stub? — for friction a comment removes; YAGNI. (C) alone is refuted by the evidence: README already names `enabled` and DESIGN.md lists all sixteen keys, and the friction happened anyway. (D) defers ten commented lines at more cost in process than in code. |
| 2 | Commented, or a live `enabled = false`? | **commented** | **commented** | The seeded config's meaning stays byte-for-byte what it is today: no `[autopilot]` table appears in any new repository, and nothing changes for the loader or for `validate`. |
| 3 | Which keys? | **the five this repository's own config uses** · all sixteen | **five, with a pointer to DESIGN.md §12** | `enabled`, `max_lanes`, `read_first`, `governing`, `escalate_gates` are what a repository actually sets; the rest would be noise in every new config. |

Given with the answers: the lane's own finding decides how much the README sentence matters —
`upgrade()` calls `install()` and `set_version_pin()`, and `installer.seed` writes the config only
when it is missing, so **a seeded block reaches new installs only**. Every repository that has
already run `init`, including the consumer this task came from, is served by the README line and by
nothing else. Say so in the artifact.

## implement gate

Reviewed: commit `83df476` and the diff `afcd71c..HEAD` — seven commented lines in
`default_config()`, one test, the artifact, and nothing else; the seeded block read in full from the
source; the lane's run against a scratch repository, where the block is inert (`validate` exits 0
with no `config-unknown-key` warning and `autopilot start` still exits 5 with its own message) and
correct (uncommenting those six lines and nothing else makes `autopilot start` exit 0);
`taskrail checks T003 --stage implement` (1,248 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | (B) was built with both sub-choices as approved, and the change stayed inside the four files the scope named. |
| 2 | The test asserting both halves — that the block stays a comment, and that uncommenting it works | **accept** | **accept** | Pinning only the first would let the block rot into keys taskrail no longer takes while still passing. The second half is what makes it a comment someone can rely on rather than decoration. |
| 3 | Leaving `README.md` and `CHANGELOG.md` uncommitted for the `docs` stage | **accept** | **accept** | The kind puts documentation in its own stage, and both files are shared append-only ones; keeping them out of the implement commit makes the code review read as code. |

## close

Reviewed: the whole diff against the merge base, `origin/main...HEAD` (three dots; `main` has moved
since this branch was cut, so the two-dot form shows other branches' work as deletions) — seven
commented lines in `default_config()`, one
test, seven lines of `README.md`, one `CHANGELOG.md` bullet, the artifact, an index row and T003's
`✅`, with `DESIGN.md` and `CLAUDE.md` untouched; the three stages' checks, the real `init` into a
scratch repository, and `taskrail validate` (106 tasks, 0 errors); the claim released.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `docs` stage opened nothing | **accept** | **accept** | The finding is discharged by this change, and nothing outside the approved boundary needed touching. |
| 2 | Pull request type | **`feat` / `install`**, as the lane recommends · the kind's default `chore` | **`feat` / `install`** | What `init` writes changes, which is user-visible; CLAUDE.md asks for the type of the most significant change with the affected area as the scope. |
| 3 | The title | **hand-written, naming the change** · the row's title, which `review` generates | **hand-written** | The row is named for the work — *Install taskrail in a first consumer project* — and that work was the human's, done before the lane existed. The squash commit is the only line that reaches `main`, and it should say what landed: the seeded block. This is the second time in this run a row's title has been the wrong sentence for the commit (T110 was the first), which is worth noticing but not worth a task yet. |

Recorded for the pull request, since a reviewer needs it and it is not obvious from the diff: the
two halves reach **different repositories with no overlap**. The seeded block serves repositories
that have not run `init` yet; the README paragraph is the only thing that reaches the ones that
have, because `installer.seed` writes the config only when it is missing and `upgrade` rewrites only
the version pin. Drop the prose and the change serves nobody who already installed taskrail; drop
the comment and it fixes nothing where the friction happens.
