"""Task kind descriptors, resolved in layers: core, repository-local, overrides."""

from __future__ import annotations

import dataclasses
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from taskrail.config import COMMIT_POLICIES, CORE_TASK_COLUMNS, Config
from taskrail.issues import Issue, error, warning
from taskrail.model import Task
from taskrail.predicates import ColumnPredicate, parse_column_predicate, parse_match, resolve_column

CORE_DIR = Path(__file__).parent / "kinds"
LOCAL_DIR = Path(".taskrail") / "types"
OVERRIDE_DIR = Path(".taskrail") / "overrides"
DESCRIPTOR = "kind.toml"
GATES = ("always", "conditional", "decisions", "none")  # DESIGN.md §5.6
PLACEHOLDERS = {"id", "slug", "artifacts", "backlog", "epic"}
PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


@dataclass(frozen=True)
class Stage:
    name: str
    summary: str
    gate: str
    commit: bool
    checks: tuple[str, ...]
    predicate: ColumnPredicate | None = None  # the stage applies only to tasks it matches
    judgement: bool = False  # the executor decides whether the stage is relevant

    def applies(self, task: Task) -> bool:
        """The column predicate's result for `task`; true for a stage without one."""
        return self.predicate is None or self.predicate.matches(task.columns)

    def to_dict(self, task: Task | None = None) -> dict:
        data = {
            "name": self.name,
            "summary": self.summary,
            "gate": self.gate,
            "commit": self.commit,
            "checks": list(self.checks),
            "column": self.predicate.column if self.predicate else None,
            "match": list(self.predicate.match) if self.predicate else [],
            "judgement": self.judgement,
        }
        if task is not None:
            data["applies"] = self.applies(task)
        return data


@dataclass(frozen=True)
class Route:
    when: tuple[ColumnPredicate, ...]  # one column predicate per `when` entry; every one must hold
    skill: str

    def matches(self, task: Task) -> bool:
        return all(predicate.matches(task.columns) for predicate in self.when)

    def covers(self, other: Route) -> bool:
        """Whether this route holds for every task `other` holds for.

        True only when each of this route's entries covers an entry of `other` on the same column.
        A column `other` does not constrain is never assumed to match, so a route some task can
        still reach is never reported as covered.
        """
        return all(any(mine.covers(theirs) for theirs in other.when) for mine in self.when)

    def when_dict(self) -> dict[str, str | list[str]]:
        """`when` as reported: declared column names, one value as a string and several as a list."""
        return {p.column: p.match[0] if len(p.match) == 1 else list(p.match) for p in self.when}


@dataclass(frozen=True)
class Kind:
    name: str
    summary: str
    skill: str | None
    branch: str
    artifact: str | None
    artifact_index: str | None
    never_edit: tuple[str, ...]
    commit_type: str | None
    stages: tuple[Stage, ...]
    routes: tuple[Route, ...]
    source: str  # "core" | "local" | "override"
    path: str
    commit: str = "stages"  # the effective commit policy (DESIGN.md §5.1)
    commit_source: str = "default"  # "kind" | "config" | "default"

    def skill_for(self, task: Task) -> str | None:
        for route in self.routes:
            if route.matches(task):
                return route.skill
        return self.skill

    def skill_names(self) -> set[str]:
        """Every skill this kind can hand a task to: its `skill` and each route's."""
        return {name for name in (self.skill, *(route.skill for route in self.routes)) if name}

    def to_dict(self, task: Task | None = None) -> dict:
        """The descriptor; with a task, each stage also reports whether it `applies` to it."""
        return {
            "name": self.name,
            "summary": self.summary,
            "skill": self.skill,
            "branch": self.branch,
            "artifact": self.artifact,
            "artifact_index": self.artifact_index,
            "never_edit": list(self.never_edit),
            "commit_type": self.commit_type,
            "commit": self.commit,
            "commit_source": self.commit_source,
            "stages": [stage.to_dict(task) for stage in self.stages],
            "routes": [{"when": r.when_dict(), "skill": r.skill} for r in self.routes],
            "source": self.source,
            "path": self.path,
        }


