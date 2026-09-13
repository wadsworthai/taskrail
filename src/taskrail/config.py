"""Loading and checking `.taskrail/config.toml`."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from taskrail.issues import ConfigError

CONFIG_PATH = Path(".taskrail") / "config.toml"
PREFIX_RE = re.compile(r"^[A-Z]{1,4}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


@dataclass(frozen=True)
class BacklogConfig:
    name: str
    prefix: str
    file: str
    mainline: str = "main"
    artifacts: str = "docs"
    may_depend_on: tuple[str, ...] = ()
    epic_prefix: str = "E"
    id_digits: int = 3


@dataclass(frozen=True)
class Config:
    root: Path
    version: str | None
    backlogs: tuple[BacklogConfig, ...]
    custom_columns: tuple[str, ...] = ()
    points_scale: tuple[int, ...] = ()
    push_task_branch: bool = False
    claim_remote: str = ""
    claim_grace_minutes: int = 15
    worktree: str = "required"  # "required" | "never"
    worktree_dir: str = ".worktrees"
    checks: dict[str, str] = field(default_factory=dict)

    def backlog(self, name: str) -> BacklogConfig | None:
        return next((b for b in self.backlogs if b.name == name), None)


def find_root(start: Path) -> Path:
    """Walk up from `start` to the directory holding `.taskrail/config.toml`."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / CONFIG_PATH).is_file():
            return directory
    raise ConfigError(
        f"no {CONFIG_PATH} found in {start} or any parent directory; run `taskrail init`"
    )


def load_config(root: Path) -> Config:
    path = root / CONFIG_PATH
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{CONFIG_PATH} not found in {root}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{CONFIG_PATH}: invalid TOML: {exc}") from exc

    problems: list[str] = []

    def expect(table: dict, key: str, kind: type, default=None, required: bool = False):
        if key not in table:
            if required:
                problems.append(f"missing required key `{key}`")
            return default
        value = table[key]
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            problems.append(f"`{key}` must be {kind.__name__}, got {type(value).__name__}")
            return default
        return value

    version = expect(data, "version", str)

    raw_backlogs = data.get("backlog", [])
    if not isinstance(raw_backlogs, list) or not raw_backlogs:
        problems.append("at least one [[backlog]] table is required")
        raw_backlogs = []

    backlogs: list[BacklogConfig] = []
    for index, raw in enumerate(raw_backlogs):
        if not isinstance(raw, dict):
            problems.append(f"[[backlog]] #{index + 1} must be a table")
            continue
        name = expect(raw, "name", str, required=True)
        prefix = expect(raw, "prefix", str, required=True)
        file = expect(raw, "file", str, required=True)
        if name is None or prefix is None or file is None:
            continue
        label = f"backlog `{name}`"
        if not NAME_RE.match(name):
            problems.append(f"{label}: name must be lowercase letters, digits and dashes")
        if not PREFIX_RE.match(prefix):
            problems.append(f"{label}: prefix `{prefix}` must be 1-4 uppercase letters")
        epic_prefix = expect(raw, "epic_prefix", str, "E")
        if not PREFIX_RE.match(epic_prefix):
            problems.append(f"{label}: epic_prefix `{epic_prefix}` must be 1-4 uppercase letters")
        if epic_prefix == prefix:
            problems.append(f"{label}: epic_prefix and prefix must differ")
        id_digits = expect(raw, "id_digits", int, 3)
        if not 1 <= id_digits <= 6:
            problems.append(f"{label}: id_digits must be between 1 and 6")
        may_depend_on = expect(raw, "may_depend_on", list, [])
        if not all(isinstance(item, str) for item in may_depend_on):
            problems.append(f"{label}: may_depend_on must be a list of backlog names")
            may_depend_on = []
        backlogs.append(
            BacklogConfig(
                name=name,
                prefix=prefix,
                file=file,
                mainline=expect(raw, "mainline", str, "main"),
                artifacts=expect(raw, "artifacts", str, "docs"),
                may_depend_on=tuple(may_depend_on),
                epic_prefix=epic_prefix,
                id_digits=id_digits,
            )
        )

    names = [b.name for b in backlogs]
    for backlog in backlogs:
        if names.count(backlog.name) > 1:
            problems.append(f"backlog name `{backlog.name}` is used more than once")
        for other in backlog.may_depend_on:
            if other not in names:
                problems.append(f"backlog `{backlog.name}`: may_depend_on names unknown `{other}`")
    prefixes = [b.prefix for b in backlogs]
    for prefix in set(prefixes):
        if prefixes.count(prefix) > 1:
            problems.append(f"prefix `{prefix}` is used by more than one backlog")
    files = [b.file for b in backlogs]
    for file in set(files):
        if files.count(file) > 1:
            problems.append(f"file `{file}` is used by more than one backlog")

    columns = data.get("columns", {})
    custom = expect(columns, "custom", list, []) if isinstance(columns, dict) else []
    if not all(isinstance(item, str) and item for item in custom):
        problems.append("columns.custom must be a list of non-empty strings")
        custom = []

    points = data.get("points", {})
    scale = expect(points, "scale", list, []) if isinstance(points, dict) else []
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in scale):
        problems.append("points.scale must be a list of integers")
        scale = []

    git = data.get("git", {})
    git = git if isinstance(git, dict) else {}
    push_task_branch = expect(git, "push_task_branch", bool, False)
    claim_remote = expect(git, "claim_remote", str, "")
    claim_grace_minutes = expect(git, "claim_grace_minutes", int, 15)
    if claim_grace_minutes < 0:
        problems.append("git.claim_grace_minutes must not be negative")
    worktree = expect(git, "worktree", str, "required")
    if worktree not in ("required", "never"):
        problems.append('git.worktree must be "required" or "never"')
    worktree_dir = expect(git, "worktree_dir", str, ".worktrees")

    checks = data.get("checks", {})
    if not isinstance(checks, dict) or not all(isinstance(v, str) for v in checks.values()):
        problems.append("[checks] must map names to command strings")
        checks = {}

    if problems:
        raise ConfigError(f"{CONFIG_PATH}: " + "; ".join(problems))

    return Config(
        root=root,
        version=version,
        backlogs=tuple(backlogs),
        custom_columns=tuple(custom),
        points_scale=tuple(scale),
        push_task_branch=push_task_branch,
        claim_remote=claim_remote,
        claim_grace_minutes=claim_grace_minutes,
        worktree=worktree,
        worktree_dir=worktree_dir,
        checks=dict(checks),
    )
