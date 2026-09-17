"""`taskrail checks <ID>`: run a task's configured checks in its worktree (DESIGN.md §7.5).

The worktree is the one the task's claim records, else the one that has its branch checked out.
Its own configuration and kinds decide the commands, so a branch that changes its checks runs
them. When an autopilot run lists the task, its lane's resource values are passed as
`TASKRAIL_RESOURCE_<NAME>`; `--resource NAME=VALUE` passes a chosen pool value instead, for a lane
whose values were released, and is refused when another lane in use holds it. Run files are read,
never written.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from taskrail import branches, claims, gitutil
from taskrail.autopilot import dispatch, runs
from taskrail.autopilot.dispatch import ENVIRONMENT_PREFIX
from taskrail.config import load_config
from taskrail.model import Project, Task
from taskrail.project import load_project

PASSED = "passed"
FAILED = "failed"
NOT_CONFIGURED = "not-configured"


class ChecksRefused(Exception):
    """The checks cannot run; `code` is the CLI exit code to return."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code


def _claim(project: Project, task_id: str):
    try:
        return claims.read(project.config, task_id)
    except gitutil.GitError:
        return None


def worktree(project: Project, task: Task, claim) -> Path:
    """The claim's worktree when it exists, else the worktree that has the task's branch checked out.

    Under `task_branch = "current"`, else the checkout the command runs from.
    """
    if claim is not None and claim.worktree and Path(claim.worktree).is_dir():
        return Path(claim.worktree).resolve()
    if branches.is_current(project.config):  # the checkout it runs from (DESIGN.md §7.5)
        try:
            return gitutil.toplevel(project.config.root).resolve()
        except gitutil.GitError:
            return project.config.root.resolve()
    branch, _ = branches.resolve(task, project)
    try:
        found = gitutil.worktree_branches(project.config.root).get(branch) if branch else None
    except gitutil.GitError:
        found = None
    if found is None:
        recorded = "no claim records an existing worktree" if claim is None or not claim.worktree else f"its claim's worktree {claim.worktree} does not exist"
        raise ChecksRefused(f"{task.id} has no worktree to run its checks in: {recorded}, and its branch `{branch}` is not checked out in any worktree", 5)
    return found


def lane_resources(project: Project, task_id: str, claim) -> tuple[str | None, dict[str, str]]:
    """The run that lists the task — the claim's, else the newest — and its lane's resource values."""
    config = project.config
    try:
        if claim is not None and claim.run:
            run = runs.read(config, claim.run)
            if run is not None and task_id in run["tasks"]:
                return run["id"], dict(run["tasks"][task_id]["resources"])
        for run in runs.read_all(config):
            if task_id in run["tasks"]:
                return run["id"], dict(run["tasks"][task_id]["resources"])
    except gitutil.GitError:
        pass
    return None, {}


def chosen_resources(project: Project, task_id: str, pairs: list[str] | None) -> dict[str, str]:
    """`--resource NAME=VALUE` pairs, each a value of a configured pool that no other task's lane in use holds."""
    if not pairs:
        return {}
    pools = {resource.name: resource.values for resource in project.config.autopilot.resources}
    chosen: dict[str, str] = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep:
            raise ChecksRefused(f"--resource expects NAME=VALUE, got `{pair}`", 2)
        if name not in pools:
            configured = ", ".join(pools) or "none"
            raise ChecksRefused(f"--resource: `{name}` is not an [[autopilot.resource]] (configured: {configured})", 2)
        if value not in pools[name]:
            raise ChecksRefused(f"--resource: `{value}` is not a value of {name} ({', '.join(pools[name])})", 2)
        if name in chosen:
            raise ChecksRefused(f"--resource: {name} is given more than once", 2)
        chosen[name] = value
    try:
        claimed = claims.read_all(project.config)
    except gitutil.GitError:
        claimed = {}
    preview = dispatch.next_lanes(project, None, claimed)  # read-only: no run, no lock, nothing written
    held = {resource["name"]: resource["held"] for resource in preview["resources"]}
    for name, value in chosen.items():
        holder = held.get(name, {}).get(value)
        if holder is not None and holder != task_id:
            raise ChecksRefused(f"--resource {name}={value}: the lane of {holder} holds it; choose a value no lane in use holds", 4)
    return chosen


