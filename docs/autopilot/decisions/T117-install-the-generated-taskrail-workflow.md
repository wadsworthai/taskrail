# T117 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T117-install-the-generated-taskrail-workflow.md` and its commit
`576fa86` (artifact and index row alone, the trial reverted before it); the trial run's full JSON,
the `installed.json` diff, the generated workflow and its sha256 matching the hash `init` recorded;
the T116 precondition on `main`; and `CLAUDE.md`'s *Layout* block.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Commit exactly what `init --github-workflow` writes? | **yes, unmodified** · hand-tune the YAML · wait for a better template | **yes** | The workflow is a managed file: `init` and `upgrade` rewrite it from the template, so a hand edit is lost at the next upgrade. The trial showed one file created, one updated, and nothing else — in particular `.taskrail/bin/taskrail` reported `unchanged`, so T118's territory is untouched. |
| 2 | Two workflows, or one? | **keep them separate** · merge `validate` into `ci.yml` · drop `ci.yml`'s test job | **separate** | Installing the extra here is how this repository dogfoods what its consumers get, and `installed.json` recording no extras is the defect this row names. The jobs genuinely differ: the generated one needs `fetch-depth: 0`, which `ci.yml` deliberately avoids, and `ci.yml` needs a matrix `validate` has no use for. The overlap is two cached setup steps. The lane agreed with T108's decision 1 **after** seeing both files side by side, which is worth more than agreeing with it in the abstract. |
| 3 | Required checks | **name them in the write-up, configure nothing** · say nothing | **name them** | The set on `main` becomes `test (3.11)`, `test (3.14)` and `validate`. None can be marked required until the workflow has run once on `main`, and branch protection is the human's, not a lane's — but the human cannot act on what nobody wrote down. |
| 4 | `CLAUDE.md`'s *Layout* line | **the tree form, naming both files** · one line · leave it | **the tree form** | The line as it stands describes a single workflow and becomes wrong the moment a second exists, and `CLAUDE.md` is a `read_first` document. The tree form matches the block's own style, which already uses `├──` and `└──` under `src/taskrail/`, and it says which file does what — the thing a reader opening that directory wants to know. |
| 5 | The generated workflow sets no `permissions` | **open a follow-up** · fix it here · say nothing | **open a follow-up** | A real hardening gap in what every consumer installs: `ci.yml` sets `permissions: contents: read` and the template sets none, so the `validate` job runs with the repository's default token scope. Fixing it means editing `src/taskrail/install.py`, which T118 holds, and CLAUDE.md says to open a task rather than widen this one. Good catch — it came from reading the two files beside each other, which is exactly what this task put the lane in a position to do. |

Given with the answers: nothing in this task is a `CHANGELOG.md` entry — it is a repository-only
change, and T058, T069, T090 and T108 all landed without one.

## implement gate

Reviewed: commit `80a104f` and the diff `190b9c4..HEAD` — the generated workflow, the
`installed.json` extras and hash, and the artifact, with nothing else touched; the sha256 of the
committed file re-computed by the orchestrator and matched against the hash in `installed.json`; the
idempotence re-run, the YAML parse, the `yamllint` comparison against `ci.yml`, the real
`.taskrail/bin/taskrail validate`, and `taskrail checks T117 --stage implement` (1,248 passed).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | Everything the scope gate settled was applied, and `init` wrote what the trial predicted, down to the hash. |
| 2 | The lane's disclosure that it wrote an unmeasured test count into the artifact and replaced it before committing | **accept, and record it** | **accept** | Nothing unmeasured reached the commit, and saying so unprompted is what makes the rest of the evidence worth trusting. It is recorded here rather than quietly dropped. |
| 3 | The `yamllint` discrepancy with T108's merged write-up | **note it, open nothing** | **note it** | T108's artifact says `yamllint` reports nothing for `ci.yml`; with this lane's rule set both files emit one `document-start` warning and exit 0. The difference is the rule set, not a regression, and both files behave identically — which is the fact this task needed. A merged artifact's minor imprecision is not worth a task. |

## close

Reviewed: the whole diff against the merge base — the generated workflow, `installed.json`, the
`CLAUDE.md` tree form, T120's row, T117's `✅`, the artifact and its index row, with
`src/taskrail/install.py`, `.taskrail/bin/taskrail`, `src/taskrail/cli.py` and `ci.yml` untouched;
`taskrail checks T117 --stage implement` (1,248 passed) and `taskrail validate` (109 tasks,
0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Folding the `docs` gate's report into the hand-off | **accept** | **accept** | The instruction said to stop at that gate to report the follow-up's ID; the lane read it as authorising the close once nothing was left to decide, and reported the ID here. That is the outcome the instruction wanted and it saved a round trip. The lane asked whether a separate stop was meant, which is the right way to raise an ambiguity rather than assume it away. |
| 2 | T120's epic | **E05, as opened** · E06 | **E05** | It is the shipped template every consumer installs, not this repository's own tooling — the same epic as T116, the previous fix to that template. |
| 3 | Pull request type and scope | **`chore` / `install`** · `ci` / `repo` | **`chore` / `install`** | Nothing here is new behaviour: it installs, in this repository, the workflow the installer already generates. `install` is the area; `ci` belonged to T108, which wrote a workflow by hand. |

## rebase after T003 merged

`main` advanced to `18bb109` (T003). This branch was rebased onto `origin/main`, with two conflicts,
both known classes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflicts in `docs/chores/README.md` and `docs/autopilot/decisions/README.md` | **keep both** · stop | **keep both** | Appended index rows, known conflict class 2; united by ID, no duplicate. |

T003 touched `src/taskrail/install.py`'s `default_config()` and `README.md`, neither of which this
branch touches, and `.taskrail/installed.json` did not move on `main`, so nothing else met.

After the rebase: both workflows present in `.github/workflows/`, T120's row in `TODO.md`,
`taskrail checks T117` passed with 1,249 tests, and `taskrail validate` reports 109 tasks, 0 errors.
