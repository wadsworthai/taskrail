"""Installing taskrail into a repository: config, backlog, wrapper, agent skills and extras."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from taskrail import __version__, gitutil

PACKAGE = Path(__file__).parent
SKILLS_SOURCE = PACKAGE / "skills"
HARNESS_SOURCE = PACKAGE / "integrations"
HARNESS_MARKER = "<!-- taskrail:harness -->"
SOURCE_URL = "https://github.com/alexkander/taskrail.git"
MANIFEST = ".taskrail/installed.json"
WRAPPER = ".taskrail/bin/taskrail"
WORKFLOW = ".github/workflows/taskrail.yml"
HOOK_BEGIN = "# >>> taskrail >>>"
HOOK_END = "# <<< taskrail <<<"

# Agent integrations: where each one loads skills from. OpenCode also reads .claude/skills, and
# requires skill names to be unique across locations, so with both installed the skills are
# written once, to .claude/skills.
INTEGRATIONS = {
    "claude": {"label": "Claude Code", "skills_dir": ".claude/skills"},
    "opencode": {"label": "OpenCode", "skills_dir": ".opencode/skills"},
}


def release_tag(version: str = __version__) -> str:
    base = re.match(r"^\d+\.\d+\.\d+", version)
    return f"v{base.group(0) if base else version}"


@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (path, reason)
    removed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": [{"path": p, "reason": r} for p, r in self.skipped],
            "removed": self.removed,
            "notes": self.notes,
        }

    def format(self) -> str:
        lines = [f"created   {p}" for p in self.created]
        lines += [f"updated   {p}" for p in self.updated]
        lines += [f"removed   {p}" for p in self.removed]
        lines += [f"skipped   {p} ({r})" for p, r in self.skipped]
        lines += [f"note      {n}" for n in self.notes]
        lines.append(f"{len(self.unchanged)} file(s) already up to date")
        return "\n".join(lines)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_manifest(root: Path) -> dict:
    try:
        return json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class Installer:
    def __init__(self, root: Path, force: bool = False):
        self.root = root
        self.force = force
        self.report = Report()
        self.manifest = read_manifest(root)
        self.files: dict[str, str] = dict(self.manifest.get("files", {}))

    def managed(self, relative: str, content: str, executable: bool = False) -> None:
        """Write a file taskrail owns, unless it was edited locally since taskrail wrote it."""
        path = self.root / relative
        new_digest = _digest(content)
        if path.exists():
            current = path.read_text(encoding="utf-8")
            current_digest = _digest(current)
            if current_digest == new_digest:
                self.files[relative] = new_digest
                self.report.unchanged.append(relative)
                return
            recorded = self.files.get(relative)
            if not self.force:
                if recorded is None:
                    self.report.skipped.append((relative, "exists and was not written by taskrail; --force replaces it"))
                    return
                if recorded != current_digest:
                    self.report.skipped.append((relative, "edited locally; --force replaces it"))
                    return
            self.report.updated.append(relative)
        else:
            self.report.created.append(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.files[relative] = new_digest

    def seed(self, relative: str, content: str) -> None:
        """Create a file the repository owns from then on; never touch an existing one."""
        path = self.root / relative
        if path.exists():
            self.report.unchanged.append(relative)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.report.created.append(relative)

    def remove_managed(self, relative: str) -> None:
        path = self.root / relative
        recorded = self.files.pop(relative, None)
        if not path.exists():
            return
        if recorded != _digest(path.read_text(encoding="utf-8")) and not self.force:
            self.files[relative] = recorded or ""
            self.report.skipped.append((relative, "no longer installed here, but edited locally; left in place"))
            return
        path.unlink()
        self.report.removed.append(relative)
        parent = path.parent
        while parent != self.root and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    def save_manifest(self, integrations: list[str], extras: dict) -> None:
        manifest = {
            "version": release_tag(),
            "integrations": sorted(integrations),
            "extras": extras,
            "files": dict(sorted(self.files.items())),
        }
        text = json.dumps(manifest, indent=2) + "\n"
        path = self.root / MANIFEST
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def default_config(mainline: str) -> str:
    return f'''version = "{release_tag()}"

[[backlog]]
name = "main"
prefix = "T"
file = "TODO.md"
mainline = "{mainline}"
artifacts = "docs"

[columns]
custom = []

[points]
scale = [1, 2, 3, 5, 8, 13]

[git]
worktree = "required"        # "required": one worktree per task; "never": a branch in this checkout
worktree_dir = ".worktrees"
push_task_branch = true      # `taskrail review --publish` pushes the task branch
claim_remote = ""            # e.g. "origin" to also claim across machines

[review]                     # hand-off after a task is closed
remote = "origin"            # fallback for a mainline without branch.<mainline>.remote
fetch = true
rebase = true                # rebase onto the further-ahead of the local and remote mainline
provider = "auto"            # auto | github | gitlab | gitea | forgejo | none
web_url = ""                 # web address of a self-hosted git host, e.g. "https://git.example.com"
url_template = ""            # for other hosts: {{web_url}} {{repo}} {{base}} {{head}} {{title}} {{body}}
scope = ""                   # default Conventional Commits scope of pull request titles

[checks]                     # commands the task kinds run as quality gates
# test = "make test"
# lint = "make lint"
'''


DEFAULT_TODO = """# TODO

