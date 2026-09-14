"""Tasks reopened in git history without a `Reopens: <ID>` trailer, for `validate` only (DESIGN §7)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from taskrail import gitutil
from taskrail.issues import Issue, warning
from taskrail.model import Project, Status
from taskrail.review import REOPENS
from taskrail.stack import _statuses

CODE = "reopen-untraced"
DEFAULT_LIMIT = 500
CLOSED = {Status.DONE.value: "done", Status.DISCARDED.value: "discarded"}
_FIELD, _RECORD = "\x1f", "\x1e"


@dataclass
class HistoryReport:
    limit: int
    examined: int = 0
    truncated: bool = False
    shallow: bool = False
    skipped: str | None = None
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "examined": self.examined,
            "limit": self.limit,
            "truncated": self.truncated,
            "shallow": self.shallow,
            "skipped": self.skipped,
        }

    def note(self) -> str | None:
        """One line for the text output when the check was incomplete; None when there is nothing to say."""
        if self.skipped and self.skipped != "--no-history":
            return f"history: not checked ({self.skipped})"
        if self.shallow:
            return f"history: shallow clone; examined {self.examined} commit(s), so older reopens are not checked"
        if self.truncated:
            return (
                f"history: examined only the latest {self.examined} commit(s) changing backlog files "
                f"(--history-limit {self.limit})"
            )
        return None


@dataclass(frozen=True)
class _Commit:
    sha: str
    parents: tuple[str, ...]
    subject: str


def check_reopens(project: Project, limit: int = DEFAULT_LIMIT, enabled: bool = True) -> HistoryReport:
    """Warn for each task pending in the working tree whose latest reopen in history carries no trailer.

    A commit reopens a task when the task is ⬜ there and ✅ or ❌ at every parent. The reopen is recorded
    when a commit reachable from HEAD but not from all of those parents has a `Reopens: <ID>` trailer.
    """
    report = HistoryReport(limit=limit)
    if not enabled:
        report.skipped = "--no-history"
        return report
    root = project.config.root
    try:
        gitutil.common_dir(root)
    except gitutil.GitError:
        report.skipped = "not a git repository"
        return report
    if gitutil.run(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", check=False).returncode != 0:
        report.skipped = "no commits"
        return report
    report.shallow = gitutil.run(root, "rev-parse", "--is-shallow-repository", check=False).stdout.strip() == "true"

    paths = sorted({backlog.config.file for backlog in project.backlogs} | {epic.file for backlog in project.backlogs for epic in backlog.epics if epic.file})
    commits = _commits(root, paths, limit + 1)
    report.truncated = len(commits) > limit
    commits = commits[:limit]
    report.examined = len(commits)

    pending = {task.id: task for task in project.tasks if task.status is Status.PENDING}
    if not commits or not pending:
        return report
    revisions = sorted({c.sha for c in commits} | {p for c in commits for p in c.parents})
    covered_cache: dict[tuple[str, ...], set[str]] = {}
    reported: set[str] = set()
    for backlog in project.backlogs:
        ids = {task_id for task_id in pending if project.backlog_for_id(task_id) is backlog}
        if not ids:
            continue
        epic_files = [epic.file for epic in backlog.epics if epic.file]
        reader = _Reader(project, backlog.config.file, epic_files, revisions)
        id_pattern = re.compile(rf"\b{re.escape(backlog.config.prefix)}\d+\b")
        for commit in commits:  # newest first, so the first unrecorded reopen of a task is its latest
            candidates = _candidates(reader, commit, ids - reported, id_pattern)
            for task_id in sorted(candidates):
                before = [reader.statuses(parent).get(task_id) for parent in commit.parents]
                if reader.statuses(commit.sha).get(task_id) != Status.PENDING.value or not all(s in CLOSED for s in before):
                    continue
                if commit.parents not in covered_cache:
                    covered_cache[commit.parents] = _recorded(root, commit.parents)
                reported.add(task_id)  # a recorded reopen also covers older ones reachable from its parents
                if task_id in covered_cache[commit.parents]:
                    continue
                task = pending[task_id]
                status = before[0]
                report.issues.append(
                    warning(
                        CODE,
                        f"{task_id} went from {status} {CLOSED[status]} to ⬜ pending in {commit.sha[:7]} "
                        f"(\"{commit.subject}\") without a `Reopens: {task_id}` trailer; the rebase rule and "
                        f"done-branch detection cannot see this reopen — record it in a commit whose message "
                        f"ends with `Reopens: {task_id}`",
                        task.file,
                        task.line,
                    )
                )
    return report


def _commits(root, paths: list[str], count: int) -> list[_Commit]:
    output = gitutil.run(
        root, "log", f"--max-count={count}", f"--format=%H %P{_FIELD}%s{_RECORD}", "HEAD", "--", *paths, check=False
    ).stdout
    commits = []
    for record in output.split(_RECORD):
        record = record.strip("\n")
        if not record:
            continue
        hashes, _, subject = record.partition(_FIELD)
        sha, *parents = hashes.split()
        commits.append(_Commit(sha, tuple(parents), subject))
    return commits


def _recorded(root, parents: tuple[str, ...]) -> set[str]:
    """Task IDs named by a `Reopens:` trailer in commits reachable from HEAD but not from every one of `parents`."""
    log = gitutil.run(root, "log", "--format=%B", "--grep=^Reopens:", "HEAD", "--not", *parents, check=False).stdout
    return set(REOPENS.findall(log))


class _Reader:
    """Backlog text at many revisions, read in two `git cat-file --batch` passes; statuses parsed on demand."""

    def __init__(self, project: Project, main_file: str, epic_files: list[str], revisions: list[str]):
        root = project.config.root
        self.aliases = project.config.column_aliases
        specs = [f"{rev}:{path}" for rev in revisions for path in (main_file, *epic_files)]
        blobs = gitutil.read_blobs(root, specs)
        self.texts: dict[str, list[str]] = {}
        for rev in revisions:
            main = blobs.get(f"{rev}:{main_file}")
            if main is None:
                self.texts[rev] = []
                continue
            epics = [blobs.get(f"{rev}:{path}") for path in epic_files]
            self.texts[rev] = [main, *(text for text in epics if text is not None)]
        self._lines: dict[str, set[str]] = {}
        self._statuses: dict[str, dict[str, str]] = {}

    def lines(self, rev: str) -> set[str]:
        if rev not in self._lines:
            self._lines[rev] = {line.strip() for text in self.texts.get(rev, []) for line in text.splitlines()}
        return self._lines[rev]

    def statuses(self, rev: str) -> dict[str, str]:
        if rev not in self._statuses:
            found: dict[str, str] = {}
            for text in self.texts.get(rev, []):
                for task_id, status in _statuses(text, self.aliases).items():
                    found.setdefault(task_id, status)
            self._statuses[rev] = found
        return self._statuses[rev]


def _candidates(reader: _Reader, commit: _Commit, ids: set[str], id_pattern: re.Pattern) -> set[str]:
    """Pending task IDs on a line holding ✅ or ❌ that no longer appears at the commit: a cheap superset of reopens."""
    if not commit.parents or not ids:
        return set()
    after = reader.lines(commit.sha)
    found: set[str] = set()
    for parent in commit.parents:
        for line in reader.lines(parent) - after:
            if Status.DONE.value in line or Status.DISCARDED.value in line:
                found.update(task_id for task_id in id_pattern.findall(line) if task_id in ids)
    return found
