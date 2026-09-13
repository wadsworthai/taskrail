"""The column predicate: `column` plus `match`, tested against a task's custom columns.

Conditional stages and `[[route]]` entries use it (DESIGN.md §5.4, §5.5). It depends on nothing
else in taskrail, so any other setting with the same shape — such as the autopilot's groups —
parses and matches it here too.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

NONE_MARKERS = frozenset({"", "—", "-"})  # a cell holding one of these is empty
ANY = "*"  # matches any non-empty cell


@dataclass(frozen=True)
class ColumnPredicate:
    column: str
    match: tuple[str, ...]

    def matches(self, columns: Mapping[str, str]) -> bool:
        """Whether the cell equals any `match` value: trimmed, case-insensitive, with `*` and `—`."""
        wanted = self.column.lower()
        actual = next((value for name, value in columns.items() if name.strip().lower() == wanted), "").strip()
        return any(_value_matches(actual, expected) for expected in self.match)

    def covers(self, other: ColumnPredicate) -> bool:
        """Whether this predicate holds for every cell `other` holds for, on the same column.

        Exact for these values: `*` covers `*` and every literal, an empty marker covers the empty
        markers, and a literal covers the same literal in any letter case.
        """
        if self.column.strip().lower() != other.column.strip().lower():
            return False
        return all(_value_covered(value, self.match) for value in other.match)


def _value_matches(actual: str, expected: str) -> bool:
    if expected == ANY:
        return actual not in NONE_MARKERS
    if expected in NONE_MARKERS:
        return actual in NONE_MARKERS
    return actual.casefold() == expected.casefold()


def _value_covered(value: str, by: tuple[str, ...]) -> bool:
    if value == ANY:
        return ANY in by
    if value in NONE_MARKERS:
        return any(expected in NONE_MARKERS for expected in by)
    return ANY in by or any(expected.casefold() == value.casefold() for expected in by)  # a literal is never a marker


def parse_match(value: object, key: str = "`match`") -> tuple[str, ...]:
    """The trimmed values of a `match`: a non-empty string, or a non-empty list of them.

    Raises ValueError naming `key`, so another setting with this shape — a route's `when.<column>` —
    reports its own key.
    """
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
        raise ValueError(f"{key} must be a non-empty string or a non-empty list of non-empty strings")
    return tuple(v.strip() for v in values)


def parse_column_predicate(column: object, match: object) -> ColumnPredicate | None:
    """Build a predicate from raw `column` and `match` values.

    Returns None when both are absent, and raises ValueError, with a message naming the key, when
    they are malformed. A string `match` is a one-element list. The column name is kept as given;
    `resolve_column` checks it against the declared columns.
    """
    if column is None and match is None:
        return None
    if match is None:
        raise ValueError("`column` needs `match`")
    if column is None:
        raise ValueError("`match` needs `column`")
    if not isinstance(column, str) or not column.strip():
        raise ValueError("`column` must be a non-empty column name")
    return ColumnPredicate(column.strip(), parse_match(match))


def resolve_column(
    predicate: ColumnPredicate,
    custom_columns: Iterable[str],
    aliases: Mapping[str, str],
    core_columns: Iterable[str],
) -> tuple[ColumnPredicate, str | None]:
    """Resolve the predicate's column to its declared custom column, case-insensitively.

    Returns the predicate with the declared spelling, and None; or the predicate unchanged and a
    problem when the name is not a declared custom column — saying so when it is a core column or
    a core column's alias (`aliases` maps core column -> header).
    """
    wanted = predicate.column.lower()
    declared = next((name for name in custom_columns if name.lower() == wanted), None)
    if declared is not None:
        return replace(predicate, column=declared), None
    core = next((name for name in core_columns if name.lower() == wanted), None)
    if core is not None:
        problem = f"column `{predicate.column}` is core column {core}; a column predicate reads custom columns only"
    else:
        aliased = next((c for c, alias in aliases.items() if alias.lower() == wanted), None)
        if aliased is not None:
            problem = (
                f"column `{predicate.column}` is the alias of core column {aliased}; "
                "a column predicate reads custom columns only"
            )
        else:
            problem = f"column `{predicate.column}` is not declared in [columns].custom"
    return predicate, problem
