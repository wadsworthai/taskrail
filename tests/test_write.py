import difflib
import json

from conftest import BASE_TODO, git

from taskrail.cli import main
from taskrail.writer import replace_cell


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def todo(repo) -> str:
    return (repo.root / "TODO.md").read_text(encoding="utf-8")


def test_replace_cell_keeps_width_and_neighbours():
    line = "| ⬜ | T002 | feature | 3   |\n"
    assert replace_cell(line, 0, "✅") == "| ✅ | T002 | feature | 3   |\n"
    assert replace_cell("| a \\| b | c |\n", 1, "d") == "| a \\| b | d |\n"


def test_done_changes_one_cell_and_releases_the_claim(git_repo, capsys):
    before = todo(git_repo)
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    code, _, _ = run(git_repo.root, "done", "T002", "--owner", "alice", capsys=capsys)
    assert code == 0
    assert changed_lines(before, todo(git_repo)) == [
        "-| ⬜ | T002 | feature | 3   | T001       | Repricing      | Recompute   |",
        "+| ✅ | T002 | feature | 3   | T001       | Repricing      | Recompute   |",
    ]
    assert run(git_repo.root, "claims", "--json", capsys=capsys)[1].count('"id"') == 0


def test_done_requires_a_claim(git_repo, capsys):
    code, _, err = run(git_repo.root, "done", "T002", capsys=capsys)
    assert code == 5
    assert "not claimed" in err
    assert run(git_repo.root, "done", "T002", "--force", capsys=capsys)[0] == 0


def test_done_refuses_someone_elses_claim(git_repo, capsys):
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    assert run(git_repo.root, "done", "T002", "--owner", "bob", capsys=capsys)[0] == 4


def test_done_refuses_unfinished_dependencies(git_repo, capsys):
    run(git_repo.root, "claim", "T003", "--ignore-deps", "--owner", "alice", capsys=capsys)
    code, _, err = run(git_repo.root, "done", "T003", "--owner", "alice", capsys=capsys)
    assert code == 5
    assert "still depends on T002" in err


def test_discard_needs_no_claim(git_repo, capsys):
    assert run(git_repo.root, "discard", "T003", capsys=capsys)[0] == 0
    assert "| ❌ | T003 |" in todo(git_repo)
    assert run(git_repo.root, "discard", "T003", capsys=capsys)[0] == 5


def test_new_appends_an_aligned_row_with_a_reserved_id(git_repo, capsys):
    before = todo(git_repo)
    code, out, _ = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals",
        "--pts", "2", "--depends-on", "T001", "--description", "a | b", capsys=capsys,
    )
    assert (code, out.strip()) == (0, "T004")
    assert changed_lines(before, todo(git_repo)) == [
        "+| ⬜ | T004 | bug     | 2   | T001       | Negative totals | a \\| b      |"
    ]
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0


def test_new_that_would_be_invalid_writes_nothing_and_frees_the_id(git_repo, capsys):
    before = todo(git_repo)
    code, _, err = run(git_repo.root, "new", "--epic", "E01", "--kind", "story", "--title", "X", capsys=capsys)
    assert code == 1
    assert "nothing was written" in err
    assert todo(git_repo) == before
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_new_with_an_unknown_column_is_refused(git_repo, capsys):
    code, _, err = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "X", "--column", "Owner=api", capsys=capsys
    )
    assert code == 2
    assert "no column(s): Owner" in err


def test_new_refuses_an_unknown_epic(git_repo, capsys):
    assert run(git_repo.root, "new", "--epic", "E09", "--kind", "bug", "--title", "X", capsys=capsys)[0] == 3


def test_epic_add_inline_then_new_creates_its_table(git_repo, capsys):
    code, out, _ = run(
        git_repo.root, "epic", "add", "--name", "Auth", "--objective", "Sign in", "--done-when", "SSO works",
        capsys=capsys,
    )
    assert (code, out.strip()) == (0, "E02")
    assert run(git_repo.root, "new", "--epic", "E02", "--kind", "chore", "--title", "Session store", capsys=capsys)[0] == 0
    project_json = run(git_repo.root, "list", "--epic", "E02", "--json", capsys=capsys)[1]
    assert [t["id"] for t in json.loads(project_json)] == ["T004"]
    text = todo(git_repo)
    assert "| E02 | Auth" in text
    assert text.index("## E02 — Auth") > text.index("## E01 — Billing")
    assert "Done when: SSO works" in text
    assert text.endswith("|\n")


def test_epic_add_in_its_own_file(git_repo, capsys):
    code, _, _ = run(git_repo.root, "epic", "add", "--name", "Auth Flow", "--objective", "Sign in", "--own-file", capsys=capsys)
    assert code == 0
    assert (git_repo.root / "todo/E02-auth-flow.md").read_text().startswith("## E02 — Auth Flow")
    assert "| todo/E02-auth-flow.md |" in todo(git_repo)
    assert run(git_repo.root, "new", "--epic", "E02", "--kind", "bug", "--title", "X", capsys=capsys)[0] == 0
    assert "| T004 |" in (git_repo.root / "todo/E02-auth-flow.md").read_text()


def test_epic_split_moves_the_section_and_keeps_the_backlog_valid(git_repo, capsys):
    before = todo(git_repo)
    code, out, _ = run(git_repo.root, "epic", "split", "E01", capsys=capsys)
    assert code == 0
    moved = (git_repo.root / "todo/E01-billing.md").read_text()
    assert moved.startswith("## E01 — Billing")
    assert "| ✅ | T001 |" in moved
    assert "## E01" not in todo(git_repo)
    assert "todo/E01-billing.md" in todo(git_repo)
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0
    assert run(git_repo.root, "epic", "split", "E01", capsys=capsys)[0] == 5

    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    assert run(git_repo.root, "done", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    assert "| ✅ | T002 |" in (git_repo.root / "todo/E01-billing.md").read_text()
    assert todo(git_repo).count("\n\n\n") == 0 and before.count("## Epics") == 1


def test_writes_refuse_an_invalid_backlog(git_repo, capsys):
    git_repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |"))
    assert run(git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "X", capsys=capsys)[0] == 1
