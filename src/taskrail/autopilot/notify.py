"""`autopilot notify`: run `[autopilot].notify` for an event (DESIGN.md §12.6).

The command runs through the platform shell in the repository root, with the message on stdin and
`TASKRAIL_EVENT`, `TASKRAIL_RUN` and `TASKRAIL_TASK` in its environment. A notification that fails
is reported and never blocks: the caller learns it from `sent`, not from an exit code.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile

from taskrail.config import Config
from taskrail.model import Task

TIMEOUT_SECONDS = 30
OUTPUT_LIMIT = 2000  # characters kept from the end of the command's stdout and stderr
TASK_EVENTS = ("lane-done", "lane-failed")  # events about one lane, which need --task


def compose_message(event: str, run: dict, task: Task | None, text: str | None) -> str:
    """The plain-text message the notify command reads on stdin."""
    lines = [f"taskrail autopilot: {event} in run {run['id']}"]
    if task is not None:
        lines.append(f"{task.id} {task.title}")
        lane = run["tasks"].get(task.id)
        if lane:
            summary = f"lane: {lane.get('state') or 'running'}"
            if lane.get("gate"):
                summary += f" at {lane['gate']}"
            if lane.get("reason"):
                summary += f" — {lane['reason']}"
            lines.append(summary)
    if text:
        lines += ["", text]
    return "\n".join(lines) + "\n"


def _tail(handle) -> str:
    handle.seek(0)
    return handle.read().decode("utf-8", errors="replace")[-OUTPUT_LIMIT:]


def _kill(process: subprocess.Popen) -> None:
    """Stop the command and every process it started (POSIX); on other platforms, the shell only."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, PermissionError):
        pass


def notify(config: Config, event: str, run: dict, task: Task | None, text: str | None) -> dict:
    command = config.autopilot.notify
    message = compose_message(event, run, task, text)
    result = {
        "event": event,
        "run": run["id"],
        "task": task.id if task else None,
        "command": command,
        "sent": False,
        "skipped": None,
        "exit_code": None,
        "timed_out": False,
        "error": None,
        "stdout": "",
        "stderr": "",
        "message": message,
    }
    if not command.strip():
        result["skipped"] = "no command in [autopilot].notify"
        return result
    if event not in config.autopilot.notify_on:
        result["skipped"] = f"{event} is not in [autopilot].notify_on ({', '.join(config.autopilot.notify_on) or 'empty'})"
        return result

    environment = {**os.environ, "TASKRAIL_EVENT": event, "TASKRAIL_RUN": run["id"], "TASKRAIL_TASK": task.id if task else ""}
    # Temporary files rather than pipes: a command that leaves a child holding its output, or that
    # never reads its input, cannot make taskrail wait.
    with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        stdin.write(message.encode("utf-8"))
        stdin.seek(0)
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=config.root,
                env=environment,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                start_new_session=sys.platform != "win32",
            )
        except OSError as exc:
            result["error"] = f"the notify command could not be started: {exc}"
            return result
        try:
            result["exit_code"] = process.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _kill(process)
            process.wait()
            result["timed_out"] = True
            result["error"] = f"the notify command timed out after {TIMEOUT_SECONDS} s and was stopped"
        else:
            if result["exit_code"] == 0:
                result["sent"] = True
            else:
                result["error"] = f"the notify command exited with status {result['exit_code']}"
        result["stdout"] = _tail(stdout)
        result["stderr"] = _tail(stderr)
    return result
