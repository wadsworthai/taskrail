import json

import pytest
from conftest import BASE_CONFIG, BASE_TODO, git

from taskrail import review
from taskrail.cli import main
from taskrail.config import ReviewConfig, load_config
from taskrail.issues import ConfigError

BRANCH = "T002-repricing"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def review_json(root, *argv, capsys, expect=0):
    code, out, err = run(root, "review", "T002", "--json", *argv, capsys=capsys)
    assert code == expect, err
    return json.loads(out) if out.strip() else None


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


@pytest.fixture
def task_repo(git_repo, tmp_path_factory):
    """A repository with a bare origin, and T002 closed on its own branch."""
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git(git_repo.root, "checkout", "-q", "-b", BRANCH)
    git_repo.write("TODO.md", BASE_TODO.replace("| ⬜ | T002 |", "| ✅ | T002 |"))
    commit_all(git_repo.root, "chore(T002): mark done")
    git_repo.bare = bare
    return git_repo


def advance_remote_main(repo, tmp_path_factory):
    clone = tmp_path_factory.mktemp("other") / "clone"
    git(repo.root, "clone", "-q", str(repo.bare), str(clone))
    (clone / "NOTES.md").write_text("elsewhere\n")
    commit_all(clone, "docs: note")
    git(clone, "push", "-q", "origin", "main")


def test_review_runs_only_on_the_task_branch(task_repo, capsys):
    git(task_repo.root, "checkout", "-q", "main")
    code, _, err = run(task_repo.root, "review", "T002", capsys=capsys)
    assert code == 5
    assert "task branch T002-repricing" in err


def test_review_requires_the_task_to_be_done(task_repo, capsys):
    git(task_repo.root, "checkout", "-q", "main")
    git(task_repo.root, "checkout", "-q", "-b", "T003-rounding-error")
    code, _, err = run(task_repo.root, "review", "T003", "--no-fetch", capsys=capsys)
    assert code == 5
    assert "run `taskrail done T003` first" in err


def test_prepare_reports_target_head_and_title(task_repo, capsys):
    data = review_json(task_repo.root, capsys=capsys)
    assert (data["head"], data["target"], data["fetched"]) == (BRANCH, "main", True)
    assert data["rebase"] == {
        "enabled": True, "onto": "origin/main", "diverged": False, "needed": False,
        "reason": "origin/main is up to date with or ahead of main", "dependency": None,
    }
    assert data["pull_request"]["title"] == "feat: repricing (T002)"
    assert data["pull_request"]["provider"] == "none" and data["pull_request"]["url"] is None
    assert data["published"] is False


def test_no_fetch_flag_and_config(task_repo, capsys):
    assert review_json(task_repo.root, "--no-fetch", capsys=capsys)["fetched"] is False
    config = task_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + "\n[review]\nfetch = false\n")
    assert review_json(task_repo.root, capsys=capsys)["fetched"] is False


def test_failed_fetch_is_a_usage_error(task_repo, capsys):
    git(task_repo.root, "remote", "set-url", "origin", str(task_repo.root / "missing.git"))
    code, _, err = run(task_repo.root, "review", "T002", capsys=capsys)
    assert code == 2
    assert "git fetch origin failed" in err


def test_remote_ahead_requires_a_rebase_before_publishing(task_repo, tmp_path_factory, capsys):
    advance_remote_main(task_repo, tmp_path_factory)
    data = review_json(task_repo.root, capsys=capsys)
    assert (data["rebase"]["onto"], data["rebase"]["needed"]) == ("origin/main", True)
    assert run(task_repo.root, "review", "T002", "--publish", capsys=capsys)[0] == 5
    git(task_repo.root, "rebase", "-q", "origin/main")
    published = review_json(task_repo.root, "--publish", capsys=capsys)
    assert published["published"] and published["push"]["pushed"]
    assert git(task_repo.bare, "rev-parse", BRANCH) == git(task_repo.root, "rev-parse", "HEAD")


def test_local_mainline_ahead_is_the_base(task_repo, capsys):
    git(task_repo.root, "checkout", "-q", "main")
    (task_repo.root / "LOCAL.md").write_text("local\n")
    commit_all(task_repo.root, "docs: local")
    git(task_repo.root, "checkout", "-q", BRANCH)
    data = review_json(task_repo.root, capsys=capsys)
    assert (data["rebase"]["onto"], data["rebase"]["needed"]) == ("main", True)


