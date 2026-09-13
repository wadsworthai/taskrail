## On Claude Code

- At a gate, ask the human with the AskUserQuestion tool when it is available; otherwise ask in
  plain text.
- Running as a subagent, you have no channel to the human: end your turn with the gate report
  and wait to be resumed.
- Create task worktrees with git as described above rather than through a subagent's worktree
  isolation, which picks its own branch name and location.
