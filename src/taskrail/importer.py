"""Importing a table-based Markdown backlog that has no epics (DESIGN.md §7.3).

The conversion rewrites only what taskrail's format needs — epic headings, an `## Epics` section,
task-table headers and the cells whose value changes — and keeps every other byte of the source.
"""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from taskrail import gitutil, ids
from taskrail.backlog import EPIC_HEADING, EPICS_TITLE
from taskrail.config import (
    CORE_TASK_COLUMNS,
    BacklogConfig,
    Config,
    find_root,
    load_config,
)
from taskrail.markdown import FENCE, is_separator, parse_sections, split_row
from taskrail.model import Project, Status
from taskrail.project import load_project
from taskrail.writer import (
    _cell_spans,
    _pad,
    _row,
    display_width,
    escape_cell,
    replace_cell,
)

EXIT_OK, EXIT_INVALID, EXIT_USAGE, EXIT_CONFLICT, EXIT_REFUSED = 0, 1, 2, 4, 5

HEADING = re.compile(r"^(#{1,6})\s+(\S.*?)\s*#*\s*$")
STATUS_NAMES = {status.label: status for status in Status}
BUILTIN_STATUSES = {
    **dict.fromkeys(("⬜", "[ ]", "todo", "pending", "open"), Status.PENDING),
    **dict.fromkeys(("✅", "[x]", "done", "closed"), Status.DONE),
    **dict.fromkeys(("❌", "discarded", "cancelled"), Status.DISCARDED),
}
EMPTY_DEPENDENCIES = {"", "-", "–", "—"}
NO_STATUS = "an ID column but no status column"


class UsageError(Exception):
    """A flag or argument cannot be used."""


@dataclass
class Options:
    columns: dict[str, str] = field(default_factory=dict)  # core column -> source header
    statuses: dict[str, Status] = field(default_factory=dict)  # lower-cased value -> status
    kinds: dict[str, str] = field(default_factory=dict)  # lower-cased value -> kind
    default_kind: str | None = None
    epic_level: int | None = None
    epic_name: str = "Backlog"


@dataclass
class Heading:
    index: int  # 0-based line index
    level: int
    text: str


@dataclass
class SourceTable:
    index: int  # 0-based line index of the header row
    header: list[str]
    rows: list[tuple[int, list[str]]]
    columns: dict[str, int] = field(default_factory=dict)  # core column -> position


@dataclass
class EpicPlan:
    heading: Heading | None  # None for the fallback epic
    tables: list[SourceTable]
    id: str = ""
    name: str = ""
    tasks: int = 0


def parse_options(args, project: Project) -> Options:
    options = Options()
    core_by_lower = {name.lower(): name for name in CORE_TASK_COLUMNS}
    for pair in args.column or []:
        key, sep, header = pair.partition("=")
        core = core_by_lower.get(key.strip().lower())
        if not sep or core is None:
            raise UsageError(f"--column expects CORE=HEADER with a core column ({', '.join(CORE_TASK_COLUMNS)}), got `{pair}`")
        if not header.strip() or "|" in header:
            raise UsageError(f"--column {core}= needs a header name without `|`")
        if core in options.columns:
            raise UsageError(f"--column names {core} more than once")
        options.columns[core] = header.strip()
    for pair in args.status or []:
        value, sep, name = pair.rpartition("=")
        if not sep or name.strip().lower() not in STATUS_NAMES:
            raise UsageError(f"--status expects VALUE=pending|done|discarded, got `{pair}`")
        options.statuses[value.strip().lower()] = STATUS_NAMES[name.strip().lower()]
    for pair in args.kind or []:
        value, sep, kind = pair.rpartition("=")
        if not sep:
            raise UsageError(f"--kind expects VALUE=KIND, got `{pair}`")
        options.kinds[value.strip().lower()] = _known_kind(project, kind.strip(), "--kind")
    if args.default_kind is not None:
        options.default_kind = _known_kind(project, args.default_kind.strip(), "--default-kind")
    if args.epic_level is not None:
        if not 2 <= args.epic_level <= 6:
            raise UsageError("--epic-level must be between 2 and 6")
        options.epic_level = args.epic_level
    if args.epic_name is not None:
        if not args.epic_name.strip() or "\n" in args.epic_name or "\r" in args.epic_name:
            raise UsageError("--epic-name must be a non-empty single line")
        options.epic_name = args.epic_name.strip()
    return options


