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