def _parse(path: Path, source: str, label: str, config: Config, issues: list[Issue]) -> Kind | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        issues.append(error("kind-toml", f"invalid TOML: {exc}", label))
        return None

    problems: list[str] = []
    name = data.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        problems.append("`name` must be lowercase letters, digits and dashes")
    elif name != path.parent.name:
        problems.append(f"`name` is `{name}` but the directory is `{path.parent.name}`")

    def text(key: str, required: bool = False) -> str | None:
        value = data.get(key)
        if value is None:
            if required:
                problems.append(f"missing `{key}`")
            return None
        if not isinstance(value, str) or not value:
            problems.append(f"`{key}` must be a non-empty string")
            return None
        return value

    summary = text("summary", required=True) or ""
    skill = text("skill")
    branch = text("branch") or "{id}-{slug}"
    artifact = text("artifact")
    artifact_index = text("artifact_index")
    commit_type = text("commit_type")
    if commit_type is not None and not re.match(r"^[a-z]+$", commit_type):
        problems.append("`commit_type` must be lowercase letters, such as feat or fix")
    declared_commit = data.get("commit")
    if declared_commit is not None and (not isinstance(declared_commit, str) or declared_commit not in COMMIT_POLICIES):
        problems.append('`commit` must be "stages" or "on-done", the kind\'s commit policy; a stage\'s `commit` is true or false')
    for key, template in (("branch", branch), ("artifact", artifact), ("artifact_index", artifact_index)):
        for placeholder in PLACEHOLDER_RE.findall(template or ""):
            if placeholder not in PLACEHOLDERS:
                problems.append(f"`{key}` uses unknown placeholder `{{{placeholder}}}`")

    never_edit = data.get("never_edit", [])
    if not isinstance(never_edit, list) or not all(isinstance(item, str) for item in never_edit):
        problems.append("`never_edit` must be a list of strings")
        never_edit = []

    stages: list[Stage] = []
    raw_stages = data.get("stage", [])
    if not isinstance(raw_stages, list) or not raw_stages:
        problems.append("at least one [[stage]] is required")
        raw_stages = []
    seen_stages: set[str] = set()
    for index, raw in enumerate(raw_stages, start=1):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            problems.append(f"stage #{index} needs a `name`")
            continue
        stage_name = raw["name"]
        if stage_name in seen_stages:
            problems.append(f"stage `{stage_name}` is defined twice")
        seen_stages.add(stage_name)
        gate = raw.get("gate", "none")
        if gate not in GATES:
            problems.append(f"stage `{stage_name}`: gate must be one of {', '.join(GATES)}")
        checks = raw.get("checks", [])
        if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
            problems.append(f"stage `{stage_name}`: `checks` must be a list of strings")
            checks = []
        for check in checks:
            # Core kinds name conventional checks that a repository may simply not have.
            if check not in config.checks and source != "core":
                issues.append(
                    warning("kind-check-unknown", f"stage `{stage_name}` runs check `{check}`, which [checks] does not define", label)
                )
        commit = raw.get("commit", False)
        if not isinstance(commit, bool):
            problems.append(f"stage `{stage_name}`: `commit` must be true or false")
            commit = False
        judgement = raw.get("judgement", False)
        if not isinstance(judgement, bool):
            problems.append(f"stage `{stage_name}`: `judgement` must be true or false")
            judgement = False
        try:
            predicate = parse_column_predicate(raw.get("column"), raw.get("match"))
        except ValueError as exc:
            problems.append(f"stage `{stage_name}`: {exc}")
            predicate = None
        if predicate is not None:
            predicate, unknown = resolve_column(predicate, config.custom_columns, config.column_aliases, CORE_TASK_COLUMNS)
            if unknown:
                # The kind stays loaded: dropping it would bury this under task-kind-unknown for every task.
                issues.append(error("stage-column-unknown", f"stage `{stage_name}`: {unknown}", label))
        stages.append(Stage(stage_name, str(raw.get("summary", "")), gate, commit, tuple(checks), predicate, judgement))

    policy, policy_source = _commit_policy(declared_commit, config)
    if policy == "on-done":  # the policy wins over every stage's boolean
        stages = [dataclasses.replace(stage, commit=False) for stage in stages]

    routes: list[Route] = []
    raw_routes = data.get("route", [])
    if not isinstance(raw_routes, list):
        problems.append("`route` must be an array of tables")
        raw_routes = []
    for index, raw in enumerate(raw_routes, start=1):
        route = _parse_route(index, raw, config, problems, issues, label)
        if route is not None:
            routes.append(route)
    if not problems:
        issues.extend(_unreachable_routes(routes, label))

    if skill is None and not routes:
        problems.append("either `skill` or at least one [[route]] is required")

    if problems:
        for problem in problems:
            issues.append(error("kind-invalid", problem, label))
        return None

    return Kind(
        name=name,
        summary=summary,
        skill=skill,
        branch=branch,
        artifact=artifact,
        artifact_index=artifact_index,
        never_edit=tuple(never_edit),
        commit_type=commit_type,
        stages=tuple(stages),
        routes=tuple(routes),
        source=source,
        path=label,
        commit=policy,
        commit_source=policy_source,
    )


