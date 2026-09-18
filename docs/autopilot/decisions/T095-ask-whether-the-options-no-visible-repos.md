# T095 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## frame gate

Reviewed: the artifact at commit c25851a, the diff against the base (the artifact and one index row
only), `taskrail checks T095 --stage frame` (`no checks` … `passed`), and the lane's two corrections
to T088, both checked by the orchestrator on the mainline: `grep -c "epic_prefix" DESIGN.md` returns
0, `DESIGN.md:971` does mention `id_digits` inside §7.3's account of what `import` refuses, and
`taskrail next --help` shows `--limit LIMIT` with no help text at all.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Does the list stay exactly these seven? | the same seven with two descriptions corrected · drop `id_digits` · add options | **the same seven, with both corrections, as recommended** | The corrections are the point of re-verifying: `id_digits` is documented once, in §7.3's import error, not "undocumented" as T088's prose said, and `--owner` is ten parser arguments with a `TASKRAIL_OWNER` equivalent rather than one flag. Dropping `id_digits` would lose a real question — its absence from §4 and its effect on the width of IDs `new` generates — and it is the cheapest of the seven to answer. Adding options was rightly refused: the list's whole value is that the human can trust every line. |
| 2 | The shape of the question at `decide` | a numbered questionnaire with an answer key and a default per line · one line per option · three grouped questions | **the questionnaire, as recommended** | The human answers seven questions in one sitting without reading the artifact, and a default per line makes a partial answer usable. Grouping was rightly refused: it forces one answer onto options whose evidence differs in strength, which is what T088's asymmetry between configuration and CLI evidence warns against. |
| 3 | Keep `--owner` on the list with route A as its default? | keep it · drop it as already settled | **keep it, with route A (document it) as the recommendation and the default** | It costs the human one word and closes the question in the record. The documentation line should name `$TASKRAIL_OWNER` as the ordinary way to set an owner, since that is the consumer path no grep for `--owner` can see. |

Instructions given with the answers: `investigate` only needs to pin down, per option, the exact
wording of route A (which document and section) and route B (what the proposed-removal task would
say). Never describe an option as having no consumer; the strongest claim is that none is visible in
this repository. Open no follow-up tasks before the human answers.

The two framing findings the lane surfaced are kept for the questionnaire: both configuration keys
are read by `taskrail import`, the one command this repository never ran because it was extracted
rather than imported, so the repository most likely to need them is exactly the class this one
cannot see; and `backlog.py:240` refuses a bad epic ID by quoting the prefix's *value* without ever
naming the key, which is a discoverability defect T098 owns.

## escalated to the human

`spike:decide` is in this repository's `[autopilot].escalate_gates`, so the questionnaire went to
the human, in the numbered form the lane designed. Answered on 2026-09-18.

| # | Question | Answer | Consequence |
|---|---|---|---|
| 1 | `[[backlog]].epic_prefix` | **A — document it** | No new task: T098 adds it to §4's example, and its prose sentence explains what the key is for. |
| 2 | `[[backlog]].id_digits` | **A — document it** | No new task: T098 adds it to §4's example with the clause that it also governs `taskrail new`. |
| 3 | `epic add --id` | **A — document it** | One line in §7's command table, which T098 already edits. |
| 4-5 | `epic add --file`, `epic split --file` | **A — document them** | One line in §7's command table, via T098. |
| 6 | `next --limit` | **A — document it** | §7's row via T098, **plus** a one-line chore giving the flag a `help=` string, which is code. |
| 7 | `--owner` | **A — document it** | A small chore adding one sentence to §6.2, naming `$TASKRAIL_OWNER` as the ordinary way to set an owner. |
| extra | Should the error that refuses a foreign epic ID name `epic_prefix` instead of only its value? | **yes, open a task** | A small chore on `backlog.py:240`. It fixes the cause of the key being undiscoverable rather than only documenting it. |

Answered by the human (the repository's maintainer), through the orchestrator. **No option is
retired**: every answer is route A, so nothing is proposed for removal and the surface is unchanged.

Three tasks to open, and no more: the `help=` string for `next --limit`, the §6.2 sentence for
`--owner`, and the error-message fix for `epic_prefix`. Questions 1-5 need none, because T098 covers
them.

## rebase at hand-off

`review T095 --json` reported `rebase.needed: true`. Rebased onto `origin/main` while the lane was
stopped at the `close` gate. Two conflicts, both known classes: `docs/autopilot/decisions/README.md`
(appended index rows, both kept) and `TODO.md` (rows united by ID, a closed cell winning, so T095's
`✅` and the rows T101-T103 it opened all survive beside what the mainline took meanwhile). After the
rebase: no conflict markers, `taskrail validate` reports 92 tasks and 0 errors.

## Conflict handling agreed for all lanes

Run 20260918-1, three lanes: T094, T095, T096.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T095 edits its own artifact and its own rows only; T094 the validator and its tests; T096 `DESIGN.md` §4 and §12.10 plus one comment in `config.py`** | This lane touches no code and no shared document, so it can only conflict on the backlog file and the artifact index. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1) and appended index rows (2)** | Resolved by the orchestrator at hand-off. A conflict in `DESIGN.md` or `config.py` would be outside them and escalates. |
| 3 | May a lane retire or rename an option? | allow · forbid | **forbidden in this run** | T087's verdict, now in `CLAUDE.md`, is prospective: what exists is reopened by a task that asks for it. A "not wanted" answer produces a task that *proposes* a removal, which the human approves separately. |
