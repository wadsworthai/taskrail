"""`autopilot next`: the tasks to dispatch now, and the resources each lane gets (DESIGN.md §12.1, §12.7).

Lanes, groups and resource values are shared by every run in the clone. A lane is in use while its
task is `running`, `gate`, `escalated` or `dispatched`; a lane that stopped using one gives its
resource values back the next time `next` runs. Claiming stays the lane's job.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from taskrail import claims as claims_module
from taskrail import prior, stack
from taskrail.autopilot import runs
from taskrail.autopilot.status import done_on_mainline, task_state
from taskrail.claims import Claim
from taskrail.config import GroupConfig
from taskrail.model import Project, Task
from taskrail.query import base_dict, eligible, task_dict
from taskrail.templates import render

OCCUPYING = ("running", "gate", "escalated", "dispatched")  # states that use a lane and hold resources
COUNTED = ("dispatched", "running", "gate", "escalated", "failed", "done-branch", "handed-off", "done-merged")  # toward a run's count
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
    extra = sorted(task_id for task_id, claim in claimed.items() if claim.run == run["id"] and task_id not in run["tasks"])
    return list(run["tasks"]) + extra


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
    candidates = eligible(project, None, claimed)
    stack.done_on_branch(project)  # read git before the lock; both are cached per project
    done_on_mainline(project)

    with runs.update_all(config) if run_id else _read_only(config) as every_run:
        run = every_run.get(run_id) if run_id else None
        if run_id and run is None:
            raise runs.RunNotFound(f"no autopilot run `{run_id}`")

        # The state of every lane, in every run.
        states: dict[tuple[str, str], str | None] = {}
        for record in every_run.values():
            for task_id in _members(record, claimed):
                task = project.task(task_id)
                states[record["id"], task_id] = task_state(task, project, record, claimed.get(task_id), now) if task else None

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
            lane["groups"] = _groups_of(task, recorded_group(task_id, lane["run"]), autopilot.groups)
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

        chosen: list[tuple[Task, dict, list[str]]] = []
        skipped: list[dict] = []
        limited_by = None
        for task in candidates:
            if kinds is not None and task.kind not in kinds:
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
            groups = _groups_of(task, recorded_group(task.id, run_id), autopilot.groups)
            full = next((name for name in groups if len(members[name]) >= limits[name]), None)
            if failed_in:
                reason = f"failed in run {failed_in[0]}"
            elif occupying_in:
                reason = f"{occupying_in[0][1]} in run {occupying_in[0][0]}"
            elif full:
                reason = f"group {full} is full"
            else:
                base = base_dict(task, project)
                if base is None or not base["onto"]:
                    reason = ("base diverged: " if base and base["diverged"] else "no base: ") + (base["reason"] if base else "no mainline")
            if reason:
                skipped.append({"id": task.id, "reason": reason})
                continue

            allocated = {}
            for resource in autopilot.resources:
                value = next(v for v in resource.values if v not in held[resource.name])
                held[resource.name][value] = task.id
                allocated[resource.name] = value
            occupied[task.id] = {"id": task.id, "run": run_id, "state": "dispatched", "groups": groups}
            for name in groups:
                members[name].append(task.id)
            if remaining is not None:
                remaining -= 1
            if run is not None:
                lane = runs.lane(run, task.id)
                lane[runs.DISPATCHED] = runs.now_iso(now)
                lane["resources"] = allocated
            chosen.append((task, allocated, groups))

    return {
        "run": run_id,
        "preview": run is None,
        "dispatch": [_entry(task, project, claimed, allocated, groups) for task, allocated, groups in chosen],
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
        "skipped": skipped,
        "limited_by": limited_by,
    }


def _entry(task: Task, project: Project, claimed: dict[str, Claim], allocated: dict[str, str], groups: list[str]) -> dict:
    """`show --json`'s fields for a dispatched task, plus what its lane brief needs."""
    config = project.config
    data = task_dict(task, project, claimed)
    kind = project.kinds.get(task.kind)
    data["kind_descriptor"] = kind.to_dict(task) if kind else None
    data["prior_work"] = prior.prior_work(config.root, task.id, data["branch"], data["artifact"])
    data["resources"] = dict(allocated)
    data["environment"] = {f"{ENVIRONMENT_PREFIX}{name}": value for name, value in allocated.items()}
    data["groups"] = list(groups)
    data["decisions"] = render(config.autopilot.decisions, task, config)
    data["decisions_index"] = render(config.autopilot.decisions_index, task, config)
    return data


def text(report: dict) -> str:
    lines = []
    for task in report["dispatch"]:
        values = " ".join(f"{name}={value}" for name, value in task["resources"].items())
        base = (task["base"] or {}).get("onto") or "—"
        lines.append(f"{task['id']:<6} {task['kind']:<8} {task['branch'] or '—'}  base {base}" + (f"  {values}" if values else ""))
    for entry in report["skipped"]:
        lines.append(f"  skipped {entry['id']}: {entry['reason']}")
    for entry in report["released"]:
        values = " ".join(f"{name}={value}" for name, value in entry["resources"].items())
        lines.append(f"  released {values} from {entry['id']} (run {entry['run']})")
    lanes = report["lanes"]
    summary = [f"dispatched {len(report['dispatch'])}" if report["dispatch"] else "nothing to dispatch"]
    summary.append(f"{len(lanes['occupied'])}/{lanes['max']} lanes in use")
    if report["remaining"] is not None:
        summary.append(f"{report['remaining']} more for run {report['run']}")
    if report["limited_by"]:
        summary.append(f"limited by {report['limited_by']}")
    if report["preview"]:
        summary.append("preview: nothing recorded")
    lines.append(" · ".join(summary))
    return "\n".join(lines)
