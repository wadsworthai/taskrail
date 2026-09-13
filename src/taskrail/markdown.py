"""Minimal Markdown reading: level-2 sections and pipe tables, fenced code skipped."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEPARATOR_CELL = re.compile(r"^:?-+:?$")
H2 = re.compile(r"^##\s+(\S.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def split_row(line: str) -> list[str] | None:
    """Split a pipe-table row into trimmed cells, honouring `\\|` escapes."""
    text = line.strip()
    if not text.startswith("|"):
        return None
    body = text[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in body:
        if escaped:
            current.append(char if char == "|" else "\\" + char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEPARATOR_CELL.match(cell) for cell in cells)


@dataclass
class Table:
    line: int  # 1-based line of the header row
    header: list[str]
    rows: list[tuple[int, list[str]]]  # (1-based line, cells)


@dataclass
class Section:
    title: str | None  # None for text before the first level-2 heading
    line: int
    lines: list[tuple[int, str]] = field(default_factory=list)  # body lines outside fences
    tables: list[Table] = field(default_factory=list)
    malformed_tables: list[int] = field(default_factory=list)


def parse_sections(text: str) -> list[Section]:
    sections = [Section(title=None, line=1)]
    in_fence = False
    pending_table: list[tuple[int, str]] = []

    def flush_table() -> None:
        if not pending_table:
            return
        section = sections[-1]
        header = split_row(pending_table[0][1])
        separator = split_row(pending_table[1][1]) if len(pending_table) > 1 else None
        if header is None or separator is None or not is_separator(separator):
            section.malformed_tables.append(pending_table[0][0])
        else:
            rows = [(number, split_row(raw) or []) for number, raw in pending_table[2:]]
            section.tables.append(Table(line=pending_table[0][0], header=header, rows=rows))
        pending_table.clear()

    for number, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            flush_table()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = H2.match(raw)
        if heading:
            flush_table()
            sections.append(Section(title=heading.group(1), line=number))
            continue
        if raw.lstrip().startswith("|"):
            pending_table.append((number, raw))
            continue
        flush_table()
        sections[-1].lines.append((number, raw))
    flush_table()
    return sections
