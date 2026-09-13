"""Signs that someone may already have worked on a task: informational, never blocking."""

from __future__ import annotations

import re
from pathlib import Path

from taskrail import gitutil

MAX_COMMITS = 10
WORKING_TREE = "working tree"
_WORD = "A-Za-z0-9_"


def _short(ref: str) -> str:
    for prefix in ("refs/heads/", "refs/remotes/"):
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return ref


def _branch_refs(root: Path) -> list[str]:
    """Local branches, then remote-tracking branches, each sorted by name."""
    return gitutil.refs(root, "refs/heads") + gitutil.refs(root, "refs/remotes")


def artifact_locations(root: Path, artifact: str | None, branch_refs: list[str]) -> list[str]:
    """The working tree, then every branch tip, where the artifact file exists."""
    if not artifact:
        return []
    found = [WORKING_TREE] if (root / artifact).is_file() else []
    specs = [f"{ref}:{artifact}" for ref in branch_refs]
    try:
        blobs = gitutil.read_blobs(root, specs)
    except gitutil.GitError:
        return found
    return found + [_short(ref) for ref, spec in zip(branch_refs, specs) if blobs.get(spec) is not None]


def task_branches(branch: str | None, branch_refs: list[str]) -> list[str]:
    """The task branch as a local branch and under each remote-tracking namespace."""
    if not branch:
        return []
    found = []
    for ref in branch_refs:
        if ref == f"refs/heads/{branch}":
            found.append(branch)
        elif ref.startswith("refs/remotes/"):
            remote, _, name = ref[len("refs/remotes/"):].partition("/")
            if remote and name == branch:
                found.append(f"{remote}/{branch}")
    return found


def subject_patterns(task_id: str, branch: str | None) -> list[tuple[str, re.Pattern]]:
    """How a commit subject names a task, in the order a match is reported."""
    escaped = re.escape(task_id)
    word = rf"(?<![{_WORD}]){escaped}(?![{_WORD}])"
    patterns = [
        ("prefix", re.compile(rf"^{word}")),
        ("scope", re.compile(rf"^[A-Za-z]+\([^)]*{word}[^)]*\)!?:")),
        ("suffix", re.compile(rf"\({escaped}\)(?:\s+\([#!]\d+\))?\s*$")),
    ]
    if branch:
        patterns.append(("branch", re.compile(rf"(?<![{_WORD}-]){re.escape(branch)}(?![{_WORD}-])")))
    return patterns


def classify(subject: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    return next((name for name, pattern in patterns if pattern.search(subject)), None)


def matching_commits(root: Path, task_id: str, branch: str | None) -> list[dict]:
    """Commits on HEAD, local and remote-tracking branches whose subject names the task, newest first."""
    revisions = ["--branches", "--remotes"]
    if gitutil.run(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False).returncode == 0:
        revisions.insert(0, "HEAD")
    # git pre-filters on the ID anywhere in the message; the subject forms are checked here.
    result = gitutil.run(
        root, "log", *revisions, "--fixed-strings", f"--grep={task_id}", "--format=%H%x1f%s", "--", check=False
    )
    if result.returncode != 0:
        return []
    patterns = subject_patterns(task_id, branch)
    commits = []
    for line in result.stdout.splitlines():
        sha, _, subject = line.partition("\x1f")
        match = classify(subject, patterns)
        if match:
            commits.append({"sha": sha, "subject": subject, "match": match})
    return commits


def prior_work(root: Path, task_id: str, branch: str | None, artifact: str | None) -> dict:
    try:
        gitutil.common_dir(root)
        branch_refs = _branch_refs(root)
    except gitutil.GitError:
        found = [WORKING_TREE] if artifact and (root / artifact).is_file() else []
        return {"artifact": found, "branches": [], "commits": [], "commits_total": 0}
    commits = matching_commits(root, task_id, branch)
    return {
        "artifact": artifact_locations(root, artifact, branch_refs),
        "branches": task_branches(branch, branch_refs),
        "commits": commits[:MAX_COMMITS],
        "commits_total": len(commits),
    }


def text_lines(data: dict, task_id: str, artifact: str | None) -> list[str]:
    lines = []
    if data["artifact"]:
        lines.append(f"  prior work: artifact {artifact} in {', '.join(data['artifact'])}")
    if data["branches"]:
        lines.append(f"  prior work: branch {', '.join(data['branches'])}")
    if data["commits_total"]:
        lines.append(f"  prior work: {data['commits_total']} commit(s) naming {task_id}")
        lines.extend(f"    {commit['sha'][:7]} {commit['subject']}" for commit in data["commits"])
    return lines
