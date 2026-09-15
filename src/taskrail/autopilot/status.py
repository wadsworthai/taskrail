"""The state of every task in the autopilot's runs, derived from git, claims and run files (DESIGN.md §12.1, §12.4)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from taskrail import claims as claims_module
from taskrail import branches, gitutil, stack
from taskrail.autopilot import escalation
from taskrail.autopilot import runs as runs_module
from taskrail.claims import Claim
from taskrail.model import Project, Status, Task
from taskrail.query import base_dict, blocked_by
from taskrail.review import resolve_remote
from taskrail.templates import render

STATES = ("pending", "dispatched", "running", "gate", "escalated", "failed", "done-branch", "handed-off", "done-merged", "discarded")
RECORDED = ("failed", "escalated", "gate")  # lane states only the run file knows
WITH_BRANCH = ("running", "gate", "escalated", "failed", "done-branch", "handed-off")  # states whose files count
MERGED_KEY = "autopilot_done_on_mainline"
WORKTREES_KEY = "autopilot_worktree_branches"


def done_on_mainline(project: Project) -> set[str]:
    """Tasks whose row is ✅ on the local mainline or its remote-tracking branch; the checkout's rows outside git."""
    if MERGED_KEY in project.cache:
        return project.cache[MERGED_KEY]
    config = project.config
    root = config.root
    merged: set[str] = set()
    try:
        gitutil.common_dir(root)
        existing = set(gitutil.refs(root, "refs/heads")) | set(gitutil.refs(root, "refs/remotes"))
    except gitutil.GitError:
        existing = None
    for backlog in project.backlogs:
        refs = []
        if existing is not None:
            mainline = backlog.config.mainline
            remote = resolve_remote(root, mainline, config.review.remote).name
            refs = [ref for ref in (f"refs/heads/{mainline}", f"refs/remotes/{remote}/{mainline}") if ref in existing]
        if not refs:
            merged |= {task.id for task in backlog.tasks if task.status is Status.DONE}
            continue
        statuses = stack._read_statuses(project, backlog.config.file, refs)
        merged |= {task_id for ref in refs for task_id, cell in statuses[ref].items() if cell == Status.DONE.value}
    from taskrail.autopilot.merged import recorded_merges  # imported here: merged imports this module

    merged |= recorded_merges(project)  # a merge `autopilot merged` proved, while its commit stays on a mainline
    project.cache[MERGED_KEY] = merged
    return merged


