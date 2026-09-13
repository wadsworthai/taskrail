"""Conditional stages: a column predicate, the executor's judgement, and how show reports them."""

import json

import pytest

from conftest import BASE_CONFIG

from taskrail.cli import main
from taskrail.config import CORE_TASK_COLUMNS
from taskrail.predicates import ColumnPredicate, parse_column_predicate, resolve_column

AREA_CONFIG = BASE_CONFIG.replace("custom = []", 'custom = ["Area"]')

AREA_TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |

## E01 — Billing

| ✓  | ID   | Kind   | Pts | Depends On | Title   | Area  |
|----|------|--------|-----|------------|---------|-------|
| ⬜ | T001 | screen | 1   | —          | Lower   | ui    |
| ⬜ | T002 | screen | 1   | —          | Upper   | UI    |
| ⬜ | T003 | screen | 1   | —          | Padded  |  Ui   |
| ⬜ | T004 | screen | 1   | —          | Backend | api   |
| ⬜ | T005 | screen | 1   | —          | Blank   | —     |
| ⬜ | T006 | screen | 1   | —          | Empty   |       |
"""

NO_AREA_TABLE = """
## E02 — Other

| ✓  | ID   | Kind   | Pts | Depends On | Title   |
|----|------|--------|-----|------------|---------|
| ⬜ | T007 | screen | 1   | —          | Missing |
"""

EPICS_WITH_E02 = "| E01 | Billing | Charge properly | —    |\n| E02 | Other   | Elsewhere       | —    |"


def screen_kind(stage_extra: str) -> str:
    return f"""
name = "screen"
summary = "A kind with one conditional stage."
skill = "screen-skill"

[[stage]]
name = "build"
gate = "always"

