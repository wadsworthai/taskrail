"""Command-line interface."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from taskrail import __version__, branches, claims, gitutil, ids, install, prior, review, stack, writer
from taskrail.autopilot import runs as autopilot_runs
from taskrail.config import CORE_TASK_COLUMNS, find_root, load_config
from taskrail.issues import ConfigError, Issue
from taskrail.model import Project, Status
from taskrail.project import load_project
from taskrail.query import STATES, base_dict, blocked_by, eligible, state, task_dict, unmerged_dependencies
from taskrail.templates import render

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_CONFLICT = 4
EXIT_REFUSED = 5

# `new` flags that fill each core task column; ID and ✓ are set by taskrail itself.
CORE_COLUMN_FLAGS = {"Kind": "--kind", "Title": "--title", "Pts": "--pts", "Depends On": "--depends-on", "Description": "--description"}


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
    return f"{task.id:<6} {task.status_raw} {task_state:<11} {task.kind:<8} {points:>4}  {task.epic:<4}  {task.title}{deps}"


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
    data["kind_descriptor"] = kind.to_dict(task) if kind else None
    data["prior_work"] = prior.prior_work(project.config.root, task.id, data["branch"], data["artifact"])
    lines = [
        f"{task.id} — {task.title}",
        f"  backlog {task.backlog} · epic {task.epic} · kind {task.kind} · state {data['state']}",
        f"  points {task.points if task.points is not None else '—'} · depends on {', '.join(task.depends_on) or '—'}",
    ]
    if data["blocked_by"]:
        lines.append(f"  blocked by {', '.join(data['blocked_by'])}")
    if data["base"]:
        base = data["base"]
        lines.append(f"  base {base['onto'] or '—'} ({base['reason']})")
    if data["claim"]:
        claim = data["claim"]
        lines.append(f"  claimed by {claim['owner']} on {claim['branch'] or '—'} since {claim['created']}")
    if data["skill"]:
        lines.append(f"  skill {data['skill']}")
    lines.extend(prior.text_lines(data["prior_work"], task.id, data["artifact"]))
    if kind:
        for stage in kind.stages:
            if not stage.applies(task):
                mark = f" — not applicable ({stage.predicate.column})"
            elif stage.judgement:
                mark = " — executor's judgement"
            else:
                mark = ""
            lines.append(f"  · {stage.name} (gate: {stage.gate}{', commit' if stage.commit else ''}){mark}")
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
    finished = stack.done_on_branch(project).get(task.id)
    if finished is not None:
        mainline = project.config.backlog(task.backlog).mainline
        print(f"taskrail: {task.id} is done on branch {', '.join(finished.refs)}, not yet merged into {mainline}", file=sys.stderr)
        return EXIT_REFUSED
    blockers = blocked_by(task, project)
    if blockers and not args.ignore_deps:
        print(f"taskrail: {task.id} is blocked by {', '.join(blockers)}; pass --ignore-deps to claim anyway", file=sys.stderr)
        return EXIT_REFUSED
    config = project.config
    if args.run is not None:
        if autopilot_runs.read(config, args.run) is None:
            print(f"taskrail: no autopilot run `{args.run}`", file=sys.stderr)
            return EXIT_NOT_FOUND
    branch = args.branch if args.branch is not None else gitutil.current_branch(config.root)
    worktree = args.worktree if args.worktree is not None else str(gitutil.toplevel(config.root))
    base = _claim_base(task, project)
    try:
        claim, created = claims.claim(
            config,
            task.id,
            owner=args.owner or claims.default_owner(),
            branch=branch or None,
            worktree=worktree or None,
            takeover=args.takeover,
            local_only=args.local_only,
            base=base,
            run=args.run,
        )
    except claims.ClaimConflict as exc:
        _emit({"claimed": False, "reason": str(exc), "claim": exc.claim.to_dict() if exc.claim else None}, args.json, "")
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    recorded, warning = _freeze_branch(task, project, claim.branch)
    if warning:
        print(f"taskrail: warning: {warning}", file=sys.stderr)
    if created and args.run is not None:
        try:
            with autopilot_runs.update(config, args.run) as run:  # the run keeps its member after `done` releases the claim
                autopilot_runs.lane(run, task.id)
        except (autopilot_runs.RunNotFound, ids.LockTimeout) as exc:
            print(f"taskrail: claimed {task.id}, but could not list it in run {args.run}: {exc}", file=sys.stderr)
            return EXIT_CONFLICT
    verb = "claimed" if created else "already held"
    _emit(
        {"claimed": True, "created": created, "claim": claim.to_dict(), "branch_recorded": recorded, "warning": warning},
        args.json,
        f"{verb} {task.id} as {claim.owner}",
    )
    return EXIT_OK


def _freeze_branch(task, project: Project, claimed_on: str | None) -> tuple[bool, str | None]:
    """Record the template branch a task is claimed on, so a later title edit cannot move it; warn on any other branch."""
    resolved, source = branches.resolve(task, project)
    if claimed_on and claimed_on == resolved:
        if source == branches.TEMPLATE:
            branches.write(project.config, task.id, resolved)
            return True, None
        return False, None
    where = f"branch {claimed_on}" if claimed_on else "a detached HEAD"
    return False, (
        f"{task.id} was claimed on {where}, but its branch is {resolved or '—'}; work on that branch, "
        f"or run `taskrail branch {task.id} <NAME>` to name the branch the task is worked on"
    )


def _claim_base(task, project: Project) -> dict | None:
    """The base a claimed branch started from; `commit` is its fork point, so `rebase --onto` works later."""
    base = base_dict(task, project)
    if not base or not base["onto"]:
        return None
    fork = gitutil.run(project.config.root, "merge-base", "HEAD", base["onto"], check=False).stdout.strip()
    return {"onto": base["onto"], "commit": fork or None, "dependency": base["dependency"]}


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
    aliases = project.config.column_aliases
    core_names = {core.lower(): core for core in CORE_TASK_COLUMNS}
    core_names.update({alias.lower(): core for core, alias in aliases.items()})
    for pair in args.column or []:
        name, sep, value = pair.partition("=")
        if not sep:
            print(f"taskrail: --column expects NAME=VALUE, got `{pair}`", file=sys.stderr)
            return EXIT_USAGE
        core = core_names.get(name.strip().lower())
        if core is not None:
            flag = CORE_COLUMN_FLAGS.get(core)
            how = f"set it with {flag}" if flag else "taskrail sets it"
            named = f" (named `{aliases[core]}` here)" if core in aliases else ""
            print(f"taskrail: --column cannot set core column {core}{named}; {how}", file=sys.stderr)
            return EXIT_USAGE
        values[name.strip()] = value.strip()

    config = origin_config = project.config
    if args.branch is not None:
        if not args.workspace:
            print("taskrail: --branch needs --workspace; name an existing task's branch with `taskrail branch <ID> <NAME>`", file=sys.stderr)
            return EXIT_USAGE
        gitutil.common_dir(config.root)
        problem = branches.invalid_name(project, args.branch)
        if problem:
            print(f"taskrail: {problem}", file=sys.stderr)
            return EXIT_USAGE
        other = branches.owner_of(project, args.branch)
        if other:
            print(f"taskrail: {args.branch} is the branch of {other}", file=sys.stderr)
            return EXIT_REFUSED
    kind = project.kinds.get(args.kind)
    if args.workspace and kind is None:
        from taskrail.kinds import defined_kind_names

        allowed = config.allowed_kinds
        disallowed = allowed and args.kind in defined_kind_names(config)
        reason = f"is not allowed (kinds.allowed: {', '.join(sorted(allowed))})" if disallowed else "is not defined"
        print(f"taskrail: kind `{args.kind}` {reason}", file=sys.stderr)
        return EXIT_USAGE
    task_id = ids.reserve(config, backlog.config, args.owner or claims.default_owner())
    values["ID"] = task_id
    values["✓"] = Status.PENDING.value
    result = {"id": task_id, "backlog": backlog.config.name, "epic": epic.id}

    workspace = None
    if args.workspace:
        try:
            depends_on = [item.strip() for item in (args.depends_on or "").split(",") if item.strip()]
            workspace = _open_workspace(project, backlog.config, kind, epic.id, task_id, args.title, depends_on, args.branch)
        except _WorkspaceRefused as exc:
            ids.cancel_reservation(config, backlog.config, task_id)
            print(f"taskrail: {exc}", file=sys.stderr)
            return exc.code
        # The row is written inside the new workspace, against the backlog as it is on its base.
        config = dataclasses.replace(config, root=workspace["path"])
        project, _ = load_project(config)
        epic = next((e for b in project.backlogs for e in b.epics if b.config.name == backlog.config.name and e.id == epic.id), None)
        if epic is None:
            _close_workspace(workspace)
            ids.cancel_reservation(origin_config, backlog.config, task_id)
            print(f"taskrail: epic `{args.epic}` does not exist on {workspace['base']}", file=sys.stderr)
            return EXIT_NOT_FOUND
        result.update(branch=workspace["branch"], workspace=str(workspace["path"]), base=workspace["base"])

    edits = writer.Edits(config)
    try:
        writer.add_task(edits, project, epic, values)
    except writer.WriteError as exc:
        if workspace:
            _close_workspace(workspace)
        ids.cancel_reservation(origin_config, backlog.config, task_id)
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
    text = task_id if not workspace else f"{task_id}\nworkspace {workspace['path']} on branch {workspace['branch']} from {workspace['base']}"
    code = _write(edits, args.json, result, text)
    if code != EXIT_OK:
        if workspace:
            _close_workspace(workspace)
        ids.cancel_reservation(origin_config, backlog.config, task_id)
    elif args.branch is not None:
        branches.write(origin_config, task_id, args.branch)
    return code


class _WorkspaceRefused(Exception):
    def __init__(self, message: str, code: int = EXIT_REFUSED):
        super().__init__(message)
        self.code = code


def _open_workspace(
    project: Project, backlog_config, kind, epic_id: str, task_id: str, title: str, depends_on: list[str], branch: str | None = None
) -> dict:
    """Create the branch (and worktree) a new task will be worked in, from the base `show` would report."""
    from taskrail.model import Task

    config = project.config
    probe = Task(
        id=task_id, status=Status.PENDING, status_raw=Status.PENDING.value, kind=kind.name, points=None, points_raw="",
        depends_on=depends_on, title=title, description="", columns={}, backlog=backlog_config.name, epic=epic_id,
        file=backlog_config.file, line=0, order=0,
    )
    branch = branch or branches.task_branch(probe, project)
    gitutil.common_dir(config.root)
    chosen = base_dict(probe, project)
    if chosen is None:
        raise _WorkspaceRefused(f"could not determine the base of {backlog_config.mainline}", EXIT_USAGE)
    base = review.Base(chosen["onto"], chosen["diverged"], chosen["reason"])
    if base.diverged:
        raise _WorkspaceRefused(f"{base.reason}; decide which one to branch from")
    if len(unmerged_dependencies(probe, project)) > 1:
        raise _WorkspaceRefused(base.reason)
    if base.onto is None:
        raise _WorkspaceRefused(base.reason, EXIT_USAGE)
    if gitutil.branch_exists(config.root, branch):
        raise _WorkspaceRefused(f"branch {branch} already exists")
    if config.worktree == "required":
        path = (config.root / config.worktree_dir / branch).resolve()
        if path.exists():
            raise _WorkspaceRefused(f"{path} already exists")
        gitutil.run(config.root, "worktree", "add", "--quiet", str(path), "-b", branch, base.onto)
        return {"path": path, "branch": branch, "base": base.onto, "worktree": True, "origin": config.root}
    if gitutil.run(config.root, "status", "--porcelain").stdout.strip():
        raise _WorkspaceRefused("this checkout has uncommitted changes; commit or set them aside before switching branch")
    previous = gitutil.current_branch(config.root)
    gitutil.run(config.root, "switch", "--quiet", "-c", branch, base.onto)
    return {"path": config.root, "branch": branch, "base": base.onto, "worktree": False, "origin": config.root, "previous": previous}


def _close_workspace(workspace: dict) -> None:
    """Undo a workspace that `new --workspace` just created and nothing else has used."""
    origin = workspace["origin"]
    if workspace["worktree"]:
        gitutil.run(origin, "worktree", "remove", "--force", str(workspace["path"]), check=False)
    elif workspace.get("previous"):
        gitutil.run(origin, "switch", "--quiet", workspace["previous"], check=False)
    gitutil.run(origin, "branch", "-D", workspace["branch"], check=False)


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


def cmd_branch(args) -> int:
    """Name or rename a task's branch: `git branch -m` when the old branch exists here, then record the name."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    config = project.config
    root = config.root
    gitutil.common_dir(root)
    name = args.name
    problem = branches.invalid_name(project, name)
    if problem:
        print(f"taskrail: {problem}", file=sys.stderr)
        return EXIT_USAGE
    other = branches.owner_of(project, name, except_id=task.id)
    if other:
        print(f"taskrail: {name} is the branch of {other}", file=sys.stderr)
        return EXIT_REFUSED
    owner = args.owner or claims.default_owner()
    claim = claims.read(config, task.id)
    if claim is not None and claim.owner != owner and not args.force:
        print(f"taskrail: {task.id} is claimed by {claim.owner}; pass --force", file=sys.stderr)
        return EXIT_CONFLICT

    old = branches.task_branch(task, project)
    old_local = bool(old) and gitutil.branch_exists(root, old)
    remote = review.resolve_remote(root, config.backlog(task.backlog).mainline, config.review.remote).name
    remote_refs = set(gitutil.refs(root, "refs/remotes"))
    remote_copies: list[str] = []
    if old != name:
        if old_local and gitutil.branch_exists(root, name):
            print(f"taskrail: branch {name} already exists; {old} cannot be renamed to it", file=sys.stderr)
            return EXIT_REFUSED
        if old and f"refs/remotes/{remote}/{old}" in remote_refs:
            remote_copies.append(f"{remote}/{old}")
        taken = f"refs/remotes/{remote}/{name}" in remote_refs and not gitutil.branch_exists(root, name)
        if (remote_copies or taken) and not args.force:
            reasons = []
            if remote_copies:
                reasons.append(f"{remote}/{old} exists: the pushed branch and any pull request from it would stay behind")
            if taken:
                reasons.append(f"{remote}/{name} exists and publishing would overwrite it")
            print(f"taskrail: {'; '.join(reasons)}; pass --force to go ahead (the remote is never changed)", file=sys.stderr)
            return EXIT_REFUSED

    renamed = False
    if old_local and old != name:
        result = gitutil.run(root, "branch", "-m", old, name, check=False)
        if result.returncode != 0:
            print(f"taskrail: git branch -m {old} {name}: {result.stderr.strip()}", file=sys.stderr)
            return EXIT_USAGE
        renamed = True
    branches.write(config, task.id, name)

    claim_updated = False
    if claim is not None and old != name and claim.branch == old:
        claims.rename_branch(config, task.id, name, local_only=args.local_only)
        claim_updated = True

    checked_out = gitutil.worktree_branches(root).get(name)
    data = {
        "id": task.id,
        "branch": name,
        "previous": old,
        "renamed": renamed,
        "claim_updated": claim_updated,
        "worktree": str(checked_out) if checked_out else None,
        "remote_copies": remote_copies,
    }
    if renamed:
        text = f"{task.id} branch renamed from {old} to {name}"
    else:
        text = f"{task.id} branch recorded as {name}"
    text += "".join(f"\nleft on the remote: {copy}" for copy in remote_copies)
    _emit(data, args.json, text)
    return EXIT_OK


