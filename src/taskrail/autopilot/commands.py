"""`taskrail autopilot …`: argument parsing and handlers. A later subcommand adds its handler and one `add` call."""

from __future__ import annotations

import sys

from taskrail import branchrows, claims, gitutil, ids, stack
from taskrail.autopilot import dispatch, notify, runs
from taskrail.autopilot.approve import add_arguments as approve_arguments
from taskrail.autopilot.approve import cmd_approve_governing
from taskrail.autopilot.merged import add_arguments as merged_arguments
from taskrail.autopilot.merged import cmd_merged
from taskrail.autopilot.status import discarded_on_mainline, done_on_mainline, task_state
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
from taskrail.config import NOTIFY_EVENTS
from taskrail.review import resolve_remote


def _fail(message: str, code: int) -> int:
    print(f"taskrail: {message}", file=sys.stderr)
    return code


def _task_branch_refusal(config) -> int | None:
    """Exit 5 when tasks are worked on the checked-out branch: a run needs a branch per task (DESIGN.md §12.2)."""
    if config.task_branch == "current":
        return _fail('the autopilot needs a branch per task; [git].task_branch is "current" in .taskrail/config.toml', EXIT_REFUSED)
    return None


def _task_ids(raw: str) -> list[str]:
    """`--tasks` IDs in the order given, each once."""
    return list(dict.fromkeys(item.strip() for item in raw.split(",") if item.strip()))


def _named_problem(project, task_ids: list[str], claimed: dict) -> tuple[str, int] | None:
    """Why these tasks cannot be named in a run, with the exit code; None when every one can (T071)."""
    config = project.config
    branchrows.adopt(project, task_ids, claimed)  # a row only its task's branch holds can be named from any checkout
    driven = set(config.autopilot.kinds)
    for task_id in task_ids:
        task = project.task(task_id)
        if task is None:
            return (
                f"no task `{task_id}` in this checkout nor on its claimed or recorded branch; if its workspace exists, "
                f"record its branch with `taskrail branch {task_id} <NAME>` inside that worktree",
                EXIT_NOT_FOUND,
            )
        closed = None
        if task.status is not None and task.status.label in ("done", "discarded"):
            closed = task.status.label
        elif task_id in done_on_mainline(project) or task_id in discarded_on_mainline(project):
            closed = "closed on the mainline"
        elif task_id in stack.done_on_branch(project):
            closed = "done-branch"
        elif task_id in stack.discarded_on_branch(project):
            closed = "discarded-branch"
        if closed:
            return f"{task_id} is {closed}, so a run cannot work it", EXIT_REFUSED
        if task.kind not in project.kinds:
            return f"{task_id}'s kind `{task.kind}` is not defined or not allowed", EXIT_REFUSED
        if driven and task.kind not in driven:
            return f"{task_id}'s kind `{task.kind}` is not in [autopilot].kinds ({', '.join(sorted(driven))})", EXIT_REFUSED
    return None


def cmd_start(args) -> int:
    project, issues = _load(args)
    config = project.config
    if not config.autopilot.enabled:
        return _fail("the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot start`", EXIT_REFUSED)
    if (refused := _task_branch_refusal(config)) is not None:
        return refused
    named = _task_ids(args.tasks) if args.tasks is not None else None
    if named is None and args.count is None:
        return _fail("autopilot start needs --count N, the number of tasks to complete, or --tasks with their IDs", EXIT_USAGE)
    if args.count is not None and args.count < 1:
        return _fail("--count must be at least 1", EXIT_USAGE)
    if named is not None:
        if not named:
            return _fail("--tasks needs at least one task ID", EXIT_USAGE)
        if args.kinds is not None:
            return _fail("--kinds does not apply with --tasks: a named run works the tasks it names", EXIT_USAGE)
        if args.count is not None and args.count != len(named):
            return _fail(f"--count {args.count} does not match the {len(named)} task(s) --tasks names", EXIT_USAGE)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    if named is not None:
        problem = _named_problem(project, named, _local_claims(project))
        if problem:
            return _fail(*problem)
        run = runs.create(config, len(named), [], claims.default_owner(), named=named)
        _emit({"run": run, "path": str(runs.runs_dir(config) / f"{run['id']}.json")}, args.json, run["id"])
        return EXIT_OK
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


