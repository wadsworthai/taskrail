"""Derived task state and ordering."""

from __future__ import annotations

from taskrail import gitutil
from taskrail.model import Project, Status, Task
from taskrail.templates import render

STATES = ("pending", "claimed", "blocked", "done", "discarded")


def blocked_by(task: Task, project: Project) -> list[str]:
    """Dependencies that are not done yet (missing ones count as blocking)."""
    blocking = []
    for dependency in task.depends_on:
        target = project.task(dependency)
        if target is None or target.status is not Status.DONE:
            blocking.append(dependency)
    return blocking


def state(task: Task, project: Project, claimed: dict | None = None) -> str:
    if task.status is Status.DONE:
        return "done"
    if task.status is Status.DISCARDED:
        return "discarded"
    if claimed and task.id in claimed:
        return "claimed"
    return "blocked" if blocked_by(task, project) else "pending"


def is_eligible(task: Task, project: Project, claimed: dict | None = None) -> bool:
    return state(task, project, claimed) == "pending"


def order_key(task: Task) -> tuple[int, int]:
    """Points ascending (unestimated last), then position in the backlog files."""
    return (task.points if task.points is not None else 10**9, task.order)


def eligible(project: Project, backlog: str | None = None, claimed: dict | None = None) -> list[Task]:
    tasks = [
        t for t in project.tasks if is_eligible(t, project, claimed) and (backlog is None or t.backlog == backlog)
    ]
    return sorted(tasks, key=order_key)


def base_dict(project: Project, mainline: str | None) -> dict | None:
    """Where a task branch should start: the further-ahead of the local and remote mainline."""
    from taskrail.review import choose_base

    if not mainline:
        return None
    try:
        gitutil.common_dir(project.config.root)
        base = choose_base(project.config.root, project.config.review.remote, mainline)
    except gitutil.GitError:
        return None
    return {"onto": base.onto, "diverged": base.diverged, "reason": base.reason}


def task_dict(task: Task, project: Project, claimed: dict | None = None) -> dict:
    kind = project.kinds.get(task.kind)
    claim = (claimed or {}).get(task.id)
    config = project.config
    backlog = config.backlog(task.backlog)
    branch = render(kind.branch, task, config) if kind else None
    return {
        "id": task.id,
        "backlog": task.backlog,
        "epic": task.epic,
        "status": task.status.label if task.status else None,
        "state": state(task, project, claimed),
        "kind": task.kind,
        "points": task.points,
        "depends_on": task.depends_on,
        "blocked_by": blocked_by(task, project) if task.status is Status.PENDING else [],
        "title": task.title,
        "description": task.description,
        "columns": task.columns,
        "skill": kind.skill_for(task) if kind else None,
        "claim": claim.to_dict() if claim else None,
        "mainline": backlog.mainline if backlog else None,
        "base": base_dict(project, backlog.mainline if backlog else None),
        "push_branch": config.push_task_branch,
        "branch": branch,
        "worktree": f"{config.worktree_dir}/{branch}" if branch and config.worktree == "required" else None,
        "artifact": render(kind.artifact, task, config) if kind else None,
        "artifact_index": render(kind.artifact_index, task, config) if kind else None,
        "never_edit": list(kind.never_edit) if kind else [],
        "checks": {name: config.checks[name] for stage in kind.stages for name in stage.checks if name in config.checks}
        if kind
        else {},
        "file": task.file,
        "line": task.line,
    }
