"""A git merge driver for backlog tables and bullet lists (DESIGN.md §7.4).

Pipe tables present on both sides are merged row by row, keyed by their `ID` column (or their first
column), and bullet lists item by item, keyed by their text; the merged rows and bullets are then
placed identically into all three inputs, so `git merge-file` treats them as context and merges
everything else — prose, headings, other tables — as git would.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from taskrail import gitutil
from taskrail.backlog import EPIC_HEADING, _index
from taskrail.markdown import FENCE, parse_sections
from taskrail.review import REOPENS
from taskrail.writer import _cell_spans, replace_cell

DONE, PENDING = "✅", "⬜"
ATTRIBUTE = "merge=taskrail"
ATTRIBUTES_FILE = ".gitattributes"
ATTRIBUTES_BEGIN = "# >>> taskrail >>>"
ATTRIBUTES_END = "# <<< taskrail <<<"
CONFIG_LABEL = "git config merge.taskrail"
DRIVER_NAME = "taskrail backlog tables"
# Git runs this through the shell from the top of the worktree. The tail runs only when taskrail
# could not start at all (exit 2 or above), so the file still gets an ordinary merge with markers.
DRIVER_COMMAND = (
    ".taskrail/bin/taskrail merge-driver %O %A %B --marker-size %L --path %P "
    "--base-label %S --current-label %X --other-label %Y; "
    "rc=$?; [ $rc -le 1 ] && exit $rc; git merge-file --marker-size %L -L %X -L %S -L %Y %A %O %B"
)

# `reopened(task_id)` answers which sides ("current", "other") have a `Reopens: <ID>` commit the
# other side lacks, or None when the sides are unknown.
Reopened = Callable[[str], "set[str] | None"]


class MergeFileError(Exception):
    """`git merge-file` failed rather than reporting conflicts."""


# --- merging ---------------------------------------------------------------------------------------


@dataclass
class _Row:
    line: str
    cells: list[str]


@dataclass
class _Table:
    start: int  # 0-based index of the first row line (after the separator)
    end: int  # exclusive
    header: list[str]
    rows: list[_Row]


def _tables(text: str, lines: list[str]) -> dict[tuple, _Table]:
    """Tables by identity: the section (an epic ID, a heading, or None) and their position in it."""
    found: dict[tuple, _Table] = {}
    ambiguous: set[tuple] = set()
    for section in parse_sections(text):
        if section.title is None:
            section_key: tuple | None = None
        else:
            match = EPIC_HEADING.match(section.title)
            section_key = ("epic", match.group(1)) if match else ("heading", section.title)
        for position, table in enumerate(section.tables):
            identity = (section_key, position)
            start = table.line + 1
            rows = [_Row(lines[number - 1], cells) for number, cells in table.rows]
            if identity in found:
                ambiguous.add(identity)
            found[identity] = _Table(start, start + len(rows), table.header, rows)
    for identity in ambiguous:
        del found[identity]
    return found


def _normal(header: list[str]) -> list[str]:
    return [cell.strip().lower() for cell in header]


def _keyed(table: _Table, key: int) -> dict[str, _Row] | None:
    rows: dict[str, _Row] = {}
    for row in table.rows:
        if len(row.cells) != len(table.header):
            return None
        value = row.cells[key]
        if not value or value in rows:
            return None
        rows[value] = row
    return rows


def _order(base: dict, current: dict, other: dict) -> list[str]:
    """The current side's keys, each key only the other side has placed after its predecessor there."""
    order = list(current)
    new_on_current = {key for key in current if key not in base and key not in other}
    previous = None
    for key in other:
        if key in current:
            previous = key
            continue
        position = 0 if previous is None else order.index(previous) + 1
        while position < len(order) and order[position] in new_on_current:
            position += 1
        order.insert(position, key)
        previous = key
    return order


def _status(key: str, current: str, other: str, reopened: Reopened | None) -> str | None:
    """Which side's status wins when both changed it differently: "c", "o", or None if unresolved."""
    if DONE not in (current, other):
        return None
    done = "c" if current == DONE else "o"
    rest = other if done == "c" else current
    if rest != PENDING:
        return done
    sides = reopened(key) if reopened is not None else None
    if sides is None:
        return None
    done_side, pending_side = ("current", "other") if done == "c" else ("other", "current")
    if pending_side in sides and done_side not in sides:
        return "o" if done == "c" else "c"
    return done


