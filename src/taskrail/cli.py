"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taskrail import __version__, claims, gitutil, ids
from taskrail.config import find_root, load_config
from taskrail.issues import ConfigError, Issue
from taskrail.model import Project, Status
from taskrail.project import load_project
from taskrail.query import STATES, blocked_by, eligible, state, task_dict

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_CONFLICT = 4
EXIT_REFUSED = 5


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


def _local_claims(project: Project) -> dict:
    """Claims visible to this clone; a directory outside git simply has none."""
    try:
        return claims.read_all(project.config)
    except gitutil.GitError:
        return {}


def _line(task, project: Project, claimed: dict | None = None) -> str:
    points = f"{task.points}pt" if task.points is not None else "—"
    task_state = state(task, project, claimed)
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
    claimed = _local_claims(project)
    if args.state:
        tasks = [t for t in tasks if state(t, project, claimed) == args.state]
    if args.kind:
        tasks = [t for t in tasks if t.kind == args.kind]
    _emit(
        [task_dict(t, project, claimed) for t in tasks],
        args.json,
        "\n".join(_line(t, project, claimed) for t in tasks),
    )
    return EXIT_OK


def cmd_show(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    claimed = _local_claims(project)
    data = task_dict(task, project, claimed)
    kind = project.kinds.get(task.kind)
    data["kind_descriptor"] = kind.to_dict() if kind else None
    lines = [
        f"{task.id} — {task.title}",
        f"  backlog {task.backlog} · epic {task.epic} · kind {task.kind} · state {data['state']}",
        f"  points {task.points if task.points is not None else '—'} · depends on {', '.join(task.depends_on) or '—'}",
    ]
    if data["blocked_by"]:
        lines.append(f"  blocked by {', '.join(data['blocked_by'])}")
    if data["claim"]:
        claim = data["claim"]
        lines.append(f"  claimed by {claim['owner']} on {claim['branch'] or '—'} since {claim['created']}")
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
    claimed = _local_claims(project)
    tasks = eligible(project, args.backlog, claimed)[: args.limit]
    _emit(
        [task_dict(t, project, claimed) for t in tasks],
        args.json,
        "\n".join(_line(t, project, claimed) for t in tasks) or "no eligible tasks",
    )
    return EXIT_OK


def cmd_claim(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    if task.status is not Status.PENDING:
        print(f"taskrail: {task.id} is {task.status.label}, not pending", file=sys.stderr)
        return EXIT_REFUSED
    blockers = blocked_by(task, project)
    if blockers and not args.ignore_deps:
        print(f"taskrail: {task.id} is blocked by {', '.join(blockers)}; pass --ignore-deps to claim anyway", file=sys.stderr)
        return EXIT_REFUSED
    config = project.config
    branch = args.branch if args.branch is not None else gitutil.current_branch(config.root)
    worktree = args.worktree if args.worktree is not None else str(gitutil.toplevel(config.root))
    try:
        claim, created = claims.claim(
            config,
            task.id,
            owner=args.owner or claims.default_owner(),
            branch=branch or None,
            worktree=worktree or None,
            takeover=args.takeover,
            local_only=args.local_only,
        )
    except claims.ClaimConflict as exc:
        _emit({"claimed": False, "reason": str(exc), "claim": exc.claim.to_dict() if exc.claim else None}, args.json, "")
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    verb = "claimed" if created else "already held"
    _emit({"claimed": True, "created": created, "claim": claim.to_dict()}, args.json, f"{verb} {task.id} as {claim.owner}")
    return EXIT_OK


def cmd_release(args) -> int:
    config = load_config(Path(args.root).resolve() if args.root else find_root(Path.cwd()))
    try:
        released = claims.release(config, args.id, args.owner or claims.default_owner(), force=args.force, local_only=args.local_only)
    except claims.ClaimConflict as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    if released is None:
        print(f"taskrail: {args.id} is not claimed", file=sys.stderr)
        return EXIT_NOT_FOUND
    _emit({"released": released.to_dict()}, args.json, f"released {args.id}")
    return EXIT_OK


def cmd_claims(args) -> int:
    config = load_config(Path(args.root).resolve() if args.root else find_root(Path.cwd()))
    local = claims.read_all(config)
    rows = []
    for claim in local.values():
        rows.append({**claim.to_dict(), "stale": claims.stale_reason(config, claim)})
    remote_only = []
    if args.remote:
        if not config.claim_remote:
            print("taskrail: [git].claim_remote is not configured", file=sys.stderr)
            return EXIT_USAGE
        remote_only = [task_id for task_id in claims.list_remote(config) if task_id not in local]
    lines = [
        f"{r['id']:<6} {r['owner']:<24} {r['branch'] or '—':<30} {'stale: ' + r['stale'] if r['stale'] else 'live'}"
        for r in rows
    ]
    lines += [f"{task_id:<6} (claimed on {config.claim_remote} from another clone)" for task_id in remote_only]
    _emit({"local": rows, "remote_only": remote_only}, args.json, "\n".join(lines) or "no claims")
    return EXIT_OK


def _backlog_arg(config, name: str | None):
    if name is None:
        if len(config.backlogs) == 1:
            return config.backlogs[0]
        print("taskrail: several backlogs are configured; pass --backlog", file=sys.stderr)
        return None
    backlog = config.backlog(name)
    if backlog is None:
        print(f"taskrail: no backlog `{name}`", file=sys.stderr)
    return backlog


def cmd_reserve_id(args) -> int:
    config = load_config(Path(args.root).resolve() if args.root else find_root(Path.cwd()))
    backlog = _backlog_arg(config, args.backlog)
    if backlog is None:
        return EXIT_USAGE
    try:
        task_id = ids.reserve(config, backlog, args.owner or claims.default_owner())
    except ids.LockTimeout as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    _emit({"id": task_id, "backlog": backlog.name}, args.json, task_id)
    return EXIT_OK


def cmd_unreserve_id(args) -> int:
    config = load_config(Path(args.root).resolve() if args.root else find_root(Path.cwd()))
    backlog = next(
        (b for b in config.backlogs if args.id.startswith(b.prefix) and args.id[len(b.prefix):].isdigit()), None
    )
    if backlog is None or not ids.cancel_reservation(config, backlog, args.id):
        print(f"taskrail: {args.id} is not reserved", file=sys.stderr)
        return EXIT_NOT_FOUND
    _emit({"cancelled": args.id}, args.json, f"cancelled reservation {args.id}")
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

    claim = add("claim", cmd_claim, "Claim a pending task so no other agent takes it.")
    claim.add_argument("id")
    claim.add_argument("--owner", help="claim owner (default: $TASKRAIL_OWNER or user@host)")
    claim.add_argument("--branch", help="branch the work happens on (default: current branch)")
    claim.add_argument("--worktree", help="worktree the work happens in (default: this worktree)")
    claim.add_argument("--takeover", action="store_true", help="replace a stale claim")
    claim.add_argument("--ignore-deps", action="store_true", help="claim even if dependencies are not done")
    claim.add_argument("--local-only", action="store_true", help="do not mirror the claim to the remote")
    claim.add_argument("--allow-invalid", action="store_true")

    release = add("release", cmd_release, "Release a claim.")
    release.add_argument("id")
    release.add_argument("--owner")
    release.add_argument("--force", action="store_true", help="release a claim held by someone else")
    release.add_argument("--local-only", action="store_true")

    listing_claims = add("claims", cmd_claims, "List claims and whether each is live or stale.")
    listing_claims.add_argument("--remote", action="store_true", help="also list claims made from other clones")

    reserve = add("reserve-id", cmd_reserve_id, "Reserve the next task ID for a backlog.")
    reserve.add_argument("--backlog")
    reserve.add_argument("--owner")

    unreserve = add("unreserve-id", cmd_unreserve_id, "Cancel an ID reservation that will not be used.")
    unreserve.add_argument("id")

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
    except (ConfigError, gitutil.GitError) as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
