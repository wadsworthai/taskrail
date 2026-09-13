"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taskrail import __version__
from taskrail.config import find_root, load_config
from taskrail.issues import ConfigError, Issue
from taskrail.model import Project
from taskrail.project import load_project
from taskrail.query import STATES, eligible, state, task_dict

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3


def _emit(data, as_json: bool, text: str) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif text:
        print(text)


def _load(args) -> tuple[Project, list[Issue]]:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    return load_project(load_config(root))


def _refuse_if_invalid(issues: list[Issue], args) -> bool:
    errors = [i for i in issues if i.severity == "error"]
    if errors and not getattr(args, "allow_invalid", False):
        print(
            f"taskrail: the backlog has {len(errors)} validation error(s); run `taskrail validate`",
            file=sys.stderr,
        )
        return True
    return False


def _line(task, project: Project) -> str:
    points = f"{task.points}pt" if task.points is not None else "—"
    task_state = state(task, project)
    deps = f"  ← {', '.join(task.depends_on)}" if task.depends_on else ""
    return f"{task.id:<6} {task.status_raw} {task_state:<9} {task.kind:<8} {points:>4}  {task.epic:<4}  {task.title}{deps}"


def cmd_validate(args) -> int:
    project, issues = _load(args)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    summary = f"{len(project.tasks)} task(s) in {len(project.backlogs)} backlog(s): {len(errors)} error(s), {len(warnings)} warning(s)"
    _emit(
        {"valid": not errors, "tasks": len(project.tasks), "issues": [i.to_dict() for i in issues]},
        args.json,
        "\n".join([*(i.format() for i in issues), summary]),
    )
    return EXIT_INVALID if errors else EXIT_OK


def cmd_list(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    tasks = project.tasks
    if args.backlog:
        tasks = [t for t in tasks if t.backlog == args.backlog]
    if args.epic:
        tasks = [t for t in tasks if t.epic == args.epic]
    if args.state:
        tasks = [t for t in tasks if state(t, project) == args.state]
    if args.kind:
        tasks = [t for t in tasks if t.kind == args.kind]
    _emit([task_dict(t, project) for t in tasks], args.json, "\n".join(_line(t, project) for t in tasks))
    return EXIT_OK


def cmd_show(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    data = task_dict(task, project)
    kind = project.kinds.get(task.kind)
    data["kind_descriptor"] = kind.to_dict() if kind else None
    lines = [
        f"{task.id} — {task.title}",
        f"  backlog {task.backlog} · epic {task.epic} · kind {task.kind} · state {data['state']}",
        f"  points {task.points if task.points is not None else '—'} · depends on {', '.join(task.depends_on) or '—'}",
    ]
    if data["blocked_by"]:
        lines.append(f"  blocked by {', '.join(data['blocked_by'])}")
    if data["skill"]:
        lines.append(f"  skill {data['skill']}")
    if kind:
        for stage in kind.stages:
            lines.append(f"  · {stage.name} (gate: {stage.gate}{', commit' if stage.commit else ''})")
    if task.description:
        lines.append(f"  {task.description}")
    lines.append(f"  {task.file}:{task.line}")
    _emit(data, args.json, "\n".join(lines))
    return EXIT_OK


def cmd_next(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    if args.backlog and project.config.backlog(args.backlog) is None:
        print(f"taskrail: no backlog `{args.backlog}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    tasks = eligible(project, args.backlog)[: args.limit]
    _emit(
        [task_dict(t, project) for t in tasks],
        args.json,
        "\n".join(_line(t, project) for t in tasks) or "no eligible tasks",
    )
    return EXIT_OK


def cmd_kind_list(args) -> int:
    project, issues = _load(args)
    kinds = sorted(project.kinds.values(), key=lambda k: k.name)
    _emit(
        [k.to_dict() for k in kinds],
        args.json,
        "\n".join(f"{k.name:<10} {k.source:<9} {k.summary}" for k in kinds),
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskrail", description="Agent-agnostic backlog tool.")
    parser.add_argument("--version", action="version", version=f"taskrail {__version__}")
    parser.add_argument("--root", help="repository root (default: nearest directory with .taskrail/config.toml)")
    commands = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler, help_text: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("--json", action="store_true", help="machine-readable output")
        sub.set_defaults(handler=handler)
        return sub

    add("validate", cmd_validate, "Check the configuration, kinds and every backlog.")

    listing = add("list", cmd_list, "List tasks with their computed state.")
    listing.add_argument("--backlog")
    listing.add_argument("--epic")
    listing.add_argument("--state", choices=STATES)
    listing.add_argument("--kind")
    listing.add_argument("--allow-invalid", action="store_true", help="list even when validation fails")

    show = add("show", cmd_show, "Show one task and its kind's stages.")
    show.add_argument("id")
    show.add_argument("--allow-invalid", action="store_true")

    nxt = add("next", cmd_next, "Eligible tasks in order: points ascending, then file order.")
    nxt.add_argument("--backlog")
    nxt.add_argument("--limit", type=int, default=5)

    kind = commands.add_parser("kind", help="Inspect task kinds.")
    kind_commands = kind.add_subparsers(dest="kind_command", required=True)
    kind_list = kind_commands.add_parser("list", help="List resolved kinds and where each comes from.")
    kind_list.add_argument("--json", action="store_true")
    kind_list.set_defaults(handler=cmd_kind_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except ConfigError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
