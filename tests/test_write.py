import difflib
import json

import pytest

from conftest import BASE_CONFIG, BASE_TODO, git

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


@pytest.mark.parametrize(
    ("pair", "core", "hint"),
    [
        ("✓=✅", "✓", "taskrail sets it"),
        ("ID=T9", "ID", "taskrail sets it"),
        ("Kind=feature", "Kind", "set it with --kind"),
        ("Depends On=T001", "Depends On", "set it with --depends-on"),
        ("Title=Other", "Title", "set it with --title"),
        ("Pts=3", "Pts", "set it with --pts"),
        ("Description=Other", "Description", "set it with --description"),
        ("id=T9", "ID", "taskrail sets it"),
        (" kind =feature", "Kind", "set it with --kind"),
    ],
)
def test_new_refuses_column_for_a_core_column_and_names_the_flag(git_repo, capsys, pair, core, hint):
    before = todo(git_repo)
    code, out, err = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "X", "--pts", "5", "--column", pair,
        capsys=capsys,
    )
    assert (code, out) == (2, "")
    assert err.strip() == f"taskrail: --column cannot set core column {core}; {hint}"
    assert todo(git_repo) == before
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_new_still_fills_a_custom_column(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = ["Owner"]'))
    table = BASE_TODO[BASE_TODO.index("| ✓"):]
    git_repo.write(
        "TODO.md",
        BASE_TODO[: BASE_TODO.index("| ✓")]
        + "".join(
            line + (" Owner |\n" if i == 0 else "-------|\n" if i == 1 else " —     |\n")
            for i, line in enumerate(table.splitlines())
        ),
    )
    git(git_repo.root, "commit", "-q", "-am", "add Owner")
    code, out, err = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "bug", "--title", "X", "--column", "Owner=api", capsys=capsys
    )
    assert (code, out.strip()) == (0, "T004"), err
    row = next(line for line in todo(git_repo).splitlines() if "| T004 |" in line)
    assert row.rstrip().endswith("| api   |")


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


def test_reopen_changes_only_the_status_cell_and_suggests_a_commit_message(git_repo, capsys):
    before = todo(git_repo)
    code, out, _ = run(git_repo.root, "reopen", "T001", "--reason", "Prices were never loaded", "--json", capsys=capsys)
    assert code == 0
    assert changed_lines(before, todo(git_repo)) == [
        "-| ✅ | T001 | chore   | 2   | —          | Price table    | Base prices |",
        "+| ⬜ | T001 | chore   | 2   | —          | Price table    | Base prices |",
    ]
    result = json.loads(out)
    assert (result["id"], result["status"], result["reason"]) == ("T001", "pending", "Prices were never loaded")
    assert result["commit_message"] == "Reopen T001: Price table\n\nPrices were never loaded\n\nReopens: T001\n"


def test_reopen_prints_the_suggested_message_in_text_output(git_repo, capsys):
    code, out, _ = run(git_repo.root, "reopen", "T001", "--reason", "Prices were never loaded", capsys=capsys)
    assert code == 0
    assert out.startswith("T001 pending\n")
    assert out.endswith("\nReopen T001: Price table\n\nPrices were never loaded\n\nReopens: T001\n")


def test_reopen_accepts_a_discarded_task(git_repo, capsys):
    run(git_repo.root, "discard", "T003", capsys=capsys)
    assert run(git_repo.root, "reopen", "T003", "--reason", "Still reproducible", capsys=capsys)[0] == 0
    assert "| ⬜ | T003 |" in todo(git_repo)


def test_reopen_refuses_a_pending_task(git_repo, capsys):
    before = todo(git_repo)
    code, _, err = run(git_repo.root, "reopen", "T002", "--reason", "x", capsys=capsys)
    assert code == 5
    assert "already pending" in err
    assert todo(git_repo) == before


def test_reopen_refuses_an_unknown_task(git_repo, capsys):
    assert run(git_repo.root, "reopen", "T009", "--reason", "x", capsys=capsys)[0] == 3


def test_reopen_requires_a_reason(git_repo, capsys):
    before = todo(git_repo)
    with pytest.raises(SystemExit) as missing:
        run(git_repo.root, "reopen", "T001", capsys=capsys)
    assert missing.value.code == 2
    code, _, err = run(git_repo.root, "reopen", "T001", "--reason", "  ", capsys=capsys)
    assert code == 2
    assert "--reason" in err
    assert todo(git_repo) == before


def test_reopen_refuses_an_invalid_backlog(git_repo, capsys):
    git_repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |"))
    assert run(git_repo.root, "reopen", "T001", "--reason", "x", capsys=capsys)[0] == 1


def test_reopen_lists_dependents_that_are_done_or_claimed(git_repo, capsys):
    run(git_repo.root, "done", "T002", "--force", capsys=capsys)
    run(git_repo.root, "claim", "T003", "--owner", "alice", capsys=capsys)
    code, out, _ = run(git_repo.root, "reopen", "T002", "--reason", "Wrong totals", "--json", capsys=capsys)
    assert code == 0
    assert json.loads(out)["dependents"] == [{"id": "T003", "state": "claimed"}]
    assert json.loads(run(git_repo.root, "reopen", "T001", "--reason", "x", "--json", capsys=capsys)[1])["dependents"] == []


def test_reopen_reports_done_dependents_in_text(git_repo, capsys):
    run(git_repo.root, "done", "T002", "--force", capsys=capsys)
    code, out, _ = run(git_repo.root, "reopen", "T001", "--reason", "Prices were never loaded", capsys=capsys)
    assert code == 0
    assert "T002 depends on T001 and is done" in out


def test_a_reopened_task_can_be_claimed_again(git_repo, capsys):
    run(git_repo.root, "reopen", "T001", "--reason", "Prices were never loaded", capsys=capsys)
    assert json.loads(run(git_repo.root, "show", "T001", "--json", capsys=capsys)[1])["state"] == "pending"
    assert run(git_repo.root, "claim", "T001", "--owner", "alice", capsys=capsys)[0] == 0
