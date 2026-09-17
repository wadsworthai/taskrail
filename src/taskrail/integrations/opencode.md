<!-- taskrail:skill taskrail -->

## On OpenCode

- At a gate, at a decision and before a push, ask the human in plain text and wait for the reply.
- Running as a subagent, your final message goes back to the agent that started you: end with
  the gate report or the question so that agent can relay it.

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
- While a batch of task calls blocks, you see neither the human nor `autopilot status`. When a
  batch returns, before anything else, record the handle of every lane it started with
  `autopilot lane --handle`, then run `autopilot status --run <R> --json` and deal with every
  `silent` lane before you start the next batch.
- Lanes cannot ask the human: the `question` permission is denied to the `general` subagent. At
  an escalation, ask the human yourself in plain text and end your turn with that question. Never
  start another batch of blocking task calls in the same turn: it leaves the human no point at
  which to answer. Resume the other lanes in the batch that follows the human's reply; with the
  background subagents, which do not block, resume them before you ask.
- A lane's model is the `model` of a lane agent definition.
- Nothing wakes you on a timer.
