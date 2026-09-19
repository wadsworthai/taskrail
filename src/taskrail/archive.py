"""Moving closed tasks and closed epics out of a backlog into its archive document (DESIGN.md §7.6).

The archive is the same Markdown as a backlog — epic sections holding task tables — so a row keeps
its exact line, `grep` finds a task wherever it lives, `ids.used_ids` reads it with the parser it
already has, and the merge driver merges two branches' archives row by row. Nothing reads it back
into a backlog: `validate` never opens it, and a row that leaves is gone from the backlog for good.
Only the autopilot reads its rows, to resolve a run member the backlog no longer holds (T121).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from taskrail import writer
from taskrail.backlog import EPIC_HEADING, _index, _is_task_table, _parse_tasks
from taskrail.markdown import parse_sections, split_row
from taskrail.model import Backlog, Epic, Project, Status, Task

CLOSED = (Status.DONE, Status.DISCARDED)  # completed and discarded rows archive alike


@dataclass
class HeldBack:
    """A closed row that stays because a row remaining in a backlog depends on it."""

    id: str
    depended_on_by: list[str]

    @property
    def reason(self) -> str:
        verb = "depends" if len(self.depended_on_by) == 1 else "depend"
        return f"{', '.join(self.depended_on_by)} {verb} on it"

    def as_dict(self) -> dict:
        return {"id": self.id, "depended_on_by": self.depended_on_by, "reason": self.reason}


@dataclass
class Plan:
    backlog: Backlog
    archive: str  # the archive file, relative to the repository root
    tasks: list[Task] = field(default_factory=list)
    epics: list[Epic] = field(default_factory=list)  # epics archived whole: every row of theirs moves
    held_back: list[HeldBack] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.tasks and not self.epics

    def as_dict(self) -> dict:
        return {
            "backlog": self.backlog.config.name,
            "archive": self.archive,
            "archived": [task.id for task in self.tasks],
            "epics": [epic.id for epic in self.epics],
            "held_back": [held.as_dict() for held in self.held_back],
        }


def plan(project: Project, backlog: Backlog) -> Plan:
    """What `archive` would move out of this backlog, and which closed rows a remaining row holds.

    A dependency named by a row that stays must stay too — `depends-unknown` is a validation error
    and `validate` does not read the archive — so held-back rows are found to a fixed point: holding
    one back may hold back the closed rows it depends on in turn.
    """
    moving = {task.id for task in backlog.tasks if task.status in CLOSED}
    while True:
        held = {
            dependency
            for task in project.tasks
            if task.id not in moving
            for dependency in task.depends_on
            if dependency in moving
        }
        if not held:
            break
        moving -= held

    held_back = []
    for task in backlog.tasks:
        if task.status in CLOSED and task.id not in moving:
            dependents = sorted({other.id for other in project.tasks if other.id not in moving and task.id in other.depends_on})
            held_back.append(HeldBack(task.id, dependents))
    return Plan(
        backlog=backlog,
        archive=backlog.config.archive_path,
        tasks=[task for task in backlog.tasks if task.id in moving],
        epics=[epic for epic in backlog.epics if epic.tasks and all(task.id in moving for task in epic.tasks)],
        held_back=held_back,
    )


def holding(config, task_id: str) -> str | None:
    """The archive file a task ID sits in, for a command that no longer finds the task (T107)."""
    from taskrail.ids import _task_ids

    for backlog in config.backlogs:
        relative = backlog.archive_path
        try:
            text = (config.root / relative).read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError, IsADirectoryError):
            continue
        if task_id in _task_ids(text, backlog.prefix, config.column_aliases):
            return relative
    return None


ARCHIVED_KEY = "archived_tasks"


def archived_task(project: Project, task_id: str) -> Task | None:
    """A task the checkout's archive holds, for an autopilot run member its backlog no longer holds (T121).

    Only the autopilot reads it: `show`, `list`, `next` and `validate` stay blind to the archive.
    """
    return archived_tasks(project).get(task_id)


def archived_tasks(project: Project) -> dict[str, Task]:
    """Every row in the checkout's archives by ID, read once per project."""
    if ARCHIVED_KEY not in project.cache:
        found: dict[str, Task] = {}
        for backlog in project.backlogs:
            relative = backlog.config.archive_path
            try:
                text = (project.config.root / relative).read_text(encoding="utf-8")
            except (FileNotFoundError, UnicodeDecodeError, IsADirectoryError):
                continue
            for task in _parse(text, relative, backlog, project.config):
                found.setdefault(task.id, task)
        project.cache[ARCHIVED_KEY] = found
    return project.cache[ARCHIVED_KEY]


def _parse(text: str, relative: str, backlog: Backlog, config) -> list[Task]:
    """The rows of an archive document, read with the backlog's own parser; its issues are not reported."""
    counter = [0]
    tasks: list[Task] = []
    for section in parse_sections(text):
        match = EPIC_HEADING.match(section.title or "")
        if not match:
            continue
        epic = Epic(id=match.group(1), name=match.group(2), objective="", file=None, backlog=backlog.config.name, listing_line=0)
        _parse_tasks(epic, section, relative, config, counter, [])
        tasks += epic.tasks
    return tasks


