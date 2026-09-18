"""Command-line interface."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from taskrail import __version__, archive, branches, checks, claims, gitutil, history, ids, install, mergedriver, prior, review, stack, writer
from taskrail.autopilot import runs as autopilot_runs
from taskrail.config import CORE_TASK_COLUMNS, find_root, load_config
from taskrail.issues import ConfigError, Issue
from taskrail.kinds import commit_policy, commit_source_label
from taskrail.model import NONE_MARKERS, Project, Status
from taskrail.project import load_project
from taskrail.query import STATES, base_dict, blocked_by, eligible, main_checkout, state, task_dict, unmerged_dependencies
from taskrail.templates import render

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_CONFLICT = 4
EXIT_REFUSED = 5
EXIT_CHECK_FAILED = 6

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


def _fetch_records(project: Project) -> None:
    """Bring mirrored branch records into this clone before any branch is resolved; a failure only warns (§6.4)."""
    config = project.config
    if not config.branch_record_remote:
        return
    _, error = branches.fetch(config)
    if error:
        print(f"taskrail: warning: could not fetch branch records from {config.branch_record_remote}: {error}", file=sys.stderr)
    branches.forget_cache(project)
    project.cache.pop(stack.CACHE_KEY, None)


def _mirror_record(config, record, local_only: bool = False) -> dict | None:
    """Push a record just written to `branch_record_remote`; a failure only warns. None when nothing is mirrored."""
    if record is None or local_only or not config.branch_record_remote:
        return None
    result = branches.push(config, record)
    if not result["pushed"]:
        print(
            f"taskrail: warning: could not push the branch record {result['ref']} to {result['name']}: {result['error']}; "
            f"retry with `taskrail branch {record.id} {record.branch}`",
            file=sys.stderr,
        )
    return result


def _line(task, project: Project, claimed: dict | None = None) -> str:
    points = f"{task.points}pt" if task.points is not None else "—"
    task_state = state(task, project, claimed)
    deps = f"  ← {', '.join(task.depends_on)}" if task.depends_on else ""
    return f"{task.id:<6} {task.status_raw} {task_state:<11} {task.kind:<8} {points:>4}  {task.epic:<4}  {task.title}{deps}"


def cmd_validate(args) -> int:
    project, issues = _load(args)
    # Only validate reads history (§7): write commands, list, show and next never pay for it.
    report = history.check_reopens(project, limit=args.history_limit, enabled=not args.no_history)
    issues = [*issues, *report.issues]
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    summary = f"{len(project.tasks)} task(s) in {len(project.backlogs)} backlog(s): {len(errors)} error(s), {len(warnings)} warning(s)"
    note = report.note()
    _emit(
        {"valid": not errors, "tasks": len(project.tasks), "issues": [i.to_dict() for i in issues], "history": report.to_dict()},
        args.json,
        "\n".join([*(i.format() for i in issues), *([note] if note else []), summary]),
    )
    return EXIT_INVALID if errors else EXIT_OK


def cmd_list(args) -> int:
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    if args.fetch:
        _fetch_records(project)
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
    if args.fetch:
        _fetch_records(project)
    claimed = _local_claims(project)
    data = task_dict(task, project, claimed)
    kind = project.kinds.get(task.kind)
    data["kind_descriptor"] = kind.to_dict(task) if kind else None
    searched = None if branches.is_current(project.config) else data["branch"]  # the checked-out branch is no evidence
    data["close"] = {
        "commit": commit_policy(kind, project.config)[0],
        "review": "report" if branches.is_current(project.config) else "publish",  # §7.1 (T083)
    }
    data["prior_work"] = prior.prior_work(
        project.config.root, task.id, searched, data["artifact"], (data["base"] or {}).get("onto"), project.config.backlog(task.backlog).file
    )
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
        if base["row"] == "missing":
            lines.append(f"  row not on {base['onto']}: only this checkout has it; run `taskrail workspace {task.id}`")
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
    if data["close"]["commit"] == "on-done":
        lines.append(f"  commit on-done ({commit_source_label(kind, project.config)})")
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
    if args.fetch:
        _fetch_records(project)
    claimed = _local_claims(project)
    tasks = eligible(project, args.backlog, claimed)[: args.limit]
    entries = [task_dict(t, project, claimed) for t in tasks]
    _emit(
        entries,
        args.json,
        "\n".join(_line(t, project, claimed) + _row_mark(entry["base"]) for t, entry in zip(tasks, entries)) or "no eligible tasks",
    )
    return EXIT_OK


def _row_mark(base: dict | None) -> str:
    """`next`'s note for a task whose row its base lacks and only this checkout has (T070)."""
    return f"  (row not on {base['onto']})" if base and base["row"] == "missing" else ""


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
    if not args.local_only:
        _fetch_records(project)
    finished = stack.done_on_branch(project).get(task.id)
    if finished is not None:
        mainline = project.config.backlog(task.backlog).mainline
        print(f"taskrail: {task.id} is done on branch {', '.join(finished.refs)}, not yet merged into {mainline}", file=sys.stderr)
        return EXIT_REFUSED
    dropped = stack.discarded_on_branch(project).get(task.id)
    if dropped is not None:
        mainline = project.config.backlog(task.backlog).mainline
        print(f"taskrail: {task.id} is discarded on branch {', '.join(dropped.refs)}, not yet merged into {mainline}", file=sys.stderr)
        return EXIT_REFUSED
    blockers = blocked_by(task, project)
    if blockers and not args.ignore_deps:
        print(f"taskrail: {task.id} is blocked by {', '.join(blockers)}; pass --ignore-deps to claim anyway", file=sys.stderr)
        return EXIT_REFUSED
    config = project.config
    if args.run is not None:
        owning_run = autopilot_runs.read(config, args.run)
        if owning_run is None:
            print(f"taskrail: no autopilot run `{args.run}`", file=sys.stderr)
            return EXIT_NOT_FOUND
        if autopilot_runs.is_closed(owning_run):
            print(f"taskrail: {autopilot_runs.closed_message(args.run)}; claim without --run or in an open run", file=sys.stderr)
            return EXIT_REFUSED
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
    record_remote = _mirror_record(config, branches.read(config, task.id) if recorded else None, args.local_only)
    if created and args.run is not None:
        try:
            with autopilot_runs.update(config, args.run) as run:  # the run keeps its member after `done` releases the claim
                autopilot_runs.lane(run, task.id)["base"] = claim.base  # and its fork point, for `autopilot merged`
        except (autopilot_runs.RunNotFound, ids.LockTimeout) as exc:
            print(f"taskrail: claimed {task.id}, but could not list it in run {args.run}: {exc}", file=sys.stderr)
            return EXIT_CONFLICT
    verb = "claimed" if created else "already held"
    _emit(
        {
            "claimed": True, "created": created, "claim": claim.to_dict(), "branch_recorded": recorded, "warning": warning,
            "record_remote": record_remote,
        },
        args.json,
        f"{verb} {task.id} as {claim.owner}",
    )
    return EXIT_OK


