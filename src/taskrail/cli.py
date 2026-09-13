"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taskrail import __version__, claims, gitutil, ids, install, writer
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


def _write(edits: "writer.Edits", as_json: bool, result: dict, text: str) -> int:
    errors = writer.apply(edits)
    if errors:
        for issue in errors:
            print(issue.format(), file=sys.stderr)
        print("taskrail: the change would leave the backlog invalid; nothing was written", file=sys.stderr)
        return EXIT_INVALID
    _emit({**result, "files": sorted(edits.files)}, as_json, text)
    return EXIT_OK


def _find_epic(project: Project, epic_id: str, backlog_name: str | None):
    matches = [
        (backlog, epic)
        for backlog in project.backlogs
        for epic in backlog.epics
        if epic.id == epic_id and (backlog_name is None or backlog.config.name == backlog_name)
    ]
    if not matches:
        print(f"taskrail: no epic `{epic_id}`", file=sys.stderr)
        return None
    if len(matches) > 1:
        print(f"taskrail: epic `{epic_id}` exists in several backlogs; pass --backlog", file=sys.stderr)
        return None
    return matches[0]


def cmd_new(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    found = _find_epic(project, args.epic, args.backlog)
    if found is None:
        return EXIT_NOT_FOUND
    backlog, epic = found
    values = {"Kind": args.kind, "Title": args.title}
    if args.pts is not None:
        values["Pts"] = str(args.pts)
    if args.depends_on:
        values["Depends On"] = ", ".join(item.strip() for item in args.depends_on.split(",") if item.strip())
    if args.description:
        values["Description"] = args.description
    for pair in args.column or []:
        name, sep, value = pair.partition("=")
        if not sep:
            print(f"taskrail: --column expects NAME=VALUE, got `{pair}`", file=sys.stderr)
            return EXIT_USAGE
        values[name.strip()] = value.strip()

    config = project.config
    task_id = ids.reserve(config, backlog.config, args.owner or claims.default_owner())
    values["ID"] = task_id
    values["✓"] = Status.PENDING.value
    edits = writer.Edits(config)
    try:
        writer.add_task(edits, project, epic, values)
    except writer.WriteError as exc:
        ids.cancel_reservation(config, backlog.config, task_id)
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
    code = _write(edits, args.json, {"id": task_id, "backlog": backlog.config.name, "epic": epic.id}, task_id)
    if code != EXIT_OK:
        ids.cancel_reservation(config, backlog.config, task_id)
    return code


def _change_status(args, status: Status) -> int:
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
    config = project.config
    owner = args.owner or claims.default_owner()
    try:
        claim = claims.read(config, task.id)
    except gitutil.GitError:
        claim = None

    if status is Status.DONE:
        if claim is None and not args.force:
            print(f"taskrail: {task.id} is not claimed; claim it before marking it done, or pass --force", file=sys.stderr)
            return EXIT_REFUSED
        blockers = blocked_by(task, project)
        if blockers and not args.force:
            print(f"taskrail: {task.id} still depends on {', '.join(blockers)}; pass --force to mark it done anyway", file=sys.stderr)
            return EXIT_REFUSED
    if claim is not None and claim.owner != owner and not args.force:
        print(f"taskrail: {task.id} is claimed by {claim.owner}; pass --force", file=sys.stderr)
        return EXIT_CONFLICT

    edits = writer.Edits(config)
    writer.set_status(edits, task, status)
    code = _write(edits, args.json, {"id": task.id, "status": status.label}, f"{task.id} {status.label}")
    if code == EXIT_OK and claim is not None:
        claims.release(config, task.id, owner, force=True)
    return code


def cmd_done(args) -> int:
    return _change_status(args, Status.DONE)


def cmd_discard(args) -> int:
    return _change_status(args, Status.DISCARDED)


def cmd_reopen(args) -> int:
    reason = args.reason.strip()
    if not reason:
        print("taskrail: --reason must not be empty; it becomes the body of the commit message", file=sys.stderr)
        return EXIT_USAGE
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    if task.status is Status.PENDING:
        print(f"taskrail: {task.id} is already pending", file=sys.stderr)
        return EXIT_REFUSED

    claimed = _local_claims(project)
    dependents = [
        {"id": other.id, "state": other_state}
        for other in project.tasks
        if task.id in other.depends_on
        and (other_state := state(other, project, claimed)) in ("done", "claimed")
    ]
    # The backlog holds state, not history: the reason travels in the commit that reopens the task.
    message = f"Reopen {task.id}: {task.title}\n\n{reason}\n\nReopens: {task.id}\n"
    edits = writer.Edits(project.config)
    writer.set_status(edits, task, Status.PENDING)
    text = [f"{task.id} {Status.PENDING.label}"]
    text += [f"{d['id']} depends on {task.id} and is {d['state']}" for d in dependents]
    text += ["Suggested commit message:", "", message.rstrip("\n")]
    result = {
        "id": task.id,
        "status": Status.PENDING.label,
        "reason": reason,
        "dependents": dependents,
        "commit_message": message,
    }
    return _write(edits, args.json, result, "\n".join(text))


def cmd_epic_add(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    config = project.config
    backlog_config = _backlog_arg(config, args.backlog)
    if backlog_config is None:
        return EXIT_USAGE
    backlog = next(b for b in project.backlogs if b.config.name == backlog_config.name)
    prefix = backlog_config.epic_prefix
    epic_id = args.id
    if epic_id is None:
        numbers = [int(e.id[len(prefix):]) for e in backlog.epics]
        epic_id = f"{prefix}{max(numbers, default=0) + 1:02d}"
    if any(e.id == epic_id for e in backlog.epics):
        print(f"taskrail: epic `{epic_id}` already exists", file=sys.stderr)
        return EXIT_REFUSED
    file = args.file
    if args.own_file and file is None:
        file = f"todo/{epic_id}-{writer.slugify(args.name)}.md"
    edits = writer.Edits(config)
    try:
        writer.add_epic(edits, backlog_config, epic_id, args.name, args.objective, args.done_when, file)
    except writer.WriteError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return _write(edits, args.json, {"id": epic_id, "backlog": backlog_config.name, "file": file}, epic_id)


def cmd_epic_split(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    found = _find_epic(project, args.id, args.backlog)
    if found is None:
        return EXIT_NOT_FOUND
    backlog, epic = found
    file = args.file or f"todo/{epic.id}-{writer.slugify(epic.name)}.md"
    edits = writer.Edits(project.config)
    try:
        writer.split_epic(edits, backlog.config, epic, file)
    except writer.WriteError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return _write(edits, args.json, {"id": epic.id, "file": file}, f"moved {epic.id} to {file}")


def _install_root(args) -> Path:
    if args.root:
        return Path(args.root).resolve()
    try:
        return gitutil.toplevel(Path.cwd())
    except gitutil.GitError:
        return Path.cwd()


def cmd_init(args) -> int:
    unknown = [name for name in args.integration or [] if name not in install.INTEGRATIONS]
    if unknown:
        print(f"taskrail: unknown integration(s): {', '.join(unknown)}; see `taskrail integration list`", file=sys.stderr)
        return EXIT_USAGE
    report = install.install(
        _install_root(args),
        args.integration or [],
        github_workflow=args.github_workflow,
        pre_commit=args.pre_commit,
        force=args.force,
    )
    _emit(report.to_dict(), args.json, report.format())
    return EXIT_OK


def cmd_upgrade(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    try:
        report = install.upgrade(root, force=args.force)
    except FileNotFoundError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    _emit(report.to_dict(), args.json, report.format())
    return EXIT_OK


def cmd_integration_list(args) -> int:
    rows = [{"name": name, **info} for name, info in install.INTEGRATIONS.items()]
    _emit(rows, args.json, "\n".join(f"{r['name']:<9} {r['label']:<12} skills in {r['skills_dir']}" for r in rows))
    return EXIT_OK


def cmd_self_upgrade(args) -> int:
    try:
        command, code = install.self_upgrade(args.tag, args.dry_run)
    except LookupError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    _emit({"command": command, "exit": code}, args.json, " ".join(command))
    return EXIT_OK if code == 0 else EXIT_USAGE


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

    init = add("init", cmd_init, "Install taskrail into a repository. Safe to run again.")
    init.add_argument("--integration", action="append", metavar="NAME", help="agent to install skills for; repeatable")
    init.add_argument("--github-workflow", action="store_true", help="add a GitHub Actions workflow running validate")
    init.add_argument("--pre-commit", action="store_true", help="add a git pre-commit hook running validate")
    init.add_argument("--force", action="store_true", help="replace files edited locally or not written by taskrail")

    upgrade = add("upgrade", cmd_upgrade, "Re-install skills and managed files for this CLI version and pin it.")
    upgrade.add_argument("--force", action="store_true")

    integration = commands.add_parser("integration", help="Agent integrations.")
    integration_commands = integration.add_subparsers(dest="integration_command", required=True)
    integration_list = integration_commands.add_parser("list", help="Available agent integrations.")
    integration_list.add_argument("--json", action="store_true")
    integration_list.set_defaults(handler=cmd_integration_list)

    self_cmd = commands.add_parser("self", help="Manage the installed CLI.")
    self_commands = self_cmd.add_subparsers(dest="self_command", required=True)
    self_upgrade = self_commands.add_parser("upgrade", help="Reinstall the CLI from a release tag with uv.")
    self_upgrade.add_argument("--tag", help="release tag, e.g. v0.1.0 (default: the latest)")
    self_upgrade.add_argument("--dry-run", action="store_true", help="print the command without running it")
    self_upgrade.add_argument("--json", action="store_true")
    self_upgrade.set_defaults(handler=cmd_self_upgrade)

    new = add("new", cmd_new, "Add a task to an epic, with a freshly reserved ID.")
    new.add_argument("--epic", required=True)
    new.add_argument("--backlog", help="needed when several backlogs have an epic with this ID")
    new.add_argument("--kind", required=True)
    new.add_argument("--title", required=True)
    new.add_argument("--pts", type=int)
    new.add_argument("--depends-on", help="comma-separated task IDs")
    new.add_argument("--description")
    new.add_argument("--column", action="append", metavar="NAME=VALUE", help="a custom column value; repeatable")
    new.add_argument("--owner")
    new.add_argument("--allow-invalid", action="store_true")

    done = add("done", cmd_done, "Mark a claimed task done and release its claim.")
    done.add_argument("id")
    done.add_argument("--owner")
    done.add_argument("--force", action="store_true", help="skip the claim and dependency checks")

    discard = add("discard", cmd_discard, "Mark a pending task discarded.")
    discard.add_argument("id")
    discard.add_argument("--owner")
    discard.add_argument("--force", action="store_true", help="discard even if someone else holds the claim")

    reopen = add("reopen", cmd_reopen, "Move a done or discarded task back to pending.")
    reopen.add_argument("id")
    reopen.add_argument("--reason", required=True, help="why it is reopened; returned as the commit message body")

    epic = commands.add_parser("epic", help="Manage epics.")
    epic_commands = epic.add_subparsers(dest="epic_command", required=True)
    epic_add = epic_commands.add_parser("add", help="Add an epic.")
    epic_add.add_argument("--id", help="epic ID (default: next in the backlog)")
    epic_add.add_argument("--name", required=True)
    epic_add.add_argument("--objective", required=True)
    epic_add.add_argument("--done-when")
    epic_add.add_argument("--backlog")
    placement = epic_add.add_mutually_exclusive_group()
    placement.add_argument("--file", help="put the epic in this file")
    placement.add_argument("--own-file", action="store_true", help="put the epic in todo/<id>-<slug>.md")
    epic_add.add_argument("--json", action="store_true")
    epic_add.set_defaults(handler=cmd_epic_add)
    epic_split = epic_commands.add_parser("split", help="Move an inline epic to its own file.")
    epic_split.add_argument("id")
    epic_split.add_argument("--file", help="target file (default: todo/<id>-<slug>.md)")
    epic_split.add_argument("--backlog")
    epic_split.add_argument("--json", action="store_true")
    epic_split.set_defaults(handler=cmd_epic_split)

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
