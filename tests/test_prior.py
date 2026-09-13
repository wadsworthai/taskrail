"""Signs of prior work on a task, as reported by `show` (T023)."""

import json

import pytest
from conftest import git

from taskrail import prior
from taskrail.cli import main

# T002 is a feature titled "Repricing" in the test backlog.
BRANCH = "T002-repricing"
ARTIFACT = "docs/features/T002-repricing.md"


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def show(root, capsys, task="T002"):
    code, out, err = run(root, "show", task, "--json", capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def commit(root, subject, body=None, path="NOTES.md"):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("a") as handle:
        handle.write(f"{subject}\n")
    git(root, "add", "-A")
    args = ["-q", "-m", subject]
    if body:
        args += ["-m", body]
    git(root, "commit", *args)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def remote_repo(git_repo, tmp_path_factory):
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    git_repo.bare = bare
    return git_repo


def test_nothing_found_reports_empty_signals(git_repo, capsys):
    data = show(git_repo.root, capsys)
    assert data["prior_work"] == {"artifact": [], "branches": [], "commits": [], "commits_total": 0}


def test_artifact_in_the_working_tree_only(git_repo, capsys):
    git_repo.write(ARTIFACT, "# T002\n")
    assert show(git_repo.root, capsys)["prior_work"]["artifact"] == ["working tree"]


def test_artifact_on_local_and_remote_tracking_branch_tips(remote_repo, capsys):
    root = remote_repo.root
    git(root, "switch", "-q", "-c", "elsewhere")
    commit(root, "docs: a plan", path=ARTIFACT)
    git(root, "push", "-q", "origin", "elsewhere")
    git(root, "switch", "-q", "main")
    assert show(root, capsys)["prior_work"]["artifact"] == ["elsewhere", "origin/elsewhere"]


def test_artifact_check_reads_branch_tips_not_history(git_repo, capsys):
    root = git_repo.root
    commit(root, "docs: a plan", path=ARTIFACT)
    git(root, "rm", "-q", ARTIFACT)
    git(root, "commit", "-q", "-m", "docs: drop the plan")
    assert show(root, capsys)["prior_work"]["artifact"] == []


def test_task_branch_locally_and_on_a_remote(remote_repo, capsys):
    root = remote_repo.root
    git(root, "branch", BRANCH)
    assert show(root, capsys)["prior_work"]["branches"] == [BRANCH]
    git(root, "push", "-q", "origin", BRANCH)
    git(root, "fetch", "-q", "origin")
    assert show(root, capsys)["prior_work"]["branches"] == [BRANCH, f"origin/{BRANCH}"]
    git(root, "branch", "-D", "-q", BRANCH)
    assert show(root, capsys)["prior_work"]["branches"] == [f"origin/{BRANCH}"]


def test_a_branch_sharing_the_prefix_is_not_the_task_branch(remote_repo, capsys):
    root = remote_repo.root
    for name in (f"{BRANCH}-v2", f"{BRANCH}/sub", f"old/{BRANCH}"):
        git(root, "branch", name)
    git(root, "push", "-q", "origin", f"{BRANCH}-v2")
    git(root, "fetch", "-q", "origin")
    assert show(root, capsys)["prior_work"]["branches"] == []


@pytest.mark.parametrize(
    ("subject", "match"),
    [
        ("T002 recompute prices", "prefix"),
        ("T002: recompute prices", "prefix"),
        ("chore(T002): mark done", "scope"),
        ("fix(billing,T002)!: recompute prices", "scope"),
        ("feat(billing): recompute prices (T002)", "suffix"),
        ("feat(billing): recompute prices (T002) (#4)", "suffix"),
        ("feat(billing): recompute prices (T002) (!4)", "suffix"),
        (f"Merge pull request #1 from owner/{BRANCH}", "branch"),
    ],
)
def test_commit_subject_forms(git_repo, capsys, subject, match):
    sha = commit(git_repo.root, subject)
    data = show(git_repo.root, capsys)["prior_work"]
    assert data["commits"] == [{"sha": sha, "subject": subject, "match": match}]
    assert data["commits_total"] == 1


@pytest.mark.parametrize(
    ("subject", "body"),
    [
        ("chore(T001): open follow-ups T002 and T003", None),
        ("T0023 is something else", None),
        ("chore(T0020): mark done", None),
        ("feat: recompute (T0021)", None),
        ("chore: tidy up", "Relates to T002.\n\nReopens: T002"),
        (f"Merge pull request #1 from owner/{BRANCH}-v2", None),
    ],
)
def test_subjects_that_do_not_name_the_task(git_repo, capsys, subject, body):
    commit(git_repo.root, subject, body)
    assert show(git_repo.root, capsys)["prior_work"]["commits"] == []


def test_commits_on_unmerged_local_and_remote_branches(remote_repo, capsys):
    root = remote_repo.root
    git(root, "switch", "-q", "-c", "local-only")
    local = commit(root, "T002 local attempt")
    git(root, "switch", "-q", "main")
    git(root, "switch", "-q", "-c", "pushed")
    pushed = commit(root, "chore(T002): pushed attempt")
    git(root, "push", "-q", "origin", "pushed")
    git(root, "switch", "-q", "main")
    git(root, "branch", "-D", "-q", "pushed")
    shas = {c["sha"] for c in show(root, capsys)["prior_work"]["commits"]}
    assert shas == {local, pushed}


def test_claim_refs_and_tags_are_not_searched_and_commits_appear_once(git_repo, capsys):
    root = git_repo.root
    git(root, "switch", "-q", "-c", "side")
    shared = commit(root, "T002 shared attempt")
    git(root, "switch", "-q", "main")
    git(root, "branch", "side-copy", "side")
    git(root, "switch", "-q", "-c", "tagged")
    commit(root, "T002 only tagged")
    git(root, "tag", "attempt")
    git(root, "switch", "-q", "main")
    git(root, "branch", "-D", "-q", "tagged")
    claim_commit = git(root, "commit-tree", "HEAD^{tree}", "-m", "T002 claim")
    git(root, "update-ref", "refs/taskrail/claims/T002", claim_commit)
    data = show(root, capsys)["prior_work"]
    assert [c["sha"] for c in data["commits"]] == [shared]
    assert data["commits_total"] == 1


def test_commits_are_capped_newest_first(git_repo, capsys):
    root = git_repo.root
    for n in range(prior.MAX_COMMITS + 2):
        git(root, "commit", "-q", "--allow-empty", "-m", f"chore(T002): step {n}")
    data = show(root, capsys)["prior_work"]
    assert data["commits_total"] == prior.MAX_COMMITS + 2
    assert len(data["commits"]) == prior.MAX_COMMITS
    assert data["commits"][0]["subject"] == f"chore(T002): step {prior.MAX_COMMITS + 1}"


def test_signals_never_change_exit_code_or_state(git_repo, capsys):
    root = git_repo.root
    before = show(root, capsys)["state"]
    git_repo.write(ARTIFACT, "# T002\n")
    commit(root, "chore(T002): earlier attempt")
    git(root, "branch", BRANCH)
    data = show(root, capsys)  # asserts exit 0
    assert data["state"] == before == "pending"
    assert data["prior_work"]["commits_total"] == 1


def test_state_is_the_same_with_and_without_signals(git_repo, capsys):
    root = git_repo.root
    before = show(root, capsys, task="T003")["state"]
    commit(root, "fix(T003): earlier attempt")
    git(root, "branch", "T003-rounding-error")
    after = show(root, capsys, task="T003")
    assert after["state"] == before
    assert after["prior_work"]["branches"] == ["T003-rounding-error"]


def test_outside_git_only_the_working_tree_is_checked(repo, capsys):
    assert show(repo.root, capsys)["prior_work"] == {"artifact": [], "branches": [], "commits": [], "commits_total": 0}
    repo.write(ARTIFACT, "# T002\n")
    assert show(repo.root, capsys)["prior_work"]["artifact"] == ["working tree"]


def test_repository_without_commits(repo, capsys):
    git(repo.root, "init", "-q", "-b", "main")
    assert show(repo.root, capsys)["prior_work"]["commits"] == []


def test_text_output_lists_each_kind_of_signal(git_repo, capsys):
    root = git_repo.root
    _, out, _ = run(root, "show", "T002", capsys=capsys)
    assert "prior work" not in out
    git_repo.write(ARTIFACT, "# T002\n")
    sha = commit(root, "chore(T002): earlier attempt")
    git(root, "branch", BRANCH)
    _, out, _ = run(root, "show", "T002", capsys=capsys)
    assert f"prior work: artifact {ARTIFACT} in working tree" in out
    assert f"prior work: branch {BRANCH}" in out
    assert "prior work: 1 commit(s) naming T002" in out
    assert f"{sha[:7]} chore(T002): earlier attempt" in out


def test_list_and_next_do_not_search_for_prior_work(git_repo, capsys):
    commit(git_repo.root, "chore(T002): earlier attempt")
    for command in ("list", "next"):
        code, out, err = run(git_repo.root, command, "--json", capsys=capsys)
        assert code == 0, err
        assert all("prior_work" not in task for task in json.loads(out))
