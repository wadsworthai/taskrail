"""`taskrail import`: converting a table-based Markdown backlog without epics (T005).

Every source here is invented for the tests.
"""

import difflib
import json
import textwrap

import pytest

from conftest import BASE_CONFIG

from taskrail.cli import main
from taskrail.install import DEFAULT_TODO
from taskrail.markdown import split_row


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def source(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


def read(repo, relative: str = "TODO.md") -> str:
    return (repo.root / relative).read_text(encoding="utf-8")


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def import_json(repo, *argv, capsys, file: str = "TODO.md"):
    code, out, err = run(repo.root, "import", str(repo.root / file), *argv, "--json", capsys=capsys)
    return code, (json.loads(out) if out.strip() else None), err


def row(text: str, task_id: str) -> list[str]:
    line = next(line for line in text.splitlines() if f"| {task_id} " in line)
    return split_row(line)


TWO_SECTIONS = source(
    """
    # Garden planner backlog

    Tasks for the planner app.

    ## Planting calendar

    | Status | ID   | Type    | Title                  | Notes              |
    |--------|------|---------|------------------------|--------------------|
    | [x]    | T001 | Feature | Show frost dates       | uses `a \\| b` form |
    | [ ]    | T002 | bug     | Fix week numbering     | —                  |

    ## Watering

    Some prose about watering.

    | Status | ID   | Type    | Title                  | Notes              |
    |--------|------|---------|------------------------|--------------------|
    | [ ]    | T003 | chore   | Rename sensor module   |                    |
    """
)

MAP_FLAGS = ("--column", "✓=Status", "--column", "Kind=Type")


# 1. Headings become epics and the result validates


def test_headings_become_epics_and_the_result_validates(repo, capsys):
    repo.write("TODO.md", TWO_SECTIONS)
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), *MAP_FLAGS, "--write", capsys=capsys)
    assert code == 0, err
    project, issues = repo.load()
    assert [i for i in issues if i.severity == "error"] == []
    warnings = [i for i in issues if i.severity == "warning"]
    assert {i.code for i in warnings} == {"column-undeclared"}
    assert all("Notes" in i.message for i in warnings)
    epics = project.backlogs[0].epics
    assert [(e.id, e.name) for e in epics] == [("E01", "Planting calendar"), ("E02", "Watering")]
    assert [(t.id, t.epic, t.status_raw, t.kind, t.title) for t in project.tasks] == [
        ("T001", "E01", "✅", "feature", "Show frost dates"),
        ("T002", "E01", "⬜", "bug", "Fix week numbering"),
        ("T003", "E02", "⬜", "chore", "Rename sensor module"),
    ]
    assert project.task("T001").columns == {"Notes": "uses `a | b` form"}


# 2. Everything but the converted lines is byte-identical


PRESERVED = source(
    """
    # Orchard tasks

    Intro with a list:

    - keep this item
    - and this one

    | ID  | Decision            |
    |-----|---------------------|
    | D1  | Use raised beds     |

    ```text
    | ✓  | ID   | Kind | Depends On | Title |
    |----|------|------|------------|-------|
    ## Not a heading
    ```

    ## Pruning

    Prose   with   odd   spacing.

    | ✓  | ID   | Kind    | Depends On | Title                     | Description          |
    |----|------|---------|------------|---------------------------|----------------------|
    | ⬜ | T001 | chore   | —          | Sharpen the shears        | a \\| b and `c \\| d`  |
    | done | T002 | Feature | T001     | Prune the apple trees     | keep  spacing        |
    | ✅ | T003 | bug     | —          | Fix ladder \\| rung        |                      |

    Closing prose.
    """
)


def test_only_converted_lines_change(repo, capsys):
    repo.write("TODO.md", PRESERVED)
    code, result, err = import_json(repo, "--write", capsys=capsys)
    assert code == 0, err
    after = read(repo)
    changed = changed_lines(PRESERVED, after)
    assert [line for line in changed if line.startswith("-")] == [
        "-## Pruning",
        "-| done | T002 | Feature | T001     | Prune the apple trees     | keep  spacing        |",
    ]
    added = [line[1:] for line in changed if line.startswith("+")]
    assert "## E01 — Pruning" in added
    assert "## Epics" in added
    new_row = next(line for line in added if "T002" in line)
    assert split_row(new_row) == ["✅", "T002", "feature", "T001", "Prune the apple trees", "keep  spacing"]
    assert "| keep  spacing        |" in new_row
    assert "| ⬜ | T001 | chore   | —          | Sharpen the shears        | a \\| b and `c \\| d`  |" in after
    assert "| ✅ | T003 | bug     | —          | Fix ladder \\| rung        |                      |" in after
    assert result["tables_skipped"] == [{"line": 8, "reason": "an ID column but no status column"}]
    assert repo.codes() == []


