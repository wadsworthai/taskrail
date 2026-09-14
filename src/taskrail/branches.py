"""A task's branch: the name recorded for it, otherwise the one its kind's template renders.

Records live next to the claims, in the git common directory, so every worktree of a clone sees
them. Unlike a claim, a record outlives `done`, `release` and the deletion of the branch: `review`,
`done-branch` detection and a dependent's base still find a renamed branch afterwards.

With `[git].branch_record_remote` set, records are also pushed as `refs/taskrail/branches/<ID>`
and fetched back into `refs/taskrail/remotes/<remote>/branches/<ID>`, so other clones see them.
The resolver still reads only the local files: a fetch adopts each remote record that is later
than the local one into its file.
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
REMOTE_NAMESPACE = "refs/taskrail/branches"
RECORD_FILE = "branch.json"


@dataclass(frozen=True)
class Record:
    id: str
    branch: str
    recorded: str


def records_dir(config: Config) -> Path:
    return gitutil.common_dir(config.root) / "taskrail" / "branches"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse(text: str | None) -> Record | None:
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not isinstance(data.get("branch"), str):
        return None
    return Record(data["id"], data["branch"], str(data.get("recorded", "")))


def _load(path: Path) -> Record | None:
    try:
        return _parse(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError):
        return None


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
    """Record `branch` as the task's branch now, replacing the file atomically."""
    return _store(config, Record(task_id, branch, _now()))


def _store(config: Config, record: Record) -> Record:
    directory = records_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=f".{record.id}.", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(record), handle, indent=2)
        os.replace(temporary, directory / f"{record.id}.json")
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return record


def remote_ref(task_id: str) -> str:
    return f"{REMOTE_NAMESPACE}/{task_id}"


def _copies(remote: str) -> str:
    """Where this clone keeps its copies of `remote`'s records."""
    return f"refs/taskrail/remotes/{remote}/branches"


def _later(candidate: str, current: str) -> bool:
    try:
        return datetime.fromisoformat(candidate) > datetime.fromisoformat(current)
    except ValueError:
        return candidate > current


def _git_detail(result) -> str:
    lines = [line.strip() for line in f"{result.stdout}\n{result.stderr}".splitlines()]
    return "; ".join(line for line in lines if line and line != "Done") or f"git exited with {result.returncode}"


def fetch(config: Config) -> tuple[list[str], str | None]:
    """Fetch the mirrored records and adopt each one later than this clone's: (adopted IDs, error or None).

    Never deletes a local record. Does nothing when `branch_record_remote` is not set.
    """
    remote = config.branch_record_remote
    if not remote:
        return [], None
    root = config.root
    copies = _copies(remote)
    result = gitutil.run(root, "fetch", "--quiet", "--prune", "--no-tags", remote, f"+{REMOTE_NAMESPACE}/*:{copies}/*", check=False)
    if result.returncode != 0:
        return [], _git_detail(result)
    found = gitutil.refs(root, copies)
    blobs = gitutil.read_blobs(root, [f"{ref}:{RECORD_FILE}" for ref in found])
    adopted = []
    for ref in found:
        task_id = ref.rsplit("/", 1)[1]
        theirs = _parse(blobs.get(f"{ref}:{RECORD_FILE}"))
        if theirs is None or theirs.id != task_id:
            continue
        ours = read(config, task_id)
        if ours is None or _later(theirs.recorded, ours.recorded):
            _store(config, theirs)
            adopted.append(task_id)
    return adopted, None


def push(config: Config, record: Record) -> dict:
    """Push `record` to `branch_record_remote`, leasing on this clone's copy of the remote ref.

    Returns `name`, `ref`, `commit` (the pushed commit, or None), `pushed` and `error`; never raises
    for a rejected or failed push.
    """
    remote = config.branch_record_remote
    root = config.root
    ref = remote_ref(record.id)
    copy = f"{_copies(remote)}/{record.id}"
    expected = gitutil.run(root, "rev-parse", "--verify", "--quiet", copy, check=False).stdout.strip()
    commit = gitutil.write_file_commit(root, RECORD_FILE, json.dumps(asdict(record), indent=2), f"taskrail branch {record.id}")
    result = gitutil.run(
        root, "push", "--quiet", "--porcelain", f"--force-with-lease={ref}:{expected}", remote, f"{commit}:{ref}", check=False
    )
    if result.returncode != 0:
        return {"name": remote, "ref": ref, "commit": None, "pushed": False, "error": _git_detail(result)}
    gitutil.run(root, "update-ref", copy, commit, check=False)  # a stale copy only makes the next lease stricter
    return {"name": remote, "ref": ref, "commit": commit, "pushed": True, "error": None}


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
