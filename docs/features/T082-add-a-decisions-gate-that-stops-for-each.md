# T082 — Add a decisions gate that stops for each decision instead of each stage

Kind: feature · Epic: E07 · Status: implemented

The contract is DESIGN.md §13.4, with the `gate` bullet of §13.1, the kind `gate` bullet of §13.6
and the T082 row of §13.8, decided at T079's scope gate
([artifact](../chores/T079-write-the-current-branch-workflow-into-d.md), decision 9 and 10;
[decision record](../autopilot/decisions/T079-write-the-current-branch-workflow-into-d.md)).

## Behaviour

A kind descriptor — core, repository-local or override — may set a stage's `gate` to
`"decisions"`, next to `always`, `conditional` and `none`:

```toml
[[stage]]
name = "scope"
gate = "decisions"   # stop as soon as a decision appears; never to approve the stage
commit = true
```

- The descriptor loads without issues, and `validate` accepts it.
- `show --json` (`kind_descriptor.stages[].gate`) and `kind list --json` (`stages[].gate`) report
  `"decisions"` as they report any gate; the text form of `show` prints
  `· scope (gate: decisions, commit)`.
- A `gate` outside the four values stays a `kind-invalid` error (exit 1 from `validate`), and its
  message names all four: ``stage `a`: gate must be one of always, conditional, decisions, none``.
- The autopilot needs nothing new and refuses nothing: a lane stopped for a decision in such a stage
  runs `autopilot lane <ID> --run R --state gate --gate <stage>`, which records the stage as for any
  gate, and `autopilot status` reports `gate` and flags `escalate_gate` for a `<kind>:<stage>` listed
  in `escalate_gates` whatever the stage's gate value — `spike:decide` still escalates when an
  override makes `decide` a `"decisions"` gate.

What the executor does at a `"decisions"` gate (stop mid-stage for a decision, never at the stage's
end; carry reports to the next stop or the close) is the skills' part, T084. This task writes it into
DESIGN.md's kinds section, where the CLI's contract for gate values lives.

### What the code already does

Reading the source before planning:

- `kinds.py` holds the only list of gate values, `GATES = ("always", "conditional", "none")`, used
  once, by the stage loop of `_parse` to validate `gate`. Core, local and override descriptors all
  go through `_parse`, so one change covers every layer.
- `show` and `kind list` print `Stage.gate` verbatim (`Stage.to_dict`, `cmd_show`'s text line), so
  they report a new value with no change.
- The autopilot never reads a stage's gate value. `autopilot lane --gate` (`_gate_problem` in
  `autopilot/commands.py`) checks only that the name is a stage of the task's kind or `close`;
  `escalation.flags` compares `<kind>:<stage>` with `escalate_gates`; `config.py` checks only the
  `kind:stage` shape. No autopilot command inspects gate values, so there is nothing to refuse or
  allow in code.

The change is therefore one constant in `kinds.py`, plus tests that pin the behaviour end to end and
the documentation.

## Acceptance criteria

1. A repository-local kind whose stage has `gate = "decisions"` loads with no issues, and its
   `Stage.gate` is `"decisions"`.
2. An override (`.taskrail/overrides/<kind>/kind.toml`) of a core kind with a `"decisions"` stage
   loads with no issues, `source` `override`, and `validate` exits 0.
3. A stage `gate` outside `always`, `conditional`, `decisions` and `none` is a `kind-invalid` error
   whose message is ``stage `<name>`: gate must be one of always, conditional, decisions, none``,
   and `validate` exits 1.
4. `show <ID> --json` reports `"gate": "decisions"` for that stage in `kind_descriptor.stages`, and
   text `show` prints `(gate: decisions` on its stage line.
5. `kind list --json` reports `"gate": "decisions"` for that stage.
6. In an autopilot run, `autopilot lane <ID> --run R --state gate --gate <stage>` succeeds for a
   stage whose gate is `"decisions"`, and `autopilot status --json` reports that stage in `gate`.
7. With `escalate_gates = ["spike:decide"]` and an override making spike's `decide` stage a
   `"decisions"` gate, a lane recorded at `--gate decide` has `escalate_gate` `spike:decide` and
   `escalation` `["escalate-gate"]`.
8. `autopilot start` and `autopilot next` accept a run whose kinds have `"decisions"` gates (no
   refusal, exit 0).

## Affected areas

- `src/taskrail/kinds.py` — `GATES` gains `"decisions"` between `conditional` and `none`, which also
  changes the stage `gate` validation message. One hunk; the stage-parsing loop is not restructured
  (T081 edits it for the effective stage `commit`).
- `tests/test_decisions_gate.py` — new file for criteria 1–8, so the tests do not share hunks with
  T080's and T081's test changes. `tests/test_kinds.py::test_invalid_descriptor` keeps asserting
  `gate must be one of`, which still holds; it is not edited.
