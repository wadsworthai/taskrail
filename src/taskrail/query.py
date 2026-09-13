"""Derived task state and ordering."""

from __future__ import annotations

from taskrail.model import Project, Status, Task

STATES = ("pending", "blocked", "done", "discarded")


def blocked_by(task: Task, project: Project) -> list[str]:
    """Dependencies that are not done yet (missing ones count as blocking)."""
    blocking = []
    for dependency in task.depends_on:
        target = project.task(dependency)
        if target is None or target.status is not Status.DONE:
            blocking.append(dependency)
    return blocking


def state(task: Task, project: Project) -> str:
    if task.status is Status.DONE:
        return "done"
    if task.status is Status.DISCARDED:
        return "discarded"
    return "blocked" if blocked_by(task, project) else "pending"


def is_eligible(task: Task, project: Project) -> bool:
    return task.status is Status.PENDING and not blocked_by(task, project)


def order_key(task: Task) -> tuple[int, int]:
    """Points ascending (unestimated last), then position in the backlog files."""
    return (task.points if task.points is not None else 10**9, task.order)


def eligible(project: Project, backlog: str | None = None) -> list[Task]:
    tasks = [t for t in project.tasks if is_eligible(t, project) and (backlog is None or t.backlog == backlog)]
    return sorted(tasks, key=order_key)


def task_dict(task: Task, project: Project) -> dict:
    kind = project.kinds.get(task.kind)
    return {
        "id": task.id,
        "backlog": task.backlog,
        "epic": task.epic,
        "status": task.status.label if task.status else None,
        "state": state(task, project),
        "kind": task.kind,
        "points": task.points,
        "depends_on": task.depends_on,
        "blocked_by": blocked_by(task, project) if task.status is Status.PENDING else [],
        "title": task.title,
        "description": task.description,
        "columns": task.columns,
        "skill": kind.skill_for(task) if kind else None,
        "file": task.file,
        "line": task.line,
    }
