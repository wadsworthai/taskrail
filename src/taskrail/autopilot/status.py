"""The state of every task in the autopilot's runs, derived from git, claims and run files (DESIGN.md §12.1, §12.4)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from taskrail import claims as claims_module
from taskrail import archive, branches, branchrows, gitutil, stack
from taskrail.autopilot import escalation
from taskrail.autopilot import runs as runs_module
from taskrail.claims import Claim
from taskrail.model import Project, Status, Task
from taskrail.query import base_dict, blocked_by
from taskrail.review import REOPENS, resolve_remote
from taskrail.templates import render

STATES = (
    "pending",
    "dispatched",
    "running",
    "gate",
    "escalated",
    "parked",
    "failed",
    "done-branch",
    "handed-off",
    "done-merged",
    "discarded-branch",
    "discarded",
)
OCCUPYING = ("running", "gate", "dispatched")  # states that use a lane and hold resources; `escalated` waits for a human (T105)
RECORDED = ("failed", "escalated", "parked", "gate")  # lane states only the run file knows
WITH_BRANCH = ("running", "gate", "escalated", "parked", "failed", "done-branch", "handed-off", "discarded-branch")  # states whose files count
WAITING = ("done-branch", "discarded-branch")  # a branch that waits for hand-off (T053, T065)
MERGED_KEY = "autopilot_done_on_mainline"
MAINLINE_KEY = "autopilot_closed_on_mainline"
RECORDED_KEY = "autopilot_recorded_merges"
WORKTREES_KEY = "autopilot_worktree_branches"


def done_on_mainline(project: Project) -> set[str]:
    """Tasks whose row is ✅ on the local mainline or its remote-tracking branch; the checkout's rows outside git."""
    if MERGED_KEY not in project.cache:
        # A merge `autopilot merged` proved counts too, while its commit stays on a mainline.
        project.cache[MERGED_KEY] = _on_mainline(project, Status.DONE) | _recorded(project, Status.DONE)
    return project.cache[MERGED_KEY]


def discarded_on_mainline(project: Project) -> set[str]:
    """Tasks whose row is ❌ on the local mainline or its remote-tracking branch; the checkout's rows outside git (T062).

    A proven merge of a branch the task was discarded on counts too, as for `done_on_mainline` (T067).
    """
    return _on_mainline(project, Status.DISCARDED) | _recorded(project, Status.DISCARDED)


def _recorded(project: Project, status: Status) -> set[str]:
    """Tasks whose newest recorded merge still on a mainline closed them with `status` (T067)."""
    if RECORDED_KEY not in project.cache:
        from taskrail.autopilot.merged import recorded_merges  # imported here: merged imports this module

        project.cache[RECORDED_KEY] = recorded_merges(project)
    return {task_id for task_id, closed in project.cache[RECORDED_KEY].items() if closed == status.label}


def _on_mainline(project: Project, status: Status) -> set[str]:
    """Tasks whose row has `status` on a mainline ref, read once per project for both statuses.

    A row on one mainline ref does not count when the other has a `Reopens: <ID>` commit it lacks (T064).
    """
    if MAINLINE_KEY not in project.cache:
        config = project.config
        root = config.root
        rows: dict[Status, set[str]] = {Status.DONE: set(), Status.DISCARDED: set()}
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
                archived = [task for task in archive.archived_tasks(project).values() if task.backlog == backlog.config.name]
                for closed, found in rows.items():
                    found |= {task.id for task in [*backlog.tasks, *archived] if task.status is closed}
                continue
            statuses = stack._read_statuses(project, backlog.config.file, refs)
            # A row `taskrail archive` moved out still counts where the mainline's archive holds it (T121).
            for ref, archived in stack._read_statuses(project, backlog.config.archive_path, refs).items():
                for task_id, cell in archived.items():
                    statuses[ref].setdefault(task_id, cell)
            reopened = {ref: _reopened_elsewhere(root, ref, refs) for ref in refs}
            for closed, found in rows.items():
                found |= {
                    task_id for ref in refs for task_id, cell in statuses[ref].items() if cell == closed.value and task_id not in reopened[ref]
                }
        project.cache[MAINLINE_KEY] = rows
    return project.cache[MAINLINE_KEY][status]


