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

## Conflict handling agreed for all lanes

Run 20260918-1, three lanes: T094, T095, T096.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Which lane edits which files? | split by area · shared | **T094: `config.py`'s parsing, `project.py`, `tests/`, `DESIGN.md` §4 after the example block and §7's `validate` row, `CHANGELOG.md`. T096: `DESIGN.md` line 194 and §12.10, one comment above `config.py:48`. T095: its artifact only** | The two places lanes meet are `config.py` and `DESIGN.md` §4, and in both they work at opposite ends: T096 at the top of `config.py` and inside §4's example block, T094 in the parsing and in the prose after it. |
| 2 | How are the expected conflicts resolved? | escalate · known classes | **known classes: backlog rows (1), appended index rows (2), changelog bullets (2); anything inside `config.py` or `DESIGN.md` escalates** | The known classes are defined by content, not by path, and two lanes editing one source file is not one of them. |
| 3 | May a lane retire, rename or default an existing key? | allow · forbid | **forbidden in this run** | The human accepted this task as a *warning*. T087's verdict, now in `CLAUDE.md`, makes the principles prospective, so what exists is reopened only by a task that asks for it. |