def cmd_review(args) -> int:
    """Prepare a closed task for review: fetch, pick the rebase base, push, and link a pull request."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    config = project.config
    root = config.root
    kind = project.kinds.get(task.kind)
    backlog = config.backlog(task.backlog)
    head = branches.task_branch(task, project)
    current = gitutil.current_branch(root)
    if current != head:
        print(f"taskrail: run review on the task branch {head} (current: {current or 'detached HEAD'})", file=sys.stderr)
        return EXIT_REFUSED
    if task.status is not Status.DONE:
        print(f"taskrail: {task.id} is {task.status.label} on this branch; run `taskrail done {task.id}` first", file=sys.stderr)
        return EXIT_REFUSED

    settings = config.review
    target = backlog.mainline
    remote = review.resolve_remote(root, target, settings.remote)
    fetched = False
    if settings.fetch and not args.no_fetch:
        result = gitutil.run(root, "fetch", "--quiet", remote.name, check=False)
        if result.returncode != 0:
            print(f"taskrail: git fetch {remote.name} failed: {result.stderr.strip()}", file=sys.stderr)
            return EXIT_USAGE
        fetched = True

    if settings.rebase:
        # After the fetch: a dependency may have been merged, or its branch moved, meanwhile.
        chosen = base_dict(task, project)
        if chosen is None:
            print(f"taskrail: could not determine the base of {target}", file=sys.stderr)
            return EXIT_USAGE
        base = review.Base(chosen["onto"], chosen["diverged"], chosen["reason"])
        rebase = {
            "enabled": True,
            "onto": base.onto,
            "diverged": base.diverged,
            "needed": bool(base.onto) and not review.contains(root, base.onto),
            "reason": base.reason,
            "dependency": chosen["dependency"],
        }
    else:
        base = None
        rebase = {
            "enabled": False, "onto": None, "diverged": False, "needed": False, "reason": "rebase is disabled in [review]",
            "dependency": None,
        }

    remote_url = gitutil.run(root, "remote", "get-url", remote.name, check=False).stdout.strip()
    parsed = review.parse_remote_url(remote_url) if remote_url else None
    provider = review.detect_provider(settings, parsed)
    title = review.pr_title(
        task,
        args.type or (kind.commit_type if kind and kind.commit_type else "chore"),
        args.scope if args.scope is not None else settings.scope,
        args.breaking,
    )
    since = base.onto if base and base.onto else None
    body = review.pr_body(task, render(kind.artifact, task, config) if kind else None, review.reopened_ids(root, since))
    url = review.pull_request_url(
        provider, review.web_base(settings, parsed), parsed.path if parsed else None, target, head, title, body, settings.url_template
    )

    push_info = {"enabled": config.push_task_branch, "pushed": False, "command": None, "error": None}
    data = {
        "id": task.id,
        "head": head,
        "target": target,
        "remote": remote.name,
        "remote_source": remote.source,
        "fetched": fetched,
        "rebase": rebase,
        "push": push_info,
        "pull_request": {"provider": provider, "title": title, "body": body, "url": url},
        "published": False,
    }

    if base is not None and base.diverged:
        _emit(data, args.json, f"{base.reason}; decide which one {head} should be rebased onto")
        print(f"taskrail: {base.reason}", file=sys.stderr)
        return EXIT_REFUSED

    if not args.publish:
        steps = []
        if rebase["needed"]:
            steps.append(f"rebase onto {rebase['onto']}: git rebase {rebase['onto']}")
        steps.append(f"then run: taskrail review {task.id} --publish")
        _emit(data, args.json, "\n".join([f"{task.id} ready for review against {target}", *steps]))
        return EXIT_OK

    if rebase["needed"]:
        print(f"taskrail: {head} does not include {rebase['onto']}; rebase before publishing", file=sys.stderr)
        _emit(data, args.json, "")
        return EXIT_REFUSED

    try:
        if config.push_task_branch and not args.no_push:
            pushed = review.push(root, remote.name, head)
            push_info.update(pushed=pushed.pushed, command=" ".join(pushed.command), error=pushed.error)
            if not pushed.pushed:
                print(f"taskrail: push rejected: {pushed.error}", file=sys.stderr)
                _emit(data, args.json, "")
                return EXIT_CONFLICT
        else:
            push_info["command"] = " ".join(review.push_command(root, remote.name, head))
    except gitutil.GitError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE

    data["published"] = True
    lines = [f"pushed {head} to {remote.name}" if push_info["pushed"] else f"not pushed; to push: {push_info['command']}", "", title]
    lines.append(url if url else "no pull request link: set [review].provider (and web_url) for this host")
    _emit(data, args.json, "\n".join(lines))
    return EXIT_OK


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
    claim.add_argument("--run", help="the autopilot run that owns this lane")
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
    new.add_argument("--workspace", action="store_true", help="create the task's branch and worktree from the mainline and add the row there")
    new.add_argument("--branch", help="with --workspace, the branch name to use instead of the kind's template")
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

    branch_cmd = add("branch", cmd_branch, "Name or rename a task's branch; claims, show and review follow it.")
    branch_cmd.add_argument("id")
    branch_cmd.add_argument("name", help="the branch name")
    branch_cmd.add_argument("--owner", help="who is renaming (default: $TASKRAIL_OWNER or user@host)")
    branch_cmd.add_argument("--force", action="store_true", help="rename a pushed branch, a name taken on the remote, or a task claimed by someone else")
    branch_cmd.add_argument("--local-only", action="store_true", help="do not update the claim's remote copy")
    branch_cmd.add_argument("--allow-invalid", action="store_true")

    review_cmd = add("review", cmd_review, "Prepare a closed task for review: fetch, rebase base, push, pull request link.")
    review_cmd.add_argument("id")
    review_cmd.add_argument("--publish", action="store_true", help="push the branch and print the pull request link")
    review_cmd.add_argument("--no-fetch", action="store_true", help="skip fetching the review remote")
    review_cmd.add_argument("--no-push", action="store_true", help="with --publish, print the push command instead of pushing")
    review_cmd.add_argument("--type", help="Conventional Commits type of the title (default: the kind's commit_type)")
    review_cmd.add_argument("--scope", help="Conventional Commits scope of the title (default: [review].scope)")
    review_cmd.add_argument("--breaking", action="store_true", help="mark the title as a breaking change (!)")

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

    from taskrail.autopilot.commands import register as register_autopilot

    register_autopilot(commands)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, gitutil.GitError) as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
