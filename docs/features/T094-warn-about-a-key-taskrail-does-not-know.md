# T094 — Warn about a key taskrail does not know in `.taskrail/config.toml`

Kind: feature · Epic: E08 · Status: planned

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
