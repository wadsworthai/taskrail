# T099 — Default the backlog file to TASKRAIL.md

`[[backlog]].file` is required with no default, and `taskrail init` seeds it as `TODO.md` — the
one name a consuming repository most likely already uses for its own list. This task makes
`TASKRAIL.md` the default, so taskrail stops taking that name.

## Behaviour

Afterwards:

- A `.taskrail/config.toml` may declare a backlog without naming a file. `[[backlog]].file`
  becomes optional and defaults to `TASKRAIL.md`.
- `taskrail init` in a fresh repository writes `file = "TASKRAIL.md"` in the config it seeds and
  creates `TASKRAIL.md`.
- A repository whose config names a file — `TODO.md` or anything else — is untouched. The named
  value is used as it always was, no default is applied, and neither `init` nor `upgrade` rewrites
  or re-seeds the file it points at.
- A repository that already keeps its own `TODO.md` is no longer taken over by `init`: taskrail
  creates `TASKRAIL.md` beside it and leaves the repository's list alone.

Nothing renames an existing repository's backlog file, and nothing offers to. This is a default,
not a migration mechanism.

### What a repository that already names `TODO.md` sees

Nothing changes, and this is proven rather than asserted below (E3, E4):

- Its config names `file = "TODO.md"` explicitly — it must, because `file` is required today, so
  **no config that loads at all today can be affected by a default being added**. The new default
  is reachable only by a key that no existing valid config omits.
- `init` and `upgrade` call `Installer.seed(backlog.file, …)`, which returns early when the path
  exists (`install.py`, `seed`: "Create a file the repository owns from then on; never touch an
  existing one"). The file is reported `unchanged` and left byte-identical.
- The version pin in its config keeps it on the CLI it chose, so it does not even see the new
  default until it upgrades — and then still not, because its config names the file.

## Acceptance criteria

1. `[[backlog]].file` is optional. A config that omits it loads, and the backlog's file is
   `TASKRAIL.md`.
2. A config that names `file` keeps that exact value; no default is applied over it.
3. `taskrail init` in a fresh git repository creates `.taskrail/config.toml` holding
   `file = "TASKRAIL.md"` and creates `TASKRAIL.md`.
4. `taskrail init` in a repository whose config names `TODO.md`, with that file present, leaves
   the config and the file byte-identical, reports them `unchanged`, and creates no `TASKRAIL.md`.
5. `taskrail upgrade` leaves an existing backlog file byte-identical; it seeds a configured
   backlog file only when that file is missing.
6. `validate` on a config that omits `file` in a repository with no `TASKRAIL.md` reports
   `backlog-missing` naming `TASKRAIL.md`, exit 1 — the case an optional `file` makes reachable by
   omission.
7. `file` stays a name taskrail defines (T094's `TABLE_KEYS`), so writing it never warns, and a
   misspelling such as `fille` now warns `did you mean \`file\`?` and fails as `backlog-missing`
   rather than exiting 2 on a missing required key.
8. `taskrail init` in a repository holding its own, non-taskrail `TODO.md` creates `TASKRAIL.md`
   and leaves `TODO.md` untouched, and `validate` then passes.

## Affected areas

| Area | Change |
|---|---|
| `src/taskrail/config.py` | `DEFAULT_BACKLOG_FILE = "TASKRAIL.md"`; `BacklogConfig.file` gains that default; `expect(raw, "file", str, DEFAULT_BACKLOG_FILE)` replaces `required=True`. `TABLE_KEYS["backlog"]` keeps `"file"`. |
| `src/taskrail/install.py` | `default_config` seeds `file = "TASKRAIL.md"`; the seeded-file constant and its `# TODO` heading follow (decision D4). |
| `tests/` | One new test module for the criteria above, plus the existing modules that name the constant. |
| `DESIGN.md` | §1 one line, §4 the example's `file` line plus one prose sentence, §7.3 one sentence. §9 needs no edit (see below). §3.1 only under D4. |
| `README.md` | Two word swaps in *Install* (decision D2). |
| `src/taskrail/skills/taskrail/SKILL.md` | Stop naming a file at all (decision D3). |
| `CHANGELOG.md` | One bullet under `## Unreleased`. |
| `TODO.md` | This task's own row, through the CLI only. |

### Why §9 needs no edit

DESIGN.md §9 already describes the seeded set as "`.taskrail/config.toml` and each backlog file"
and never writes the literal `TODO.md`. It is correct as it stands, which also keeps this task out
of the section T100 is rewriting.

### Why §10 needs no edit

§10's tree shows this repository's own `TODO.md`. A seeded file belongs to the repository; this
repository keeps its name.

## Out of scope

- Renaming any existing repository's backlog file, and any prompt, flag or command that would.
- Any change to `taskrail import`'s behaviour; only the one sentence of §7.3 that becomes false.
- A `--file` flag for `init`.
- Renaming this repository's own `TODO.md`, or the second example backlog `APP_TODO.md` in §4.

## Open questions and risks

- **Forward compatibility.** A config written for the new CLI that *omits* `file` will not load on
  taskrail ≤ v0.3.0: it exits 2 with `missing required key \`file\``. This is the ordinary cost of
  any new optional key, the config carries a version pin, and the CHANGELOG bullet must say it.
- **A default is silent where a required key was loud.** Omitting `file` by accident now points the
  backlog at `TASKRAIL.md` instead of failing at load. It cannot silently read the wrong file:
  `validate` reports `backlog-missing` (E2). Only a repository that both omits the key and happens
  to have a `TASKRAIL.md` could be surprised, and that file would be the one it meant.
- The decisions D1–D6 are carried to the plan gate.