def _merge_row(key: str, base: _Row | None, current: _Row, other: _Row, status: int | None, reopened) -> str | None:
    if current.cells == other.cells:
        return current.line
    from_other: list[int] = []
    for index, (mine, theirs) in enumerate(zip(current.cells, other.cells)):
        if mine == theirs:
            continue
        original = base.cells[index] if base is not None else None
        if base is not None and mine == original:
            from_other.append(index)
        elif base is not None and theirs == original:
            continue
        elif index == status and (side := _status(key, mine, theirs, reopened)) is not None:
            if side == "o":
                from_other.append(index)
        else:
            return None
    differing = [i for i, (mine, theirs) in enumerate(zip(current.cells, other.cells)) if mine != theirs]
    if not from_other:
        return current.line
    if from_other == differing:
        return other.line
    line = current.line
    spans = _cell_spans(other.line)
    for index in from_other:
        start, end = spans[index]
        line = replace_cell(line, index, other.line[start:end].strip())
    return line


def _merge_rows(base: dict, current: dict, other: dict, status: int | None, reopened) -> list[tuple]:
    """(base, current, other) line per merged position; a resolved row carries one line three times."""
    entries: list[tuple] = []
    for key in _order(base, current, other):
        original, mine, theirs = base.get(key), current.get(key), other.get(key)
        if mine is not None and theirs is not None:
            line = _merge_row(key, original, mine, theirs, status, reopened)
            if line is not None:
                entries.append((line, line, line))
            else:
                entries.append((original.line if original else None, mine.line, theirs.line))
        else:
            kept = mine or theirs
            if original is None:
                entries.append((kept.line, kept.line, kept.line))
            elif kept.cells != original.cells:
                entries.append((original.line, mine.line if mine else None, theirs.line if theirs else None))
            # else: removed by the other side
    return entries


def _eol(line: str) -> str:
    return line[len(line.rstrip("\r\n")) :]


def _region(entries: list[tuple], version: int, lines: list[str], table: _Table) -> list[str]:
    chosen = [entry[version] for entry in entries if entry[version] is not None]
    default = next((_eol(row.line) for row in table.rows if _eol(row.line)), None) or _eol(lines[table.start - 1]) or "\n"
    region = [line if _eol(line) else line + default for line in chosen]
    at_end = table.end == len(lines) and not _eol(lines[-1])
    if at_end and region:
        region[-1] = region[-1].rstrip("\r\n")
    return region


def merge_tables(
    base: str,
    current: str,
    other: str,
    aliases: Mapping[str, str] | None = None,
    reopened: Reopened | None = None,
) -> tuple[str, str, str]:
    """The three inputs with every table mergeable row by row replaced by its merged rows."""
    texts = (base, current, other)
    lines = [text.splitlines(keepends=True) for text in texts]
    tables = [_tables(text, version_lines) for text, version_lines in zip(texts, lines)]
    replacements: list[list[tuple[int, int, list[str]]]] = [[], [], []]
    for identity, mine in tables[1].items():
        theirs = tables[2].get(identity)
        if theirs is None or _normal(theirs.header) != _normal(mine.header):
            continue
        columns = _index(mine.header, aliases)
        key = columns.get("ID", 0)
        status = columns.get("✓") if "ID" in columns else None
        original = tables[0].get(identity)
        if original is not None and _normal(original.header) != _normal(mine.header):
            continue
        keyed = [_keyed(table, key) if table is not None else {} for table in (original, mine, theirs)]
        if any(rows is None for rows in keyed):
            continue
        present = [(version, table) for version, table in enumerate((original, mine, theirs)) if table is not None]
        # A table with no rows whose separator ends the file without a newline has nowhere to put rows.
        if any(not table.rows and not _eol(lines[version][table.start - 1]) for version, table in present):
            continue
        entries = _merge_rows(*keyed, status, reopened)
        for version, table in present:
            replacements[version].append((table.start, table.end, _region(entries, version, lines[version], table)))
    results = []
    for version_lines, version_replacements in zip(lines, replacements):
        for start, end, region in sorted(version_replacements, reverse=True):
            version_lines[start:end] = region
        results.append("".join(version_lines))
    return results[0], results[1], results[2]


# --- bullet lists ----------------------------------------------------------------------------------

HEADING = re.compile(r"^(#{1,6})[ \t]+(\S.*?)(?:[ \t]+#+)?[ \t]*$")
BULLET = re.compile(r"^[-*+][ \t]+\S")
THEMATIC_BREAK = re.compile(r"^([-*_])([ \t]*\1){2,}[ \t]*$")


