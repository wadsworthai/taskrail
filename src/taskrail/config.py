"""Loading and checking `.taskrail/config.toml`."""

from __future__ import annotations

import difflib
import re
import tomllib
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

from taskrail.issues import ConfigError, Issue, warning
from taskrail.predicates import ColumnPredicate, parse_column_predicate, resolve_column

CONFIG_PATH = Path(".taskrail") / "config.toml"
DEFAULT_BACKLOG_FILE = "TASKRAIL.md"  # [[backlog]].file when the key is absent (DESIGN.md §4, T099)
PREFIX_RE = re.compile(r"^[A-Z]{1,4}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
CORE_TASK_COLUMNS = ("✓", "ID", "Kind", "Depends On", "Title", "Pts", "Description")
COMMIT_POLICIES = ("stages", "on-done")  # [git].commit and a kind's top-level `commit` (DESIGN.md §4, §5.1)


@dataclass(frozen=True)
class BacklogConfig:
    name: str
    prefix: str
    file: str = DEFAULT_BACKLOG_FILE
    mainline: str = "main"
    artifacts: str = "docs"
    may_depend_on: tuple[str, ...] = ()
    epic_prefix: str = "E"
    id_digits: int = 3


PROVIDERS = ("auto", "github", "gitlab", "gitea", "forgejo", "none")


@dataclass(frozen=True)
class ReviewConfig:
    remote: str = "origin"
    fetch: bool = True
    rebase: bool = True
    provider: str = "auto"
    web_url: str = ""
    url_template: str = ""
    scope: str = ""


NOTIFY_EVENTS = ("escalation", "lane-done", "lane-failed")
# "batch" is the foreseen second mode, deferred by the T033 trial (DESIGN.md §12.10).
HANDOFF_MODES = ("sequential",)
GATE_RE = re.compile(r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*$")
TEMPLATE_VALUES = {"id": "T001", "slug": "slug", "artifacts": "docs", "backlog": "main", "epic": "E01"}
RESOURCE_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class GroupConfig:
    """`[[autopilot.group]]`: at most `limit` lanes at once from the group (DESIGN.md §12.7)."""

    name: str
    limit: int
    predicate: ColumnPredicate | None = None  # None: membership assigned by judgement with `autopilot lane --group`


@dataclass(frozen=True)
class ResourceConfig:
    """`[[autopilot.resource]]`: a pool of values, one per lane (DESIGN.md §12.7)."""

    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class AutopilotConfig:
    """`[autopilot]` (DESIGN.md §12.9)."""

    enabled: bool = False
    max_lanes: int = 3
    kinds: tuple[str, ...] = ()  # empty: every allowed kind
    governing: tuple[str, ...] = ()
    read_first: tuple[str, ...] = ()  # loaded from the `governing` entries when the key is absent (T061)
    escalate_gates: tuple[str, ...] = ()  # "kind:stage"
    decisions: str = "{artifacts}/autopilot/decisions/{id}-{slug}.md"
    decisions_index: str = "{artifacts}/autopilot/decisions/README.md"
    silent_minutes: int = 20
    handoff: str = "sequential"
    notify: str = ""
    notify_on: tuple[str, ...] = ("escalation", "lane-done")
    groups: tuple[GroupConfig, ...] = ()
    resources: tuple[ResourceConfig, ...] = ()

    def group(self, name: str) -> GroupConfig | None:
        return next((group for group in self.groups if group.name == name), None)


@dataclass(frozen=True)
class Config:
    root: Path
    version: str | None
    backlogs: tuple[BacklogConfig, ...]
    custom_columns: tuple[str, ...] = ()
    column_aliases: dict[str, str] = field(default_factory=dict)  # core task column -> this repository's header
    points_scale: tuple[int, ...] = ()
    push_task_branch: bool = True
    commit: str | None = None  # [git].commit: "stages" | "on-done"; None when unset
    claim_remote: str = ""
    branch_record_remote: str = ""  # mirror branch records to this remote (DESIGN.md §6.4)
    claim_grace_minutes: int = 15
    worktree: str = "required"  # "required" | "never"
    worktree_dir: str = ".worktrees"
    task_branch: str = "task"  # "task": one branch per task; "current": the checked-out branch (DESIGN.md §6.4)
    checks: dict[str, str] = field(default_factory=dict)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    allowed_kinds: tuple[str, ...] = ()  # empty: every defined kind is allowed
    autopilot: AutopilotConfig = field(default_factory=AutopilotConfig)
    warnings: tuple[Issue, ...] = ()  # names the file holds that taskrail does not define (T094)

    def backlog(self, name: str) -> BacklogConfig | None:
        return next((b for b in self.backlogs if b.name == name), None)


# Every name `.taskrail/config.toml` may hold, by the table it sits in (DESIGN.md §4). taskrail
# ignores anything else, so `validate` warns about it: without that, a typo and a key a newer
# taskrail no longer defines are equally silent (T088 E2). A key is warned about, never refused, so
# a config written for another version still loads.
TOP_LEVEL_KEYS = ("version",)
TABLE_KEYS: dict[str, tuple[str, ...] | None] = {  # None: free-form, the repository names its own
    "backlog": ("name", "prefix", "file", "mainline", "artifacts", "may_depend_on", "epic_prefix", "id_digits"),
    "columns": ("custom", "aliases"),  # the keys under `aliases` are core column names, checked in _column_aliases
    "points": ("scale",),
    "git": ("push_task_branch", "commit", "claim_remote", "branch_record_remote", "claim_grace_minutes", "worktree", "worktree_dir", "task_branch"),
    "review": ("remote", "fetch", "rebase", "provider", "web_url", "url_template", "scope"),
    "kinds": ("allowed",),
    "checks": None,
    "autopilot": ("enabled", "max_lanes", "kinds", "governing", "read_first", "escalate_gates", "decisions", "decisions_index", "silent_minutes", "handoff", "notify", "notify_on", "group", "resource"),
}
AUTOPILOT_ENTRY_KEYS = {"group": ("name", "limit", "column", "match"), "resource": ("name", "values")}


def _hint(name: str, known, table: bool = False) -> str:
    """`did you mean …? ` when `name` is a near miss of one that exists, empty otherwise."""
    close = difflib.get_close_matches(name, list(known), 1, 0.8)
    if not close:
        return ""
    return f"did you mean [{close[0]}]? " if table else f"did you mean `{close[0]}`? "


def unknown_names(data: dict) -> list[Issue]:
    """Warn about every name in a parsed config that taskrail does not define (§4).

    Never an error: a repository pinned to an older CLI must keep loading a config written for a
    newer one, and the other way round. A table taskrail does not know is reported once, as a
    table, and not descended into.
    """
    found: list[Issue] = []
    where = str(CONFIG_PATH)

    def keys(table: dict, known: tuple[str, ...], label: str) -> None:
        for name in table:
            if name not in known:
                found.append(warning("config-unknown-key", f"unknown key `{name}` in {label}; {_hint(name, known)}taskrail ignores it", where))

    def entries(raw, label: str, known: tuple[str, ...]) -> None:
        """Each entry of a repeatable table, labelled by its `name` when it has one."""
        for index, entry in enumerate(raw if isinstance(raw, list) else [], start=1):
            if isinstance(entry, dict):
                name = entry.get("name")
                keys(entry, known, f"{label} `{name}`" if isinstance(name, str) and name else f"{label} #{index}")

    for name, value in data.items():
        if name in TOP_LEVEL_KEYS:
            continue
        if name not in TABLE_KEYS:
            if isinstance(value, dict) or (isinstance(value, list) and value and all(isinstance(item, dict) for item in value)):
                found.append(warning("config-unknown-table", f"unknown table [{name}]; {_hint(name, TABLE_KEYS, table=True)}taskrail ignores it", where))
            else:
                found.append(warning("config-unknown-key", f"unknown top-level key `{name}`; {_hint(name, (*TOP_LEVEL_KEYS, *TABLE_KEYS))}taskrail ignores it", where))
            continue
        known = TABLE_KEYS[name]
        if known is None:
            continue
        if name == "backlog":
            entries(value, "[[backlog]]", known)
        elif isinstance(value, dict):
            keys(value, known, f"[{name}]")
            if name == "autopilot":
                for table, entry_keys in AUTOPILOT_ENTRY_KEYS.items():
                    entries(value.get(table), f"[[autopilot.{table}]]", entry_keys)
    return found


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
        file = expect(raw, "file", str, DEFAULT_BACKLOG_FILE)
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
    aliases = _column_aliases(expect(columns, "aliases", dict, {}) if isinstance(columns, dict) else {}, custom, problems)

    points = data.get("points", {})
    scale = expect(points, "scale", list, []) if isinstance(points, dict) else []
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in scale):
        problems.append("points.scale must be a list of integers")
        scale = []

    git = data.get("git", {})
    git = git if isinstance(git, dict) else {}
    push_task_branch = expect(git, "push_task_branch", bool, True)
    commit = git.get("commit")
    if commit is not None and (not isinstance(commit, str) or commit not in COMMIT_POLICIES):
        problems.append('git.commit must be "stages" or "on-done"')
    claim_remote = expect(git, "claim_remote", str, "")
    branch_record_remote = expect(git, "branch_record_remote", str, "")
    claim_grace_minutes = expect(git, "claim_grace_minutes", int, 15)
    if claim_grace_minutes < 0:
        problems.append("git.claim_grace_minutes must not be negative")
    worktree = expect(git, "worktree", str, "required")
    if worktree not in ("required", "never"):
        problems.append('git.worktree must be "required" or "never"')
    worktree_dir = expect(git, "worktree_dir", str, ".worktrees")
    task_branch = expect(git, "task_branch", str, "task")
    if task_branch not in ("task", "current"):
        problems.append('git.task_branch must be "task" or "current"')
    elif task_branch == "current" and worktree != "never":
        problems.append('git.task_branch = "current" requires git.worktree = "never"')

    raw_review = data.get("review", {})
    raw_review = raw_review if isinstance(raw_review, dict) else {}
    review = ReviewConfig(
        remote=expect(raw_review, "remote", str, "origin"),
        fetch=expect(raw_review, "fetch", bool, True),
        rebase=expect(raw_review, "rebase", bool, True),
        provider=expect(raw_review, "provider", str, "auto"),
        web_url=expect(raw_review, "web_url", str, "").rstrip("/"),
        url_template=expect(raw_review, "url_template", str, ""),
        scope=expect(raw_review, "scope", str, ""),
    )
    if review.provider not in PROVIDERS:
        problems.append(f"review.provider must be one of {', '.join(PROVIDERS)}")

    raw_kinds = data.get("kinds", {})
    if not isinstance(raw_kinds, dict):
        problems.append("[kinds] must be a table")
        raw_kinds = {}
    allowed_kinds = expect(raw_kinds, "allowed", list, None)
    if allowed_kinds is not None:
        if not allowed_kinds:
            problems.append("kinds.allowed must name at least one kind; omit it to allow every kind")
        elif not all(isinstance(item, str) and NAME_RE.match(item) for item in allowed_kinds):
            problems.append("kinds.allowed must be a list of kind names (lowercase letters, digits and dashes)")
            allowed_kinds = []
        for name in sorted({n for n in allowed_kinds if allowed_kinds.count(n) > 1}):
            problems.append(f"kinds.allowed names `{name}` more than once")

    checks = data.get("checks", {})
    if not isinstance(checks, dict) or not all(isinstance(v, str) for v in checks.values()):
        problems.append("[checks] must map names to command strings")
        checks = {}

    autopilot = _autopilot(data.get("autopilot", {}), problems, custom, aliases)

    if problems:
        raise ConfigError(f"{CONFIG_PATH}: " + "; ".join(problems))

    return Config(
        root=root,
        version=version,
        backlogs=tuple(backlogs),
        custom_columns=tuple(custom),
        column_aliases=aliases,
        points_scale=tuple(scale),
        push_task_branch=push_task_branch,
        commit=commit,
        claim_remote=claim_remote,
        branch_record_remote=branch_record_remote,
        claim_grace_minutes=claim_grace_minutes,
        worktree=worktree,
        worktree_dir=worktree_dir,
        task_branch=task_branch,
        checks=dict(checks),
        review=review,
        allowed_kinds=tuple(allowed_kinds or ()),
        autopilot=autopilot,
        warnings=tuple(unknown_names(data)),
    )


def _autopilot(raw, problems: list[str], custom_columns=(), aliases=None) -> AutopilotConfig:
    """Check `[autopilot]` and return it with the defaults of DESIGN.md §12.9 filled in."""
    defaults = AutopilotConfig()
    if not isinstance(raw, dict):
        problems.append("[autopilot] must be a table")
        return defaults
    values: dict = {}

    def scalar(key: str, kind: type) -> None:
        if key not in raw:
            return
        value = raw[key]
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            problems.append(f"autopilot.{key} must be {kind.__name__}, got {type(value).__name__}")
        else:
            values[key] = value

    def strings(key: str) -> None:
        if key not in raw:
            return
        value = raw[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            problems.append(f"autopilot.{key} must be a list of non-empty strings")
        else:
            values[key] = tuple(value)

    for key in ("enabled",):
        scalar(key, bool)
    for key in ("max_lanes", "silent_minutes"):
        scalar(key, int)
    for key in ("decisions", "decisions_index", "handoff", "notify"):
        scalar(key, str)
    for key in ("kinds", "governing", "read_first", "escalate_gates", "notify_on"):
        strings(key)
    if "read_first" not in raw:
        values["read_first"] = values.get("governing", ())  # the reading list before T061

    if values.get("max_lanes", 1) < 1:
        problems.append("autopilot.max_lanes must be at least 1")
    if values.get("silent_minutes", 0) < 0:
        problems.append("autopilot.silent_minutes must not be negative")
    if values.get("handoff", "sequential") not in HANDOFF_MODES:
        problems.append(f"autopilot.handoff must be one of {', '.join(HANDOFF_MODES)}")
    for name in values.get("kinds", ()):
        if not NAME_RE.match(name):
            problems.append(f"autopilot.kinds: `{name}` is not a kind name (lowercase letters, digits and dashes)")
    for gate in values.get("escalate_gates", ()):
        if not GATE_RE.match(gate):
            problems.append(f"autopilot.escalate_gates: `{gate}` must be shaped kind:stage")
    for event in values.get("notify_on", ()):
        if event not in NOTIFY_EVENTS:
            problems.append(f"autopilot.notify_on: `{event}` is not one of {', '.join(NOTIFY_EVENTS)}")
    for key in ("decisions", "decisions_index"):
        if key in values:
            try:
                values[key].format(**TEMPLATE_VALUES)
            except (KeyError, IndexError, ValueError) as exc:
                problems.append(f"autopilot.{key}: invalid template ({exc!r}); placeholders are {', '.join(f'{{{k}}}' for k in TEMPLATE_VALUES)}")
    if "group" in raw:
        values["groups"] = _autopilot_groups(raw["group"], problems, custom_columns, aliases or {})
    if "resource" in raw:
        values["resources"] = _autopilot_resources(raw["resource"], problems)
    return dataclasses.replace(defaults, **values)


def _entries(raw, table: str, problems: list[str]) -> list[tuple[str, dict]]:
    """The tables of `[[autopilot.<table>]]`, each with the label its errors use."""
    if not isinstance(raw, list) or not all(isinstance(entry, dict) for entry in raw):
        problems.append(f"autopilot.{table} must be an array of tables ([[autopilot.{table}]])")
        return []
    found = []
    for index, entry in enumerate(raw, start=1):
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            problems.append(f"autopilot.{table} #{index}: missing `name`")
            continue
        found.append((f"autopilot.{table} `{name}`", entry))
    names = [entry["name"] for _, entry in found]
    for name in sorted({n for n in names if names.count(n) > 1}):
        problems.append(f"autopilot.{table}: `{name}` is used more than once")
    return found


def _autopilot_groups(raw, problems: list[str], custom_columns, aliases: dict) -> tuple[GroupConfig, ...]:
    groups = []
    for label, entry in _entries(raw, "group", problems):
        name = entry["name"]
        if not NAME_RE.match(name):
            problems.append(f"{label}: name must be lowercase letters, digits and dashes")
        limit = entry.get("limit")
        if "limit" not in entry:
            problems.append(f"{label}: missing `limit`")
        elif not isinstance(limit, int) or isinstance(limit, bool):
            problems.append(f"{label}: `limit` must be int, got {type(limit).__name__}")
        elif limit < 1:
            problems.append(f"{label}: `limit` must be at least 1")
        try:
            predicate = parse_column_predicate(entry.get("column"), entry.get("match"))
        except ValueError as exc:
            problems.append(f"{label}: {exc}")
            continue
        if predicate is not None:
            predicate, problem = resolve_column(predicate, custom_columns, aliases, CORE_TASK_COLUMNS)
            if problem:
                problems.append(f"{label}: {problem}")
        if isinstance(limit, int) and not isinstance(limit, bool):
            groups.append(GroupConfig(name, limit, predicate))
    return tuple(groups)


def _autopilot_resources(raw, problems: list[str]) -> tuple[ResourceConfig, ...]:
    resources = []
    for label, entry in _entries(raw, "resource", problems):
        name = entry["name"]
        if not RESOURCE_NAME_RE.match(name):
            problems.append(f"{label}: name must be uppercase letters, digits and underscores, starting with a letter")
        if "values" not in entry:
            problems.append(f"{label}: missing `values`")
            continue
        values = entry["values"]
        if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
            problems.append(f"{label}: `values` must be a non-empty list of strings")
            continue
        for value in sorted({v for v in values if values.count(v) > 1}):
            problems.append(f"{label}: value `{value}` is listed more than once")
        resources.append(ResourceConfig(name, tuple(values)))
    return tuple(resources)


def _column_aliases(raw: dict, custom: list, problems: list[str]) -> dict[str, str]:
    """Check `[columns].aliases` (core task column -> header) and return it keyed by core name."""
    core_by_lower = {name.lower(): name for name in CORE_TASK_COLUMNS}
    custom_lower = {name.lower() for name in custom if isinstance(name, str)}
    aliases: dict[str, str] = {}
    owners: dict[str, str] = {}
    for key, value in raw.items():
        core = core_by_lower.get(key.strip().lower())
        if core is None:
            problems.append(f"columns.aliases: `{key}` is not a core task column ({', '.join(CORE_TASK_COLUMNS)})")
            continue
        if not isinstance(value, str) or not value.strip() or "|" in value:
            problems.append(f"columns.aliases.{core} must be a non-empty header name without `|`")
            continue
        if core in aliases:
            problems.append(f"columns.aliases: {core} is aliased more than once")
            continue
        alias = value.strip()
        lower = alias.lower()
        if lower == core.lower():
            continue  # its own name: nothing to map
        if lower in core_by_lower:
            problems.append(f"columns.aliases: alias `{alias}` for {core} is the name of core column {core_by_lower[lower]}")
        elif lower in owners:
            problems.append(f"columns.aliases: alias `{alias}` is given to both {owners[lower]} and {core}")
        elif lower in custom_lower:
            problems.append(f"columns.aliases: alias `{alias}` for {core} is also a custom column")
        else:
            owners[lower] = core
            aliases[core] = alias
    return aliases
