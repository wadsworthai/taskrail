import json
import subprocess
import sys
from pathlib import Path

from conftest import BASE_TODO, git

from taskrail.cli import main

NEW_ROW = "| ⬜ | T003 | bug     | 1   | T002       | Rounding error | Off by one  |"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def test_reserve_starts_above_the_highest_existing_id(git_repo, capsys):
    code, out, _ = run(git_repo.root, "reserve-id", capsys=capsys)
    assert (code, out.strip()) == (0, "T004")


def test_reserved_ids_are_not_handed_out_twice(git_repo, capsys):
    first = run(git_repo.root, "reserve-id", capsys=capsys)[1].strip()
    second = run(git_repo.root, "reserve-id", capsys=capsys)[1].strip()
    assert (first, second) == ("T004", "T005")


def test_ids_on_other_branches_count(git_repo, capsys):
    git(git_repo.root, "checkout", "-q", "-b", "T010-elsewhere")
    git_repo.write("TODO.md", BASE_TODO + NEW_ROW.replace("T003", "T010").replace("T002       ", "—          ") + "\n")
    git(git_repo.root, "commit", "-q", "-am", "add T010 on a branch")
    git(git_repo.root, "checkout", "-q", "main")
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T011"


def test_uncommitted_ids_in_the_working_tree_count(git_repo, capsys):
    git_repo.write("TODO.md", BASE_TODO + NEW_ROW.replace("T003", "T020") + "\n")
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T021"


def test_ids_in_epic_files_on_branches_count(git_repo, capsys):
    listing, section = BASE_TODO.split("## E01 — Billing")
    git(git_repo.root, "checkout", "-q", "-b", "split")
    git_repo.write("TODO.md", listing.replace("| —    |", "| todo/E01.md |"))
    git_repo.write("todo/E01.md", "## E01 — Billing" + section.replace("T003", "T030"))
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "split epic")
    git(git_repo.root, "checkout", "-q", "main")
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T031"


def test_a_reservation_is_dropped_once_the_id_is_used(git_repo, capsys):
    reserved = run(git_repo.root, "reserve-id", capsys=capsys)[1].strip()
    git_repo.write("TODO.md", BASE_TODO + NEW_ROW.replace("T003", reserved) + "\n")
    git(git_repo.root, "commit", "-q", "-am", "use it")
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T005"
    state = Path(git(git_repo.root, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "taskrail/reserved/main.json"
    assert [r["id"] for r in json.loads(state.read_text())] == ["T005"]


def test_unreserve(git_repo, capsys):
    run(git_repo.root, "reserve-id", capsys=capsys)
    assert run(git_repo.root, "unreserve-id", "T004", capsys=capsys)[0] == 0
    assert run(git_repo.root, "unreserve-id", "T004", capsys=capsys)[0] == 3
    assert run(git_repo.root, "reserve-id", capsys=capsys)[1].strip() == "T004"


def test_concurrent_reservations_never_collide(git_repo):
    script = "from taskrail.cli import main; raise SystemExit(main(['--root', r'%s', 'reserve-id']))" % git_repo.root
    processes = [
        subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True) for _ in range(12)
    ]
    results = [p.communicate()[0].strip() for p in processes]
    assert all(p.returncode == 0 for p in processes)
    assert sorted(results) == [f"T{n:03d}" for n in range(4, 16)]
