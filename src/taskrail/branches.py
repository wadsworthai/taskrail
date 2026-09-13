"""A task's branch: the name recorded for it, otherwise the one its kind's template renders.

Records live next to the claims, in the git common directory, so every worktree of a clone sees
them. Unlike a claim, a record outlives `done`, `release` and the deletion of the branch: `review`,
`done-branch` detection and a dependent's base still find a renamed branch afterwards.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from taskrail import gitutil
from taskrail.config import Config
from taskrail.model import Project, Task
from taskrail.templates import render

CACHE_KEY = "branch_records"
RECORDED = "recorded"
TEMPLATE = "template"


@dataclass(frozen=True)
class Record:
    id: str
    branch: str
    recorded: str


def records_dir(config: Config) -> Path:
    return gitutil.common_dir(config.root) / "taskrail" / "branches"


def _load(path: Path) -> Record | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not isinstance(data.get("branch"), str):
        return None
    return Record(data["id"], data["branch"], str(data.get("recorded", "")))


def read(config: Config, task_id: str) -> Record | None:
    try:
        return _load(records_dir(config) / f"{task_id}.json")
    except gitutil.GitError:
        return None


def read_all(config: Config) -> dict[str, Record]:
    """Every record of this clone; none outside git."""
    try:
        directory = records_dir(config)
    except gitutil.GitError:
        return {}
    if not directory.is_dir():
        return {}
    found = {}
    for path in sorted(directory.glob("*.json")):
        loaded = _load(path)
        if loaded is not None and loaded.id == path.stem:
            found[loaded.id] = loaded
    return found


def write(config: Config, task_id: str, branch: str) -> Record:
    """Record `branch` as the task's branch, replacing the file atomically."""
    directory = records_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    new = Record(task_id, branch, datetime.now(timezone.utc).isoformat(timespec="seconds"))
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f".{task_id}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(new), handle, indent=2)
        os.replace(temporary, directory / f"{task_id}.json")
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return new


def remove(config: Config, task_id: str) -> None:
    try:
        (records_dir(config) / f"{task_id}.json").unlink(missing_ok=True)
    except gitutil.GitError:
        pass


def _records(project: Project) -> dict[str, Record]:
    if CACHE_KEY not in project.cache:
        project.cache[CACHE_KEY] = read_all(project.config)
    return project.cache[CACHE_KEY]


def forget_cache(project: Project) -> None:
    project.cache.pop(CACHE_KEY, None)


def template_branch(task: Task, project: Project) -> str | None:
    kind = project.kinds.get(task.kind)
    return render(kind.branch, task, project.config) if kind else None


def resolve(task: Task, project: Project) -> tuple[str | None, str]:
    """The task's branch and where it comes from: `recorded` or `template`."""
    found = _records(project).get(task.id)
    if found is not None:
        return found.branch, RECORDED
    return template_branch(task, project), TEMPLATE


def task_branch(task: Task, project: Project) -> str | None:
    """The one lookup of a task's branch; every command goes through it."""
    return resolve(task, project)[0]


def invalid_name(project: Project, name: str) -> str | None:
    """Why `name` cannot be a task branch, or None when it can."""
    result = gitutil.run(project.config.root, "check-ref-format", "--branch", name, check=False)
    if result.returncode != 0 or result.stdout.strip() != name:
        return f"`{name}` is not a valid branch name"
    mainlines = {backlog.mainline for backlog in project.config.backlogs}
    if name in mainlines:
        return f"`{name}` is a mainline, not a task branch"
    return None


def owner_of(project: Project, name: str, except_id: str | None = None) -> str | None:
    """The ID of another task whose branch is `name`.

    Records count even for a task whose row is not in this checkout yet, such as one created
    with `new --workspace`, whose row lives only on its own branch.
    """
    for found in _records(project).values():
        if found.id != except_id and found.branch == name:
            return found.id
    for task in project.tasks:
        if task.id != except_id and task_branch(task, project) == name:
            return task.id
    return None
