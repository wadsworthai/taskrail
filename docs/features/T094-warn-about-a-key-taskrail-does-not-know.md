# T094 — Warn about a key taskrail does not know in `.taskrail/config.toml`

Kind: feature · Epic: E08 · Status: verified

Contract: DESIGN.md §4 (the configuration surface) and §7's `validate` row. Evidence:
[T088](../spikes/T088-measure-the-cli-and-configuration-surfac.md) **E2** and its cost table **E9**.
Prior work: none (`show` lists no artifact, branch or commit naming the task).

## Premise, checked on this branch

On `0fd8dcb` (`origin/main`), against a copy of this repository's own backlog and config with two
unknown keys and one unknown table added:

```
$ sed -e 's/^version = "local:."/nonsense_top_key = "x"\nversion = "local:."/' \
      -e 's/^claim_remote = ""/claim_remote = ""\nnonsense_git_key = true/' \
      .taskrail/config.toml > $D/.taskrail/config.toml      # + [nonsense_table] what = 1
$ uv run taskrail --root $D validate
history: not checked (not a git repository)
88 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)
exit=0
```

The premise holds: three names taskrail does not define are ignored in silence.

A second probe fixes what "warn, never error" has to mean for the exit code — a warning alone
already leaves `validate` green, so nothing about exit codes needs to change:

```
$ # the same copy, with T094's Depends On cell set to "T088, T088"
$ uv run taskrail --root $D validate
TODO.md:136: warning: task `T094` lists a dependency more than once [depends-repeated]
history: not checked (not a git repository)
88 task(s) in 1 backlog(s): 0 error(s), 1 warning(s)
exit=0
```

## Behaviour

`taskrail validate` reports a name in `.taskrail/config.toml` that taskrail does not define as a
**warning**, naming the key and the table it sits in. It is never an error: `validate` keeps
exiting 0 when only warnings are present, and every other command goes on working, because a
repository pinned to an older CLI and one on a newer CLI must both keep running — a key a future
version adds must not break the version that does not know it yet.

**Where it is computed.** In `load_config` (`src/taskrail/config.py`), beside the `[autopilot]`,
`[git]` and `[columns]` checks that are already there: that is where the names taskrail defines are
written down, so the check cannot drift away from the parser that reads them. `load_config` raises
`ConfigError` for a *problem* and must keep doing so for problems only, so the warnings are carried
out on the `Config` it returns, in a new frozen field `warnings: tuple[Issue, ...] = ()`.
`load_project` puts them at the front of the issue list it already returns, which is what
`cmd_validate` prints, counts and serialises. No call site of `load_config` changes (there are
about thirty), `cmd_validate` does not change, and no command other than `validate` reports issues,
so none of them gains output.

**What warns.**

| In the file | Warns | Message |
|---|---|---|
| a key under a known table — `[git].nonsens` | yes | ``unknown key `nonsens` in [git]; taskrail ignores it`` |
| a key at the top level — `nonsens = 1` | yes | ``unknown top-level key `nonsens`; taskrail ignores it`` |
| an unknown top-level table — `[nonsens]` | yes, **once** | ``unknown table [nonsens]; taskrail ignores it`` |
| a key in a repeatable table — `[[backlog]]`, `[[autopilot.group]]`, `[[autopilot.resource]]` | yes | ``unknown key `mainlien` in [[backlog]] `main`; taskrail ignores it`` |
| a close miss of a name that exists | yes, with the suggestion | ``unknown key `mainlien` in [[backlog]] `main`; did you mean `mainline`? taskrail ignores it`` |
| anything under `[checks]` | **never** — free-form by design (§4) | — |
| anything under `[columns].aliases` | **never** here — its keys are core column names, already checked with an error (§3.2) | — |
| a table whose *shape* is already wrong (`backlog = "x"`, `[autopilot]` not a table) | no | the existing error stands; nothing descends into it |

The severity is `warning`, the code is `config-unknown-key` for a key and `config-unknown-table`
for a table, and the issue's `file` is `.taskrail/config.toml` with no line — `tomllib` does not
report line numbers, and the file plus the table locate the name well enough. So `validate` prints

```
.taskrail/config.toml: warning: unknown key `nonsens` in [git]; taskrail ignores it [config-unknown-key]
```

through `Issue.format()`, which is the shape every other issue already has, and
`validate --json` lists it in `issues` with `severity`, `code`, `message`, `file` and `line: null`,
leaving `valid` true and the exit code 0.

**The names taskrail defines** are declared once, as data, next to the parser: the nine top-level
names (`version`, `backlog`, `columns`, `points`, `git`, `review`, `kinds`, `checks`, `autopilot`),
the keys of each of them, and the keys of the three repeatable tables. Two tests guard that
declaration against drifting from the parser: the config `taskrail init` seeds, and the example
config in DESIGN.md §4, must each produce **zero** unknown-key warnings.

