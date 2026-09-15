# T061 — Separate the documents the orchestrator reads first from the paths that escalate

Kind: feature · Epic: E02 · Status: verified

Source: question 3 of T060's scope gate
([decision record](../autopilot/decisions/T060-remove-design-md-and-claude-md-from-the.md)), which
follows the autopilot trial ([T033](../spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md)).
No prior work: `show` reported no artifact, branch or commit for T061.

## Premise, checked on the current mainline

`[autopilot].governing` has two roles today. `escalation.py` matches its entries against each
lane's `touched` files and `status` raises `governing` (§12.6); and the `taskrail-autopilot` skill
tells the orchestrator, under *Before the first dispatch*, to "Read the governing documents: the
`[autopilot].governing` paths", as does `references/gate-review.md` ("Answer from the
`[autopilot].governing` documents"). DESIGN.md §4 and §12.9 comment the key "read first to answer
gates". T060 emptied `governing` in this repository so that edits to `CLAUDE.md` and
`DESIGN.md` stop escalating, and kept the reading list only in a config comment and a
`CLAUDE.md` *Backlog* bullet, which the skill does not read. The premise holds.

## Behaviour

- **A new key, `[autopilot].read_first`**: a list of repository-relative paths — files, directories
  or shell-style globs — that the orchestrator reads first to answer gates. It never escalates.
  `governing` keeps only its escalation role.
- **Fallback.** When `read_first` is absent, it takes the `governing` entries, so a repository
  configured before this change keeps its reading list. An explicit `read_first = []` means none.
- **`autopilot status`** reports the list at the top level of its JSON as `read_first`, and the
  entries that match nothing in the checkout as `read_first_missing`. The text form starts with
  `read first: …` when the list is not empty, and adds `read first missing: …` when an entry
  matches nothing. `status` already runs before the first dispatch, so the orchestrator gets the
  list without parsing TOML.
- **The skill** keeps its prose term: *the governing documents* are the `read_first` documents,
  and *a governing path* is a `governing` entry — the words condition 1 and condition 3 of
  *Escalate* already use. *Before the first dispatch* runs `status` first and reads the documents
  `read_first` lists, and tells the human about any `read_first_missing` entry;
  `references/gate-review.md` names `read_first` instead of `governing`.
- **This repository** sets `read_first = ["CLAUDE.md", "DESIGN.md"]`, keeps
  `governing = []`, and its `CLAUDE.md` *Backlog* bullet names the key (exact text in the gate
  questions).

## Acceptance criteria

1. `load_config` reads `read_first` as a tuple of strings; a value that is not a list of non-empty
   strings fails with `autopilot.read_first must be a list of non-empty strings`.
2. With `read_first` absent, `AutopilotConfig.read_first` equals the configured `governing` entries
   (empty when neither is set); with `read_first = []` it is empty even when `governing` is set.
3. `autopilot status --json` has a top-level `read_first` with the configured entries in order and
   `read_first_missing` with the entries that match no file or directory under the root (a glob
   counts as present when it matches anything); both are lists, also when there are no runs.
4. The text form of `autopilot status` starts with `read first: <entries>` when `read_first` is not
   empty, prints `read first missing: <entries>` when some are missing, prints neither line when
   the list is empty, and still says `no autopilot runs` when there are none.
5. `governing` escalation is unchanged: a `read_first` entry a lane touches raises nothing (a
   `status` test with a touched `read_first` path and empty `governing`).
6. The `taskrail-autopilot` skill source says, in *Before the first dispatch*, that the governing
   documents are the `read_first` entries from `autopilot status` and names `read_first_missing`;
   `references/gate-review.md` names `read_first`, not `[autopilot].governing`, for the documents
   to answer from; the copies `init` installs carry the same text. Asserted in
   `test_autopilot_skill.py`; this repository's installed copies are refreshed with
   `taskrail upgrade`.
7. All tests pass: `uv run pytest -q`; `taskrail validate` reports no
   errors.

## Tests per criterion