def _freeze_branch(task, project: Project, claimed_on: str | None) -> tuple[bool, str | None]:
    """Record the template branch a task is claimed on, so a later title edit cannot move it; warn on any other branch."""
    resolved, source = branches.resolve(task, project)
    if source == branches.CURRENT:  # the checked-out branch is the task's: nothing to record (DESIGN.md §6.1)
        return False, None if claimed_on else f"{task.id} was claimed on a detached HEAD: check out a branch to work the task on"
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


def _write(edits: "writer.Edits", as_json: bool, result: dict, text: str, on_written=None) -> int:
    errors = writer.apply(edits)
    if errors:
        for issue in errors:
            print(issue.format(), file=sys.stderr)
        print("taskrail: the change would leave the backlog invalid; nothing was written", file=sys.stderr)
        return EXIT_INVALID
    if on_written is not None:
        on_written(result)
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


def _custom_columns(project: Project, pairs: list[str] | None) -> dict[str, str] | None:
    """`--column NAME=VALUE` pairs as a dict; None, after printing why, for a malformed pair or a core column."""
    aliases = project.config.column_aliases
    core_names = {core.lower(): core for core in CORE_TASK_COLUMNS}
    core_names.update({alias.lower(): core for core, alias in aliases.items()})
    values: dict[str, str] = {}
    for pair in pairs or []:
        name, sep, value = pair.partition("=")
        if not sep:
            print(f"taskrail: --column expects NAME=VALUE, got `{pair}`", file=sys.stderr)
            return None
        core = core_names.get(name.strip().lower())
        if core is not None:
            flag = CORE_COLUMN_FLAGS.get(core)
            how = f"set it with {flag}" if flag else "taskrail sets it"
            named = f" (named `{aliases[core]}` here)" if core in aliases else ""
            print(f"taskrail: --column cannot set core column {core}{named}; {how}", file=sys.stderr)
            return None
        values[name.strip()] = value.strip()
    return values


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
    custom = _custom_columns(project, args.column)
    if custom is None:
        return EXIT_USAGE
    values.update(custom)

    config = origin_config = project.config
    if args.workspace and branches.is_current(config):
        print(f"taskrail: {branches.CURRENT_REFUSAL}", file=sys.stderr)
        return EXIT_REFUSED
    if args.workspace:
        _fetch_records(project)
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
    result = {"id": task_id, "backlog": backlog.config.name, "epic": epic.id, "warning": None}

    workspace = None
    if args.workspace:
        try:
            depends_on = [item.strip() for item in (args.depends_on or "").split(",") if item.strip()]
            probe = _probe_task(backlog.config, kind, epic.id, task_id, args.title, depends_on)
            workspace = _open_workspace(project, backlog.config, probe, args.branch)
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

    def record_branch(result: dict) -> None:
        if workspace:  # record every workspace's branch, so commands outside it find the task's row there (T071)
            written = branches.write(origin_config, task_id, workspace["branch"])
            result["record_remote"] = _mirror_record(origin_config, written)

    warning = None
    if not workspace and not branches.is_current(config) and gitutil.current_branch(config.root) == backlog.config.mainline:
        warning = (
            f"{task_id} was written to this checkout of {backlog.config.mainline}, uncommitted; commit it to "
            f"{backlog.config.mainline}, or run `taskrail workspace {task_id}` to move it into its own branch"
        )
        result["warning"] = warning
    code = _write(edits, args.json, result, text, on_written=record_branch)
    if code != EXIT_OK:
        if workspace:
            _close_workspace(workspace)
        ids.cancel_reservation(origin_config, backlog.config, task_id)
    elif warning:
        print(f"taskrail: warning: {warning}", file=sys.stderr)
    return code


