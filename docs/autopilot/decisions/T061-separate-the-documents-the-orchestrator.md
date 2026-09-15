# T061 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## escalated to the human

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Who decides changes to `DESIGN.md` and `CLAUDE.md` proposed by autopilot lanes | the human per text · the orchestrator · remove them from `governing` | **the orchestrator decides them and the human reviews them in the pull request; both files were removed from `governing` (T060)** | The human's instruction during run 20260914-1, made permanent by T060. |
| 2 | Continue the autopilot with the follow-up tasks | — | **run 20260914-2 with T059, T061, T062 and T063, each dispatched once its row reaches `main`** | The human's instruction. |

Answered by the human (repository owner), in the orchestrator session.

## plan gate

Reviewed: the plan in `docs/features/T061-separate-the-documents-the-orchestrator.md` (commit
`7b3e58c`), its seven acceptance criteria, and on `origin/main` (`502ea3b`) the two roles of
`[autopilot].governing`: `escalation.py` matches it against touched files, and the skill's *Before the
first dispatch* and `gate-review.md` read it as the documents to answer from. With this repository's
list now empty (T060), the skill points the orchestrator at nothing. The premise holds. No code
changed, so no checks were re-run.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the plan with the key `read_first` | `read_first` · `guidance` · `documents` · `reference_documents` | **as recommended (`read_first`)** | Matches the wording the configuration and design already use. |
| 2 | Absent `read_first` | falls back to `governing` · means empty | **as recommended (fall back)** | Existing repositories keep their reading list without a behaviour change. |
| 3 | Report `read_first_missing` | yes · no | **as recommended (yes)** | A renamed document must not drop out silently. |
| 4 | Wording of the two lists | "governing documents" = `read_first`, "governing path" = `governing` · rename everywhere | **as recommended (keep the wording)** | Matches escalation conditions 1 and 3 and leaves T055's *Resume a run* correct without edits on either branch. |
| 5 | This repository's key and the `CLAUDE.md` bullet | set it and update the bullet · leave the bullet · remove the bullet | **as recommended (set it, bullet as proposed)** | Agents outside the autopilot read `CLAUDE.md`, and the bullet carries the policy; the configuration is the machine-readable list. Decided under the human's delegation of `CLAUDE.md` decisions. |
| 6 | `.taskrail/config.toml` text | as proposed · other | **as proposed** | States both roles next to the keys. |
| 7 | DESIGN.md §4 and §12.9 samples, §12.1 `autopilot status` sentence, §12.6 condition 3 and new *Read-first documents* bullet | approve as written · other | **approve as written** | Decided under the human's delegation. The §12.1 row is also edited by T051, T053, T054 (unmerged) and T059 (running); each phrase is kept at hand-off. |
| 8 | Skill *Before the first dispatch* bullets and gate-review *Governing documents first* bullet | approve as written · other | **approve as written** | Sections no other lane edits. |

## Conflict handling agreed for all lanes

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files | per-plan areas · free | **T061 owns `AutopilotConfig.read_first` and its reading in `config.py` `_autopilot`, `cmd_status` and `_status_text` in `commands.py` for the new fields, the skill's *Before the first dispatch* bullets, gate-review's *Governing documents first* bullet, its tests in `tests/test_autopilot.py` and `tests/test_autopilot_skill.py`, the approved DESIGN text, the `[autopilot]` block of `.taskrail/config.toml` and the last *Backlog* bullet of `CLAUDE.md`. T059 owns `escalation.py`, `approve.py`, `_escalation_text` and `governing_approved` in `status.py`; T051 (unmerged) `status()` and the overlaps lines of `_status_text` plus the no-runs expected dict in `test_autopilot.py`; T048 (unmerged) the run header line of `_status_text` and `cmd_status`'s closed-run filter.** | `cmd_status` and `_status_text` are shared with T048 and T051: add the new fields in separate lines so the hand-off keeps every change. |
| 2 | Installed skill copies, `installed.json`, CHANGELOG, TODO.md, index READMEs, same-line DESIGN rows | resolve at hand-off · serialize | **resolve at hand-off, keeping every phrase** | Known conflict classes 1–3; row edits apply phrase by phrase. |

## implement gate

Reviewed: commits `0d0cb76` (tests, 13 of 14 shown failing; the one passing guards that `governing`
escalation is unchanged) and `2bb9e14` (range `e3ba0cb..2bb9e14`): `AutopilotConfig.read_first` with
its fallback in `config.py`, `read_first` and `read_first_missing` added in `cmd_status` on separate
lines with `_matches_anything` and `_read_first_text`, the approved skill and gate-review text with
installed copies, the approved DESIGN.md, `.taskrail/config.toml` and `CLAUDE.md` text, one CHANGELOG
bullet, and one-line updates to two existing tests. Re-ran `uv run pytest
-q` in the lane's worktree: 854 passed.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Criteria 1–7 map to tests; the diff avoids T059's and T051's functions. |
| 2 | Tests in their own file | keep · move to planned files | **as recommended (keep)** | Fewer conflicts with four other branches editing those test files. |
| 3 | One-line edits to two existing tests | accept · rewrite them | **as recommended (accept)** | A conflict on the no-runs expected dict keeps every key at hand-off. |
| 4 | `Path.glob` for `read_first_missing` | accept · reuse `escalation.matches` | **as recommended (accept)** | Only affects a report, never escalation, and stays out of T059's module. |

## close gate

Reviewed: `1fa92e1` (verification with the real CLI on run `20260914-2`: this repository's config
lists both documents with none missing; a temporary missing entry and a `./` glob were reported
correctly; with the key removed the `governing` entries were used; the config was restored) and
`0480141` (`taskrail done T061` on its own). No code changed after the checks re-run at the implement
gate (854 passed). `taskrail validate`: 0 errors. No upstream is configured. `review --json`:
`rebase.needed` true onto `origin/main` (T054 and T055 merged).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the close and queue the branch | queue · changes | **queue, as `feat(taskrail)`** | Every close check holds; the verification covers the list, the missing report and the fallback. |

## rebase after the merged tasks

T054, T055, T052, T053, T056, T048, T051 and T047 (`4313c71`) were merged into `main` since the
branch started. The branch was rebased onto `origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Conflict in `docs/features/README.md`, `docs/autopilot/decisions/README.md` and `CHANGELOG.md` | keep both · stop | **keep both** | Class 2. |
| 2 | Conflict in `TODO.md` | unite rows by ID · stop | **unite by ID** | Class 1. |
| 3 | Conflict in `.taskrail/installed.json` | manifest valid, then `upgrade --force` · stop | **kept `main`'s digests, then `taskrail upgrade --force`, committed** | Class 3. |
| 4 | Conflict in `DESIGN.md`, §12.1 `autopilot status` row | stop · keep every task's phrase | **`main`'s row with T061's `read_first` sentence inserted after "to a flagged lane."** | The row carries T049, T051, T053 and T054's phrases; T061 only adds a sentence. Decided under the human's delegation. |
| 5 | Conflict in `tests/test_autopilot.py`, the no-runs expected dict | stop · keep every key | **every key: `known_overlaps` (T051) and `read_first`, `read_first_missing` (T061)** | Anticipated at T061's implement gate: both tasks add top-level keys to the same report. |

After the rebase: no conflict markers, `taskrail checks T061 --stage implement`: `test` 907 passed,
`lint` not configured; `taskrail validate` 0 errors.
