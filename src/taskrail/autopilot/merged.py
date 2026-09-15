"""`taskrail autopilot merged`: detect a merge by content, record it, clean up, and list stacked dependents (DESIGN.md §12.8).

Pull requests are squash-merged, so ancestry alone sees nothing. After one `git fetch --prune`, a
finished task branch counts as merged when the first of these holds against the mainline, `M`
being their merge-base: the head is an ancestor; a first-parent commit since `M` has the head's
tree; a first-parent commit since `M` has the patch-id of `git diff M <head>`; or `git merge-tree`
of the head into the mainline changes nothing. Only a head whose row is `✅` or `❌` is checked (T067).
The row on the mainline and an `(ID)` title are reported as confirmations and never prove a merge.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from taskrail import branches, branchrows, claims, gitutil
from taskrail.autopilot import runs
from taskrail.autopilot import status as status_module
from taskrail.cli import (
    EXIT_CONFLICT,
    EXIT_INVALID,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_REFUSED,
    EXIT_USAGE,
    _emit,
    _load,
    _local_claims,
    _refuse_if_invalid,
)
from taskrail.model import Project, Status, Task
from taskrail.query import base_dict
from taskrail.review import _is_ancestor, _sha, choose_base, resolve_remote
from taskrail.stack import _read_statuses

CHECKS = ("ancestor", "tree", "patch-id", "merge-tree")


# Detection


def _tree(root: Path, rev: str) -> str | None:
    return _sha_of(root, f"{rev}^{{tree}}")


def _sha_of(root: Path, spec: str) -> str | None:
    result = gitutil.run(root, "rev-parse", "--verify", "--quiet", spec, check=False)
    return result.stdout.strip() or None


def _stop(*processes: subprocess.Popen) -> None:
    for process in processes:
        if process.poll() is None:
            process.kill()
        process.wait()


def _branch_patch_id(root: Path, base: str, head: str) -> str | None:
    diff = subprocess.Popen(["git", "diff", "--no-color", "--no-ext-diff", base, head], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    patch = subprocess.run(["git", "patch-id", "--stable"], cwd=root, stdin=diff.stdout, capture_output=True)
    diff.stdout.close()
    _stop(diff)
    fields = patch.stdout.split()
    return fields[0].decode() if fields else None


def _first_parent_patch(root: Path, span: str, wanted: str) -> str | None:
    """The newest first-parent commit in `span` whose patch-id is `wanted`, reading one stream and stopping at the first match."""
    log = subprocess.Popen(
        ["git", "log", "--first-parent", "-p", "--no-color", "--no-ext-diff", "--format=commit %H", span],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    patch = subprocess.Popen(["git", "patch-id", "--stable"], cwd=root, stdin=log.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    log.stdout.close()
    found = None
    try:
        for line in patch.stdout:
            fields = line.split()
            if len(fields) == 2 and fields[0].decode() == wanted:
                found = fields[1].decode()
                break
    finally:
        patch.stdout.close()
        _stop(patch, log)
    return found


def detect(root: Path, head: str, mainline: str) -> dict:
    """Run the four checks in order, stopping at the first that proves `head` is in `mainline`."""
    checks: dict[str, bool | None] = dict.fromkeys(CHECKS)

    def result(via: str | None = None, commit: str | None = None) -> dict:
        return {"via": via, "commit": commit, "checks": checks}

    checks["ancestor"] = _is_ancestor(root, head, mainline)
    if checks["ancestor"]:
        # The oldest first-parent commit descending from the head: the merge commit, or the head after a fast-forward.
        chain = gitutil.run(root, "rev-list", "--first-parent", "--ancestry-path", f"{head}..{mainline}", check=False).stdout.split()
        return result("ancestor", chain[-1] if chain else _sha(root, head))

    base = gitutil.run(root, "merge-base", head, mainline, check=False).stdout.strip()
    span = f"{base}..{mainline}" if base else mainline
    tree = _tree(root, head)
    listing = gitutil.run(root, "log", "--first-parent", "--format=%H %T", span, check=False).stdout.splitlines()
    matches = [line.split(" ")[0] for line in listing if line.endswith(f" {tree}")]
    checks["tree"] = bool(matches)
    if matches:
        return result("tree", matches[-1])

    wanted = _branch_patch_id(root, base, head) if base else None
    commit = _first_parent_patch(root, span, wanted) if wanted else None
    checks["patch-id"] = commit is not None
    if commit:
        return result("patch-id", commit)

    merge = gitutil.run(root, "merge-tree", "--write-tree", mainline, head, check=False)
    if merge.returncode in (0, 1):
        checks["merge-tree"] = merge.returncode == 0 and merge.stdout.split("\n", 1)[0].strip() == _tree(root, mainline)
    if checks["merge-tree"]:
        return result("merge-tree", _sha(root, mainline))
    return result()


def _title_commit(root: Path, task_id: str, head: str | None, mainline: str) -> str | None:
    base = gitutil.run(root, "merge-base", head, mainline, check=False).stdout.strip() if head else ""
    span = f"{base}..{mainline}" if base else mainline
    pattern = re.compile(rf"\({re.escape(task_id)}\)(?: \(#\d+\))?$")
    for line in gitutil.run(root, "log", "--first-parent", "--format=%H%x09%s", span, check=False).stdout.splitlines():
        commit, _, subject = line.partition("\t")
        if pattern.search(subject):
            return commit
    return None


def _row_status(project: Project, task: Task, rev: str) -> str | None:
    """The task's status cell at `rev`."""
    backlog = project.config.backlog(task.backlog)
    return _read_statuses(project, backlog.file, [rev])[rev].get(task.id)