def cmd_extend(args) -> int:
    """Add named tasks to a named run, or set a count-only run's count (T071)."""
    project, issues = _load(args)
    config = project.config
    if not config.autopilot.enabled:
        return _fail("the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot extend`", EXIT_REFUSED)
    if (refused := _task_branch_refusal(config)) is not None:
        return refused
    stored = runs.read(config, args.run)
    if stored is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    if runs.is_closed(stored):
        return _fail(runs.closed_message(args.run), EXIT_REFUSED)
    named_run = runs.is_named(stored)
    if args.tasks is None and args.count is None:
        return _fail("autopilot extend needs --tasks (a named run) or --count (a count-only run)", EXIT_USAGE)
    if named_run and args.count is not None:
        return _fail(f"run {args.run} names its tasks; its count grows with --tasks, not --count", EXIT_USAGE)
    if not named_run and args.tasks is not None:
        return _fail(f"run {args.run} was started with --count; raise it with --count, or start a run with --tasks", EXIT_USAGE)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    claimed = _local_claims(project)
    if named_run:
        requested = _task_ids(args.tasks)
        if not requested:
            return _fail("--tasks needs at least one task ID", EXIT_USAGE)
        problem = _named_problem(project, [task_id for task_id in requested if task_id not in stored["named"]], claimed)
        if problem:
            return _fail(*problem)
    else:
        if args.count < 1:
            return _fail("--count must be at least 1", EXIT_USAGE)
        branchrows.adopt(project, runs.members(stored, claimed), claimed)
        counted = [
            task_id
            for task_id in dispatch._members(stored, claimed)
            if (task := project.task(task_id)) is not None and task_state(task, project, stored, claimed.get(task_id)) in dispatch.COUNTED
        ]
        if args.count < len(counted):
            return _fail(
                f"--count {args.count} is lower than the {len(counted)} task(s) already counted toward run {args.run} ({', '.join(counted)})",
                EXIT_REFUSED,
            )
    try:
        with runs.update(config, args.run) as run:
            if runs.is_closed(run):
                raise runs.RunClosed(runs.closed_message(args.run))
            previous = run["count"]
            if named_run:
                added = runs.add_named(run, requested)
            else:
                added = []
                run["count"] = args.count
            updated = dict(run)
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except runs.RunClosed as exc:
        return _fail(str(exc), EXIT_REFUSED)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    text = f"run {args.run}: count {previous} → {updated['count']}"
    if named_run:
        text += f"; added {', '.join(added)}" if added else "; every task was already named"
    _emit({"run": updated, "added": added, "previous_count": previous}, args.json, text)
    return EXIT_OK


def cmd_lane(args) -> int:
    project, _ = _load(args)
    config = project.config
    stored = runs.read(config, args.run)
    if stored is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    if runs.is_closed(stored):
        return _fail(runs.closed_message(args.run), EXIT_REFUSED)
    task = branchrows.find(project, args.id, _local_claims(project))  # also a row only its branch holds (T071)
    if task is None:
        return _fail(f"no task `{args.id}`", EXIT_NOT_FOUND)
    if args.group is not None:
        group = config.autopilot.group(args.group)
        if group is None:
            judgement = [g.name for g in config.autopilot.groups if g.predicate is None]
            return _fail(f"no judgement group `{args.group}` in [[autopilot.group]] (judgement groups: {', '.join(judgement) or 'none'})", EXIT_USAGE)
        if group.predicate is not None:
            return _fail(f"group `{group.name}` is computed from column {group.predicate.column}; --group assigns only a group without column and match", EXIT_USAGE)
    handed_off = args.state == runs.HANDED_OFF
    state = None if handed_off else args.state
    if state in runs.REASON_REQUIRED and not (args.reason or "").strip():
        return _fail(f"--state {state} needs --reason", EXIT_USAGE)
    if handed_off and task.id not in stack.done_on_branch(project) and task.id not in stack.discarded_on_branch(project):
        return _fail(f"{task.id} is neither done nor discarded on its branch (done-branch or discarded-branch), so it cannot be handed off", EXIT_REFUSED)
    current = stored["tasks"].get(task.id, {}).get("state", "running")
    if args.reason is not None and (state or current) == "running":
        return _fail("a running lane has no reason; pass --state gate, escalated or failed with --reason", EXIT_USAGE)
    if args.gate is not None:
        problem = _gate_problem(project, task, args.gate, None if handed_off else (state or current))
        if problem:
            return _fail(problem, EXIT_USAGE)
    try:
        with runs.update(config, args.run) as run:
            if runs.is_closed(run):
                raise runs.RunClosed(runs.closed_message(args.run))
            lane = runs.record_lane(
                run, task.id, handle=args.handle, group=args.group, state=state, reason=args.reason.strip() if args.reason else None, gate=args.gate
            )
            if handed_off:
                runs.hand_off(run, task.id)
            order = list(run["handed_off"])
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except runs.RunClosed as exc:
        return _fail(str(exc), EXIT_REFUSED)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    text = f"{task.id} in run {args.run}: {lane['state']}" + (f" at {lane['gate']}" if lane.get("gate") else "")
    text += f" ({lane['reason']})" if lane["reason"] else ""
    if handed_off:
        text += f"; handed off ({order.index(task.id) + 1} of {len(order)})"
    _emit({"run": args.run, "task": {"id": task.id, "gate": None, **lane}, "handed_off": order}, args.json, text)
    return EXIT_OK


