"""Exclusive task claims: a file in the git common directory, optionally mirrored to a remote ref."""

from __future__ import annotations

import getpass
import json
import os
import socket
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

from taskrail import gitutil
from taskrail.config import Config

REMOTE_NAMESPACE = "refs/taskrail/claims"


class ClaimConflict(Exception):
    def __init__(self, message: str, claim: "Claim | None" = None):
        super().__init__(message)
        self.claim = claim


# Fields that describe the local machine; they stay out of the copy pushed to a remote.
LOCAL_ONLY_FIELDS = ("worktree", "host", "remote")


@dataclass
class Claim:
    id: str
    owner: str
    branch: str | None
    created: str
    worktree: str | None = None
    host: str = ""
    remote: dict | None = None  # {"name", "ref", "commit"} when mirrored to a remote
    base: dict | None = None  # {"onto", "commit", "dependency"}: where the task branch started
    run: str | None = None  # the autopilot run that owns the lane (DESIGN.md §12.4)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data) -> "Claim | None":
        """A claim from its JSON form, ignoring keys a later version may add."""
        if not isinstance(data, dict):
            return None
        known = {field.name for field in fields(cls)}
        try:
            return cls(**{key: value for key, value in data.items() if key in known})
        except TypeError:
            return None


def default_owner() -> str:
    return os.environ.get("TASKRAIL_OWNER") or f"{getpass.getuser()}@{socket.gethostname()}"


def claims_dir(config: Config) -> Path:
    return gitutil.common_dir(config.root) / "taskrail" / "claims"


def _path(config: Config, task_id: str) -> Path:
    return claims_dir(config) / f"{task_id}.json"


def _load(path: Path) -> Claim | None:
    try:
        return Claim.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def read(config: Config, task_id: str) -> Claim | None:
    return _load(_path(config, task_id))


def read_all(config: Config) -> dict[str, Claim]:
    directory = claims_dir(config)
    if not directory.is_dir():
        return {}
    found = {}
    for path in sorted(directory.glob("*.json")):
        claim = _load(path)
        if claim is not None:
            found[claim.id] = claim
    return found


def stale_reason(config: Config, claim: Claim, now: datetime | None = None) -> str | None:
    """Why a claim is abandoned, or None while it is live. Never releases anything."""
    if claim.worktree:
        path = Path(claim.worktree)
        if not path.exists() or path.resolve() not in gitutil.worktrees(config.root):
            return f"worktree {claim.worktree} no longer exists"
    if claim.branch and not gitutil.branch_exists(config.root, claim.branch):
        now = now or datetime.now(timezone.utc)
        age = now - datetime.fromisoformat(claim.created)
        if age >= timedelta(minutes=config.claim_grace_minutes):
            return f"branch {claim.branch} no longer exists"
    return None


def _write_exclusive(path: Path, claim: Claim) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(claim.to_dict(), handle, indent=2)


def _remote_ref(task_id: str) -> str:
    return f"{REMOTE_NAMESPACE}/{task_id}"


def read_remote(config: Config, task_id: str) -> Claim | None:
    remote = config.claim_remote
    ref = _remote_ref(task_id)
    listing = gitutil.run(config.root, "ls-remote", remote, ref).stdout.strip()
    if not listing:
        return None
    gitutil.run(config.root, "fetch", "--quiet", remote, ref)
    content = gitutil.run(config.root, "show", "FETCH_HEAD:claim.json", check=False).stdout
    try:
        return Claim.from_dict(json.loads(content))
    except json.JSONDecodeError:
        return None


def list_remote(config: Config) -> list[str]:
    output = gitutil.run(config.root, "ls-remote", config.claim_remote, f"{REMOTE_NAMESPACE}/*").stdout
    return sorted(line.split("\t", 1)[1].rsplit("/", 1)[1] for line in output.splitlines() if "\t" in line)


def _claim_commit(config: Config, claim: Claim) -> str:
    public = {key: value for key, value in claim.to_dict().items() if key not in LOCAL_ONLY_FIELDS}
    return gitutil.write_claim_commit(config.root, json.dumps(public, indent=2), f"taskrail claim {claim.id}")