def _worktree_project(project: Project, path: Path) -> Project:
    """The worktree's own project when it has a configuration, else the caller's."""
    if path.resolve() == project.config.root.resolve() or not (path / ".taskrail" / "config.toml").is_file():
        return project
    own, _ = load_project(load_config(path))
    return own


def select(project: Project, task: Task, stage: str | None, names: list[str] | None) -> list[str]:
    """Check names in stage order, each once: every applying stage's, or `stage`'s, narrowed to `names`."""
    kind = project.kinds.get(task.kind)
    if kind is None:
        raise ChecksRefused(f"kind `{task.kind}` of {task.id} is not defined", 2)
    if stage is not None:
        chosen = [s for s in kind.stages if s.name == stage]
        if not chosen:
            raise ChecksRefused(f"--stage: `{stage}` is not a stage of kind {kind.name} ({', '.join(s.name for s in kind.stages)})", 2)
    else:
        chosen = [s for s in kind.stages if s.applies(task)]
    selected = list(dict.fromkeys(name for s in chosen for name in s.checks))
    if names:
        unknown = [name for name in dict.fromkeys(names) if name not in selected]
        if unknown:
            where = f"stage {stage}" if stage else f"the stages of kind {kind.name}"
            raise ChecksRefused(f"--check: {', '.join(f'`{n}`' for n in unknown)} is not a check of {where} ({', '.join(selected) or 'none'})", 2)
        selected = [name for name in selected if name in names]
    return selected


def run_checks(project: Project, task: Task, stage: str | None, names: list[str] | None, capture: bool, resource_pairs: list[str] | None = None) -> dict:
    """Run the selected checks; with `capture`, each check's output goes into the result instead of the terminal.

    `resource_pairs` are `--resource NAME=VALUE` values, each replacing that name's lane value.
    """
    claim = _claim(project, task.id)
    path = worktree(project, task, claim)
    own = _worktree_project(project, path)
    own_task = own.task(task.id) or task
    selected = select(own, own_task, stage, names)
    chosen = chosen_resources(project, task.id, resource_pairs)
    run_id, resources = lane_resources(project, task.id, claim)
    resources.update(chosen)
    environment = {f"{ENVIRONMENT_PREFIX}{name}": value for name, value in resources.items()}
    results = []
    for name in selected:
        command = own.config.checks.get(name)
        if command is None:
            results.append({"name": name, "command": None, "status": NOT_CONFIGURED, "exit": None, "output": None})
            if not capture:
                print(f"== {name}: not configured", flush=True)
            continue
        if not capture:
            print(f"== {name}: {command}", flush=True)
        process = subprocess.run(
            command,
            shell=True,
            cwd=path,
            env={**os.environ, **environment},
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            text=True,
            errors="replace",
        )
        sys.stdout.flush()
        results.append(
            {
                "name": name,
                "command": command,
                "status": PASSED if process.returncode == 0 else FAILED,
                "exit": process.returncode,
                "output": process.stdout if capture else None,
            }
        )
    return {
        "id": task.id,
        "worktree": str(path),
        "run": run_id,
        "resources": resources,
        "environment": environment,
        "chosen": chosen,
        "stage": stage,
        "checks": results,
        "passed": all(result["status"] != FAILED for result in results),
    }


def summary(result: dict) -> str:
    lines = []
    for check in result["checks"]:
        if check["status"] == PASSED:
            lines.append(f"passed {check['name']}")
        elif check["status"] == FAILED:
            lines.append(f"failed {check['name']} (exit {check['exit']})")
        else:
            lines.append(f"not configured {check['name']}")
    if not result["checks"]:
        lines.append(f"no checks for {result['id']}" + (f" at stage {result['stage']}" if result["stage"] else ""))
    lines.append(f"{result['id']} in {result['worktree']}: " + ("passed" if result["passed"] else "failed"))
    return "\n".join(lines)
