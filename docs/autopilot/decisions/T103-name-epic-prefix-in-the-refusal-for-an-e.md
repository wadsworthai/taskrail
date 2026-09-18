# T103 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact at commit 1bcb73e, the diff against the base (the artifact and one index row;
no source touched, as `scope` requires), and the lane's reproduction of the failure in a throwaway
repository, which is the evidence the wording rests on.

**A correction the orchestrator owes the lane.** The brief quoted this task's row up to "Name the
key in the message" and stopped; the row continues "and keep the same shape for the prefix refusal
in `project.py` if it has the same defect". The lane read the row itself, found the clause, found
the defect, and asked. Its touch map was drawn from the truncated quote, so it is widened here.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `project.py:43` here, or a follow-up? | **here** · a follow-up | **here; the touch map is widened to `src/taskrail/project.py`** | The row asks for it. One word each, one family, one reviewer pass — splitting it would cost more in ceremony than the change itself. No other lane holds that file. |
| 2 | `importer.py:362`, the third sibling | leave it, noted · include it · a follow-up task | **leave it, noted in the artifact** | A different command, not named by the row, and its message already names `id_digits` in the hint it appends. The lane checked that including it would break no test, so this is a free choice made on scope rather than on cost — which is the right reason to decline. |
| 3 | Name `id_digits` in the `task-id` message too | leave it · name it | **leave it** | The row asks for the prefix refusal. A bare number is self-explanatory where bare letters are not, and every grammar that names the key reads badly. |
| 4 | A `CHANGELOG.md` bullet | **yes, one short bullet** · no | **yes** | It changes what every reader of a failed `validate` sees, which is the kind of change a consumer meets after an upgrade — unlike T098 and T102, which changed only a repository document. One correction to the brief: **appended changelog bullets are a known conflict class** (class 2), so the risk of a parallel lane adding one is not a reason to decline; the orchestrator's earlier lane briefs listed the classes incompletely. |

Instructions given with the answers: assert that the key is named rather than pinning the sentence,
following `tests/test_import.py:462-463`, which is the house pattern the lane found; re-run the
`EP01` reproduction and a matching `task-id` one after the change.

Noted: `epic-id` has **no** test anywhere in the repository, which the lane established rather than
assumed after the brief claimed one existed. Two new tests, not an extension.

## implement gate

Reviewed: the two message strings and the two tests read by commit range, the red-first evidence
(both tests fail on the exact assertion they exist for when only the two source files are stashed),
and `taskrail checks T103` re-run by the orchestrator, which passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the change what was approved? | accept · amend | **accepted** | One word added to each message, two tests asserting the key is named rather than pinning the sentence, and no error code, exit code, regex or `--json` shape touched. |
| 2 | `DESIGN.md` §4's sentence, which this change makes stale | open a follow-up · fix it here · ask T099 to fix it | **open a follow-up task** | The sentence T098 added reads "`validate` refuses an ID that does not match, quoting the prefix it expected rather than the key" — true when written, false once this lands, and its *reason for existing* disappears with it. It sits in §4, which T099 is editing right now, so touching it would risk a conflict in a file that is not a known conflict class; and T099 has already passed its own code review, so adding to its scope now would mean re-reviewing it. A one-point chore is the cheap, honest route. |

The lane's own framing of the evidence is worth keeping: a message test that has never been seen red
is worth little, so it stashed only the two source files, watched both tests fail on their own
assertions, and restored. It also ran the task end to end — hit the failure, did what the new message
tells a reader to do, and got a clean `validate`. That is the task's whole purpose demonstrated
rather than argued.

Noted, no action: the worktree's `CLAUDE.md` carries the *Design principles* section that the
primary checkout lacked when this run began, because T090 merged mid-run. Every lane briefed from
here on reads the current file; the observation is correct and cost nothing.

## close gate and rebase at hand-off

Reviewed the close: `done` committed on its own, the backlog differing only in this task's row and
T110's, no upstream on the branch, `taskrail validate` clean. Rebased onto `origin/main` over T102
and T099; three conflicts, all known classes (the two artifact indexes and `TODO.md`'s rows). No
source file conflicted, as the lane predicted from its own diff of the base against the mainline.
After the rebase `taskrail checks T103` passed.

Published as **`fix(cli)`**, departing from the kind's default `chore`, on the lane's argument: the
pull request title is the single commit that reaches `main` and is what semantic versioning reads,
and this change alters what every consumer sees from a failed `validate` after an upgrade — which is
why it earned a changelog entry. A `chore` title would ship that entry with nothing to trigger a
release.

## Conflict handling agreed for all lanes

Run 20260918-1. T099 holds `config.py` and `install.py`; T102 holds `DESIGN.md` §6.1.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by file · shared | **T103: `backlog.py`, `project.py`, `tests/`, `CHANGELOG.md`** | No other live lane holds any of them. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), appended changelog bullets (2); a conflict inside a source file escalates** | |
| 3 | May this lane change behaviour? | allow · forbid | **forbidden** | Message text only: no exit code, no error code, no regex, no `--json` shape. |