CLOSE_GATE = "close"  # the stop after `taskrail done` that every kind shares (T050)


def _gate_problem(project, task, gate: str, state: str | None) -> str | None:
    """Why `lane --gate` cannot record this stage, or None when it can."""
    if state not in runs.GATE_STATES:
        return f"--gate needs --state gate or escalated (the lane is {state or 'being handed off'})"
    if gate == CLOSE_GATE:
        return None  # needs no stage of the kind, so an undefined kind does not refuse it
    kind = project.kinds.get(task.kind)
    if kind is None:
        return f"--gate: {task.id}'s kind `{task.kind}` is not defined, so its stages are unknown"
    stages = [stage.name for stage in kind.stages]
    if gate not in stages:
        return f"--gate: `{gate}` is not a stage of kind {kind.name} ({', '.join(stages)}) or `{CLOSE_GATE}`"
    return None


def cmd_notify(args) -> int:
    project, _ = _load(args)  # a notification about a broken backlog must still go out
    config = project.config
    run = runs.read(config, args.run)
    if run is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    if args.event in notify.TASK_EVENTS and args.task is None:
        return _fail(f"--event {args.event} needs --task", EXIT_USAGE)
    task = None
    if args.task is not None:
        task = branchrows.find(project, args.task, _local_claims(project))  # also a row only its branch holds (T071)
        if task is None:
            return _fail(f"no task `{args.task}`", EXIT_NOT_FOUND)
        claim = _local_claims(project).get(task.id)
        if task.id not in run["tasks"] and not (claim and claim.run == run["id"]):
            return _fail(f"{task.id} is not a task of run {run['id']}", EXIT_NOT_FOUND)
    result = notify.notify(config, args.event, run, task, args.message)
    if result["error"]:
        detail = result["stderr"].strip().splitlines()[-1:] if result["stderr"].strip() else []
        print(f"taskrail: warning: {result['error']}" + (f": {detail[0]}" if detail else ""), file=sys.stderr)
    if result["sent"]:
        text = f"notified: {args.event}"
    else:
        text = f"not sent: {result['skipped'] or result['error']}"
    _emit(result, args.json, text)
    return EXIT_OK


def cmd_decision(args) -> int:
    project, _ = _load(args)
    values = {name: (getattr(args, name) or "").strip() for name in ("question", "decision", "reason")}
    empty = [f"--{name}" for name, value in values.items() if not value]
    if empty:
        return _fail(f"{', '.join(empty)} must not be empty", EXIT_USAGE)
    try:
        with runs.update(project.config, args.run) as run:
            if runs.is_closed(run):
                raise runs.RunClosed(runs.closed_message(args.run))
            entry = runs.add_decision(run, **values)
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except runs.RunClosed as exc:
        return _fail(str(exc), EXIT_REFUSED)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    _emit({"run": args.run, "decision": entry}, args.json, f"decision {entry['number']} recorded in run {args.run}")
    return EXIT_OK


