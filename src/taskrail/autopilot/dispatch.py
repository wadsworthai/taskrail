"""`autopilot next`: the tasks to dispatch now, and the resources each lane gets (DESIGN.md §12.1, §12.7).

Lanes, groups and resource values are shared by every open run in the clone; a closed run is ignored.
A lane is in use while its task is `running`, `gate` or `dispatched`; a lane that stopped using one
gives its resource values back the next time `next` runs. A task `escalated` or `parked` keeps its
claim, branch and worktree but no lane, and a `parked` task — one whose escalation the human has
answered — is redispatched before any task that has never started (T105). Claiming stays the lane's
job.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from taskrail import claims as claims_module
from taskrail import branchrows, prior, stack
from taskrail.autopilot import runs
from taskrail.autopilot.status import OCCUPYING, discarded_on_mainline, done_on_mainline, task_state
from taskrail.claims import Claim
from taskrail.config import GroupConfig
from taskrail.model import Project, Task
from taskrail.query import base_dict, blocked_by, eligible, state, task_dict
from taskrail.templates import render

# toward a run's count; `escalated`, `parked` and `failed` wait for a human and keep their place (T105)
COUNTED = ("dispatched", "running", "gate", "escalated", "parked", "failed", "done-branch", "handed-off", "done-merged")
ENVIRONMENT_PREFIX = "TASKRAIL_RESOURCE_"


def run_kinds(project: Project, run: dict | None) -> set[str] | None:
    """Kinds a run drives: both lists intersected when both are set, else whichever is; None means every kind."""
    of_run = set(run["kinds"]) if run else set()
    of_config = set(project.config.autopilot.kinds)
    if of_run and of_config:
        return of_run & of_config
    return (of_run or of_config) or None


@contextmanager
def _read_only(config):
    yield {run["id"]: run for run in runs.read_all(config)}


def _members(run: dict, claimed: dict[str, Claim]) -> list[str]:
    """The run's lanes: the tasks it records and those whose claim names it; a named task not dispatched yet holds none."""
    extra = sorted(task_id for task_id, claim in claimed.items() if claim.run == run["id"] and task_id not in run["tasks"])
    return list(run["tasks"]) + extra


def _waiting_reason(project: Project, task_id: str, claimed: dict[str, Claim]) -> str:
    """Why a named task that is not eligible waits (T071)."""
    task = project.task(task_id)
    if task is None:
        return "not in the backlog nor on a recorded branch"
    found = state(task, project, claimed)
    if found == "blocked":
        return f"blocked by {', '.join(blocked_by(task, project))}"
    if found == "claimed":
        claim = claimed[task_id]
        return f"claimed in run {claim.run}" if claim.run else f"claimed by {claim.owner}"
    return found


def _groups_of(task: Task, recorded: str | None, groups: tuple[GroupConfig, ...]) -> list[str]:
    """The configured groups a task counts toward: column groups it matches, and a recorded judgement group."""
    names = []
    for group in groups:
        if group.predicate is not None:
            if group.predicate.matches(task.columns):
                names.append(group.name)
        elif group.name == recorded:
            names.append(group.name)
    return names