def _known_kind(project: Project, kind: str, flag: str) -> str:
    if kind not in project.kinds:
        known = ", ".join(sorted(project.kinds)) or "none"
        raise UsageError(f"{flag}: `{kind}` is not a kind this repository defines and allows (known: {known})")
    return kind


def _scan(lines: list[str]) -> tuple[list[Heading], list[SourceTable]]:
    """Headings of every level and well-formed pipe tables, outside fenced code."""
    headings: list[Heading] = []
    tables: list[SourceTable] = []
    pending: list[int] = []
    in_fence = False

    def flush() -> None:
        if len(pending) >= 2:
            header = split_row(lines[pending[0]])
            separator = split_row(lines[pending[1]])
            if header is not None and separator is not None and is_separator(separator):
                rows = [(i, split_row(lines[i]) or []) for i in pending[2:]]
                tables.append(SourceTable(index=pending[0], header=header, rows=rows))
        pending.clear()

    for index, raw in enumerate(lines):
        text = raw.rstrip("\r\n")
        if FENCE.match(text):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(text)
        if match:
            flush()
            headings.append(Heading(index, len(match.group(1)), match.group(2)))
            continue
        if text.lstrip().startswith("|"):
            pending.append(index)
            continue
        flush()
    flush()
    return headings, tables


def _insert_cell(line: str, after: int, cell: str) -> str:
    """Insert already-padded cell content after cell `after`, keeping the rest of the line."""
    body = line.rstrip("\r\n")
    ending = line[len(body):]
    _, end = _cell_spans(line)[after]
    if end < len(body) and body[end] == "|":
        return body[: end + 1] + cell + "|" + body[end + 1 :] + ending
    return body[:end].rstrip() + " |" + cell.rstrip() + body[end:] + ending


