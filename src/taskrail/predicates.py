"""The column predicate: `column` plus `match`, tested against a task's custom columns.

Conditional stages use it (DESIGN.md §5.4). It depends on nothing else in taskrail, so any other
setting with the same shape — such as the autopilot's groups — parses and matches it here too.
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


def _value_matches(actual: str, expected: str) -> bool:
    if expected == ANY:
        return actual not in NONE_MARKERS
    if expected in NONE_MARKERS:
        return actual in NONE_MARKERS
    return actual.casefold() == expected.casefold()


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
    values = [match] if isinstance(match, str) else match
    if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
        raise ValueError("`match` must be a non-empty string or a non-empty list of non-empty strings")
    return ColumnPredicate(column.strip(), tuple(v.strip() for v in values))


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
