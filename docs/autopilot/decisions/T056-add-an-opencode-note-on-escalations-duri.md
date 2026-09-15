# T056 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to the governing documents (`DESIGN.md`, `CLAUDE.md`) proposed by this run's lanes | the human per text · the orchestrator for this run · remove them from `governing` | **the orchestrator decides every `DESIGN.md` and `CLAUDE.md` change in this run; the human reviews them in the pull request. Also open a separate task removing both files from `[autopilot].governing` (T060)** | The human delegated the decisions to keep the lanes moving, and chose to make the change permanent. |

Answered by the human (repository owner), in the orchestrator session.

## scope gate

Reviewed: the scope in `docs/chores/T056-add-an-opencode-note-on-escalations-duri.md` (commit
`c7cf7f0`), the `taskrail-autopilot` section of `src/taskrail/integrations/opencode.md`
on `origin/main` (`b184707`), which says "ask the human yourself in plain text and wait for the
reply" and nothing about ending the turn, handles or `silent` between batches, and the portable
skill's "Other lanes keep going meanwhile". Nothing else is edited yet.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | DESIGN.md §8 `opencode` row and §12.3 sentence (governing) | approve as written · no change | **approve as written** | Decided by the orchestrator under the human's delegation; it records why the OpenCode orchestrator ends its turn (F3). |
| 2 | Other lanes during an escalation on OpenCode | wait for the next batch, resume first with background subagents · resume first then ask · ask with `question` | **as recommended** | Resuming first is what failed in the trial; the `question` tool is not the core note's contract. The note is an agent-specific narrowing of "other lanes keep going", which still holds with background subagents. |
| 3 | CHANGELOG entry | add · skip | **as recommended (add)** | Consumers of the OpenCode integration see a behaviour change in the installed note. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T056 owns the `taskrail-autopilot` section of `integrations/opencode.md`, one OpenCode test in `tests/test_autopilot_skill.py`, the DESIGN §8 `opencode` row and one sentence in §12.3. T049, T050 and T053 (closed) changed the DESIGN §12.1 `autopilot status` and `autopilot lane` rows, §12.6, `status.py` `_handoff`, `escalation.py`, `commands.py` and the portable skill's *Escalate* and *Close and hand off* sections. T052 (later) edits the Claude Code note and T055 the portable skill text.** | Built from the gates reached so far. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs | resolve at hand-off by the known classes · serialize | **resolve at hand-off** | Known conflict classes 1–3. |

## implement gate

Reviewed: commit `07fd103` (range `5e8e12b..07fd103`): the `taskrail-autopilot` section of
`integrations/opencode.md` (one new bullet, the escalation sentence replaced), the §8 row and §12.3
sentence exactly as approved, one CHANGELOG bullet, and a test parametrized over an OpenCode-only and
a Claude-plus-OpenCode install, shown failing on the old note. Re-ran
`uv run pytest -q` in the lane's worktree: 830 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve, with the CHANGELOG bullet moved to the end of *Unreleased*** | The *Unreleased* bullets run in delivery order (T024 … T039, then this run's tasks); inserting after T024 breaks that order. |

The lane used `git stash push`/`pop` to check the test against the old note. The stash stack is
shared by every worktree of this clone; use a temporary commit or a scratch copy instead.

## close gate

Reviewed: `a57b91a` (CHANGELOG bullet moved to the end of *Unreleased*) and `0f38eea`
(`taskrail done T056` on its own, changing only T056's row). No code or test changed after the
checks re-run at the implement gate (830 passed). `taskrail validate`: 0 errors. No upstream is
configured. `review --json`: `rebase.needed` true onto `origin/main` (T050 merged).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch | queue · changes | **queue, as `docs(taskrail)`** | The change is skill-note text, design text and a test; no CLI behaviour changes. Hand-off after T049, T060 and T053. |

## rebase after the merged tasks

T050, T049, T060, T054, T055, T052 and T053 (`23d2e20`) were merged into `main` since the branch
started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/chores/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. The CHANGELOG bullet T056 moved to the end of *Unreleased* is there once. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |
| 3 | Conflict in `DESIGN.md` §8 integrations table | stop · keep each task's row | **`main`'s `claude` row (T052) with T056's `opencode` row** | Each task changed a different row of the same table. Decided under the human's delegation of DESIGN.md decisions. |

After the rebase: `taskrail checks T056 --stage implement`: `test` 872 passed, `lint` not configured;
`taskrail validate` 0 errors.
