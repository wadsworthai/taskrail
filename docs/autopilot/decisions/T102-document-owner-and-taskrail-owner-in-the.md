# T102 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## scope gate

Reviewed: the artifact at commit d455827, the diff against the base (the artifact and one index row;
`DESIGN.md` untouched as `scope` requires), and the lane's re-verification, checked by the
orchestrator: `grep -n '^### 6' DESIGN.md` puts §6.1 at 481 and §6.2 at 519, so line 511 — the
sentence the row points at — is inside **§6.1**; and `grep -c 'add_argument("--owner")'` confirms
five of the ten carry no help string.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Write in §6.1, where the sentence is, or §6.2, as the row says? | **§6.1** · §6.2 as written · §6.1 plus correcting the other documents | **§6.1, beside line 511** | The row's own pointer — "beside the line that already says the owner defaults to `$TASKRAIL_OWNER`" — names line 511 exactly, and that line is in §6.1. §6.2 is the optional pushed ref and would strand a paragraph about the local default under a heading that has nothing to do with it. The "§6.2" in the row is a miscount inherited from T095 and repeated by T098; both are merged records of what was believed at the time and are not rewritten. Correcting them is not worth widening this lane's touch map for. |
| 2 | Name the ten commands, or state the rule generally? | both, rule first · the rule alone · the names alone | **both, as drafted** | The lane's argument is the right one: with the rule in front, an eleventh command satisfies the sentence before anyone updates the list, so the paragraph degrades into incomplete rather than into wrong. The names alone would be wrong the day an eleventh lands; the rule alone sends the reader to `--help`, and invisibility of this surface is what created the task. |
| 3 | Keep the `autopilot start` / `autopilot close` clause? | keep · drop | **keep** | It is the hard evidence for the human's stated reason: for those two commands the environment variable is not a convenience but the only identity available, since neither takes `--owner`. That is a surface no search for the flag can find. |

Instructions given with the answers: re-run the ten `--help` checks after the edit so the list is a
statement about the built parser rather than about the source; touch nothing in `DESIGN.md` outside
the single insertion point.

**The finding this gate exists for.** The lane was told to re-verify rather than trust, and it found
the task's own row wrong about which sub-section holds the sentence. That is the third time in this
run that re-verification caught an inherited claim — after T095's two corrections to T088 and T098's
correction of its own row — and it is the strongest argument for keeping that instruction in every
brief.

Reported, not fixed, and carried to the human: five of the ten `--owner` arguments have no
argparse `help=` (`release`, `reserve-id`, `new`, `done`, `discard`). It is the same family as
T101's `next --limit` and T101's measurement of 65 such arguments — the second lane to hit it, which
is what turns a curiosity into a question worth putting to the human.

## implement gate

Reviewed: the diff against the lane's true base (5d605ca) — **8 insertions, 0 deletions**, one hunk
inside §6.1; the `--help` re-runs against the built parser; and `taskrail checks T102` re-run by the
orchestrator, which passed. A diff against today's `origin/main` looks larger only because the base
predates T100's §9 rewrite; the rebase at hand-off resolves that, and the lane's own change is the
pure insertion.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the applied paragraph what was approved? | accept · amend | **accepted** | Verbatim, in §6.1, with nothing modified or deleted. §6.1 now runs 481-526 and every line below 512 shifted by a clean offset, which is why it will rebase past T099 without a textual overlap. |
| 2 | The evidence standard | accept · ask for more | **accepted, and worth naming** | Each of the paragraph's three claims was exercised in a throwaway repository rather than asserted: the default owner, `TASKRAIL_OWNER` covering a command with no flag on the call, and `--owner` overriding the variable for one command — with the exit 4 refusals that prove the claim was really held by someone else. The list of ten was re-run against the built parser after the edit, and the exclusions checked too. |

## Conflict handling agreed for all lanes

Run 20260918-1. T099 edits `DESIGN.md` §1, §3.1, §4 and §7.3; T101 one line of `cli.py`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `DESIGN.md`, edited by two live lanes | split by section · one lane only | **T102 takes §6.1 only; T099 takes §1, §3.1, §4 and §7.3** | A pure insertion of seven lines at 512, thirty lines from anything T099 touches. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1) and appended index rows (2); a conflict inside `DESIGN.md` escalates** | Which is why each lane names its lines at the gate. |
| 3 | May this lane fix the missing help strings? | allow · forbid | **forbidden** | Code, outside the touch map, and the subject of a question now before the human. |
