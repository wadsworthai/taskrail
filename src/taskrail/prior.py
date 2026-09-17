"""Signs that someone may already have worked on a task: informational, never blocking."""

from __future__ import annotations

import re
from pathlib import Path

from taskrail import gitutil
from taskrail.ids import _epic_files
from taskrail.markdown import split_row

MAX_COMMITS = 10
WORKING_TREE = "working tree"
_WORD = "A-Za-z0-9_"
_ID_CELL = re.compile(r"^[A-Za-z]+\d+$")


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


def matching_commits(root: Path, task_id: str, branch: str | None, head_only: bool = False) -> list[dict]:
    """Commits on HEAD, and unless `head_only` local and remote-tracking branches, whose subject names the task, newest first."""
    revisions = [] if head_only else ["--branches", "--remotes"]
    if gitutil.run(root, "rev-parse", "--verify", "--quiet", "HEAD", check=False).returncode == 0:
        revisions.insert(0, "HEAD")
    elif head_only:
        return []
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


def _lines(root: Path, *args: str) -> list[str]:
    result = gitutil.run(root, *args, check=False)
    return [item for item in result.stdout.split("\0") if item] if result.returncode == 0 else []


def _only_the_row(diff: str, task_id: str) -> bool:
    """Whether a `--unified=0` diff only adds lines: one task row with the task's ID, plus at most a table header and separator."""
    rows, others = 0, 0
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("diff "):
            in_hunk = False  # a file's header lines follow, up to its first hunk
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line.startswith("\\"):
            continue
        if line.startswith("-"):
            return False
        if not line.startswith("+") or not line[1:].strip():
            continue
        cells = split_row(line[1:])
        if cells is None:
            return False
        if task_id in cells:
            rows += 1
        elif any(_ID_CELL.match(cell) for cell in cells):
            return False  # another task's row
        else:
            others += 1  # the header and separator `new` writes into an epic without a table
    return rows == 1 and others <= 2


def prepared_workspace(root: Path, task_id: str, branch: str | None, onto: str | None, backlog_file: str | None) -> dict | None:
    """The task's branch when it holds only the task's own row since its fork point, as `new --workspace` leaves it (T071).

    Compared with the merge-base of the branch and `onto`, the branch's content — its tip, plus the
    uncommitted and untracked changes of the worktree that has it checked out — may change only the
    backlog's files, and only by adding the task's row. None otherwise.
    """
    if not branch or not onto or not backlog_file or not gitutil.branch_exists(root, branch):
        return None
    ref = f"refs/heads/{branch}"
    fork = gitutil.run(root, "merge-base", ref, onto, check=False).stdout.strip()
    if not fork:
        return None
    worktree = gitutil.worktree_branches(root).get(branch)
    where = worktree if worktree is not None else root
    against = [fork] if worktree is not None else [fork, ref]  # a worktree compares its files, uncommitted ones included
    if worktree is not None and _lines(worktree, "ls-files", "-z", "--others", "--exclude-standard"):
        return None
    changed = _lines(where, "diff", "--no-renames", "--name-only", "-z", *against, "--")
    if worktree is not None:
        try:
            main = (worktree / backlog_file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
    else:
        main = gitutil.read_blobs(root, [f"{ref}:{backlog_file}"]).get(f"{ref}:{backlog_file}")
        if main is None:
            return None
    allowed = {backlog_file, *_epic_files(main)}
    if not changed or any(path not in allowed for path in changed):
        return None
    diff = gitutil.run(where, "diff", "--no-renames", "--no-color", "--unified=0", *against, "--", *changed, check=False)
    if diff.returncode != 0 or not _only_the_row(diff.stdout, task_id):
        return None
    committed = gitutil.run(root, "diff", "--no-renames", "--no-color", "--unified=0", fork, ref, "--", *allowed, check=False).stdout
    commits = gitutil.run(root, "rev-list", "--count", f"{fork}..{ref}", check=False).stdout.strip()
    return {
        "branch": branch,
        "worktree": str(worktree) if worktree is not None else None,
        "fork": fork,
        "commits": int(commits) if commits.isdigit() else 0,
        "row": "committed" if _only_the_row(committed, task_id) else "uncommitted",
    }


def prior_work(
    root: Path, task_id: str, branch: str | None, artifact: str | None, onto: str | None = None, backlog_file: str | None = None
) -> dict:
    """Signs of earlier work on a task; with `onto` and `backlog_file`, also whether its branch is a prepared workspace."""
    try:
        gitutil.common_dir(root)
        branch_refs = _branch_refs(root)
    except gitutil.GitError:
        found = [WORKING_TREE] if artifact and (root / artifact).is_file() else []
        return {"artifact": found, "branches": [], "commits": [], "commits_total": 0, "prepared": None}
    commits = matching_commits(root, task_id, branch)
    return {
        "artifact": artifact_locations(root, artifact, branch_refs),
        "branches": task_branches(branch, branch_refs),
        "commits": commits[:MAX_COMMITS],
        "commits_total": len(commits),
        "prepared": prepared_workspace(root, task_id, branch, onto, backlog_file),
    }


def text_lines(data: dict, task_id: str, artifact: str | None) -> list[str]:
    lines = []
    if data["artifact"]:
        lines.append(f"  prior work: artifact {artifact} in {', '.join(data['artifact'])}")
    if data["branches"]:
        prepared = " (prepared: only the task's row)" if data.get("prepared") else ""
        lines.append(f"  prior work: branch {', '.join(data['branches'])}{prepared}")
    if data["commits_total"]:
        lines.append(f"  prior work: {data['commits_total']} commit(s) naming {task_id}")
        lines.extend(f"    {commit['sha'][:7]} {commit['subject']}" for commit in data["commits"])
    return lines
