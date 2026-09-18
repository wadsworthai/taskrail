"""Reading backlog files into the model, reporting structural problems as issues."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from taskrail.config import BacklogConfig, Config
from taskrail.issues import Issue, error, warning
from taskrail.markdown import Section, Table, parse_sections
from taskrail.model import NONE_MARKERS, Backlog, Epic, Status, Task

EPICS_TITLE = "epics"
EPIC_HEADING = re.compile(r"^([A-Z]{1,4}\d+)\s+[—–-]\s+(\S.*)$")
DONE_WHEN = re.compile(r"^\s*(?:\*\*|__)?done when:?(?:\*\*|__)?:?\s*(.*)$", re.IGNORECASE)

TASK_REQUIRED = ("✓", "ID", "Kind", "Depends On", "Title")
TASK_OPTIONAL = ("Pts", "Description")
EPIC_REQUIRED = ("ID", "Epic")
EPIC_OPTIONAL = ("Objective", "File")


def _index(header: list[str], aliases: Mapping[str, str] | None = None) -> dict[str, int]:
    """Map canonical column names to positions, matching case-insensitively.

    `aliases` (core task column -> header) applies to task tables only: an aliased column is
    found by its alias, and its core name is no longer recognised.
    """
    known = {name.lower(): name for name in (*TASK_REQUIRED, *TASK_OPTIONAL, *EPIC_OPTIONAL, "Epic")}
    for core, alias in (aliases or {}).items():
        known.pop(core.lower(), None)
        known[alias.lower()] = core
    result: dict[str, int] = {}
    for position, cell in enumerate(header):
        result[known.get(cell.strip().lower(), cell.strip())] = position
    return result


def _is_task_table(table: Table, aliases: Mapping[str, str] | None = None) -> bool:
    columns = _index(table.header, aliases)
    return "ID" in columns and ("✓" in columns or "Kind" in columns)


def _read(root: Path, relative: str, issues: list[Issue], overlay: dict[str, str] | None = None) -> list[Section] | None:
    if overlay and relative in overlay:
        return parse_sections(overlay[relative])
    path = root / relative
    try:
        return parse_sections(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        issues.append(error("file-encoding", "file is not valid UTF-8", relative))
        return None


def _epic_sections(sections: list[Section]) -> dict[str, tuple[Section, str]]:
    found: dict[str, tuple[Section, str]] = {}
    for section in sections:
        if section.title is None:
            continue
        match = EPIC_HEADING.match(section.title)
        if match:
            found.setdefault(match.group(1), (section, match.group(2).strip()))
    return found


def _check_stray_tables(
    sections: list[Section], allowed: set[int], file: str, issues: list[Issue], aliases: Mapping[str, str] | None = None
) -> None:
    """Task tables must sit in an epic section; malformed tables are always reported."""
    for index, section in enumerate(sections):
        for line in section.malformed_tables:
            issues.append(error("table-malformed", "table has no header separator row", file, line))
        if index in allowed:
            continue
        for table in section.tables:
            if _is_task_table(table, aliases):
                issues.append(
                    error("task-outside-epic", "task table is not inside an epic section", file, table.line)
                )


def _parse_tasks(
    epic: Epic,
    section: Section,
    file: str,
    config: Config,
    counter: list[int],
    issues: list[Issue],
) -> None:
    for number, raw in section.lines:
        match = DONE_WHEN.match(raw)
        if match and epic.done_when is None:
            epic.done_when = match.group(1).strip() or None

    known_columns = {*TASK_REQUIRED, *TASK_OPTIONAL}
    aliases = config.column_aliases
    aliased_by_lower = {core.lower(): core for core in aliases}
    for table in section.tables:
        if not _is_task_table(table, aliases):
            continue
        replaced = [aliased_by_lower[c.strip().lower()] for c in table.header if c.strip().lower() in aliased_by_lower]
        if replaced:
            expected = ", ".join(f"`{aliases[core]}` instead of `{core}`" for core in replaced)
            issues.append(
                error("column-alias", f"[columns].aliases names column(s) differently: use {expected}", file, table.line)
            )
            continue
        columns = _index(table.header, aliases)
        missing = [f"{aliases[name]} ({name})" if name in aliases else name for name in TASK_REQUIRED if name not in columns]
        if missing:
            issues.append(
                error("task-columns", f"task table is missing column(s): {', '.join(missing)}", file, table.line)
            )
            continue
        for name in columns:
            if name not in known_columns and name not in config.custom_columns:
                issues.append(
                    warning(
                        "column-undeclared",
                        f"column `{name}` is not declared in [columns].custom",
                        file,
                        table.line,
                    )
                )

        for line, cells in table.rows:
            if len(cells) != len(table.header):
                issues.append(
                    error(
                        "row-cells",
                        f"row has {len(cells)} cells but the header has {len(table.header)}",
                        file,
                        line,
                    )
                )
                continue

            def cell(name: str) -> str:
                position = columns.get(name)
                return cells[position] if position is not None else ""

            status_raw = cell("✓")
            status = next((s for s in Status if s.value == status_raw), None)
            points_raw = cell("Pts")
            points = int(points_raw) if points_raw.isdigit() else None
            depends_raw = cell("Depends On")
            depends = (
                []
                if depends_raw in NONE_MARKERS
                else [item.strip() for item in depends_raw.split(",") if item.strip()]
            )
            custom = {name: cells[pos] for name, pos in columns.items() if name not in known_columns}
            counter[0] += 1
            epic.tasks.append(
                Task(
                    id=cell("ID"),
                    status=status,
                    status_raw=status_raw,
                    kind=cell("Kind"),
                    points=points,
                    points_raw=points_raw,
                    depends_on=depends,
                    title=cell("Title"),
                    description=cell("Description"),
                    columns=custom,
                    backlog=epic.backlog,
                    epic=epic.id,
                    file=file,
                    line=line,
                    order=counter[0],
                )
            )


def load_backlog(
    config: Config, backlog_config: BacklogConfig, counter: list[int], overlay: dict[str, str] | None = None
) -> tuple[Backlog, list[Issue]]:
    issues: list[Issue] = []
    backlog = Backlog(config=backlog_config)
    main_file = backlog_config.file
    sections = _read(config.root, main_file, issues, overlay)
    if sections is None:
        if not any(issue.file == main_file for issue in issues):
            issues.append(error("backlog-missing", f"backlog `{backlog_config.name}` file does not exist", main_file))
        return backlog, issues

    listings = [s for s in sections if s.title is not None and s.title.strip().lower() == EPICS_TITLE]
    if not listings:
        issues.append(error("epics-missing", "no `## Epics` section", main_file))
    elif len(listings) > 1:
        issues.append(error("epics-duplicate", "more than one `## Epics` section", main_file, listings[1].line))

    inline = _epic_sections(sections)
    allowed_main = {index for index, s in enumerate(sections) if s.title and EPIC_HEADING.match(s.title)}
    _check_stray_tables(sections, allowed_main, main_file, issues, config.column_aliases)

    epic_id_re = re.compile(rf"^{backlog_config.epic_prefix}\d{{2,}}$")
    listed: set[str] = set()
    listing = listings[0] if listings else None
    listing_table = None
    if listing is not None:
        tables = [t for t in listing.tables if "ID" in _index(t.header)]
        if not tables:
            issues.append(error("epics-table-missing", "`## Epics` section has no epics table", main_file, listing.line))
        else:
            listing_table = tables[0]

    if listing_table is not None:
        columns = _index(listing_table.header)
        missing = [name for name in EPIC_REQUIRED if name not in columns]
        if missing:
            issues.append(
                error("epics-columns", f"epics table is missing column(s): {', '.join(missing)}", main_file, listing_table.line)
            )
        else:
            for line, cells in listing_table.rows:
                if len(cells) != len(listing_table.header):
                    issues.append(
                        error(
                            "row-cells",
                            f"row has {len(cells)} cells but the header has {len(listing_table.header)}",
                            main_file,
                            line,
                        )
                    )
                    continue

                def cell(name: str) -> str:
                    position = columns.get(name)
                    return cells[position] if position is not None else ""

                epic_id = cell("ID")
                if not epic_id_re.match(epic_id):
                    issues.append(
                        error(
                            "epic-id",
                            f"epic ID `{epic_id}` does not match epic_prefix `{backlog_config.epic_prefix}` plus two or more digits",
                            main_file,
                            line,
                        )
                    )
                    continue
                if epic_id in listed:
                    issues.append(error("epic-duplicate", f"epic `{epic_id}` is listed more than once", main_file, line))
                    continue
                listed.add(epic_id)
                file_cell = cell("File")
                epic = Epic(
                    id=epic_id,
                    name=cell("Epic"),
                    objective=cell("Objective"),
                    file=None if file_cell in NONE_MARKERS else file_cell,
                    backlog=backlog_config.name,
                    listing_line=line,
                )
                backlog.epics.append(epic)

    for epic in backlog.epics:
        if epic.file is None:
            if epic.id not in inline:
                issues.append(
                    error("epic-no-section", f"epic `{epic.id}` is listed but has no `## {epic.id} — …` section", main_file, epic.listing_line)
                )
                continue
            section, heading_name = inline[epic.id]
            epic.section_file, epic.section_line = main_file, section.line
        else:
            if epic.id in inline:
                issues.append(
                    error(
                        "epic-both",
                        f"epic `{epic.id}` has a File but is also defined inline",
                        main_file,
                        inline[epic.id][0].line,
                    )
                )
                continue
            epic_sections = _read(config.root, epic.file, issues, overlay)
            if epic_sections is None:
                issues.append(error("epic-file-missing", f"epic `{epic.id}` file `{epic.file}` does not exist", main_file, epic.listing_line))
                continue
            defined = _epic_sections(epic_sections)
            for other_id, (other_section, _) in defined.items():
                if other_id != epic.id:
                    issues.append(
                        error("epic-file-extra", f"file for `{epic.id}` also defines `{other_id}`", epic.file, other_section.line)
                    )
            for section in epic_sections:
                if section.title and section.title.strip().lower() == EPICS_TITLE:
                    issues.append(error("epic-file-listing", "an epic file must not contain `## Epics`", epic.file, section.line))
            if epic.id not in defined:
                issues.append(error("epic-no-section", f"`{epic.file}` has no `## {epic.id} — …` section", epic.file))
                continue
            allowed = {index for index, s in enumerate(epic_sections) if s.title and EPIC_HEADING.match(s.title)}
            _check_stray_tables(epic_sections, allowed, epic.file, issues, config.column_aliases)
            section, heading_name = defined[epic.id]
            epic.section_file, epic.section_line = epic.file, section.line

        if heading_name != epic.name:
            issues.append(
                warning(
                    "epic-name-mismatch",
                    f"heading names epic `{epic.id}` `{heading_name}` but the Epics table says `{epic.name}`",
                    epic.section_file,
                    epic.section_line,
                )
            )
        _parse_tasks(epic, section, epic.section_file, config, counter, issues)

    for epic_id, (section, _) in inline.items():
        if epic_id not in listed:
            issues.append(error("epic-unlisted", f"section `{epic_id}` is not in the Epics table", main_file, section.line))

    return backlog, issues
