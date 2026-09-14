# T024 — autopilot decisions

Decisions the orchestrator took on the human's behalf while this task ran in an autopilot lane.
Each is recorded before it is given to the lane.

The human asked the autopilot to start tasks from the branches that block them. T024 started on an
integration of T032 and T031, both unmerged; both merged before the plan was committed, so the lane
recreated the workspace on `origin/main` (`a41ca8a`) and claimed without `--ignore-deps`.

## plan gate

Reviewed: the plan in `docs/features/T024-write-the-taskrail-autopilot-skill-with.md` (commit
`3b03bc9`), its thirteen acceptance criteria and Q1–Q10, and the lane's probes: the new skill is not
removed by the kind filter, reference files are not installed today, the integration notes replace
the harness marker in every skill, and `autopilot start` refuses with exit 5 in a fresh repository.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Skill structure | `SKILL.md` plus `references/lane-brief.md`, `gate-review.md`, `decision-record.md` · one long file · two references | **as recommended** | The orchestrator loads the brief and checklists when it needs them; `SKILL.md` stays readable. |
| Q2 | Installing reference files | every file in a skill directory as a managed file, marker replaced only in `SKILL.md` · no installer change | **as recommended** | Without it references never reach a consumer; the manifest tracks each file's digest as for skills. |
| Q3 | Per-skill agent notes | sections opened by `<!-- taskrail:skill <name> -->` in `claude.md`/`opencode.md` · per-skill files · one shared note | **sections** | Orchestrator instructions must not reach every lane's core skill; the core skill's text stays unchanged. |
| Q4 | Lane brief | template in the skill filled from `next --json` · rendered by `next` | **template in the skill** | Agent-facing prose stays out of Python and `next` stays finished. |
| Q5 | Gate criteria | per gate type from the decision records · generic approve | **per gate type** | These checks caught real gaps in this run: tests seen failing, deliberate breakages, scratch runtimes, no upstream before publishing. |
| Q6 | Who rebases | lane stops after `review --json`, orchestrator rebases at hand-off · both | **orchestrator at hand-off** | One rebase per hand-off onto the mainline that is actually current; the brief states the override of core step 8. |
| Q7 | Rebase section format | `File / Conflict / Resolution` per §12.5 · the Question/Options table the records use | **the Question/Options table, and update §12.5 to it** | One table shape for every section of a record; this run's records are the working evidence and read well. |
| Q8 | Tests | invariants (installation, notes, prose rules, no agent names in portable text, commands exist in the parser) · full snapshot | **invariants** | A snapshot would fail on every wording change and prove nothing about behaviour. |
| Q9 | DESIGN §12 status | skill parts and heading *implemented* · keep "partly implemented" | **implemented** | T033 is a trial and builds nothing; it changes the design only through its findings. |
| Q10 | Starting from several unmerged dependencies | short paragraph: only on the human's explicit instruction, record the integration merge as the fork point, claim with `--ignore-deps --run R` · leave out | **include it** | The human asked for exactly this in this run, and the procedure worked. |

Plan approved with Q7 changed.

## implement gate

Reviewed: commits `d0599f9` (tests alone) and `01ebfe1` (the skill, its three references, per-skill
sections in the integration notes, `install.py` `harness_sections`/`skill_of`/`skill_files`,
DESIGN.md §8–§10 and §12, README, CHANGELOG, this repository's installed copy). Read the portable
`SKILL.md` in full: it names no agent and no private project, states the "only when asked with a
count" and exit-5 rules in prose, and matches this run's practice. Re-ran `uv run pytest -q` in the lane's worktree: 629 passed. The 24 new tests failed before the
code; six deliberate breakages (installing only `SKILL.md`, notes for every skill, removing only
`SKILL.md` paths, an invented flag, dropping "stop and report", no `notify` in the skill) each failed
the tests that cover them.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Approve the implementation | approve · changes | **approve** | Follows Q1–Q10 with Q7 changed; criteria map to tests seen failing. |
| 2 | Deviations: no separate escalations list in `SKILL.md`, `<SERVICES>` and `<CONTEXT>` placeholders, a per-skill column in the §8 notes table | accept · revert some | **accept all** | Small and visible; the record template keeps the escalation section. |
| 3 | Rebase at close | lane rebases · orchestrator rebases at hand-off | **orchestrator at hand-off** | The skill this task writes says lanes stop after `review --json`; the orchestrator follows it. |

## verify, close and rebase after T005 and T038

The verify stage installed the skill for Claude Code, OpenCode and both, confirmed the exit-5
refusal, filled every placeholder of the lane brief from a real `autopilot next --json`, and ran the
commands the brief hands out. It noted that `autopilot start --json` nests the ID as `run.id`, which
the skill did not name.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Rebase onto `origin/main` (`cfba7e6`, T005 and T038 merged) | plain rebase · `--onto` | **plain rebase** | The fork point `a41ca8a` is on `main`. The docs indexes and CHANGELOG conflicted and kept both, one bullet per task. |
| 2 | Name `run.id` in the skill | now, before publishing · leave for T033 | **now** | One phrase that prevents a wrong read in every run; the orchestrator committed it separately and regenerated the installed copy with `upgrade`. |

After the rebase: no conflict markers, the skill source still keeps T038's core step 3, `pytest -q`
665 passed, `taskrail validate` 0 errors, a second `upgrade` reports nothing to create or update.
