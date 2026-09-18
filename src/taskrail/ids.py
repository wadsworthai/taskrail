"""Race-free task ID reservation across branches and worktrees."""

from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from taskrail import gitutil
from taskrail.backlog import EPICS_TITLE, _index, _is_task_table
from taskrail.config import BacklogConfig, Config
from taskrail.markdown import parse_sections
from taskrail.model import NONE_MARKERS

LOCK_TIMEOUT = 10.0
LOCK_STALE_SECONDS = 60.0


class LockTimeout(Exception):
    pass


def _state_dir(config: Config) -> Path:
    return gitutil.common_dir(config.root) / "taskrail"


@contextmanager
def id_lock(config: Config):
    """A short-lived exclusive lock shared by every worktree of the clone."""
    path = _state_dir(config) / "ids.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT
    while True:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            os.write(descriptor, str(os.getpid()).encode())
            os.close(descriptor)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > LOCK_STALE_SECONDS:
                    path.unlink(missing_ok=True)  # a holder crashed; the lock is only ever held briefly
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise LockTimeout(f"could not acquire {path} within {LOCK_TIMEOUT:.0f}s")
            time.sleep(0.02)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _task_ids(text: str, prefix: str, aliases: dict[str, str] | None = None) -> set[str]:
    id_re = re.compile(rf"^{prefix}\d+$")
    found = set()
    for section in parse_sections(text):
        for table in section.tables:
            if not _is_task_table(table, aliases):
                continue
            position = _index(table.header, aliases)["ID"]
            for _, cells in table.rows:
                if position < len(cells) and id_re.match(cells[position]):
                    found.add(cells[position])
    return found


def _epic_files(text: str) -> list[str]:
    files = []
    for section in parse_sections(text):
        if section.title and section.title.strip().lower() == EPICS_TITLE:
            for table in section.tables:
                columns = _index(table.header)
                if "File" not in columns:
                    continue
                for _, cells in table.rows:
                    position = columns["File"]
                    if position < len(cells) and cells[position] not in NONE_MARKERS:
                        files.append(cells[position])
    return files


def used_ids(config: Config, backlog: BacklogConfig) -> set[str]:
    """IDs present in the backlog's files on the working tree and on every scanned branch."""
    found: set[str] = set()

    def scan(read) -> None:
        # The archive first: an ID whose row has moved there is used, or `new` would hand it out
        # again once the branches carrying the row are gone (DESIGN.md §6.3, §7.6).
        archived = read(backlog.archive_path)
        if archived is not None:
            found.update(_task_ids(archived, backlog.prefix, config.column_aliases))
        main = read(backlog.file)
        if main is None:
            return
        found.update(_task_ids(main, backlog.prefix, config.column_aliases))
        for epic_file in _epic_files(main):
            content = read(epic_file)
            if content is not None:
                found.update(_task_ids(content, backlog.prefix, config.column_aliases))

    def read_working(relative: str) -> str | None:
        try:
            return (config.root / relative).read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            return None

    scan(read_working)

    revisions = gitutil.refs(config.root, "refs/heads")
    if config.claim_remote:
        revisions += gitutil.refs(config.root, f"refs/remotes/{config.claim_remote}")
    mains = gitutil.read_blobs(config.root, [f"{rev}:{backlog.file}" for rev in revisions])
    epic_specs = [f"{rev}:{backlog.archive_path}" for rev in revisions]
    for rev in revisions:
        text = mains.get(f"{rev}:{backlog.file}")
        if text is None:
            continue
        found.update(_task_ids(text, backlog.prefix, config.column_aliases))
        epic_specs += [f"{rev}:{path}" for path in _epic_files(text)]
    for text in gitutil.read_blobs(config.root, epic_specs).values():
        if text is not None:
            found.update(_task_ids(text, backlog.prefix, config.column_aliases))
    return found


def _number(task_id: str, prefix: str) -> int:
    return int(task_id[len(prefix):])


def _reservations_path(config: Config, backlog: BacklogConfig) -> Path:
    return _state_dir(config) / "reserved" / f"{backlog.name}.json"


def reservations(config: Config, backlog: BacklogConfig) -> list[dict]:
    try:
        return json.loads(_reservations_path(config, backlog).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def reserve(config: Config, backlog: BacklogConfig, owner: str) -> str:
    """Reserve the next ID: one above everything used on any branch or reserved and not yet used."""
    with id_lock(config):
        used = used_ids(config, backlog)
        pending = [r for r in reservations(config, backlog) if r["id"] not in used]
        numbers = [_number(i, backlog.prefix) for i in used] + [_number(r["id"], backlog.prefix) for r in pending]
        task_id = f"{backlog.prefix}{max(numbers, default=0) + 1:0{backlog.id_digits}d}"
        pending.append({"id": task_id, "owner": owner, "created": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        _store_reservations(config, backlog, pending)
        return task_id


def _store_reservations(config: Config, backlog: BacklogConfig, entries: list[dict]) -> None:
    path = _reservations_path(config, backlog)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    temporary.replace(path)


def keep_reservation(config: Config, backlog: BacklogConfig, task_id: str, owner: str) -> bool:
    """Reserve an ID a row already has, unless it is reserved; True when a reservation was added.

    `reserve` drops a reservation once its ID appears in a scanned file, so a row moved into an
    uncommitted workspace needs its ID reserved again until it is committed (T070).
    """
    with id_lock(config):
        current = reservations(config, backlog)
        if any(r["id"] == task_id for r in current):
            return False
        current.append({"id": task_id, "owner": owner, "created": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        _store_reservations(config, backlog, current)
        return True


def cancel_reservation(config: Config, backlog: BacklogConfig, task_id: str) -> bool:
    with id_lock(config):
        current = reservations(config, backlog)
        remaining = [r for r in current if r["id"] != task_id]
        if len(remaining) == len(current):
            return False
        _reservations_path(config, backlog).write_text(json.dumps(remaining, indent=2), encoding="utf-8")
        return True