class _WorkspaceRefused(Exception):
    def __init__(self, message: str, code: int = EXIT_REFUSED):
        super().__init__(message)
        self.code = code


def _probe_task(backlog_config, kind, epic_id: str, task_id: str, title: str, depends_on: list[str]):
    """A task not written yet, enough to resolve its branch and base."""
    from taskrail.model import Task

    return Task(
        id=task_id, status=Status.PENDING, status_raw=Status.PENDING.value, kind=kind.name, points=None, points_raw="",
        depends_on=depends_on, title=title, description="", columns={}, backlog=backlog_config.name, epic=epic_id,
        file=backlog_config.file, line=0, order=0,
    )


def _workspace_target(project: Project, backlog_config, task, branch: str | None = None) -> tuple[str, str, Path | None]:
    """The branch, base and worktree path (None without worktrees) a task's workspace gets; refuses what cannot be created."""
    config = project.config
    branch = branch or branches.task_branch(task, project)
    gitutil.common_dir(config.root)
    chosen = base_dict(task, project)
    if chosen is None:
        raise _WorkspaceRefused(f"could not determine the base of {backlog_config.mainline}", EXIT_USAGE)
    base = review.Base(chosen["onto"], chosen["diverged"], chosen["reason"])
    if base.diverged:
        raise _WorkspaceRefused(f"{base.reason}; decide which one to branch from")
    if len(unmerged_dependencies(task, project)) > 1:
        raise _WorkspaceRefused(base.reason)
    if base.onto is None:
        raise _WorkspaceRefused(base.reason, EXIT_USAGE)
    if gitutil.branch_exists(config.root, branch):
        raise _WorkspaceRefused(f"branch {branch} already exists")
    path = None
    if config.worktree == "required":
        # Under the worktree base `show` reports (the main checkout, or the directory holding a bare
        # repository), whichever checkout runs this (T073, T075).
        path = (main_checkout(project) / config.worktree_dir / branch).resolve()
        if path.exists():
            raise _WorkspaceRefused(f"{path} already exists")
    return branch, base.onto, path


def _open_workspace(project: Project, backlog_config, task, branch: str | None = None) -> dict:
    """Create the branch (and worktree) a task will be worked in, from the base `show` would report."""
    config = project.config
    branch, onto, path = _workspace_target(project, backlog_config, task, branch)
    if path is not None:
        gitutil.run(config.root, "worktree", "add", "--quiet", "--no-track", str(path), "-b", branch, onto)
        return {"path": path, "branch": branch, "base": onto, "worktree": True, "origin": config.root}
    if gitutil.run(config.root, "status", "--porcelain").stdout.strip():
        raise _WorkspaceRefused("this checkout has uncommitted changes; commit or set them aside before switching branch")
    previous = gitutil.current_branch(config.root)
    gitutil.run(config.root, "switch", "--quiet", "--no-track", "-c", branch, onto)
    return {"path": config.root, "branch": branch, "base": onto, "worktree": False, "origin": config.root, "previous": previous}


def _close_workspace(workspace: dict) -> None:
    """Undo a workspace that `new --workspace` or `workspace` just created and nothing else has used."""
    origin = workspace["origin"]
    if workspace["worktree"]:
        gitutil.run(origin, "worktree", "remove", "--force", str(workspace["path"]), check=False)
    elif workspace.get("previous"):
        gitutil.run(origin, "switch", "--quiet", workspace["previous"], check=False)
    gitutil.run(origin, "branch", "-D", workspace["branch"], check=False)


def _print_issues(issues: list[Issue], what: str) -> None:
    for issue in issues:
        print(issue.format(), file=sys.stderr)
    print(f"taskrail: {what} would leave the backlog invalid; nothing was written", file=sys.stderr)