CLOSED = {Status.DONE.value: Status.DONE.label, Status.DISCARDED.value: Status.DISCARDED.label}  # a row's cell → a record's `status` (T067)


# Recorded merges


def _mainline_refs(project: Project, task: Task) -> list[str]:
    config = project.config
    mainline = config.backlog(task.backlog).mainline
    remote = resolve_remote(config.root, mainline, config.review.remote).name
    return [ref for ref in (f"refs/heads/{mainline}", f"refs/remotes/{remote}/{mainline}") if _sha(config.root, ref)]


def _still_on_mainline(project: Project, task: Task, record) -> bool:
    if not isinstance(record, dict) or not isinstance(record.get("commit"), str):
        return False
    root = project.config.root
    commit = _sha(root, record["commit"])
    return bool(commit) and any(_is_ancestor(root, commit, ref) for ref in _mainline_refs(project, task))


def record_status(record: dict) -> str:
    """A merge record's closing status: `done` or `discarded`; a record written before T067 has none and is `done`."""
    return Status.DISCARDED.label if record.get("status") == Status.DISCARDED.label else Status.DONE.label


def recorded_merges(project: Project) -> dict[str, str]:
    """Per task a run records as merged while its mainline commit is still on the local or remote mainline,
    the status of its newest such record by `detected` (T067)."""
    try:
        every_run = runs.read_all(project.config)
    except gitutil.GitError:
        return {}
    found: dict[str, str] = {}
    for task_id in {task_id for run in every_run for task_id in run["tasks"]}:
        task = project.task(task_id)
        if task is not None and (latest := _latest_record(project, task, every_run)):
            found[task_id] = record_status(latest)
    return found


def _latest_record(project: Project, task: Task, selected: list[dict]) -> dict | None:
    records = [run["tasks"][task.id].get("merged") for run in selected if task.id in run["tasks"]]
    valid = [record for record in records if _still_on_mainline(project, task, record)]
    return max(valid, key=lambda record: str(record.get("detected") or "")) if valid else None


# Worktrees and cleanup


def _worktree_entries(root: Path) -> list[dict]:
    output = gitutil.run(root, "worktree", "list", "--porcelain").stdout
    entries: list[dict] = []
    for block in output.split("\n\n"):
        entry: dict = {"path": None, "branch": None, "locked": False}
        for line in block.splitlines():
            if line.startswith("worktree "):
                entry["path"] = Path(line[len("worktree "):]).resolve()
            elif line.startswith("branch refs/heads/"):
                entry["branch"] = line[len("branch refs/heads/"):]
            elif line == "locked" or line.startswith("locked "):
                entry["locked"] = True
        if entry["path"] is not None:
            entry["main"] = not entries
            entries.append(entry)
    return entries


def _remove_worktree(root: Path, path: Path) -> None:
    gitutil.run(root, "worktree", "remove", str(path))


def _inside(path: Path, other: Path) -> bool:
    other = other.resolve()
    return other == path or other.is_relative_to(path)


