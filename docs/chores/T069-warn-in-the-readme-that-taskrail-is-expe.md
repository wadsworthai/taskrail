# T069 — Warn in the README that taskrail is experimental and AI-developed

## Goal

`README.md` gives no sign of taskrail's maturity: it has no "experimental", "warning", "alpha" or
"unstable" wording, and nothing says how taskrail is developed. A reader deciding whether to adopt
it should learn, before the install instructions, that it is experimental — commands, files and
skills may still change incompatibly — and that it is developed with AI agents.

This chore adds a short, factual notice near the top of `README.md`.

## Change set

Approved at the scope gate as proposed (decision record:
`docs/autopilot/decisions/T069-warn-in-the-readme-that-taskrail-is-expe.md`).

- `README.md` — one notice between the introductory paragraph (which ends with "See
  [DESIGN.md](DESIGN.md) for the full model.") and `## Install`. Wording:

  ```markdown
  > **Experimental.** taskrail is under active development and not yet stable: commands, flags,
  > file formats and skills may change incompatibly between releases, so pin a release and read
  > [CHANGELOG.md](CHANGELOG.md) before upgrading. It is developed with AI coding agents, under
  > human direction and review.
  ```

  Nothing else in `README.md` changes.
- This artifact and its row in `docs/chores/README.md`.

## Decisions needed

Decided at the scope gate: the wording as proposed, a plain blockquote with a bold lead, placed
after the introductory paragraph, and no CHANGELOG.md entry. The options that were put forward:

1. **Wording.** Approve the text above, or amend it. Alternatives: drop the upgrade advice
   ("so pin a release and read CHANGELOG.md before upgrading") to keep only the two statements
   asked for; or drop "under human direction and review" if the human does not want to make that
   claim.
2. **Markup.** Recommended: a plain blockquote with a bold lead, as above, which renders the same
   on GitHub, in other forges and in package metadata built from `readme = "README.md"`.
   Alternative: GitHub's alert syntax (`> [!WARNING]` on its own line, then the text), which
   renders as a coloured warning box on GitHub but shows the literal `[!WARNING]` elsewhere.
3. **Placement.** Recommended: after the introductory paragraph, so the first thing the README
   says is still what taskrail is, and the warning comes before *Install*. Alternative: directly
   under the `# taskrail` heading.
4. **CHANGELOG.md.** Recommended: no entry. The Unreleased notes describe changes users of the CLI
   and skills act on; this notice changes no behaviour and states what was already true.
   Alternative: one Unreleased bullet, for example "**The README marks taskrail as
   experimental and developed with AI agents.**"

## Out of scope

- `pyproject.toml` metadata such as a `Development Status` classifier.
- `DESIGN.md`, `CLAUDE.md`, the skills and any code: the notice is for readers of the README.
- Any change to versioning or release policy implied by "experimental".

## Verification

All commands run against the task's worktree (`<worktree>` below).

- `git -C <worktree> diff origin/main -- README.md` shows one hunk, `@@ -4,6 +4,11 @@`: the four
  lines of the notice and a blank line after them, between the introductory paragraph and
  `## Install`. No other README line changes. The notice's link target, `CHANGELOG.md`, exists at
  the repository root.
- `git -C <worktree> diff origin/main --stat` lists only `README.md`, `TODO.md` (the task's row),
  this artifact and its index row, and the decision record and its index row.
- `taskrail checks T069 --stage implement`: `test` (`uv run pytest -q`) gave
  `959 passed in 124.25s (0:02:04)`. `lint` is not configured in the `checks` map.
- `taskrail --root <worktree> validate`: `58 task(s) in 1 backlog(s): 0 error(s), 0 warning(s)`,
  exit 0.

## Docs

Nothing else to update. The change is itself documentation; `CLAUDE.md`, `DESIGN.md` and the
skills describe neither the README's structure nor the project's maturity, and the scope gate
decided against a `CHANGELOG.md` entry. No follow-up tasks were opened.
