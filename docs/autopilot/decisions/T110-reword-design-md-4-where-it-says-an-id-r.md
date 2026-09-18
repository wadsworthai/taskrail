# T110 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T110-reword-design-md-4-where-it-says-an-id-r.md` and its commit
`5667a23` (artifact and index row alone); the two refusal sites in the source; the lane's two CLI
reproductions, which show both messages naming the key *and* quoting its value, so the sentence is
wrong in both halves of its contrast; and the grep showing no other copy of the stale claim.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| D1 | The replacement wording | **`naming the key — `epic_prefix` or `prefix` — and the value it expected`** · `naming the key that would accept it` · drop `and the value it expected` | **as recommended (a)** | It is accurate on both halves against the observed output, and it matches the wording T103 already shipped in the changelog. Spelling the two keys out costs one line in the section a reader would otherwise leave to look them up. Dropping the value clause would replace one inaccuracy with another. |
| D2 | A `CHANGELOG.md` bullet | **none** · a second bullet | **none** | T103 already recorded the user-facing change. `DESIGN.md` is this repository's own design document and neither `init` nor `upgrade` installs it, so nothing a consumer holds changes here. |
| D3 | The stale line numbers in the task's own row | **leave them** · `taskrail edit --description` | **leave them** | The row is closed by this task and the artifact records the real location. Rewriting a `TODO.md` cell that three other live lanes also append to adds conflict surface at hand-off for nothing that outlives the task. |
| D4 | The wrapper resolving its root from the process cwd | **open a task, with the three occurrences as its premise** · leave it · fix it here | **open a task** | Three lanes of this run — T106, T108 and T110 — claimed against the primary checkout before catching it, each having run the worktree's own wrapper from a shell whose cwd was elsewhere. That is the rule of three met by measurement, not by argument, and the fix is a design question about `.taskrail/bin/taskrail` and `DESIGN.md` §9 that does not belong inside a documentation reword. |

Given with the answers: T003's claim is **not** the same mistake. The orchestrator made it
deliberately, from the primary checkout, to hold the task while it waits for the human — an
escalated task that never claimed is otherwise re-dispatched by `next` on the following call. Its
branch is recorded correctly; only its `worktree` field points at the primary checkout, because that
is where the claim was made. Leave it alone.

## implement gate

Reviewed: commit `b80da2a` and the diff `bd821db..HEAD`, read by the orchestrator — a single hunk in
`DESIGN.md`, two lines out and three in, with §4's configuration example, §3.1, §7 and §7.4
byte-identical; T115's row in `TODO.md`; the lane's two reproductions re-run against the edited
branch; `taskrail checks T110` (1221 passed) and `taskrail validate` (102 tasks, 0 errors).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Anything to decide at this gate? | **no** | **no** | The wording, the changelog, the row's line numbers and the follow-up were settled at the scope gate and applied as answered. |
| 2 | T115's kind | **accept `spike`** · `bug` | **accept `spike`** | Its contract is a documented decision, not code under a regression test, which is what the answer to D4 asked for; `spike` is the kind T095 and T097 used for the same shape of question. Note for whoever runs it: this repository sets `escalate_gates = ["spike:decide"]`, so its decision gate reaches the human by configuration. |
| 3 | Stop again at the `docs` stage, which changes nothing? | **fold it into the close** · stop twice | **fold it into the close** | The change *is* the documentation, and the scope-gate grep already showed no other copy of the stale claim anywhere in the repository. A gate whose only content is "nothing to do" is a stop for its own sake. |
