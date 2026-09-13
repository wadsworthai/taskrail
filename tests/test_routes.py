"""Routes: `[[route]]` matched through the shared column predicate, validated, ordered and reported."""

import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import BASE_CONFIG

from taskrail.cli import main
from taskrail.config import CORE_TASK_COLUMNS
from taskrail.kinds import Route
from taskrail.predicates import ColumnPredicate, parse_column_predicate, parse_match

ROUTE_CONFIG = BASE_CONFIG.replace("custom = []", 'custom = ["Stack", "Spec"]')

ROUTE_TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |
| E02 | Other   | Elsewhere       | —    |

## E01 — Billing

| ✓  | ID   | Kind | Pts | Depends On | Title  | Stack | Spec |
|----|------|------|-----|------------|--------|-------|------|
| ⬜ | T001 | svc  | 1   | —          | Lower  | api   | —    |
| ⬜ | T002 | svc  | 1   | —          | Upper  | API   | -    |
| ⬜ | T003 | svc  | 1   | —          | Padded |  Api  | 0007 |
| ⬜ | T004 | svc  | 1   | —          | Web    | web   | —    |
| ⬜ | T005 | svc  | 1   | —          | Blank  | —     | —    |
| ⬜ | T006 | svc  | 1   | —          | Empty  |       | 0009 |

## E02 — Other

