"""The backlog merge driver (DESIGN.md §7.4): row-by-row table merges, git integration and install."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import git

from taskrail import mergedriver
from taskrail.cli import main

HEADER = (
    "| ✓  | ID   | Kind    | Pts | Depends On | Title          | Description |\n"
    "|----|------|---------|-----|------------|----------------|-------------|\n"
)


def row(status: str, task_id: str, title: str = "Task", description: str = "Some work", kind: str = "feature") -> str:
    return f"| {status} | {task_id} | {kind:<7} | 1   | —          | {title:<14} | {description:<11} |\n"


def backlog(e01: list[str], e02: list[str] | None = None, intro: str = "Done when: every session has a cost.") -> str:
    text = (
        "# TODO\n\n## Epics\n\n"
        "| ID  | Epic    | Objective       | File |\n"
        "|-----|---------|-----------------|------|\n"
        "| E01 | Billing | Charge properly | —    |\n"
        "| E02 | Auth    | Sign in         | —    |\n\n"
        f"## E01 — Billing\n\n{intro}\n\n" + HEADER + "".join(e01) + "\n"
        "## E02 — Auth\n\nDone when: nobody types a password.\n\n" + HEADER + "".join(e02 or [row("⬜", "T009")])
    )
    return text


BASE_ROWS = [row("✅", "T001", "Price table"), row("⬜", "T002", "Repricing"), row("⬜", "T003", "Rounding")]


def merge(base: str, current: str, other: str, **kwargs) -> tuple[str, bool]:
    kwargs.setdefault("labels", ("ours", "base", "theirs"))
    return mergedriver.merge_text(base, current, other, **kwargs)


def git_merge_file(tmp_path: Path, base: str, current: str, other: str, marker_size: int = 7) -> tuple[str, int]:
    for name, text in (("b", base), ("c", current), ("o", other)):
        (tmp_path / name).write_bytes(text.encode())
    result = subprocess.run(
        ["git", "merge-file", "-p", f"--marker-size={marker_size}", "-L", "ours", "-L", "base", "-L", "theirs", "c", "b", "o"],
        cwd=tmp_path,
        capture_output=True,
    )
    return result.stdout.decode(), result.returncode


# --- the merge itself, on three strings ------------------------------------------------------------


def test_rows_appended_on_both_sides_are_all_kept_current_first():
    base = backlog(BASE_ROWS)
    current = backlog([*BASE_ROWS, row("⬜", "T010", "Mine")])
    other = backlog([*BASE_ROWS, row("⬜", "T011", "Theirs")])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == backlog([*BASE_ROWS, row("⬜", "T010", "Mine"), row("⬜", "T011", "Theirs")])


def test_a_status_flip_merges_with_a_row_appended_right_after_it():
    base = backlog(BASE_ROWS)
    current = backlog([BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding")])
    other = backlog([*BASE_ROWS, row("⬜", "T010", "Next")])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == backlog([BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding"), row("⬜", "T010", "Next")])


def test_different_cells_of_one_row_changed_on_each_side_are_both_kept():
    base = backlog(BASE_ROWS)
    current = backlog([BASE_ROWS[0], row("✅", "T002", "Repricing"), BASE_ROWS[2]])
    other = backlog([BASE_ROWS[0], row("⬜", "T002", "Repricing v2"), BASE_ROWS[2]])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == backlog([BASE_ROWS[0], row("✅", "T002", "Repricing v2"), BASE_ROWS[2]])


def test_a_row_added_identically_on_both_sides_appears_once():
    base = backlog(BASE_ROWS)
    current = backlog([*BASE_ROWS, row("⬜", "T010", "Opened"), row("⬜", "T011", "Later")])
    other = backlog([*BASE_ROWS, row("⬜", "T010", "Opened")])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == current


@pytest.mark.parametrize(
    ("reopened", "expected"),
    [
        (set(), "✅"),  # no reopen anywhere: done wins
        ({"theirs"}, "⬜"),  # the pending side reopened it and the done side lacks that commit
        ({"ours", "theirs"}, "✅"),  # both sides carry a reopen
        ({"ours"}, "✅"),  # the done side has the reopen: it was done again afterwards
    ],
)
def test_the_same_new_row_done_on_one_side_and_pending_on_the_other(reopened, expected):
    base = backlog(BASE_ROWS)
    current = backlog([*BASE_ROWS, row("✅", "T010", "Opened")])
    other = backlog([*BASE_ROWS, row("⬜", "T010", "Opened")])
    calls = []

    def lookup(task_id):
        calls.append(task_id)
        return {"current" if side == "ours" else "other" for side in reopened}

    text, conflicted = merge(base, current, other, reopened=lookup)
    assert not conflicted
    assert text == backlog([*BASE_ROWS, row(expected, "T010", "Opened")])
    assert calls == ["T010"]


def test_a_status_conflict_that_needs_the_reopen_check_stays_marked_when_sides_are_unknown():
    base = backlog(BASE_ROWS)
    current = backlog([*BASE_ROWS, row("✅", "T010", "Opened"), row("⬜", "T011", "Mine")])
    other = backlog([*BASE_ROWS, row("⬜", "T010", "Opened"), row("⬜", "T012", "Theirs")])
    text, conflicted = merge(base, current, other, reopened=None)
    assert conflicted
    assert (
        "<<<<<<< ours\n" + row("✅", "T010", "Opened") + "=======\n" + row("⬜", "T010", "Opened") + ">>>>>>> theirs\n"
    ) in text
    assert row("⬜", "T011", "Mine") + row("⬜", "T012", "Theirs") in text
    assert text.count("<<<<<<<") == 1


def test_done_wins_over_discarded_without_a_reopen_check():
    base = backlog(BASE_ROWS)
    current = backlog([BASE_ROWS[0], row("✅", "T002", "Repricing"), BASE_ROWS[2]])
    other = backlog([BASE_ROWS[0], row("❌", "T002", "Repricing"), BASE_ROWS[2]])
    text, conflicted = merge(base, current, other, reopened=None)
    assert not conflicted
    assert text == current


def test_pending_against_discarded_on_a_done_row_is_marked_alone():
    base = backlog(BASE_ROWS)
    current = backlog([row("⬜", "T001", "Price table"), BASE_ROWS[1], BASE_ROWS[2], row("⬜", "T010", "Mine")])
    other = backlog([row("❌", "T001", "Price table"), BASE_ROWS[1], BASE_ROWS[2], row("⬜", "T011", "Theirs")])
    text, conflicted = merge(base, current, other, reopened=lambda task_id: set())
    assert conflicted
    assert text.count("<<<<<<<") == 1
    assert "<<<<<<< ours\n" + row("⬜", "T001", "Price table") + "=======\n" + row("❌", "T001", "Price table") in text
    assert row("⬜", "T010", "Mine") + row("⬜", "T011", "Theirs") in text


def test_the_same_cell_changed_differently_marks_only_that_row_with_the_marker_size():
    base = backlog(BASE_ROWS)
    current = backlog([BASE_ROWS[0], row("⬜", "T002", "Mine"), BASE_ROWS[2], row("⬜", "T010")], intro="Done when: ours.")
    other = backlog([BASE_ROWS[0], row("⬜", "T002", "Theirs"), row("✅", "T003", "Rounding")])
    text, conflicted = merge(base, current, other, marker_size=10)
    assert conflicted
    assert text == backlog(
        [
            BASE_ROWS[0],
            "<<<<<<<<<< ours\n" + row("⬜", "T002", "Mine") + "==========\n" + row("⬜", "T002", "Theirs") + ">>>>>>>>>> theirs\n",
            row("✅", "T003", "Rounding"),
            row("⬜", "T010"),
        ],
        intro="Done when: ours.",
    )


def test_prose_right_after_a_merged_table_merges_cleanly():
    base = backlog(BASE_ROWS)
    current = backlog(BASE_ROWS).replace("\n## E02 — Auth", "Rows are appended.\n## E02 — Auth")
    other = backlog([*BASE_ROWS, row("⬜", "T010")])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert row("⬜", "T010") + "Rows are appended.\n## E02 — Auth" in text


def test_the_same_prose_line_changed_differently_conflicts_as_git_would(tmp_path):
    base = backlog(BASE_ROWS)
    current = backlog([*BASE_ROWS, row("⬜", "T010")], intro="Done when: ours.")
    other = backlog([*BASE_ROWS, row("⬜", "T011")], intro="Done when: theirs.")
    text, conflicted = merge(base, current, other)
    assert conflicted
    assert "<<<<<<< ours\nDone when: ours.\n=======\nDone when: theirs.\n>>>>>>> theirs\n" in text
    assert row("⬜", "T010") + row("⬜", "T011") in text


UNMERGEABLE = {
    "header changed on one side": lambda text: text.replace("| Description |\n|----|", "| Notes       |\n|----|", 1),
    "duplicate keys": lambda text: text.replace(BASE_ROWS[2], BASE_ROWS[2] + BASE_ROWS[2]),
    "a row with the wrong cell count": lambda text: text.replace(BASE_ROWS[2], BASE_ROWS[2].rstrip("\n") + " extra |\n"),
    "section removed": lambda text: text[: text.index("## E01")] + text[text.index("## E02") :],
}


@pytest.mark.parametrize("case", sorted(UNMERGEABLE))
def test_a_table_that_cannot_be_merged_by_row_gets_git_merge_file_result(tmp_path, case):
    base = backlog(BASE_ROWS)
    current = UNMERGEABLE[case](backlog([*BASE_ROWS, row("⬜", "T010")]))
    other = backlog([*BASE_ROWS, row("⬜", "T011")], e02=[row("✅", "T009")])
    expected, code = git_merge_file(tmp_path, base, current, other)
    text, conflicted = merge(base, current, other)
    assert (text, conflicted) == (expected, code > 0)


def test_a_deleted_row_is_removed_unless_the_other_side_changed_it():
    base = backlog(BASE_ROWS)
    text, conflicted = merge(base, backlog([BASE_ROWS[0], BASE_ROWS[2]]), backlog([*BASE_ROWS, row("⬜", "T010")]))
    assert not conflicted
    assert text == backlog([BASE_ROWS[0], BASE_ROWS[2], row("⬜", "T010")])

    text, conflicted = merge(base, backlog([BASE_ROWS[0], BASE_ROWS[2]]), backlog([BASE_ROWS[0], row("✅", "T002", "Repricing"), BASE_ROWS[2]]))
    assert conflicted
    assert "<<<<<<< ours\n=======\n" + row("✅", "T002", "Repricing") + ">>>>>>> theirs\n" in text


def test_a_row_moved_to_another_table_is_not_duplicated():
    base = backlog(BASE_ROWS)
    current = backlog([BASE_ROWS[0], BASE_ROWS[1]], e02=[row("⬜", "T009"), BASE_ROWS[2]])
    other = backlog([*BASE_ROWS, row("⬜", "T010")])
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == backlog([BASE_ROWS[0], BASE_ROWS[1], row("⬜", "T010")], e02=[row("⬜", "T009"), BASE_ROWS[2]])


def test_the_epics_table_and_an_artifact_index_merge_by_their_first_key():
    epic = "| E03 | Search  | Find things     | —    |\n"
    other_epic = "| E04 | Export  | Ship data       | —    |\n"
    base = backlog(BASE_ROWS)
    current = base.replace("| E02 | Auth    | Sign in         | —    |\n", "| E02 | Auth    | Sign in         | —    |\n" + epic)
    other = base.replace("| E02 | Auth    | Sign in         | —    |\n", "| E02 | Auth    | Sign in         | —    |\n" + other_epic)
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert epic + other_epic in text

    index = "# Features\n\n| Task | Title | Document |\n|------|-------|----------|\n| T001 | One | [a](a.md) |\n"
    text, conflicted = merge(index, index + "| T002 | Two | [b](b.md) |\n", index + "| T003 | Three | [c](c.md) |\n")
    assert not conflicted
    assert text == index + "| T002 | Two | [b](b.md) |\n| T003 | Three | [c](c.md) |\n"


def test_aliased_status_and_id_columns_are_honoured():
    header = "| Done | Key  | Kind    | Depends On | Title |\n|------|------|---------|------------|-------|\n"
    table = lambda rows: "## E01 — Billing\n\n" + header + "".join(f"| {s} | {i} | feature | —          | {t} |\n" for s, i, t in rows)
    base = table([("⬜", "T001", "A"), ("⬜", "T002", "B")])
    # Same Key added on both sides, done against pending: only the status rule resolves it.
    current = table([("⬜", "T001", "A"), ("⬜", "T002", "B"), ("✅", "T003", "C")])
    other = table([("⬜", "T001", "A"), ("⬜", "T002", "B"), ("⬜", "T003", "C")])
    aliases = {"✓": "Done", "ID": "Key"}
    text, conflicted = merge(base, current, other, aliases=aliases, reopened=lambda task_id: set())
    assert (text, conflicted) == (current, False)
    _, conflicted = merge(base, current, other, reopened=lambda task_id: set())
    assert conflicted  # without the aliases `Done` is an ordinary cell


def test_the_driver_reads_aliases_from_the_working_tree_config_and_ignores_an_unreadable_one(tmp_path):
    (tmp_path / ".taskrail").mkdir()
    config = tmp_path / ".taskrail/config.toml"
    config.write_text('[[backlog]]\nname = "main"\nprefix = "T"\nfile = "TODO.md"\n\n[columns]\naliases = { ID = "Key" }\n')
    assert mergedriver._aliases(tmp_path) == {"ID": "Key"}
    config.write_text("<<<<<<< HEAD\nversion = 1\n=======\n")
    assert mergedriver._aliases(tmp_path) is None


def test_line_endings_and_a_missing_final_newline_are_kept():
    base = backlog(BASE_ROWS).replace("\n", "\r\n").rstrip("\r\n")
    current = backlog([*BASE_ROWS, row("⬜", "T010")]).replace("\n", "\r\n").rstrip("\r\n")
    other = backlog([BASE_ROWS[0], row("✅", "T002", "Repricing"), BASE_ROWS[2]]).replace("\n", "\r\n").rstrip("\r\n")
    text, conflicted = merge(base, current, other)
    assert not conflicted
    assert text == backlog([BASE_ROWS[0], row("✅", "T002", "Repricing"), BASE_ROWS[2], row("⬜", "T010")]).replace("\n", "\r\n").rstrip("\r\n")


# --- the driver command ----------------------------------------------------------------------------


def run_driver(tmp_path: Path, base: bytes, current: bytes, other: bytes, *extra: str, capsys) -> tuple[int, bytes, str]:
    paths = []
    for name, data in (("base", base), ("current", current), ("other", other)):
        (tmp_path / name).write_bytes(data)
        paths.append(str(tmp_path / name))
    code = main(["merge-driver", *paths, "--marker-size", "7", "--path", "TODO.md",
                 "--base-label", "base", "--current-label", "ours", "--other-label", "theirs", *extra])
    return code, (tmp_path / "current").read_bytes(), capsys.readouterr().err


def test_the_driver_writes_the_result_over_current_and_exits_0_or_1(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = backlog(BASE_ROWS)
    clean = run_driver(tmp_path, base.encode(), backlog([*BASE_ROWS, row("⬜", "T010")]).encode(),
                       backlog([*BASE_ROWS, row("⬜", "T011")]).encode(), capsys=capsys)
    assert clean[0] == 0
    assert clean[1].decode() == backlog([*BASE_ROWS, row("⬜", "T010"), row("⬜", "T011")])
    conflict = run_driver(tmp_path, base.encode(), backlog([*BASE_ROWS], intro="A").encode(),
                          backlog([*BASE_ROWS], intro="B").encode(), capsys=capsys)
    assert conflict[0] == 1
    assert b"<<<<<<< ours\nA\n=======\nB\n>>>>>>> theirs\n" in conflict[1]


@pytest.mark.parametrize("case", ["no tables", "not utf-8", "internal error"])
def test_the_driver_falls_back_to_git_merge_file(tmp_path, capsys, monkeypatch, case):
    monkeypatch.chdir(tmp_path)
    if case == "no tables":
        inputs = (b"a\nb\nc\n", b"a\nB\nc\n", b"a\nb\nC\n")
    elif case == "not utf-8":
        inputs = (b"a\n\xff\nc\n", b"x\n\xff\nc\n", b"a\n\xff\ny\n")
    else:
        inputs = (backlog(BASE_ROWS).encode(), backlog(BASE_ROWS, intro="A").encode(), backlog(BASE_ROWS, intro="B").encode())

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(mergedriver, "merge_tables", boom)
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    for name, data in zip(("b", "c", "o"), inputs):
        (expected_dir / name).write_bytes(data)
    expected = subprocess.run(["git", "merge-file", "-p", "-L", "ours", "-L", "base", "-L", "theirs", "c", "b", "o"],
                              cwd=expected_dir, capture_output=True)
    code, result, err = run_driver(tmp_path, *inputs, capsys=capsys)
    assert result == expected.stdout
    assert code == min(expected.returncode, 1)
    if case == "internal error":
        assert "TODO.md" in err and "boom" in err


# --- real git --------------------------------------------------------------------------------------


@pytest.fixture
def driven(tmp_path, monkeypatch, capsys):
    """A repository with taskrail installed with --merge-driver, running this checkout's code."""
    root = tmp_path / "repo"
    root.mkdir()
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    shim = tmp_path / "taskrail-shim"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m taskrail "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("TASKRAIL_BIN", str(shim))
    git(root, "init", "-q", "-b", "main")
    assert main(["--root", str(root), "init", "--merge-driver", "--json"]) == 0
    capsys.readouterr()
    (root / "TODO.md").write_text(backlog(BASE_ROWS))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def commit(root: Path, text: str, message: str, path: str = "TODO.md") -> None:
    (root / path).write_text(text)
    git(root, "add", path)
    git(root, "commit", "-q", "-m", message)