@dataclass
class _Bullet:
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(self.lines)

    @property
    def key(self) -> str:
        return _key(self.text)


@dataclass
class _List:
    start: int  # 0-based index of the first bullet line
    end: int  # exclusive
    bullets: list[_Bullet]


def _key(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def _lists(lines: list[str]) -> tuple[dict[tuple, list[_List]], set[tuple]]:
    """Tight bullet lists outside fenced code by heading path, and the paths whose lists cannot be read.

    Every heading path seen is a key, so a path with no lists maps to an empty list.
    """
    found: dict[tuple, list[_List]] = {(): []}
    unreadable: set[tuple] = set()
    path: tuple = ()
    in_fence = False
    open_list: _List | None = None
    for index, line in enumerate(lines):
        raw = line.rstrip("\r\n")
        if FENCE.match(raw):
            if open_list is not None and raw[:1] in (" ", "\t"):
                unreadable.add(path)  # a fence inside a bullet: its extent is not a plain line run
            open_list = None
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if open_list is not None and raw.strip() and raw[0] in (" ", "\t"):
            open_list.bullets[-1].lines.append(line)
            open_list.end = index + 1
            continue
        if BULLET.match(raw) and not THEMATIC_BREAK.match(raw):
            if open_list is None:
                open_list = _List(index, index, [])
                found[path].append(open_list)
            open_list.bullets.append(_Bullet([line]))
            open_list.end = index + 1
            continue
        open_list = None
        heading = HEADING.match(raw)
        if heading:
            level = len(heading.group(1))
            path = tuple(entry for entry in path if entry[0] < level) + ((level, heading.group(2)),)
            found.setdefault(path, [])
    return found, unreadable


def _edits(base: list[str], side: list[str]) -> dict[str, str] | None:
    """A side's edited bullets as {side key: base key}, or None when a replaced block cannot be paired."""
    base_keys, side_keys = set(base), set(side)
    pairs: dict[str, str] = {}
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, base, side, autojunk=False).get_opcodes():
        if tag != "replace":
            continue
        removed = [key for key in base[i1:i2] if key not in side_keys]
        added = [key for key in side[j1:j2] if key not in base_keys]
        if removed and added:
            if len(removed) != len(added):
                return None
            pairs.update(zip(added, removed))
    return pairs


def _moved(base: list[str], side: list[str], common: set[str]) -> set[str]:
    """Bullets present everywhere that a side placed out of the base's order."""
    original = [key for key in base if key in common]
    placed = [key for key in side if key in common]
    kept: set[str] = set()
    for block in SequenceMatcher(None, original, placed, autojunk=False).get_matching_blocks():
        kept.update(original[block.a : block.a + block.size])
    return common - kept


def _merge_bullets(base: list[_Bullet], current: list[_Bullet], other: list[_Bullet]) -> list[tuple] | None:
    """(base, current, other) text per merged position, or None when the list is left to git."""
    keys = [[bullet.key for bullet in bullets] for bullets in (base, current, other)]
    if any(len(set(version)) != len(version) for version in keys):
        return None
    texts = [{bullet.key: bullet.text for bullet in bullets} for bullets in (base, current, other)]
    identities = [keys[0]]
    by_identity: list[dict[str, str]] = [texts[0]]
    for version in (1, 2):
        pairs = _edits(keys[0], keys[version])
        if pairs is None:
            return None
        identities.append([pairs.get(key, key) for key in keys[version]])
        by_identity.append({pairs.get(key, key): text for key, text in texts[version].items()})

    entries: dict[str, tuple] = {}
    for identity in dict.fromkeys(identities[0] + identities[1] + identities[2]):
        original, mine, theirs = (texts.get(identity) for texts in by_identity)
        if mine is not None and theirs is not None:
            if _key(mine) == _key(theirs):
                entries[identity] = (mine, mine, mine)
            elif original is not None and _key(mine) == _key(original):
                entries[identity] = (theirs, theirs, theirs)
            elif original is not None and _key(theirs) == _key(original):
                entries[identity] = (mine, mine, mine)
            else:
                entries[identity] = (original, mine, theirs)
        elif mine is not None or theirs is not None:
            kept = mine if mine is not None else theirs
            if original is None:
                entries[identity] = (kept, kept, kept)
            elif _key(kept) != _key(original):
                entries[identity] = (original, mine, theirs)
            # else: removed by the other side
        # else: removed by both sides

    common = set(identities[0]) & set(identities[1]) & set(identities[2])
    moved_current = _moved(identities[0], identities[1], common)
    moved_other = _moved(identities[0], identities[2], common) - moved_current
    new_on_current = {key for key in identities[1] if key not in identities[0] and key not in identities[2]}
    order = [key for key in identities[1] if key in entries and key not in moved_other]
    previous = None
    for key in identities[2]:
        if key not in entries:
            continue
        if key in order:
            previous = key
            continue
        position = 0 if previous is None else order.index(previous) + 1
        while position < len(order) and order[position] in new_on_current:
            position += 1
        order.insert(position, key)
        previous = key

    merged = [entries[key] for key in order]
    for version in range(3):
        present = [_key(entry[version]) for entry in merged if entry[version] is not None]
        if len(set(present)) != len(present):
            return None  # the same text twice: never duplicate a bullet
    return merged