def test_crlf_line_endings_are_kept(repo, capsys):
    (repo.root / "TODO.md").write_bytes(TWO_SECTIONS.replace("\n", "\r\n").encode("utf-8"))
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), *MAP_FLAGS, "--write", capsys=capsys)
    assert code == 0, err
    data = (repo.root / "TODO.md").read_bytes().decode("utf-8")
    assert data.count("\n") == data.count("\r\n")
    assert "Some prose about watering.\r\n" in data
    assert repo.codes() == []


# 3. Dry run by default


def test_dry_run_writes_nothing_and_prints_the_content(repo, capsys):
    repo.write("TODO.md", TWO_SECTIONS)
    code, out, err = run(repo.root, "import", str(repo.root / "TODO.md"), *MAP_FLAGS, capsys=capsys)
    assert code == 0, err
    assert read(repo) == TWO_SECTIONS
    assert "--write" in err
    code, result, _ = import_json(repo, *MAP_FLAGS, capsys=capsys)
    assert code == 0
    assert result["written"] is False and result["content"] == out
    assert result["tasks"] == 3
    assert result["mapped"]["statuses"] == {"[x]": {"status": "done", "count": 1}, "[ ]": {"status": "pending", "count": 2}}
    assert result["custom_columns"] == ["Notes"]
    run(repo.root, "import", str(repo.root / "TODO.md"), *MAP_FLAGS, "--write", capsys=capsys)
    assert read(repo) == out


# 4. The epic level


NESTED = source(
    """
    # Workshop

    ## Backlog

    ### Tools

    | ✓  | ID   | Kind  | Depends On | Title         |
    |----|------|-------|------------|---------------|
    | ⬜ | T001 | chore | —          | Oil the lathe |

    ### Ideas

    Maybe a new bench.

    ### Wood

    | ✓  | ID   | Kind    | Depends On | Title          |
    |----|------|---------|------------|----------------|
    | ⬜ | T002 | feature | T001       | Dry the planks |

    ## Archive

    Nothing here.
    """
)


def test_default_epic_level_is_the_shallowest_nearest_heading(repo, capsys):
    repo.write("TODO.md", NESTED)
    code, result, err = import_json(repo, "--write", capsys=capsys)
    assert code == 0, err
    assert result["epic_level"] == 3
    assert [(e["id"], e["name"], e["tasks"]) for e in result["epics"]] == [("E01", "Tools", 1), ("E02", "Wood", 1)]
    after = read(repo)
    for kept in ("## Backlog", "### Ideas", "## Archive", "Maybe a new bench."):
        assert kept in after.splitlines()
    assert repo.codes() == []


SUBSECTIONS = source(
    """
    # Workshop

    ## Tools

    ### Pending

    | ✓  | ID   | Kind  | Depends On | Title         |
    |----|------|-------|------------|---------------|
    | ⬜ | T001 | chore | —          | Oil the lathe |

    ### Done

    | ✓  | ID   | Kind  | Depends On | Title        |
    |----|------|-------|------------|--------------|
    | ✅ | T002 | chore | —          | Fix the vise |
    """
)


def test_epic_level_groups_subsections_under_their_heading(repo, capsys):
    repo.write("TODO.md", SUBSECTIONS)
    code, result, _ = import_json(repo, capsys=capsys)
    assert code == 0
    assert [e["name"] for e in result["epics"]] == ["Pending", "Done"]
    code, result, err = import_json(repo, "--epic-level", "2", "--write", capsys=capsys)
    assert code == 0, err
    assert [(e["id"], e["name"], e["tasks"]) for e in result["epics"]] == [("E01", "Tools", 2)]
    lines = read(repo).splitlines()
    assert "### Pending" in lines and "### Done" in lines
    assert repo.codes() == []


# 5. The fallback epic


HEADINGLESS = source(
    """
    # Herb garden

    A short list of chores.

    | ✓  | ID   | Kind  | Depends On | Title          |
    |----|------|-------|------------|----------------|
    | ⬜ | T001 | chore | —          | Water the mint |
    """
)