- `DESIGN.md`, moving T082's part of §13 into the body as the §13 status line says:
  - §2 *Concepts*, the `Gate` row: name the four values.
  - §5.1: the *Planned (§13.1)* note loses its gate half, which becomes current text about
    `"decisions"` pointing to the new §5.6; the `commit` half stays planned for T081.
  - §5.4: a `judgement` stage whose gate is `"decisions"` may be skipped without asking.
  - new §5.6 *Gates*: the four values and what each stops for, what a decision is, and that there
    is no repository-wide gate key (overrides set gates) — the text of §13.4 and the `gate` bullet
    of §13.1, as current behaviour.
  - §12.6 *Escalated gates* bullet: a `"decisions"` gate is recorded and flagged like any gate, and
    with no stage-end stops the orchestrator's first full review is the close review.
  - §13.1 `gate` bullet, §13.4, the kind `gate` bullet of §13.6 and the T082 row of §13.8: marked
    *implemented (T082)* with a pointer to §5.6 and §12.6 (see open question 1). §13's introduction,
    its summary table and the other lanes' subsections are not touched.
- `CHANGELOG.md` — one bullet under *Unreleased*.
- `docs/features/README.md` — the index row for this artifact.

## Out of scope

- The skills (`taskrail`, the executor skills, the autopilot skill's gate review) and the README:
  T084 teaches them the decisions gate. No test asserts the list of gate values in skill text:
  `tests/test_autopilot_skill.py` checks gate-review headings by stage name, not gate values.
- Changing any core kind's gates: the core kinds keep `always` and `conditional`.
- A repository-wide gate key, and any refusal of `"decisions"` gates in the autopilot (§13.4, §13.6
  say neither exists).
- `[git].task_branch`, `[git].commit`, the kind's `commit` policy, `show`'s `close` and the autopilot
  start/extend/next refusals (T080, T081).
- A `kind show` command (none exists).

## Open questions and risks

1. **How §13.4 is marked once moved.** *Recommended:* replace §13.4's body with a one-line status —
   *Implemented (T082): now §5.6 (gate values, decisions, judgement skips) and §12.6 (the
   autopilot).* — so the text lives in one place, and mark the §13.1 `gate` bullet, the §13.6 kind
   `gate` bullet and the §13.8 T082 row *implemented (T082)* in place without removing them, since
   they share their lists with other lanes' lines. *Alternative:* keep §13.4's full text and add
   only an *Implemented (T082)* marker, duplicating §5.6.
2. **Where the gate semantics go.** *Recommended:* a new §5.6 *Gates* appended after §5.5, in its
   own hunk, rather than growing §5.1, whose *Planned* note T081 also edits. *Alternative:* a
   paragraph under §5.1's example.
3. **Risk: merge conflicts with T081** in `kinds.py` (T081 edits the stage loop and `Kind`) and in
   DESIGN.md §5.1's *Planned* note and §13.1/§13.6/§13.8 lines, which both lanes mark. The
   `kinds.py` change is a single line at the top of the module; the DESIGN.md edits are separate
   lines or bullets, so a rebase should resolve them by keeping both sides.

## Plan gate

Approved as written; decisions in the
[decision record](../autopilot/decisions/T082-add-a-decisions-gate-that-stops-for-each.md): §13.4's
body becomes a one-line pointer and the other §13 lines are marked *implemented (T082)* in place;
the gate semantics go into a new §5.6 *Gates*.

## Implementation

- `src/taskrail/kinds.py`: `GATES` is `("always", "conditional", "decisions", "none")`.
- `DESIGN.md`: §2 `Gate` row; §5.1 note split (the gate half is current, the `commit` half stays
  planned for T081); §5.4 judgement skips; new §5.6 *Gates*; §12.6 *Escalated gates*; §13.1 `gate`
  bullet, §13.4, §13.6 kind-gate bullet and §13.8 T082 row marked.
- `CHANGELOG.md`: one bullet under *Unreleased*.

The new tests were run before the `GATES` change and all eight failed (a `decisions` gate was
`kind-invalid`, so descriptors did not load, `validate` exited 1 and every command refusing an
invalid backlog refused); after it, all eight pass.

## Acceptance criteria and tests

All in `tests/test_decisions_gate.py`:

| # | Test |
|---|---|
| 1 | `test_local_kind_loads_a_decisions_gate` |
| 2 | `test_override_of_a_core_kind_loads_a_decisions_gate` |
| 3 | `test_an_unknown_gate_names_the_four_values` |
| 4 | `test_show_reports_a_decisions_gate` |
| 5 | `test_kind_list_reports_a_decisions_gate` |
| 6 | `test_lane_records_a_decisions_gate_and_status_reports_it` |
| 7 | `test_escalate_gates_flags_a_decisions_gate` |
| 8 | `test_start_and_next_accept_kinds_with_decisions_gates` |
