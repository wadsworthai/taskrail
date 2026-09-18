from conftest import BASE_TODO


def test_valid_backlog_has_no_issues(repo):
    project, issues = repo.load()
    assert issues == []
    assert [t.id for t in project.tasks] == ["T001", "T002", "T003"]
    assert project.backlogs[0].epics[0].done_when == "every session has a cost."


def test_unknown_and_empty_kind(repo):
    repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |").replace("| chore   |", "|         |"))
    assert set(repo.codes()) == {"task-kind-unknown", "task-kind-empty"}


def test_invalid_status_and_points(repo):
    repo.write("TODO.md", BASE_TODO.replace("| ✅ | T001", "| x  | T001").replace("| 3   |", "| big |"))
    assert set(repo.codes()) == {"task-status", "task-points"}


def test_points_scale(repo):
    config = (repo.root / ".taskrail/config.toml").read_text() + "\n[points]\nscale = [1, 2, 5]\n"
    repo.write(".taskrail/config.toml", config)
    assert repo.codes() == ["task-points-scale"]


def test_duplicate_id_and_bad_format(repo):
    repo.write("TODO.md", BASE_TODO.replace("| T003 |", "| T002 |").replace("| T001 |", "| X001 |", 1))
    codes = repo.codes()
    assert "task-duplicate" in codes
    assert "task-id" in codes


def test_task_id_refusal_names_the_prefix_key(repo):
    # The refusal has to name the key that would accept the ID, not only the prefix's value.
    repo.write("TODO.md", BASE_TODO.replace("| T001 |", "| X001 |", 1))
    _, issues = repo.load()
    message = next(i.message for i in issues if i.code == "task-id")
    assert "prefix" in message


def test_epic_id_refusal_names_the_epic_prefix_key(repo):
    repo.write("TODO.md", BASE_TODO.replace("E01", "EP01"))
    _, issues = repo.load()
    message = next(i.message for i in issues if i.code == "epic-id")
    assert "epic_prefix" in message


def test_dependency_problems(repo):
    todo = BASE_TODO.replace("| T001       |", "| T999       |").replace("| T002       |", "| T003       |")
    repo.write("TODO.md", todo)
    assert sorted(repo.codes()) == ["depends-self", "depends-unknown"]


def test_cycle_is_reported_once(repo):
    repo.write("TODO.md", BASE_TODO.replace("| —          | Price", "| T003       | Price"))
    assert repo.codes().count("depends-cycle") == 1


def test_row_cell_count(repo):
    repo.write("TODO.md", BASE_TODO.replace("| Off by one  |", ""))
    assert repo.codes() == ["row-cells"]


def test_missing_required_column(repo):
    todo = BASE_TODO.replace("| Depends On |", "| Needs      |")
    repo.write("TODO.md", todo)
    assert "task-columns" in repo.codes()


def test_custom_column_must_be_declared(repo):
    todo = BASE_TODO.replace("| Description |", "| Description | Owner |").replace(
        "|-------------|", "|-------------|-------|"
    )
    for row in ("Base prices |", "Recompute   |", "Off by one  |"):
        todo = todo.replace(row, row + " api   |")
    repo.write("TODO.md", todo)
    assert repo.codes() == []
    assert repo.codes("warning") == ["column-undeclared"]


def test_task_table_outside_epic(repo):
    repo.write("TODO.md", BASE_TODO + "\n## Notes\n\n| ✓ | ID | Kind |\n|---|---|---|\n| ⬜ | T010 | bug |\n")
    assert repo.codes() == ["task-outside-epic"]


def test_epic_listed_without_section_and_unlisted_section(repo):
    todo = BASE_TODO.replace("## E01 — Billing", "## E02 — Billing")
    repo.write("TODO.md", todo)
    assert sorted(repo.codes()) == ["epic-no-section", "epic-unlisted"]


def test_epic_in_its_own_file(repo):
    listing, section = BASE_TODO.split("## E01 — Billing")
    repo.write("TODO.md", listing.replace("| —    |", "| todo/E01-billing.md |"))
    repo.write("todo/E01-billing.md", "## E01 — Billing" + section)
    project, issues = repo.load()
    assert issues == []
    assert project.tasks[0].file == "todo/E01-billing.md"


def test_epic_defined_twice(repo):
    repo.write("TODO.md", BASE_TODO.replace("| —    |", "| todo/E01.md |"))
    repo.write("todo/E01.md", "## E01 — Billing\n")
    assert "epic-both" in repo.codes()


def test_epic_file_missing(repo):
    listing = BASE_TODO.split("## E01 — Billing")[0]
    repo.write("TODO.md", listing.replace("| —    |", "| todo/nope.md |"))
    assert repo.codes() == ["epic-file-missing"]


def test_missing_epics_section(repo):
    repo.write("TODO.md", "# TODO\n")
    assert repo.codes() == ["epics-missing"]


def test_backlog_file_missing(repo):
    (repo.root / "TODO.md").unlink()
    assert repo.codes() == ["backlog-missing"]