def next_lanes(project: Project, run_id: str | None, claimed: dict[str, Claim], now: datetime | None = None) -> dict:
    """Choose the tasks to dispatch now. With a run, records them and releases ended lanes' resources."""
    now = now or datetime.now(timezone.utc)
    config = project.config
    autopilot = config.autopilot
    stored_runs = [record for record in runs.read_all(config) if not runs.is_closed(record)]
    # Rows that only their task's branch holds count as in any checkout: before anything reads the rows (T071).
    branchrows.adopt(project, [task_id for record in stored_runs for task_id in runs.members(record, claimed)], claimed)
    candidates = eligible(project, None, claimed)
    stack.done_on_branch(project)  # read git before the lock; both are cached per project
    merged, discarded = done_on_mainline(project), discarded_on_mainline(project)

    with runs.update_all(config) if run_id else _read_only(config) as stored:
        run = stored.get(run_id) if run_id else None
        if run_id and run is None:
            raise runs.RunNotFound(f"no autopilot run `{run_id}`")
        if runs.is_closed(run):
            raise runs.RunClosed(runs.closed_message(run_id))
        every_run = {record_id: record for record_id, record in stored.items() if not runs.is_closed(record)}  # a closed run holds nothing (T048)

        # The state of every lane, in every run.
        states: dict[tuple[str, str], str | None] = {}
        for record in every_run.values():
            for task_id in _members(record, claimed):
                task = project.task(task_id)
                if task is not None:
                    states[record["id"], task_id] = task_state(task, project, record, claimed.get(task_id), now)
                else:  # a claim in this run still uses a lane when its row cannot be found anywhere (T071)
                    claim = claimed.get(task_id)
                    states[record["id"], task_id] = "running" if claim is not None and claim.run == record["id"] else None

        occupied: dict[str, dict] = {}  # task ID -> the lane using it
        for (record_id, task_id), state in states.items():
            if state not in OCCUPYING or task_id in occupied:
                continue
            claim = claimed.get(task_id)
            if claim is not None and claim.run in every_run and claim.run != record_id and states.get((claim.run, task_id)) in OCCUPYING:
                record_id = claim.run  # the run that owns the claim
            occupied[task_id] = {"id": task_id, "run": record_id, "state": states[record_id, task_id]}

        released = []
        for record in every_run.values():
            for task_id, lane in record["tasks"].items():
                if lane["resources"] and states.get((record["id"], task_id)) not in OCCUPYING:
                    released.append({"id": task_id, "run": record["id"], "resources": dict(lane["resources"])})
                    if run is not None:
                        lane["resources"] = {}

        def recorded_group(task_id: str, preferred: str | None) -> str | None:
            order = [every_run[preferred]] if preferred in every_run else []
            order += [record for record in every_run.values() if record["id"] != preferred]
            return next((record["tasks"][task_id]["group"] for record in order if (record["tasks"].get(task_id) or {}).get("group")), None)

        members: dict[str, list[str]] = {group.name: [] for group in autopilot.groups}
        held: dict[str, dict[str, str]] = {resource.name: {} for resource in autopilot.resources}
        for task_id, lane in occupied.items():
            task = project.task(task_id)
            lane["groups"] = _groups_of(task, recorded_group(task_id, lane["run"]), autopilot.groups) if task else []
            for name in lane["groups"]:
                members[name].append(task_id)
        for (record_id, task_id), state in states.items():
            if state in OCCUPYING:
                for name, value in every_run[record_id]["tasks"].get(task_id, {}).get("resources", {}).items():
                    held.get(name, {}).setdefault(value, task_id)

        remaining = None
        if run is not None:
            remaining = run["count"] - sum(1 for task_id in _members(run, claimed) if states.get((run["id"], task_id)) in COUNTED)
        kinds = run_kinds(project, run)
        limits = {group.name: group.limit for group in autopilot.groups}
        named = list(run["named"]) if runs.is_named(run) else None
        if named is not None:  # a named run takes only its tasks, in the order given (T071)
            by_id = {task.id: task for task in candidates}
            candidates = [by_id[task_id] for task_id in named if task_id in by_id]

        chosen: list[tuple[Task, dict, list[str], bool]] = []
        skipped: list[dict] = []
        limited_by = None

        def give_a_lane(task: Task, groups: list[str], *, restart: bool) -> None:
            """Put a task in a lane: the first free value of every resource, its place in each group, the run's record."""
            allocated = {}
            for resource in autopilot.resources:
                value = next(v for v in resource.values if v not in held[resource.name])
                held[resource.name][value] = task.id
                allocated[resource.name] = value
            occupied[task.id] = {"id": task.id, "run": run_id, "state": "dispatched", "groups": groups}
            for name in groups:
                members[name].append(task.id)
            if run is not None:
                if restart:  # a parked lane is on its way back: it leaves its gate and its answer behind (T105)
                    runs.record_lane(run, task.id, state="running", now=now)
                lane = runs.lane(run, task.id)
                lane[runs.DISPATCHED] = runs.now_iso(now)
                lane["resources"] = allocated
            chosen.append((task, allocated, groups, restart))

        # Parked lanes first: the human has answered, the workspace is there, and the run's count already holds them (T105).
        parked: list[dict] = []
        answered = sorted(
            ((every_run[record_id]["tasks"].get(task_id) or {}).get("updated") or "", task_id, record_id)
            for (record_id, task_id), found in states.items()
            if found == runs.PARKED
        )
        for _, task_id, record_id in answered:
            task = project.task(task_id)
            lane_record = every_run[record_id]["tasks"].get(task_id) or {}
            groups = _groups_of(task, recorded_group(task_id, record_id), autopilot.groups)
            full = next((name for name in groups if len(members[name]) >= limits[name]), None)
            exhausted = next((r.name for r in autopilot.resources if all(v in held[r.name] for v in r.values)), None)
            if run is None or record_id != run_id:
                why = f"needs --run {record_id}"
            elif autopilot.max_lanes - len(occupied) <= 0:
                why = "no free lane"
                limited_by = limited_by or "max_lanes"
            elif full:
                why = f"group {full} is full"
            elif exhausted:
                why = f"resource:{exhausted}"
            else:
                why = None
            parked.append(
                {"id": task_id, "run": record_id, "gate": lane_record.get("gate"), "reason": lane_record.get("reason"), "dispatched": why is None, "why": why}
            )
            if why is None:
                give_a_lane(task, groups, restart=True)

        for task in candidates:
            if kinds is not None and task.kind not in kinds:
                if named is not None:
                    skipped.append({"id": task.id, "reason": f"kind {task.kind} is not driven by run {run_id}"})
                continue
            if autopilot.max_lanes - len(occupied) <= 0:
                limited_by = "max_lanes"
                break
            if remaining is not None and remaining <= 0:
                limited_by = "count"
                break
            exhausted = next((r.name for r in autopilot.resources if all(v in held[r.name] for v in r.values)), None)
            if exhausted:
                limited_by = f"resource:{exhausted}"
                break

            reason = None
            failed_in = [record["id"] for record in ([run] if run else every_run.values()) if (record["tasks"].get(task.id) or {}).get("state") == "failed"]
            # An unclaimed candidate may still hold a lane: dispatched, recorded at a gate, or closing (T054).
            occupying_in = [(record_id, state) for (record_id, task_id), state in states.items() if task_id == task.id and state in OCCUPYING]
            if not occupying_in and task.id in occupied:  # a parked lane this call just sent back, whose claim was released (T105)
                occupying_in = [(occupied[task.id]["run"], occupied[task.id]["state"])]
            groups = _groups_of(task, recorded_group(task.id, run_id), autopilot.groups)
            full = next((name for name in groups if len(members[name]) >= limits[name]), None)
            if task.id in merged or task.id in discarded:
                # Closed on a mainline ref the checkout has not pulled: `autopilot status` reads it closed (T064).
                reason = ("done-merged" if task.id in merged else "discarded") + " on the mainline, not in this checkout"
            elif failed_in:
                reason = f"failed in run {failed_in[0]}"
            elif occupying_in:
                reason = f"{occupying_in[0][1]} in run {occupying_in[0][0]}"
            elif full:
                reason = f"group {full} is full"
            else:
                base = base_dict(task, project)
                if base is None or not base["onto"]:
                    reason = ("base diverged: " if base and base["diverged"] else "no base: ") + (base["reason"] if base else "no mainline")
                elif base["row"] == "missing":
                    # Only this checkout has the row: a lane's workspace from `onto` could not claim it (T070).
                    reason = f"row not on {base['onto']}: run taskrail workspace {task.id}"
            if reason:
                skipped.append({"id": task.id, "reason": reason})
                continue

            give_a_lane(task, groups, restart=False)
            if remaining is not None:
                remaining -= 1

        if named is not None:
            listed = {task.id for task in candidates} | {entry["id"] for entry in skipped}
            for task_id in named:
                if task_id not in listed and states.get((run_id, task_id)) not in (*COUNTED, *OCCUPYING):
                    skipped.append({"id": task_id, "reason": _waiting_reason(project, task_id, claimed)})

    return {
        "run": run_id,
        "preview": run is None,
        "dispatch": [_entry(task, project, claimed, allocated, groups, restart) for task, allocated, groups, restart in chosen],
        "lanes": {
            "max": autopilot.max_lanes,
            "occupied": [
                {**lane, "stale": claims_module.stale_reason(config, claimed[lane["id"]]) if lane["id"] in claimed else None}
                for lane in sorted(occupied.values(), key=lambda lane: lane["id"])
            ],
            "free": max(0, autopilot.max_lanes - len(occupied)),
        },
        "remaining": remaining,
        "groups": [
            {
                "name": group.name,
                "limit": group.limit,
                "column": group.predicate.column if group.predicate else None,
                "match": list(group.predicate.match) if group.predicate else [],
                "members": sorted(members[group.name]),
                "free": max(0, group.limit - len(members[group.name])),
            }
            for group in autopilot.groups
        ],
        "resources": [
            {
                "name": resource.name,
                "values": list(resource.values),
                "held": {value: held[resource.name][value] for value in resource.values if value in held[resource.name]},
                "free": [value for value in resource.values if value not in held[resource.name]],
            }
            for resource in autopilot.resources
        ],
        "released": released,
        "parked": parked,
        "skipped": skipped,
        "limited_by": limited_by,
    }