[[stage]]
name = "visual-check"
gate = "always"
{stage_extra}
"""


def setup(repo, stage_extra: str, *, layer: str = "types", name: str = "screen", config: str = AREA_CONFIG) -> None:
    repo.write(".taskrail/config.toml", config)
    todo = AREA_TODO.replace("| E01 | Billing | Charge properly | —    |", EPICS_WITH_E02) + NO_AREA_TABLE
    repo.write("TODO.md", todo)
    descriptor = screen_kind(stage_extra)
    if name != "screen":
        descriptor = descriptor.replace('name = "screen"', f'name = "{name}"')
    repo.write(f".taskrail/{layer}/{name}/kind.toml", descriptor)


def run(repo, capsys, *argv: str) -> tuple[int, object]:
    code = main(["--root", str(repo.root), *argv])
    out = capsys.readouterr().out
    try:
        return code, json.loads(out)
    except json.JSONDecodeError:
        return code, out


def stage(repo, capsys, task_id: str, name: str = "visual-check") -> dict:
    code, data = run(repo, capsys, "show", task_id, "--json")
    assert code == 0, data
    return next(s for s in data["kind_descriptor"]["stages"] if s["name"] == name)


# 1, 9 — a column predicate resolved per task, case-insensitively, column spelled as declared


def test_column_predicate_matches_case_insensitively_after_trimming(repo, capsys):
    setup(repo, 'column = "area"\nmatch = ["ui"]')
    assert repo.load()[1] == []
    for task_id in ("T001", "T002", "T003"):
        assert stage(repo, capsys, task_id)["applies"] is True, task_id
    for task_id in ("T004", "T005", "T006"):
        assert stage(repo, capsys, task_id)["applies"] is False, task_id
    reported = stage(repo, capsys, "T001")
    assert reported["column"] == "Area"
    assert reported["match"] == ["ui"]
    assert reported["judgement"] is False


# 2 — several values, "*" and "—"


def test_any_of_several_values(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = ["api", "UX", "ui"]')
    assert [stage(repo, capsys, t)["applies"] for t in ("T001", "T004", "T005")] == [True, True, False]


def test_star_matches_any_non_empty_cell(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = ["*"]')
    assert [stage(repo, capsys, t)["applies"] for t in ("T001", "T004", "T005", "T006", "T007")] == [
        True,
        True,
        False,
        False,
        False,
    ]


@pytest.mark.parametrize("marker", ["—", "-"])
def test_empty_marker_matches_an_empty_cell_or_a_missing_column(repo, capsys, marker):
    setup(repo, f'column = "Area"\nmatch = ["{marker}"]')
    assert [stage(repo, capsys, t)["applies"] for t in ("T001", "T005", "T006", "T007")] == [False, True, True, True]


# 3 — a string is a one-element list


def test_match_as_a_string(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = "ui"')
    reported = stage(repo, capsys, "T002")
    assert reported["match"] == ["ui"]
    assert reported["applies"] is True
    assert stage(repo, capsys, "T004")["applies"] is False


# 4 — judgement, alone and with a column predicate; applies is always a boolean


def test_judgement_alone(repo, capsys):
    setup(repo, "judgement = true")
    for task_id in ("T001", "T004", "T007"):
        reported = stage(repo, capsys, task_id)
        assert reported["applies"] is True
        assert reported["judgement"] is True
        assert reported["column"] is None


def test_judgement_with_a_column_predicate(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = ["ui"]\njudgement = true')
    matching, other = stage(repo, capsys, "T001"), stage(repo, capsys, "T004")
    assert (matching["applies"], matching["judgement"]) == (True, True)
    assert (other["applies"], other["judgement"]) == (False, True)


# 5 — a plain stage, and the core kinds


def test_plain_stage_reports_defaults(repo, capsys):
    setup(repo, "")
    reported = stage(repo, capsys, "T004")
    assert {k: reported[k] for k in ("column", "match", "judgement", "applies")} == {
        "column": None,
        "match": [],
        "judgement": False,
        "applies": True,
    }


def test_core_kind_stages_only_gain_the_new_fields(repo, capsys):
    code, data = run(repo, capsys, "show", "T002", "--json")
    assert code == 0
    stages = data["kind_descriptor"]["stages"]
    assert [s["name"] for s in stages] == ["plan", "implement", "verify"]
    for entry in stages:
        assert set(entry) == {"name", "summary", "gate", "commit", "checks", "column", "match", "judgement", "applies"}
        assert (entry["column"], entry["match"], entry["judgement"], entry["applies"]) == (None, [], False, True)


# 6 — kind list has no task, so no applies


def test_kind_list_reports_the_predicate_without_applies(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = ["ui"]\njudgement = true')
    code, data = run(repo, capsys, "kind", "list", "--json")
    assert code == 0
    screen = next(k for k in data if k["name"] == "screen")
    entry = next(s for s in screen["stages"] if s["name"] == "visual-check")
    assert (entry["column"], entry["match"], entry["judgement"]) == ("Area", ["ui"], True)
    assert "applies" not in entry


# 7 — malformed predicates


@pytest.mark.parametrize(
    ("extra", "fragment"),
    [
        ('column = "Area"', "`column` needs `match`"),
        ('match = ["ui"]', "`match` needs `column`"),
        ('column = "Area"\nmatch = []', "`match` must"),
        ('column = "Area"\nmatch = ["ui", 3]', "`match` must"),
        ('column = "Area"\nmatch = ["  "]', "`match` must"),
        ('column = ""\nmatch = ["ui"]', "`column` must"),
        ('column = 3\nmatch = ["ui"]', "`column` must"),
        ('judgement = "yes"', "`judgement` must be true or false"),
    ],
)
def test_malformed_predicate_is_kind_invalid(repo, extra, fragment):
    setup(repo, extra)
    _, issues = repo.load()
    invalid = [i for i in issues if i.code == "kind-invalid"]
    assert len(invalid) == 1, issues
    assert "stage `visual-check`" in invalid[0].message
    assert fragment in invalid[0].message


# 8 — undeclared, core and aliased columns


def test_undeclared_column_is_an_error_that_keeps_the_kind(repo, capsys):
    setup(repo, 'column = "Team"\nmatch = ["ui"]')
    project, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["stage-column-unknown"]
    assert errors[0].file == ".taskrail/types/screen/kind.toml"
    assert "`Team`" in errors[0].message and "[columns].custom" in errors[0].message
    assert "screen" in project.kinds
    code, _ = run(repo, capsys, "show", "T001", "--json")
    assert code == 1


@pytest.mark.parametrize("name", ["Pts", "pts", "DESCRIPTION", "Kind", "✓"])
def test_core_column_is_refused(repo, name):
    setup(repo, f'column = "{name}"\nmatch = ["1"]')
    _, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["stage-column-unknown"]
    core = next(c for c in CORE_TASK_COLUMNS if c.lower() == name.lower())
    assert f"core column {core}" in errors[0].message


@pytest.mark.parametrize("name", ["Size", "size"])
def test_alias_of_a_core_column_is_refused(repo, name):
    config = AREA_CONFIG.replace('custom = ["Area"]', 'custom = ["Area"]\naliases = { Pts = "Size" }')
    setup(repo, f'column = "{name}"\nmatch = ["1"]', config=config)
    todo = (repo.root / "TODO.md").read_text().replace("| Pts |", "| Size |")
    repo.write("TODO.md", todo)
    _, issues = repo.load()
    errors = [i for i in issues if i.severity == "error"]
    assert [i.code for i in errors] == ["stage-column-unknown"]
    assert "alias of core column Pts" in errors[0].message


# 10 — overrides


def test_predicate_in_an_override_of_a_core_kind(repo, capsys):
    setup(repo, 'column = "Area"\nmatch = ["ui"]', layer="overrides", name="feature")
    todo = (repo.root / "TODO.md").read_text().replace("| screen |", "| feature |")
    repo.write("TODO.md", todo)
    assert repo.load()[1] == []
    assert stage(repo, capsys, "T001")["applies"] is True
    assert stage(repo, capsys, "T004")["applies"] is False


def test_override_errors_carry_the_override_path(repo):
    setup(repo, 'column = "Team"\nmatch = ["ui"]', layer="overrides", name="feature")
    _, issues = repo.load()
    unknown = [i for i in issues if i.code == "stage-column-unknown"]
    assert [i.file for i in unknown] == [".taskrail/overrides/feature/kind.toml"]


# 11 — the predicate module stands on its own


def test_predicate_module_parses_resolves_and_matches_without_kinds():
    predicate = parse_column_predicate("area", ["UI"])
    assert predicate == ColumnPredicate("area", ("UI",))
    resolved, problem = resolve_column(predicate, ("Area",), {}, CORE_TASK_COLUMNS)
    assert problem is None
    assert resolved.column == "Area"
    assert resolved.matches({"Area": " ui "})
    assert resolved.matches({"area": "Ui"})
    assert not resolved.matches({"Area": "api"})
    assert not resolved.matches({})
    assert parse_column_predicate(None, None) is None
    with pytest.raises(ValueError):
        parse_column_predicate("Area", None)
    _, problem = resolve_column(ColumnPredicate("Size", ("1",)), ("Area",), {"Pts": "Size"}, CORE_TASK_COLUMNS)
    assert problem is not None and "alias of core column Pts" in problem


# 12 — text show


def test_text_show_marks_conditional_stages(repo, capsys):
    repo.write(".taskrail/config.toml", AREA_CONFIG)
    repo.write("TODO.md", AREA_TODO)
    repo.write(
        ".taskrail/types/screen/kind.toml",
        screen_kind('column = "Area"\nmatch = ["ui"]')
        + '\n[[stage]]\nname = "migration-review"\ngate = "conditional"\njudgement = true\n',
    )
    code, out = run(repo, capsys, "show", "T004")
    assert code == 0
    assert "  · build (gate: always)\n" in out
    assert "  · visual-check (gate: always) — not applicable (Area)\n" in out
    assert "  · migration-review (gate: conditional) — executor's judgement\n" in out
    code, out = run(repo, capsys, "show", "T001")
    assert "  · visual-check (gate: always)\n" in out


def test_predicate_module_imports_nothing_else_from_taskrail():
    import taskrail.predicates

    source = open(taskrail.predicates.__file__, encoding="utf-8").read()
    assert "from taskrail" not in source and "import taskrail" not in source


# 13 — the core skill's step 5


def test_core_skill_step_5_covers_applies_and_judgement():
    import taskrail

    skill = taskrail.__path__[0] + "/skills/taskrail/SKILL.md"
    text = open(skill, encoding="utf-8").read()
    step = " ".join(text[text.index("5. **Stages.**") : text.index("6. **Scope.**")].split())
    assert "Skip a stage whose `applies` is false" in step
    assert "When `applies` and `judgement` are both true" in step
    assert "in the artifact and in the next gate report" in step
    assert "if its gate is `always`, stop and ask before" in step
    assert "`summary`" in step
