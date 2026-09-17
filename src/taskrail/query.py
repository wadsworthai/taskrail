"""Derived task state and ordering."""

from __future__ import annotations

import os
from pathlib import Path

from taskrail import branches, gitutil, stack
from taskrail.model import Project, Status, Task
from taskrail.templates import render

STATES = ("pending", "claimed", "blocked", "done-branch", "discarded-branch", "done", "discarded")


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
    if task.id in stack.discarded_on_branch(project):
        return "discarded-branch"
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
    if branches.is_current(project.config):  # no workspace to create and nothing to rebase onto
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
        row = row_on_base(task, project, onto, remote.name) if onto else None
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
        "row": row,
    }


ROWS_CACHE_KEY = "rows_at_base"
REFS_CACHE_KEY = "branch_refs"


def row_on_base(task: Task, project: Project, onto: str, remote: str) -> str:
    """Where a task's row is relative to its base (T070).

    `on-base` when the backlog's files at `onto` have a row with the task's ID; otherwise
    `on-branch` when the task's branch exists locally or as `<remote>/<branch>`, and `missing` when
    it does not: only this checkout has the row, so a workspace created from `onto` would lack it.
    Each backlog is read once per distinct `onto`, cached per project.
    """
    backlog = project.config.backlog(task.backlog)
    rows = project.cache.setdefault(ROWS_CACHE_KEY, {})
    key = (backlog.file, onto)
    if key not in rows:
        rows[key] = set(stack._read_statuses(project, backlog.file, [onto])[onto])
    if task.id in rows[key]:
        return "on-base"
    if REFS_CACHE_KEY not in project.cache:
        root = project.config.root
        project.cache[REFS_CACHE_KEY] = set(gitutil.refs(root, "refs/heads")) | set(gitutil.refs(root, "refs/remotes"))
    branch = branches.task_branch(task, project)
    existing = project.cache[REFS_CACHE_KEY]
    if branch and (f"refs/heads/{branch}" in existing or f"refs/remotes/{remote}/{branch}" in existing):
        return "on-branch"
    return "missing"


def _checked_out(project: Project) -> dict[str, Path]:
    if "worktree_branches" not in project.cache:
        try:
            project.cache["worktree_branches"] = gitutil.worktree_branches(project.config.root)
        except gitutil.GitError:
            project.cache["worktree_branches"] = {}
    return project.cache["worktree_branches"]


def main_checkout(project: Project) -> Path:
    """The clone's worktree base, which task worktree paths are read against and created under (T072, T073).

    The main worktree, or, in a bare repository, the directory holding it (T075).
    """
    if "main_worktree" not in project.cache:
        try:
            project.cache["main_worktree"] = gitutil.main_worktree(project.config.root)
        except gitutil.GitError:
            project.cache["main_worktree"] = project.config.root.resolve()
    return project.cache["main_worktree"]


def worktree_path(branch: str | None, project: Project) -> str | None:
    """Where the task's worktree is: the one that has its branch checked out, else where it would go.

    Relative to the clone's worktree base (`main_checkout`, reported as `worktree_base`), whichever of
    its checkouts runs the command (T072, T075): one outside it gets `..` segments, and one not created
    yet is `<worktree_dir>/<branch>`.
    """
    config = project.config
    if not branch or config.worktree != "required":
        return None
    path = _checked_out(project).get(branch)
    if path is None:
        return f"{config.worktree_dir}/{branch}"
    try:
        return Path(os.path.relpath(path, main_checkout(project))).as_posix()
    except ValueError:  # another drive than the main worktree's: no relative path exists
        return str(path)


def task_dict(task: Task, project: Project, claimed: dict | None = None) -> dict:
    kind = project.kinds.get(task.kind)
    claim = (claimed or {}).get(task.id)
    config = project.config
    backlog = config.backlog(task.backlog)
    branch, branch_source = branches.resolve(task, project)
    worktree = worktree_path(branch, project)
    return {
        "id": task.id,
        "backlog": task.backlog,
        "epic": task.epic,
        "status": task.status.label if task.status else None,
        "state": state(task, project, claimed),
        "task_branch": config.task_branch,
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
        "branch_source": branch_source,
        "worktree": worktree,
        "worktree_base": str(main_checkout(project)) if worktree is not None else None,
        "artifact": render(kind.artifact, task, config) if kind else None,
        "artifact_index": render(kind.artifact_index, task, config) if kind else None,
        "never_edit": list(kind.never_edit) if kind else [],
        "checks": {name: config.checks[name] for stage in kind.stages for name in stage.checks if name in config.checks}
        if kind
        else {},
        "file": task.file,
        "line": task.line,
    }