def _cleanup(project: Project, task: Task, branch: str, verified: str | None, remote_ref: str | None, owner: str, merged: bool) -> tuple[dict, int]:
    config = project.config
    root = config.root
    info = {
        "worktree": None,
        "worktree_removed": False,
        "branch_deleted": False,
        "claim_released": False,
        "remote_branch": remote_ref,
        "refused": None,
    }

    def refuse(reason: str, code: int = EXIT_REFUSED) -> tuple[dict, int]:
        info["refused"] = reason
        return info, code

    if not merged:
        return refuse(f"{task.id} is not merged, so nothing was removed")
    try:
        claim = claims.read(config, task.id)
    except gitutil.GitError:
        claim = None
    if claim is not None and claim.owner != owner:
        return refuse(f"{task.id} is claimed by {claim.owner}; nothing was removed", EXIT_CONFLICT)

    local = _sha(root, f"refs/heads/{branch}")
    entries = _worktree_entries(root) if local else []
    entry = next((e for e in entries if e["branch"] == branch), None)
    if entry is not None:
        path = entry["path"]
        info["worktree"] = str(path)
        if entry["main"]:
            return refuse(f"{branch} is checked out in the main worktree {path}; switch it to another branch first")
        if _inside(path, Path.cwd()) or _inside(path, root):
            return refuse(f"the current directory or --root is inside the worktree {path}; run the cleanup from outside it")
        if entry["locked"]:
            return refuse(f"the worktree {path} is locked; unlock it first")
        # git worktree remove deletes ignored content, and a worktree nested in an ignored directory is invisible to status (T074).
        contained = [str(e["path"]) for e in entries if e is not entry and _inside(path, e["path"]) and e["path"].exists()]
        if contained:
            return refuse(
                f"the worktree {path} contains other worktrees: {', '.join(contained)}; move them out with git worktree move, or remove them, first"
            )
        dirty = gitutil.run(path, "status", "--porcelain", "--untracked-files=all", check=False).stdout.strip()
        if dirty:
            return refuse(f"the worktree {path} has uncommitted or untracked changes")

    if entry is not None:
        try:
            _remove_worktree(root, entry["path"])
        except gitutil.GitError as exc:
            return refuse(f"could not remove the worktree: {exc}", EXIT_USAGE)
        info["worktree_removed"] = True
    if local:
        deleted = gitutil.run(root, "update-ref", "-d", f"refs/heads/{branch}", verified or local, check=False)
        if deleted.returncode != 0:
            return refuse(f"{branch} moved since it was checked, so it was kept: {deleted.stderr.strip()}", EXIT_USAGE)
        gitutil.run(root, "config", "--remove-section", f"branch.{branch}", check=False)
        info["branch_deleted"] = True
    if claim is not None:
        claims.release(config, task.id, owner)
        info["claim_released"] = True
    return info, EXIT_OK


# Stacked dependents


def _kept_bases(project: Project) -> dict[str, list[dict]]:
    """Per task, the claim bases runs kept in their lanes, newest run first: they outlive the claim `done` releases."""
    try:
        every_run = runs.read_all(project.config)
    except gitutil.GitError:
        return {}
    kept: dict[str, list[dict]] = {}
    for run in every_run:
        for task_id, lane in run["tasks"].items():
            if isinstance(lane.get("base"), dict):
                kept.setdefault(task_id, []).append(lane["base"])
    return kept


def _recorded_fork(root: Path, base: dict | None, dependency: str, head: str) -> str | None:
    """A recorded base's fork point, when it was taken from `dependency` and `head` still contains it."""
    if not isinstance(base, dict) or base.get("dependency") != dependency or not isinstance(base.get("commit"), str):
        return None
    commit = _sha(root, base["commit"])
    return commit if commit and _is_ancestor(root, commit, head) else None  # a rebased branch no longer contains it


