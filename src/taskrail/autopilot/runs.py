"""Autopilot run files: the local state git cannot derive (DESIGN.md §12.4).

A run file lives at `<git common dir>/taskrail/runs/<run>.json`, next to the claims, and is
never committed. It is written only by the CLI: created exclusively, changed under the
common-directory lock `reserve-id` uses, and replaced atomically. Keys this version does not
know are kept as they are, so a later version's fields survive an older CLI's update.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from taskrail import gitutil, ids
from taskrail.config import Config

RUN_ID_RE = re.compile(r"^(\d{8})-([1-9]\d*)$")
LANE_STATES = ("running", "gate", "escalated", "failed")  # what `autopilot lane --state` records
REASON_REQUIRED = ("escalated", "failed")
HANDED_OFF = "handed-off"
DISPATCHED = "dispatched"  # recorded by `autopilot next` until the lane claims or the dispatch expires
GATE_STATES = ("gate", "escalated")  # states `lane --gate` records a stage for
GATE_CLEARING = ("running", "failed")


class RunNotFound(Exception):
    pass


class RunClosed(Exception):
    pass


def now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def runs_dir(config: Config) -> Path:
    return gitutil.common_dir(config.root) / "taskrail" / "runs"


def _path(config: Config, run_id: str) -> Path | None:
    return runs_dir(config) / f"{run_id}.json" if RUN_ID_RE.match(run_id or "") else None


def _normalize(data) -> dict | None:
    """A run from its JSON form, with missing keys filled in and unknown keys kept."""
    if not isinstance(data, dict) or not isinstance(data.get("id"), str):
        return None
    run = dict(data)
    run.setdefault("started", None)
    run.setdefault("owner", None)
    run.setdefault("count", 0)
    run.setdefault("kinds", [])
    run.setdefault("closed", None)
    if not isinstance(run.get("named"), list):
        run["named"] = []  # a run started with --count names no tasks (T071)
    for key, empty in (("tasks", dict), ("handed_off", list), ("decisions", list)):
        if not isinstance(run.get(key), empty):
            run[key] = empty()
    for task_id, lane in list(run["tasks"].items()):
        run["tasks"][task_id] = _lane(lane if isinstance(lane, dict) else {})
    return run


def _lane(entry: dict) -> dict:
    lane = dict(entry)
    for key, default in (("handle", None), ("group", None), ("state", "running"), ("reason", None), ("updated", None), ("dispatched", None)):
        lane.setdefault(key, default)
    if not isinstance(lane.get("resources"), dict):
        lane["resources"] = {}
    return lane


def _load(path: Path) -> dict | None:
    try:
        return _normalize(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def read(config: Config, run_id: str) -> dict | None:
    path = _path(config, run_id)
    return _load(path) if path else None


def _sort_key(run: dict) -> tuple[str, int]:
    match = RUN_ID_RE.match(run["id"])
    return (match.group(1), int(match.group(2))) if match else ("", 0)


def read_all(config: Config) -> list[dict]:
    """Every run in the common directory, newest first."""
    directory = runs_dir(config)
    if not directory.is_dir():
        return []
    found = [run for path in directory.glob("*.json") if RUN_ID_RE.match(path.stem) and (run := _load(path))]
    return sorted(found, key=_sort_key, reverse=True)


def _serialize(run: dict) -> str:
    return json.dumps(run, ensure_ascii=False, indent=2) + "\n"


def _temporary(directory: Path, content: str) -> Path:
    descriptor, name = tempfile.mkstemp(dir=directory, prefix=".run-", suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    return Path(name)


def create(config: Config, count: int, kinds: list[str], owner: str, now: datetime | None = None, named: list[str] | None = None) -> dict:
    """Write a new run as `YYYYMMDD-N`, taking the first number of the UTC day nobody holds.

    `named` lists the only tasks the run works, in the order `next` takes them (T071).
    """
    now = now or datetime.now(timezone.utc)
    directory = runs_dir(config)
    directory.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y%m%d")
    number = 1
    while True:
        run_id = f"{day}-{number}"
        run = _normalize(
            {"id": run_id, "started": now_iso(now), "owner": owner, "count": count, "kinds": list(kinds), "named": list(named or [])}
        )
        temporary = _temporary(directory, _serialize(run))
        try:
            os.link(temporary, directory / f"{run_id}.json")  # fails if the ID is taken; never half-written
            return run
        except FileExistsError:
            number += 1
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def update(config: Config, run_id: str):
    """Yield a run to change in place; it is written back atomically when the block ends."""
    path = _path(config, run_id)
    if path is None or not path.is_file():
        raise RunNotFound(f"no autopilot run `{run_id}`")
    with ids.id_lock(config):
        run = _load(path)
        if run is None:
            raise RunNotFound(f"autopilot run `{run_id}` cannot be read: {path}")
        yield run
        temporary = _temporary(path.parent, _serialize(run))
        os.replace(temporary, path)


@contextmanager
def update_all(config: Config):
    """Yield every run, newest first and keyed by ID, under one hold of the lock.

    For a change that reads or writes several runs at once, such as `autopilot next`: the lock is
    not re-entrant, so `update` cannot be nested. Each run that changed is replaced atomically when
    the block ends; nothing is written when it raises.
    """
    with ids.id_lock(config):
        loaded = {run["id"]: run for run in read_all(config)}
        before = {run_id: _serialize(run) for run_id, run in loaded.items()}
        yield loaded
        for run_id, run in loaded.items():
            content = _serialize(run)
            if content != before[run_id]:
                path = runs_dir(config) / f"{run_id}.json"
                os.replace(_temporary(path.parent, content), path)


def dispatch_live(entry: dict, grace_minutes: int, now: datetime | None = None) -> bool:
    """Whether a lane's dispatch still holds its place: recorded less than `grace_minutes` ago."""
    value = entry.get(DISPATCHED)
    if not isinstance(value, str):
        return False
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return False
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - moment < timedelta(minutes=grace_minutes)