def test_tables_without_a_heading_form_a_fallback_epic(repo, capsys):
    repo.write("TODO.md", HEADINGLESS)
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), "--write", capsys=capsys)
    assert code == 0, err
    assert read(repo) == source(
        """
        # Herb garden

        A short list of chores.

        ## Epics

        | ID  | Epic    | Objective | File |
        |-----|---------|-----------|------|
        | E01 | Backlog | —         | —    |

        ## E01 — Backlog

        | ✓  | ID   | Kind  | Depends On | Title          |
        |----|------|-------|------------|----------------|
        | ⬜ | T001 | chore | —          | Water the mint |
        """
    )
    assert repo.codes() == []


def test_epic_name_names_the_fallback_epic(repo, capsys):
    repo.write("TODO.md", HEADINGLESS)
    code, result, _ = import_json(repo, "--epic-name", "Herbs | pots", capsys=capsys)
    assert code == 0
    assert result["epics"][0]["name"] == "Herbs | pots"
    assert "## E01 — Herbs | pots" in result["content"]
    assert "| E01 | Herbs \\| pots |" in result["content"]


# 6. Headings shaped like an epic keep their ID


def test_a_heading_shaped_like_an_epic_keeps_its_id(repo, capsys):
    repo.write(
        "TODO.md",
        source(
            """
            ### E07 — Watering

            | ✓  | ID   | Kind  | Depends On | Title          |
            |----|------|-------|------------|----------------|
            | ⬜ | T001 | chore | —          | Water the mint |

            ### Planting

            | ✓  | ID   | Kind  | Depends On | Title          |
            |----|------|-------|------------|----------------|
            | ⬜ | T002 | chore | —          | Plant the sage |
            """
        ),
    )
    code, result, err = import_json(repo, "--write", capsys=capsys)
    assert code == 0, err
    assert [(e["id"], e["name"]) for e in result["epics"]] == [("E07", "Watering"), ("E01", "Planting")]
    assert "## E07 — Watering" in read(repo).splitlines()
    assert repo.codes() == []


# 7. Mapping statuses, kinds and dependencies; inserted columns


def test_statuses_kinds_and_dependencies_are_mapped(repo, capsys):
    repo.write(
        "TODO.md",
        source(
            """
            ## Tools

            | Status    | ID   | Type      | Depends On | Title          |
            |-----------|------|-----------|------------|----------------|
            | todo      | T001 | Bug       | —          | Oil the lathe  |
            | DONE      | T002 | tech debt | T001       | Fix the vise   |
            | cancelled | T003 |           |            | Sweep the shop |
            | wip       | T004 | feature   | T001;T002  | Build a bench  |
            | [X]       | T005 | chore     | T001 T002  | Sort the nails |
            | open      | T006 | bug       | -          | Mend the door  |
            """
        ),
    )
    code, result, err = import_json(
        repo, *MAP_FLAGS, "--status", "wip=pending", "--kind", "tech debt=chore", "--default-kind", "feature",
        "--write", capsys=capsys,
    )
    assert code == 0, err
    project, issues = repo.load()
    assert issues == []
    assert [(t.id, t.status_raw, t.kind, t.depends_on) for t in project.tasks] == [
        ("T001", "⬜", "bug", []),
        ("T002", "✅", "chore", ["T001"]),
        ("T003", "❌", "feature", []),
        ("T004", "⬜", "feature", ["T001", "T002"]),
        ("T005", "✅", "chore", ["T001", "T002"]),
        ("T006", "⬜", "bug", []),
    ]
    after = read(repo)
    assert row(after, "T003")[3] == "—" and row(after, "T004")[3] == "T001, T002" and row(after, "T006")[3] == "—"
    assert result["mapped"]["kinds"]["tech debt"] == {"kind": "chore", "count": 1}
    assert result["mapped"]["default_kind"] == {"kind": "feature", "count": 1}


def test_missing_kind_and_depends_on_columns_are_inserted_after_id(repo, capsys):
    repo.write(
        "TODO.md",
        source(
            """
            ## Tools

            | Status | ID   | Title         |
            |--------|------|---------------|
            | [ ]    | T001 | Oil the lathe |
            | [x]    | T002 | Fix the vise  |
            """
        ),
    )
    code, _, err = run(
        repo.root, "import", str(repo.root / "TODO.md"), "--column", "✓=Status", "--default-kind", "chore", "--write",
        capsys=capsys,
    )
    assert code == 0, err
    after = read(repo)
    header = next(line for line in after.splitlines() if line.startswith("| ✓"))
    assert split_row(header) == ["✓", "ID", "Kind", "Depends On", "Title"]
    assert row(after, "T001") == ["⬜", "T001", "chore", "—", "Oil the lathe"]
    assert row(after, "T002") == ["✅", "T002", "chore", "—", "Fix the vise"]
    assert repo.codes() == []


