from conftest import BASE_TODO

TWO_BACKLOGS = """
[[backlog]]
name = "template"
prefix = "T"
file = "TODO.md"

[[backlog]]
name = "product"
prefix = "A"
file = "APP_TODO.md"
mainline = "dev"
may_depend_on = ["template"]
"""

APP_TODO = """
# APP TODO

## Epics

| ID  | Epic  | Objective |
|-----|-------|-----------|
| E01 | Users | Accounts  |

## E01 — Users

| ✓  | ID   | Kind  | Depends On | Title   |
|----|------|-------|------------|---------|
| ⬜ | A001 | chore | T001       | Sign-up |
"""


def test_product_may_depend_on_template(repo):
    repo.write(".taskrail/config.toml", TWO_BACKLOGS)
    repo.write("APP_TODO.md", APP_TODO)
    project, issues = repo.load()
    assert [i for i in issues if i.severity == "error"] == []
    assert project.task("A001").backlog == "product"


def test_template_may_not_depend_on_product(repo):
    repo.write(".taskrail/config.toml", TWO_BACKLOGS)
    repo.write("APP_TODO.md", APP_TODO)
    repo.write("TODO.md", BASE_TODO.replace("| —          | Price", "| A001       | Price"))
    assert "depends-direction" in repo.codes()


def test_task_id_must_use_its_backlog_prefix(repo):
    repo.write(".taskrail/config.toml", TWO_BACKLOGS)
    repo.write("APP_TODO.md", APP_TODO.replace("A001", "T004"))
    assert "task-id" in repo.codes()