def _commit_policy(declared: object, config: Config) -> tuple[str, str]:
    """The effective commit policy and its source: the kind's, else `[git].commit`, else "stages"."""
    if isinstance(declared, str) and declared in COMMIT_POLICIES:
        return declared, "kind"
    if config.commit is not None:
        return config.commit, "config"
    return "stages", "default"


def commit_policy(kind: Kind | None, config: Config) -> tuple[str, str]:
    """A task's effective commit policy and its source; the configuration's when its kind is not loaded."""
    if kind is not None:
        return kind.commit, kind.commit_source
    return _commit_policy(None, config)


def commit_source_label(kind: Kind | None, config: Config) -> str:
    """Where a task's policy is set, as `show`'s text names it: the descriptor path, `[git].commit` or `default`."""
    _, source = commit_policy(kind, config)
    if source == "kind" and kind is not None:
        return kind.path
    return "[git].commit" if source == "config" else "default"


def _parse_route(index: int, raw: object, config: Config, problems: list[str], issues: list[Issue], label: str) -> Route | None:
    """One `[[route]]`: each `when` entry is a column predicate, resolved like a stage's (§5.5)."""
    when = raw.get("when") if isinstance(raw, dict) else None
    route_skill = raw.get("skill") if isinstance(raw, dict) else None
    if not isinstance(when, dict) or not when:
        problems.append(f"route #{index}: `when` must map column names to values")
        return None
    predicates: list[ColumnPredicate] = []
    seen: set[str] = set()
    invalid = False
    for column, value in when.items():
        name = column.strip()
        if not name:
            problems.append(f"route #{index}: `when` has an empty column name")
            invalid = True
            continue
        if name.lower() in seen:
            problems.append(f"route #{index}: `when` names column `{name}` twice")
            invalid = True
            continue
        seen.add(name.lower())
        try:
            predicates.append(ColumnPredicate(name, parse_match(value, f"`when.{name}`")))
        except ValueError as exc:
            problems.append(f"route #{index}: {exc}")
            invalid = True
    if not isinstance(route_skill, str) or not route_skill:
        problems.append(f"route #{index}: `skill` is required")
        return None
    if invalid:
        return None
    resolved: list[ColumnPredicate] = []
    for predicate in predicates:
        predicate, unknown = resolve_column(predicate, config.custom_columns, config.column_aliases, CORE_TASK_COLUMNS)
        if unknown:
            # As for stages: the kind stays loaded, so its tasks are not also reported as task-kind-unknown.
            issues.append(error("route-column-unknown", f"route #{index}: {unknown}", label))
        resolved.append(predicate)
    return Route(tuple(resolved), route_skill)