def _reopened_elsewhere(root: Path, ref: str, refs: list[str]) -> set[str]:
    """Tasks with a `Reopens: <ID>` commit on another mainline ref that `ref` lacks: a closed row on `ref` predates it (T064)."""
    others = [other for other in refs if other != ref]
    if not others:
        return set()
    log = gitutil.run(root, "log", "--format=%B", "--grep=^Reopens:", *others, "--not", ref, check=False).stdout
    return set(REOPENS.findall(log))


def _closing(task: Task, project: Project) -> bool:
    """Whether `done` or `discard` wrote the task's ✅ or ❌ in the worktree of its branch and it is not committed yet (T054, T062)."""
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
    return stack._statuses(text, project.config.column_aliases).get(task.id) in (Status.DONE.value, Status.DISCARDED.value)


def task_state(task: Task, project: Project, run: dict, claim: Claim | None, now: datetime | None = None) -> str:
    if task.id in done_on_mainline(project):
        return "done-merged"
    if task.status is Status.DISCARDED or task.id in discarded_on_mainline(project):
        return "discarded"
    if task.id in stack.done_on_branch(project):
        return "handed-off" if task.id in run["handed_off"] else "done-branch"
    if task.id in stack.discarded_on_branch(project):
        return "discarded-branch"  # uses no lane and frees its place (T062); keeps this state once handed off (T065)
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


def current_blobs(root: Path, worktree: str | None, head: str | None, paths: list[str]) -> dict[str, str | None]:
    """The blob ID of each path's current content, as `approve-governing` records it (T059).

    From the file in the lane's worktree when that directory exists, so uncommitted content counts;
    else from the branch tip. A path absent from where it is read is `None`.
    """
    blobs: dict[str, str | None] = {path: None for path in paths}
    if not paths:
        return blobs
    if worktree and Path(worktree).is_dir():
        present = [path for path in paths if (Path(worktree) / path).is_file()]
        if present:
            result = gitutil.run(Path(worktree), "hash-object", "--", *present, check=False)
            if result.returncode == 0:
                blobs.update(zip(present, result.stdout.split()))
        return blobs
    if head:
        listing = gitutil.run(root, "ls-tree", "-r", "-z", head, "--", *paths, check=False).stdout
        for entry in listing.split("\0"):
            meta, _, path = entry.partition("\t")
            parts = meta.split()
            if path in blobs and len(parts) == 3 and parts[1] == "blob":
                blobs[path] = parts[2]
    return blobs


def _approved(root: Path, lane: dict, worktree: str | None, head: str | None, touched: set[str]) -> list[str]:
    """The touched files whose content still has the blob ID the lane's approval recorded."""
    recorded = lane.get("governing_approved")
    if not isinstance(recorded, dict):
        return []
    candidates = sorted(path for path in recorded if path in touched)
    current = current_blobs(root, worktree, head, candidates)
    return [path for path in candidates if current[path] == recorded[path]]


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
        "holds_lane": state in OCCUPYING,  # false for a task that keeps its workspace but no lane (T105)
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
        "governing_approved": _approved(root, lane, worktree, head, touched),
    }


def _closed_time(project: Project, task_id: str) -> int:
    """When a task was closed on its branch: the author time of its done or discard commit (T053, T065).

    That commit is the newest first-parent commit on the task branch — the local one, else its
    remote copy — and off its mainline that turns the row ✅, or ❌ for a task discarded there. A
    rebase, an amend or a later commit on the branch leaves its author time alone. Without one, the
    branch tip's author time.
    """
    closed, status = stack.done_on_branch(project).get(task_id), Status.DONE.value
    if closed is None:
        closed, status = stack.discarded_on_branch(project).get(task_id), Status.DISCARDED.value
    backlog = project.backlog_for_id(task_id)
    if closed is None or backlog is None:
        return 0
    root = project.config.root
    branch = closed.refs[0]
    mainline = backlog.config.mainline
    mainline_refs = [ref for ref in (f"refs/heads/{mainline}", f"refs/remotes/{closed.remote}/{mainline}") if _resolves(root, ref)]
    log = gitutil.run(root, "log", "--first-parent", "--format=%H %at", branch, "--not", *mainline_refs, "--", check=False).stdout
    commits = [(sha, int(at)) for sha, at in (line.split() for line in log.splitlines() if line.strip())]
    if commits:
        revisions = [sha for sha, _ in commits] + [f"{commits[-1][0]}^"]
        statuses = stack._read_statuses(project, backlog.config.file, revisions)
        for index, (sha, at) in enumerate(commits):
            if statuses[sha].get(task_id) == status and statuses[revisions[index + 1]].get(task_id) != status:
                return at
    tip = gitutil.run(root, "log", "-1", "--format=%at", branch, "--", check=False).stdout.strip()
    return int(tip) if tip.isdigit() else 0