def _list_region(entries: list[tuple], version: int, lines: list[str], found: _List) -> list[str]:
    default = next((_eol(line) for bullet in found.bullets for line in bullet.lines if _eol(line)), None) or "\n"
    region = [text if _eol(text) else text + default for text in (entry[version] for entry in entries) if text is not None]
    if region and found.end == len(lines) and not _eol(lines[-1]):
        region[-1] = region[-1].rstrip("\r\n")
    return region


def merge_lists(base: str, current: str, other: str) -> tuple[str, str, str]:
    """The three inputs with every bullet list mergeable item by item replaced by its merged bullets."""
    texts = (base, current, other)
    lines = [text.splitlines(keepends=True) for text in texts]
    scanned = [_lists(version_lines) for version_lines in lines]
    replacements: list[list[tuple[int, int, list[str]]]] = [[], [], []]
    for path, mine in scanned[1][0].items():
        theirs = scanned[2][0].get(path)
        if theirs is None or len(theirs) != len(mine) or any(path in unreadable for _, unreadable in scanned):
            continue
        original = scanned[0][0].get(path) or []
        if original and len(original) != len(mine):
            continue
        for position, (my_list, their_list) in enumerate(zip(mine, theirs)):
            base_list = original[position] if original else None
            entries = _merge_bullets(base_list.bullets if base_list else [], my_list.bullets, their_list.bullets)
            if entries is None:
                continue
            for version, found in enumerate((base_list, my_list, their_list)):
                if found is not None:
                    replacements[version].append((found.start, found.end, _list_region(entries, version, lines[version], found)))
    results = []
    for version_lines, version_replacements in zip(lines, replacements):
        for start, end, region in sorted(version_replacements, reverse=True):
            version_lines[start:end] = region
        results.append("".join(version_lines))
    return results[0], results[1], results[2]


def _merge_file(base: str, current: str, other: str, labels: tuple[str, str, str], marker_size: int) -> tuple[str, bool]:
    with tempfile.TemporaryDirectory(prefix="taskrail-merge-") as directory:
        paths = {}
        for name, text in (("base", base), ("current", current), ("other", other)):
            paths[name] = Path(directory) / name
            paths[name].write_bytes(text.encode("utf-8"))
        result = subprocess.run(
            ["git", "merge-file", "-p", f"--marker-size={marker_size}",
             "-L", labels[0], "-L", labels[1], "-L", labels[2],
             str(paths["current"]), str(paths["base"]), str(paths["other"])],
            capture_output=True,
        )
    if result.returncode < 0 or result.returncode >= 128:
        raise MergeFileError(result.stderr.decode(errors="replace").strip() or f"exit {result.returncode}")
    return result.stdout.decode("utf-8"), result.returncode > 0


def merge_text(
    base: str,
    current: str,
    other: str,
    labels: tuple[str, str, str] = ("current", "base", "other"),
    marker_size: int = 7,
    aliases: Mapping[str, str] | None = None,
    reopened: Reopened | None = None,
) -> tuple[str, bool]:
    """Merge three versions of a file; returns the result and whether conflicts are left.

    `labels` are the current, base and other labels of the conflict markers, in `git merge-file` order.
    """
    merged = merge_tables(base, current, other, aliases=aliases, reopened=reopened)
    merged = merge_lists(*merged)
    return _merge_file(*merged, labels, marker_size)


# --- the sides of the merge ------------------------------------------------------------------------