def cmd_workspace(args) -> int:
    """Carry a row only this checkout has into its task's own branch and worktree, with its ID (T070)."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    if branches.is_current(project.config):
        print(f"taskrail: {branches.CURRENT_REFUSAL}", file=sys.stderr)
        return EXIT_REFUSED
    if task.status is not Status.PENDING:
        label = task.status.label if task.status else f"`{task.status_raw}`"
        print(f"taskrail: {task.id} is {label}, not pending", file=sys.stderr)
        return EXIT_REFUSED
    config = project.config
    backlog_config = config.backlog(task.backlog)
    _fetch_records(project)
    if args.branch is not None:
        gitutil.common_dir(config.root)
        problem = branches.invalid_name(project, args.branch)
        if problem:
            print(f"taskrail: {problem}", file=sys.stderr)
            return EXIT_USAGE
        other = branches.owner_of(project, args.branch, except_id=task.id)
        if other:
            print(f"taskrail: {args.branch} is the branch of {other}", file=sys.stderr)
            return EXIT_REFUSED
    for found, label in ((stack.done_on_branch(project), "done"), (stack.discarded_on_branch(project), "discarded")):
        if task.id in found:
            print(f"taskrail: {task.id} is {label} on branch {', '.join(found[task.id].refs)}", file=sys.stderr)
            return EXIT_REFUSED
    owner = args.owner or claims.default_owner()
    try:
        claim = claims.read(config, task.id)
    except gitutil.GitError:
        claim = None
    if claim is not None and claim.owner != owner:
        print(f"taskrail: {task.id} is claimed by {claim.owner}", file=sys.stderr)
        return EXIT_CONFLICT
    if claim is not None:
        print(f"taskrail: {task.id} is claimed by {owner} in this checkout; release it first with `taskrail release {task.id}`", file=sys.stderr)
        return EXIT_REFUSED
    base = base_dict(task, project)
    if base is not None and base["row"] == "on-base":
        print(
            f"taskrail: {task.id} is already on {base['onto']}; nothing to carry: create its workspace as the taskrail skill's workspace step says",
            file=sys.stderr,
        )
        return EXIT_REFUSED
    if base is not None and base["row"] == "on-branch":
        print(f"taskrail: branch {branches.task_branch(task, project)} already exists", file=sys.stderr)
        return EXIT_REFUSED
    try:
        _workspace_target(project, backlog_config, task, args.branch)
        values = writer.row_values(writer.Edits(config), task)
        removal = writer.Edits(config)
        writer.remove_task(removal, task)
    except _WorkspaceRefused as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return exc.code
    except writer.WriteError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
    errors = [issue for issue in load_project(config, overlay=removal.files)[1] if issue.severity == "error"]
    if errors:
        _print_issues(errors, f"removing {task.id} from this checkout")
        return EXIT_INVALID

    # Checked: now change things, undoing each step if a later one fails.
    originals = {relative: (config.root / relative).read_text(encoding="utf-8") for relative in removal.files}
    added = ids.keep_reservation(config, backlog_config, task.id, owner)
    state = {"workspace": None, "removed": False}

    def undo() -> None:
        if state["workspace"]:
            _close_workspace(state["workspace"])
        if state["removed"]:
            for relative, content in originals.items():
                (config.root / relative).write_text(content, encoding="utf-8")
        if added:
            ids.cancel_reservation(config, backlog_config, task.id)

    def uncommitted() -> bool:
        return bool(gitutil.run(config.root, "status", "--porcelain", "--", *removal.files).stdout.strip())

    worktrees = config.worktree == "required"
    left_uncommitted = False
    if not worktrees:  # the branch is switched in this checkout, which must be clean once the row is gone
        writer.apply(removal)
        state["removed"] = True
        left_uncommitted = uncommitted()
    try:
        state["workspace"] = workspace = _open_workspace(project, backlog_config, task, args.branch)
    except _WorkspaceRefused as exc:
        undo()
        print(f"taskrail: {exc}", file=sys.stderr)
        return exc.code

    target = dataclasses.replace(config, root=workspace["path"])
    target_project, _ = load_project(target)
    epic = next(
        (e for b in target_project.backlogs for e in b.epics if b.config.name == backlog_config.name and e.id == task.epic), None
    )
    if epic is None:
        undo()
        print(f"taskrail: epic `{task.epic}` does not exist on {workspace['base']}", file=sys.stderr)
        return EXIT_NOT_FOUND
    edits = writer.Edits(target)
    try:
        writer.add_task(edits, target_project, epic, values)
    except writer.WriteError as exc:
        undo()
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
    errors = writer.apply(edits)
    if errors:
        undo()
        _print_issues(errors, f"adding {task.id} on {workspace['base']}")
        return EXIT_INVALID
    if worktrees:
        errors = writer.apply(removal)
        if errors:
            undo()
            _print_issues(errors, f"removing {task.id} from this checkout")
            return EXIT_INVALID
        left_uncommitted = uncommitted()

    # Recorded like `new --workspace` records its branch, so the row living only there is found by its branch.
    record_remote = _mirror_record(config, branches.write(config, task.id, workspace["branch"]))
    result = {
        "id": task.id,
        "backlog": backlog_config.name,
        "epic": task.epic,
        "branch": workspace["branch"],
        "workspace": str(workspace["path"]),
        "base": workspace["base"],
        "files": sorted(edits.files),
        "removed_from": {"path": str(config.root), "files": sorted(removal.files), "uncommitted": left_uncommitted},
        "reservation_added": added,
        "record_remote": record_remote,
    }
    text = [
        task.id,
        f"workspace {workspace['path']} on branch {workspace['branch']} from {workspace['base']}",
        f"removed from {config.root}: {', '.join(sorted(removal.files))}",
    ]
    if left_uncommitted:
        text.append(f"the removal is not committed in {config.root}")
    _emit(result, args.json, "\n".join(text))
    return EXIT_OK


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

    warning = _closed_elsewhere(task, project, status)
    edits = writer.Edits(config)
    writer.set_status(edits, task, status)
    policy, _ = commit_policy(project.kinds.get(task.kind), config)
    text = f"{task.id} {status.label}" + (f"\ncommit everything {task.id} changed now, the status change included" if policy == "on-done" else "")
    code = _write(edits, args.json, {"id": task.id, "status": status.label, "commit": policy, "warning": warning}, text)
    if code == EXIT_OK and warning:  # after the write: the warning says the row has already been written here
        print(f"taskrail: warning: {warning}", file=sys.stderr)
    if code == EXIT_OK and claim is not None:
        try:
            claims.release(config, task.id, owner, force=True)
        except gitutil.GitError as exc:  # the row is written; keep the claim so the release can be retried
            print(
                f"taskrail: {task.id} is marked {status.label}, but its claim was not released: {exc}; "
                f"run `taskrail release {task.id} --force` to retry",
                file=sys.stderr,
            )
            return EXIT_USAGE
    return code


def _closed_elsewhere(task, project: Project, status: Status) -> str | None:
    """Why the checkout a status was just written in is not the task's branch, or None (T119).

    `claim` warns before the work (`_freeze_branch`); this warns after the write, because the row
    of the checkout it ran in has already changed while the task's branch still holds the old one.
    Silent with no branch to compare — outside git, and on a detached `HEAD`, which `claim` covers.
    """
    resolved, source = branches.resolve(task, project)
    if source == branches.CURRENT:  # the checked-out branch is the task's (DESIGN.md §6.4)
        return None
    current = gitutil.current_branch(project.config.root)
    if not current or not resolved or current == resolved:
        return None
    return (
        f"{task.id} was marked {status.label} in {project.config.root} on branch {current}, but its branch is "
        f"{resolved}; the row on that branch is unchanged — undo this change and run the command there, "
        f"or run `taskrail branch {task.id} <NAME>` to name the branch the task is worked on"
    )


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
        # Archived is archived: say where the row went, but never bring it back (DESIGN.md §7.6).
        where = archive.holding(project.config, args.id)
        hint = f"; it is archived in {where}, and an archived task is not reopened" if where else ""
        print(f"taskrail: no task `{args.id}`{hint}", file=sys.stderr)
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


def _empty(value: str) -> str:
    return "" if value in NONE_MARKERS else value


def _points(raw: str):
    """A points cell as JSON: its number, None when empty, else the raw text."""
    return int(raw) if raw.isdigit() else None if raw in NONE_MARKERS else raw


def cmd_edit(args) -> int:
    """Change cells of an existing task row; the status and the ID stay with their own commands."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    fields = (args.title, args.pts, args.depends_on, args.description, args.kind)
    if all(value is None for value in fields) and not args.column:
        print("taskrail: nothing to edit; pass --title, --pts, --depends-on, --description, --kind or --column", file=sys.stderr)
        return EXIT_USAGE
    pts = None if args.pts is None else args.pts.strip()
    if pts and not pts.isdigit():
        print(f"taskrail: --pts expects a whole number or an empty value, got `{args.pts}`", file=sys.stderr)
        return EXIT_USAGE
    custom = _custom_columns(project, args.column)
    if custom is None:
        return EXIT_USAGE

    task = project.task(args.id)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    config = project.config
    if not args.force:
        if task.status is not Status.PENDING:
            label = task.status.label if task.status else f"`{task.status_raw}`"
            print(f"taskrail: {task.id} is {label}, not pending; pass --force to edit it anyway", file=sys.stderr)
            return EXIT_REFUSED
        try:
            finished = stack.done_on_branch(project).get(task.id)
            dropped = stack.discarded_on_branch(project).get(task.id)
        except gitutil.GitError:
            finished = dropped = None
        if finished is not None:
            print(f"taskrail: {task.id} is done on branch {', '.join(finished.refs)}; pass --force to edit it anyway", file=sys.stderr)
            return EXIT_REFUSED
        if dropped is not None:
            print(f"taskrail: {task.id} is discarded on branch {', '.join(dropped.refs)}; pass --force to edit it anyway", file=sys.stderr)
            return EXIT_REFUSED
        try:
            claim = claims.read(config, task.id)
        except gitutil.GitError:
            claim = None
        owner = args.owner or claims.default_owner()
        if claim is not None and claim.owner != owner:
            print(f"taskrail: {task.id} is claimed by {claim.owner}; pass --force", file=sys.stderr)
            return EXIT_CONFLICT

    # Each changed field: the cell to write, and its JSON `from` and `to`.
    values: dict[str, str] = {}
    changes: dict = {}

    def change(field: str, column: str, cell: str, before, after) -> None:
        if before != after:
            values[column] = cell
            changes[field] = {"from": before, "to": after}

    if args.title is not None:
        change("title", "Title", args.title.strip(), task.title, args.title.strip())
    if pts is not None:
        change("points", "Pts", pts or "—", _points(task.points_raw), _points(pts))
    if args.depends_on is not None:
        depends = [item.strip() for item in args.depends_on.split(",") if item.strip()]
        change("depends_on", "Depends On", ", ".join(depends) or "—", task.depends_on, depends)
    if args.description is not None:
        description = args.description.strip()
        change("description", "Description", description, _empty(task.description), description)
    if args.kind is not None:
        change("kind", "Kind", args.kind.strip(), task.kind, args.kind.strip())
    columns = {}
    for name, value in custom.items():
        header = next((h for h in task.columns if h.lower() == name.lower()), None)
        if header is None:
            print(f"taskrail: the task table has no column(s): {name}", file=sys.stderr)
            return EXIT_USAGE
        if _empty(task.columns[header]) != value:
            values[header] = value or "—"
            columns[header] = {"from": task.columns[header], "to": value or "—"}
    if columns:
        changes["columns"] = columns

    edits = writer.Edits(config)
    try:
        writer.set_cells(edits, task, values)
    except writer.WriteError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE

    renames = "title" in changes or "kind" in changes
    if renames and not args.local_only:
        _fetch_records(project)
    try:
        previous, source = branches.resolve(task, project)
    except gitutil.GitError:
        previous, source = branches.template_branch(task, project), branches.TEMPLATE
    edited = dataclasses.replace(task, title=values.get("Title", task.title), kind=values.get("Kind", task.kind))
    branch = {"name": previous, "source": source, "previous": None, "recorded": False}
    if source == branches.TEMPLATE and renames:
        current = branches.template_branch(edited, project)
        if current != previous:
            try:
                keep = previous is not None and gitutil.branch_exists(config.root, previous)
            except gitutil.GitError:
                keep = False
            if keep:
                branch.update(source=branches.RECORDED, recorded=True)
            else:
                branch.update(name=current, previous=previous)
    result = {"id": task.id, "changes": changes, "branch": branch, "record_remote": None}

    text = [f"{task.id} {field}: {_shown(change['from'])} → {_shown(change['to'])}" for field, change in changes.items() if field != "columns"]
    text += [f"{task.id} {name}: {_shown(change['from'])} → {_shown(change['to'])}" for name, change in columns.items()]
    if branch["recorded"]:
        text.append(f"{task.id} branch: {branch['name']} (recorded, so the title change does not move it)")
    elif branch["previous"]:
        text.append(f"{task.id} branch: {branch['previous']} → {branch['name']}")
    if not values:
        _emit({**result, "files": []}, args.json, f"{task.id} unchanged")
        return EXIT_OK

    def record_branch(result: dict) -> None:
        if branch["recorded"]:
            written = branches.write(config, task.id, branch["name"])
            result["record_remote"] = _mirror_record(config, written, args.local_only)

    return _write(edits, args.json, result, "\n".join(text), on_written=record_branch)