class Importer:
    def __init__(self, project: Project, backlog: BacklogConfig, options: Options, text: str):
        self.project = project
        self.config: Config = project.config
        self.backlog = backlog
        self.options = options
        self.text = text
        self.newline = "\r\n" if "\r\n" in text else "\n"
        self.lines = text.splitlines(keepends=True)
        self.problems: list[dict] = []
        self.unmapped: dict[tuple[str, str], list[int]] = {}
        self.epics: list[EpicPlan] = []
        self.epic_level = 2
        self.tasks = 0
        self.task_ids: list[str] = []
        self.mapped_columns: dict[str, str] = {}
        self.statuses: dict[str, dict] = {}
        self.kinds: dict[str, dict] = {}
        self.defaulted = 0
        self.custom_columns: list[str] = []
        self.tables_skipped: list[dict] = []

    # -- problems

    def problem(self, code: str, message: str, lines: list[int], **extra) -> None:
        self.problems.append({"code": code, "message": message, "lines": lines, **extra})

    def unmapped_value(self, code: str, value: str, line: int) -> None:
        self.unmapped.setdefault((code, value), []).append(line)

    def _report_unmapped(self) -> None:
        for (code, value), lines in self.unmapped.items():
            count = len(lines)
            if code == "status-unmapped":
                message = f'status `{value}` is not mapped ({count} row(s)); pass --status "{value}=pending|done|discarded"'
            elif code == "kind-unmapped" and not value:
                message = f"the Kind cell is empty ({count} row(s)); pass --default-kind KIND"
            elif code == "kind-unmapped":
                message = f'kind `{value}` is not a kind this repository allows ({count} row(s)); pass --kind "{value}=KIND"'
            else:
                message = f"dependencies `{value}` are not a list of task IDs ({count} row(s)); fix the cell in the source"
            self.problem(code, message, lines, value=value, count=count)

    # -- conversion

    def convert(self) -> str:
        headings, tables = _scan(self.lines)
        task_tables = [t for t in tables if self._resolve(t)]
        if not task_tables:
            self.problem("no-task-table", "no task table found: a task table needs an ID and a status column (map them with --column)", [])
            return self.text
        self._group(headings, task_tables)
        replaced: dict[int, str] = {}
        seen: dict[str, int] = {}
        for epic in self.epics:
            for table in epic.tables:
                epic.tasks += self._convert_table(table, replaced, seen)
        self.tasks = sum(epic.tasks for epic in self.epics)
        self._report_unmapped()
        for epic in self.epics:
            if epic.heading is not None:
                replaced[epic.heading.index] = f"## {epic.id} — {epic.name}" + self._ending(epic.heading.index)
        return self._assemble(headings, replaced)

    def _ending(self, index: int) -> str:
        line = self.lines[index]
        return line[len(line.rstrip("\r\n")):] or self.newline

    def _resolve(self, table: SourceTable) -> bool:
        aliases = self.config.column_aliases
        lookup = {name.lower(): name for name in CORE_TASK_COLUMNS}
        lookup.update({alias.lower(): core for core, alias in aliases.items()})
        lookup.update({header.lower(): core for core, header in self.options.columns.items()})
        duplicates: list[tuple[str, str, str]] = []
        for position, cell in enumerate(table.header):
            core = lookup.get(cell.strip().lower())
            if core is None:
                continue
            if core in table.columns:
                duplicates.append((table.header[table.columns[core]], cell, core))
            else:
                table.columns[core] = position
        if "ID" not in table.columns or "✓" not in table.columns:
            if "ID" in table.columns:
                self.tables_skipped.append({"line": table.index + 1, "reason": NO_STATUS})
            return False
        for first, second, core in duplicates:
            self.problem("column-duplicate", f"columns `{first}` and `{second}` both map to {core}", [table.index + 1])
        return True

    def _group(self, headings: list[Heading], tables: list[SourceTable]) -> None:
        def above(table: SourceTable, top: int) -> Heading | None:
            found = None
            for heading in headings:
                if heading.index >= table.index:
                    break
                if 2 <= heading.level <= top:
                    found = heading
            return found

        if self.options.epic_level is not None:
            self.epic_level = self.options.epic_level
        else:
            nearest = [h.level for h in (above(t, 6) for t in tables) if h is not None]
            self.epic_level = min(nearest, default=2)
        for table in tables:
            owner = above(table, self.epic_level)
            if self.epics and self.epics[-1].heading is owner:
                self.epics[-1].tables.append(table)
            else:
                self.epics.append(EpicPlan(heading=owner, tables=[table]))

        prefix = self.backlog.epic_prefix
        kept_re = re.compile(rf"^{re.escape(prefix)}\d{{2,}}$")
        taken: set[str] = set()
        for epic in self.epics:
            if epic.heading is None:
                epic.name = self.options.epic_name
                continue
            epic.name = epic.heading.text
            match = EPIC_HEADING.match(epic.heading.text)
            if match and kept_re.match(match.group(1)) and match.group(1) not in taken:
                epic.id, epic.name = match.group(1), match.group(2).strip()
                taken.add(epic.id)
        number = 0
        for epic in self.epics:
            if epic.id:
                continue
            while True:
                number += 1
                candidate = f"{prefix}{number:02d}"
                if candidate not in taken:
                    break
            epic.id = candidate
            taken.add(candidate)

    def _convert_table(self, table: SourceTable, replaced: dict[int, str], seen: dict[str, int]) -> int:
        aliases = self.config.column_aliases
        columns = table.columns
        header_line = self.lines[table.index]
        for core, position in sorted(columns.items(), key=lambda item: item[1]):
            source = table.header[position]
            self.mapped_columns.setdefault(source, core)
            name = aliases.get(core, core)
            if source.strip().lower() != name.lower():
                header_line = replace_cell(header_line, position, escape_cell(name))
        mapped_positions = set(columns.values())
        for position, cell in enumerate(table.header):
            if position not in mapped_positions and cell and cell not in self.custom_columns:
                self.custom_columns.append(cell)

        refused = False
        if "Title" not in columns:
            self.problem("title-missing", "task table has no Title column; pass --column Title=HEADER", [table.index + 1])
            refused = True
        insert_kind = "Kind" not in columns
        if insert_kind and self.options.default_kind is None:
            self.problem(
                "kind-missing", "task table has no Kind column; pass --column Kind=HEADER or --default-kind KIND", [table.index + 1]
            )
            refused = True
        insert_depends = "Depends On" not in columns

        count = 0
        status_values = {**BUILTIN_STATUSES, **self.options.statuses}
        kind_names = {kind.lower(): kind for kind in self.project.kinds}
        prefixes = "|".join(re.escape(b.prefix) for b in self.config.backlogs)
        dependency_re = re.compile(rf"^(?:{prefixes})\d+$")
        id_re = re.compile(rf"^{re.escape(self.backlog.prefix)}\d{{{self.backlog.id_digits},}}$")
        loose_id_re = re.compile(rf"^{re.escape(self.backlog.prefix)}(\d+)$")

        for index, cells in table.rows:
            line_number = index + 1
            if len(cells) != len(table.header):
                self.problem("row-cells", f"row has {len(cells)} cells but the header has {len(table.header)}", [line_number])
                continue
            count += 1
            line = self.lines[index]
            changes: list[tuple[int, str]] = []

            task_id = cells[columns["ID"]]
            if not id_re.match(task_id):
                message = (
                    f"task ID `{task_id}` does not match `{self.backlog.prefix}` plus {self.backlog.id_digits} or more digits"
                )
                loose = loose_id_re.match(task_id)
                if loose:
                    message += f"; IDs are kept as written, so set id_digits = {len(loose.group(1))} for backlog `{self.backlog.name}`"
                self.problem("id-format", message, [line_number])
            elif task_id in seen:
                self.problem("id-duplicate", f"task ID `{task_id}` appears more than once", [seen[task_id], line_number])
            else:
                seen[task_id] = line_number
                self.task_ids.append(task_id)

            raw_status = cells[columns["✓"]]
            status = status_values.get(raw_status.lower())
            if status is None:
                self.unmapped_value("status-unmapped", raw_status, line_number)
            else:
                entry = self.statuses.setdefault(raw_status, {"status": status.label, "count": 0})
                entry["count"] += 1
                if raw_status != status.value:
                    changes.append((columns["✓"], status.value))

            if not insert_kind:
                raw_kind = cells[columns["Kind"]]
                kind = self.options.kinds.get(raw_kind.lower()) or kind_names.get(raw_kind.lower())
                if kind is None and not raw_kind and self.options.default_kind:
                    kind = self.options.default_kind
                    self.defaulted += 1
                elif kind is not None:
                    entry = self.kinds.setdefault(raw_kind, {"kind": kind, "count": 0})
                    entry["count"] += 1
                if kind is None:
                    self.unmapped_value("kind-unmapped", raw_kind, line_number)
                elif kind != raw_kind:
                    changes.append((columns["Kind"], kind))
            elif self.options.default_kind:
                self.defaulted += 1

            if not insert_depends:
                raw_depends = cells[columns["Depends On"]]
                if raw_depends in EMPTY_DEPENDENCIES:
                    normalised = "—"
                else:
                    tokens = [token for token in re.split(r"[\s,;]+", raw_depends) if token]
                    normalised = ", ".join(tokens) if all(dependency_re.match(t) for t in tokens) else None
                if normalised is None:
                    self.unmapped_value("depends-unmapped", raw_depends, line_number)
                elif normalised != raw_depends:
                    changes.append((columns["Depends On"], normalised))

            if "Title" in columns and not cells[columns["Title"]]:
                self.problem("title-empty", f"task `{task_id}` has no title", [line_number])

            for position, value in changes:
                line = replace_cell(line, position, value)
            replaced[index] = line
        if refused:
            return count

        # Kind goes after ID, and Depends On after Kind, as in taskrail's default column order.
        inserts: list[tuple[int, str, str]] = []
        kind_position = columns["ID"] + 1 if insert_kind else columns["Kind"]
        if insert_kind:
            inserts.append((columns["ID"], aliases.get("Kind", "Kind"), self.options.default_kind or ""))
        if insert_depends:
            inserts.append((kind_position, aliases.get("Depends On", "Depends On"), "—"))
        separator_line = self.lines[table.index + 1]
        for after, name, value in inserts:
            width = max(display_width(name), display_width(value))
            header_line = _insert_cell(header_line, after, f" {_pad(name, width)} ")
            separator_line = _insert_cell(separator_line, after, "-" * (width + 2))
            for index, _ in table.rows:
                if index in replaced:
                    replaced[index] = _insert_cell(replaced[index], after, f" {_pad(value, width)} ")
        replaced[table.index + 1] = separator_line
        replaced[table.index] = header_line
        return count

    def _assemble(self, headings: list[Heading], replaced: dict[int, str]) -> str:
        insertions: dict[int, list[str]] = {}
        fallback = next((epic for epic in self.epics if epic.heading is None), None)
        candidates = [h.index for h in headings if h.level == 2]
        candidates += [epic.heading.index for epic in self.epics if epic.heading is not None]
        if fallback is not None:
            candidates.append(fallback.tables[0].index)
        first = min(candidates)
        insertions.setdefault(first, []).extend(self._epics_section())
        if fallback is not None:
            insertions.setdefault(fallback.tables[0].index, []).extend([f"## {fallback.id} — {fallback.name}", ""])

        output: list[str] = []
        for index, line in enumerate(self.lines):
            block = insertions.get(index)
            if block:
                previous = output[-1] if output else ""
                if output and previous.strip():
                    output.append(self.newline)
                output.extend(text + self.newline for text in block)
            output.append(replaced.get(index, line))
        return "".join(output)

    def _epics_section(self) -> list[str]:
        header = ["ID", "Epic", "Objective", "File"]
        rows = [[epic.id, escape_cell(epic.name), "—", "—"] for epic in self.epics]
        widths = [max(display_width(cells[i]) for cells in [header, *rows]) for i in range(len(header))]
        separator = "|" + "|".join("-" * (width + 2) for width in widths) + "|"
        table = [_row(cells, widths).rstrip("\n") for cells in [header]] + [separator]
        table += [_row(cells, widths).rstrip("\n") for cells in rows]
        return ["## Epics", "", *table, ""]