# 8. Unmapped values are reported together


UNMAPPED = source(
    """
    ## Tools

    | Status  | ID   | Kind  | Depends On | Title         |
    |---------|------|-------|------------|---------------|
    | wip     | T001 | chore | —          | Oil the lathe |
    | wip     | T002 | story | see above  | Fix the vise  |
    | blocked | T003 | chore | —          |               |
    | ⬜      | T004 | chore | —          |

    ## Wood

    | ✓  | ID   | Title          |
    |----|------|----------------|
    | ⬜ | T005 | Dry the planks |
    """
)


def test_unmapped_values_are_reported_together_and_nothing_is_written(repo, capsys):
    repo.write("TODO.md", UNMAPPED)
    code, result, err = import_json(repo, "--column", "✓=Status", "--write", capsys=capsys)
    assert code == 5
    assert read(repo) == UNMAPPED
    problems = {(p["code"], p.get("value")): p for p in result["problems"]}
    assert problems[("status-unmapped", "wip")]["count"] == 2
    assert problems[("status-unmapped", "wip")]["lines"] == [5, 6]
    assert problems[("status-unmapped", "blocked")]["lines"] == [7]
    assert problems[("kind-unmapped", "story")]["lines"] == [6]
    assert problems[("depends-unmapped", "see above")]["lines"] == [6]
    assert problems[("title-empty", None)]["lines"] == [7]
    assert problems[("row-cells", None)]["lines"] == [8]
    assert problems[("kind-missing", None)]["lines"] == [12]
    code, out, err = run(repo.root, "import", str(repo.root / "TODO.md"), "--column", "✓=Status", capsys=capsys)
    assert code == 5 and out == ""
    assert "wip" in err and "--status" in err and "--default-kind" in err
    assert "[task-status]" not in err  # a refused conversion is not validated
    assert result["issues"] == []


# 9. IDs are kept and checked


@pytest.mark.parametrize(("first", "second", "code", "hint"), [
    ("T1", "T002", "id-format", "id_digits"),
    ("BUG-3", "T002", "id-format", "`T`"),
    ("T002", "T002", "id-duplicate", "T002"),
])
def test_ids_must_match_the_prefix_and_be_unique(repo, capsys, first, second, code, hint):
    text = HEADINGLESS.replace("| ⬜ | T001 | chore | —          | Water the mint |", (
        f"| ⬜ | {first} | chore | —          | Water the mint |\n| ⬜ | {second} | chore | —          | Sow basil |"
    ))
    repo.write("TODO.md", text)
    exit_code, result, _ = import_json(repo, "--write", capsys=capsys)
    assert exit_code == 5
    matching = [p for p in result["problems"] if p["code"] == code]
    assert matching and hint in matching[0]["message"]
    assert read(repo) == text


# 10. A result that fails validation


def test_a_result_that_fails_validation_exits_1(repo, capsys):
    text = HEADINGLESS.replace("| chore | —          | Water", "| chore | T099       | Water")
    repo.write("TODO.md", text)
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), "--write", capsys=capsys)
    assert code == 1
    assert "depends-unknown" in err
    assert read(repo) == text


# 11. Running it twice


def test_an_in_place_import_run_twice_changes_nothing_the_second_time(repo, capsys):
    repo.write("TODO.md", TWO_SECTIONS)
    assert run(repo.root, "import", str(repo.root / "TODO.md"), *MAP_FLAGS, "--write", capsys=capsys)[0] == 0
    first = read(repo)
    code, result, err = import_json(repo, *MAP_FLAGS, "--write", capsys=capsys)
    assert code == 0, err
    assert (result["written"], result["unchanged"]) == (False, True)
    assert read(repo) == first


def test_importing_into_the_seeded_backlog_twice(git_repo, capsys):
    repo = git_repo
    repo.write("TODO.md", DEFAULT_TODO)
    repo.write("BACKLOG.md", TWO_SECTIONS)
    code, result, err = import_json(repo, *MAP_FLAGS, "--write", capsys=capsys, file="BACKLOG.md")
    assert code == 0, err
    assert (result["source"], result["target"], result["written"]) == ("BACKLOG.md", "TODO.md", True)
    assert read(repo, "BACKLOG.md") == TWO_SECTIONS
    imported = read(repo)
    assert repo.codes() == []
    code, result, _ = import_json(repo, *MAP_FLAGS, "--write", capsys=capsys, file="BACKLOG.md")
    assert (code, result["unchanged"]) == (0, True)
    assert run(repo.root, "new", "--epic", "E02", "--kind", "chore", "--title", "Extra", capsys=capsys)[0] == 0
    changed = read(repo)
    code, result, _ = import_json(repo, *MAP_FLAGS, "--write", capsys=capsys, file="BACKLOG.md")
    assert code == 5
    assert [p["code"] for p in result["problems"]] == ["target-not-empty"]
    assert read(repo) == changed != imported


