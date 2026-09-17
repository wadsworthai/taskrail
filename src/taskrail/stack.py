"""Tasks finished or discarded on their own branch but not merged into their mainline, read from git refs."""

from __future__ import annotations

from dataclasses import dataclass

from taskrail import branches, gitutil
from taskrail.backlog import _index, _is_task_table
from taskrail.ids import _epic_files
from taskrail.markdown import parse_sections
from taskrail.model import Project, Status, Task
from taskrail.prior import _short
from taskrail.review import REOPENS, resolve_remote

CACHE_KEY = "done_on_branch"


@dataclass(frozen=True)
class DoneOnBranch:
    task_id: str
    branch: str  # the task branch's name, without a remote
    remote: str  # the remote of the task's mainline, where its branch is pushed
    refs: tuple[str, ...]  # branch tips where the row is ✅ (❌ for `discarded_on_branch`), as short names


def _statuses(text: str, aliases) -> dict[str, str]:
    """`ID` → raw `✓` cell for every task row in one backlog file."""
    found: dict[str, str] = {}
    for section in parse_sections(text):
        for table in section.tables:
            if not _is_task_table(table, aliases):
                continue
            columns = _index(table.header, aliases)
            if "ID" not in columns or "✓" not in columns:
                continue
            for _, cells in table.rows:
                if max(columns["ID"], columns["✓"]) < len(cells):
                    found.setdefault(cells[columns["ID"]], cells[columns["✓"]])
    return found


def _read_statuses(project: Project, backlog_file: str, revisions: list[str]) -> dict[str, dict[str, str]]:
    """Task statuses in a backlog's main file and its epic files, at each revision."""
    aliases = project.config.column_aliases
    mains = gitutil.read_blobs(project.config.root, [f"{rev}:{backlog_file}" for rev in revisions])
    result: dict[str, dict[str, str]] = {}
    epic_specs: list[tuple[str, str]] = []
    for rev in revisions:
        text = mains.get(f"{rev}:{backlog_file}")
        result[rev] = _statuses(text, aliases) if text is not None else {}
        if text is not None:
            epic_specs += [(rev, f"{rev}:{path}") for path in _epic_files(text)]
    epics = gitutil.read_blobs(project.config.root, [spec for _, spec in epic_specs])
    for rev, spec in epic_specs:
        text = epics.get(spec)
        if text is not None:
            for task_id, status in _statuses(text, aliases).items():
                result[rev].setdefault(task_id, status)
    return result


def _reopened_since(root, task_id: str, tip: str, mainline_refs: list[str]) -> bool:
    """Whether a mainline ref has a `Reopens: <ID>` commit that `tip` lacks, so the ✅ there predates it."""
    if not mainline_refs:
        return False
    log = gitutil.run(root, "log", "--format=%B", "--grep=^Reopens:", *mainline_refs, "--not", tip, check=False).stdout
    return task_id in REOPENS.findall(log)


def done_on_branch(project: Project) -> dict[str, DoneOnBranch]:
    """Tasks whose row is ✅ at a tip of their task branch and on neither mainline ref. Cached per project.

    A tip whose ✅ predates a reopen on a mainline ref — a `Reopens: <ID>` commit the tip lacks — does not count.
    """
    return _cached(project)[0]


def discarded_on_branch(project: Project) -> dict[str, DoneOnBranch]:
    """Tasks whose row is ❌ at a tip of their task branch, closed (✅ or ❌) on neither mainline ref (T062).

    The same scan and reopen rule as `done_on_branch`, whose tasks it never includes: a ✅ tip wins. `refs` holds the ❌ tips.
    """
    return _cached(project)[1]


def _cached(project: Project) -> tuple[dict[str, DoneOnBranch], dict[str, DoneOnBranch]]:
    if CACHE_KEY not in project.cache:
        project.cache[CACHE_KEY] = _find(project)
    return project.cache[CACHE_KEY]


def _find(project: Project) -> tuple[dict[str, DoneOnBranch], dict[str, DoneOnBranch]]:
    config = project.config
    root = config.root
    if branches.is_current(config):  # no task has a branch of its own, so none is closed on one (DESIGN.md §6.4)
        return {}, {}
    try:
        gitutil.common_dir(root)
        existing = set(gitutil.refs(root, "refs/heads")) | set(gitutil.refs(root, "refs/remotes"))
    except gitutil.GitError:
        return {}, {}

    found: dict[str, DoneOnBranch] = {}
    discarded: dict[str, DoneOnBranch] = {}
    closed_values = (Status.DONE.value, Status.DISCARDED.value)
    for backlog in project.backlogs:
        mainline = backlog.config.mainline
        remote = resolve_remote(root, mainline, config.review.remote).name
        candidates: dict[str, tuple[Task, str, list[str]]] = {}
        for task in backlog.tasks:
            branch = branches.task_branch(task, project)
            if not branch:
                continue
            refs = [ref for ref in (f"refs/heads/{branch}", f"refs/remotes/{remote}/{branch}") if ref in existing]
            if refs:
                candidates[task.id] = (task, branch, refs)
        if not candidates:
            continue
        mainline_refs = [ref for ref in (f"refs/heads/{mainline}", f"refs/remotes/{remote}/{mainline}") if ref in existing]
        revisions = sorted({ref for _, _, refs in candidates.values() for ref in refs} | set(mainline_refs))
        statuses = _read_statuses(project, backlog.config.file, revisions)
        merged = {task_id for ref in mainline_refs for task_id, status in statuses[ref].items() if status == Status.DONE.value}
        closed = {task_id for ref in mainline_refs for task_id, status in statuses[ref].items() if status in closed_values}

        def tips(task_id: str, refs: list[str], value: str) -> tuple[str, ...]:
            return tuple(
                _short(ref) for ref in refs if statuses[ref].get(task_id) == value and not _reopened_since(root, task_id, ref, mainline_refs)
            )

        for task_id, (task, branch, refs) in candidates.items():
            if task_id in merged:
                continue
            done = tips(task_id, refs, Status.DONE.value)
            if done:
                found[task_id] = DoneOnBranch(task_id, branch, remote, done)
            elif task_id not in closed:
                dropped = tips(task_id, refs, Status.DISCARDED.value)
                if dropped:
                    discarded[task_id] = DoneOnBranch(task_id, branch, remote, dropped)
    return found, discarded