def _replaceable(text: str) -> bool:
    """A target holding nothing but headings and empty tables, like the file `init` seeds."""
    for section in parse_sections(text):
        if any(table.rows for table in section.tables):
            return False
        for _, raw in section.lines:
            if raw.strip() and not HEADING.match(raw):
                return False
    return True


@contextmanager
def _id_lock(config: Config):
    """The ID lock when the repository is a git clone; outside git no reservation can exist."""
    try:
        gitutil.common_dir(config.root)
    except gitutil.GitError:
        yield False
        return
    with ids.id_lock(config):
        yield True


def _display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root.resolve()))
    except ValueError:
        return str(path)


def cmd_import(args) -> int:
    root = Path(args.root).resolve() if args.root else find_root(Path.cwd())
    config = load_config(root)
    project, _ = load_project(config)
    try:
        backlog = _backlog(config, args.backlog)
        options = parse_options(args, project)
        source_path = Path(args.source).resolve()
        try:
            text = source_path.read_bytes().decode("utf-8")
        except FileNotFoundError:
            raise UsageError(f"{args.source} does not exist")
        except (OSError, UnicodeDecodeError) as exc:
            raise UsageError(f"cannot read {args.source}: {exc}")
    except UsageError as exc:
        print(f"taskrail: {exc}", file=sys.stderr)
        return EXIT_USAGE

    target_path = (config.root / backlog.file).resolve()
    same_file = target_path == source_path
    importer = Importer(project, backlog, options, text)
    already = any(s.title and s.title.strip().lower() == EPICS_TITLE for s in parse_sections(text))
    content = text if already else importer.convert()

    issues = []
    if not importer.problems:  # a refused conversion is half-done: validating it only adds noise
        _, issues = load_project(config, overlay={backlog.file: content})
        issues = [issue for issue in issues if issue.file == backlog.file]
    errors = [issue for issue in issues if issue.severity == "error"]
    if already and errors:
        importer.problem("epics-invalid", "the source already has an `## Epics` section but does not validate; fix it by hand", [])

    current = target_path.read_bytes().decode("utf-8", errors="replace") if target_path.is_file() else None
    unchanged = current == content
    result = {
        "source": _display(source_path, config.root),
        "target": backlog.file,
        "backlog": backlog.name,
        "written": False,
        "unchanged": unchanged,
        "already_imported": already,
        "epic_level": None if already else importer.epic_level,
        "epics": [
            {"id": e.id, "name": e.name, "line": (e.heading.index if e.heading else e.tables[0].index) + 1, "tasks": e.tasks}
            for e in importer.epics
        ],
        "tasks": importer.tasks,
        "mapped": {
            "columns": importer.mapped_columns,
            "statuses": importer.statuses,
            "kinds": importer.kinds,
            "default_kind": {"kind": options.default_kind, "count": importer.defaulted} if importer.defaulted else None,
        },
        "custom_columns": importer.custom_columns,
        "tables_skipped": importer.tables_skipped,
        "problems": importer.problems,
        "issues": [issue.to_dict() for issue in issues],
        "content": content,
    }

    if importer.problems:
        return _finish(args, result, EXIT_REFUSED)
    if errors:
        return _finish(args, result, EXIT_INVALID)
    if args.write and not unchanged:
        if not same_file and current is not None and not _replaceable(current):
            importer.problem(
                "target-not-empty",
                f"{backlog.file} already holds a backlog; import into an empty backlog file or convert it in place",
                [],
            )
            return _finish(args, result, EXIT_REFUSED)
        try:
            with _id_lock(config) as locked:
                if locked:
                    used = ids.used_ids(config, backlog)
                    wanted = set(importer.task_ids)
                    conflicts = [r for r in ids.reservations(config, backlog) if r["id"] in wanted and r["id"] not in used]
                    if conflicts:
                        for reservation in conflicts:
                            importer.problem(
                                "id-reserved",
                                f"task ID `{reservation['id']}` is reserved by {reservation.get('owner', 'someone')}; "
                                f"cancel it with `taskrail unreserve-id {reservation['id']}` if it will not be used",
                                [],
                            )
                        return _finish(args, result, EXIT_CONFLICT)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = target_path.with_name(f".{target_path.name}.taskrail-tmp")
                temporary.write_bytes(content.encode("utf-8"))
                os.replace(temporary, target_path)
        except ids.LockTimeout as exc:
            print(f"taskrail: {exc}", file=sys.stderr)
            return EXIT_CONFLICT
        result["written"] = True
    return _finish(args, result, EXIT_OK)