## Acceptance criteria

Each is testable, and each gets at least one test observed failing before the code exists.

1. An unknown key under a known table warns once, with severity `warning`, code
   `config-unknown-key`, `file` `.taskrail/config.toml`, and a message naming both the key and the
   table (`[git]`).
2. An unknown key at the top level warns once, naming the key and saying it is top-level.
3. An unknown top-level table warns **once**, with code `config-unknown-table`, naming the table —
   and not once per key inside it.
4. An unknown key inside `[[backlog]]`, `[[autopilot.group]]` and `[[autopilot.resource]]` warns,
   naming the key and the entry it sits in by its `name`.
5. `[checks]` never warns, whatever names it holds; neither does `[columns].aliases`.
6. Nothing warns for a configuration taskrail defines: the `taskrail init` seed and the DESIGN.md
   §4 example config each load with no unknown-key or unknown-table warning.
7. It is never an error: with unknown keys present `load_config` does not raise, `validate` prints
   the warnings, counts them in its summary line and exits **0**, and `list`/`show` keep working.
8. `validate --json` lists each warning in `issues` with its severity, code, message and file, and
   keeps `"valid": true`.
9. A near miss of a name that exists carries the suggestion: `[git].clam_remote` names
   `claim_remote` in its message.
10. A repository whose config holds only names taskrail defines gains no new output: the existing
    suite's clean-config cases still report no issues.

## Affected areas

| File | Change |
|---|---|
| `src/taskrail/config.py` | the declaration of the names taskrail defines; the unknown-name walk; `Config.warnings` |
| `src/taskrail/project.py` | put `config.warnings` at the front of the issues `load_project` returns |
| `tests/test_config_unknown_keys.py` | new: one test per acceptance criterion |
| `DESIGN.md` | §4 — a paragraph after the example, and §7's `validate` row |
| `CHANGELOG.md` | one entry under `## Unreleased` |
| `docs/features/` | this artifact and its index row |
| `TODO.md` | this task's row, through the CLI |

## Out of scope

- **Removing, renaming or defaulting any key.** Nothing existing is touched. Every question about
  retiring an option belongs to T095 and T096, which run beside this task.
- **Erroring on an unknown key**, and any `--strict` flag that would. The exit code stays 0.
- **A line number in the warning.** `tomllib` does not give one; finding it by scanning the raw
  text is a separate, larger change.
- **Deprecation warnings for keys that still work.** There is no list of retired names yet; when a
  key is withdrawn, this warning is what makes it audible.
- **Unknown keys in kind descriptors** (`types/<kind>/kind.toml`, §5.1) — a different surface, and
  one whose errors already exist.
- **Warning at `init` or `upgrade` time**, or in any command other than `validate`.

## Open questions and risks

- **Drift.** A declaration of known names sitting beside the parser can fall behind it. Criterion 6
  is the guard: a key documented in §4 or seeded by `init` that is not declared fails the suite.
  The residual risk is a key that is neither seeded nor documented — `epic_prefix` is exactly that
  case today (T088 E6) — so the declaration is written from the parser, not from §4.
- **Noise for a repository on a newer config.** A repository that pins an older CLI but keeps a
  config written for a newer one will now see warnings at `validate`. That is the intended signal,
  it is a warning rather than an error for exactly that reason, and T088 E2 shows the alternative
  is silence.

## How it was built

The plan was approved on 2026-09-18 with all five decisions as recommended, one condition and one
placement constraint; both are met and recorded in
[`docs/autopilot/decisions/T094-warn-about-a-key-taskrail-does-not-know.md`](../autopilot/decisions/T094-warn-about-a-key-taskrail-does-not-know.md).

- **Q2's condition — the suggestion must be shown firing.**
  `test_a_near_miss_suggests_the_key_it_missed` writes `clam_remote = ""` under `[git]` and asserts
  the message carries ``did you mean `claim_remote`?``. `difflib.get_close_matches` at cutoff 0.8
  rates that pair 0.96, so the default cutoff stands and nothing had to be loosened. The suggestion
  is one line of the standard library with a caller today, inside the message the task asks for —
  not an option and not an abstraction kept for later.
- **Q5's placement constraint.** The §4 paragraph sits **after** the example config block, at the
  end of §4 below the `[git].commit` paragraph; nothing inside the block is touched, so T096's edit
  at line 194 does not meet it. The same holds in `config.py`: the diff's hunks are at lines 2-14,
  111-121 and 303-308 of the old file, while `HANDOFF_MODES` is at line 48, 34 lines from the
  nearest hunk.

