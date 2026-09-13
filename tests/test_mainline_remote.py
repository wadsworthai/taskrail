"""Each mainline's own remote: `branch.<mainline>.remote` before `[review].remote`."""

import json
from pathlib import Path

import pytest
from conftest import BASE_TODO, git

from taskrail import review
from taskrail.cli import main

BRANCH = "T002-repricing"

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


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def run_json(root, *argv, capsys, expect=0):
    code, out, err = run(root, *argv, "--json", capsys=capsys)
    assert code == expect, err
    return json.loads(out) if out.strip() else None


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def advance(repo, remote, tmp_path_factory, branch="main", todo=None):
    """Push a new commit to `branch` on one of the bare remotes, without fetching it here."""
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(repo.root, "clone", "-q", "-b", branch, str(repo.bares[remote]), str(clone))
    if todo is not None:
        (clone / "TODO.md").write_text(todo)
    else:
        (clone / f"{remote.upper()}.md").write_text(f"{remote}\n")
    commit_all(clone, f"change on {remote}")
    git(clone, "push", "-q", "origin", branch)


@pytest.fixture
def two_remotes(git_repo, tmp_path_factory):
    """Bare `origin` and `upstream` remotes, both holding main; the local main tracks upstream."""
    remotes = tmp_path_factory.mktemp("remotes")
    git_repo.bares = {}
    for name in ("origin", "upstream"):
        bare = remotes / f"{name}.git"
        git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
        git(git_repo.root, "remote", "add", name, str(bare))
        git(git_repo.root, "push", "-q", name, "main")
        git_repo.bares[name] = bare
    git(git_repo.root, "branch", "-q", "--set-upstream-to=upstream/main", "main")
    return git_repo


def close_on_branch(repo, branch, file="TODO.md", content=None):
    git(repo.root, "checkout", "-q", "-b", branch)
    repo.write(file, content)
    commit_all(repo.root, f"chore: mark {branch} done")


# 1. show reports the base from the mainline's tracked remote.
def test_show_uses_the_remote_the_mainline_tracks(two_remotes, tmp_path_factory, capsys):
    advance(two_remotes, "upstream", tmp_path_factory)
    git(two_remotes.root, "fetch", "-q", "upstream")
    base = run_json(two_remotes.root, "show", "T002", capsys=capsys)["base"]
    assert base == {
        "onto": "upstream/main",
        "diverged": False,
        "reason": "upstream/main is up to date with or ahead of main",
        "remote": "upstream",
        "remote_source": "branch.main.remote",
        "commit": git(two_remotes.root, "rev-parse", "upstream/main"),
        "dependency": None,
    }
    assert "base upstream/main" in run(two_remotes.root, "show", "T002", capsys=capsys)[1]


# 2. Without a usable tracking remote, [review].remote applies.
@pytest.mark.parametrize("tracked", [None, ".", "url", "nosuch"])
def test_show_falls_back_to_the_review_remote(two_remotes, tracked, capsys):
    if tracked is None:
        git(two_remotes.root, "branch", "-q", "--unset-upstream", "main")
    else:
        value = str(two_remotes.bares["upstream"]) if tracked == "url" else tracked
        git(two_remotes.root, "config", "branch.main.remote", value)
    base = run_json(two_remotes.root, "show", "T002", capsys=capsys)["base"]
    assert (base["onto"], base["remote"], base["remote_source"]) == ("origin/main", "origin", "[review].remote")


def test_resolve_remote_uses_the_configured_fallback(two_remotes):
    git(two_remotes.root, "branch", "-q", "--unset-upstream", "main")
    assert review.resolve_remote(two_remotes.root, "main", "upstream") == review.ResolvedRemote("upstream", "[review].remote")
    assert review.resolve_remote(two_remotes.root, "no-such-branch", "origin") == review.ResolvedRemote("origin", "[review].remote")
    git(two_remotes.root, "branch", "-q", "--set-upstream-to=origin/main", "main")
    assert review.resolve_remote(two_remotes.root, "main", "upstream") == review.ResolvedRemote("origin", "branch.main.remote")


# 3. new --workspace branches from the resolved remote.
def test_workspace_branches_from_the_mainline_remote(two_remotes, tmp_path_factory, capsys):
    advance(two_remotes, "upstream", tmp_path_factory, todo=BASE_TODO.replace("| Off by one  |", "| Off by two  |"))
    git(two_remotes.root, "fetch", "-q", "upstream")
    data = run_json(
        two_remotes.root, "new", "--epic", "E01", "--kind", "bug", "--title", "Negative totals", "--workspace", capsys=capsys
    )
    assert data["base"] == "upstream/main"
    assert "Off by two" in (Path(data["workspace"]) / "TODO.md").read_text()


