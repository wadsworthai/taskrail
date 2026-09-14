# T033 — autopilot decisions

Decisions for this task while it ran in an autopilot lane. Its frame and decide gates are reserved
to the human; the orchestrator relays them and records the answers before resuming the lane.

## frame gate — escalated to the human

Reviewed: the frame in `docs/spikes/T033-trial-the-autopilot-on-a-real-backlog-wi.md` (commit
`d822080`), the environment checks (Claude Code 2.1.270 and OpenCode 1.15.13 available, `gh` not
installed), and the CLI probes (exit-5 refusal, both agents' skills installed, no pull request link
with a local bare remote, absolute remote paths required).

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| Q1 | Definition of "what the design got wrong" | checks D1–D12 · drop the new-session probe | **D1–D12** (orchestrator's proposal; the human did not object) | Keeps §12.3's claim that a new session can resume lanes under test. |
| Q2 | Backlog | synthetic in a throwaway repository · copy of this backlog · a consumer project | **synthetic** — decided by the human | Same backlog for both agents, every design path triggerable, no real merges, publishable seed. |
| Q3 | Roles | the human drives both orchestrator sessions with a local bare remote and a squash helper · private hosted repository with pull requests | **the human, local bare remote** — decided by the human | A lane cannot drive a session, and headless modes skip permission prompts. |
| Q4 | Models | same model on both agents · each agent's default · an extra non-Claude run | **same model** (Claude Code default, OpenCode `github-copilot/claude-opus-5`) — decided by the human | Measures the agent, not the model. |
| Q5 | Permissions | a common trial-local allowlist, prompts outside it counted · default prompts | **common allowlist** — decided by the human | Comparable runs without skipping any prompt. |
| Q6 | Extra runs | none · OpenCode background subagents | **none** (orchestrator's proposal; the human did not object) | The design does not require the experimental flag. |
| Q7 | Order and pinning | Claude Code first, taskrail pinned at `977064f`, no patches between runs · OpenCode first | **Claude Code first, pinned, no patches** (orchestrator's proposal; the human did not object) | A shared answer sheet limits order effects; patches mid-trial would break the comparison. |
| Q8 | Time box and the investigate stop | 2 points of analysis, at most 3 hours per run, investigate stops once seed, scripts, answer sheet and capture are built · other limits | **as proposed** (orchestrator's proposal; the human did not object) | The agent runs need the human, so the lane stops before them. |

Frame approved.

## investigate — stopped before the agent runs, as agreed

Reviewed: commit `4be511f` (the trial kit under `docs/spikes/T033-trial-kit/` and the updated
spike document) and the lane's dry run through the CLI alone, which passed every check and reset
the kit. The orchestrator searched the committed files for user names, home paths, hosts, e-mail
addresses and private project names; the only local detail found was the name of a user-level
OpenCode skill, which it removed from the document.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Hand the kit to the human now | yes · extend the dry run first | **yes** | What the dry run leaves out (a stacked rebase, the spike's decide flag, content-only merges, real conflicts) needs the agents; the human runs them from `RUNBOOK.md`. |

## decide gate — decided by the human

Reviewed: the completed spike (commits `f4041e8` kit fixes, `42ea93a` decision) evaluating three
runs — an aborted Claude Code attempt, a complete Claude Code run (5/5 merged) and an OpenCode run
with a substituted model stopped by a usage limit (0/5 merged) — against checks D1–D12, with
findings F1–F13 classified. The committed files carry no local user, account or session details.

| # | Question | Options | Decision | Reason |
|---|---|---|---|---|
| 1 | Verdict | option 2, keep the design with targeted fixes · option 1, skill text only · option 3, lanes always restart from checkpoints | **option 2** — decided by the human | The design delivered 5/5 on Claude Code; F1, F3 and F7 need CLI and integration changes, not a redesign. |
| 2 | Follow-up tasks | all proposed · design-level only · none | **all proposed** — decided by the human | Features for F1, F7, F9, F10, F12 and F11; bugs for F8 and F13; chores for the skill text (F2, F4, F5, F6, F7) and the OpenCode note (F3); one spike for compaction, OpenCode with a Claude model and messaging an old lane. |
| 3 | How follow-ups are verified | end-to-end trials like T033 · short automated tests | **short automated tests** — decided by the human | Trials like T033 are long and need a human at several terminals; follow-ups must be checkable quickly and without one. |