def _shown(value) -> str:
    if isinstance(value, list):
        return ", ".join(value) or "—"
    return "—" if value is None or value == "" else str(value)


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
    if branches.is_current(config):
        print(f"taskrail: {branches.CURRENT_REFUSAL}", file=sys.stderr)
        return EXIT_REFUSED
    root = config.root
    gitutil.common_dir(root)
    if not args.local_only:
        _fetch_records(project)
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
    written = branches.write(config, task.id, name)
    record_remote = _mirror_record(config, written, args.local_only)

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
        "record_remote": record_remote,
    }
    if renamed:
        text = f"{task.id} branch renamed from {old} to {name}"
    else:
        text = f"{task.id} branch recorded as {name}"
    text += "".join(f"\nleft on the remote: {copy}" for copy in remote_copies)
    _emit(data, args.json, text)
    return EXIT_OK


def _review_closed(task) -> bool:
    """Whether `review` may run: the task is done or discarded here; says what to run otherwise."""
    if task.status in (Status.DONE, Status.DISCARDED):
        return True
    print(f"taskrail: {task.id} is {task.status.label} on this branch; run `taskrail done {task.id}` or `taskrail discard {task.id}` first", file=sys.stderr)
    return False


def _review_title_body(args, project, task, since: str | None) -> tuple[str, str]:
    """The pull request title and description; `Reopens:` trailers come from the commits after `since`."""
    config = project.config
    kind = project.kinds.get(task.kind)
    title = review.pr_title(
        task,
        # A discard delivers none of the kind's change, so its squash commit is a chore by default (T065).
        args.type or (kind.commit_type if kind and kind.commit_type and task.status is Status.DONE else "chore"),
        args.scope if args.scope is not None else config.review.scope,
        args.breaking,
    )
    body = review.pr_body(task, render(kind.artifact, task, config) if kind else None, review.reopened_ids(config.root, since))
    return title, body