# 4. review fetches the resolved remote and picks the rebase base against it.
def test_review_fetches_and_rebases_against_the_mainline_remote(two_remotes, tmp_path_factory, capsys):
    close_on_branch(two_remotes, BRANCH, content=BASE_TODO.replace("| ⬜ | T002 |", "| ✅ | T002 |"))
    advance(two_remotes, "upstream", tmp_path_factory)
    advance(two_remotes, "origin", tmp_path_factory)
    origin_before = git(two_remotes.root, "rev-parse", "refs/remotes/origin/main")
    data = run_json(two_remotes.root, "review", "T002", capsys=capsys)
    assert (data["remote"], data["remote_source"], data["fetched"]) == ("upstream", "branch.main.remote", True)
    assert (data["rebase"]["onto"], data["rebase"]["needed"]) == ("upstream/main", True)
    assert git(two_remotes.root, "rev-parse", "refs/remotes/upstream/main") == git(two_remotes.bares["upstream"], "rev-parse", "main")
    assert git(two_remotes.root, "rev-parse", "refs/remotes/origin/main") == origin_before


def test_a_failed_fetch_names_the_mainline_remote(two_remotes, capsys):
    close_on_branch(two_remotes, BRANCH, content=BASE_TODO.replace("| ⬜ | T002 |", "| ✅ | T002 |"))
    git(two_remotes.root, "remote", "set-url", "upstream", str(two_remotes.root / "missing.git"))
    code, _, err = run(two_remotes.root, "review", "T002", capsys=capsys)
    assert code == 2
    assert "git fetch upstream failed" in err


# 5. --publish pushes to the resolved remote only.
def test_publish_pushes_to_the_mainline_remote(two_remotes, tmp_path_factory, capsys):
    close_on_branch(two_remotes, BRANCH, content=BASE_TODO.replace("| ⬜ | T002 |", "| ✅ | T002 |"))
    data = run_json(two_remotes.root, "review", "T002", "--publish", capsys=capsys)
    assert data["push"]["pushed"] is True
    assert data["push"]["command"] == f"git push --set-upstream upstream HEAD:refs/heads/{BRANCH}"
    assert git(two_remotes.bares["upstream"], "rev-parse", BRANCH) == git(two_remotes.root, "rev-parse", "HEAD")
    assert git(two_remotes.bares["origin"], "branch", "--list", BRANCH) == ""

    config = two_remotes.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + "\n[git]\npush_task_branch = false\n")
    commit_all(two_remotes.root, "chore: stop pushing")
    unpushed = run_json(two_remotes.root, "review", "T002", "--publish", capsys=capsys)
    assert unpushed["push"]["command"].startswith(f"git push --set-upstream --force-with-lease={BRANCH}:")
    assert unpushed["push"]["command"].endswith(f" upstream HEAD:refs/heads/{BRANCH}")


# 6. The link points at the resolved remote's repository.
def test_link_points_at_the_mainline_remote_repository(two_remotes, capsys):
    close_on_branch(two_remotes, BRANCH, content=BASE_TODO.replace("| ⬜ | T002 |", "| ✅ | T002 |"))
    git(two_remotes.root, "remote", "set-url", "origin", "git@github.com:acme/product.git")
    git(two_remotes.root, "remote", "set-url", "upstream", "git@github.com:acme/template.git")
    data = run_json(two_remotes.root, "review", "T002", "--no-fetch", capsys=capsys)
    assert data["pull_request"]["provider"] == "github"
    assert data["pull_request"]["url"].startswith(f"https://github.com/acme/template/compare/main...{BRANCH}?quick_pull=1")


# 7. Two backlogs whose mainlines track different remotes.
def test_each_backlog_resolves_its_own_mainline_remote(two_remotes, tmp_path_factory, capsys):
    root = two_remotes.root
    two_remotes.write(".taskrail/config.toml", TWO_BACKLOGS)
    two_remotes.write("APP_TODO.md", APP_TODO)
    commit_all(root, "chore: add the product backlog")
    git(root, "push", "-q", "upstream", "main")
    git(root, "branch", "-q", "dev")
    git(root, "push", "-q", "--set-upstream", "origin", "dev")
    advance(two_remotes, "upstream", tmp_path_factory)
    advance(two_remotes, "origin", tmp_path_factory, branch="dev")
    git(root, "fetch", "-q", "--all")

    template = run_json(root, "show", "T002", capsys=capsys)["base"]
    product = run_json(root, "show", "A001", capsys=capsys)["base"]
    assert (template["onto"], template["remote_source"]) == ("upstream/main", "branch.main.remote")
    assert (product["onto"], product["remote_source"]) == ("origin/dev", "branch.dev.remote")

    git(root, "checkout", "-q", "dev")
    close_on_branch(two_remotes, "A001-sign-up", file="APP_TODO.md", content=APP_TODO.replace("| ⬜ | A001 |", "| ✅ | A001 |"))
    data = run_json(root, "review", "A001", "--no-fetch", capsys=capsys)
    assert (data["target"], data["remote"], data["rebase"]["onto"]) == ("dev", "origin", "origin/dev")