def _backlog(config: Config, name: str | None) -> BacklogConfig:
    if name is None:
        if len(config.backlogs) == 1:
            return config.backlogs[0]
        raise UsageError("several backlogs are configured; pass --backlog")
    backlog = config.backlog(name)
    if backlog is None:
        raise UsageError(f"no backlog `{name}`")
    return backlog


def _finish(args, result: dict, code: int) -> int:
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    source = result["source"]
    for problem in result["problems"]:
        where = f"{source}:{problem['lines'][0]}: " if problem["lines"] else f"{source}: "
        more = f" (lines {', '.join(map(str, problem['lines']))})" if len(problem["lines"]) > 1 else ""
        print(f"{where}{problem['message']}{more} [{problem['code']}]", file=sys.stderr)
    for issue in result["issues"]:
        where = f"{issue['file']}:{issue['line']}: " if issue["line"] else f"{issue['file']}: "
        print(f"{where}{issue['severity']}: {issue['message']} [{issue['code']}]", file=sys.stderr)
    if code == EXIT_INVALID:
        print("taskrail: the imported backlog would not validate; nothing was written", file=sys.stderr)
    if code == EXIT_REFUSED:
        print("taskrail: nothing was imported", file=sys.stderr)
    if code != EXIT_OK:
        return code
    print(_summary(args, result), file=sys.stderr)
    if result["written"]:
        print(f"wrote {result['target']}")
    elif result["unchanged"]:
        print(f"unchanged {result['target']}")
    elif not args.write:
        sys.stdout.write(result["content"])
    return code


