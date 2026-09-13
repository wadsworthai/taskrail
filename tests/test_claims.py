import json
import shutil
from datetime import datetime, timedelta, timezone

import pytest
from conftest import BASE_CONFIG, git

from taskrail import claims
from taskrail.cli import main
from taskrail.config import load_config


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def test_claim_then_conflict_for_another_owner(git_repo, capsys):
    assert run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    code, _, err = run(git_repo.root, "claim", "T002", "--owner", "bob", capsys=capsys)
    assert code == 4
    assert "claimed by alice" in err


def test_reclaim_by_the_same_owner_is_idempotent(git_repo, capsys):
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    code, out, _ = run(git_repo.root, "claim", "T002", "--owner", "alice", "--json", capsys=capsys)
    assert code == 0
    assert json.loads(out)["created"] is False


@pytest.mark.parametrize(("task", "reason"), [("T001", "done, not pending"), ("T003", "blocked by T002")])
def test_claim_refuses_done_and_blocked_tasks(git_repo, capsys, task, reason):
    code, _, err = run(git_repo.root, "claim", task, capsys=capsys)
    assert code == 5
    assert reason in err


def test_blocked_task_can_be_claimed_explicitly(git_repo, capsys):
    assert run(git_repo.root, "claim", "T003", "--ignore-deps", capsys=capsys)[0] == 0


def test_claimed_tasks_leave_next_and_show_their_claim(git_repo, capsys):
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    _, out, _ = run(git_repo.root, "next", "--json", capsys=capsys)
    assert json.loads(out) == []
    _, out, _ = run(git_repo.root, "show", "T002", "--json", capsys=capsys)
    data = json.loads(out)
    assert data["state"] == "claimed"
    assert data["claim"]["owner"] == "alice"


def test_release_requires_ownership_or_force(git_repo, capsys):
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    assert run(git_repo.root, "release", "T002", "--owner", "bob", capsys=capsys)[0] == 4
    assert run(git_repo.root, "release", "T002", "--owner", "bob", "--force", capsys=capsys)[0] == 0
    assert run(git_repo.root, "release", "T002", capsys=capsys)[0] == 3


def test_claims_are_shared_between_worktrees(git_repo, tmp_path, capsys):
    other = tmp_path.parent / (tmp_path.name + "-wt")
    git(git_repo.root, "worktree", "add", "-q", "-b", "T002-repricing", str(other))
    assert run(other, "claim", "T002", "--owner", "lane-1", capsys=capsys)[0] == 0
    code, _, err = run(git_repo.root, "claim", "T002", "--owner", "lane-2", capsys=capsys)
    assert code == 4
    assert "T002-repricing" in err


def test_removed_worktree_makes_a_claim_stale_and_takeover_replaces_it(git_repo, tmp_path, capsys):
    other = tmp_path.parent / (tmp_path.name + "-gone")
    git(git_repo.root, "worktree", "add", "-q", "-b", "T002-repricing", str(other))
    run(other, "claim", "T002", "--owner", "lane-1", capsys=capsys)
    shutil.rmtree(other)
    git(git_repo.root, "worktree", "prune")

    code, _, err = run(git_repo.root, "claim", "T002", "--owner", "lane-2", capsys=capsys)
    assert code == 4
    assert "stale" in err and "--takeover" in err
    assert run(git_repo.root, "claim", "T002", "--owner", "lane-2", "--takeover", capsys=capsys)[0] == 0


def test_takeover_does_not_replace_a_live_claim(git_repo, capsys):
    run(git_repo.root, "claim", "T002", "--owner", "alice", capsys=capsys)
    assert run(git_repo.root, "claim", "T002", "--owner", "bob", "--takeover", capsys=capsys)[0] == 4


def test_missing_branch_is_stale_only_after_the_grace_period(git_repo):
    config = load_config(git_repo.root)
    claim, _ = claims.claim(config, "T002", "alice", branch="T002-not-yet", worktree=None)
    assert claims.stale_reason(config, claim) is None
    later = datetime.now(timezone.utc) + timedelta(minutes=config.claim_grace_minutes)
    assert "no longer exists" in claims.stale_reason(config, claim, now=later)


def test_claims_listing_reports_staleness(git_repo, capsys):
    config = load_config(git_repo.root)
    claims.claim(config, "T002", "alice", branch="main", worktree="/nowhere")
    _, out, _ = run(git_repo.root, "claims", "--json", capsys=capsys)
    [row] = json.loads(out)["local"]
    assert row["id"] == "T002"
    assert "no longer exists" in row["stale"]


def test_claims_need_a_git_repository(repo, capsys):
    code, _, err = run(repo.root, "claim", "T002", capsys=capsys)
    assert code == 2
    assert "not inside a git repository" in err


@pytest.fixture
def remote_pair(git_repo, tmp_path_factory, capsys):
    """Two clones of one bare remote, both configured to mirror claims to it."""
    bare = tmp_path_factory.mktemp("remote") / "origin.git"
    git(git_repo.root, "init", "-q", "--bare", "-b", "main", str(bare))
    config = BASE_CONFIG + '\n[git]\nclaim_remote = "origin"\n'
    git_repo.write(".taskrail/config.toml", config)
    git(git_repo.root, "commit", "-q", "-am", "claim remote")
    git(git_repo.root, "remote", "add", "origin", str(bare))
    git(git_repo.root, "push", "-q", "origin", "main")
    second = tmp_path_factory.mktemp("clone") / "second"
    git(bare.parent, "clone", "-q", str(bare), str(second))
    return git_repo.root, second, bare


def test_remote_claim_blocks_another_clone(remote_pair, capsys):
    first, second, bare = remote_pair
    assert run(first, "claim", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    assert git(bare, "for-each-ref", "refs/taskrail/claims").endswith("refs/taskrail/claims/T002")

    code, _, err = run(second, "claim", "T002", "--owner", "bob", capsys=capsys)
    assert code == 4
    assert "on origin by alice" in err
    _, out, _ = run(second, "claims", "--remote", "--json", capsys=capsys)
    assert json.loads(out)["remote_only"] == ["T002"]
    assert run(second, "claims", "--json", capsys=capsys)[0] == 0


def test_releasing_a_remote_claim_deletes_the_ref(remote_pair, capsys):
    first, second, bare = remote_pair
    run(first, "claim", "T002", "--owner", "alice", capsys=capsys)
    assert run(first, "release", "T002", "--owner", "alice", capsys=capsys)[0] == 0
    assert git(bare, "for-each-ref", "refs/taskrail/claims") == ""
    assert run(second, "claim", "T002", "--owner", "bob", capsys=capsys)[0] == 0


def test_local_only_claim_skips_the_remote(remote_pair, capsys):
    first, _, bare = remote_pair
    assert run(first, "claim", "T002", "--local-only", capsys=capsys)[0] == 0
    assert git(bare, "for-each-ref", "refs/taskrail/claims") == ""