def cmd_next(args) -> int:
    project, issues = _load(args)
    config = project.config
    if not config.autopilot.enabled:
        return _fail("the autopilot is disabled; set [autopilot].enabled = true in .taskrail/config.toml to allow `autopilot next`", EXIT_REFUSED)
    if (refused := _task_branch_refusal(config)) is not None:
        return refused
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    if args.run is not None:
        stored = runs.read(config, args.run)
        if stored is None:
            return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
        if runs.is_closed(stored):
            return _fail(runs.closed_message(args.run), EXIT_REFUSED)
    try:
        report = dispatch.next_lanes(project, args.run, _local_claims(project))
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except runs.RunClosed as exc:
        return _fail(str(exc), EXIT_REFUSED)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    _emit(report, args.json, dispatch.text(report))
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
        selected = [run for run in runs.read_all(config) if not runs.is_closed(run)]  # a closed run is shown only when named
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
    report["read_first"] = list(config.autopilot.read_first)
    report["read_first_missing"] = [entry for entry in config.autopilot.read_first if not _matches_anything(config.root, entry)]
    _emit(report, args.json, _status_text(report))
    return EXIT_OK


def _matches_anything(root, entry: str) -> bool:
    """Whether a `read_first` entry — a path or a glob, relative to the root — names anything that exists (T061)."""
    try:
        return any(True for _ in root.glob(entry.removeprefix("./")))
    except (ValueError, NotImplementedError):  # an empty or absolute pattern
        return False


def _read_first_text(report: dict) -> list[str]:
    lines = [f"read first: {', '.join(report['read_first'])}"] if report["read_first"] else []
    if report["read_first_missing"]:
        lines.append(f"read first missing: {', '.join(report['read_first_missing'])}")
    return lines


def _status_text(report: dict) -> str:
    lines = _read_first_text(report)
    if not report["runs"]:
        return "\n".join([*lines, "no autopilot runs"])
    for run in report["runs"]:
        kinds = ", ".join(run["kinds"]) or "every allowed kind"
        done = " · complete" if run["complete"] else ""
        scope = f"named: {', '.join(run['named'])}" if run.get("named") else f"kinds: {kinds}"
        lines.append(f"run {run['id']} · {run['done_merged']}/{run['count']} done-merged{done} · {scope} · started {run['started']} by {run['owner']}")
        if run.get("closed"):
            closed = run["closed"]
            lines.append(f"  closed {closed['at']} by {closed['by']} — {closed['reason']}")
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
            parts += _escalation_text(row)
            lines.append("  ".join(parts))
        handoff = run["handoff"]
        lines.append(f"  hand-off: next {handoff['next'] or '—'} · in review {handoff['in_review'] or '—'} · queue {', '.join(handoff['queue']) or '—'}")
    if report["overlaps"]:
        lines.append("files touched by more than one lane:")
        lines += [f"  {path}: {', '.join(task_ids)}" for path, task_ids in report["overlaps"].items()]
    if report["known_overlaps"]:
        lines.append("known conflict classes touched by more than one lane (resolved at hand-off):")
        lines += [f"  {path} ({known['class']}): {', '.join(known['tasks'])}" for path, known in report["known_overlaps"].items()]
    return "\n".join(lines)


def _escalation_text(row: dict) -> list[str]:
    reasons = []  # only the reasons in `escalation`, so the text and the JSON agree (T049)
    escalation = row.get("escalation") or []
    if "governing" in escalation:
        approved = set(row.get("governing_approved") or [])  # only the files still waiting for approval (T059)
        reasons.append(f"governing {', '.join(path for path in row['governing_touched'] if path not in approved)}")
    if "escalate-gate" in escalation:
        reasons.append(f"gate {row['escalate_gate']}")
    return [f"ESCALATE: {'; '.join(reasons)}"] if reasons else []