def _entry(task: Task, project: Project, claimed: dict[str, Claim], allocated: dict[str, str], groups: list[str], restart: bool) -> dict:
    """`show --json`'s fields for a dispatched task, plus what its lane brief needs."""
    config = project.config
    data = task_dict(task, project, claimed)
    kind = project.kinds.get(task.kind)
    data["kind_descriptor"] = kind.to_dict(task) if kind else None
    data["prior_work"] = prior.prior_work(
        config.root, task.id, data["branch"], data["artifact"], onto=(data["base"] or {}).get("onto"), backlog_file=config.backlog(task.backlog).file
    )
    data["resources"] = dict(allocated)
    data["environment"] = {f"{ENVIRONMENT_PREFIX}{name}": value for name, value in allocated.items()}
    data["groups"] = list(groups)
    data["decisions"] = render(config.autopilot.decisions, task, config)
    data["decisions_index"] = render(config.autopilot.decisions_index, task, config)
    data["restart"] = restart  # a parked lane returning to its own branch and worktree (T105)
    return data


def text(report: dict) -> str:
    lines = []
    for task in report["dispatch"]:
        values = " ".join(f"{name}={value}" for name, value in task["resources"].items())
        base = (task["base"] or {}).get("onto") or "—"
        lines.append(
            f"{task['id']:<6} {task['kind']:<8} {task['branch'] or '—'}  base {base}"
            + (f"  {values}" if values else "")
            + ("  restart" if task.get("restart") else "")
        )
    for entry in report["parked"]:
        what = "restarted" if entry["dispatched"] else f"waiting: {entry['why']}"
        at_gate = f" at {entry['gate']}" if entry["gate"] else ""
        lines.append(f"  parked {entry['id']} (run {entry['run']}){at_gate}: {what}")
    for entry in report["skipped"]:
        lines.append(f"  skipped {entry['id']}: {entry['reason']}")
    for entry in report["released"]:
        values = " ".join(f"{name}={value}" for name, value in entry["resources"].items())
        lines.append(f"  released {values} from {entry['id']} (run {entry['run']})")
    lanes = report["lanes"]
    summary = [f"dispatched {len(report['dispatch'])}" if report["dispatch"] else "nothing to dispatch"]
    summary.append(f"{len(lanes['occupied'])}/{lanes['max']} lanes in use")
    waiting = [entry for entry in report["parked"] if not entry["dispatched"]]
    if waiting:
        summary.append(f"{len(waiting)} parked waiting for a lane")
    if report["remaining"] is not None:
        summary.append(f"{report['remaining']} more for run {report['run']}")
    if report["limited_by"]:
        summary.append(f"limited by {report['limited_by']}")
    if report["preview"]:
        summary.append("preview: nothing recorded")
    lines.append(" · ".join(summary))
    return "\n".join(lines)