def attempt(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def validate(root: Path, capsys) -> int:
    code = main(["--root", str(root), "validate"])
    capsys.readouterr()
    return code


def test_git_merge_keeps_rows_appended_on_both_branches(driven, capsys):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T011", "Theirs")]), "add T011")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T010", "Mine")]), "add T010")
    result = attempt(driven, "merge", "--no-edit", "topic")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (driven / "TODO.md").read_text() == backlog([*BASE_ROWS, row("⬜", "T010", "Mine"), row("⬜", "T011", "Theirs")])
    assert validate(driven, capsys) == 0


def test_git_rebase_replays_rows_and_a_done_mark_onto_new_rows(driven, capsys):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T011", "Theirs")]), "add T011")
    commit(driven, backlog([BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding"), row("⬜", "T011", "Theirs")]), "done T003")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T010", "Mine")]), "add T010")
    git(driven, "switch", "-q", "topic")
    result = attempt(driven, "rebase", "main")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (driven / "TODO.md").read_text() == backlog(
        [BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding"), row("⬜", "T010", "Mine"), row("⬜", "T011", "Theirs")]
    )
    assert validate(driven, capsys) == 0


def test_git_cherry_pick_of_a_done_mark_next_to_an_appended_row(driven):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding")]), "done T003")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T010", "Mine")]), "add T010")
    result = attempt(driven, "cherry-pick", "topic")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (driven / "TODO.md").read_text() == backlog([BASE_ROWS[0], BASE_ROWS[1], row("✅", "T003", "Rounding"), row("⬜", "T010", "Mine")])