| ✓  | ID   | Kind | Pts | Depends On | Title   |
|----|------|------|-----|------------|---------|
| ⬜ | T007 | svc  | 1   | —          | Missing |
"""

KIND_PATH = ".taskrail/types/svc/kind.toml"


def svc_kind(routes: str, default: str | None = "svc-default") -> str:
    skill = f'skill = "{default}"\n' if default else ""
    return f'name = "svc"\nsummary = "Service work."\n{skill}\n{routes}\n[[stage]]\nname = "build"\n'


def route(when: str, skill: str) -> str:
    return f"[[route]]\nwhen = {when}\nskill = \"{skill}\"\n"


def setup(repo, *routes: str, config: str = ROUTE_CONFIG, default: str | None = "svc-default") -> None:
    repo.write(".taskrail/config.toml", config)
    repo.write("TODO.md", ROUTE_TODO)
    repo.write(KIND_PATH, svc_kind("\n".join(routes), default))


def run(repo, capsys, *argv: str) -> tuple[int, object]:
    code = main(["--root", str(repo.root), *argv])
    out = capsys.readouterr().out
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


def skills(repo, capsys, *task_ids: str) -> list[str | None]:
    result = []
    for task_id in task_ids:
        code, data = run(repo, capsys, "show", task_id, "--json")
        assert code == 0, data
        result.append(data["skill"])
    return result


# 1 — values are trimmed and case-insensitive


def test_route_values_are_trimmed_and_case_insensitive(repo, capsys):
    setup(repo, route('{ Stack = "api" }', "r1"), route('{ Stack = " WEB " }', "r2"))
    assert repo.load()[1] == []
    assert skills(repo, capsys, "T001", "T002", "T003", "T004", "T005", "T006", "T007") == [
        "r1",
        "r1",
        "r1",
        "r2",
        "svc-default",
        "svc-default",
        "svc-default",
    ]


# 2 — a list of values, and a one-element list as the string


def test_route_value_list_holds_for_any_value(repo, capsys):
    setup(repo, route('{ Stack = ["web", "API"] }', "r1"))
    assert repo.load()[1] == []
    assert skills(repo, capsys, "T001", "T003", "T004", "T005") == ["r1", "r1", "r1", "svc-default"]


def test_one_element_list_behaves_as_the_string(repo, capsys):
    setup(repo, route('{ Stack = ["web"] }', "r1"))
    assert skills(repo, capsys, "T001", "T004") == ["svc-default", "r1"]


# 3 — every entry must hold; "*" and the empty markers


def test_route_holds_only_when_every_entry_holds(repo, capsys):
    setup(repo, route('{ Stack = "*", Spec = "—" }', "r1"))
    assert skills(repo, capsys, "T001", "T002", "T003", "T004", "T005", "T006", "T007") == [
        "r1",
        "r1",
        "svc-default",
        "r1",
        "svc-default",
        "svc-default",
        "svc-default",
    ]


def test_star_never_holds_for_an_empty_cell(repo, capsys):
    setup(repo, route('{ Stack = "*" }', "r1"))
    assert skills(repo, capsys, "T001", "T005", "T006", "T007") == ["r1", "svc-default", "svc-default", "svc-default"]


@pytest.mark.parametrize("marker", ["—", "-"])
def test_empty_marker_holds_for_an_empty_cell_or_a_missing_column(repo, capsys, marker):
    setup(repo, route(f'{{ Stack = "{marker}" }}', "r1"))
    assert skills(repo, capsys, "T001", "T005", "T006", "T007") == ["svc-default", "r1", "r1", "r1"]


# 4 — the first route that holds wins, in descriptor order


def test_first_route_that_holds_wins(repo, capsys):
    setup(repo, route('{ Stack = "*" }', "by-stack"), route('{ Spec = "*" }', "by-spec"))
    assert repo.load()[1] == []
    assert skills(repo, capsys, "T003", "T006", "T005") == ["by-stack", "by-spec", "svc-default"]


def test_reordered_routes_change_the_winner(repo, capsys):
    setup(repo, route('{ Spec = "*" }', "by-spec"), route('{ Stack = "*" }', "by-stack"))
    assert skills(repo, capsys, "T003", "T001") == ["by-spec", "by-stack"]


def test_no_route_and_no_skill_reports_null(repo, capsys):
    setup(repo, route('{ Stack = "api" }', "r1"), default=None)
    assert skills(repo, capsys, "T001", "T004") == ["r1", None]


# 5 — column keys resolve case-insensitively


def test_column_key_resolves_case_insensitively(repo, capsys):
    setup(repo, route('{ stack = "*", SPEC = "0007" }', "r1"))
    assert repo.load()[1] == []
    assert skills(repo, capsys, "T003", "T001") == ["r1", "svc-default"]


# 6 — undeclared, core and aliased columns


def test_undeclared_column_is_an_error_that_keeps_the_kind(repo, capsys):
    setup(repo, route('{ Stack = "api" }', "r1"), route('{ Team = "x" }', "r2"))
    project, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["route-column-unknown"]
    assert errors[0].file == KIND_PATH
    assert "route #2" in errors[0].message
    assert "`Team`" in errors[0].message and "[columns].custom" in errors[0].message
    assert "svc" in project.kinds
    assert all(i.code != "route-column-undeclared" for i in issues)
    code, _ = run(repo, capsys, "validate", "--json")
    assert code == 1
    code, _ = run(repo, capsys, "show", "T001", "--json")
    assert code == 1


def test_undeclared_column_present_in_the_table_is_still_an_error(repo):
    setup(repo, route('{ Spec = "*" }', "r1"), config=BASE_CONFIG.replace("custom = []", 'custom = ["Stack"]'))
    _, issues = repo.load()
    assert [i.code for i in issues if i.severity == "error"] == ["route-column-unknown"]
    assert "route-column-undeclared" not in [i.code for i in issues]


@pytest.mark.parametrize("name", ["Pts", "pts", "DESCRIPTION", "Kind", "✓"])
def test_core_column_is_refused(repo, name):
    setup(repo, route(f'{{ "{name}" = "1" }}', "r1"))
    _, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["route-column-unknown"]
    core = next(c for c in CORE_TASK_COLUMNS if c.lower() == name.lower())
    assert f"core column {core}" in errors[0].message
    assert "route #1" in errors[0].message


@pytest.mark.parametrize("name", ["Size", "size"])
def test_alias_of_a_core_column_is_refused(repo, name):
    config = ROUTE_CONFIG.replace('custom = ["Stack", "Spec"]', 'custom = ["Stack", "Spec"]\naliases = { Pts = "Size" }')
    setup(repo, route(f'{{ {name} = "1" }}', "r1"), config=config)
    repo.write("TODO.md", ROUTE_TODO.replace("| Pts |", "| Size |"))
    _, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["route-column-unknown"]
    assert "alias of core column Pts" in errors[0].message


def test_override_route_errors_carry_the_override_path(repo):
    repo.write(".taskrail/config.toml", ROUTE_CONFIG)
    repo.write(
        ".taskrail/overrides/feature/kind.toml",
        'name = "feature"\nsummary = "x"\nskill = "f"\n' + route('{ Team = "x" }', "r1") + '[[stage]]\nname = "a"\n',
    )
    _, issues = repo.load()
    assert [(i.code, i.file) for i in issues if i.severity == "error"] == [
        ("route-column-unknown", ".taskrail/overrides/feature/kind.toml")
    ]


# 7 — malformed routes


@pytest.mark.parametrize(
    ("routes", "fragment"),
    [
        ('[[route]]\nwhen = "api"\nskill = "r1"\n', "route #1: `when` must map column names to values"),
        ('[[route]]\nwhen = {}\nskill = "r1"\n', "route #1: `when` must map column names to values"),
        ('[[route]]\nskill = "r1"\n', "route #1: `when` must map column names to values"),
        ('[[route]]\nwhen = { Stack = 3 }\nskill = "r1"\n', "route #1: `when.Stack` must be a non-empty string"),
        ('[[route]]\nwhen = { Stack = "" }\nskill = "r1"\n', "route #1: `when.Stack` must be a non-empty string"),
        ('[[route]]\nwhen = { Stack = "  " }\nskill = "r1"\n', "route #1: `when.Stack` must be a non-empty string"),
        ('[[route]]\nwhen = { Stack = [] }\nskill = "r1"\n', "route #1: `when.Stack` must be a non-empty string"),
        ('[[route]]\nwhen = { Stack = ["api", 3] }\nskill = "r1"\n', "route #1: `when.Stack` must be a non-empty string"),
        ('[[route]]\nwhen = { " " = "api" }\nskill = "r1"\n', "route #1: `when` has an empty column name"),
        ('[[route]]\nwhen = { Stack = "a", stack = "b" }\nskill = "r1"\n', "route #1: `when` names column `stack` twice"),
        ('[[route]]\nwhen = { Stack = "api" }\n', "route #1: `skill` is required"),
        ('route = "x"\n', "`route` must be an array of tables"),
    ],
)
def test_malformed_route_is_kind_invalid(repo, routes, fragment):
    setup(repo, routes)
    _, issues = repo.load()
    invalid = [i for i in issues if i.code == "kind-invalid"]
    assert [i.message for i in invalid if fragment in i.message], [i.message for i in invalid]


# 8 — route-unreachable: only for a route no task can be the first to reach


@pytest.mark.parametrize(
    ("whens", "expected"),
    [
        # letter case and padding
        (['{ Stack = "API" }', '{ Stack = "api" }'], [(2, 1)]),
        (['{ Stack = "api" }', '{ Stack = " Api " }'], [(2, 1)]),
        # a list, and the values it covers
        (['{ Stack = ["api", "web"] }', '{ Stack = "WEB" }'], [(2, 1)]),
        (['{ Stack = "api" }', '{ Stack = ["api", "web"] }'], []),
        # "*" and the empty markers
        (['{ Stack = "*" }', '{ Stack = "api" }'], [(2, 1)]),
        (['{ Stack = "api" }', '{ Stack = "*" }'], []),
        (['{ Stack = "*" }', '{ Stack = "—" }'], []),
        (['{ Stack = "—" }', '{ Stack = "*" }'], []),
        (['{ Stack = "*" }', '{ Stack = ["api", "—"] }'], []),
        (['{ Stack = "—" }', '{ Stack = "-" }'], [(2, 1)]),
        (['{ Stack = ["*", "—"] }', '{ Stack = "—" }'], [(2, 1)]),
        (['{ Stack = ["*", "-"] }', '{ Stack = ["api", "—"] }'], [(2, 1)]),
        # several columns
        (['{ Stack = "*" }', '{ Stack = "api", Spec = "—" }'], [(2, 1)]),
        (['{ Stack = "api", Spec = "—" }', '{ Stack = "api" }'], []),
        (['{ Stack = "api", Spec = "—" }', '{ spec = "-", STACK = "API" }'], [(2, 1)]),
        (['{ Stack = "*" }', '{ Spec = "*" }'], []),
        (['{ Stack = "api", Spec = "*" }', '{ Stack = "api", Spec = "—" }'], []),
        # the first covering route is named, and each unreachable route is reported once
        (['{ Stack = "api" }', '{ Spec = "*" }', '{ Stack = "API", Spec = "x" }'], [(3, 1)]),
        (['{ Stack = "*" }', '{ Stack = "api" }', '{ Stack = "API" }'], [(2, 1), (3, 1)]),
    ],
)
def test_route_unreachable(repo, whens, expected):
    setup(repo, *(route(when, f"r{n}") for n, when in enumerate(whens, start=1)))
    _, issues = repo.load()
    assert [i for i in issues if i.severity == "error"] == []
    unreachable = [i for i in issues if i.code == "route-unreachable"]
    assert all(i.severity == "warning" and i.file == KIND_PATH for i in unreachable)
    assert [i.message for i in unreachable] == [
        f"route #{later} never applies: route #{earlier}, listed before it, matches every task it matches"
        for later, earlier in expected
    ]


CELLS = ["", "—", "-", "api", "API", "web", "x"]
VALUES = ["*", "—", "-", "api", "Api", "web"]


def _whens():
    singles = [(v,) for v in VALUES] + [pair for pair in itertools.combinations(VALUES, 2)]
    for columns in (("Stack",), ("Spec",), ("Stack", "Spec")):
        for choice in itertools.product(singles, repeat=len(columns)):
            yield tuple(ColumnPredicate(c, m) for c, m in zip(columns, choice))


def test_covers_never_hides_a_route_some_task_reaches():
    """Exhaustively: whenever a route covers another, every task the later one matches, the earlier matches."""
    tasks = [SimpleNamespace(columns={"Stack": s, "Spec": p}) for s in CELLS for p in CELLS]
    tasks.append(SimpleNamespace(columns={}))
    whens = list(_whens())
    covered = 0
    for earlier, later in itertools.product(whens, repeat=2):
        first, second = Route(earlier, "a"), Route(later, "b")
        if first.covers(second):
            covered += 1
            assert all(first.matches(t) for t in tasks if second.matches(t)), (earlier, later)
    assert covered > 0


# 9 — routes in show and kind list


def test_routes_json_keeps_single_values_as_strings(repo, capsys):
    setup(
        repo,
        route('{ stack = " api " }', "r1"),
        route('{ Spec = ["x", " Y "], STACK = "*" }', "r2"),
        route('{ Stack = ["web"] }', "r3"),
    )
    expected = [
        {"when": {"Stack": "api"}, "skill": "r1"},
        {"when": {"Spec": ["x", "Y"], "Stack": "*"}, "skill": "r2"},
        {"when": {"Stack": "web"}, "skill": "r3"},
    ]
    code, data = run(repo, capsys, "kind", "list", "--json")
    assert code == 0
    assert next(k for k in data if k["name"] == "svc")["routes"] == expected
    code, data = run(repo, capsys, "show", "T001", "--json")
    assert code == 0
    assert data["kind_descriptor"]["routes"] == expected


def test_text_show_prints_only_the_resolved_skill(repo, capsys):
    setup(repo, route('{ Stack = "API" }', "r1"))
    code, out = run(repo, capsys, "show", "T001")
    assert code == 0
    assert "  skill r1\n" in out
    assert "route" not in out


def test_spec_kit_example_routes_report_as_before(repo, capsys):
    example = Path(__file__).parents[1] / "examples/spec-kit/.taskrail/types/spec/kind.toml"
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = ["Spec"]'))
    repo.write(".taskrail/types/spec/kind.toml", example.read_text(encoding="utf-8"))
    assert [i for i in repo.load()[1] if i.severity == "error"] == []
    code, data = run(repo, capsys, "kind", "list", "--json")
    assert code == 0
    assert next(k for k in data if k["name"] == "spec")["routes"] == [
        {"when": {"Spec": "—"}, "skill": "spec-new-pipeline"},
        {"when": {"Spec": "*"}, "skill": "spec-amend-pipeline"},
    ]


# 10 — the predicate module


def test_parse_match_names_its_key():
    assert parse_match(" ui ") == ("ui",)
    assert parse_match(["ui", " UX "], "`when.Area`") == ("ui", "UX")
    with pytest.raises(ValueError, match=r"^`when.Area` must be a non-empty string"):
        parse_match("", "`when.Area`")
    with pytest.raises(ValueError, match=r"^`match` must be a non-empty string or a non-empty list of non-empty strings$"):
        parse_column_predicate("Area", [])


def test_parse_column_predicate_messages_are_unchanged():
    for column, match, message in [
        ("Area", None, "`column` needs `match`"),
        (None, "ui", "`match` needs `column`"),
        ("", "ui", "`column` must be a non-empty column name"),
        ("Area", ["ui", 3], "`match` must be a non-empty string or a non-empty list of non-empty strings"),
    ]:
        with pytest.raises(ValueError) as caught:
            parse_column_predicate(column, match)
        assert str(caught.value) == message


def test_covers_compares_values_as_the_matcher_does():
    star, empty, dash = ColumnPredicate("Area", ("*",)), ColumnPredicate("Area", ("—",)), ColumnPredicate("area", ("-",))
    assert star.covers(ColumnPredicate("Area", ("UI", "api")))
    assert not star.covers(empty)
    assert not empty.covers(star)
    assert empty.covers(dash) and dash.covers(empty)
    assert ColumnPredicate("Area", ("ui",)).covers(ColumnPredicate("AREA", ("UI",)))
    assert not ColumnPredicate("Area", ("ui",)).covers(ColumnPredicate("Team", ("ui",)))
    assert not ColumnPredicate("Area", ("ui",)).covers(ColumnPredicate("Area", ("ui", "ux")))