def _closing(task: Task, project: Project) -> bool:
    """Whether `done` wrote the task's ✅ in the worktree of its branch and it is not committed yet (T054)."""
    branch = branches.task_branch(task, project)
    if not branch:
        return False
    if WORKTREES_KEY not in project.cache:
        try:
            project.cache[WORKTREES_KEY] = gitutil.worktree_branches(project.config.root)
        except gitutil.GitError:
            project.cache[WORKTREES_KEY] = {}
    worktree = project.cache[WORKTREES_KEY].get(branch)
    if worktree is None:
        return False
    try:
        text = (worktree / task.file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return stack._statuses(text, project.config.column_aliases).get(task.id) == Status.DONE.value


def task_state(task: Task, project: Project, run: dict, claim: Claim | None, now: datetime | None = None) -> str:
    if task.id in done_on_mainline(project):
        return "done-merged"
    if task.status is Status.DISCARDED:
        return "discarded"
    if task.id in stack.done_on_branch(project):
        return "handed-off" if task.id in run["handed_off"] else "done-branch"
    lane = run["tasks"].get(task.id)
    if lane and lane["state"] in RECORDED:
        return lane["state"]
    if claim is not None or _closing(task, project):
        return "running"
    if lane and runs_module.dispatch_live(lane, project.config.claim_grace_minutes, now):
        return "dispatched"  # `autopilot next` sent it to a lane that has not claimed yet
    return "pending"


def _changed_in_worktree(worktree: str | None) -> list[str]:
    """Paths `git status` reports as changed or untracked in a worktree (not ignored ones)."""
    if not worktree or not Path(worktree).is_dir():
        return []
    result = gitutil.run(Path(worktree), "status", "--porcelain", "-z", "--untracked-files=all", check=False)
    if result.returncode != 0:
        return []
    records = result.stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        paths.append(record[3:])
        if record[0] in "RC":  # a rename or copy is followed by its original path
            if index < len(records) and records[index]:
                paths.append(records[index])
            index += 1
    return paths


def _branch_ref(root: Path, branch: str | None) -> str | None:
    if branch and gitutil.branch_exists(root, branch):
        return f"refs/heads/{branch}"
    return None


def _resolves(root: Path, ref: str | None) -> bool:
    return bool(ref) and gitutil.run(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).returncode == 0


def _fork_point(task: Task, project: Project, claim: Claim | None, head: str) -> str | None:
    """Where the task branch left its base: from the claim's recorded base, else the base `show` reports."""
    root = project.config.root
    base = (claim.base if claim else None) or {}
    onto = base.get("onto")
    if not _resolves(root, onto):
        onto = None
        if base.get("commit") and _resolves(root, base["commit"]):
            return base["commit"]
        derived = base_dict(task, project)
        onto = derived["onto"] if derived else None
    if not onto:
        return None
    return gitutil.run(root, "merge-base", head, onto, check=False).stdout.strip() or None


def _parse_time(value: str | None) -> float | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def _lane_details(task: Task, project: Project, run: dict, claim: Claim | None, state: str, worktrees: dict, now: datetime) -> dict:
    config = project.config
    root = config.root
    lane = run["tasks"].get(task.id) or {}
    branch = claim.branch if claim and claim.branch else branches.task_branch(task, project)
    checked_out = worktrees.get(branch)
    worktree = claim.worktree if claim and claim.worktree else (str(checked_out) if checked_out else None)
    head = _branch_ref(root, branch)

    changed = _changed_in_worktree(worktree) if state in WITH_BRANCH else []
    touched: set[str] = set(changed)
    if state in WITH_BRANCH and head:
        fork = _fork_point(task, project, claim, head)
        if fork:
            diff = gitutil.run(root, "diff", "--name-only", "-z", fork, head, check=False).stdout
            touched |= {path for path in diff.split("\0") if path}

    moments: list[float] = []
    if head:
        tip = gitutil.run(root, "log", "-1", "--format=%ct", head, check=False).stdout.strip()
        if tip.isdigit():
            moments.append(float(tip))
    for path in changed:
        try:
            moments.append(os.lstat(Path(worktree) / path).st_mtime)
        except OSError:
            continue  # deleted files leave no time behind
    for value in (claim.created if claim else None, lane.get("updated")):
        moment = _parse_time(value)
        if moment is not None:
            moments.append(moment)
    idle = max(0, int((now.timestamp() - max(moments)) // 60)) if moments else None
    silent = state == "running" and idle is not None and idle > config.autopilot.silent_minutes

    return {
        "handle": lane.get("handle"),
        "group": lane.get("group"),
        "reason": lane.get("reason"),
        "gate": lane.get("gate"),
        "resources": lane.get("resources") or {},
        "branch": branch,
        "worktree": worktree,
        "claim": {**claim.to_dict(), "stale": claims_module.stale_reason(config, claim)} if claim else None,
        "idle_minutes": idle,
        "silent": silent,
        "touched": sorted(touched),
    }


def _done_time(project: Project, task_id: str) -> int:
    """When a task was finished on its branch: the author time of its done commit (T053).

    The done commit is the newest first-parent commit on the task branch — the local one, else its
    remote copy — and off its mainline that turns the row ✅. A rebase, an amend or a later commit on
    the branch leaves its author time alone. Without one, the branch tip's author time.
    """
    done = stack.done_on_branch(project).get(task_id)
    backlog = project.backlog_for_id(task_id)
    if done is None or backlog is None:
        return 0
    root = project.config.root
    branch = done.refs[0]
    mainline = backlog.config.mainline
    mainline_refs = [ref for ref in (f"refs/heads/{mainline}", f"refs/remotes/{done.remote}/{mainline}") if _resolves(root, ref)]
    log = gitutil.run(root, "log", "--first-parent", "--format=%H %at", branch, "--not", *mainline_refs, "--", check=False).stdout
    commits = [(sha, int(at)) for sha, at in (line.split() for line in log.splitlines() if line.strip())]
    if commits:
        revisions = [sha for sha, _ in commits] + [f"{commits[-1][0]}^"]
        statuses = stack._read_statuses(project, backlog.config.file, revisions)
        for index, (sha, at) in enumerate(commits):
            if statuses[sha].get(task_id) == Status.DONE.value and statuses[revisions[index + 1]].get(task_id) != Status.DONE.value:
                return at
    tip = gitutil.run(root, "log", "-1", "--format=%at", branch, "--", check=False).stdout.strip()
    return int(tip) if tip.isdigit() else 0


def _handoff(run: dict, rows: list[dict], project: Project) -> dict:
    by_id = {row["id"]: row for row in rows}
    in_review = next((task_id for task_id in run["handed_off"] if by_id.get(task_id, {}).get("state") == "handed-off"), None)
    waiting = sorted((row for row in rows if row["state"] == "done-branch"), key=lambda row: (_done_time(project, row["id"]), row["id"]))
    queue: list[str] = []
    pending = list(waiting)
    while pending:
        # Dependencies first: take the earliest-finished task none of whose waiting dependencies is still unplaced.
        unplaced = {row["id"] for row in pending}
        chosen = next(
            (row for row in pending if not unplaced.intersection(project.task(row["id"]).depends_on)),
            pending[0],
        )
        queue.append(chosen["id"])
        pending.remove(chosen)
    return {
        "mode": project.config.autopilot.handoff,
        "in_review": in_review,
        "queue": queue,
        "next": None if in_review else (queue[0] if queue else None),
    }


def _flag_escalations(rows: list[dict], config) -> None:
    """Add the computed escalation reasons of §12.6 to each task row (T032)."""
    for row in rows:
        if row["state"] is not None:
            row.update(escalation.flags(row["kind"], row["state"], row["gate"], row["touched"], config.autopilot))


def run_status(project: Project, run: dict, claimed: dict[str, Claim], now: datetime | None = None, worktrees: dict | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    config = project.config
    if worktrees is None:
        worktrees = gitutil.worktree_branches(config.root)
    members = list(run["tasks"])
    members += sorted(task_id for task_id, claim in claimed.items() if claim.run == run["id"] and task_id not in run["tasks"])
    rows = []
    for task_id in members:
        task = project.task(task_id)
        if task is None:
            rows.append({"id": task_id, "title": None, "kind": None, "state": None, "problem": "not in the backlog"})
            continue
        claim = claimed.get(task_id)
        state = task_state(task, project, run, claim, now)
        rows.append(
            {
                "id": task.id,
                "title": task.title,
                "kind": task.kind,
                "state": state,
                "blocked_by": blocked_by(task, project) if state == "pending" else [],
                **_lane_details(task, project, run, claim, state, worktrees, now),
                "decisions": render(config.autopilot.decisions, task, config),
                "decisions_index": render(config.autopilot.decisions_index, task, config),
            }
        )
    _flag_escalations(rows, config)
    merged = sum(1 for row in rows if row["state"] == "done-merged")
    return {
        "id": run["id"],
        "started": run["started"],
        "owner": run["owner"],
        "count": run["count"],
        "kinds": run["kinds"],
        "closed": run.get("closed"),
        "complete": merged >= run["count"] > 0,
        "done_merged": merged,
        "tasks": rows,
        "handoff": _handoff(run, [row for row in rows if row["state"] is not None], project),
        "decisions": run["decisions"],
    }


def status(project: Project, runs: list[dict], claimed: dict[str, Claim], now: datetime | None = None) -> dict:
    worktrees = gitutil.worktree_branches(project.config.root) if runs else {}
    reports = [run_status(project, run, claimed, now, worktrees) for run in runs]
    touched_by: dict[str, set[str]] = {}
    for report in reports:
        for row in report["tasks"]:
            for path in row.get("touched") or []:
                touched_by.setdefault(path, set()).add(row["id"])
    overlaps = {path: sorted(task_ids) for path, task_ids in sorted(touched_by.items()) if len(task_ids) > 1}
    return {"runs": reports, "overlaps": overlaps}
