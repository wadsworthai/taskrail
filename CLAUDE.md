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

## Commands

None yet — the repository has no build, lint, or test setup. Tools are expected to carry their
own (per-directory) instructions. Record any repository-wide command here once one exists.