def _unreachable_routes(routes: list[Route], label: str) -> list[Issue]:
    """Warn about each route an earlier route of the kind fully covers, so it never gives the skill."""
    issues = []
    for later, route in enumerate(routes, start=1):
        earlier = next((n for n, previous in enumerate(routes[: later - 1], start=1) if previous.covers(route)), None)
        if earlier is not None:
            issues.append(
                warning(
                    "route-unreachable",
                    f"route #{later} never applies: route #{earlier}, listed before it, matches every task it matches",
                    label,
                )
            )
    return issues


def _layers(config: Config) -> tuple[tuple[str, Path, Path | None], ...]:
    return (
        ("core", CORE_DIR, None),
        ("local", config.root / LOCAL_DIR, LOCAL_DIR),
        ("override", config.root / OVERRIDE_DIR, OVERRIDE_DIR),
    )


def defined_kind_names(config: Config) -> set[str]:
    """Names of every kind a layer has a descriptor for, whether or not `[kinds].allowed` keeps it."""
    return {
        kind_dir.name
        for _, directory, _ in _layers(config)
        if directory.is_dir()
        for kind_dir in directory.iterdir()
        if (kind_dir / DESCRIPTOR).is_file()
    }


def core_kinds(config: Config) -> dict[str, Kind]:
    """The kinds taskrail ships, before any repository layer or `[kinds].allowed` applies."""
    kinds: dict[str, Kind] = {}
    for kind_dir in sorted(p for p in CORE_DIR.iterdir() if (p / DESCRIPTOR).is_file()):
        kind = _parse(kind_dir / DESCRIPTOR, "core", f"<core>/{kind_dir.name}/{DESCRIPTOR}", config, [])
        if kind is not None:
            kinds[kind.name] = kind
    return kinds


def load_kinds(config: Config) -> tuple[dict[str, Kind], list[Issue]]:
    issues: list[Issue] = []
    kinds: dict[str, Kind] = {}
    for source, directory, relative in _layers(config):
        if not directory.is_dir():
            continue
        for kind_dir in sorted(p for p in directory.iterdir() if p.is_dir()):
            descriptor = kind_dir / DESCRIPTOR
            label = f"{relative / kind_dir.name / DESCRIPTOR}" if relative else f"<core>/{kind_dir.name}/{DESCRIPTOR}"
            if not descriptor.is_file():
                if source != "core":
                    issues.append(error("kind-descriptor-missing", f"no {DESCRIPTOR} in kind directory", label))
                continue
            if source == "override" and kind_dir.name not in kinds:
                issues.append(
                    error("override-unknown", f"override for `{kind_dir.name}`, which no core or local kind defines", label)
                )
                continue
            kind = _parse(descriptor, source, label, config, issues)
            if kind is not None:
                kinds[kind.name] = kind
    if config.allowed_kinds:
        kinds = _restrict(kinds, config.allowed_kinds, issues)
    return kinds, issues


def _restrict(kinds: dict[str, Kind], allowed: tuple[str, ...], issues: list[Issue]) -> dict[str, Kind]:
    """Keep only the kinds `[kinds].allowed` names, after every layer is resolved."""
    for name in allowed:
        if name not in kinds:
            issues.append(error("kind-allowed-unknown", f"kinds.allowed names `{name}`, which no core, local or override kind defines"))
    for kind in kinds.values():
        # Leaving out a core kind is the point of the setting; a repository's own descriptor left out is likely a mistake.
        if kind.name not in allowed and kind.source != "core":
            issues.append(warning("kind-not-allowed", f"kind `{kind.name}` is defined but kinds.allowed does not list it", kind.path))
    return {name: kind for name, kind in kinds.items() if name in allowed}
