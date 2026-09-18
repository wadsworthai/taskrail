# T097 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: the artifact at commit 9cc71f7, the diff against the base (the artifact and one index row
only), `taskrail checks T097 --stage frame` (`no checks` … `passed`), and the lane's two corrections
to the task row's framing.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is this the right question for the human? | as drafted · ask only about `--fetch` · ask whether the remote half should exist | **as drafted, as recommended** | It separates the fact only the human holds — who runs taskrail from more than one clone — from the only change on the table, one line of skill text, so a "no" to the first does not read as licence to remove the mechanism. Asking only about `--fetch` would lose the record T088's recommendation exists to obtain; asking whether the remote half should exist is forbidden by T087's prospective verdict. |
| 2 | The shape of the answer | three questions with a default per line · two questions · no defaults | **three questions, in T095's format, and route C is approved** | The human has answered that format once already. Route C — keep the flag but have the skill say plainly that the fetch does nothing unless the repository sets `branch_record_remote` — is the honest middle the row's binary does not offer, and the lane was right to raise it at the gate instead of springing it at `decide`. Splitting questions 1 and 2 costs one word and buys a precise record, since the two keys guard different code and one may be set without the other. |
| 3 | Should `investigate` set the keys in throwaway clones? | yes, two clones · no: probe the unset path by hand and cite the tests | **no — departing from the lane's recommendation** | T095's probes earned their cost because nothing proved those options worked; here `tests/test_branch_records_remote.py` (382 lines) and the `claim_remote` tests already exercise the enabled path, and 20-30 minutes of a lane would not change any of the three answers the human gives. Probe the **unset** path by hand — that is what the `--fetch` proposal turns on — cite the tests for the enabled path, and say in *Limits* that the enabled path rests on the suite rather than on two observed clones. |

Instructions given with the answers: measure route B's blast radius exactly, including
`README.md:50`, which the lane found and the task row missed; keep the note that
`autopilot status --fetch` is an unrelated flag sharing the name; and open no follow-up task before
the human answers.

## escalated to the human

`spike:decide` is in this repository's `[autopilot].escalate_gates`, so the three questions went to
the human. Answered on 2026-09-18. The orchestrator verified the two load-bearing measurements
before escalating: `cli.py:67` returns before touching git when `branch_record_remote` is unset, and
`DESIGN.md:588` already states the flag "does nothing while the setting is off".

| # | Question | Answer | Consequence |
|---|---|---|---|
| 1 | Does any repository set `[git].claim_remote`? | **B — none visible to the human either** | Recorded; nothing retired. The key, its flag and the code it guards stay as they are. |
| 2 | Does any repository set `[git].branch_record_remote`? | **B — none visible either** | Recorded; nothing retired. Route B stayed available for question 3 and was not taken. |
| 3 | The core skill's `--fetch` step | **C — keep the flag and say the condition plainly** | One small chore rewriting that clause so the skill states that the fetch does nothing unless the repository sets `branch_record_remote`, and what it resolves when it does. No behaviour change. |

Answered by the human (the repository's maintainer), through the orchestrator. The task row's own
proposal — dropping `--fetch` — was put to the human with the lane's recommendation against it, and
was not taken: with the key off the flag costs nothing (0.224s against 1.561s for a real fetch,
byte-identical output), and with the key on it is load-bearing.

One task to open: the route-C chore on the core skill's step 3. It ships to every consumer, so it
edits `src/taskrail/skills/taskrail/SKILL.md` and needs `taskrail upgrade` for the installed copies;
`README.md:50` teaches the same command and should be checked while there.

## Conflict handling agreed for all lanes

Run 20260918-1. T094 is live in `config.py`, `project.py`, `tests/`, `DESIGN.md` and `CHANGELOG.md`;
T095 is stopped at its own escalated `decide` gate; T097 touches no code and no shared document.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T097: its artifact, its index row and its own rows in `TODO.md` through the CLI** | It is a spike whose whole output is a questionnaire; `never_edit` is `code` and `specs` for its kind, and the brief forbids `DESIGN.md` and `config.py` outright. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1) and appended index rows (2)** | Resolved at hand-off. A conflict in any source file or in `DESIGN.md` escalates, which is why this lane is kept out of both. |
| 3 | May this lane change the skill line it is asking about? | allow · forbid | **forbidden** | The proposal is what the human answers; the change, if any, is a separate task with its own gate. |
