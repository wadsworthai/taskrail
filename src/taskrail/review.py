"""Preparing a closed task for review: base selection, push, pull request title, body and link."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

from taskrail import gitutil
from taskrail.config import ReviewConfig
from taskrail.model import Task

MAX_URL_LENGTH = 8000
KNOWN_HOSTS = {"github.com": "github", "gitlab.com": "gitlab", "codeberg.org": "forgejo"}
REOPENS = re.compile(r"^Reopens:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Remote:
    host: str
    path: str  # owner/repo, or group/subgroup/project


def parse_remote_url(url: str) -> Remote | None:
    """Host and repository path from the usual git remote URL forms."""
    url = url.strip()
    patterns = (
        r"^(?:ssh|git\+ssh|https?|git)://(?:[^@/]+@)?(?P<host>[^/:]+)(?::\d+)?/(?P<path>.+?)(?:\.git)?/?$",
        r"^(?:[^@/]+@)?(?P<host>[^/:]+):(?P<path>[^/].*?)(?:\.git)?/?$",  # scp-like: git@host:owner/repo.git
    )
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return Remote(host=match.group("host").lower(), path=match.group("path"))
    return None


def detect_provider(review: ReviewConfig, remote: Remote | None) -> str:
    if review.provider != "auto":
        return review.provider
    if review.url_template:
        return "template"
    return KNOWN_HOSTS.get(remote.host, "none") if remote else "none"


def web_base(review: ReviewConfig, remote: Remote | None) -> str | None:
    if review.web_url:
        return review.web_url
    return f"https://{remote.host}" if remote else None


@dataclass(frozen=True)
class ResolvedRemote:
    name: str
    source: str  # "branch.<mainline>.remote" or "[review].remote"


def resolve_remote(root: Path, mainline: str, fallback: str) -> ResolvedRemote:
    """The remote a mainline tracks when it names a configured remote, else the `[review].remote` fallback."""
    tracked = gitutil.run(root, "config", "--get", f"branch.{mainline}.remote", check=False).stdout.strip()
    if tracked and tracked in gitutil.run(root, "remote", check=False).stdout.split():
        return ResolvedRemote(tracked, f"branch.{mainline}.remote")
    return ResolvedRemote(fallback, "[review].remote")


@dataclass(frozen=True)
class Base:
    onto: str | None
    diverged: bool
    reason: str


def _sha(root: Path, ref: str) -> str | None:
    result = gitutil.run(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return result.stdout.strip() or None


def _is_ancestor(root: Path, older: str, newer: str) -> bool:
    return gitutil.run(root, "merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def choose_base(root: Path, remote: str, mainline: str) -> Base:
    """The further-ahead of the local mainline and its remote-tracking branch."""
    local_ref, remote_ref = mainline, f"{remote}/{mainline}"
    local, tracked = _sha(root, f"refs/heads/{mainline}"), _sha(root, f"refs/remotes/{remote}/{mainline}")
    if local is None and tracked is None:
        return Base(None, False, f"neither {local_ref} nor {remote_ref} exists")
    if local is None:
        return Base(remote_ref, False, f"only {remote_ref} exists")
    if tracked is None:
        return Base(local_ref, False, f"only {local_ref} exists")
    if local == tracked or _is_ancestor(root, local, tracked):
        return Base(remote_ref, False, f"{remote_ref} is up to date with or ahead of {local_ref}")
    if _is_ancestor(root, tracked, local):
        return Base(local_ref, False, f"{local_ref} is ahead of {remote_ref}")
    return Base(None, True, f"{local_ref} and {remote_ref} have diverged")


def contains(root: Path, ref: str) -> bool:
    """Whether HEAD already includes `ref`, so no rebase is needed."""
    sha = _sha(root, ref)
    return sha is not None and _is_ancestor(root, sha, "HEAD")


def subject(title: str) -> str:
    first, _, rest = title.partition(" ")
    if len(first) > 1 and first.isupper():
        return title
    return title[:1].lower() + title[1:]


def pr_title(task: Task, commit_type: str, scope: str, breaking: bool) -> str:
    scoped = f"{commit_type}({scope})" if scope else commit_type
    return f"{scoped}{'!' if breaking else ''}: {subject(task.title)} ({task.id})"


def reopened_ids(root: Path, since: str | None) -> list[str]:
    revisions = f"{since}..HEAD" if since else "HEAD"
    log = gitutil.run(root, "log", "--format=%B", revisions, check=False).stdout
    seen: list[str] = []
    for task_id in REOPENS.findall(log):
        if task_id not in seen:
            seen.append(task_id)
    return seen


def pr_body(task: Task, artifact: str | None, reopens: list[str]) -> str:
    lines = [f"Task: {task.id} — {task.title}"]
    if artifact:
        lines.append(f"Artifact: {artifact}")
    if reopens:
        lines += ["", *(f"Reopens: {task_id}" for task_id in reopens)]
    return "\n".join(lines) + "\n"


def pull_request_url(provider: str, web: str | None, path: str | None, base: str, head: str, title: str, body: str, template: str = "") -> str | None:
    if provider == "none" or web is None or path is None:
        return None

    def build(with_body: bool) -> str | None:
        text = body if with_body else ""
        if provider == "github":
            query = {"quick_pull": "1", "title": title, **({"body": text} if text else {})}
            return f"{web}/{path}/compare/{quote(base, safe='')}...{quote(head, safe='')}?{urlencode(query, quote_via=quote)}"
        if provider == "gitlab":
            query = {
                "merge_request[source_branch]": head,
                "merge_request[target_branch]": base,
                "merge_request[title]": title,
                **({"merge_request[description]": text} if text else {}),
            }
            return f"{web}/{path}/-/merge_requests/new?{urlencode(query, quote_via=quote)}"
        if provider == "gitea":
            query = {"title": title, **({"body": text} if text else {})}
            return f"{web}/{path}/compare/{quote(base, safe='')}...{quote(head, safe='')}?{urlencode(query, quote_via=quote)}"
        if provider == "forgejo":
            return f"{web}/{path}/compare/{quote(base, safe='')}...{quote(head, safe='')}"
        if provider == "template" and template:
            values = {
                "web_url": web,
                "repo": path,
                "base": quote(base, safe=""),
                "head": quote(head, safe=""),
                "title": quote(title, safe=""),
                "body": quote(text, safe=""),
            }
            return template.format(**values)
        return None

    url = build(with_body=True)
    if url is not None and len(url) > MAX_URL_LENGTH:
        url = build(with_body=False)
    return url


@dataclass(frozen=True)
class PushResult:
    pushed: bool
    command: list[str]
    error: str | None = None


def push_command(root: Path, remote: str, branch: str) -> list[str]:
    listing = gitutil.run(root, "ls-remote", "--heads", remote, branch, check=False)
    if listing.returncode != 0:
        raise gitutil.GitError(f"could not reach {remote}: {listing.stderr.strip()}")
    remote_sha = listing.stdout.split("\t", 1)[0].strip() if listing.stdout.strip() else None
    command = ["git", "push", "--set-upstream"]
    if remote_sha:
        command.append(f"--force-with-lease={branch}:{remote_sha}")
    return [*command, remote, f"HEAD:refs/heads/{branch}"]


def push(root: Path, remote: str, branch: str) -> PushResult:
    command = push_command(root, remote, branch)
    result = gitutil.run(root, *command[1:], check=False)
    if result.returncode != 0:
        return PushResult(False, command, result.stderr.strip() or result.stdout.strip())
    return PushResult(True, command)
