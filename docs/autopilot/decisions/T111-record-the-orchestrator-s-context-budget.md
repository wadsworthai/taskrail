# T111 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact `docs/chores/T111-record-the-orchestrator-s-context-budget.md` and its commit
`3836c0c` (artifact and index row alone); the figures, which the lane quoted from T057's own artifact
and decision record rather than from its brief; the table of places considered and rejected; and
`tests/test_autopilot_skill.py`, which forbids the portable skill files from naming an agent or a
model. The orchestrator also checked `DESIGN.md`'s own link style and T057's artifact path.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where the measured figures live | the lane's recommendation: inline in `SKILL.md` with the caveat · **the rule in `SKILL.md`, the figures with their provenance in `src/taskrail/integrations/claude.md` and `DESIGN.md` §12.1** | **against the lane's recommendation: rule portable, figures attributed** | The argument that decides it is the lane's own evidence: `tests/test_autopilot_skill.py` forbids the portable files from naming an agent or a model, so inside `SKILL.md` the numbers can only appear stripped of the one thing that makes them meaningful — who measured them, on what. A number that cannot say whose it is invites being read as taskrail's, which is what CLAUDE.md's *Agent portability* section exists to prevent. What every agent must **do** is identical and stays in `SKILL.md`: your session is the one that fills up, measure your own per-task cost, plan the count against it, and hand the rest to a fresh session through the resume path. The figures go where they can be attributed: `DESIGN.md` §12.1, which is free to name Claude Code, and the Claude Code integration note, which the installer inserts into that agent's copy — so the agent the numbers came from still reads them in its own skill. |
| 2 | A clause in the skill's *Resume a run* section | **no** · one sentence there too | **no** | The new *When to run* paragraph already ends on that pointer; restating it in the section it points at is duplication for its own sake. |
| 3 | Recording this run's corroboration in `DESIGN.md` or the skill | **no — record it here instead** · include it | **no** | The lane is right that it cannot verify the number, and a paragraph whose force is that its figures are reproducible is weakened by an unverifiable one beside them. It is recorded below instead. |

Given with the answers: the proposed `DESIGN.md` paragraph links T057's artifact as
`../../docs/spikes/…`, which is wrong from a file at the repository root — `DESIGN.md:1820` links
artifacts as `docs/chores/…`. Use the repository-root form.

### This run's corroboration, recorded here rather than in the shipped text

Run `20260918-1`, the run this task belongs to, compacted its orchestrator after roughly twenty
dispatched tasks — inside the 21-26 band T057 predicted for a 1M-context orchestrator. It is one
more data point from the same agent and model, observed rather than harvested, which is why it
belongs in a decision record and not in `DESIGN.md`.

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `DESIGN.md` §12 with two lanes in it | split by subsection · serialize the lanes | **split: T111 takes §12.1 and the count-choosing text; T112 takes §12.3 and nothing else** | The two changes are about different things — choosing a count, and whether an old handle reaches a lane — and they sit in different subsections, so both can be written at once and git rebases them without meeting. Each lane was told to stop at its gate rather than cross into the other's subsection. |

## implement gate

Reviewed: commit `b4d35c4` and the diff `f7a1ef8..HEAD` — seven files, no code, no test, no
configuration, `DESIGN.md` a single 16-line insertion at §12.1 with §§12.3/4/3.1/7/7.4 untouched;
the portable paragraph read in full by the orchestrator and grepped for the four figures and for
`Claude`, which returns nothing, so the split holds in the file the test polices; the installed copy
grepped for both new texts and diffed against its source; `taskrail checks T111 --stage implement`
(1221 passed) and `taskrail validate`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | The one sentence added beyond what was approved, telling a `DESIGN.md` reader where the figures went and why the skill carries none | **keep it** · remove it | **keep it** | Without it the absence of numbers from the skill reads as an omission a later task would "fix", putting them back in the portable file. Documenting the split is what makes it survive. |
| 2 | Replacing the four numbers in the skill with the method that produces them, rather than deleting the sentence | **accept** | **accept** | "The context you are served per dispatched task, over what a session costs before any task starts, against the context window you have" is the rule the figures were an instance of. It needs no disclaimer because there is nothing left in it to disclaim — which is the test of whether the split was the right call. |
| 3 | Stop again at `docs`, whose only content was the changelog bullet already in the change set? | **fold it into the close** · stop twice | **fold it into the close** | Documentation is this change, and the bullet is committed. |
