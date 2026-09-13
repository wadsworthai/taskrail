"""Derived task state and ordering."""

from __future__ import annotations

from taskrail import gitutil, stack
from taskrail.model import Project, Status, Task
from taskrail.templates import render

STATES = ("pending", "claimed", "blocked", "done-branch", "done", "discarded")


def unmerged_dependencies(task: Task, project: Project) -> list[str]:
    """Dependencies finished on their own branch but not merged into their mainline, in listed order."""
    done = stack.done_on_branch(project)
    return list(dict.fromkeys(d for d in task.depends_on if d in done))


def blocked_by(task: Task, project: Project) -> list[str]:
    """Dependencies that are not done yet (missing ones count as blocking).

    One dependency done only on its unmerged branch does not block: the task branches from it.
    Two or more such dependencies all block.
    """
    unmerged = unmerged_dependencies(task, project)
    blocking = []
    for dependency in task.depends_on:
        if dependency in unmerged:
            if len(unmerged) > 1:
                blocking.append(dependency)
            continue
        target = project.task(dependency)
        if target is None or target.status is not Status.DONE:
            blocking.append(dependency)
    return blocking


def state(task: Task, project: Project, claimed: dict | None = None) -> str:
    if task.status is Status.DONE:
        return "done"
    if task.status is Status.DISCARDED:
        return "discarded"
    if task.id in stack.done_on_branch(project):
        return "done-branch"
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


def base_dict(task: Task, project: Project) -> dict | None:
    """Where a task branch should start.

    The further-ahead of the local and remote mainline; or, when exactly one dependency is done
    only on its unmerged branch, the further-ahead of that branch's local and remote copies.
    """
    from taskrail.review import _sha, choose_base, resolve_remote

    backlog = project.config.backlog(task.backlog)
    mainline = backlog.mainline if backlog else None
    if not mainline:
        return None
    root = project.config.root
    try:
        gitutil.common_dir(root)
        remote = resolve_remote(root, mainline, project.config.review.remote)
        unmerged = unmerged_dependencies(task, project)
        dependency = None
        if len(unmerged) > 1:
            onto, diverged = None, False
            reason = f"{', '.join(unmerged)} are done only on unmerged branches; wait until all but one are merged into {mainline}"
        elif unmerged:
            dependency = unmerged[0]
            done = stack.done_on_branch(project)[dependency]
            base = choose_base(root, done.remote, done.branch)
            onto, diverged = base.onto, base.diverged
            reason = f"{dependency} is done on {done.branch} but not merged into {mainline}: {base.reason}"
        else:
            base = choose_base(root, remote.name, mainline)
            onto, diverged, reason = base.onto, base.diverged, base.reason
        commit = _sha(root, onto) if onto else None
    except gitutil.GitError:
        return None
    return {
        "onto": onto,
        "diverged": diverged,
        "reason": reason,
        "remote": remote.name,
        "remote_source": remote.source,
        "commit": commit,
        "dependency": dependency,
    }


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
        "base": base_dict(task, project),
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