def test_a_rebase_replaying_a_row_already_done_upstream_keeps_it_done(driven, capsys):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T010", "Opened")]), "open T010")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS, row("✅", "T010", "Opened"), row("⬜", "T011", "Next")]), "T010 merged and done")
    git(driven, "switch", "-q", "topic")
    result = attempt(driven, "rebase", "main")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (driven / "TODO.md").read_text() == backlog([*BASE_ROWS, row("✅", "T010", "Opened"), row("⬜", "T011", "Next")])


@pytest.mark.parametrize("trailer", [True, False])
def test_a_reopen_commit_on_the_pending_side_keeps_it_pending(driven, trailer):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([*BASE_ROWS, row("✅", "T010", "Opened")]), "open and finish T010")
    message = "Reopen T010: Opened\n\nStill broken.\n" + ("\nReopens: T010\n" if trailer else "")
    commit(driven, backlog([*BASE_ROWS, row("⬜", "T010", "Opened")]), message)
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS, row("✅", "T010", "Opened"), row("⬜", "T011", "Next")]), "T010 done")
    result = attempt(driven, "merge", "--no-edit", "topic")
    assert result.returncode == 0, result.stdout + result.stderr
    expected = "⬜" if trailer else "✅"
    assert (driven / "TODO.md").read_text() == backlog([*BASE_ROWS, row(expected, "T010", "Opened"), row("⬜", "T011", "Next")])


