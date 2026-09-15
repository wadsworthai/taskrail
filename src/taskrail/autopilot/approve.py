"""`taskrail autopilot approve-governing`: record a governing edit the human approved (DESIGN.md §12.6; T059).

Each approved path is stored in the task's lane with the blob ID of its content, so `autopilot status`
stops raising `governing` for it until that content changes.
"""

from __future__ import annotations

import sys

from taskrail import branchrows, ids
from taskrail.autopilot import runs
from taskrail.autopilot import status as status_module
from taskrail.cli import EXIT_CONFLICT, EXIT_NOT_FOUND, EXIT_OK, EXIT_REFUSED, EXIT_USAGE, _emit, _load, _local_claims

KEY = "governing_approved"


def _fail(message: str, code: int) -> int:
    print(f"taskrail: {message}", file=sys.stderr)
    return code


def cmd_approve_governing(args) -> int:
    project, _ = _load(args)  # like `lane`: recording an approval must not wait for a valid backlog
    config = project.config
    run = runs.read(config, args.run)
    if run is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    claimed = _local_claims(project)
    task = branchrows.find(project, args.id, claimed)  # a row only its branch holds counts (T071)
    if task is None:
        return _fail(f"no task `{args.id}`", EXIT_NOT_FOUND)
    claim = claimed.get(task.id)
    if task.id not in run["tasks"] and not (claim and claim.run == run["id"]):
        return _fail(f"{task.id} is not a task of run {run['id']}", EXIT_NOT_FOUND)

    found = next(row for row in status_module.run_status(project, run, claimed)["tasks"] if row["id"] == task.id)
    governing = found.get("governing_touched") or []
    if not governing:
        return _fail(f"{task.id} touches no governing path in run {run['id']}, so there is nothing to approve", EXIT_REFUSED)
    paths = list(dict.fromkeys(args.path)) if args.path else governing
    unknown = [path for path in paths if path not in governing]
    if unknown:
        return _fail(f"--path {', '.join(unknown)}: not in {task.id}'s governing_touched ({', '.join(governing)})", EXIT_USAGE)

    root = config.root
    head = status_module._branch_ref(root, found.get("branch"))
    approved = status_module.current_blobs(root, found.get("worktree"), head, paths)
    try:
        with runs.update(config, args.run) as stored:
            lane = runs.lane(stored, task.id)
            recorded = lane.get(KEY) if isinstance(lane.get(KEY), dict) else {}
            lane[KEY] = dict(sorted({**recorded, **approved}.items()))
            everything = dict(lane[KEY])
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    text = f"{task.id} in run {args.run}: approved " + ", ".join(f"{path} ({(blob or 'deleted')[:12]})" for path, blob in approved.items())
    _emit({"run": args.run, "task": task.id, "approved": approved, KEY: everything}, args.json, text)
    return EXIT_OK


def add_arguments(parser) -> None:
    parser.add_argument("id")
    parser.add_argument("--run", required=True)
    parser.add_argument(
        "--path", action="append", help="a governing file to approve; repeat for several (default: every file in governing_touched)"
    )