def _review_current(args, project, task) -> int:
    """`review` under `[git] task_branch = "current"`: a report, with no fetch, rebase or push (DESIGN.md §7.1)."""
    if args.publish:
        print(f"taskrail: {review.CURRENT_PUBLISH_REFUSAL}", file=sys.stderr)
        return EXIT_REFUSED
    if not _review_closed(task):
        return EXIT_REFUSED
    config = project.config
    root = config.root
    target = config.backlog(task.backlog).mainline
    remote = review.resolve_remote(root, target, config.review.remote)
    head = gitutil.current_branch(root)
    upstream = review.upstream(root)
    title, body = _review_title_body(args, project, task, upstream["ref"] if upstream else None)
    remote_url = gitutil.run(root, "remote", "get-url", remote.name, check=False).stdout.strip()
    provider = review.detect_provider(config.review, review.parse_remote_url(remote_url) if remote_url else None)
    found = prior.matching_commits(root, task.id, None, head_only=True)
    data = {
        "id": task.id,
        "head": head,
        "target": target,
        "remote": remote.name,
        "remote_source": remote.source,
        "fetched": False,
        "rebase": {
            "enabled": False, "onto": None, "diverged": False, "needed": False, "reason": review.CURRENT_REBASE_REASON,
            "dependency": None,
        },
        "push": {"enabled": False, "pushed": False, "command": None, "error": None},
        "pull_request": {"provider": provider, "title": title, "body": body, "url": None},
        "published": False,
        "commits": found[: prior.MAX_COMMITS],
        "commits_total": len(found),
        "upstream": upstream,
    }
    lines = [f'{task.id} {task.status.label} on {head or "detached HEAD"}; review reports only ([git].task_branch is "current")']
    if found:
        lines.append(f"{len(found)} commit(s) naming {task.id}:")
        lines.extend(f"  {commit['sha'][:7]} {commit['subject']}" for commit in data["commits"])
    else:
        lines.append(f"no commits naming {task.id}")
    lines.append(f"upstream {upstream['ref']}: {upstream['ahead']} commit(s) not pushed" if upstream else "no upstream")
    lines += [f"reference title: {title}", "push with git once the human approves"]
    _emit(data, args.json, "\n".join(lines))
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
    if branches.is_current(project.config):
        return _review_current(args, project, task)
    config = project.config
    root = config.root
    backlog = config.backlog(task.backlog)
    if config.review.fetch and not args.no_fetch:
        _fetch_records(project)  # before resolving the branch, which another clone may have renamed
    head = branches.task_branch(task, project)
    current = gitutil.current_branch(root)
    if current != head:
        print(f"taskrail: run review on the task branch {head} (current: {current or 'detached HEAD'})", file=sys.stderr)
        return EXIT_REFUSED
    if not _review_closed(task):
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
    title, body = _review_title_body(args, project, task, base.onto if base and base.onto else None)
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