def _push_remote(config: Config, claim: Claim) -> dict:
    ref = _remote_ref(claim.id)
    commit = _claim_commit(config, claim)
    result = gitutil.run(
        config.root, "push", "--quiet", "--porcelain", f"--force-with-lease={ref}:", config.claim_remote, f"{commit}:{ref}", check=False
    )
    if result.returncode != 0:
        existing = read_remote(config, claim.id)
        if existing is not None:
            raise ClaimConflict(f"{claim.id} is already claimed on {config.claim_remote} by {existing.owner}", existing)
        raise gitutil.GitError(f"could not push claim to {config.claim_remote}: {result.stderr.strip()}")
    return {"name": config.claim_remote, "ref": ref, "commit": commit}


def _delete_remote(config: Config, claim: Claim, force: bool) -> None:
    remote = claim.remote or {}
    ref = remote.get("ref", _remote_ref(claim.id))
    lease = f"--force-with-lease={ref}" if force else f"--force-with-lease={ref}:{remote.get('commit', '')}"
    result = gitutil.run(config.root, "push", "--quiet", lease, remote.get("name", config.claim_remote), f":{ref}", check=False)
    if result.returncode != 0 and gitutil.run(config.root, "ls-remote", remote.get("name", config.claim_remote), ref).stdout.strip():
        raise gitutil.GitError(f"could not delete remote claim {ref}: {result.stderr.strip()}")


def claim(
    config: Config,
    task_id: str,
    owner: str,
    branch: str | None,
    worktree: str | None,
    takeover: bool = False,
    local_only: bool = False,
    base: dict | None = None,
    run: str | None = None,
) -> tuple[Claim, bool]:
    """Create a claim. Returns (claim, created); created is False when the owner already held it."""
    path = _path(config, task_id)
    existing = _load(path)
    if existing is not None:
        if existing.owner == owner and existing.branch == branch:
            return existing, False
        reason = stale_reason(config, existing)
        if reason is None:
            raise ClaimConflict(f"{task_id} is claimed by {existing.owner} on branch {existing.branch or '—'}", existing)
        if not takeover:
            raise ClaimConflict(f"{task_id} is claimed by {existing.owner}, but the claim is stale ({reason}); pass --takeover", existing)
        release(config, task_id, owner, force=True, local_only=local_only)

    new = Claim(
        id=task_id,
        owner=owner,
        branch=branch,
        worktree=worktree,
        host=socket.gethostname(),
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        base=base,
        run=run,
    )
    try:
        _write_exclusive(path, new)
    except FileExistsError as exc:
        raise ClaimConflict(f"{task_id} was claimed concurrently", _load(path)) from exc

    if config.claim_remote and not local_only:
        try:
            new.remote = _push_remote(config, new)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        path.write_text(json.dumps(new.to_dict(), indent=2), encoding="utf-8")
    return new, True


def rename_branch(config: Config, task_id: str, branch: str, local_only: bool = False) -> Claim | None:
    """Point a claim at the task's renamed branch; its remote copy is re-pushed with a lease on the recorded commit."""
    path = _path(config, task_id)
    existing = _load(path)
    if existing is None:
        return None
    existing.branch = branch
    path.write_text(json.dumps(existing.to_dict(), indent=2), encoding="utf-8")
    if existing.remote and not local_only:
        remote = existing.remote
        ref = remote.get("ref", _remote_ref(task_id))
        name = remote.get("name", config.claim_remote)
        commit = _claim_commit(config, existing)
        lease = f"--force-with-lease={ref}:{remote.get('commit', '')}"
        result = gitutil.run(config.root, "push", "--quiet", "--porcelain", lease, name, f"{commit}:{ref}", check=False)
        if result.returncode != 0:
            raise gitutil.GitError(f"could not update the remote claim {ref} on {name}: {result.stderr.strip() or result.stdout.strip()}")
        existing.remote = {**remote, "commit": commit}
        path.write_text(json.dumps(existing.to_dict(), indent=2), encoding="utf-8")
    return existing


def release(config: Config, task_id: str, owner: str, force: bool = False, local_only: bool = False) -> Claim | None:
    path = _path(config, task_id)
    existing = _load(path)
    if existing is None:
        return None
    if existing.owner != owner and not force:
        raise ClaimConflict(f"{task_id} is claimed by {existing.owner}; pass --force to release someone else's claim", existing)
    if existing.remote and not local_only:
        _delete_remote(config, existing, force)
    path.unlink(missing_ok=True)
    return existing
