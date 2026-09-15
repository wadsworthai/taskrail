<!-- taskrail:skill taskrail -->

## On Claude Code

- At a gate, ask the human with the AskUserQuestion tool when it is available; otherwise ask in
  plain text.
- Running as a subagent, you have no channel to the human: end your turn with the gate report
  and wait to be resumed.
- Create task worktrees with git as described above rather than through a subagent's worktree
  isolation, which picks its own branch name and location.
- Shape every shell command so a permission allowlist can match it: one command per Bash
  call, the taskrail wrapper and files by absolute path, and `git -C <worktree>` or
  `taskrail --root <worktree>` instead of `cd <worktree> && …`. Avoid `&&`, `;` and `|`
  chains, shell variables, `$?` and heredocs, and edit files with the Edit tool: Claude Code
  checks each part of a compound command on its own, so it asks for permission even when
  every part is allowed.
- Run a task's checks with `taskrail checks <ID>`, adding `--stage <stage>` for one stage's
  checks, rather than changing into its worktree: it runs them there, with the task's
  autopilot resources, as one command that a single allowlist entry covers.

<!-- taskrail:skill taskrail-autopilot -->

## On Claude Code

- Launch each lane as a background general-purpose subagent with the Agent tool, with the filled
  lane brief as its prompt, and launch the lanes of one dispatch in a single message so they run
  concurrently. The agent ID is the lane's handle for `autopilot lane --handle`.
- Resume a lane after a gate with `SendMessage` to its agent ID: `continue <ID>` plus the answers.
  A resumed subagent keeps its full context.
- A completion notification wakes you when a lane stops; run `autopilot status` then.
- Lanes cannot ask the human: `AskUserQuestion` is removed from subagents. At an escalation, ask
  the human yourself with `AskUserQuestion` when it is available, otherwise in plain text.
- When the human wants lanes on another model than yours, pass it in the Agent tool's `model`
  parameter.
- Lanes create their worktrees with git, as the brief says, never through the Agent tool's
  worktree isolation, which picks its own branch name and location.
- Nothing wakes you on a timer. A tool that waits on a condition may re-run `autopilot status`
  while lanes work, but nothing may depend on it.
- Use the command shape of the `taskrail` skill's Claude Code notes yourself — one command
  per Bash call, absolute paths, `git -C` and `taskrail --root` rather than `cd … &&` — and
  re-run a lane's checks at a gate or at hand-off with `taskrail checks <ID>`, which runs them
  in its worktree with its resources.
