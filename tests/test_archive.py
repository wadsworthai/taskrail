"""`taskrail archive`: moving closed tasks and closed epics into the backlog's archive (DESIGN.md §7.6)."""

import json

import pytest

from conftest import BASE_CONFIG, git

from taskrail.cli import main

TODO = """
# TODO

## Epics

| ID  | Epic    | Objective       | File |
|-----|---------|-----------------|------|
| E01 | Billing | Charge properly | —    |
| E02 | Auth    | Sign in         | —    |

## E01 — Billing

Done when: every session has a cost.

| ✓  | ID   | Kind    | Pts | Depends On | Title          | Description |
|----|------|---------|-----|------------|----------------|-------------|
| ✅ | T001 | chore   | 2   | —          | Price table    | Base prices |
| ❌ | T002 | feature | 3   | T001       | Repricing      | Dropped     |
| ⬜ | T003 | bug     | 1   | T004       | Rounding error | Off by one  |
| ✅ | T004 | chore   | 1   | —          | Kept by T003   | Depended on |

## E02 — Auth

Done when: passwords are gone.

| ✓  | ID   | Kind  | Pts | Depends On | Title      | Description |
|----|------|-------|-----|------------|------------|-------------|
| ✅ | T005 | chore | 1   | —          | Magic link | Sent        |
| ❌ | T006 | bug   | 1   | —          | Cookie bug | Dropped     |
"""


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def archived(root, *argv, capsys) -> dict:
    code, out, err = run(root, "archive", *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def text(root, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


@pytest.fixture
def backlog(repo):
    repo.write("TODO.md", TODO)
    return repo


def test_closed_rows_move_into_the_archive_and_the_backlog_stays_valid(backlog, capsys):
    result = archived(backlog.root, capsys=capsys)

    assert result["backlogs"][0]["archived"] == ["T001", "T002", "T005", "T006"]
    assert result["backlogs"][0]["archive"] == "docs/archive.md"
    todo = text(backlog.root, "TODO.md")
    assert "T001" not in todo and "T002" not in todo
    assert "| ⬜ | T003" in todo and "| ✅ | T004" in todo

    archive = text(backlog.root, "docs/archive.md")
    assert "| ✅ | T001 | chore   | 2   | —          | Price table    | Base prices |" in archive
    assert "| ❌ | T002 | feature | 3   | T001       | Repricing      | Dropped     |" in archive
    assert run(backlog.root, "validate", capsys=capsys)[0] == 0


def test_a_discarded_row_archives_exactly_like_a_done_row(backlog, capsys):
    """The row's words: completed *and discarded*. Both closed states are treated the same."""
    result = archived(backlog.root, capsys=capsys)
    moved = result["backlogs"][0]["archived"]
    assert "T002" in moved and "T006" in moved  # ❌ rows
    assert "T001" in moved and "T005" in moved  # ✅ rows
    archive = text(backlog.root, "docs/archive.md")
    assert archive.count("| ❌ |") == 2 and archive.count("| ✅ |") == 2
    assert "❌" not in text(backlog.root, "TODO.md")


def test_a_row_a_remaining_row_depends_on_is_held_back_and_named(backlog, capsys):
    code, out, _ = run(backlog.root, "archive", capsys=capsys)
    assert code == 0
    assert "held back T004: T003 depends on it" in out

    result = archived(backlog.root, capsys=capsys)  # the second run has nothing left to move
    assert result["backlogs"][0]["archived"] == []
    assert result["backlogs"][0]["held_back"] == [{"id": "T004", "depended_on_by": ["T003"], "reason": "T003 depends on it"}]
    assert "| ✅ | T004" in text(backlog.root, "TODO.md")


def test_a_chain_of_closed_rows_behind_a_held_back_one_stays_whole(repo, capsys):
    """T007 is closed but held by open T008; T006, which T007 depends on, must stay too."""
    repo.write("TODO.md", """
        # TODO

        ## Epics

        | ID  | Epic    | Objective       | File |
        |-----|---------|-----------------|------|
        | E01 | Billing | Charge properly | —    |

        ## E01 — Billing

        | ✓  | ID   | Kind  | Pts | Depends On | Title | Description |
        |----|------|-------|-----|------------|-------|-------------|
        | ✅ | T006 | chore | 1   | —          | Deep  | Bottom      |
        | ✅ | T007 | chore | 1   | T006       | Mid   | Middle      |
        | ⬜ | T008 | chore | 1   | T007       | Open  | Top         |
        """)
    result = archived(repo.root, capsys=capsys)
    assert result["backlogs"][0]["archived"] == []
    assert [held["id"] for held in result["backlogs"][0]["held_back"]] == ["T006", "T007"]
    assert not (repo.root / "docs/archive.md").exists()


def test_a_fully_closed_epic_loses_its_listing_row_and_section(backlog, capsys):
    result = archived(backlog.root, capsys=capsys)
    assert result["backlogs"][0]["epics"] == ["E02"]

    todo = text(backlog.root, "TODO.md")
    assert "## E02 — Auth" not in todo
    assert "| E02 |" not in todo
    assert "| E01 |" in todo and "## E01 — Billing" in todo

    archive = text(backlog.root, "docs/archive.md")
    assert "## E02 — Auth" in archive
    assert "Objective: Sign in" in archive
    assert "Done when: passwords are gone." in archive
    assert run(backlog.root, "validate", capsys=capsys)[0] == 0


def test_an_epic_that_keeps_a_row_keeps_its_heading_and_table(backlog, capsys):
    archived(backlog.root, capsys=capsys)
    todo = text(backlog.root, "TODO.md")
    assert "## E01 — Billing" in todo
    assert "Done when: every session has a cost." in todo
    assert "| ✓  | ID   | Kind    | Pts | Depends On | Title          | Description |" in todo
    # E01 is not archived whole, so the archive carries its rows but not its objective.
    archive = text(backlog.root, "docs/archive.md")
    assert "## E01 — Billing" in archive
    assert "Objective: Charge properly" not in archive


def test_an_epic_in_its_own_file_is_archived_with_its_file(repo, capsys):
    repo.write("TODO.md", """
        # TODO

        ## Epics

        | ID  | Epic    | Objective       | File                |
        |-----|---------|-----------------|---------------------|
        | E01 | Billing | Charge properly | —                   |
        | E02 | Auth    | Sign in         | todo/E02-auth.md    |

        ## E01 — Billing

        | ✓  | ID   | Kind  | Pts | Depends On | Title | Description |
        |----|------|-------|-----|------------|-------|-------------|
        | ⬜ | T001 | chore | 1   | —          | Open  | Stays       |
        """)
    repo.write("todo/E02-auth.md", """
        ## E02 — Auth

        Done when: passwords are gone.

        | ✓  | ID   | Kind  | Pts | Depends On | Title      | Description |
        |----|------|-------|-----|------------|------------|-------------|
        | ✅ | T002 | chore | 1   | —          | Magic link | Sent        |
        """)
    result = archived(repo.root, capsys=capsys)
    assert result["backlogs"][0]["epics"] == ["E02"]
    assert result["removed"] == ["todo/E02-auth.md"]
    assert not (repo.root / "todo/E02-auth.md").exists()
    assert "todo/E02-auth.md" not in text(repo.root, "TODO.md")
    assert "| ✅ | T002" in text(repo.root, "docs/archive.md")
    assert run(repo.root, "validate", capsys=capsys)[0] == 0


def test_the_archive_is_created_once_and_a_second_run_appends_to_its_section(backlog, capsys):
    archived(backlog.root, capsys=capsys)
    first = text(backlog.root, "docs/archive.md")
    assert first.startswith("# Archive — main\n")

    run(backlog.root, "done", "T003", "--force", capsys=capsys)  # T004 is free once T003 closes
    result = archived(backlog.root, capsys=capsys)
    assert result["backlogs"][0]["archived"] == ["T003", "T004"]
    archive = text(backlog.root, "docs/archive.md")
    assert archive.count("# Archive — main") == 1
    assert archive.count("## E01 — Billing") == 1
    assert archive.index("| ✅ | T001") < archive.index("| ✅ | T003") < archive.index("| ✅ | T004")
    # E01 archives whole on this run, so its objective and Done when join the section it already had.
    assert result["backlogs"][0]["epics"] == ["E01"]
    assert "Objective: Charge properly" in archive
    assert "Done when: every session has a cost." in archive
    # Every epic is archived now: the backlog keeps its `## Epics` table with no rows, and validates.
    todo = text(backlog.root, "TODO.md")
    assert "## Epics" in todo and "| E01 |" not in todo and "| E02 |" not in todo
    assert run(backlog.root, "validate", capsys=capsys)[0] == 0


def test_the_archived_table_keeps_aliases_and_custom_columns(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace("[columns]\ncustom = []", '[columns]\ncustom = ["Owner"]\naliases = { Pts = "Size" }'))
    repo.write("TODO.md", """
        # TODO

        ## Epics

        | ID  | Epic    | Objective       | File |
        |-----|---------|-----------------|------|
        | E01 | Billing | Charge properly | —    |

        ## E01 — Billing

        | ✓  | ID   | Kind  | Size | Depends On | Title | Description | Owner |
        |----|------|-------|------|------------|-------|-------------|-------|
        | ✅ | T001 | chore | 2    | —          | Done  | Finished    | api   |
        | ⬜ | T002 | chore | 1    | —          | Open  | Stays       | web   |
        """)
    archived(repo.root, capsys=capsys)
    archive = text(repo.root, "docs/archive.md")
    assert "| ✓  | ID   | Kind  | Size | Depends On | Title | Description | Owner |" in archive
    assert "| ✅ | T001 | chore | 2    | —          | Done  | Finished    | api   |" in archive


def test_dry_run_writes_nothing_and_reports_what_would_move(backlog, capsys):
    before = text(backlog.root, "TODO.md")
    code, out, _ = run(backlog.root, "archive", "--dry-run", capsys=capsys)
    assert code == 0
    assert "would archive" in out and "held back T004: T003 depends on it" in out
    assert text(backlog.root, "TODO.md") == before
    assert not (backlog.root / "docs/archive.md").exists()

    result = archived(backlog.root, "--dry-run", capsys=capsys)
    assert result["dry_run"] is True
    assert result["files"] == [] and result["removed"] == []
    assert result["backlogs"][0]["archived"] == ["T001", "T002", "T005", "T006"]
    assert result["backlogs"][0]["epics"] == ["E02"]


def test_nothing_to_archive_is_reported_and_writes_nothing(backlog, capsys):
    code, out, _ = run(backlog.root, "archive", capsys=capsys)
    assert code == 0 and "archived 4 task(s) and 1 epic(s)" in out
    before = text(backlog.root, "docs/archive.md")
    code, out, _ = run(backlog.root, "archive", capsys=capsys)
    assert code == 0 and "nothing to archive" in out
    assert text(backlog.root, "docs/archive.md") == before


def test_backlog_selects_one_backlog_and_an_unknown_name_is_usage(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG + """
[[backlog]]
name = "product"
prefix = "A"
file = "APP_TODO.md"
artifacts = "appdocs"
""")
    repo.write("APP_TODO.md", """
        # App

        ## Epics

        | ID  | Epic | Objective | File |
        |-----|------|-----------|------|
        | E09 | Shop | Sell      | —    |

        ## E09 — Shop

        | ✓  | ID   | Kind  | Pts | Depends On | Title | Description |
        |----|------|-------|-----|------------|-------|-------------|
        | ✅ | A001 | chore | 1   | —          | Done  | Finished    |
        """)
    result = archived(repo.root, "--backlog", "product", capsys=capsys)
    assert [entry["backlog"] for entry in result["backlogs"]] == ["product"]
    assert (repo.root / "appdocs/archive.md").exists()
    assert not (repo.root / "docs/archive.md").exists()
    assert "T001" in text(repo.root, "TODO.md")
    assert run(repo.root, "archive", "--backlog", "nope", capsys=capsys)[0] == 2


def test_the_archive_path_is_configurable(backlog, capsys):
    backlog.write(".taskrail/config.toml", BASE_CONFIG.replace('file = "TODO.md"', 'file = "TODO.md"\narchive = "docs/{backlog}/closed.md"'))
    result = archived(backlog.root, capsys=capsys)
    assert result["backlogs"][0]["archive"] == "docs/main/closed.md"
    assert (backlog.root / "docs/main/closed.md").exists()
    assert not (backlog.root / "docs/archive.md").exists()


@pytest.mark.parametrize(
    "archive, message",
    [
        ('archive = ""', "archive must not be empty"),
        ('archive = "{artifacts}/{id}.md"', "invalid template"),
    ],
)
def test_a_bad_archive_value_is_a_configuration_error(repo, capsys, archive, message):
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace('file = "TODO.md"', f'file = "TODO.md"\n{archive}'))
    code, _, err = run(repo.root, "validate", capsys=capsys)
    assert code == 2 and message in err


def test_two_backlogs_may_not_archive_into_one_file(repo, capsys):
    """Refused where the damage would be done, not at load: such a config keeps working otherwise."""
    repo.write(".taskrail/config.toml", BASE_CONFIG + """
[[backlog]]
name = "product"
prefix = "A"
file = "APP_TODO.md"
""")
    repo.write("APP_TODO.md", "# App\n\n## Epics\n\n| ID  | Epic | Objective | File |\n|-----|------|-----------|------|\n")
    assert run(repo.root, "validate", capsys=capsys)[0] == 0  # sharing an artifacts root is not an error

    code, _, err = run(repo.root, "archive", capsys=capsys)
    assert code == 2
    assert "both archive into docs/archive.md" in err

    repo.write(".taskrail/config.toml", BASE_CONFIG.replace('file = "TODO.md"', 'file = "TODO.md"\narchive = "APP_TODO.md"') + """
[[backlog]]
name = "product"
prefix = "A"
file = "APP_TODO.md"
archive = "docs/product.md"
""")
    code, _, err = run(repo.root, "archive", capsys=capsys)
    assert code == 2 and "which is backlog `product`'s file" in err


def test_archive_is_a_known_configuration_key(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace('file = "TODO.md"', 'file = "TODO.md"\narchive = "docs/archive.md"'))
    code, out, _ = run(repo.root, "validate", "--json", capsys=capsys)
    assert code == 0
    assert "config-unknown-key" not in out


def test_validate_show_and_list_ignore_the_archive(backlog, capsys):
    archived(backlog.root, capsys=capsys)
    # A row that would be invalid in a backlog: an unknown kind and a dependency on nothing.
    archive = text(backlog.root, "docs/archive.md")
    backlog.write("docs/archive.md", archive.replace("| ✅ | T001 | chore  ", "| ✅ | T001 | mystery"))
    assert run(backlog.root, "validate", capsys=capsys)[0] == 0
    assert run(backlog.root, "show", "T001", capsys=capsys)[0] == 3
    assert "T001" not in run(backlog.root, "list", capsys=capsys)[1]


def test_reopening_an_archived_task_names_the_archive(backlog, capsys):
    archived(backlog.root, capsys=capsys)
    code, _, err = run(backlog.root, "reopen", "T001", "--reason", "not finished", capsys=capsys)
    assert code == 3
    assert "T001" in err and "docs/archive.md" in err
    assert run(backlog.root, "reopen", "T999", "--reason", "x", capsys=capsys)[2].strip() == "taskrail: no task `T999`"


def allocated(root, capsys) -> str:
    code, out, err = run(root, "new", "--epic", "E01", "--kind", "chore", "--title", "Next", "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)["id"]


def test_an_archived_id_is_never_allocated_again(git_repo, capsys):
    """`ids.used_ids` must read the archive: without it `new` reissues an ID whose row has moved."""
    git_repo.write("TODO.md", TODO)
    archived(git_repo.root, capsys=capsys)  # T005 and T006 leave TODO.md, which keeps T003 and T004
    assert allocated(git_repo.root, capsys) == "T007"


def test_an_archived_id_counts_from_a_branch_that_no_longer_has_the_file(git_repo, capsys):
    """The archive is scanned on every revision too, like the backlog's own files."""
    git_repo.write("TODO.md", TODO)
    archived(git_repo.root, capsys=capsys)
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "archive")
    (git_repo.root / "docs/archive.md").unlink()  # gone from the working tree, still on refs/heads/main
    assert allocated(git_repo.root, capsys) == "T007"


def added_epic(root, capsys, *argv) -> tuple[int, str, str]:
    return run(root, "epic", "add", "--name", "Payments", "--objective", "Take money", *argv, capsys=capsys)


def test_an_archived_epic_id_is_never_allocated_again(backlog, capsys):
    """`epic add` must read the archive's epic headings: E02 is archived whole, so E03 is next (T122)."""
    archived(backlog.root, capsys=capsys)  # E02 leaves TODO.md whole; E01 stays with T003 and T004
    code, out, err = added_epic(backlog.root, capsys)
    assert (code, out.strip()) == (0, "E03"), err
    assert "| E02 |" not in text(backlog.root, "TODO.md")


def test_without_the_archive_the_same_backlog_would_reissue_the_epic_id(backlog, capsys):
    """The negative control: with the archive gone, E02 is genuinely free, so the scan is what moves it."""
    archived(backlog.root, capsys=capsys)
    (backlog.root / "docs/archive.md").unlink()
    code, out, err = added_epic(backlog.root, capsys)
    assert (code, out.strip()) == (0, "E02"), err


def test_an_archived_epic_id_is_refused_when_passed_explicitly(backlog, capsys):
    archived(backlog.root, capsys=capsys)
    before = text(backlog.root, "TODO.md")
    code, _, err = added_epic(backlog.root, capsys, "--id", "E02")
    assert code == 5
    assert "E02" in err and "docs/archive.md" in err
    assert text(backlog.root, "TODO.md") == before