**The shape of the code.** `TABLE_KEYS` in `src/taskrail/config.py` declares every name §4 defines,
by the table it sits in, with `None` for `[checks]` — the one free-form table. `unknown_names(data)`
walks a parsed config against it and returns `Issue`s; `load_config` calls it once and carries the
result on `Config.warnings`, and `load_project` puts those at the front of the issues it already
returns. `cmd_validate` is unchanged: it counts, prints and serialises them like any other issue,
and its exit code is computed from errors alone, so warnings leave it 0. No call site of
`load_config` changed.

## Acceptance criteria, and the tests that cover them

All in `tests/test_config_unknown_keys.py`. Run against the code stubbed out — `unknown_names`
returning `[]` and an empty `Config.warnings` — 7 of the 10 failed, each on its own assertion, and
all 10 pass against the implementation. The three that could not be red are the negative ones
(5, 6, 10): they assert that nothing warns, which a stub satisfies by doing nothing. They are
regression guards, and criterion 6 is the guard that keeps this warning from becoming noise.

| # | Test | Observed failing first |
|---|---|---|
| 1 | `test_an_unknown_key_in_a_known_table_warns_naming_the_key_and_the_table` | yes |
| 2 | `test_an_unknown_top_level_key_warns` | yes |
| 3 | `test_an_unknown_table_warns_once_and_is_not_descended_into` | yes |
| 4 | `test_an_unknown_key_in_a_repeatable_table_names_its_entry` | yes |
| 5 | `test_the_free_form_tables_never_warn` | no — a negative assertion |
| 6 | `test_nothing_taskrail_defines_warns` | no — a negative assertion |
| 7 | `test_an_unknown_key_is_never_an_error` | yes |
| 8 | `test_validate_json_reports_the_warning_and_stays_valid` | yes |
| 9 | `test_a_near_miss_suggests_the_key_it_missed` | yes |
| 10 | `test_a_config_taskrail_defines_adds_no_issue` | no — a negative assertion |

Criterion 6 holds both drift guards: the config `taskrail init` seeds (`install.default_config`)
loads with no unknown-name warning, and the example config of DESIGN.md §4, parsed out of the file
itself, produces none either. The §4 guard calls `unknown_names` on the parsed block rather than
loading it as a repository, because that example is a two-backlog illustration that would not load
as a whole; what it guards is the declaration, which is exactly what can drift.

## Deviations from the plan

None in behaviour. Two details the plan left open were settled while building:

- the suggestion for an unknown **table** is bracketed (``did you mean [review]?``), and an unknown
  **top-level key** is matched against the table names as well as `version`, since that is where a
  misspelling at the top level most likely belongs;
- `AUTOPILOT_ENTRY_KEYS` declares the keys of `[[autopilot.group]]` and `[[autopilot.resource]]`
  separately from `TABLE_KEYS`, because they are nested one level deeper than the other repeatable
  table, `[[backlog]]`.

## Verified in the real CLI

In a fresh scratch repository outside this one — `git init`, then `taskrail init` — rather than
against this repository's own config, so the seeded config is exercised as a consumer gets it.

**A repository `init` seeds warns about nothing**, the first thing to check:

```
$ uv run taskrail --root $S init
created   .taskrail/config.toml …
$ uv run taskrail --root $S validate
history: not checked (no commits)
0 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)      exit=0
```

Then one epic, one task, and three realistic mistakes in that config: `worktree_dr` for
`worktree_dir` under `[git]`, `handof` for `handoff` under an `[autopilot]` table added by hand, and
a whole `[telemetry]` table with two keys, standing in for a table a newer version might add.

```
$ uv run taskrail --root $S validate
.taskrail/config.toml: warning: unknown key `worktree_dr` in [git]; did you mean `worktree_dir`? taskrail ignores it [config-unknown-key]
.taskrail/config.toml: warning: unknown key `handof` in [autopilot]; did you mean `handoff`? taskrail ignores it [config-unknown-key]
.taskrail/config.toml: warning: unknown table [telemetry]; taskrail ignores it [config-unknown-table]
history: not checked (no commits)
1 task(s) in 1 backlog(s): 0 error(s), 3 warning(s)      exit=0
```

Both typos are named with the key they missed; the stray table is one line, not two. Exit 0.

**The warning is a warning, and nothing else moved.** `taskrail list` prints the task and exits 0,
printing nothing about the config; `show T001 --json` reports
`"worktree": ".worktrees/T001-add-a-price-table"` — `worktree_dr` really is ignored, and the default
really is what the repository gets, which is the silent behaviour change T088 E2 described, now
audible. `validate --json` gives `"valid": true` with the three issues in `issues`.

**An error still decides the exit code.** With a task kind of `storyy` added on top of the three
typos, `validate` lists all four issues and exits **1** on the error, counting
`1 error(s), 3 warning(s)`.

No behaviour differs from the plan, so the `verify` gate did not stop.
