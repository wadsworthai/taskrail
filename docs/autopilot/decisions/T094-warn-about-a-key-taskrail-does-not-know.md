# T094 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

## plan gate

Reviewed: `docs/features/T094-warn-about-a-key-taskrail-does-not-know.md` at commit ca1d4ce, the
diff against the base (the artifact and one index row; no source, test or document touched, as
`plan` requires), and the lane's two measurements — that an unknown key, an unknown key under a
known table and an unknown table all leave `validate` at 0 errors and 0 warnings, and that a warning
alone already leaves it at exit 0 and already appears in the summary and in `--json`. The
orchestrator had reproduced the first independently before this task was dispatched.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Where does the check live? | `load_config`, warnings carried on `Config.warnings` · a `validate`-only function that re-parses · `load_config` returns `(Config, issues)` | **`load_config` with `Config.warnings`, as recommended** | The names taskrail defines are written down in `config.py` and nowhere else, so the check cannot drift from the parser. Re-parsing would put the key list in a second place; changing the return type is the most consistent with `load_kinds` but edits about thirty call sites for a two-point task, which the design principles in `CLAUDE.md` weigh against. |
| 2 | A "did you mean" suggestion? | yes, one `difflib.get_close_matches` call · no | **yes, with a test that proves it fires** | The task's own motivation is a typo, and the suggestion is what turns the warning into a fix. It is one line of stdlib with a caller today, not an option or an abstraction kept for later. The condition: a test must show it firing on a realistic typo; if the 0.8 cutoff does not fire on something like `clam_remote`, lower it or drop the suggestion rather than shipping one that never appears. |
| 3 | An unknown table: one warning, per key, or none? | one for the table, do not descend · one per key · none | **one for the table, as recommended** | A stray `[nonsens]` with ten keys should produce one line, not eleven. Warning for unknown tables also covers the case the orchestrator's own probe hit. |
| 4 | One issue code or two? | two: `config-unknown-key`, `config-unknown-table` · one | **two, as recommended** | It matches the codebase's habit of specific codes (`task-kind-unknown`, `column-alias`) and lets a `--json` consumer tell the cases apart. |
| 5 | Document it in `DESIGN.md`? | §4 paragraph and a clause in §7's `validate` row · `CHANGELOG.md` only | **yes, both, with a placement constraint** | This is behaviour a consumer cannot discover otherwise, and §4 is where the configuration contract lives. The constraint: put the §4 paragraph **after** the example config block, not inside it — T096 is editing line 194 inside that block in a parallel lane, and T098 is queued to touch §4 later. A conflict inside `DESIGN.md` is not a known conflict class and would escalate to the human instead of being resolved at hand-off. |

Instructions given with the answers: the ten acceptance criteria stand, each with its test observed
failing first; keep both drift guards as tests (`install.py`'s seeded config and §4's example config
must each produce zero warnings); `[checks]` and `[columns].aliases` never warn; and change no
existing key — every question about retiring one belongs to T095 and T096, running beside this lane.

## implement gate

Reviewed: the diff read by commit range in the lane's worktree — `config.py`'s declaration and
walker, the one-line merge in `project.py`, the ten new tests, `DESIGN.md` §4's paragraph placed
after the example block as required, and `CHANGELOG.md`'s entry; the red-first evidence, which names
each failing assertion rather than an import error; and `taskrail checks T094 --stage implement`
re-run by the orchestrator, which passed.

**The orchestrator broke the code on purpose**, as the gate checklist requires when a guard's
coverage is the thing in doubt: removing `"file"` from the `backlog` entry of `TABLE_KEYS` in the
lane's worktree made all ten tests of `tests/test_config_unknown_keys.py` fail, and the file was
restored with `git checkout --` leaving the worktree clean. The drift guard the whole design rests
on does fail when the declaration drifts from the parser.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Is the implementation what was approved? | accept · amend | **accepted** | It is the plan as approved: the check lives in `load_config`, warnings ride on `Config.warnings`, `load_project` merges them in one line, no call site and no exit code changed, and nothing was removed, renamed or defaulted. |
| 2 | Q2's condition — does the suggestion actually fire? | met · loosen the cutoff · drop the suggestion | **met, at the default cutoff** | `clam_remote` against `claim_remote` rates 0.96 against the 0.8 threshold, with a test asserting the message, and the live probe fired it twice more (`escalat_gates`, `[reviw]`). Nothing ships that never appears. |
| 3 | Q5's placement constraint | met · move it | **met** | The §4 paragraph is after the example block and nothing inside the block was touched; in `config.py` the nearest hunk is 34 lines from `HANDOFF_MODES`, so T096's comment merged clean — as the mainline now shows. |
| 4 | The two risks the lane raised | accept as recorded · act now | **accept as recorded** | The declaration can drift from the parser: criterion 6 guards it, and the orchestrator verified that guard by breaking it. Warnings surface only for a config that loads: that is the existing precedence between a `ConfigError` and a warning, and this task was right not to change it. |

Instructions given with the answers: run `verify` as planned — exercise the feature in a fresh
scratch repository rather than this one's config — and close.

## rebase after T096 merged

T096 was squash-merged into `main` as df64fe6. `review T094 --json` reported `rebase.needed: true`,
so the orchestrator rebased at hand-off, while the lane was stopped at the `close` gate:
`git rebase origin/main`.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | `docs/autopilot/decisions/README.md`: a row appended by each side | keep both · stop | **keep both, one entry per task** | Known class 2, appended index rows. The only conflict of the rebase. |
| 2 | `DESIGN.md`, which both tasks edited | resolve · escalate | **no conflict arose** | The placement constraint set at the `plan` gate did its job: T096 wrote inside §4's example block and in §12.10, T094 after the block and in §7's `validate` row, so git merged them without overlap. `§12.10 on batch` is still present on the rebased branch, and the one removed `DESIGN.md` line is T094's own rewrite of the `validate` row. |

After the rebase: six commits ahead of `origin/main`, `git diff --check` clean, `taskrail checks
T094` passed, `taskrail validate` reports 88 tasks and 0 errors — and this repository's own config
still produces no warning, which is the live drift check the feature depends on.

## Conflict handling agreed for all lanes

Run 20260918-1, three lanes: T094, T095, T096.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T094: `config.py`'s parsing, `project.py`, `tests/`, `DESIGN.md` §4 after the example block and §7's `validate` row, `CHANGELOG.md`. T096: `DESIGN.md` line 194 and §12.10, one comment above `config.py:48`. T095: its artifact only** | The two places lanes meet are `config.py` and `DESIGN.md` §4, and in both they work at opposite ends: T096 at the top of `config.py` and inside §4's example block, T094 in the parsing and in the prose after it. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), changelog bullets (2); anything inside `config.py` or `DESIGN.md` escalates** | The known classes are defined by content, not by path, and two lanes editing one source file is not one of them. |
| 3 | May a lane retire, rename or default an existing key? | allow · forbid | **forbidden in this run** | The human accepted this task as a *warning*. T087's verdict, now in `CLAUDE.md`, makes the principles prospective, so what exists is reopened only by a task that asks for it. |