def reopen_sides(root: Path, current: str, other: str) -> dict[str, set[str]]:
    """Task IDs with a `Reopens:` commit on one side that has no patch-equivalent on the other."""
    log = gitutil.run(
        root, "log", "--left-right", "--cherry-pick", "--format=%m%x00%B%x01", "--grep=^Reopens:", f"{current}...{other}"
    ).stdout
    found: dict[str, set[str]] = {}
    for record in log.split("\x01"):
        mark, _, body = record.strip("\n").partition("\x00")
        side = {"<": "current", ">": "other"}.get(mark)
        if side is None:
            continue
        for task_id in REOPENS.findall(body):
            found.setdefault(task_id, set()).add(side)
    return found


def _commit(root: Path, label: str | None) -> str | None:
    words = (label or "").split()
    if not words:
        return None
    result = gitutil.run(root, "rev-parse", "--verify", "--quiet", f"{words[0]}^{{commit}}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _reopen_lookup(root: Path, current_label: str | None, other_label: str | None) -> Reopened:
    state: dict[str, dict | None] = {}

    def lookup(task_id: str) -> set[str] | None:
        if "sides" not in state:
            try:
                current, other = _commit(root, current_label), _commit(root, other_label)
                state["sides"] = reopen_sides(root, current, other) if current and other else None
            except gitutil.GitError:
                state["sides"] = None
        sides = state["sides"]
        return None if sides is None else sides.get(task_id, set())

    return lookup


def _aliases(root: Path) -> Mapping[str, str] | None:
    from taskrail.config import find_root, load_config

    try:
        return load_config(find_root(root)).column_aliases
    except Exception:
        return None


# --- the command -----------------------------------------------------------------------------------


def _plain_merge(args, labels: tuple[str, str, str], marker_size: int) -> int:
    result = subprocess.run(
        ["git", "merge-file", f"--marker-size={marker_size}", "-L", labels[0], "-L", labels[1], "-L", labels[2],
         args.current, args.base, args.other],
        capture_output=True,
    )
    return 1 if result.returncode < 0 or result.returncode >= 1 else 0


def cmd_merge_driver(args) -> int:
    labels = (args.current_label or "current", args.base_label or "base", args.other_label or "other")
    try:
        marker_size = int(args.marker_size)
    except ValueError:
        marker_size = 7
    path = args.path or args.current
    try:
        data = [Path(name).read_bytes() for name in (args.base, args.current, args.other)]
        texts = [chunk.decode("utf-8") for chunk in data]
        root = Path.cwd()
        merged, conflicted = merge_text(
            *texts,
            labels=labels,
            marker_size=marker_size,
            aliases=_aliases(root),
            reopened=_reopen_lookup(root, args.current_label, args.other_label),
        )
    except Exception as exc:  # any failure: behave exactly like git's own text merge
        print(f"taskrail merge-driver: {path}: {exc}; merged as plain text", file=sys.stderr)
        return _plain_merge(args, labels, marker_size)
    Path(args.current).write_bytes(merged.encode("utf-8"))
    return 1 if conflicted else 0


def register(commands) -> None:
    """Add the `merge-driver` command to the top-level subparsers."""
    help_text = "Merge three versions of a backlog file for git, uniting table rows by ID (a git merge driver)."
    parser = commands.add_parser("merge-driver", help=help_text, description=help_text)
    parser.add_argument("base", help="the common ancestor's version (%%O)")
    parser.add_argument("current", help="the current version, overwritten with the result (%%A)")
    parser.add_argument("other", help="the other side's version (%%B)")
    parser.add_argument("--marker-size", default="7", help="conflict marker length (%%L)")
    parser.add_argument("--path", help="the path being merged, for messages (%%P)")
    parser.add_argument("--base-label", help="label of the base in conflict markers (%%S)")
    parser.add_argument("--current-label", help="label of the current side (%%X); its first word names a commit")
    parser.add_argument("--other-label", help="label of the other side (%%Y); its first word names a commit")
    parser.set_defaults(handler=cmd_merge_driver)


# --- installing ------------------------------------------------------------------------------------


def attribute_line(path: str) -> str:
    """A `.gitattributes` line that matches exactly `path`, relative to the repository root."""
    pattern = "/" + re.sub(r"([*?\[\\])", r"\\\1", path.lstrip("/"))
    if re.search(r'[\s"]', pattern):
        pattern = '"' + pattern.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return f"{pattern} {ATTRIBUTE}"


def attribute_paths(config) -> list[str]:
    """Backlog files, epic files, artifact indexes and changelogs the driver applies to."""
    from taskrail.project import load_project

    project, _ = load_project(config)
    return sorted(known_conflict_paths(project))


def known_conflict_paths(project) -> dict[str, str]:
    """The driver's paths, each with its known conflict class (§12.8): `backlog`, `index` or `changelog`."""
    from taskrail.kinds import PLACEHOLDER_RE

    config = project.config
    classes: dict[str, str] = {}

    def add(path: str, kind: str) -> None:
        normal = Path(path).as_posix().removeprefix("./") if path else ""
        if normal and normal != "." and not normal.startswith("../"):
            classes.setdefault(normal, kind)  # the first class wins: backlog, then index, then changelog

    templates = [kind.artifact_index for kind in project.kinds.values()] + [config.autopilot.decisions_index]
    for backlog in project.backlogs:
        add(backlog.config.file, "backlog")
        for epic in backlog.epics:
            if epic.file:
                add(epic.file, "backlog")
    for backlog in project.backlogs:
        for template in filter(None, templates):
            placeholders = set(PLACEHOLDER_RE.findall(template))
            if placeholders - {"artifacts", "backlog", "epic"}:
                continue  # a per-task index cannot be listed
            epics = [epic.id for epic in backlog.epics] if "epic" in placeholders else [""]
            for epic_id in epics:
                add(template.format(artifacts=backlog.config.artifacts, backlog=backlog.config.name, epic=epic_id), "index")
    for path in changelog_paths(config.root, config.worktree_dir):
        add(path, "changelog")
    return classes


def changelog_paths(root: Path, worktree_dir: str = "") -> list[str]:
    """Files named CHANGELOG.md in any letter case that git tracks or would track, outside the worktrees."""
    try:
        listed = gitutil.run(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", check=False)
    except gitutil.GitError:
        return []
    if listed.returncode != 0:
        return []
    skip = Path(worktree_dir).as_posix().strip("/") + "/" if worktree_dir.strip("./") else None
    found = {
        path for path in listed.stdout.split("\0")
        if path and Path(path).name.lower() == "changelog.md" and not (skip and path.startswith(skip))
    }
    return sorted(found)


def _record(report, bucket: str, label: str) -> None:
    if report is not None:
        getattr(report, bucket).append(label)


def update_attributes(root: Path, paths: list[str], report=None, create: bool = True) -> bool:
    """Write the marked block into `.gitattributes`; without `create`, only refresh an existing block."""
    path = root / ATTRIBUTES_FILE
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = ATTRIBUTES_BEGIN + "\n" + "".join(attribute_line(p) + "\n" for p in paths) + ATTRIBUTES_END + "\n"
    if ATTRIBUTES_BEGIN in existing and ATTRIBUTES_END in existing:
        start = existing.index(ATTRIBUTES_BEGIN)
        end = existing.index(ATTRIBUTES_END) + len(ATTRIBUTES_END)
        end += existing[end:].startswith("\n")
        updated = existing[:start] + block + existing[end:]
    elif not create:
        return False
    else:
        separator = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
        updated = existing + separator + block
    if updated == existing:
        _record(report, "unchanged", ATTRIBUTES_FILE)
        return False
    path.write_text(updated, encoding="utf-8")
    _record(report, "updated" if existing else "created", ATTRIBUTES_FILE)
    return True


def install_git_config(root: Path, report=None, add: bool = True) -> None:
    """Define `merge.taskrail` in this clone's config; without `add`, only keep an existing definition current."""
    try:
        gitutil.common_dir(root)
    except gitutil.GitError:
        if add and report is not None:
            report.notes.append("not a git repository: the merge driver's git config was not written")
        return

    def get(key: str) -> str | None:
        result = gitutil.run(root, "config", "--local", "--get", key, check=False)
        return result.stdout.rstrip("\n") if result.returncode == 0 else None

    driver = get("merge.taskrail.driver")
    if driver is None and not add:
        return
    if driver == DRIVER_COMMAND and get("merge.taskrail.name") == DRIVER_NAME:
        _record(report, "unchanged", CONFIG_LABEL)
        return
    gitutil.run(root, "config", "--local", "merge.taskrail.name", DRIVER_NAME)
    gitutil.run(root, "config", "--local", "merge.taskrail.driver", DRIVER_COMMAND)
    _record(report, "created" if driver is None else "updated", CONFIG_LABEL)


def install(root: Path, config, report, add_config: bool) -> None:
    update_attributes(root, attribute_paths(config), report)
    install_git_config(root, report, add=add_config)


def refresh_attributes(config) -> bool:
    """After an epic file is created or moved: refresh the block if the repository has one."""
    return update_attributes(config.root, attribute_paths(config), create=False)
