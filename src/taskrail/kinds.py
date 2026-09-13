"""Task kind descriptors, resolved in layers: core, repository-local, overrides."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from taskrail.config import Config
from taskrail.issues import Issue, error, warning
from taskrail.model import NONE_MARKERS, Task

CORE_DIR = Path(__file__).parent / "kinds"
LOCAL_DIR = Path(".taskrail") / "types"
OVERRIDE_DIR = Path(".taskrail") / "overrides"
DESCRIPTOR = "kind.toml"
GATES = ("always", "conditional", "none")
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


@dataclass(frozen=True)
class Route:
    when: dict[str, str]
    skill: str

    def matches(self, task: Task) -> bool:
        for column, expected in self.when.items():
            actual = task.columns.get(column, "")
            if expected == "*":
                if actual in NONE_MARKERS:
                    return False
            elif expected in NONE_MARKERS:
                if actual not in NONE_MARKERS:
                    return False
            elif actual != expected:
                return False
        return True


@dataclass(frozen=True)
class Kind:
    name: str
    summary: str
    skill: str | None
    branch: str
    artifact: str | None
    artifact_index: str | None
    never_edit: tuple[str, ...]
    stages: tuple[Stage, ...]
    routes: tuple[Route, ...]
    source: str  # "core" | "local" | "override"
    path: str

    def skill_for(self, task: Task) -> str | None:
        for route in self.routes:
            if route.matches(task):
                return route.skill
        return self.skill

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "summary": self.summary,
            "skill": self.skill,
            "branch": self.branch,
            "artifact": self.artifact,
            "artifact_index": self.artifact_index,
            "never_edit": list(self.never_edit),
            "stages": [
                {"name": s.name, "summary": s.summary, "gate": s.gate, "commit": s.commit, "checks": list(s.checks)}
                for s in self.stages
            ],
            "routes": [{"when": r.when, "skill": r.skill} for r in self.routes],
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
        stages.append(Stage(stage_name, str(raw.get("summary", "")), gate, commit, tuple(checks)))

    routes: list[Route] = []
    raw_routes = data.get("route", [])
    if not isinstance(raw_routes, list):
        problems.append("`route` must be an array of tables")
        raw_routes = []
    for index, raw in enumerate(raw_routes, start=1):
        when = raw.get("when") if isinstance(raw, dict) else None
        route_skill = raw.get("skill") if isinstance(raw, dict) else None
        if not isinstance(when, dict) or not when or not all(isinstance(v, str) for v in when.values()):
            problems.append(f"route #{index}: `when` must map column names to strings")
            continue
        if not isinstance(route_skill, str) or not route_skill:
            problems.append(f"route #{index}: `skill` is required")
            continue
        routes.append(Route(dict(when), route_skill))

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
        stages=tuple(stages),
        routes=tuple(routes),
        source=source,
        path=label,
    )


def load_kinds(config: Config) -> tuple[dict[str, Kind], list[Issue]]:
    issues: list[Issue] = []
    kinds: dict[str, Kind] = {}
    layers = (
        ("core", CORE_DIR, None),
        ("local", config.root / LOCAL_DIR, LOCAL_DIR),
        ("override", config.root / OVERRIDE_DIR, OVERRIDE_DIR),
    )
    for source, directory, relative in layers:
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
    return kinds, issues


def columns_used_by_routes(kinds: dict[str, Kind]) -> set[str]:
    return {column for kind in kinds.values() for route in kind.routes for column in route.when}
