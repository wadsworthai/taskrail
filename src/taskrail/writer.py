"""Editing backlog files with minimal diffs, validated in memory before anything is written."""

from __future__ import annotations

import os
import re
import unicodedata

from taskrail.backlog import EPIC_HEADING, EPICS_TITLE, _index, _is_task_table
from taskrail.config import BacklogConfig, Config
from taskrail.issues import Issue
from taskrail.markdown import Section, parse_sections, split_row
from taskrail.model import Epic, Project, Status, Task
from taskrail.templates import slugify  # noqa: F401  (re-exported for the CLI)

DEFAULT_TASK_COLUMNS = ("✓", "ID", "Kind", "Pts", "Depends On", "Title", "Description")
DEFAULT_WIDTHS = {"✓": 2, "ID": 4, "Kind": 7, "Pts": 3, "Depends On": 10, "Title": 30, "Description": 30}


class WriteError(Exception):
    """The requested edit cannot be made."""


def escape_cell(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise WriteError("table cells cannot contain line breaks")
    return value.replace("|", "\\|").strip()


class Edits:
    """Pending file contents keyed by path relative to the repository root."""

    def __init__(self, config: Config):
        self.config = config
        self.files: dict[str, str] = {}

    def read(self, relative: str) -> str:
        if relative in self.files:
            return self.files[relative]
        return (self.config.root / relative).read_text(encoding="utf-8")

    def exists(self, relative: str) -> bool:
        return relative in self.files or (self.config.root / relative).exists()

    def lines(self, relative: str) -> list[str]:
        return self.read(relative).splitlines(keepends=True)

    def set_lines(self, relative: str, lines: list[str]) -> None:
        self.files[relative] = "".join(lines)


def _cell_spans(line: str) -> list[tuple[int, int]]:
    """Character ranges of each cell's content, between unescaped pipes."""
    body = line.rstrip("\r\n")
    pipes = []
    escaped = False
    for position, char in enumerate(body):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            pipes.append(position)
    spans = [(pipes[i] + 1, pipes[i + 1]) for i in range(len(pipes) - 1)]
    if pipes and body[pipes[-1] + 1 :].strip():
        spans.append((pipes[-1] + 1, len(body)))
    return spans


def replace_cell(line: str, index: int, value: str) -> str:
    """Replace one cell, keeping the width of the original cell whenever the value fits."""
    start, end = _cell_spans(line)[index]
    width = end - start
    content = f" {value} "
    original = display_width(line[start:end])
    if display_width(content) < original:
        content = _pad(content, original)
    return line[:start] + content + line[end:]


def display_width(text: str) -> int:
    """Terminal/editor column width: wide characters such as ⬜ ✅ ❌ take two columns."""
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


def _pad(value: str, width: int) -> str:
    return value + " " * max(width - display_width(value), 0)


def _row(values: list[str], widths: list[int]) -> str:
    cells = [_pad(value, width) for value, width in zip(values, widths)]
    return "| " + " | ".join(cells) + " |\n"


def _widths(separator_line: str, count: int) -> list[int]:
    """Column content widths of an aligned table: separator dashes minus the two padding spaces."""
    spans = _cell_spans(separator_line)
    widths = [max(len(separator_line[a:b].strip()) - 2, 1) for a, b in spans]
    return (widths + [1] * count)[:count]


def _section_bounds(sections: list[Section], index: int, total_lines: int) -> tuple[int, int]:
    """0-based [start, end) line range of a section, heading included."""
    start = sections[index].line - 1
    end = sections[index + 1].line - 1 if index + 1 < len(sections) else total_lines
    return start, end


def _find_epic_section(text: str, epic_id: str) -> tuple[list[Section], int]:
    sections = parse_sections(text)
    for index, section in enumerate(sections):
        match = EPIC_HEADING.match(section.title or "")
        if match and match.group(1) == epic_id:
            return sections, index
    raise WriteError(f"no section for epic {epic_id}")


def _epics_table(text: str):
    for section in parse_sections(text):
        if section.title and section.title.strip().lower() == EPICS_TITLE:
            for table in section.tables:
                if "ID" in _index(table.header):
                    return table
    raise WriteError("the backlog has no `## Epics` table")


def set_status(edits: Edits, task: Task, status: Status) -> None:
    lines = edits.lines(task.file)
    text = "".join(lines)
    for section in parse_sections(text):
        for table in section.tables:
            for number, _ in table.rows:
                if number == task.line and _is_task_table(table, edits.config.column_aliases):
                    column = _index(table.header, edits.config.column_aliases)["✓"]
                    lines[number - 1] = replace_cell(lines[number - 1], column, status.value)
                    edits.set_lines(task.file, lines)
                    return
    raise WriteError(f"could not locate the row for {task.id} at {task.file}:{task.line}")


def _header_template(edits: Edits, project: Project, backlog: BacklogConfig) -> tuple[str, str]:
    """Header and separator lines copied from an existing task table of the backlog, or a default."""
    for task in project.tasks:
        if task.backlog != backlog.name:
            continue
        lines = edits.lines(task.file)
        for section in parse_sections("".join(lines)):
            for table in section.tables:
                if _is_task_table(table, project.config.column_aliases):
                    return lines[table.line - 1], lines[table.line]
    aliases = project.config.column_aliases
    core_and_names = [(c, aliases.get(c, c)) for c in DEFAULT_TASK_COLUMNS] + [(c, c) for c in project.config.custom_columns]
    columns = [name for _, name in core_and_names]
    widths = [max(display_width(name), DEFAULT_WIDTHS.get(core, 3)) for core, name in core_and_names]
    header = _row(columns, widths)
    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|\n"
    return header, separator


def add_task(edits: Edits, project: Project, epic: Epic, values: dict[str, str]) -> None:
    """Append a row to the epic's last task table, creating the table if the epic has none."""
    backlog = project.config.backlog(epic.backlog)
    relative = epic.section_file
    lines = edits.lines(relative)
    sections, index = _find_epic_section("".join(lines), epic.id)
    tables = [t for t in sections[index].tables if _is_task_table(t, project.config.column_aliases)]

    if tables:
        table = tables[-1]
        header, separator_line = table.header, lines[table.line]
        insert_at = table.rows[-1][0] if table.rows else table.line + 1
        new_lines = []
    else:
        header_line, separator_line = _header_template(edits, project, backlog)
        header = split_row(header_line) or []
        start, end = _section_bounds(sections, index, len(lines))
        insert_at = end
        while insert_at > start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        new_lines = ["\n", header_line, separator_line]

    columns = _index(header, project.config.column_aliases)
    unknown = [name for name in values if name not in columns]
    if unknown:
        raise WriteError(f"the task table has no column(s): {', '.join(unknown)}")
    row = ["" for _ in header]
    for name, position in columns.items():
        row[position] = escape_cell(values.get(name, "—" if name not in ("Description",) else ""))
    new_lines.append(_row(row, _widths(separator_line, len(header))))
    lines[insert_at:insert_at] = new_lines
    edits.set_lines(relative, lines)


def add_epic(
    edits: Edits,
    backlog: BacklogConfig,
    epic_id: str,
    name: str,
    objective: str,
    done_when: str | None,
    file: str | None,
) -> None:
    main = backlog.file
    lines = edits.lines(main)
    table = _epics_table("".join(lines))
    columns = _index(table.header)
    if file is not None and "File" not in columns:
        raise WriteError("the Epics table has no File column")
    row = ["" for _ in table.header]
    values = {"ID": epic_id, "Epic": name, "Objective": objective, "File": file or "—"}
    for column, position in columns.items():
        row[position] = escape_cell(values.get(column, "—"))
    insert_at = table.rows[-1][0] if table.rows else table.line + 1
    lines[insert_at:insert_at] = [_row(row, _widths(lines[table.line], len(table.header)))]

    section = [f"## {epic_id} — {name}\n", "\n"]
    if done_when:
        section += [f"Done when: {done_when}\n", "\n"]
    if file is None:
        while lines and not lines[-1].strip():
            lines.pop()
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += ["\n", *section]
        while lines and not lines[-1].strip():
            lines.pop()
        edits.set_lines(main, lines)
    else:
        if edits.exists(file):
            raise WriteError(f"{file} already exists")
        edits.set_lines(main, lines)
        edits.files[file] = "".join(section).rstrip("\n") + "\n"


def split_epic(edits: Edits, backlog: BacklogConfig, epic: Epic, file: str) -> None:
    if epic.file is not None:
        raise WriteError(f"epic {epic.id} already lives in {epic.file}")
    if edits.exists(file):
        raise WriteError(f"{file} already exists")
    main = backlog.file
    lines = edits.lines(main)
    sections, index = _find_epic_section("".join(lines), epic.id)
    start, end = _section_bounds(sections, index, len(lines))
    moved = lines[start:end]
    while moved and not moved[-1].strip():
        moved.pop()
    remaining = lines[:start] + lines[end:]
    while start > 0 and start < len(remaining) and not remaining[start - 1].strip() and not remaining[start].strip():
        del remaining[start]
    while remaining and not remaining[-1].strip():
        remaining.pop()

    table = _epics_table("".join(remaining))
    columns = _index(table.header)
    if "File" not in columns:
        raise WriteError("the Epics table has no File column")
    for number, cells in table.rows:
        if cells[columns["ID"]] == epic.id:
            remaining[number - 1] = replace_cell(remaining[number - 1], columns["File"], escape_cell(file))
            break
    edits.set_lines(main, remaining)
    text = "".join(moved)
    edits.files[file] = text if text.endswith("\n") else text + "\n"


def apply(edits: Edits) -> list[Issue]:
    """Validate the edited project; write every file atomically only if it has no errors."""
    from taskrail.project import load_project

    _, issues = load_project(edits.config, overlay=edits.files)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        return errors
    # New files first, so a backlog file never references an epic file that is not there yet.
    for relative, content in sorted(edits.files.items(), key=lambda item: (edits.config.root / item[0]).exists()):
        path = edits.config.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.taskrail-tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    return []
