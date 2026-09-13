"""Thin wrappers around the git command line."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class GitError(Exception):
    """A git command failed, or the directory is not inside a git repository."""


# Fixed identity for the plumbing commits that carry remote claims; they are never merged.
_PLUMBING_ENV = {
    "GIT_AUTHOR_NAME": "taskrail",
    "GIT_AUTHOR_EMAIL": "taskrail@localhost",
    "GIT_COMMITTER_NAME": "taskrail",
    "GIT_COMMITTER_EMAIL": "taskrail@localhost",
}


def run(root: Path, *args: str, input: str | None = None, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            input=input,
            capture_output=True,
            text=True,
            env={**os.environ, **(env or {})},
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed") from exc
    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip() or result.stdout.strip()}")
    return result


def common_dir(root: Path) -> Path:
    result = run(root, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False)
    if result.returncode != 0:
        raise GitError(f"{root} is not inside a git repository")
    return Path(result.stdout.strip())


def toplevel(root: Path) -> Path:
    result = run(root, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        raise GitError(f"{root} is not inside a git repository")
    return Path(result.stdout.strip())


def current_branch(root: Path) -> str | None:
    result = run(root, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    return result.stdout.strip() or None


def branch_exists(root: Path, branch: str) -> bool:
    return run(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0


def worktrees(root: Path) -> set[Path]:
    output = run(root, "worktree", "list", "--porcelain").stdout
    return {Path(line[len("worktree "):]).resolve() for line in output.splitlines() if line.startswith("worktree ")}


def refs(root: Path, pattern: str) -> list[str]:
    output = run(root, "for-each-ref", "--format=%(refname)", pattern).stdout
    return [line for line in output.splitlines() if line and not line.endswith("/HEAD")]


def read_blobs(root: Path, specs: list[str]) -> dict[str, str | None]:
    """Read many `<rev>:<path>` blobs through one `git cat-file --batch` process."""
    if not specs:
        return {}
    process = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root,
        input="".join(f"{spec}\n" for spec in specs).encode(),
        capture_output=True,
    )
    if process.returncode != 0:
        raise GitError(f"git cat-file --batch: {process.stderr.decode().strip()}")
    data = process.stdout
    results: dict[str, str | None] = {}
    position = 0
    for spec in specs:
        end = data.index(b"\n", position)
        header = data[position:end].decode()
        position = end + 1
        if header.endswith(" missing") or header.endswith(" ambiguous"):
            results[spec] = None
            continue
        _, object_type, size = header.rsplit(" ", 2)
        content = data[position : position + int(size)]
        position += int(size) + 1  # skip the trailing newline
        results[spec] = content.decode("utf-8", errors="replace") if object_type == "blob" else None
    return results


def write_claim_commit(root: Path, content: str, message: str) -> str:
    """Store `content` as `claim.json` in a parentless commit and return its id."""
    blob = run(root, "hash-object", "-w", "--stdin", input=content).stdout.strip()
    tree = run(root, "mktree", input=f"100644 blob {blob}\tclaim.json\n").stdout.strip()
    return run(root, "commit-tree", tree, "-m", message, env=_PLUMBING_ENV).stdout.strip()
