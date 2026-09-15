"""Editing cells of an existing task row with `taskrail edit` (T014)."""

import difflib
import json

import pytest

from conftest import BASE_CONFIG, BASE_TODO, git

from taskrail import branches
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.markdown import split_row

T002 = "T002-repricing"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def data(root, *argv, capsys):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def todo(repo, relative="TODO.md") -> str:
    return (repo.root / relative).read_text(encoding="utf-8")


def changed_lines(before: str, after: str) -> list[str]:
    return [
        line
        for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


def row(repo, task_id, relative="TODO.md") -> list[str]:
    line = next(line for line in todo(repo, relative).splitlines() if f"| {task_id} |" in line)
    return split_row(line)


def refused(repo, *argv, code, capsys) -> str:
    """Run an edit that must fail with `code` and leave the backlog untouched; return stderr."""
    before = todo(repo)
    result, out, err = run(repo.root, "edit", *argv, capsys=capsys)
    assert (result, out) == (code, ""), err
    assert todo(repo) == before
    return err


def with_owner_column(repo):
    repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = ["Owner"]'))
    table = BASE_TODO[BASE_TODO.index("| ✓"):]
    repo.write(
        "TODO.md",
        BASE_TODO[: BASE_TODO.index("| ✓")]
        + "".join(
            line + (" Owner |\n" if i == 0 else "-------|\n" if i == 1 else " —     |\n")
            for i, line in enumerate(table.splitlines())
        ),
    )
    git(repo.root, "commit", "-q", "-am", "add Owner")


# 1. Title: one cell changes


def test_title_rewrites_only_its_cell(git_repo, capsys):
    before = todo(git_repo)
    result = data(git_repo.root, "edit", "T002", "--title", "Retroactive pricing", capsys=capsys)
    assert changed_lines(before, todo(git_repo)) == [
        "-| ⬜ | T002 | feature | 3   | T001       | Repricing      | Recompute   |",
        "+| ⬜ | T002 | feature | 3   | T001       | Retroactive pricing | Recompute   |",
    ]
    assert result["id"] == "T002"
    assert result["changes"] == {"title": {"from": "Repricing", "to": "Retroactive pricing"}}
    assert result["files"] == ["TODO.md"]


def test_a_shorter_value_keeps_the_cell_width(git_repo, capsys):
    before = todo(git_repo)
    assert run(git_repo.root, "edit", "T002", "--title", "Reprice", capsys=capsys)[0] == 0
    assert changed_lines(before, todo(git_repo))[1] == (
        "+| ⬜ | T002 | feature | 3   | T001       | Reprice        | Recompute   |"
    )


def test_a_pipe_in_a_value_is_escaped(git_repo, capsys):
    assert run(git_repo.root, "edit", "T002", "--title", "A | B", capsys=capsys)[0] == 0
    assert row(git_repo, "T002")[5] == "A | B"
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0


# 2. Points


def test_points_are_set_and_cleared(git_repo, capsys):
    result = data(git_repo.root, "edit", "T002", "--pts", "5", capsys=capsys)
    assert result["changes"] == {"points": {"from": 3, "to": 5}}
    assert row(git_repo, "T002")[3] == "5"
    result = data(git_repo.root, "edit", "T002", "--pts", "", capsys=capsys)
    assert result["changes"] == {"points": {"from": 5, "to": None}}
    assert row(git_repo, "T002")[3] == "—"


def test_points_that_are_not_a_whole_number_are_a_usage_error(git_repo, capsys):
    err = refused(git_repo, "T002", "--pts", "abc", code=2, capsys=capsys)
    assert "--pts" in err


def test_points_off_the_scale_are_refused_by_validation(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG + "\n[points]\nscale = [1, 2, 3, 5]\n")
    err = refused(git_repo, "T002", "--pts", "4", code=1, capsys=capsys)
    assert "task-points-scale" in err or "not on the scale" in err
    assert "nothing was written" in err


# 3. Dependencies


def test_dependencies_are_replaced_and_cleared(git_repo, capsys):
    result = data(git_repo.root, "edit", "T003", "--depends-on", "T001,T002", capsys=capsys)
    assert result["changes"] == {"depends_on": {"from": ["T002"], "to": ["T001", "T002"]}}
    assert row(git_repo, "T003")[4] == "T001, T002"
    result = data(git_repo.root, "edit", "T003", "--depends-on", "", capsys=capsys)
    assert result["changes"] == {"depends_on": {"from": ["T001", "T002"], "to": []}}
    assert row(git_repo, "T003")[4] == "—"


@pytest.mark.parametrize(
    ("task_id", "value", "message"),
    [
        ("T002", "T099", "dependency `T099` does not exist"),
        ("T002", "T002", "depends on itself"),
        ("T002", "T001, T003", "dependency cycle"),
    ],
)
def test_invalid_dependencies_write_nothing(git_repo, capsys, task_id, value, message):
    err = refused(git_repo, task_id, "--depends-on", value, code=1, capsys=capsys)
    assert message in err


# 4. Description


def test_description_is_set_and_emptied(git_repo, capsys):
    assert data(git_repo.root, "edit", "T002", "--description", "Recompute after a price change", capsys=capsys)[
        "changes"
    ] == {"description": {"from": "Recompute", "to": "Recompute after a price change"}}
    assert row(git_repo, "T002")[6] == "Recompute after a price change"
    assert data(git_repo.root, "edit", "T002", "--description", "", capsys=capsys)["changes"] == {
        "description": {"from": "Recompute after a price change", "to": ""}
    }
    assert row(git_repo, "T002")[6] == ""


# 5. Kind


def test_kind_is_changed(git_repo, capsys):
    assert data(git_repo.root, "edit", "T002", "--kind", "bug", capsys=capsys)["changes"] == {
        "kind": {"from": "feature", "to": "bug"}
    }
    assert row(git_repo, "T002")[2] == "bug"


def test_an_undefined_kind_is_refused(git_repo, capsys):
    assert "is not defined" in refused(git_repo, "T002", "--kind", "nope", code=1, capsys=capsys)


def test_a_disallowed_kind_is_refused(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[kinds]\nallowed = ["feature", "bug", "chore"]\n')
    assert "is not allowed" in refused(git_repo, "T002", "--kind", "spike", code=1, capsys=capsys)


# 6. Custom columns and refusals


def test_a_custom_column_is_set_and_cleared(git_repo, capsys):
    with_owner_column(git_repo)
    assert data(git_repo.root, "edit", "T002", "--column", "Owner=api", capsys=capsys)["changes"] == {
        "columns": {"Owner": {"from": "—", "to": "api"}}
    }
    assert row(git_repo, "T002")[7] == "api"
    assert data(git_repo.root, "edit", "T002", "--column", "owner=", capsys=capsys)["changes"] == {
        "columns": {"Owner": {"from": "api", "to": "—"}}
    }
    assert row(git_repo, "T002")[7] == "—"


@pytest.mark.parametrize(
    ("pair", "core", "hint"),
    [
        ("✓=✅", "✓", "taskrail sets it"),
        ("ID=T9", "ID", "taskrail sets it"),
        ("kind=bug", "Kind", "set it with --kind"),
        ("Depends On=T001", "Depends On", "set it with --depends-on"),
        ("Title=Other", "Title", "set it with --title"),
        ("PTS=3", "Pts", "set it with --pts"),
        ("Description=Other", "Description", "set it with --description"),
    ],
)
def test_column_refuses_a_core_column_and_names_the_flag(git_repo, capsys, pair, core, hint):
    err = refused(git_repo, "T002", "--column", pair, code=2, capsys=capsys)
    assert err.strip() == f"taskrail: --column cannot set core column {core}; {hint}"


def test_a_column_the_table_lacks_is_refused(git_repo, capsys):
    assert "no column(s): Owner" in refused(git_repo, "T002", "--column", "Owner=api", code=2, capsys=capsys)


def test_an_optional_core_column_the_table_lacks_is_refused(git_repo, capsys):
    git_repo.write("TODO.md", BASE_TODO.replace(" Pts |", "").replace("-----|", "", 1).replace(" 2   |", "").replace(" 3   |", "").replace(" 1   |", ""))
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0
    assert "no column(s): Pts" in refused(git_repo, "T002", "--pts", "5", code=2, capsys=capsys)


def test_column_without_an_equals_sign_is_refused(git_repo, capsys):
    assert "NAME=VALUE" in refused(git_repo, "T002", "--column", "Owner", code=2, capsys=capsys)


def test_a_line_break_in_a_value_is_refused(git_repo, capsys):
    assert "line breaks" in refused(git_repo, "T002", "--title", "One\nTwo", code=2, capsys=capsys)


# 7. Aliased columns


def test_pts_writes_an_aliased_column(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = []\naliases = { Pts = "Size" }'))
    git_repo.write("TODO.md", BASE_TODO.replace("| Pts |", "| Size |").replace("|-----|------------|", "|------|------------|").replace("| 3   |", "| 3    |").replace("| 2   |", "| 2    |").replace("| 1   |", "| 1    |"))
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0
    before = todo(git_repo)
    assert data(git_repo.root, "edit", "T002", "--pts", "5", capsys=capsys)["changes"] == {"points": {"from": 3, "to": 5}}
    changed = changed_lines(before, todo(git_repo))
    assert len(changed) == 2
    assert split_row(changed[1][1:])[3] == "5"


def test_column_names_an_alias_to_refuse(git_repo, capsys):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG.replace("custom = []", 'custom = []\naliases = { Pts = "Size" }'))
    git_repo.write("TODO.md", BASE_TODO.replace("| Pts |", "| Size |"))
    err = refused(git_repo, "T002", "--column", "size=5", code=2, capsys=capsys)
    assert err.strip() == "taskrail: --column cannot set core column Pts (named `Size` here); set it with --pts"


# 8. Several flags; epic files


def test_several_flags_change_their_cells_in_one_write(git_repo, capsys):
    before = todo(git_repo)
    result = data(
        git_repo.root, "edit", "T003", "--title", "Rounding", "--pts", "2", "--depends-on", "T001", "--kind", "chore",
        "--description", "Half-up", capsys=capsys,
    )
    assert set(result["changes"]) == {"title", "points", "depends_on", "kind", "description"}
    changed = changed_lines(before, todo(git_repo))
    assert len(changed) == 2
    assert split_row(changed[1][1:]) == ["⬜", "T003", "chore", "2", "T001", "Rounding", "Half-up"]


def test_a_task_in_an_epic_file_is_edited_there(git_repo, capsys):
    assert run(git_repo.root, "epic", "split", "E01", capsys=capsys)[0] == 0
    main_before = todo(git_repo)
    result = data(git_repo.root, "edit", "T002", "--title", "Reprice", capsys=capsys)
    assert result["files"] == ["todo/E01-billing.md"]
    assert row(git_repo, "T002", "todo/E01-billing.md")[5] == "Reprice"
    assert todo(git_repo) == main_before


# 9. Nothing to change


def test_no_field_flag_is_a_usage_error(git_repo, capsys):
    assert "nothing to edit" in refused(git_repo, "T002", code=2, capsys=capsys)


def test_values_equal_to_the_current_ones_write_nothing(git_repo, capsys):
    before = todo(git_repo)
    path = git_repo.root / "TODO.md"
    mtime = path.stat().st_mtime_ns
    result = data(
        git_repo.root, "edit", "T002", "--title", "Repricing", "--pts", "3", "--depends-on", "T001", capsys=capsys
    )
    assert (result["changes"], result["files"]) == ({}, [])
    assert todo(git_repo) == before
    assert path.stat().st_mtime_ns == mtime


# 10. Unknown, closed and done-branch tasks


def test_an_unknown_task_is_not_found(git_repo, capsys):
    assert "no task `T099`" in refused(git_repo, "T099", "--title", "X", code=3, capsys=capsys)


@pytest.mark.parametrize("closing", ["done", "discard"])
def test_a_closed_task_is_refused_unless_forced(git_repo, capsys, closing):
    assert run(git_repo.root, closing, "T003", "--force", capsys=capsys)[0] == 0
    label = "done" if closing == "done" else "discarded"
    assert f"T003 is {label}" in refused(git_repo, "T003", "--title", "X", code=5, capsys=capsys)
    assert run(git_repo.root, "edit", "T003", "--title", "X", "--force", capsys=capsys)[0] == 0
    assert row(git_repo, "T003")[5] == "X"


def test_a_task_done_on_its_branch_is_refused_unless_forced(git_repo, capsys):
    git(git_repo.root, "switch", "-q", "-c", "T003-rounding-error")
    assert run(git_repo.root, "done", "T003", "--force", capsys=capsys)[0] == 0
    git(git_repo.root, "commit", "-q", "-am", "done T003")
    git(git_repo.root, "switch", "-q", "main")
    assert "done on branch" in refused(git_repo, "T003", "--description", "X", code=5, capsys=capsys)
    assert run(git_repo.root, "edit", "T003", "--description", "X", "--force", capsys=capsys)[0] == 0


def test_a_task_discarded_on_its_branch_is_refused_unless_forced(git_repo, capsys):
    git(git_repo.root, "switch", "-q", "-c", "T003-rounding-error")
    assert run(git_repo.root, "discard", "T003", capsys=capsys)[0] == 0
    git(git_repo.root, "commit", "-q", "-am", "discard T003")
    git(git_repo.root, "switch", "-q", "main")
    assert "T003 is discarded on branch T003-rounding-error" in refused(git_repo, "T003", "--description", "X", code=5, capsys=capsys)
    assert run(git_repo.root, "edit", "T003", "--description", "X", "--force", capsys=capsys)[0] == 0


# 11. Claims


def claim_file(repo, task_id):
    common = git(repo.root, "rev-parse", "--git-common-dir")
    return (repo.root / common / "taskrail" / "claims" / f"{task_id}.json").read_text()


def test_someone_elses_claim_is_refused_unless_forced(git_repo, capsys):
    assert run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    before = claim_file(git_repo, "T002")
    assert "claimed by alice" in refused(git_repo, "T002", "--title", "X", "--owner", "bob", code=4, capsys=capsys)
    assert run(git_repo.root, "edit", "T002", "--title", "X", "--owner", "bob", "--force", capsys=capsys)[0] == 0
    assert claim_file(git_repo, "T002") == before


def test_the_callers_claim_or_no_claim_is_fine(git_repo, capsys):
    assert run(git_repo.root, "edit", "T003", "--title", "Unclaimed", capsys=capsys)[0] == 0
    assert run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    before = claim_file(git_repo, "T002")
    assert run(git_repo.root, "edit", "T002", "--title", "Mine", "--owner", "alice", capsys=capsys)[0] == 0
    assert claim_file(git_repo, "T002") == before


# 12. Invalid backlogs


def cyclic(repo):
    repo.write("TODO.md", BASE_TODO.replace("| ✅ | T001 | chore   | 2   | —    ", "| ✅ | T001 | chore   | 2   | T003 "))
    assert "depends-cycle" in repo.codes()


def test_an_invalid_backlog_is_refused(git_repo, capsys):
    cyclic(git_repo)
    assert "validation error" in refused(git_repo, "T002", "--title", "X", code=1, capsys=capsys)


def test_allow_invalid_writes_an_edit_that_fixes_the_backlog(git_repo, capsys):
    cyclic(git_repo)
    assert "nothing was written" in refused(git_repo, "T002", "--title", "X", "--allow-invalid", code=1, capsys=capsys)
    code, _, err = run(git_repo.root, "edit", "T001", "--depends-on", "", "--allow-invalid", "--force", capsys=capsys)
    assert code == 0, err
    assert run(git_repo.root, "validate", capsys=capsys)[0] == 0


# 13–14. Branch names


def record(repo, task_id):
    return branches.read(load_config(repo.root), task_id)


def test_a_recorded_branch_keeps_its_name(git_repo, capsys):
    assert run(git_repo.root, "branch", "T002", "feature/reprice", capsys=capsys)[0] == 0
    kept = record(git_repo, "T002")
    result = data(git_repo.root, "edit", "T002", "--title", "Retroactive pricing", capsys=capsys)
    assert result["branch"] == {"name": "feature/reprice", "source": "recorded", "previous": None, "recorded": False}
    assert record(git_repo, "T002") == kept
    assert data(git_repo.root, "show", "T002", capsys=capsys)["branch"] == "feature/reprice"


def test_an_existing_template_branch_is_recorded_before_the_title_changes(git_repo, capsys):
    git(git_repo.root, "branch", T002)
    result = data(git_repo.root, "edit", "T002", "--title", "Retroactive pricing", capsys=capsys)
    assert result["branch"] == {"name": T002, "source": "recorded", "previous": None, "recorded": True}
    assert record(git_repo, "T002").branch == T002
    shown = data(git_repo.root, "show", "T002", capsys=capsys)
    assert (shown["branch"], shown["branch_source"]) == (T002, "recorded")
    assert git(git_repo.root, "branch", "--list", T002) != ""


def test_without_a_branch_the_task_resolves_to_the_new_name(git_repo, capsys):
    result = data(git_repo.root, "edit", "T002", "--title", "Retroactive pricing", capsys=capsys)
    assert result["branch"] == {
        "name": "T002-retroactive-pricing", "source": "template", "previous": T002, "recorded": False
    }
    assert result["record_remote"] is None
    assert record(git_repo, "T002") is None


def test_an_edit_that_keeps_the_branch_name_reports_no_previous(git_repo, capsys):
    git(git_repo.root, "branch", T002)
    result = data(git_repo.root, "edit", "T002", "--pts", "5", capsys=capsys)
    assert result["branch"] == {"name": T002, "source": "template", "previous": None, "recorded": False}
    assert record(git_repo, "T002") is None


@pytest.fixture
def mirrored(git_repo, tmp_path_factory):
    git_repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[git]\nbranch_record_remote = "origin"\n')
    git(git_repo.root, "commit", "-q", "-am", "mirror records")
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare
    return git_repo


def test_a_recorded_branch_is_mirrored_like_claim(mirrored, capsys):
    git(mirrored.root, "branch", T002)
    result = data(mirrored.root, "edit", "T002", "--title", "Retroactive pricing", capsys=capsys)
    assert result["branch"]["recorded"] is True
    assert result["record_remote"]["pushed"] is True
    assert git(mirrored.bare, "for-each-ref", "--format=%(refname)", "refs/taskrail/branches/") == "refs/taskrail/branches/T002"


def test_local_only_records_without_mirroring(mirrored, capsys):
    git(mirrored.root, "branch", T002)
    result = data(mirrored.root, "edit", "T002", "--title", "Retroactive pricing", "--local-only", capsys=capsys)
    assert (result["branch"]["recorded"], result["record_remote"]) == (True, None)
    assert git(mirrored.bare, "for-each-ref", "--format=%(refname)", "refs/taskrail/branches/") == ""


# 15. Text output


def test_text_output_names_each_change(git_repo, capsys):
    code, out, _ = run(git_repo.root, "edit", "T003", "--title", "Rounding", "--pts", "", "--depends-on", "T001, T002", capsys=capsys)
    assert code == 0
    lines = out.splitlines()
    assert "T003 title: Rounding error → Rounding" in lines
    assert "T003 points: 1 → —" in lines
    assert "T003 depends_on: T002 → T001, T002" in lines
    assert "T003 branch: T003-rounding-error → T003-rounding" in lines


def test_text_output_when_nothing_changes(git_repo, capsys):
    code, out, _ = run(git_repo.root, "edit", "T003", "--title", "Rounding error", capsys=capsys)
    assert (code, out.strip()) == (0, "T003 unchanged")