def test_diverged_mainlines_stop_the_review(task_repo, tmp_path_factory, capsys):
    advance_remote_main(task_repo, tmp_path_factory)
    git(task_repo.root, "fetch", "-q", "origin")
    git(task_repo.root, "checkout", "-q", "main")
    (task_repo.root / "LOCAL.md").write_text("local\n")
    commit_all(task_repo.root, "docs: local")
    git(task_repo.root, "checkout", "-q", BRANCH)
    data = review_json(task_repo.root, capsys=capsys, expect=5)
    assert data["rebase"]["diverged"] is True and data["rebase"]["onto"] is None


def test_rebase_can_be_disabled(task_repo, tmp_path_factory, capsys):
    advance_remote_main(task_repo, tmp_path_factory)
    config = task_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + "\n[review]\nrebase = false\n")
    data = review_json(task_repo.root, capsys=capsys)
    assert data["rebase"]["enabled"] is False and data["rebase"]["onto"] is None
    assert review_json(task_repo.root, "--publish", capsys=capsys)["push"]["pushed"] is True


def test_push_disabled_returns_the_command(task_repo, capsys):
    config = task_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + "\n[git]\npush_task_branch = false\n")
    data = review_json(task_repo.root, "--publish", capsys=capsys)
    assert data["published"] and not data["push"]["pushed"]
    assert data["push"]["command"] == f"git push --set-upstream origin HEAD:refs/heads/{BRANCH}"
    assert git(task_repo.bare, "branch", "--list", BRANCH) == ""


def test_republishing_uses_a_lease_and_a_moved_branch_is_rejected(task_repo, tmp_path_factory, capsys):
    review_json(task_repo.root, "--publish", capsys=capsys)
    (task_repo.root / "MORE.md").write_text("more\n")
    commit_all(task_repo.root, "docs(T002): more")
    first = review.push_command(task_repo.root, "origin", BRANCH)
    assert first[3].startswith(f"--force-with-lease={BRANCH}:")

    clone = tmp_path_factory.mktemp("rival") / "clone"
    git(task_repo.root, "clone", "-q", "-b", BRANCH, str(task_repo.bare), str(clone))
    (clone / "RIVAL.md").write_text("rival\n")
    commit_all(clone, "docs: rival")
    git(clone, "push", "-q", "origin", BRANCH)
    # The lease is computed from the remote's current state, so the push itself is what must fail:
    # simulate a stale lease by pushing with the earlier sha.
    result = __import__("subprocess").run(first, cwd=task_repo.root, capture_output=True, text=True)
    assert result.returncode != 0


def test_rejected_push_exits_with_conflict(task_repo, capsys, monkeypatch):
    monkeypatch.setattr(review, "push", lambda root, remote, branch: review.PushResult(False, ["git", "push"], "stale info"))
    code, _, err = run(task_repo.root, "review", "T002", "--publish", capsys=capsys)
    assert code == 4
    assert "push rejected: stale info" in err


def test_title_type_scope_and_breaking(task_repo, capsys):
    config = task_repo.root / ".taskrail/config.toml"
    config.write_text(config.read_text() + '\n[review]\nscope = "billing"\n')
    assert review_json(task_repo.root, "--no-fetch", capsys=capsys)["pull_request"]["title"] == "feat(billing): repricing (T002)"
    data = review_json(task_repo.root, "--no-fetch", "--type", "perf", "--scope", "", "--breaking", capsys=capsys)
    assert data["pull_request"]["title"] == "perf!: repricing (T002)"


@pytest.mark.parametrize(("title", "expected"), [("Repricing", "repricing"), ("API tokens expire", "API tokens expire"), ("I", "i")])
def test_subject_keeps_acronyms(title, expected):
    assert review.subject(title) == expected


def test_body_carries_reopens_trailers(task_repo, capsys):
    (task_repo.root / "FIX.md").write_text("fix\n")
    git(task_repo.root, "add", "-A")
    git(task_repo.root, "commit", "-q", "-m", "Reopen T001: Price table\n\nPrices were wrong\n\nReopens: T001")
    body = review_json(task_repo.root, capsys=capsys)["pull_request"]["body"]
    assert body.startswith("Task: T002 — Repricing\nArtifact: docs/features/T002-repricing.md\n")
    assert body.endswith("\nReopens: T001\n")


