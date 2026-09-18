# T087 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: `docs/spikes/T087-decide-whether-the-design-principles-gov.md` at commit 7482950, the
diff range `origin/main..HEAD` (2 files, 74 insertions: the artifact and one index row),
`taskrail checks T087` re-run in the lane's worktree (`no checks for T087` … `passed`), and the
task row's premise against `CLAUDE.md` at 5476c00, where the `## Design principles` section is
present and says only what the lane quotes.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the question as framed, the approach and the limits? | A as framed · B drop the reach sub-question · C also design the wording · D re-measure the CLI surface in depth | **A, as recommended** | The three sub-questions are the task row's own, and the row's premise holds. B would leave T088 and T089 without knowing whether an executor ever reads the principles, which is what makes their findings actionable. C is adoption, which the executor skill and the lane brief exclude from a spike. D duplicates T088. |
| 2 | Which governing text must the `investigate` stage weigh for the reach sub-question? | leave it to the lane · name the passages | **Name them: CLAUDE.md *Agent portability* and DESIGN.md §8** | *Agent portability* requires the skills under `src/taskrail/skills/` to stay agent-agnostic and free of this repository's specifics, and DESIGN.md §8 makes them the portable core shipped to every consumer. A consumer's principles are not this repository's, so the cost of the "put them in the skills" option is not only size. The lane weighs this; it is not told the verdict. |
| 3 | Where should the refusal sub-question look for existing vocabulary rather than inventing a path? | leave it to the lane · name the passages | **DESIGN.md §5.6 and §12.6** | §5.6 defines a *decision* — a choice the task, the artifact, the repository's instructions and the skill do not settle — and the `decisions` gate; §12.6 lists escalation reason 6, "a task row rests on a false premise", which is the nearest existing path for an executor that disagrees with what a task asks for. A refusal mechanism that duplicates either is a cost to state. |

Instructions given with the answers: continue into `investigate` (gate `none`, no commit), then
write the full artifact and stop at `decide`. Keep the scratch measurements out of the repository,
as the executor skill requires. The `decide` gate is escalated to the human by this repository's
`escalate_gates = ["spike:decide"]`, so the report must let a human accept or reject without
reading the diff.

## escalated to the human

`spike:decide` is in this repository's `[autopilot].escalate_gates`, so the verdict went to the
human. Reviewed before escalating: the artifact at commit 653aa4d, the range `origin/main..HEAD`
(4 files, 412 insertions), `taskrail checks T087 --stage decide` (`no checks` … `passed`), the full
suite the lane reported (`uv run pytest -q`: 1183 passed), and an independent re-measurement of the
CLI surface from the live argparse tree (27 top-level commands, 42 at all levels, ~70 distinct long
flags, 9 first-level configuration names) which confirmed E9 and contradicted the figures in T088's
row. The orchestrator also told the human that E1 — the message of commit 5476c00 — was written by
an agent in the session that produced the section, not by the human, so it evidences the drafter's
intent rather than the human's.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Scope: do the principles judge only the change a task makes, or also the code that exists? | prospective · also retroactive · leave unstated | **prospective** | As recommended. They judge what a task adds or changes; what already exists is reopened only by a task that asks for it. A retroactive default contradicts the scope rule the skills already state, defeats the touch map, and on a public tool would let options private consumers depend on be removed as a side effect of unrelated work. |
| 2 | Reach: where does an executor read them? | CLAUDE.md plus one generic pointer in the core skill · CLAUDE.md only, core untouched · name the principles in the executor skills | **CLAUDE.md plus one generic pointer in the core skill** | As recommended. The pointer is agent-agnostic and repository-agnostic — read the repository's agent instruction files before planning — generalising what `taskrail-chore` already does. Naming the principles in the shipped skills was refused: it would ship one repository's taste to every consumer with the authority of the procedure, against *Agent portability* and DESIGN.md §8. |
| 3 | Refusal: may an executor refuse a described design on a principle? | object, not refuse · a true veto · leave the text as it is | **object, not refuse** | As recommended. At the task's first gate the executor names the principle and proposes the alternative as a decision, then builds what the answer says; §5.6 supplies the stop and §12.6 reason 6 the escalation, so no new mechanism is added. With it: replace "the plan gate" with the task's first gate (`plan`, `scope`, `diagnose` or `frame`), since `plan` is a stage of `feature` only, and forbid substituting a simpler design silently. |
| 4 | Follow-ups: when are the three chores opened? | all three on this branch · only the two adoption chores · none until after the merge | **all three on this branch** | As recommended, so the verdict and its adoption are reviewed in one pull request. The third corrects T088's row rather than the lane editing another task's row, which the touch map forbids. |

Answered by the human (the repository's maintainer), through the orchestrator, at the `decide`
gate of run 20260918-1.

Consequence for dispatch, decided by the orchestrator: T088's row keeps its wrong figures until
that chore is worked, so when T088 is dispatched its lane brief carries the measured figures from
E9 as verified context and names the chore that corrects the row.

## Conflict handling agreed for all lanes

Run 20260918-1 works E08: T087 now, then T088 and T089 together once T087 is `done-branch`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | one artifact per lane · shared edits | **Each lane edits only its own `docs/spikes/T0NN-*.md`, plus one appended row in `docs/spikes/README.md` and its own row in `TODO.md` through the CLI** | The three tasks of E08 are spikes with the same artifact directory; nothing else is shared. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **Known classes only: appended index rows (class 2) and backlog rows (class 1)** | `docs/spikes/README.md` is an index and `TODO.md` a backlog file; both are known conflict classes resolved at hand-off, and `autopilot status` reports them under `known_overlaps`. |
| 3 | May a lane edit `CLAUDE.md`, `src/taskrail/skills/` or code? | allow · forbid in E08 | **Forbidden for every lane of this run** | All three tasks are spikes: they decide, they do not adopt. Adoption becomes follow-up tasks, which a lane may open with `taskrail new` on its own branch. |