def test_reopen_commits_patch_equivalent_on_both_sides_cancel_out(driven):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, "reopened\n", "Reopen T002: Repricing\n\nReopens: T002\n", path="notes.txt")
    git(driven, "switch", "-q", "main")
    commit(driven, "other\n", "unrelated", path="other.txt")
    assert mergedriver.reopen_sides(driven, "main", "topic") == {"T002": {"other"}}
    git(driven, "cherry-pick", "topic")
    assert mergedriver.reopen_sides(driven, "main", "topic") == {}


def test_a_real_conflict_is_left_with_markers_around_the_row_only(driven):
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([BASE_ROWS[0], row("⬜", "T002", "Theirs"), BASE_ROWS[2], row("⬜", "T011")]), "retitle theirs")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([BASE_ROWS[0], row("⬜", "T002", "Mine"), BASE_ROWS[2], row("⬜", "T010")]), "retitle mine")
    result = attempt(driven, "merge", "--no-edit", "topic")
    assert result.returncode != 0
    assert git(driven, "diff", "--name-only", "--diff-filter=U") == "TODO.md"
    text = (driven / "TODO.md").read_text()
    assert text.count("<<<<<<<") == 1
    assert "<<<<<<< HEAD\n" + row("⬜", "T002", "Mine") + "=======\n" + row("⬜", "T002", "Theirs") + ">>>>>>> topic\n" in text
    assert row("⬜", "T010") + row("⬜", "T011") in text


