"""`taskrail autopilot …`: argument parsing and handlers. A later subcommand adds its handler and one `add` call."""

from __future__ import annotations

import sys

from taskrail import claims, gitutil, ids, stack
from taskrail.autopilot import runs
from taskrail.autopilot.status import status as compute_status
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
from taskrail.review import resolve_remote


def _fail(message: str, code: int) -> int:
    print(f"taskrail: {message}", file=sys.stderr)
    return code


def cmd_start(args) -> int:
    project, issues = _load(args)
    config = project.config
    if not config.autopilot.enabled:
        return _fail("the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot start`", EXIT_REFUSED)
    if args.count is None:
        return _fail("autopilot start needs --count N, the number of tasks to complete", EXIT_USAGE)
    if args.count < 1:
        return _fail("--count must be at least 1", EXIT_USAGE)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    if args.kinds is None:
        kinds, source = list(config.autopilot.kinds), "[autopilot].kinds"
    else:
        kinds, source = [name.strip() for name in args.kinds.split(",") if name.strip()], "--kinds"
    kinds = list(dict.fromkeys(kinds))
    for name in kinds:
        if name not in project.kinds:
            from taskrail.kinds import defined_kind_names

            if config.allowed_kinds and name in defined_kind_names(config):
                reason = f"is not allowed (kinds.allowed: {', '.join(sorted(config.allowed_kinds))})"
            else:
                reason = f"is not defined (known: {', '.join(sorted(project.kinds)) or 'none'})"
            return _fail(f"{source}: kind `{name}` {reason}", EXIT_USAGE)
    run = runs.create(config, args.count, kinds, claims.default_owner())
    _emit({"run": run, "path": str(runs.runs_dir(config) / f"{run['id']}.json")}, args.json, run["id"])
    return EXIT_OK


def cmd_lane(args) -> int:
    project, _ = _load(args)
    config = project.config
    if runs.read(config, args.run) is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    task = project.task(args.id)
    if task is None:
        return _fail(f"no task `{args.id}`", EXIT_NOT_FOUND)
    handed_off = args.state == runs.HANDED_OFF
    state = None if handed_off else args.state
    if state in runs.REASON_REQUIRED and not (args.reason or "").strip():
        return _fail(f"--state {state} needs --reason", EXIT_USAGE)
    if handed_off and task.id not in stack.done_on_branch(project):
        return _fail(f"{task.id} is not done on its branch (done-branch), so it cannot be handed off", EXIT_REFUSED)
    current = runs.read(config, args.run)["tasks"].get(task.id, {}).get("state", "running")
    if args.reason is not None and (state or current) == "running":
        return _fail("a running lane has no reason; pass --state gate, escalated or failed with --reason", EXIT_USAGE)
    try:
        with runs.update(config, args.run) as run:
            lane = runs.record_lane(
                run, task.id, handle=args.handle, group=args.group, state=state, reason=args.reason.strip() if args.reason else None
            )
            if handed_off:
                runs.hand_off(run, task.id)
            order = list(run["handed_off"])
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    text = f"{task.id} in run {args.run}: {lane['state']}" + (f" ({lane['reason']})" if lane["reason"] else "")
    if handed_off:
        text += f"; handed off ({order.index(task.id) + 1} of {len(order)})"
    _emit({"run": args.run, "task": {"id": task.id, **lane}, "handed_off": order}, args.json, text)
    return EXIT_OK


def cmd_decision(args) -> int:
    project, _ = _load(args)
    values = {name: (getattr(args, name) or "").strip() for name in ("question", "decision", "reason")}
    empty = [f"--{name}" for name, value in values.items() if not value]
    if empty:
        return _fail(f"{', '.join(empty)} must not be empty", EXIT_USAGE)
    try:
        with runs.update(project.config, args.run) as run:
            entry = runs.add_decision(run, **values)
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    _emit({"run": args.run, "decision": entry}, args.json, f"decision {entry['number']} recorded in run {args.run}")
    return EXIT_OK


