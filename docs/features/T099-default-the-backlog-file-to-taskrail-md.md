# T099 — Default the backlog file to TASKRAIL.md

`[[backlog]].file` was required with no default, and `taskrail init` seeded it as `TODO.md` — the
one name a consuming repository most likely already uses for its own list. This task makes
`TASKRAIL.md` the default, so taskrail stops taking that name.

## Why this is safe: `file` was required

**`file` is required today, so no configuration that loads at all omits it. Adding a default
therefore cannot change what any existing repository does.** The new default is reachable only
through a key that no valid configuration leaves out, which makes every other claim below a
consequence rather than a hope:

```
$ uv run taskrail --root <scratch>/e1 validate     # [[backlog]] with name and prefix, no file
taskrail: .taskrail/config.toml: missing required key `file`
exit=2
```

Three further properties hold on top of it:

- `init` and `upgrade` call `Installer.seed(backlog.file, …)`, which returns early when the path
  exists — *"Create a file the repository owns from then on; never touch an existing one"*
  (`src/taskrail/install.py`). A repository's backlog file is reported `unchanged` and left
  byte-identical.
- A repository pinned to an older taskrail keeps running that CLI, so it does not even see the new
  default; and when it upgrades, its config still names its file.
- Nothing renames an existing backlog file, and nothing offers to. This is a default, not a
  migration mechanism.

### What a repository that already names `TODO.md` sees

Nothing. Its config names `file = "TODO.md"` — it must, per the proof above — so no default is
applied over it, `init` and `upgrade` leave both the config's `file` line and the file itself
alone, and no `TASKRAIL.md` is created. Criterion 4 and criterion 5 pin this down as tests.

The adoption path for a repository that wants taskrail to use its own `TODO.md` stays explicit:
write `file = "TODO.md"`, or convert the list with `taskrail import TODO.md --write`, which writes
into the seeded `TASKRAIL.md` and leaves the source untouched (DESIGN.md §7.3).

## Behaviour

- A `.taskrail/config.toml` may declare a backlog without naming a file. `[[backlog]].file` is
  optional and defaults to `TASKRAIL.md`.
- `taskrail init` in a fresh repository writes `file = "TASKRAIL.md"` in the config it seeds and
  creates `TASKRAIL.md`, headed `# Backlog`.
- A repository whose config names a file — `TODO.md` or anything else — is untouched.
- A repository that already keeps its own `TODO.md` is no longer taken over by `init`: taskrail
  creates `TASKRAIL.md` beside it and leaves the repository's list alone. Before this change `init`
  silently adopted that file as the backlog and the repository failed `validate` out of the box:

  ```
  $ printf '# Our TODO\n\n- [ ] ship the thing\n' > <scratch>/e5/TODO.md
  $ uv run taskrail --root <scratch>/e5 init
  created   .taskrail/config.toml
  created   .taskrail/bin/taskrail
  created   .gitignore
  1 file(s) already up to date          # ← TODO.md, "unchanged": adopted, not created
  $ uv run taskrail --root <scratch>/e5 validate
  TODO.md: error: no `## Epics` section [epics-missing]
  exit=1
  ```

## Acceptance criteria, and the tests that cover them

Every test below was written before the implementation and observed failing
(`8 failed, 1 passed`; see *Evidence*).

| # | Criterion | Test |
|---|---|---|
| 1 | `[[backlog]].file` is optional; omitted, the backlog's file is `TASKRAIL.md`, and `validate` and `show` agree | `tests/test_backlog_file_default.py::test_a_backlog_without_a_file_key_defaults_to_taskrail_md` |
| 2 | A named `file` keeps its exact value; no default is applied over it, and no `TASKRAIL.md` appears | `…::test_a_named_file_keeps_its_value` |
| 3 | `init` in a fresh repository writes `file = "TASKRAIL.md"` and creates `TASKRAIL.md`; no `TODO.md` anywhere | `…::test_init_seeds_taskrail_md_and_names_it_in_the_config` |
| 4 | `init` and `upgrade` on a repository naming `TODO.md` report it `unchanged`, leave it byte-identical, keep the `file` line and create no `TASKRAIL.md` | `…::test_a_repository_that_names_its_file_is_untouched_by_init_and_upgrade` |
| 5 | `upgrade` seeds a configured backlog file only when it is missing | `…::test_upgrade_re_seeds_a_backlog_file_only_when_it_is_missing` |
| 6 | Omitting `file` where no `TASKRAIL.md` exists reports `backlog-missing` naming `TASKRAIL.md`, exit 1 | `…::test_an_omitted_file_with_no_taskrail_md_reports_backlog_missing` |
| 7 | `file` stays a name taskrail defines (T094), so writing it never warns and `fille` warns `did you mean \`file\`?` and fails as `backlog-missing` instead of exiting 2 | `…::test_file_stays_a_known_key_and_a_misspelling_warns` |
| 8 | `init` in a repository holding its own `TODO.md` creates `TASKRAIL.md`, leaves `TODO.md` byte-identical, and `validate` passes | `…::test_init_does_not_adopt_a_repositorys_own_todo_md` |
| — | The seeded file is headed `# Backlog`, not `# TODO` | `…::test_the_seeded_file_is_headed_backlog_not_todo` |

