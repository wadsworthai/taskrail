import json

from conftest import BASE_TODO

from taskrail.cli import build_parser, main


def run(repo, *argv, capsys):
    code = main(["--root", str(repo.root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def test_validate_exit_codes(repo, capsys):
    assert run(repo, "validate", capsys=capsys)[0] == 0
    repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |"))
    code, out, _ = run(repo, "validate", capsys=capsys)
    assert code == 1
    assert "task-kind-unknown" in out


def test_next_orders_by_points_then_file_order(repo, capsys):
    repo.write(
        "TODO.md",
        BASE_TODO.replace("| ⬜ | T002 | feature | 3   | T001 ", "| ⬜ | T002 | feature | 5   | —    ")
        .replace("| ⬜ | T003 | bug     | 1   | T002 ", "| ⬜ | T003 | bug     | 1   | —    "),
    )
    code, out, _ = run(repo, "next", "--json", capsys=capsys)
    assert code == 0
    assert [t["id"] for t in json.loads(out)] == ["T003", "T002"]


def test_next_excludes_blocked_tasks(repo, capsys):
    _, out, _ = run(repo, "next", "--json", capsys=capsys)
    assert [t["id"] for t in json.loads(out)] == ["T002"]


def test_next_limit_says_what_it_does_in_help():
    """T101: `--limit` shipped with no `help=`, so `next --help` printed the bare line `--limit LIMIT`."""
    commands = next(action for action in build_parser()._actions if action.dest == "command").choices
    assert commands["next"]._option_string_actions["--limit"].help
    assert "--limit N" in commands["next"].format_help()


def test_show_reports_blockers_and_skill(repo, capsys):
    code, out, _ = run(repo, "show", "T003", "--json", capsys=capsys)
    data = json.loads(out)
    assert code == 0
    assert data["state"] == "blocked"
    assert data["blocked_by"] == ["T002"]
    assert data["skill"] == "taskrail-bug"
    assert [s["name"] for s in data["kind_descriptor"]["stages"]] == ["diagnose", "fix", "impact"]


def test_show_unknown_task(repo, capsys):
    assert run(repo, "show", "T999", capsys=capsys)[0] == 3


def test_queries_refuse_an_invalid_backlog(repo, capsys):
    repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |"))
    code, _, err = run(repo, "next", capsys=capsys)
    assert code == 1
    assert "validation error" in err
    assert run(repo, "list", "--allow-invalid", capsys=capsys)[0] == 0


def test_list_filters(repo, capsys):
    _, out, _ = run(repo, "list", "--state", "blocked", "--json", capsys=capsys)
    assert [t["id"] for t in json.loads(out)] == ["T003"]


def test_missing_config_is_a_usage_error(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "validate"]) == 2