def test_importing_the_output_again_is_a_no_op(repo, capsys):
    repo.write("TODO.md", DEFAULT_TODO)
    repo.write("BACKLOG.md", PRESERVED)
    code, out, _ = run(repo.root, "import", str(repo.root / "BACKLOG.md"), capsys=capsys)
    assert code == 0
    repo.write("OUTPUT.md", out)
    code, result, err = import_json(repo, capsys=capsys, file="OUTPUT.md")
    assert code == 0, err
    assert result["content"] == out


def test_a_source_with_an_invalid_epics_section_is_refused(repo, capsys):
    text = "## Epics\n\n| ID  | Epic |\n|-----|------|\n| E01 | Tools |\n"
    repo.write("TODO.md", text)
    code, result, _ = import_json(repo, "--write", capsys=capsys)
    assert code == 5
    assert [p["code"] for p in result["problems"]] == ["epics-invalid"]
    assert read(repo) == text


# 12. IDs and reserve-id


def test_reserve_id_counts_the_imported_ids(git_repo, capsys):
    git_repo.write("TODO.md", HEADINGLESS.replace("T001", "T010"))
    assert run(git_repo.root, "import", str(git_repo.root / "TODO.md"), "--write", capsys=capsys)[0] == 0
    code, out, _ = run(git_repo.root, "reserve-id", capsys=capsys)
    assert (code, out.strip()) == (0, "T011")


def test_a_reserved_id_refuses_the_import(git_repo, capsys):
    git_repo.write("TODO.md", TWO_SECTIONS.replace("T003", "T004"))
    code, out, _ = run(git_repo.root, "reserve-id", "--owner", "alice@example", capsys=capsys)
    assert (code, out.strip()) == (0, "T004")
    before = read(git_repo)
    code, _, err = run(git_repo.root, "import", str(git_repo.root / "TODO.md"), *MAP_FLAGS, "--write", capsys=capsys)
    assert code == 4
    assert "T004" in err and "alice@example" in err
    assert read(git_repo) == before


# 13. Usage errors


@pytest.mark.parametrize("argv", [
    ("--column", "Priority=Prio"),
    ("--column", "Title"),
    ("--status", "wip=started"),
    ("--kind", "tech debt=story"),
    ("--default-kind", "story"),
    ("--epic-level", "1"),
    ("--epic-level", "7"),
])
def test_usage_errors_exit_2(repo, capsys, argv):
    repo.write("TODO.md", TWO_SECTIONS)
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), *argv, capsys=capsys)
    assert code == 2 and err
    assert read(repo) == TWO_SECTIONS


def test_a_missing_source_exits_2(repo, capsys):
    code, _, err = run(repo.root, "import", str(repo.root / "NOPE.md"), capsys=capsys)
    assert code == 2 and "NOPE.md" in err


def test_several_backlogs_need_backlog(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[[backlog]]\nname = "ops"\nprefix = "OPS"\nfile = "OPS.md"\n')
    repo.write("SOURCE.md", HEADINGLESS)
    code, _, err = run(repo.root, "import", str(repo.root / "SOURCE.md"), capsys=capsys)
    assert code == 2 and "--backlog" in err
    code, result, err = import_json(repo, "--backlog", "main", capsys=capsys, file="SOURCE.md")
    assert code == 0, err
    assert result["backlog"] == "main"


# 14. Column aliases


def test_configured_aliases_name_the_headers(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = ["Notes"]\naliases = { "✓" = "Status", Kind = "Type" }'))
    repo.write("TODO.md", TWO_SECTIONS.replace("| Status |", "| State  |", 1))
    code, _, err = run(repo.root, "import", str(repo.root / "TODO.md"), "--column", "✓=State", "--write", capsys=capsys)
    assert code == 0, err
    headers = [split_row(line) for line in read(repo).splitlines() if "| ID   |" in line]
    assert headers == [["Status", "ID", "Type", "Depends On", "Title", "Notes"]] * 2
    assert repo.load()[1] == []
