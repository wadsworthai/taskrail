# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

taskrail is an agent-agnostic backlog tool: a deterministic CLI plus the skills agents follow to
execute backlog tasks. This repository is where it is developed; other repositories install it.

The repository is MIT-licensed and public. **Update this file as it grows** — especially the
Commands section.

## Language policy

- **Everything committed to the repository is in English** — code, identifiers, comments,
  documentation, skill descriptions, commit messages, PR titles and bodies, file names.
- **Conversation with the user mirrors the language they write in.** They may write in
  Spanish or English; answer in that same language. This never changes what goes in the files.

## Publishing constraint

Content arrives here by extraction from other projects, and this repository is public.
When importing anything, strip what does not belong in the open: internal hostnames, private
URLs and repo paths, client or employer names, ticket IDs, sample data derived from real
records, and any assumption about a private project's directory layout. Generalize a tool so
it stands on its own before committing it, rather than committing it and cleaning up later.

## Agent portability

Claude Code is the first target, not the only one. taskrail's canonical form must not assume a
particular agent:

- **Keep agent-specific packaging out of the item itself.** Marketplace manifests,
  `plugin.json`, hook wiring and installers belong in a separate adapter layer, so the same
  skill or tool can be wired into a second agent without being rewritten.
- **`SKILL.md` plus YAML frontmatter is the portable core** — many agents read it. Claude-only
  frontmatter keys are ignored elsewhere, which is fine for hints but **not** for guarantees:
  a skill whose safe behaviour depends on `disable-model-invocation` or `user-invocable` is
  unsafe on an agent that ignores those keys. State such a rule in the skill's prose too, where
  every agent will read it.
- **Prefer plain contracts for tools** — arguments, stdin/stdout, exit codes — over
  agent-specific integrations, so any agent can call them through a shell.

## Backlog

This repository tracks its own work with taskrail: `TODO.md` holds the epics and tasks, and
`.taskrail/bin/taskrail` runs the CLI from this checkout's source (the config pins `local:.`), so a
task worktree runs its own branch's code. Use the `taskrail` skill and its executor skills to work
tasks.

- The skills under `.claude/skills/taskrail*` are **installed copies**. Edit the sources in
  `src/taskrail/skills/`, then run `.taskrail/bin/taskrail upgrade`.
- `TODO.md` and the artifacts under `docs/` are public like everything else here; the
  publishing constraint above applies to task titles, descriptions and write-ups.
- Claims stay local (`claim_remote` is off), so no refs are pushed for them.

## Commands

Python, managed with uv, no runtime dependencies. Run from the repository root:

```bash
uv run pytest                                   # all tests
uv run pytest tests/test_validate.py -k cycle   # a single test
uv run taskrail --root <repo> validate          # run the CLI against a repository
```