Criterion 2 is the one that passed before the change as well as after: it is a regression guard on
behaviour that must *not* move, which is exactly what the proof above requires of it.

## Affected areas

| Area | Change |
|---|---|
| `src/taskrail/config.py` | `DEFAULT_BACKLOG_FILE = "TASKRAIL.md"`; `BacklogConfig.file` defaults to it; `expect(raw, "file", str, DEFAULT_BACKLOG_FILE)` replaces `required=True`. `TABLE_KEYS["backlog"]` keeps `"file"`, so T094 still warns about a misspelling of it. |
| `src/taskrail/install.py` | `default_config` seeds `file = "TASKRAIL.md"` with a comment; `DEFAULT_TODO` → `DEFAULT_BACKLOG`, headed `# Backlog`. |
| `tests/test_backlog_file_default.py` | New; the nine tests above. |
| `tests/test_install.py`, `tests/test_merge_driver.py`, `tests/test_import.py` | The places that name the file `init` seeds, or the constant holding its content. Hand-written configs that name `TODO.md` themselves, and the path-quoting unit test `test_attribute_lines_match_exactly_their_path`, are left alone — they do not depend on the default. |
| `DESIGN.md` | §1 the main-file line; §3.1 a sentence plus the example's heading; §4 the example's `file` line plus a paragraph on the default; §7.3 the sentence this change makes false. |
| `README.md` | Two word swaps in *Install*. |
| `src/taskrail/skills/taskrail/SKILL.md` | Stops fixing a file name, in the prose and in the `description`; `.claude/skills/taskrail/SKILL.md` and `.taskrail/installed.json` follow from `taskrail upgrade`. |
| `CHANGELOG.md` | One bullet under `## Unreleased`, naming the forward-compatibility cost. |
| `TODO.md` | This task's own row, through the CLI only. |

### Sections that need no edit

- **DESIGN.md §9** already describes the seeded set as "`.taskrail/config.toml` and each backlog
  file" and never writes the literal `TODO.md`. It is correct as it stands.
- **DESIGN.md §10**'s tree shows *this* repository's own `TODO.md`. A seeded file belongs to the
  repository; this one keeps its name.
- **DESIGN.md §4**'s second example backlog, `file = "APP_TODO.md"`, demonstrates a repository
  naming its own file.
- **README's *Adopting an existing backlog*** names `TODO.md` as the *source* of an import, which
  stays correct.

## Out of scope

- Renaming any existing repository's backlog file, and any prompt, flag or command that would.
- Any change to `taskrail import`'s behaviour; only the one sentence of §7.3 that became false.
- A `--file` flag for `init`.
- Renaming this repository's own `TODO.md`, or §4's `APP_TODO.md`.

## Open questions and risks

- **Forward compatibility, the one real cost.** A config written for this version that *omits*
  `file` will not load on taskrail v0.3.0 or earlier: it exits 2 with `missing required key
  \`file\``. This is the ordinary cost of any new optional key, the config carries a version pin,
  and the CHANGELOG bullet says it.
- **A default is silent where a required key was loud.** Omitting `file` by accident now points the
  backlog at `TASKRAIL.md` instead of failing at load. It cannot silently read the wrong file:
  `validate` reports `backlog-missing` naming `TASKRAIL.md` (criterion 6). Only a repository that
  both omits the key and happens to have a `TASKRAIL.md` could be surprised, and that file would be
  the one it meant.
- **A misspelling now fails more softly, and more usefully.** `fille = "TODO.md"` used to exit 2 on
  a missing required key, which swallowed T094's warning entirely. It now warns
  ``unknown key `fille` … did you mean `file`?`` and exits 1 on `backlog-missing` (criterion 7).
- **`README.md` and the T100 rebase.** T100 (`bd9458a`, merged) rewrote *Install* around `uvx`. The
  two sentences carrying `TODO.md` survived it word for word, but the line after the first one did
  not, so a rebase may conflict there. The intended final text is exactly: ``` `init` is safe to
  run again. It creates `.taskrail/config.toml` and `TASKRAIL.md` when missing, and ``` and
  ``` Commit `.taskrail/`, `TASKRAIL.md` and the installed skills. Skills and managed files you
  edit are ```, with every other word of T100's text kept.
