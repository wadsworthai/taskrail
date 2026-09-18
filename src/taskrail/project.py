"""Loading and validating a whole project: config, kinds, every backlog."""

from __future__ import annotations

import re

from taskrail.backlog import load_backlog
from taskrail.config import Config
from taskrail.issues import Issue, error, warning
from taskrail.kinds import defined_kind_names, load_kinds
from taskrail.model import Project, Status


def load_project(config: Config, overlay: dict[str, str] | None = None) -> tuple[Project, list[Issue]]:
    """Load everything; `overlay` maps relative paths to contents that replace what is on disk."""
    kinds, issues = load_kinds(config)
    issues = [*config.warnings, *issues]  # names `.taskrail/config.toml` holds that taskrail ignores (T094)
    backlogs = []
    counter = [0]
    for backlog_config in config.backlogs:
        backlog, backlog_issues = load_backlog(config, backlog_config, counter, overlay)
        backlogs.append(backlog)
        issues.extend(backlog_issues)
    project = Project(config=config, backlogs=backlogs, kinds=kinds)
    issues.extend(_check_tasks(project))
    return project, issues


def _check_tasks(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    config = project.config
    excluded = defined_kind_names(config) - set(project.kinds) if config.allowed_kinds else set()
    seen: dict[str, tuple[str, int]] = {}
    by_id = {}
    for backlog in project.backlogs:
        id_re = re.compile(rf"^{backlog.config.prefix}\d{{{backlog.config.id_digits},}}$")
        for task in backlog.tasks:
            where = (task.file, task.line)
            if not id_re.match(task.id):
                issues.append(
                    error(
                        "task-id",
                        f"task ID `{task.id}` does not match prefix `{backlog.config.prefix}` plus {backlog.config.id_digits} or more digits",
                        *where,
                    )
                )
            if task.id in seen:
                first_file, first_line = seen[task.id]
                issues.append(
                    error("task-duplicate", f"task `{task.id}` is already defined at {first_file}:{first_line}", *where)
                )
            else:
                seen[task.id] = where
                by_id[task.id] = task
            if task.status is None:
                issues.append(
                    error("task-status", f"status `{task.status_raw}` is not one of ⬜ (pending), ✅ (done), ❌ (discarded)", *where)
                )
            if not task.kind:
                issues.append(error("task-kind-empty", f"task `{task.id}` has no kind", *where))
            elif task.kind not in project.kinds and task.kind in excluded:
                allowed = ", ".join(sorted(config.allowed_kinds))
                issues.append(error("task-kind-disallowed", f"kind `{task.kind}` is not allowed (kinds.allowed: {allowed})", *where))
            elif task.kind not in project.kinds:
                known = ", ".join(sorted(project.kinds)) or "none"
                issues.append(error("task-kind-unknown", f"kind `{task.kind}` is not defined (known: {known})", *where))
            if task.points_raw and task.points_raw not in ("—", "-"):
                if task.points is None:
                    issues.append(error("task-points", f"points `{task.points_raw}` is not a whole number", *where))
                elif config.points_scale and task.points not in config.points_scale:
                    scale = ", ".join(map(str, config.points_scale))
                    issues.append(error("task-points-scale", f"points `{task.points}` is not on the scale ({scale})", *where))
            if not task.title:
                issues.append(error("task-title", f"task `{task.id}` has no title", *where))

    for backlog in project.backlogs:
        allowed = {backlog.config.name, *backlog.config.may_depend_on}
        for task in backlog.tasks:
            where = (task.file, task.line)
            if len(set(task.depends_on)) != len(task.depends_on):
                issues.append(warning("depends-repeated", f"task `{task.id}` lists a dependency more than once", *where))
            for dependency in task.depends_on:
                if dependency == task.id:
                    issues.append(error("depends-self", f"task `{task.id}` depends on itself", *where))
                    continue
                target = by_id.get(dependency)
                if target is None:
                    issues.append(error("depends-unknown", f"dependency `{dependency}` does not exist", *where))
                    continue
                if target.backlog not in allowed:
                    issues.append(
                        error(
                            "depends-direction",
                            f"backlog `{backlog.config.name}` may not depend on backlog `{target.backlog}` (`{dependency}`)",
                            *where,
                        )
                    )
                if target.status is Status.DISCARDED and task.status is Status.PENDING:
                    issues.append(
                        warning("depends-discarded", f"task `{task.id}` depends on discarded task `{dependency}`", *where)
                    )

    issues.extend(_check_cycles(by_id))
    return issues


def _check_cycles(by_id: dict) -> list[Issue]:
    issues: list[Issue] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done
    reported: set[frozenset[str]] = set()

    def visit(task_id: str, path: list[str]) -> None:
        state[task_id] = 1
        path.append(task_id)
        for dependency in by_id[task_id].depends_on:
            if dependency not in by_id or dependency == task_id:
                continue
            if state.get(dependency) == 1:
                cycle = path[path.index(dependency):]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    task = by_id[cycle[0]]
                    chain = " → ".join([*cycle, dependency])
                    issues.append(error("depends-cycle", f"dependency cycle: {chain}", task.file, task.line))
            elif dependency not in state:
                visit(dependency, path)
        path.pop()
        state[task_id] = 2

    for task_id in by_id:
        if task_id not in state:
            visit(task_id, [])
    return issues