def cmd_close(args) -> int:
    project, _ = _load(args)  # abandoning a run must work with a broken backlog or a disabled autopilot
    config = project.config
    reason = (args.reason or "").strip()
    if not reason:
        return _fail("--reason must not be empty", EXIT_USAGE)
    if runs.read(config, args.run) is None:
        return _fail(f"no autopilot run `{args.run}`", EXIT_NOT_FOUND)
    try:
        with runs.update(config, args.run) as run:
            if runs.is_closed(run):
                raise runs.RunClosed(f"autopilot run `{args.run}` is already closed ({run['closed'].get('at')}: {run['closed'].get('reason')})")
            released = runs.close(run, reason, claims.default_owner())
            closed = dict(run["closed"])
    except runs.RunNotFound as exc:
        return _fail(str(exc), EXIT_NOT_FOUND)
    except runs.RunClosed as exc:
        return _fail(str(exc), EXIT_REFUSED)
    except ids.LockTimeout as exc:
        return _fail(str(exc), EXIT_CONFLICT)
    held = sorted((claim for claim in _local_claims(project).values() if claim.run == args.run), key=lambda claim: claim.id)
    kept = [{"id": claim.id, "owner": claim.owner, "branch": claim.branch, "worktree": claim.worktree} for claim in held]
    lines = [f"closed run {args.run}: {reason}"]
    for entry in released:
        values = " ".join(f"{name}={value}" for name, value in entry["resources"].items())
        dispatched = f"dispatch of {entry['dispatched']}" if entry["dispatched"] else ""
        lines.append(f"  released {' and '.join(part for part in (dispatched, values) if part)} from {entry['id']}")
    for claim in kept:
        lines.append(f"  kept claim {claim['id']} by {claim['owner']}" + (f" in {claim['worktree']}" if claim["worktree"] else "") + f"; release it with `taskrail release {claim['id']}`")
    _emit({"run": args.run, "closed": closed, "released": released, "claims": kept}, args.json, "\n".join(lines))
    return EXIT_OK


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
    start.add_argument("--count", type=int, help="number of tasks to complete (required unless --tasks names them)")
    start.add_argument("--kinds", help="comma-separated kinds to drive (default: [autopilot].kinds)")
    start.add_argument("--tasks", help="comma-separated task IDs: the run works only these, in this order, and its count is their number")

    extend = add("extend", cmd_extend, "Add tasks to a named run, or set a count-only run's count.")
    extend.add_argument("run")
    extend.add_argument("--tasks", help="comma-separated task IDs to append to a run started with --tasks; its count grows by as many")
    extend.add_argument("--count", type=int, help="the new count of a run started with --count")

    lane = add("lane", cmd_lane, "Record the orchestrator's view of one lane in a run.")
    lane.add_argument("id")
    lane.add_argument("--run", required=True)
    lane.add_argument("--handle", help="the agent-specific handle to resume the lane")
    lane.add_argument("--group", help="a group assigned by judgement")
    lane.add_argument("--state", choices=(*runs.LANE_STATES, runs.HANDED_OFF))
    lane.add_argument("--reason", help="required with escalated and failed")
    lane.add_argument("--gate", help="the stage whose gate the lane is stopped at, or close for the stop after done (with --state gate or escalated)")

    next_ = add("next", cmd_next, "Tasks to dispatch now within lanes, kinds, groups and the run's count, with their resources.")
    next_.add_argument("--run", help="record the dispatch in this run (default: a preview that records nothing)")

    decision = add("decision", cmd_decision, "Record a run-level decision in a run.")
    decision.add_argument("--run", required=True)
    decision.add_argument("--question", required=True)
    decision.add_argument("--decision", required=True)
    decision.add_argument("--reason", required=True)

    approve_arguments(add("approve-governing", cmd_approve_governing, "Record a governing edit the human approved, so status stops flagging it until the file changes."))

    notify_ = add("notify", cmd_notify, "Run [autopilot].notify for an event in notify_on; a failing command is reported and never blocks.")
    notify_.add_argument("--event", required=True, choices=NOTIFY_EVENTS)
    notify_.add_argument("--run", required=True)
    notify_.add_argument("--task", help="the lane's task (required for lane-done and lane-failed)")
    notify_.add_argument("--message", help="text appended to the message on the command's stdin")

    status = add("status", cmd_status, "Every run task with its state, lane activity, touched files and hand-off queue.")
    status.add_argument("--run", help="only this run (default: every run, newest first)")
    status.add_argument("--fetch", action="store_true", help="fetch each mainline's remote first")
    status.add_argument("--allow-invalid", action="store_true")

    close = add("close", cmd_close, "Abandon a run: release its dispatches and resources, and hide it from next and status.")
    close.add_argument("run")
    close.add_argument("--reason", required=True, help="why the run is abandoned")

    merged_arguments(add("merged", cmd_merged, "Check by content whether a task branch was merged; optionally remove its worktree and branch."))