def apply_plan(edits: writer.Edits, plan: Plan) -> None:
    """Append the moving rows to the archive and take them, and any archived epic, out of the backlog."""
    aliases = edits.config.column_aliases
    rows = _source_rows(edits, plan.tasks, aliases)
    _write_archive(edits, plan, rows, aliases)
    _remove_rows(edits, plan.tasks, rows)
    for epic in plan.epics:
        writer.remove_epic(edits, plan.backlog.config, epic)


def _source_rows(edits: writer.Edits, tasks: list[Task], aliases) -> dict[str, tuple[str, str, str, str, int]]:
    """Each task's own row line, its table's header and separator lines, its file and its line number."""
    wanted = {task.id for task in tasks}
    found: dict[str, tuple[str, str, str, str, int]] = {}
    for relative in sorted({task.file for task in tasks}):
        lines = edits.lines(relative)
        for section in parse_sections("".join(lines)):
            for table in section.tables:
                if not _is_task_table(table, aliases):
                    continue
                position = _index(table.header, aliases)["ID"]
                header, separator = lines[table.line - 1], lines[table.line]
                for number, cells in table.rows:
                    if position < len(cells) and cells[position] in wanted:
                        found[cells[position]] = (lines[number - 1], header, separator, relative, number)
    missing = sorted(wanted - set(found))
    if missing:
        raise writer.WriteError(f"could not locate the row(s) for {', '.join(missing)}")
    return found


def _remove_rows(edits: writer.Edits, tasks: list[Task], rows: dict) -> None:
    """Delete the moved rows, a file at a time and from the bottom up, so no line number shifts."""
    by_file: dict[str, list[int]] = {}
    for task in tasks:
        _, _, _, relative, number = rows[task.id]
        by_file.setdefault(relative, []).append(number)
    for relative, numbers in by_file.items():
        lines = edits.lines(relative)
        for number in sorted(numbers, reverse=True):
            del lines[number - 1]
        edits.set_lines(relative, lines)


def _write_archive(edits: writer.Edits, plan: Plan, rows: dict, aliases) -> None:
    relative = plan.archive
    if edits.exists(relative):
        lines = edits.lines(relative)
    else:
        lines = [
            f"# Archive — {plan.backlog.config.name}\n",
            "\n",
            f"Closed tasks and epics moved out of `{plan.backlog.config.file}` by `taskrail archive`.\n",
            "taskrail does not validate this file and never reads a row back into the backlog; it\n",
            "reads it so an archived ID is never allocated again and an autopilot run still\n",
            "resolves its archived tasks.\n",
        ]
    whole = {epic.id for epic in plan.epics}
    for epic in plan.backlog.epics:
        moving = [task for task in plan.tasks if task.epic == epic.id]
        if not moving:
            continue
        _ensure_section(lines, epic)
        if epic.id in whole:
            _describe(lines, epic)
        for task in moving:
            row, header, separator, _, _ = rows[task.id]
            _append_row(lines, epic.id, row, header, separator, aliases)
    edits.set_lines(relative, lines)


def _section(lines: list[str], epic_id: str) -> tuple[list, int] | None:
    sections = parse_sections("".join(lines))
    for index, section in enumerate(sections):
        match = EPIC_HEADING.match(section.title or "")
        if match and match.group(1) == epic_id:
            return sections, index
    return None


def _ensure_section(lines: list[str], epic: Epic) -> None:
    if _section(lines, epic.id) is not None:
        return
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines += ["\n", f"## {epic.id} — {epic.name}\n"]


def _describe(lines: list[str], epic: Epic) -> None:
    """Carry an archived epic's objective and `Done when:` into its section; the Epics table goes."""
    sections, index = _section(lines, epic.id)
    start, end = writer._section_bounds(sections, index, len(lines))
    body = "".join(lines[start:end])
    added = [
        text
        for text in (f"Objective: {epic.objective}\n" if epic.objective else "", f"Done when: {epic.done_when}\n" if epic.done_when else "")
        if text and text not in body
    ]
    if added:
        lines[start + 1 : start + 1] = ["\n", *added]


def _append_row(lines: list[str], epic_id: str, row: str, header: str, separator: str, aliases) -> None:
    """Put the row at the end of the section's table with the same header, or start that table."""
    sections, index = _section(lines, epic_id)
    start, end = writer._section_bounds(sections, index, len(lines))
    wanted = [cell.strip().lower() for cell in split_row(header) or []]
    for table in sections[index].tables:
        if _is_task_table(table, aliases) and [cell.strip().lower() for cell in table.header] == wanted:
            lines.insert(table.rows[-1][0] if table.rows else table.line + 1, row)
            return
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines[insert_at:insert_at] = ["\n", header, separator, row]