def cmd_status(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    config = project.config
    if args.run is not None:
        run = runs.read(config, args.run)
        if run is None:
            return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
        selected = [run]
    else:
        selected = runs.read_all(config)
    fetched = []
    if args.fetch:
        for remote in dict.fromkeys(resolve_remote(config.root, b.mainline, config.review.remote).name for b in config.backlogs):
            result = gitutil.run(config.root, "fetch", "--quiet", remote, check=False)
            if result.returncode != 0:
                return _fail(f"git fetch {remote} failed: {result.stderr.strip()}", EXIT_USAGE)
            fetched.append(remote)
        project, _ = _load(args)  # the refs moved: derive states from the fetched ones
    report = compute_status(project, selected, _local_claims(project))
    report["fetched"] = fetched
    _emit(report, args.json, _status_text(report))
    return EXIT_OK


def _status_text(report: dict) -> str:
    if not report["runs"]:
        return "no autopilot runs"
    lines = []
    for run in report["runs"]:
        kinds = ", ".join(run["kinds"]) or "every allowed kind"
        done = " · complete" if run["complete"] else ""
        lines.append(f"run {run['id']} · {run['done_merged']}/{run['count']} done-merged{done} · kinds: {kinds} · started {run['started']} by {run['owner']}")
        for row in run["tasks"]:
            if row["state"] is None:
                lines.append(f"  {row['id']:<6} {row['problem']}")
                continue
            parts = [f"  {row['id']:<6} {row['state']:<11}"]
            if row["handle"]:
                parts.append(f"handle {row['handle']}")
            if row["group"]:
                parts.append(f"group {row['group']}")
            if row["idle_minutes"] is not None:
                parts.append(f"idle {row['idle_minutes']}m" + (" SILENT" if row["silent"] else ""))
            if row["claim"] and row["claim"]["stale"]:
                parts.append(f"stale claim: {row['claim']['stale']}")
            if row["reason"]:
                parts.append(f"— {row['reason']}")
            lines.append("  ".join(parts))
        handoff = run["handoff"]
        lines.append(f"  hand-off: next {handoff['next'] or '—'} · in review {handoff['in_review'] or '—'} · queue {', '.join(handoff['queue']) or '—'}")
    if report["overlaps"]:
        lines.append("files touched by more than one lane:")
        lines += [f"  {path}: {', '.join(task_ids)}" for path, task_ids in report["overlaps"].items()]
    return "\n".join(lines)


def register(commands) -> None:
    """Add the `autopilot` command group to the top-level subparsers."""
    autopilot = commands.add_parser("autopilot", help="Run several tasks at once in lanes (DESIGN.md §12).")
    group = autopilot.add_subparsers(dest="autopilot_command", required=True)

    def add(name: str, handler, help_text: str):
        sub = group.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("--json", action="store_true", help="machine-readable output")
        sub.set_defaults(handler=handler)
        return sub

    start = add("start", cmd_start, "Start a run; refused until [autopilot].enabled is true.")
    start.add_argument("--count", type=int, help="number of tasks to complete (required)")
    start.add_argument("--kinds", help="comma-separated kinds to drive (default: [autopilot].kinds)")

    lane = add("lane", cmd_lane, "Record the orchestrator's view of one lane in a run.")
    lane.add_argument("id")
    lane.add_argument("--run", required=True)
    lane.add_argument("--handle", help="the agent-specific handle to resume the lane")
    lane.add_argument("--group", help="a group assigned by judgement")
    lane.add_argument("--state", choices=(*runs.LANE_STATES, runs.HANDED_OFF))
    lane.add_argument("--reason", help="required with escalated and failed")

    decision = add("decision", cmd_decision, "Record a run-level decision in a run.")
    decision.add_argument("--run", required=True)
    decision.add_argument("--question", required=True)
    decision.add_argument("--decision", required=True)
    decision.add_argument("--reason", required=True)

    status = add("status", cmd_status, "Every run task with its state, lane activity, touched files and hand-off queue.")
    status.add_argument("--run", help="only this run (default: every run, newest first)")
    status.add_argument("--fetch", action="store_true", help="fetch each mainline's remote first")
    status.add_argument("--allow-invalid", action="store_true")