All new tests are in `tests/test_autopilot_read_first.py`, a file of its own so the
other lanes editing `test_autopilot.py`, `test_autopilot_notify.py` and `test_autopilot_skill.py`
do not collide with it. They were committed and observed failing (13 failed, 1 passed — the one
passing is criterion 5's guard, which holds before and after) before the implementation.

| # | Tests |
|---|---|
| 1 | `test_read_first_is_read_as_a_tuple`, `test_read_first_must_be_a_list_of_non_empty_strings` (3 cases) |
| 2 | `test_an_absent_read_first_takes_the_governing_entries` (4 cases); `test_autopilot.py::test_autopilot_configuration_reads_every_single_value_key` now expects the fallback |
| 3 | `test_status_reports_read_first_and_the_missing_entries`, `test_status_has_empty_read_first_lists_and_no_lines_without_entries`; `test_autopilot.py::test_status_without_runs_and_for_an_unknown_run` now expects the two keys |
| 4 | `test_status_text_starts_with_read_first_lines`, `test_status_has_empty_read_first_lists_and_no_lines_without_entries` |
| 5 | `test_a_touched_read_first_document_raises_no_escalation` |
| 6 | `test_the_skill_source_reads_the_governing_documents_from_read_first`, `test_the_installed_skill_copies_read_the_governing_documents_from_read_first`; this repository's copies refreshed by `taskrail upgrade` |
| 7 | `uv run pytest -q`: 854 passed; `taskrail validate`: 0 errors |

Two existing tests in `test_autopilot.py` pinned the old shape and were changed by one line each:
the every-key configuration test expects `read_first` to take the `governing` entry, and the
no-runs status test expects `read_first` and `read_first_missing` beside `fetched`.

## Verification in the real CLI

Run from the task worktree with `.taskrail/bin/taskrail --root <worktree> autopilot status --run
20260914-2`, against the live run of this repository (T059 and T061 lanes). No gap against the plan.

1. **This repository's configuration** (`read_first = ["CLAUDE.md", "DESIGN.md"]`):
   the text form started with `read first: CLAUDE.md, DESIGN.md` and no missing line;
   `--json` ended with `"read_first": ["CLAUDE.md", "DESIGN.md"]` and
   `"read_first_missing": []`. Both lanes touch `DESIGN.md` (T061 also `CLAUDE.md`)
   and both show `governing_touched: []`, `escalation: []`.
2. **A missing entry and a `./` glob**, set temporarily
   (`["CLAUDE.md", "./docs/spikes/*.md", "GONE.md", "DESIGN.md"]`): `read first:
   CLAUDE.md, ./docs/spikes/*.md, GONE.md, DESIGN.md` then `read first missing:
   GONE.md`.
3. **The fallback**, with the `read_first` line removed and `governing = ["docs/nowhere",
   "TODO.md"]`: `read first: docs/nowhere, TODO.md` then `read first missing: docs/nowhere`.

The configuration was restored with `git checkout -- .taskrail/config.toml`; `git status` was clean.

## Affected areas

- `src/taskrail/config.py`: the `read_first` field of `AutopilotConfig` and its
  reading and fallback in `_autopilot` (the tuple of list keys).
- `src/taskrail/autopilot/commands.py`: `cmd_status` adds `read_first` and
  `read_first_missing` to the report beside `fetched`, and `_status_text` prints the two lines.
  `status()` in `status.py` (T051's area) and `escalation.py` (T059's area) are not edited.
- `src/taskrail/skills/taskrail-autopilot/SKILL.md`: the two bullets of
  *Before the first dispatch* only. `references/gate-review.md`: the *Governing documents first*
  bullet of *Every gate* only. Installed copies under `.claude/skills/taskrail-autopilot/` and
  `.taskrail/installed.json` through `taskrail upgrade`.
- `DESIGN.md`: the `[autopilot]` sample in §4 and in §12.9 (one added line each,
  and the `governing` comment); the `autopilot status` row of the §12.1 command table (one added
  sentence on `read_first`); a *Read-first documents* bullet added before *Governing paths* in
  §12.6, and condition 3 there naming them.
- `.taskrail/config.toml`: the `[autopilot]` block's `read_first` line and comment.
- `CLAUDE.md`: the autopilot bullet of *Backlog*.
- Tests: the new `tests/test_autopilot_read_first.py`, and one line in each of two existing tests
  in `tests/test_autopilot.py` (planned: new tests in `test_autopilot.py` and
  `test_autopilot_skill.py`; moved to their own file at implement to keep clear of other lanes).
- `CHANGELOG.md` (one bullet), `docs/features/README.md` (one row).

## Out of scope

- Any change to how `governing` entries match or escalate (`escalation.py`, T059).
- The *Resume a run* section T055 adds to the skill: its "Read the governing documents" stays
  correct under the prose term above, so it needs no edit here or there.
- Validating `read_first` entries in `taskrail validate`, or failing `status` on a missing one.
- Putting `read_first` in `autopilot start` or `next` output, or in the lane brief: lanes do not
  answer gates.

## Open questions and risks

- **Term.** Keeping *governing documents* for the read-first list in prose, while `governing` names
  the escalating key, could confuse; the skill and DESIGN.md define both terms in one sentence each.
- **Fallback with globs.** A repository that relies on the fallback may have glob `governing`
  entries such as `src/**/policy-*.py`; they become read-first entries too, which is what the
  skill did before this change.
- **Overlap with T059**, which may add `[autopilot]` configuration of its own in `config.py` and
  DESIGN.md §12.6/§12.9: the edits are separate lines, a known class at worst.
