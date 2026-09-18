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