def _handoff(run: dict, rows: list[dict], project: Project) -> dict:
    by_id = {row["id"]: row for row in rows}
    # A branch discarded on it keeps reading `discarded-branch` once handed off; the hand-off order tells them apart (T065).
    in_review = next((task_id for task_id in run["handed_off"] if by_id.get(task_id, {}).get("state") in ("handed-off", "discarded-branch")), None)
    waiting = sorted(
        (row for row in rows if row["state"] in WAITING and not (row["state"] == "discarded-branch" and row["id"] in run["handed_off"])),
        key=lambda row: (_closed_time(project, row["id"]), row["id"]),
    )
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
            row.update(escalation.flags(row["kind"], row["state"], row["gate"], row["touched"], config.autopilot, row["governing_approved"]))


def run_status(project: Project, run: dict, claimed: dict[str, Claim], now: datetime | None = None, worktrees: dict | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    config = project.config
    if worktrees is None:
        worktrees = gitutil.worktree_branches(config.root)
    members = runs_module.members(run, claimed)
    branchrows.adopt(project, members, claimed)  # a member whose row only its branch holds reads as in any checkout (T071)
    rows = []
    for task_id in members:
        task = project.task(task_id) or archive.archived_task(project, task_id)  # a member `taskrail archive` moved out (T121)
        if task is None:
            rows.append({"id": task_id, "title": None, "kind": None, "state": None, "problem": "not in the backlog"})
            continue
        claim = claimed.get(task_id)
        if claim is not None and task_id not in run["tasks"] and claim.run != run["id"]:
            claim = None  # a named task claimed outside this run is not one of its lanes (T071)
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
        "named": list(run.get("named") or []),
        "closed": run.get("closed"),
        "complete": merged >= run["count"] > 0,
        "done_merged": merged,
        "tasks": rows,
        "handoff": _handoff(run, [row for row in rows if row["state"] is not None], project),
        "decisions": run["decisions"],
    }


def status(project: Project, runs: list[dict], claimed: dict[str, Claim], now: datetime | None = None) -> dict:
    branchrows.adopt(project, [task_id for run in runs for task_id in runs_module.members(run, claimed)], claimed)  # before any state is derived (T071)
    worktrees = gitutil.worktree_branches(project.config.root) if runs else {}
    reports = [run_status(project, run, claimed, now, worktrees) for run in runs]
    touched_by: dict[str, set[str]] = {}
    for report in reports:
        for row in report["tasks"]:
            for path in row.get("touched") or []:
                touched_by.setdefault(path, set()).add(row["id"])
    shared = {path: sorted(task_ids) for path, task_ids in sorted(touched_by.items()) if len(task_ids) > 1}
    known = _known_conflicts(project) if shared else {}
    overlaps, known_overlaps = {}, {}
    for path, task_ids in shared.items():
        kind = known.get(path) or ("changelog" if Path(path).name.lower() == "changelog.md" else None)
        if kind is None:
            overlaps[path] = task_ids
        else:
            known_overlaps[path] = {"class": kind, "tasks": task_ids}
    return {"runs": reports, "overlaps": overlaps, "known_overlaps": known_overlaps}


def _known_conflicts(project: Project) -> dict[str, str]:
    """Paths of the known conflict classes (§12.8) by class; a file created only on lane branches
    counts as `changelog` by its name, and an unreadable install manifest gives no `installed` path (T051)."""
    from taskrail import install, mergedriver
    from taskrail.issues import ConfigError

    known = mergedriver.known_conflict_paths(project)
    try:
        manifest = install.read_manifest(project.config.root)
    except ConfigError:
        return known
    files = manifest.get("files")
    for path in [install.MANIFEST, *(files if isinstance(files, dict) else [])]:
        known.setdefault(path, "installed")
    return known
