<!-- taskrail:skill taskrail -->

## On OpenCode

- At a gate, ask the human in plain text and wait for the reply.
- Running as a subagent, your final message goes back to the agent that started you: end with
  the gate report so that agent can relay it.

<!-- taskrail:skill taskrail-autopilot -->

## On OpenCode

- Launch each lane with the task tool, `subagent_type` `general` (or a lane agent definition the
  repository provides), with the filled lane brief as its prompt. The `task_id` it returns — the
  child session's ID — is the lane's handle for `autopilot lane --handle`.
- Resume a lane by calling the task tool again with the same `task_id`: `continue <ID>` plus the
  answers.
- Task calls block until the subagent returns, and lanes started in one message return together.
  You therefore answer gates in waves, once every lane in the batch has stopped: correct, but
  slower. The experimental background subagents (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`)
  notify you when each lane stops instead; use them only when the human has enabled them.
- Lanes cannot ask the human: the `question` permission is denied to the `general` subagent. At
  an escalation, ask the human yourself in plain text and wait for the reply.
- A lane's model is the `model` of a lane agent definition.
- Nothing wakes you on a timer.
