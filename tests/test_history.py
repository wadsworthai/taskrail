"""validate reads git history for tasks reopened without a `Reopens: <ID>` trailer (T012)."""

import json
import subprocess
import time
from pathlib import Path

import pytest
from conftest import BASE_CONFIG, BASE_TODO, Repo, git

from taskrail import history
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.project import load_project

CODE = "reopen-untraced"


def run(repo, *argv, capsys):
    code = main(["--root", str(repo.root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def validate(repo, capsys, *extra):
    code, out, _ = run(repo, "validate", "--json", *extra, capsys=capsys)
    return code, json.loads(out)


def untraced(data) -> list[dict]:
    return [issue for issue in data["issues"] if issue["code"] == CODE]


def set_status(repo: Repo, task_id: str, status: str, relative: str = "TODO.md") -> None:
    path = repo.root / relative
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        cells = line.split("|")
        if len(cells) > 2 and cells[2].strip() == task_id:
            cells[1] = f" {status} "
            lines[index] = "|".join(cells)
    path.write_text("".join(lines), encoding="utf-8")


def commit(repo: Repo, message: str, *extra: str) -> str:
    git(repo.root, "add", "-A")
    git(repo.root, "commit", "-q", *extra, "-m", message)
    return git(repo.root, "rev-parse", "--short", "HEAD")


def edit_title(repo: Repo, old: str, new: str) -> None:
    path = repo.root / "TODO.md"
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


# 1, 2 — a hand reopen is reported, as a warning


def test_a_done_task_reopened_without_a_trailer_is_reported(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    sha = commit(git_repo, "Mark T001 pending")
    code, data = validate(git_repo, capsys)
    assert code == 0
    assert data["valid"] is True
    [issue] = untraced(data)
    assert issue["severity"] == "warning"
    assert issue["file"] == "TODO.md"
    assert issue["line"] == 15
    assert "T001" in issue["message"]
    assert sha in issue["message"]
    assert "✅ done" in issue["message"]
    assert "`Reopens: T001`" in issue["message"]


def test_the_warning_appears_in_text_output(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    sha = commit(git_repo, "Mark T001 pending")
    code, out, _ = run(git_repo, "validate", capsys=capsys)
    assert code == 0
    assert f"TODO.md:15: warning: T001 went from ✅ done to ⬜ pending in {sha}" in out
    assert f"[{CODE}]" in out


def test_a_discarded_task_reopened_without_a_trailer_is_reported(git_repo, capsys):
    set_status(git_repo, "T003", "❌")
    commit(git_repo, "Discard T003")
    set_status(git_repo, "T003", "⬜")
    sha = commit(git_repo, "Bring T003 back")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert "T003" in issue["message"] and sha in issue["message"]
    assert "❌ discarded" in issue["message"]


# 3 — what records a reopen


@pytest.mark.parametrize("trailer", ["Reopens: T001", "Reopens:  T001 ", "Reopens:T001"])
def test_a_trailer_in_the_reopen_commit_records_it(git_repo, capsys, trailer):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, f"Reopen T001: Price table\n\nPrices were never loaded\n\n{trailer}")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_a_later_commit_with_the_trailer_records_it(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    edit_title(git_repo, "Rounding error", "Rounding fault")
    commit(git_repo, "Rename T003")
    commit(git_repo, "Record the reopen of T001\n\nReopens: T001", "--allow-empty")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_a_squash_commit_carrying_the_trailer_in_its_body_records_it(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    edit_title(git_repo, "Rounding error", "Rounding fault")
    commit(
        git_repo,
        "fix(billing): load refund prices (T009) (#12)\n\nTask: T009 — Load refund prices\nArtifact: docs/bugs/T009.md\n\nReopens: T001",
    )
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


# 4 — a trailer older than the transition does not count


def test_an_older_trailer_does_not_cover_a_later_hand_reopen(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Reopen T001\n\nFirst time\n\nReopens: T001")
    set_status(git_repo, "T001", "✅")
    commit(git_repo, "Done T001")
    set_status(git_repo, "T001", "⬜")
    sha = commit(git_repo, "Mark T001 pending again")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert sha in issue["message"]


# 5 — what is not reported


def test_a_hand_reopen_closed_again_is_not_reported(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    set_status(git_repo, "T001", "✅")
    commit(git_repo, "Done T001")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_a_hand_reopen_closed_again_in_the_working_tree_is_not_reported(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    set_status(git_repo, "T001", "❌")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_a_task_that_no_longer_exists_is_not_reported(git_repo, capsys):
    set_status(git_repo, "T003", "❌")
    commit(git_repo, "Discard T003")
    set_status(git_repo, "T003", "⬜")
    commit(git_repo, "Bring T003 back")
    path = git_repo.root / "TODO.md"
    path.write_text("".join(line for line in path.read_text().splitlines(keepends=True) if "| T003 |" not in line))
    commit(git_repo, "Drop T003")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_an_uncommitted_reopen_is_not_reported(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


# 6 — epic files


def split_epic(repo: Repo) -> None:
    listing, section = (repo.root / "TODO.md").read_text(encoding="utf-8").split("## E01 — Billing")
    repo.write("TODO.md", listing.replace("| —    |", "| todo/E01-billing.md |"))
    repo.write("todo/E01-billing.md", "## E01 — Billing" + section)


def test_a_row_moved_to_an_epic_file_is_not_a_transition(git_repo, capsys):
    split_epic(git_repo)
    commit(git_repo, "Split E01")
    _, data = validate(git_repo, capsys)
    assert data["issues"] == []
    assert data["history"]["examined"] == 2


def test_a_hand_reopen_in_an_epic_file_is_reported(git_repo, capsys):
    split_epic(git_repo)
    commit(git_repo, "Split E01")
    set_status(git_repo, "T001", "⬜", "todo/E01-billing.md")
    sha = commit(git_repo, "Mark T001 pending")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert issue["file"] == "todo/E01-billing.md"
    assert sha in issue["message"]


# 7 — merges


def test_a_merge_resolution_that_reopens_a_task_is_reported(git_repo, capsys):
    git(git_repo.root, "switch", "-q", "-c", "side")
    edit_title(git_repo, "Rounding error", "Rounding fault")
    commit(git_repo, "Rename T003")
    git(git_repo.root, "switch", "-q", "main")
    edit_title(git_repo, "Charge properly", "Charge exactly ")
    commit(git_repo, "Reword E01")
    git(git_repo.root, "merge", "-q", "--no-ff", "--no-commit", "side")
    set_status(git_repo, "T001", "⬜")
    sha = commit(git_repo, "Merge side")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert sha in issue["message"]


def test_a_merged_branch_with_a_recorded_reopen_is_not_reported(git_repo, capsys):
    git(git_repo.root, "switch", "-q", "-c", "side")
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Reopen T001\n\nStill broken\n\nReopens: T001")
    git(git_repo.root, "switch", "-q", "main")
    edit_title(git_repo, "Charge properly", "Charge exactly ")
    commit(git_repo, "Reword E01")
    git(git_repo.root, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
    _, data = validate(git_repo, capsys)
    assert untraced(data) == []


def test_a_merged_branch_with_a_hand_reopen_is_reported_at_its_own_commit(git_repo, capsys):
    git(git_repo.root, "switch", "-q", "-c", "side")
    set_status(git_repo, "T001", "⬜")
    sha = commit(git_repo, "Mark T001 pending")
    git(git_repo.root, "switch", "-q", "main")
    edit_title(git_repo, "Charge properly", "Charge exactly ")
    commit(git_repo, "Reword E01")
    git(git_repo.root, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert sha in issue["message"]


# 8 — one warning per task


def test_several_hand_reopens_of_one_task_give_one_warning_for_the_latest(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    set_status(git_repo, "T001", "✅")
    commit(git_repo, "Done T001")
    set_status(git_repo, "T001", "⬜")
    latest = commit(git_repo, "Mark T001 pending again")
    _, data = validate(git_repo, capsys)
    [issue] = untraced(data)
    assert latest in issue["message"]


# 9 — flags, outside git, shallow clones


def test_no_history_skips_the_check(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    code, data = validate(git_repo, capsys, "--no-history")
    assert code == 0
    assert untraced(data) == []
    assert data["history"] == {"examined": 0, "limit": 500, "truncated": False, "shallow": False, "skipped": "--no-history"}


def test_history_limit_bounds_the_commits_examined(git_repo, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    edit_title(git_repo, "Rounding error", "Rounding fault")
    commit(git_repo, "Rename T003")
    _, data = validate(git_repo, capsys, "--history-limit", "1")
    assert untraced(data) == []
    assert data["history"] == {"examined": 1, "limit": 1, "truncated": True, "shallow": False, "skipped": None}
    code, out, _ = run(git_repo, "validate", "--history-limit", "1", capsys=capsys)
    assert code == 0
    assert "history: examined only the latest 1 commit(s) changing backlog files (--history-limit 1)" in out
    _, data = validate(git_repo, capsys, "--history-limit", "2")
    assert len(untraced(data)) == 1
    assert data["history"]["truncated"] is True
    _, data = validate(git_repo, capsys, "--history-limit", "3")
    assert data["history"] == {"examined": 3, "limit": 3, "truncated": False, "shallow": False, "skipped": None}


def test_history_limit_must_be_positive(git_repo, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--root", str(git_repo.root), "validate", "--history-limit", "0"])
    assert exit_info.value.code == 2


def test_the_default_run_reports_its_history(git_repo, capsys):
    code, data = validate(git_repo, capsys)
    assert code == 0
    assert data["history"] == {"examined": 1, "limit": 500, "truncated": False, "shallow": False, "skipped": None}
    _, out, _ = run(git_repo, "validate", capsys=capsys)
    assert "history:" not in out


def test_outside_git_the_check_is_skipped(repo, capsys):
    code, data = validate(repo, capsys)
    assert code == 0
    assert data["issues"] == []
    assert data["history"]["skipped"] == "not a git repository"
    _, out, _ = run(repo, "validate", capsys=capsys)
    assert "history: not checked (not a git repository)" in out


def test_a_shallow_clone_reports_it_and_does_not_fail(git_repo, tmp_path, capsys):
    set_status(git_repo, "T001", "⬜")
    commit(git_repo, "Mark T001 pending")
    clone = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", f"file://{git_repo.root}", str(clone))
    shallow = Repo(clone)
    code, data = validate(shallow, capsys)
    assert code == 0
    assert data["history"] == {"examined": 1, "limit": 500, "truncated": False, "shallow": True, "skipped": None}
    assert untraced(data) == []
    _, out, _ = run(shallow, "validate", capsys=capsys)
    assert "history: shallow clone; examined 1 commit(s)" in out


# 10 — only validate reads history


def test_other_commands_do_not_read_history(git_repo, capsys, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("history was read")

    monkeypatch.setattr(history, "check_reopens", refuse)
    for argv in (["list"], ["show", "T002"], ["next"]):
        assert run(git_repo, *argv, capsys=capsys)[0] == 0
    with pytest.raises(AssertionError):
        run(git_repo, "validate", capsys=capsys)


# 11 — cost on a long history


def test_a_long_history_is_checked_quickly(tmp_path, monkeypatch):
    for key, value in {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}.items():
        monkeypatch.setenv(key, value)
    root = tmp_path / "long"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    header = BASE_TODO.split("| ✅ | T001")[0]
    rows = [f"| {'✅' if n % 8 else '⬜'} | T{n:03d} | chore   | 2   | —          | Task {n} " + "x" * 80 + " | Description |" for n in range(1, 451)]

    def blob(revision: int, reopened: bool) -> bytes:
        current = list(rows)
        edited = revision % len(current)
        current[edited] = current[edited].replace(" Description |", f" Revision {revision} |")
        if reopened:
            current[0] = current[0].replace("| ✅ |", "| ⬜ |", 1)
        return (header + "\n".join(current) + "\n").encode()

    stream = []
    for revision in range(1, 1001):
        data = blob(revision, reopened=revision >= 900)
        message = f"Revision {revision}".encode()
        stream.append(b"commit refs/heads/main\n")
        stream.append(f"committer test <test@example.com> {1_700_000_000 + revision} +0000\n".encode())
        stream.append(b"data %d\n%s\n" % (len(message), message))
        stream.append(b"M 100644 inline TODO.md\n")
        stream.append(b"data %d\n%s\n" % (len(data), data))
    subprocess.run(["git", "fast-import", "--quiet"], cwd=root, input=b"".join(stream), check=True)
    git(root, "reset", "-q", "--hard", "main")
    assert len((root / "TODO.md").read_bytes()) > 50_000
    (root / ".taskrail").mkdir()
    (root / ".taskrail/config.toml").write_text(BASE_CONFIG, encoding="utf-8")

    project, issues = load_project(load_config(root))
    assert [i for i in issues if i.severity == "error"] == []
    started = time.monotonic()
    report = history.check_reopens(project)
    elapsed = time.monotonic() - started
    assert report.to_dict() == {"examined": 500, "limit": 500, "truncated": True, "shallow": False, "skipped": None}
    [issue] = report.issues
    assert issue.code == CODE and "T001" in issue.message and "Revision 900" in issue.message
    assert elapsed < 2.0, f"history check took {elapsed:.2f}s"


def test_repository_without_commits_is_skipped(tmp_path: Path, capsys):
    repo = Repo(tmp_path)
    repo.write(".taskrail/config.toml", BASE_CONFIG)
    repo.write("TODO.md", BASE_TODO)
    git(tmp_path, "init", "-q", "-b", "main")
    code, data = validate(repo, capsys)
    assert code == 0
    assert data["history"]["skipped"] == "no commits"