## Epics

| ID  | Epic | Objective | File |
|-----|------|-----------|------|
"""


def wrapper_script() -> str:
    return f'''#!/bin/sh
# Managed by taskrail: `taskrail init` and `taskrail upgrade` rewrite this file.
# Runs the taskrail version pinned in .taskrail/config.toml: the installed CLI when it matches,
# otherwise that exact version through uvx. A pin of the form `local:<path>` runs the taskrail
# source at that path inside this checkout instead. TASKRAIL_BIN overrides everything.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ -n "${{TASKRAIL_BIN:-}}" ]; then
  exec "$TASKRAIL_BIN" "$@"
fi
pin=$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\\([^"]*\\)".*/\\1/p' "$root/.taskrail/config.toml" | head -n 1)
case "$pin" in
  local:*)
    exec uv run --quiet --project "$root/${{pin#local:}}" taskrail "$@"
    ;;
esac
installed=$(command -v taskrail 2>/dev/null || true)
if [ -n "$installed" ] && [ "$installed" != "$0" ]; then
  have=$(taskrail --version 2>/dev/null | sed 's/^taskrail //')
  if [ -z "$pin" ] || [ "v$have" = "$pin" ]; then
    exec taskrail "$@"
  fi
fi
if [ -z "$pin" ]; then
  echo "taskrail: not installed, and no version is pinned in .taskrail/config.toml" >&2
  exit 2
fi
if ! command -v uvx >/dev/null 2>&1; then
  echo "taskrail: $pin is needed but neither a matching taskrail nor uvx is installed (https://docs.astral.sh/uv/)" >&2
  exit 2
fi
exec uvx --quiet --from "git+${{TASKRAIL_SOURCE:-{SOURCE_URL}}}@$pin" taskrail "$@"
'''


def workflow(mainlines: list[str]) -> str:
    branches = ", ".join(sorted(set(mainlines)))
    return f"""# Managed by taskrail: `taskrail init --github-workflow` and `taskrail upgrade` rewrite this file.
name: taskrail

on:
  pull_request:
  push:
    branches: [{branches}]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
      - run: .taskrail/bin/taskrail validate
"""


def hook_block() -> str:
    return f"""{HOOK_BEGIN}
if git diff --cached --name-only --diff-filter=ACMR | grep -Eq '\\.md$|^\\.taskrail/'; then
  .taskrail/bin/taskrail validate >&2 || {{ echo "taskrail: backlog validation failed; commit aborted" >&2; exit 1; }}