def cmd_checks(args) -> int:
    """Run a task's configured checks in its worktree, with its autopilot lane's resources (§7.5)."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    from taskrail import branchrows

    task = branchrows.find(project, args.id, _local_claims(project))  # also a row only its branch holds (T071)
    if task is None:
        print(f"taskrail: no task `{args.id}`", file=sys.stderr)
        return EXIT_NOT_FOUND
    try:
        result = checks.run_checks(project, task, args.stage, args.check, capture=args.json, resource_pairs=args.resource)
    except checks.ChecksRefused as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return exc.code
    _emit(result, args.json, checks.summary(result))
    return EXIT_OK if result["passed"] else EXIT_CHECK_FAILED


def cmd_archive(args) -> int:
    """Move closed rows, and epics whose rows are all closed, into each backlog's archive (§7.6)."""
    project, issues = _load(args)
    if _refuse_if_invalid(issues, args):
        return EXIT_INVALID
    config = project.config
    if args.backlog is not None and config.backlog(args.backlog) is None:
        print(f"taskrail: no backlog `{args.backlog}`", file=sys.stderr)
        return EXIT_USAGE
    # Checked here rather than at load: the default archive of two backlogs sharing an artifacts
    # root is the same path, and only writing to it would mix them. A config that never archives
    # keeps working.
    for backlog in config.backlogs:
        clash = next((b.name for b in config.backlogs if b.name != backlog.name and b.archive_path == backlog.archive_path), None)
        if clash:
            print(
                f"taskrail: backlogs `{backlog.name}` and `{clash}` both archive into {backlog.archive_path}; "
                "give each one an [[backlog]].archive of its own",
                file=sys.stderr,
            )
            return EXIT_USAGE
        owner = next((b.name for b in config.backlogs if b.file == backlog.archive_path), None)
        if owner:
            print(f"taskrail: backlog `{backlog.name}` archives into {backlog.archive_path}, which is backlog `{owner}`'s file", file=sys.stderr)
            return EXIT_USAGE
    plans = [archive.plan(project, backlog) for backlog in project.backlogs if args.backlog in (None, backlog.config.name)]

    edits = writer.Edits(config)
    if not args.dry_run:
        try:
            for plan in plans:
                if not plan.empty:
                    archive.apply_plan(edits, plan)
        except writer.WriteError as exc:
            print(f"taskrail: {exc}", file=sys.stderr)
            return EXIT_USAGE

    text: list[str] = []
    for plan in plans:
        name = plan.backlog.config.name
        if plan.empty:
            text.append(f"{name}: nothing to archive")
        else:
            verb = "would archive" if args.dry_run else "archived"
            text.append(f"{name}: {verb} {len(plan.tasks)} task(s) and {len(plan.epics)} epic(s) into {plan.archive}")
        text += [f"held back {held.id}: {held.reason}" for held in plan.held_back]
    result = {"dry_run": args.dry_run, "backlogs": [plan.as_dict() for plan in plans], "removed": sorted(edits.removed)}
    if args.dry_run:
        _emit({**result, "files": []}, args.json, "\n".join(text))
        return EXIT_OK
    return _write(edits, args.json, result, "\n".join(text), on_written=lambda _: mergedriver.refresh_attributes(config))


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
    return _write(
        edits, args.json, {"id": epic_id, "backlog": backlog_config.name, "file": file}, epic_id,
        on_written=lambda _: file and mergedriver.refresh_attributes(config),
    )


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
    return _write(
        edits, args.json, {"id": epic.id, "file": file}, f"moved {epic.id} to {file}",
        on_written=lambda _: mergedriver.refresh_attributes(project.config),
    )


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
        merge_driver=args.merge_driver,
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


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"expected a whole number of at least 1, got `{value}`")
    return number


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

    validate = add("validate", cmd_validate, "Check the configuration, kinds and every backlog.")
    validate.add_argument("--no-history", action="store_true", help="do not read git history for reopens without a Reopens trailer")
    validate.add_argument(
        "--history-limit",
        type=_positive_int,
        default=history.DEFAULT_LIMIT,
        metavar="N",
        help=f"examine at most N commits changing backlog files (default {history.DEFAULT_LIMIT})",
    )

    listing = add("list", cmd_list, "List tasks with their computed state.")
    listing.add_argument("--fetch", action="store_true", help="first fetch branch records mirrored to [git].branch_record_remote")
    listing.add_argument("--backlog")
    listing.add_argument("--epic")
    listing.add_argument("--state", choices=STATES)
    listing.add_argument("--kind")
    listing.add_argument("--allow-invalid", action="store_true", help="list even when validation fails")

    show = add("show", cmd_show, "Show one task and its kind's stages.")
    show.add_argument("--fetch", action="store_true", help="first fetch branch records mirrored to [git].branch_record_remote")
    show.add_argument("id")
    show.add_argument("--allow-invalid", action="store_true")

    nxt = add("next", cmd_next, "Eligible tasks in order: points ascending, then file order.")
    nxt.add_argument("--fetch", action="store_true", help="first fetch branch records mirrored to [git].branch_record_remote")
    nxt.add_argument("--backlog")
    nxt.add_argument("--limit", type=_positive_int, default=5, metavar="N", help="show at most N eligible tasks (default 5)")

    claim = add("claim", cmd_claim, "Claim a pending task so no other agent takes it.")
    claim.add_argument("id")
    claim.add_argument("--owner", help="claim owner (default: $TASKRAIL_OWNER or user@host)")
    claim.add_argument("--branch", help="branch the work happens on (default: current branch)")
    claim.add_argument("--worktree", help="worktree the work happens in (default: this worktree)")
    claim.add_argument("--takeover", action="store_true", help="replace a stale claim")
    claim.add_argument("--ignore-deps", action="store_true", help="claim even if dependencies are not done")
    claim.add_argument("--local-only", action="store_true", help="do not mirror the claim or the branch record to the remote")
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
    init.add_argument("--merge-driver", action="store_true", help="resolve backlog table conflicts with taskrail's git merge driver")

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
    self_upgrade.add_argument("--tag", help="release tag, e.g. v0.2.0 (default: the latest)")
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

    workspace = add(
        "workspace", cmd_workspace, "Move the row of a task missing from its base, with its ID, into the task's own branch and worktree."
    )
    workspace.add_argument("id")
    workspace.add_argument("--branch", help="the branch name to use instead of the kind's template")
    workspace.add_argument("--owner", help="who is moving it, checked against a claim and kept on the reservation (default: $TASKRAIL_OWNER or user@host)")

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

    edit = add("edit", cmd_edit, "Change cells of an existing task row: title, points, dependencies, description, kind or custom columns.")
    edit.add_argument("id")
    edit.add_argument("--title")
    edit.add_argument("--pts", help="a whole number; an empty value clears it")
    edit.add_argument("--depends-on", help="comma-separated task IDs, replacing the current ones; an empty value clears them")
    edit.add_argument("--description", help="an empty value clears it")
    edit.add_argument("--kind")
    edit.add_argument("--column", action="append", metavar="NAME=VALUE", help="a custom column value; an empty value clears it; repeatable")
    edit.add_argument("--owner", help="who is editing, checked against an existing claim (default: $TASKRAIL_OWNER or user@host)")
    edit.add_argument("--force", action="store_true", help="edit a task that is not pending or is claimed by someone else")
    edit.add_argument("--local-only", action="store_true", help="do not fetch or mirror branch records")
    edit.add_argument("--allow-invalid", action="store_true", help="edit an invalid backlog; the result is still written only if it is valid")

    branch_cmd = add("branch", cmd_branch, "Name or rename a task's branch; claims, show and review follow it.")
    branch_cmd.add_argument("id")
    branch_cmd.add_argument("name", help="the branch name")
    branch_cmd.add_argument("--owner", help="who is renaming (default: $TASKRAIL_OWNER or user@host)")
    branch_cmd.add_argument("--force", action="store_true", help="rename a pushed branch, a name taken on the remote, or a task claimed by someone else")
    branch_cmd.add_argument("--local-only", action="store_true", help="do not update the claim's remote copy or mirror the branch record")
    branch_cmd.add_argument("--allow-invalid", action="store_true")

    review_cmd = add("review", cmd_review, "Prepare a closed task for review: fetch, rebase base, push, pull request link.")
    review_cmd.add_argument("id")
    review_cmd.add_argument("--publish", action="store_true", help="push the branch and print the pull request link")
    review_cmd.add_argument("--no-fetch", action="store_true", help="skip fetching the review remote")
    review_cmd.add_argument("--no-push", action="store_true", help="with --publish, print the push command instead of pushing")
    review_cmd.add_argument("--type", help="Conventional Commits type of the title (default: the kind's commit_type)")
    review_cmd.add_argument("--scope", help="Conventional Commits scope of the title (default: [review].scope)")
    review_cmd.add_argument("--breaking", action="store_true", help="mark the title as a breaking change (!)")

    checks_cmd = add(
        "checks", cmd_checks, "Run a task's configured checks in its worktree with its autopilot lane's resources; exit 6 when one fails."
    )
    checks_cmd.add_argument("id")
    checks_cmd.add_argument("--stage", help="only this stage's checks")
    checks_cmd.add_argument("--check", action="append", metavar="NAME", help="only this check; repeatable")
    checks_cmd.add_argument(
        "--resource", action="append", metavar="NAME=VALUE", help="pass this pool value as TASKRAIL_RESOURCE_<NAME>, replacing the lane's; refused when another lane holds it; repeatable"
    )
    checks_cmd.add_argument("--allow-invalid", action="store_true")

    archive_cmd = add("archive", cmd_archive, "Move closed tasks, and epics whose tasks are all closed, into the backlog's archive.")
    archive_cmd.add_argument("--backlog", help="only this backlog (default: every configured backlog)")
    archive_cmd.add_argument("--dry-run", action="store_true", help="report what would move and write nothing")

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
    from taskrail.importer import register as register_import

    register_autopilot(commands)
    register_import(commands)
    mergedriver.register(commands)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, gitutil.GitError) as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE
