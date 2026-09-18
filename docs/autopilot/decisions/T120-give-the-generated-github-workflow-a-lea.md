# T120 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T120-give-the-generated-github-workflow-a-lea.md` and its commit
`29aa158` (artifact and index row alone); both workflows as they stand on `main`; the sha256 of the
managed copy matching its recorded digest, so `upgrade` rewrites it without `--force`; the four
existing workflow tests; and `DESIGN.md` §9's *Extras* bullet.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where the block goes and what it contains | **workflow-level `permissions: contents: read`** · job-level · `permissions: {}` · leave it to consumers | **as recommended** | The lane checked what the job actually does rather than assuming: `checkout` reads the repository, `setup-uv` fetches a release of a public repository, and `validate` reads the checkout and at most clones taskrail over anonymous HTTPS. Nothing writes back, and naming one scope makes every unnamed scope `none`. Workflow-level because the file has one job today, it matches `ci.yml`, and a second job added later inherits the restriction instead of silently getting the default. **`permissions: {}` is the option to reject loudly**: it breaks `checkout` in a *private* consumer repository, and taskrail's consumers are often private. |
| 2 | Regenerating this repository's own generated workflow here | **yes, with this worktree's `upgrade`** · leave it to a later `upgrade` | **yes** | The file is managed and provably unedited, so `upgrade` rewrites it cleanly, and that is the very pick-up path this change tells consumers to use. Leaving it stale would ship a generated file that does not match its own template — the argument T118 faced about the wrapper and answered the same way. The lane's offer to stop if `upgrade` touches anything beyond the workflow and the manifest is the right guard. |
| 3 | What the test asserts | **the literal block, beside T116's tag test** · a general "a `permissions` key exists" · parse the YAML · extend T116's test | **the literal block** | A general assertion would pass for `contents: write`, which is the exact failure this task prevents — there is nothing to generalise over. The suite has no YAML parser and taskrail has no runtime dependencies, so parsing is out. Two invariants in one test makes a failure read wrongly. |
| 4 | `DESIGN.md` §9 and `CHANGELOG.md` | **a clause in the existing *Extras* sentence, one changelog bullet, no `README.md` change** | **as recommended** | §9 already records this template's other two deliberate properties with their reasons; the permissions block is the third of exactly that kind. The changelog is where a consumer with a locally edited workflow — the one case `upgrade` will not fix for them — is told to add the block themselves. |

Given with the answers: this branch's base already contains T118 (`b865681`), which the lane noticed
and reported; the primary checkout's `main` was behind at that moment and has since caught up.

## implement gate

Reviewed: commit `30f9159` and the diff `05bcc16..HEAD` — three template lines, one test, the
regenerated workflow and its manifest digest, and the artifact, with `ci.yml`, the wrapper template,
`.taskrail/bin/taskrail`, `cli.py` and `DESIGN.md` §7 untouched; the test's recorded failure; the
real `init` into a scratch repository and its YAML parse; and, recomputed by the orchestrator, the
`sha256sum` of the regenerated workflow matching the digest `upgrade` recorded (`eb05606e…`).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The stage did what the scope gate approved and nothing surprising came up. |
| 2 | The `upgrade` guard the lane offered at the scope gate | **held; accept** | **accept** | The run's report shows the wrapper, the config with its `local:.` pin, `TODO.md` and all eight skill files coming back `unchanged` — so regenerating the workflow touched the workflow and the manifest and nothing else. The guard was worth asking for and worth reading afterwards. |
| 3 | The YAML parse confirming no job-level `permissions` | **accept** | **accept** | It is the check that makes the workflow-level choice mean what decision 1 said it means: the workflow grant *is* the job's grant, so every unnamed scope is `none`. Asserting the literal block in the suite and parsing once by hand here is the right division — the suite stays dependency-free. |

## close

Reviewed: the whole diff against the merge base — three template lines, one test, the regenerated
workflow and its digest, the `DESIGN.md` §9 clause, one changelog bullet, the artifact, two index
rows and T120's `✅`, with `ci.yml`, the wrapper, `cli.py` and §7 untouched; `taskrail validate`
(109 tasks, 0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The `docs` stage continued without stopping | **accept** | **accept** | Its gate is `conditional` and nothing arose to decide: no follow-up opened, and no design principle argued against the row. |
| 2 | The changelog bullet ending in the two-line block a consumer can paste | **accept** | **accept** | `upgrade` rewrites an untouched workflow and reports an edited one as `edited locally; --force replaces it`. For that one consumer the change can do nothing automatically, so the bullet gives them the exact lines instead of describing them. That is the difference between announcing a hardening and delivering it. |
| 3 | Pull request type and scope | **`chore` / `install`** · `fix` | **`chore` / `install`** | It hardens a generated file rather than repairing a broken one — unlike T116, which fixed a workflow that could not resolve its action. The template lives in `src/taskrail/install.py`. |

## rebase after T119 merged

`main` advanced to `8c3358f` (T119). This branch was rebased onto `origin/main`, with two conflicts,
both known classes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2. |
| 2 | `TODO.md` status cells | **unite by ID, `✅` wins** | **as decided** | Known conflict class 1. |

`.taskrail/installed.json` did not conflict — T119 touched `cli.py` and `DESIGN.md` §7, no managed
file — and `upgrade` re-run in the rebased worktree reports all 13 files already up to date, so the
workflow and its recorded digest are still consistent.

After the rebase: `permissions: contents: read` is in the committed workflow,
`taskrail checks T120` passed with 1,256 tests, and `taskrail validate` reports 109 tasks, 0 errors.