fi
{HOOK_END}
"""


def install_hook(root: Path, report: Report) -> None:
    hooks = Path(gitutil.run(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks").stdout.strip())
    path = hooks / "pre-commit"
    block = hook_block()
    label = str(path)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if HOOK_BEGIN in text and HOOK_END in text:
            start = text.index(HOOK_BEGIN)
            end = text.index(HOOK_END) + len(HOOK_END) + 1
            updated = text[:start] + block + text[end:]
            if updated == text:
                report.unchanged.append(label)
                return
            path.write_text(updated, encoding="utf-8")
            report.updated.append(label)
            return
        if not text.startswith("#!") or "sh" not in text.splitlines()[0]:
            report.skipped.append((label, "an existing non-shell hook; add `.taskrail/bin/taskrail validate` to it by hand"))
            return
        path.write_text(text.rstrip("\n") + "\n\n" + block, encoding="utf-8")
        report.updated.append(label)
    else:
        hooks.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n" + block, encoding="utf-8")
        report.created.append(label)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def skill_files(integrations: list[str]) -> dict[str, str]:
    """Rendered skill files per destination path for the selected integrations."""
    if "claude" in integrations:
        targets = {INTEGRATIONS["claude"]["skills_dir"]: integrations}
    else:
        targets = {INTEGRATIONS[name]["skills_dir"]: [name] for name in integrations}
    files: dict[str, str] = {}
    for skills_dir, served in targets.items():
        harness = "\n".join((HARNESS_SOURCE / f"{name}.md").read_text(encoding="utf-8") for name in sorted(served)).strip()
        for skill in sorted(p for p in SKILLS_SOURCE.iterdir() if p.is_dir()):
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            text = text.replace(HARNESS_MARKER, harness) if harness else text.replace(HARNESS_MARKER + "\n\n", "")
            files[f"{skills_dir}/{skill.name}/SKILL.md"] = text
    return files


def _ensure_gitignore(root: Path, entry: str, report: Report) -> None:
    path = root / ".gitignore"
    line = entry.rstrip("/") + "/"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(l.strip() in (line, entry, "/" + line) for l in existing.splitlines()):
        return
    path.write_text(existing + ("" if not existing or existing.endswith("\n") else "\n") + line + "\n", encoding="utf-8")
    (report.updated if existing else report.created).append(".gitignore")


def install(
    root: Path,
    integrations: list[str],
    github_workflow: bool = False,
    pre_commit: bool = False,
    force: bool = False,
) -> Report:
    """Idempotent install. Integrations and extras add to what is already installed."""
    from taskrail.config import load_config

    installer = Installer(root, force=force)
    manifest = installer.manifest
    selected = sorted(set(manifest.get("integrations", [])) | set(integrations))
    extras = dict(manifest.get("extras", {}))
    if github_workflow:
        extras["github_workflow"] = True

    try:
        mainline = gitutil.current_branch(root) or "main"
    except gitutil.GitError:
        mainline = "main"
        installer.report.notes.append("not a git repository: claims, ID reservation and --pre-commit need git")
    installer.seed(".taskrail/config.toml", default_config(mainline))
    config = load_config(root)
    for backlog in config.backlogs:
        installer.seed(backlog.file, DEFAULT_TODO)
    installer.managed(WRAPPER, wrapper_script(), executable=True)

    wanted = skill_files(selected)
    for relative, content in wanted.items():
        installer.managed(relative, content)
    for relative in [p for p in list(installer.files) if p.endswith("/SKILL.md") and p not in wanted]:
        installer.remove_managed(relative)

    if extras.get("github_workflow"):
        installer.managed(WORKFLOW, workflow([b.mainline for b in config.backlogs]))
    if config.worktree == "required":
        _ensure_gitignore(root, config.worktree_dir, installer.report)
    if pre_commit:
        install_hook(root, installer.report)
    changed = [*installer.report.created, *installer.report.updated, *installer.report.removed]
    if any(path.endswith("/SKILL.md") for path in changed):
        installer.report.notes.append("skills changed: restart the agent session so it loads them")
    if not selected:
        installer.report.notes.append("no agent integration installed; pass --integration claude or --integration opencode")

    installer.save_manifest(selected, extras)
    return installer.report


LOCAL_PIN = re.compile(r'^version\s*=\s*"local:[^"]*"', re.MULTILINE)


def set_version_pin(root: Path) -> bool:
    """Pin the running release; a `local:` pin is a deliberate development setup and is kept."""
    path = root / ".taskrail/config.toml"
    text = path.read_text(encoding="utf-8")
    if LOCAL_PIN.search(text):
        return False
    pin = f'version = "{release_tag()}"'
    updated, count = re.subn(r'^version\s*=\s*"[^"]*"', pin, text, count=1, flags=re.MULTILINE)
    if count == 0:
        updated = pin + "\n" + text
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def upgrade(root: Path, force: bool = False) -> Report:
    manifest = read_manifest(root)
    if not manifest:
        raise FileNotFoundError(f"{MANIFEST} not found; run `taskrail init` first")
    report = install(root, list(manifest.get("integrations", [])), force=force)
    if set_version_pin(root):
        report.updated.append(f".taskrail/config.toml (version pin → {release_tag()})")
    return report


def latest_tag(source: str = SOURCE_URL) -> str | None:
    output = gitutil.run(Path.cwd(), "ls-remote", "--tags", "--refs", source, "v*").stdout
    tags = [line.rsplit("refs/tags/", 1)[1] for line in output.splitlines() if "refs/tags/" in line]

    def key(tag: str):
        return tuple(int(part) if part.isdigit() else 0 for part in re.split(r"[.-]", tag.removeprefix("v")))

    return max(tags, key=key) if tags else None


def self_upgrade_command(tag: str, source: str = SOURCE_URL) -> list[str]:
    return ["uv", "tool", "install", "--force", "taskrail", "--from", f"git+{source}@{tag}"]


def self_upgrade(tag: str | None, dry_run: bool) -> tuple[list[str], int]:
    import subprocess

    source = os.environ.get("TASKRAIL_SOURCE", SOURCE_URL)
    tag = tag or latest_tag(source)
    if tag is None:
        raise LookupError(f"no v* release tag found at {source}")
    command = self_upgrade_command(tag, source)
    if dry_run:
        return command, 0
    return command, subprocess.run(command).returncode
