# T096 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: `docs/chores/T096-settle-whether-autopilot-handoff-is-a-pl.md` at commit 306ad79, the diff
against the base (the artifact only, nothing else edited as `scope` requires), and every citation the
lane's verdict rests on, checked by the orchestrator on the mainline rather than taken from the
report: `DESIGN.md:1722-1723` ("Not planned now: … a `batch` hand-off mode"), `DESIGN.md:1734` (the
§12.10 condition for adding it), `tests/test_autopilot.py:172` (which asserts `handoff = "batch"` is
refused today), and `docs/spikes/T033-…:129` ("The §12.10 condition for adding `batch` is not met").
The three copies of the comment are as the lane reports: §4's is bare, §12 and §13's already hedge
with "at first".

The lane's finding changes the question the task was opened with. T088 recorded a key whose whole
range is its default and could see no intent; the intent is recorded in two places and the condition
for the second value was already measured by a past trial. So this is a named extension point with a
deferred second value, not a placeholder.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Settle it by documenting the recorded intent, or escalate to the human? | document · escalate · propose retiring the key | **document, as recommended** | The escalation route existed because T088 could see no intent. The repository has already answered: `batch` is the foreseen second mode and T033 measured that the condition for adding it is not met. Escalating would spend a human decision on a question the record settles, and retiring the key would be a silent loss for any repository that set it — the very failure T094 is adding a warning for, in parallel. |
| 2 | The one comment line in `src/taskrail/config.py`? | include it · `DESIGN.md` only | **include it** | `config.py:47-48` is exactly where T088 hit the question, and a source reader does not have §4 in front of them. It sits above `HANDOFF_MODES` at line 48, far from the `[autopilot]` parsing at 330-360 that T094 is editing; if a conflict does arise it is a one-line addition in a file neither lane restructures. |
| 3 | Is the §12.10 edit inside the touch map? | include it · §4 only | **include it** | The brief named §4 because that is where the puzzle shows; §12.10 is where the intent lives, and leaving it in the future tense ("the trial shows … add `batch`") after T033 answered it would make the new §4 pointer half-true. One line, same list style. The touch map is widened to §12.10 for this. |

Instructions given with the answers: keep the §12.10 entry live for a future trial rather than
deleting it — the condition may be met by a later run — and add no `CHANGELOG.md` entry, since no
consumer's behaviour changes.

Noted, no action: the lane's first `claim` ran with the CLI resolving the main checkout as its root,
recorded `branch: main` and warned; the lane released it and re-claimed with `--root <worktree>`,
leaving the other lanes' claims untouched. That is the CLI behaving as designed — the wrapper
resolves the root from the working directory — and the lane's handling was correct.

## Conflict handling agreed for all lanes

Run 20260918-1, three lanes: T094, T095, T096.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T094: the validator and its tests. T095: its artifact only, no code. T096: `DESIGN.md` §4 and §12.10, and one comment line in `config.py` above `HANDOFF_MODES`** | The only place two lanes meet is `src/taskrail/config.py`, and they meet at opposite ends of it: T096 adds a comment at line 48, T094 works in the parsing around 330-360. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), changelog bullets (2)** | Resolved by the orchestrator at hand-off. A conflict inside `config.py` would be outside the known classes and escalates. |
| 3 | May a lane retire or rename a configuration key? | allow · forbid | **forbidden in this run** | T087's verdict, now in `CLAUDE.md`, makes the principles prospective: what exists is reopened by a task that asks for it. T095 collects the questions; retiring anything is a separate task the human approves. |