def test_a_driver_that_cannot_start_falls_back_to_an_ordinary_merge(driven, monkeypatch):
    monkeypatch.setenv("TASKRAIL_BIN", str(driven / "missing-taskrail"))
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog(BASE_ROWS, intro="Done when: theirs."), "theirs")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog(BASE_ROWS, intro="Done when: ours."), "ours")
    result = attempt(driven, "merge", "--no-edit", "topic")
    assert result.returncode != 0
    assert "<<<<<<< HEAD\nDone when: ours.\n=======\nDone when: theirs.\n>>>>>>> topic\n" in (driven / "TODO.md").read_text()


def test_a_clone_without_the_driver_definition_uses_git_text_merge(driven):
    git(driven, "config", "--local", "--remove-section", "merge.taskrail")
    git(driven, "switch", "-q", "-c", "topic")
    commit(driven, backlog([*BASE_ROWS], e02=[row("✅", "T009")]), "done T009")
    git(driven, "switch", "-q", "main")
    commit(driven, backlog([*BASE_ROWS], intro="Done when: ours."), "prose")
    result = attempt(driven, "merge", "--no-edit", "topic")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (driven / "TODO.md").read_text() == backlog([*BASE_ROWS], e02=[row("✅", "T009")], intro="Done when: ours.")


