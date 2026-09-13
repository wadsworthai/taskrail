"""Column aliases: a repository's own header names for taskrail's core task columns."""

import difflib
import json
import re

import pytest

from conftest import BASE_CONFIG, BASE_TODO, git

from taskrail.cli import main
from taskrail.config import load_config
from taskrail.issues import ConfigError
from taskrail.markdown import split_row

ALL_ALIASES = (
    '{ "✓" = "Status", ID = "Key", Kind = "Type", Pts = "Size", '
    '"Depends On" = "Blocked By", Title = "Summary", Description = "Notes" }'
)

ALIASED_TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |

## E01 — Billing

Done when: every session has a cost.

| Status | Key  | Type    | Size | Blocked By | Summary        | Notes       |
|--------|------|---------|------|------------|----------------|-------------|
| ✅     | T001 | chore   | 2    | —          | Price table    | Base prices |
| ⬜     | T002 | feature | 3    | T001       | Repricing      | Recompute   |
| ⬜     | T003 | bug     | 1    | T002       | Rounding error | Off by one  |
"""


def configure(repo, aliases: str, custom: str = "[]") -> None:
    repo.write(
        ".taskrail/config.toml",
        BASE_CONFIG.replace("custom = []", f"custom = {custom}\naliases = {aliases}"),
    )


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def todo(repo) -> str:
    return (repo.root / "TODO.md").read_text(encoding="utf-8")


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def messages(repo, code: str) -> list[str]:
    return [issue.message for issue in repo.load()[1] if issue.code == code]


@pytest.fixture
def aliased(git_repo):
    configure(git_repo, ALL_ALIASES)
    git_repo.write("TODO.md", ALIASED_TODO)
    git(git_repo.root, "commit", "-q", "-am", "alias every core column")
    return git_repo


# 1. Size for Pts


def test_size_alias_for_pts_validates_and_feeds_points(repo, capsys):
    configure(repo, '{ Pts = "Size" }')
    repo.write("TODO.md", BASE_TODO.replace("| Pts |", "| Size |").replace("|-----|---", "|------|---", 1))
    assert repo.codes() == []
    assert repo.codes("warning") == []
    code, out, _ = run(repo.root, "show", "T002", "--json", capsys=capsys)
    assert code == 0
    shown = json.loads(out)
    assert (shown["points"], shown["columns"]) == (3, {})


# 2. Every core column


def test_every_core_column_can_be_aliased(aliased):
    project, issues = aliased.load()
    assert issues == []
    task = next(t for t in project.tasks if t.id == "T002")
    assert (task.status_raw, task.kind, task.points, task.depends_on, task.title, task.description, task.columns) == (
        "⬜", "feature", 3, ["T001"], "Repricing", "Recompute", {},
    )


def test_a_missing_aliased_column_is_named_by_alias_and_core_name(aliased):
    aliased.write("TODO.md", ALIASED_TODO.replace("| Blocked By |", "| Needs      |"))
    assert messages(aliased, "task-columns") == ["task table is missing column(s): Blocked By (Depends On)"]


# 3. Case-insensitive


@pytest.mark.parametrize("header", ["size", "SIZE"])
def test_aliases_match_case_insensitively(repo, header):
    configure(repo, '{ Pts = "Size" }')
    repo.write("TODO.md", BASE_TODO.replace("| Pts |", f"| {header} |").replace("|-----|---", "|------|---", 1))
    assert repo.codes() == []
    assert repo.codes("warning") == []
    assert next(t for t in repo.load()[0].tasks if t.id == "T002").points == 3


def test_alias_for_the_other_case_of_its_own_name_changes_nothing(repo):
    configure(repo, '{ Pts = "pts" }')
    assert repo.load()[1] == []


# 4. The alias replaces the core name


def test_core_name_of_an_aliased_column_is_a_column_alias_error(repo):
    assert repo.codes() == []
    configure(repo, '{ Pts = "Size" }')
    _, issues = repo.load()
    alias_issues = [i for i in issues if i.code == "column-alias"]
    assert [i.code for i in issues if i.severity == "error"] == ["column-alias"]
    assert len(alias_issues) == 1
    assert "`Size`" in alias_issues[0].message
    lines = BASE_TODO.lstrip("\n").splitlines()
    table_line = next(number for number, line in enumerate(lines, 1) if line.startswith("| ✓"))
    assert (alias_issues[0].file, alias_issues[0].line) == ("TODO.md", table_line)


# 5. new fills aliased columns


def test_new_fills_aliased_columns_with_a_one_row_diff(aliased, capsys):
    before = todo(aliased)
    code, out, _ = run(
        aliased.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals",
        "--pts", "3", "--depends-on", "T001", "--description", "D", capsys=capsys,
    )
    assert (code, out.strip()) == (0, "T004")
    changed = changed_lines(before, todo(aliased))
    assert len(changed) == 1 and changed[0].startswith("+")
    assert split_row(changed[0][1:]) == ["⬜", "T004", "bug", "3", "T001", "Negative totals", "D"]
    assert run(aliased.root, "validate", capsys=capsys)[0] == 0


@pytest.mark.parametrize(
    ("pair", "hint"),
    [("Size=3", "--pts"), ("size=3", "--pts"), ("Pts=3", "--pts"), ("Blocked By=T001", "--depends-on"), ("Key=T009", "taskrail")],
)
def test_new_column_for_an_aliased_core_column_names_the_flag_to_use(aliased, capsys, pair, hint):
    before = todo(aliased)
    code, _, err = run(
        aliased.root, "new", "--epic", "E01", "--kind", "bug", "--title", "X", "--column", pair, capsys=capsys
    )
    assert code == 2
    assert hint in err
    assert todo(aliased) == before
    assert run(aliased.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


# 6. A new table uses the alias names


def test_new_table_without_a_template_uses_the_alias_names(git_repo, capsys):
    configure(git_repo, ALL_ALIASES)
    git_repo.write("TODO.md", ALIASED_TODO.split("| Status |")[0])
    git(git_repo.root, "commit", "-q", "-am", "an epic with no tasks")
    code, out, _ = run(git_repo.root, "new", "--epic", "E01", "--kind", "chore", "--title", "First", capsys=capsys)
    assert (code, out.strip()) == (0, "T001")
    header = next(line for line in todo(git_repo).splitlines() if "Key" in line)
    assert split_row(header) == ["Status", "Key", "Type", "Size", "Blocked By", "Summary", "Notes"]
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0


# 7. Status changes on an aliased ✓ column


def test_status_commands_change_an_aliased_status_column(aliased, capsys):
    assert run(aliased.root, "discard", "T003", capsys=capsys)[0] == 0
    assert "| ❌     | T003 |" in todo(aliased)
    assert run(aliased.root, "reopen", "T003", "--reason", "Still needed", capsys=capsys)[0] == 0
    assert "| ⬜     | T003 |" in todo(aliased)
    assert run(aliased.root, "claim", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    assert run(aliased.root, "done", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    assert "| ✅     | T002 |" in todo(aliased)


# 8. ID allocation


def test_id_allocation_sees_an_aliased_id_column(aliased, capsys):
    assert run(aliased.root, "reserve-id", capsys=capsys)[1].strip() == "T004"
    git(aliased.root, "checkout", "-q", "-b", "T010-elsewhere")
    aliased.write("TODO.md", ALIASED_TODO + "| ⬜     | T010 | bug     | 1    | —          | Elsewhere      | Branch      |\n")
    git(aliased.root, "commit", "-q", "-am", "add T010 on a branch")
    git(aliased.root, "checkout", "-q", "main")
    assert run(aliased.root, "reserve-id", capsys=capsys)[1].strip() == "T011"


# 9. Conflicting configuration


@pytest.mark.parametrize(
    ("aliases", "custom", "match"),
    [
        ('{ Owner = "Team" }', "[]", "`Owner` is not a core task column"),
        ('{ Pts = "" }', "[]", "columns.aliases.Pts must be a non-empty header name"),
        ('{ Pts = "a|b" }', "[]", "columns.aliases.Pts must be a non-empty header name"),
        ('{ Pts = 3 }', "[]", "columns.aliases.Pts must be a non-empty header name"),
        ('{ Pts = "title" }', "[]", "alias `title` for Pts is the name of core column Title"),
        ('{ Pts = "Size", Description = "SIZE" }', "[]", "alias `SIZE` is given to both Pts and Description"),
        ('{ Pts = "Size", pts = "Points" }', "[]", "Pts is aliased more than once"),
        ('{ Pts = "Size" }', '["size"]', "alias `Size` for Pts is also a custom column"),
        ('["Pts"]', "[]", "`aliases` must be dict"),
    ],
)
def test_conflicting_aliases_are_refused(repo, capsys, aliases, custom, match):
    configure(repo, aliases, custom)
    with pytest.raises(ConfigError, match=re.escape(match)):
        load_config(repo.root)
    assert run(repo.root, "validate", capsys=capsys)[0] == 2


# 10. No aliases: unchanged behaviour is covered by the rest of the suite.
