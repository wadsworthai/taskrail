# T003 — Install taskrail in a first consumer project

Kind: chore · Epic: E01 · Branch: `T003-install-taskrail-in-a-first-consumer-pro`

## Goal

The backlog row asks to install taskrail in a real project and note any friction. The install
half is done: taskrail has been installed in a real repository outside this one, through the
`uvx` route the README documents as the default, with no global CLI install. What remains is the
second half — turning the friction that install produced into a change here.

**The finding, stated as a property of taskrail:** `init` does not set up the autopilot, so a
repository that wants it writes the `[autopilot]` config section by hand and has to go to
`DESIGN.md` §12 to find out which keys exist. That was the only thing the install left to be
done by hand; nothing else about the route, the CLI's messages or the assumed repository layout
caused trouble.

Verified in this checkout rather than taken on report:

- `taskrail init --help` offers `--integration`, `--github-workflow`, `--pre-commit`, `--force`
  and `--merge-driver`. There is no autopilot option.
- `grep -rn autopilot src/taskrail/install.py` prints nothing and exits 1: the config
  `default_config()` seeds has `[[backlog]]`, `[columns]`, `[points]`, `[git]`, `[review]` and
  `[checks]`, and no `[autopilot]` section — not even a commented one.
- `README.md` names `[autopilot].enabled = true` in its *Autopilot* section, but the *Install*
  section that walks through `init` does not mention the autopilot at all, and neither document
  says the section has to be written by hand.
- `upgrade()` in `src/taskrail/install.py` only re-pins `version`; `installer.seed` writes
  `.taskrail/config.toml` only when it is missing. So whatever `default_config()` seeds reaches
  new installs only, never an existing repository.

## Change set

Proposed, pending the decision below. Under the recommended option:

- `src/taskrail/install.py` — in `default_config()`, append a fully commented `[autopilot]`
  block after `[checks]`, carrying the keys a repository enabling the autopilot actually sets
  (`enabled`, `max_lanes`, `read_first`, `governing`, `escalate_gates`) and a pointer to
  `DESIGN.md` §12 for the rest. Every line stays a comment, so the seeded config loads exactly as
  it does today and `[autopilot]` stays absent until a repository uncomments it. This follows the
  block's own neighbours: `# aliases = …` under `[columns]` and `# test = "make test"` under
  `[checks]` are already commented examples.
- `tests/test_install.py` — one test that the seeded config carries the commented block and that
  `[autopilot]` is still not active in it (the config loads with the autopilot disabled), so the
  comment cannot silently turn into live configuration.
- `README.md` — one sentence in *Install*, where the `init` flags are listed, saying `init` does
  not configure the autopilot and that a repository enabling it uncomments or writes the
  `[autopilot]` section (README *Autopilot* and `DESIGN.md` §12 hold the keys). This is what
  reaches repositories that already ran `init`, which the seeded block cannot.
- `CHANGELOG.md` — one bullet under Unreleased, appended.
- `docs/chores/README.md` — the index row for this document.

## Decisions needed

**Question: which of these should T003 build?**

The friction is real and reported by a consumer, so it is evidence, not speculation — but
CLAUDE.md is explicit that an option with no caller today is not written, and that a documented
convention beats a mechanism that enforces it.

**Recommendation: (B) seed a fully commented `[autopilot]` block in `default_config()`, plus the
one-sentence README note.** It is the smallest change that removes the friction at the place
where it happens: the consumer is already in `.taskrail/config.toml` when the question arises, so
the answer belongs in that file. It adds no flag, no branch in the installer, no new
configuration semantics and no behaviour to test beyond "the comment is there and it is still a
comment". It is a documented convention, not a mechanism. The README line covers repositories
that already ran `init`, which the seeded block never reaches.

The alternatives, and why not:

- **(A) an `init --autopilot` flag that seeds a commented or minimal section.** A flag, a new
  install path, its own tests and a second question (does it write `enabled = true` or a disabled
  stub?) to remove the same friction a comment removes. KISS prefers the convention; the flag
  also has no second caller, and `upgrade` would not carry it to existing repositories either.
- **(C) documentation only — README or `DESIGN.md` §12.** The cheapest, but `DESIGN.md` §12.9 and
  §4 already list every key and README already names `enabled`, and the friction happened anyway:
  a consumer editing `.taskrail/config.toml` does not have those documents open. Recommended as
  part of (B), not instead of it.
- **(D) a follow-up task, closing T003 on the write-up alone.** The change is roughly ten
  commented lines in one template string and a test; deferring it costs more in process than in
  code, and leaves the next consumer with the same friction.

Two smaller choices inside (B), which I will take as recommended unless the answer says
otherwise:

- **Fully commented, not `enabled = false` live.** A live `enabled = false` would also be
  discoverable, but it puts a real `[autopilot]` table in every new repository's config and
  changes what `validate` and the config loader see. Commented keeps the seeded config
  byte-for-byte equivalent in meaning to today's.
- **Five keys, not all sixteen.** `enabled`, `max_lanes`, `read_first`, `governing` and
  `escalate_gates` are the ones this repository's own `[autopilot]` section sets; the rest
  (`kinds`, `decisions`, `silent_minutes`, `handoff`, `notify`, `notify_on`, the `group` and
  `resource` tables) stay in `DESIGN.md` §12.9, which the block points at. A full dump of the
  schema into every new config would be noise.

## Out of scope

- **Re-running the install.** It is done, in a repository that is not this one and is not public.
  Nothing here reproduces it, and nothing here names or describes it.
- **Making `upgrade` add the block to an existing config.** `upgrade` deliberately touches only
  the version pin; rewriting a repository's hand-edited config is a much larger change and is not
  what this friction asks for. The README sentence serves existing repositories instead.
- **Any change to the autopilot's behaviour, keys or defaults.** Only how a repository discovers
  them changes.
- **The `specs` area** (`never_edit`).

## Verification

To be filled in at the implement stage with the real output of:

- `uv run pytest -q` (the task's `test` check, through `taskrail checks T003 --stage implement`);
  `lint` is not configured in this repository and will be reported as such.
- An actual `taskrail init` into a scratch repository outside this checkout, showing the seeded
  `.taskrail/config.toml` with the commented `[autopilot]` block, and `taskrail validate` in that
  repository exiting 0 with no `config-unknown-key` warning — proving the comment stays inert.
- `taskrail autopilot start` in that scratch repository still refusing with exit 5 while the
  block is commented, which is the guarantee the change must not weaken.

## Notes

This document, the backlog row and every commit on this branch describe the finding as a property
of taskrail. The consuming repository, its owner, its domain, its layout and its purpose are not
named, described or implied anywhere in them, as CLAUDE.md's publishing constraint requires.
