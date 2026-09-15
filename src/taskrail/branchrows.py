"""Rows a checkout lacks, read from their task's own branch (DESIGN.md §12.1; T071).

A task created with `taskrail new --workspace` has its row only on its branch until that branch is
merged, so a checkout of the mainline, or another task's worktree, does not see it. The autopilot
commands and `taskrail checks` still find such a task: on the branch of its live claim, else on its
recorded branch (§6.4), reading the row from the worktree that has that branch checked out, else from
the local branch tip, else from `<remote>/<branch>`.

A row found this way reads `⬜` in the checkout, which does not close it; whether it is done or
discarded on its branch, or merged, comes from the refs as for every task.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from taskrail import branches, gitutil, stack
from taskrail.backlog import load_backlog
from taskrail.ids import _epic_files
from taskrail.model import Epic, Project, Status, Task

CACHE_KEY = "branch_rows"  # task ID -> (Task, Epic, source) or None
ADOPTED_ORDER = 10**9  # adopted rows sort after every row of the checkout at equal points


def branch_of(project: Project, task_id: str, claimed: dict | None) -> str | None:
    """The branch a task absent from the checkout lives on: its live claim's, else its recorded one."""
    claim = (claimed or {}).get(task_id)
    if claim is not None and claim.branch:
        return claim.branch
    record = branches.read(project.config, task_id)
    return record.branch if record else None


def _sources(project: Project, branch: str, remote: str) -> list[tuple[str, object]]:
    """Where the row may be read, in order: the branch's worktree, its local tip, its remote tip."""
    root = project.config.root
    found: list[tuple[str, object]] = []
    try:
        worktree = gitutil.worktree_branches(root).get(branch)
        refs = set(gitutil.refs(root, "refs/heads")) | set(gitutil.refs(root, "refs/remotes"))
    except gitutil.GitError:
        return []
    if worktree is not None and worktree.resolve() != root.resolve():
        found.append((str(worktree), worktree))
    for ref in (f"refs/heads/{branch}", f"refs/remotes/{remote}/{branch}"):
        if ref in refs:
            found.append((ref.removeprefix("refs/heads/").removeprefix("refs/remotes/"), ref))
    return found


def _overlay(project: Project, backlog_file: str, source: object) -> dict[str, str] | None:
    """The backlog's main file and epic files as they are at a worktree path or a ref."""
    root = project.config.root
    if isinstance(source, Path):
        def read(relative: str) -> str | None:
            try:
                return (source / relative).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return None

        main = read(backlog_file)
        if main is None:
            return None
        overlay = {backlog_file: main}
        for path in _epic_files(main):
            overlay[path] = read(path) or ""
        return overlay
    try:
        main = gitutil.read_blobs(root, [f"{source}:{backlog_file}"]).get(f"{source}:{backlog_file}")
        if main is None:
            return None
        epic_files = _epic_files(main)
        blobs = gitutil.read_blobs(root, [f"{source}:{path}" for path in epic_files])
    except gitutil.GitError:
        return None
    overlay = {backlog_file: main}
    for path in epic_files:
        overlay[path] = blobs.get(f"{source}:{path}") or ""
    return overlay


def _lookup(project: Project, task_id: str, claimed: dict | None) -> tuple[Task, Epic, str] | None:
    backlog = project.backlog_for_id(task_id)
    branch = branch_of(project, task_id, claimed)
    if backlog is None or not branch:
        return None
    from taskrail.review import resolve_remote

    config = project.config
    try:
        remote = resolve_remote(config.root, backlog.config.mainline, config.review.remote).name
    except gitutil.GitError:
        return None
    for name, source in _sources(project, branch, remote):
        overlay = _overlay(project, backlog.config.file, source)
        if overlay is None:
            continue
        loaded, _ = load_backlog(config, backlog.config, [ADOPTED_ORDER], overlay)
        for epic in loaded.epics:
            task = next((task for task in epic.tasks if task.id == task_id), None)
            if task is not None:
                pending = dataclasses.replace(task, status=Status.PENDING, status_raw=Status.PENDING.value)
                return pending, epic, name
    return None


def find(project: Project, task_id: str, claimed: dict | None = None) -> Task | None:
    """The task: the checkout's row, else the row on its branch; None when neither exists."""
    task = project.task(task_id)
    if task is not None:
        return task
    return adopt(project, [task_id], claimed).get(task_id)


def adopt(project: Project, task_ids, claimed: dict | None = None) -> dict[str, Task]:
    """Add to the loaded project every task among `task_ids` whose row only its branch holds.

    Returns the tasks adopted by this call or an earlier one, by ID. Values cached from the rows —
    the branch scan and the autopilot's mainline reads — are dropped when a row is added.
    """
    cache = project.cache.setdefault(CACHE_KEY, {})
    adopted: dict[str, Task] = {}
    for task_id in dict.fromkeys(task_ids):
        if task_id in cache:
            if cache[task_id] is not None:
                adopted[task_id] = cache[task_id]
            continue
        if project.task(task_id) is not None:
            continue
        found = _lookup(project, task_id, claimed)
        cache[task_id] = None
        if found is None:
            continue
        task, epic, _ = found
        backlog = next(b for b in project.backlogs if b.config.name == task.backlog)
        target = next((e for e in backlog.epics if e.id == epic.id), None)
        if target is None:
            target = dataclasses.replace(epic, tasks=[])
            backlog.epics.append(target)
        target.tasks.append(task)
        cache[task_id] = task
        adopted[task_id] = task
        _forget_derived(project)
    return adopted


def _forget_derived(project: Project) -> None:
    """Drop values derived from the project's rows, so they are computed again with the adopted ones."""
    project.cache.pop(stack.CACHE_KEY, None)
    for key in [key for key in project.cache if key.startswith("autopilot_")]:
        project.cache.pop(key)