def _dependents(project: Project, task: Task, dependency_head: str | None, recorded_head: str | None, mainline: str) -> list[dict]:
    root = project.config.root
    claimed = _local_claims(project)
    merged = status_module.done_on_mainline(project)
    remote = resolve_remote(root, project.config.backlog(task.backlog).mainline, project.config.review.remote).name
    worktrees = gitutil.worktree_branches(root)
    kept = _kept_bases(project)
    found = []
    for dependent in project.tasks:
        if task.id not in dependent.depends_on or dependent.id in merged or dependent.status is Status.DISCARDED:
            continue
        claim = claimed.get(dependent.id)
        branch = claim.branch if claim and claim.branch else branches.task_branch(dependent, project)
        head = _sha(root, f"refs/heads/{branch}") or _sha(root, f"refs/remotes/{remote}/{branch}") if branch else None
        if not head:
            continue
        reason = None
        recorded = [(claim.base if claim else None, "claim")] + [(base, "run-base") for base in kept.get(dependent.id, [])]
        fork, source = next(
            ((commit, name) for base, name in recorded if (commit := _recorded_fork(root, base, task.id, head))), (None, None)
        )
        if fork is None:
            for other, name in ((dependency_head, "merge-base"), (recorded_head, "run")):
                if other and _sha(root, other):
                    fork = gitutil.run(root, "merge-base", head, other, check=False).stdout.strip() or None
                    source = name if fork else None
                    break
        if fork is None:
            reason = f"the fork point from {task.id} is unknown: no claim or run records it and {task.id}'s head is gone"
        stacked = fork is not None and not _is_ancestor(root, fork, mainline)
        command = None
        if stacked:
            chosen = base_dict(dependent, project)
            onto = chosen["onto"] if chosen else None
            if onto:
                command = f"git rebase --onto {onto} {fork}"
            else:
                reason = chosen["reason"] if chosen else "no base could be determined"
        else:
            onto = None
        checked_out = worktrees.get(branch)
        found.append(
            {
                "id": dependent.id,
                "branch": branch,
                "worktree": str(checked_out) if checked_out else None,
                "head": head,
                "stacked": stacked,
                "fork": fork,
                "fork_source": source,
                "onto": onto,
                "command": command,
                "reason": reason,
            }
        )
    return found


# Command


def _fail(message: str, code: int) -> int:
    print(f"taskrail: {message}", file=sys.stderr)
    return code