def is_closed(run: dict | None) -> bool:
    """Whether `autopilot close` ended the run (T048)."""
    return bool(run) and isinstance(run.get("closed"), dict)


def closed_message(run_id: str) -> str:
    return f"autopilot run `{run_id}` is closed"


def close(run: dict, reason: str, owner: str, now: datetime | None = None) -> list[dict]:
    """Record the close and release every lane's dispatch and resources; return what was released."""
    released = []
    for task_id, entry in run["tasks"].items():
        if entry.get(DISPATCHED) or entry.get("resources"):
            released.append({"id": task_id, "dispatched": entry.get(DISPATCHED), "resources": dict(entry.get("resources") or {})})
        entry[DISPATCHED] = None
        entry["resources"] = {}
    run["closed"] = {"at": now_iso(now), "by": owner, "reason": reason}
    return released


def lane(run: dict, task_id: str) -> dict:
    """The run's record of a task's lane, created when missing."""
    return run["tasks"].setdefault(task_id, _lane({}))


def record_lane(
    run: dict,
    task_id: str,
    *,
    handle: str | None = None,
    group: str | None = None,
    state: str | None = None,
    reason: str | None = None,
    gate: str | None = None,
    now: datetime | None = None,
) -> dict:
    entry = lane(run, task_id)
    if handle is not None:
        entry["handle"] = handle
    if group is not None:
        entry["group"] = group
    if state is not None:
        entry["state"] = state
        entry["reason"] = None
    if reason is not None:
        entry["reason"] = reason
    if state in GATE_CLEARING:
        entry["gate"] = None  # the lane has left its gate
    if gate is not None:
        entry["gate"] = gate
    entry["updated"] = now_iso(now)
    return entry


def hand_off(run: dict, task_id: str) -> None:
    """Append a task to the run's hand-off order once."""
    if task_id not in run["handed_off"]:
        run["handed_off"].append(task_id)


def members(run: dict, claimed: dict) -> list[str]:
    """The run's tasks: those it records, those it names but has not dispatched yet (T071), and those whose claim names it."""
    found = list(run["tasks"])
    found += [task_id for task_id in run.get("named") or [] if task_id not in found]
    found += sorted(task_id for task_id, claim in claimed.items() if claim.run == run["id"] and task_id not in found)
    return found


def is_named(run: dict | None) -> bool:
    """Whether the run was started with `--tasks`: it works only the tasks it names (T071)."""
    return bool(run) and bool(run.get("named"))


def add_named(run: dict, task_ids: list[str]) -> list[str]:
    """Append the IDs not yet named, raising the count by as many; return the IDs appended (T071)."""
    added = [task_id for task_id in dict.fromkeys(task_ids) if task_id not in run["named"]]
    run["named"].extend(added)
    run["count"] += len(added)
    return added


def add_decision(run: dict, question: str, decision: str, reason: str, now: datetime | None = None) -> dict:
    entry = {
        "number": len(run["decisions"]) + 1,
        "question": question,
        "decision": decision,
        "reason": reason,
        "recorded": now_iso(now),
    }
    run["decisions"].append(entry)
    return entry