@pytest.mark.parametrize(
    ("url", "host", "path"),
    [
        ("git@github.com:octo-org/octo-repo.git", "github.com", "octo-org/octo-repo"),
        ("ssh://git@gitlab.example.com:2222/group/sub/project.git", "gitlab.example.com", "group/sub/project"),
        ("https://gitlab.com/group/sub/project", "gitlab.com", "group/sub/project"),
        ("https://user@codeberg.org/owner/repo.git/", "codeberg.org", "owner/repo"),
    ],
)
def test_parse_remote_url(url, host, path):
    assert review.parse_remote_url(url) == review.Remote(host, path)


def test_local_path_remotes_have_no_web_address():
    assert review.parse_remote_url("/srv/git/repo.git") is None


def test_provider_detection():
    github = review.Remote("github.com", "o/r")
    assert review.detect_provider(ReviewConfig(), github) == "github"
    assert review.detect_provider(ReviewConfig(), review.Remote("git.example.com", "o/r")) == "none"
    assert review.detect_provider(ReviewConfig(provider="gitlab"), review.Remote("git.example.com", "o/r")) == "gitlab"
    assert review.detect_provider(ReviewConfig(url_template="{web_url}"), review.Remote("x.org", "o/r")) == "template"
    assert review.web_base(ReviewConfig(web_url="https://code.example.com"), github) == "https://code.example.com"


TITLE, BODY = "feat(taskrail): add review (T015)", "Task: T015\n"


def test_github_link():
    url = review.pull_request_url("github", "https://github.com", "o/r", "main", "T015-x", TITLE, BODY)
    assert url == "https://github.com/o/r/compare/main...T015-x?quick_pull=1&title=feat%28taskrail%29%3A%20add%20review%20%28T015%29&body=Task%3A%20T015%0A"


def test_gitlab_link():
    url = review.pull_request_url("gitlab", "https://gitlab.com", "g/sub/p", "main", "T015-x", TITLE, BODY)
    assert url.startswith("https://gitlab.com/g/sub/p/-/merge_requests/new?")
    assert "merge_request%5Bsource_branch%5D=T015-x" in url
    assert "merge_request%5Btarget_branch%5D=main" in url
    assert "merge_request%5Btitle%5D=feat%28taskrail%29%3A%20add%20review%20%28T015%29" in url
    assert "merge_request%5Bdescription%5D=Task%3A%20T015%0A" in url


def test_gitea_forgejo_and_template_links():
    assert review.pull_request_url("gitea", "https://git.example.com", "o/r", "dev", "T1-x", "t", "b") == (
        "https://git.example.com/o/r/compare/dev...T1-x?title=t&body=b"
    )
    assert review.pull_request_url("forgejo", "https://codeberg.org", "o/r", "main", "T1-x", "t", "b") == (
        "https://codeberg.org/o/r/compare/main...T1-x"
    )
    template = "{web_url}/{repo}/pull-requests/new?source={head}&dest={base}&title={title}"
    assert review.pull_request_url("template", "https://bitbucket.org", "w/r", "main", "T1-x", "a b", "", template) == (
        "https://bitbucket.org/w/r/pull-requests/new?source=T1-x&dest=main&title=a%20b"
    )
    assert review.pull_request_url("none", "https://x", "o/r", "main", "h", "t", "b") is None


def test_an_over_long_body_is_dropped_from_the_link():
    url = review.pull_request_url("github", "https://github.com", "o/r", "main", "h", "t", "x" * 9000)
    assert "body=" not in url and "title=t" in url


def test_push_defaults_to_true_and_provider_is_checked(repo):
    assert load_config(repo.root).push_task_branch is True
    repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[review]\nprovider = "sourcehut"\n')
    with pytest.raises(ConfigError, match="review.provider"):
        load_config(repo.root)


def test_core_kinds_declare_commit_types(repo):
    kinds = repo.load()[0].kinds
    assert {name: kinds[name].commit_type for name in kinds} == {"bug": "fix", "chore": "chore", "feature": "feat", "spike": "docs"}
    repo.write(".taskrail/types/research/kind.toml", 'name = "research"\nsummary = "x"\nskill = "x"\ncommit_type = "Feat!"\n[[stage]]\nname = "a"\n')
    assert "kind-invalid" in repo.codes()