def cmd_merged(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = branchrows.find(project, args.id, _local_claims(project))  # a row only its branch holds counts (T071)
    if task is None:
        return _fail(f"no task `{args.id}`", EXIT_NOT_FOUND)
    config = project.config
    root = config.root
    try:
        gitutil.common_dir(root)
    except gitutil.GitError as exc:
        return _fail(str(exc), EXIT_USAGE)
    mainline = config.backlog(task.backlog).mainline
    remote = resolve_remote(root, mainline, config.review.remote).name

    fetched = False
    if not args.no_fetch and remote in gitutil.run(root, "remote", check=False).stdout.split():
        result = gitutil.run(root, "fetch", "--quiet", "--prune", remote, check=False)
        if result.returncode != 0:
            return _fail(f"git fetch --prune {remote} failed: {result.stderr.strip()}", EXIT_USAGE)
        fetched = True
        project, _ = _load(args)  # the refs moved
        task = branchrows.find(project, args.id, _local_claims(project))
        config = project.config

    if args.run is not None:
        run = runs.read(config, args.run)
        if run is None:
            return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
        if task.id not in run["tasks"]:
            return _fail(f"run {args.run} does not hold {task.id}", EXIT_NOT_FOUND)
        selected = [run]
    else:
        claim_run = None
        try:
            held = claims.read(config, task.id)
            claim_run = held.run if held else None
        except gitutil.GitError:
            pass
        selected = [run for run in runs.read_all(config) if task.id in run["tasks"] or run["id"] == claim_run]

    try:
        claim = claims.read(config, task.id)
    except gitutil.GitError:
        claim = None
    branch = claim.branch if claim and claim.branch else branches.task_branch(task, project)

    base = choose_base(root, remote, mainline)
    if base.diverged:
        candidates = [f"{remote}/{mainline}", mainline]
    elif base.onto:
        candidates = [base.onto]
    else:
        return _fail(f"cannot check {task.id}: {base.reason}", EXIT_USAGE)

    local = _sha(root, f"refs/heads/{branch}") if branch else None
    tracked = _sha(root, f"refs/remotes/{remote}/{branch}") if branch else None
    head_commit = local or tracked
    head_ref = branch if local else (f"{remote}/{branch}" if tracked else None)
    remote_ref = f"{remote}/{branch}" if tracked else None

    record = _latest_record(project, task, selected)
    mainline_ref = candidates[0]
    detection = {"via": None, "commit": None, "checks": dict.fromkeys(CHECKS)}
    done_at_head = None
    closed = None
    recorded = False
    reason = None
    if head_commit is None:
        if record is None:
            return _fail(
                f"no branch of {task.id} to check: neither {branch} nor {remote}/{branch} exists, and no run records a merge", EXIT_NOT_FOUND
            )
        recorded = True
        closed = record_status(record)
        detection.update(via=record.get("via"), commit=record["commit"])
        mainline_ref = record.get("mainline") or mainline_ref
    else:
        cell = _row_status(project, task, head_commit)
        done_at_head = cell == Status.DONE.value
        closed = CLOSED.get(cell)  # detection needs a closed row: an unstarted branch is an ancestor of the mainline
        if closed is None:
            reason = f"{task.id} is not done or discarded at the head of {head_ref}; content detection needs a closed branch"
        else:
            for candidate in candidates:
                detection = detect(root, head_commit, candidate)
                if detection["via"]:
                    mainline_ref = candidate
                    break
            if not detection["via"]:
                reason = f"no check proves that {head_ref} is contained in {mainline_ref}"
    is_merged = detection["via"] is not None

    written: list[str] = []
    if is_merged and not recorded:
        entry = {
            "via": detection["via"],
            "commit": detection["commit"],
            "head": head_commit,
            "mainline": mainline_ref,
            "detected": runs.now_iso(datetime.now(timezone.utc)),
            "status": closed,
        }
        for run in selected:
            with runs.update(config, run["id"]) as stored:
                runs.lane(stored, task.id)["merged"] = dict(entry)
            written.append(run["id"])

    dependents = _dependents(project, task, head_commit, (record or {}).get("head"), mainline_ref)
    mainline_row = _row_status(project, task, mainline_ref)

    data = {
        "id": task.id,
        "branch": branch,
        "remote": remote,
        "fetched": fetched,
        "mainline": {"ref": mainline_ref, "commit": _sha(root, mainline_ref), "diverged": base.diverged},
        "head": {"ref": head_ref, "commit": head_commit if head_commit else (record or {}).get("head"), "local": local, "remote": tracked},
        "done_at_head": done_at_head,
        "closed": closed,
        "merged": is_merged,
        "via": detection["via"],
        "commit": detection["commit"],
        "recorded": recorded,
        "reason": reason,
        "checks": detection["checks"],
        "confirmations": {
            "row_done_on_mainline": mainline_row == Status.DONE.value,
            "row_discarded_on_mainline": mainline_row == Status.DISCARDED.value,
            "title_commit": _title_commit(root, task.id, head_commit, mainline_ref),
        },
        "runs": written,
        "cleanup": None,
        "dependents": dependents,
    }

    code = EXIT_OK
    if args.cleanup:
        owner = args.owner or claims.default_owner()
        data["cleanup"], code = _cleanup(project, task, branch, local, remote_ref, owner, is_merged)
        if data["cleanup"]["refused"]:
            print(f"taskrail: cleanup refused: {data['cleanup']['refused']}", file=sys.stderr)
    _emit(data, args.json, _text(data))
    return code


def _text(data: dict) -> str:
    ref = data["mainline"]["ref"]
    if data["merged"]:
        lines = [
            f"{data['id']} merged into {ref} via {data['via']} at {data['commit'][:7]}"
            + (" (recorded in a run)" if data["recorded"] else "")
            + (" (discarded)" if data["closed"] == Status.DISCARDED.label else "")
        ]
    else:
        lines = [f"{data['id']} not merged into {ref}: {data['reason']}"]
    cleanup = data["cleanup"]
    if cleanup:
        if cleanup["worktree_removed"]:
            lines.append(f"removed worktree {cleanup['worktree']}")
        if cleanup["branch_deleted"]:
            lines.append(f"deleted branch {data['branch']}")
        if cleanup["claim_released"]:
            lines.append(f"released the claim on {data['id']}")
        if cleanup["remote_branch"] and not cleanup["refused"]:
            lines.append(f"kept remote branch {cleanup['remote_branch']}")
        if cleanup["refused"]:
            lines.append(f"cleanup refused: {cleanup['refused']}")
    for dependent in data["dependents"]:
        where = f" (in {dependent['worktree']})" if dependent["worktree"] else ""
        if dependent["command"]:
            lines.append(f"{dependent['id']}: {dependent['command']}{where}")
        elif not dependent["stacked"] and dependent["fork"]:
            lines.append(f"{dependent['id']}: not stacked on {data['id']}, no rebase --onto needed")
        else:
            lines.append(f"{dependent['id']}: {dependent['reason']}")
    return "\n".join(lines)


def add_arguments(parser) -> None:
    parser.add_argument("id")
    parser.add_argument("--run", help="record the merge in this run only (default: every run that holds the task)")
    parser.add_argument("--cleanup", action="store_true", help="remove the task's worktree and local branch once the merge is proven")
    parser.add_argument("--no-fetch", action="store_true", help="check the refs as they are, without git fetch --prune")
    parser.add_argument("--owner", help="who is cleaning up, to release a claim left behind (default: $TASKRAIL_OWNER or user@host)")
    parser.add_argument("--allow-invalid", action="store_true")