# --- installing ------------------------------------------------------------------------------------


@pytest.fixture
def plain(tmp_path, monkeypatch):
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def cli(root: Path, *argv: str, capsys) -> dict:
    code = main(["--root", str(root), *argv, "--json"])
    out, err = capsys.readouterr()
    assert code == 0, err
    return json.loads(out)


def block(root: Path) -> list[str]:
    text = (root / ".gitattributes").read_text()
    start, end = text.index(mergedriver.ATTRIBUTES_BEGIN), text.index(mergedriver.ATTRIBUTES_END)
    return text[start:end].splitlines()[1:]


def local_config(root: Path, key: str) -> str | None:
    result = subprocess.run(["git", "config", "--local", "--get", key], cwd=root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def test_init_merge_driver_writes_attributes_config_and_the_extra(plain, capsys):
    (plain / ".gitattributes").write_text("*.png binary\n")
    report = cli(plain, "init", "--merge-driver", capsys=capsys)
    assert ".gitattributes" in report["updated"]
    assert "git config merge.taskrail" in report["created"]
    assert (plain / ".gitattributes").read_text().startswith("*.png binary\n")
    assert block(plain) == [
        "/TODO.md merge=taskrail",
        "/docs/autopilot/decisions/README.md merge=taskrail",
        "/docs/bugs/README.md merge=taskrail",
        "/docs/chores/README.md merge=taskrail",
        "/docs/features/README.md merge=taskrail",
        "/docs/spikes/README.md merge=taskrail",
    ]
    assert local_config(plain, "merge.taskrail.driver") == mergedriver.DRIVER_COMMAND
    assert local_config(plain, "merge.taskrail.name") == mergedriver.DRIVER_NAME
    assert json.loads((plain / ".taskrail/installed.json").read_text())["extras"]["merge_driver"] is True

    again = cli(plain, "init", "--merge-driver", capsys=capsys)
    assert ".gitattributes" in again["unchanged"] and "git config merge.taskrail" in again["unchanged"]
    assert (plain / ".gitattributes").read_text().count(mergedriver.ATTRIBUTES_BEGIN) == 1


def test_init_without_the_flag_installs_no_merge_driver(plain, capsys):
    cli(plain, "init", capsys=capsys)
    assert not (plain / ".gitattributes").exists()
    assert local_config(plain, "merge.taskrail.driver") is None


def test_upgrade_refreshes_the_block_and_only_updates_an_existing_definition(plain, capsys):
    cli(plain, "init", "--merge-driver", "--integration", "claude", capsys=capsys)
    todo = (plain / "TODO.md").read_text() + "| E01 | Billing | Charge | todo/E01-billing.md |\n"
    (plain / "TODO.md").write_text(todo)
    (plain / "todo").mkdir()
    (plain / "todo/E01-billing.md").write_text("## E01 — Billing\n")
    git(plain, "config", "--local", "--unset", "merge.taskrail.driver")
    report = cli(plain, "upgrade", capsys=capsys)
    assert "/todo/E01-billing.md merge=taskrail" in block(plain)
    assert ".gitattributes" in report["updated"]
    assert local_config(plain, "merge.taskrail.driver") is None

    git(plain, "config", "--local", "merge.taskrail.driver", "old command")
    cli(plain, "upgrade", capsys=capsys)
    assert local_config(plain, "merge.taskrail.driver") == mergedriver.DRIVER_COMMAND


def test_epic_commands_add_their_file_to_an_existing_block(plain, capsys):
    cli(plain, "init", "--merge-driver", capsys=capsys)
    cli(plain, "epic", "add", "--name", "Billing", "--objective", "Charge", "--own-file", capsys=capsys)
    assert "/todo/E01-billing.md merge=taskrail" in block(plain)
    cli(plain, "epic", "add", "--name", "Auth", "--objective", "Sign in", capsys=capsys)
    cli(plain, "epic", "split", "E02", capsys=capsys)
    assert "/todo/E02-auth.md merge=taskrail" in block(plain)


def test_epic_commands_create_no_block_when_none_exists(plain, capsys):
    cli(plain, "init", capsys=capsys)
    cli(plain, "epic", "add", "--name", "Billing", "--objective", "Charge", "--own-file", capsys=capsys)
    assert not (plain / ".gitattributes").exists()


@pytest.mark.parametrize("path", ["TODO.md", "my backlog/E01 [x].md", 'odd "name"*?.md', "back\\slash.md"])
def test_attribute_lines_match_exactly_their_path(plain, path):
    assert mergedriver.attribute_line("TODO.md") == "/TODO.md merge=taskrail"
    (plain / ".gitattributes").write_text(mergedriver.attribute_line(path) + "\n")

    def merge_attribute(name: str) -> str:
        output = subprocess.run(["git", "check-attr", "-z", "merge", "--", name], cwd=plain, capture_output=True, text=True).stdout
        return output.split("\0")[2]

    assert merge_attribute(path) == "taskrail"
    assert merge_attribute("sub/" + path) == "unspecified"
    assert merge_attribute("TODO.mdx") == "unspecified"