def _summary(args, result: dict) -> str:
    if result["unchanged"]:
        state = "already up to date"
    elif result["written"]:
        state = "written"
    else:
        state = "dry run: add --write to write it"
    lines = [f"import {result['source']} -> {result['target']} ({state})"]
    if result["already_imported"]:
        lines.append("the source already is a taskrail backlog")
        return "\n".join(lines)
    lines.append(f"{result['tasks']} task(s) in {len(result['epics'])} epic(s), epic level {result['epic_level']}")
    for epic in result["epics"]:
        lines.append(f"  {epic['id']} {epic['name']} (line {epic['line']}): {epic['tasks']} task(s)")
    mapped = result["mapped"]
    if mapped["columns"]:
        lines.append("columns: " + ", ".join(f"{header} -> {core}" for header, core in mapped["columns"].items()))
    if mapped["statuses"]:
        lines.append("statuses: " + ", ".join(f"{v} -> {m['status']} ({m['count']})" for v, m in mapped["statuses"].items()))
    if mapped["kinds"]:
        lines.append("kinds: " + ", ".join(f"{v} -> {m['kind']} ({m['count']})" for v, m in mapped["kinds"].items()))
    if mapped["default_kind"]:
        lines.append(f"default kind: {mapped['default_kind']['kind']} ({mapped['default_kind']['count']})")
    if result["custom_columns"]:
        lines.append(f"custom columns: {', '.join(result['custom_columns'])} (declare them in [columns].custom)")
    for skipped in result["tables_skipped"]:
        lines.append(f"left as it is: the table at line {skipped['line']} ({skipped['reason']})")
    return "\n".join(lines)


def register(commands) -> None:
    """Add the `import` command to the top-level subparsers."""
    help_text = "Convert a table-based Markdown backlog without epics into this backlog (dry run unless --write)."
    parser = commands.add_parser("import", help=help_text, description=help_text)
    parser.add_argument("source", help="the Markdown file to convert; may be the backlog file itself")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--write", action="store_true", help="write the result to the backlog's file")
    parser.add_argument("--backlog", help="needed when several backlogs are configured")
    parser.add_argument("--column", action="append", metavar="CORE=HEADER", help="the source header of a core column; repeatable")
    parser.add_argument("--status", action="append", metavar="VALUE=STATUS", help="map a status value to pending, done or discarded; repeatable")
    parser.add_argument("--kind", action="append", metavar="VALUE=KIND", help="map a kind value to a kind; repeatable")
    parser.add_argument("--default-kind", metavar="KIND", help="the kind of rows without a Kind column or with an empty Kind cell")
    parser.add_argument("--epic-level", type=int, metavar="N", help="heading level (2-6) whose headings become epics")
    parser.add_argument("--epic-name", metavar="NAME", help="name of the epic for tables under no heading (default: Backlog)")
    parser.set_defaults(handler=cmd_import)
