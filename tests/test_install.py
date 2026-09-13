import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import git

from taskrail import install
from taskrail.cli import main

SKILLS = ["taskrail", "taskrail-bug", "taskrail-chore", "taskrail-feature", "taskrail-spike"]


@pytest.fixture
def empty_repo(tmp_path, monkeypatch):
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def init(root, *argv, capsys):
    code, out, err = run(root, "init", "--json", *argv, capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def test_init_creates_a_valid_project(empty_repo, capsys):
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    for path in [".taskrail/config.toml", "TODO.md", ".taskrail/bin/taskrail", ".gitignore"]:
        assert path in report["created"]
    assert sorted(p.parent.name for p in (empty_repo / ".claude/skills").glob("*/SKILL.md")) == SKILLS
    assert os.access(empty_repo / ".taskrail/bin/taskrail", os.X_OK)
    assert ".worktrees/" in (empty_repo / ".gitignore").read_text()
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert manifest["integrations"] == ["claude"]


def test_changing_skills_asks_for_an_agent_restart(empty_repo, capsys):
    first = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert any("restart the agent session" in note for note in first["notes"])
    assert not any("restart" in note for note in init(empty_repo, capsys=capsys)["notes"])


def test_init_is_idempotent(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    snapshot = {p: p.read_bytes() for p in empty_repo.rglob("*") if p.is_file() and ".git/" not in str(p)}
    report = init(empty_repo, capsys=capsys)
    assert report["created"] == report["updated"] == report["skipped"] == []
    assert {p: p.read_bytes() for p in snapshot} == snapshot


def test_init_never_touches_an_existing_config_or_backlog(empty_repo, capsys):
    (empty_repo / ".taskrail").mkdir()
    (empty_repo / ".taskrail/config.toml").write_text('[[backlog]]\nname = "x"\nprefix = "X"\nfile = "BACKLOG.md"\n')
    (empty_repo / "BACKLOG.md").write_text("# mine\n")
    init(empty_repo, capsys=capsys)
    assert (empty_repo / "BACKLOG.md").read_text() == "# mine\n"
    assert not (empty_repo / "TODO.md").exists()


def test_locally_edited_skills_are_kept_unless_forced(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    skill = empty_repo / ".claude/skills/taskrail-bug/SKILL.md"
    skill.write_text(skill.read_text() + "\nLocal note.\n")
    report = init(empty_repo, capsys=capsys)
    assert report["skipped"][0]["path"] == ".claude/skills/taskrail-bug/SKILL.md"
    assert "Local note." in skill.read_text()
    init(empty_repo, "--force", capsys=capsys)
    assert "Local note." not in skill.read_text()


def test_a_foreign_file_is_not_overwritten(empty_repo, capsys):
    target = empty_repo / ".claude/skills/taskrail/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("someone else's skill\n")
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert "not written by taskrail" in report["skipped"][0]["reason"]


def test_opencode_alone_uses_its_own_directory(empty_repo, capsys):
    init(empty_repo, "--integration", "opencode", capsys=capsys)
    text = (empty_repo / ".opencode/skills/taskrail/SKILL.md").read_text()
    assert "## On OpenCode" in text and "## On Claude Code" not in text
    assert not (empty_repo / ".claude").exists()


def test_claude_and_opencode_share_one_copy(empty_repo, capsys):
    init(empty_repo, "--integration", "opencode", capsys=capsys)
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    text = (empty_repo / ".claude/skills/taskrail/SKILL.md").read_text()
    assert "## On Claude Code" in text and "## On OpenCode" in text
    assert not (empty_repo / ".opencode/skills").exists()
    assert ".opencode/skills/taskrail/SKILL.md" in report["removed"]


def test_skills_have_only_frontmatter_every_agent_accepts(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    for path in (empty_repo / ".claude/skills").glob("*/SKILL.md"):
        text = path.read_text()
        frontmatter = text.split("---\n")[1]
        keys = re.findall(r"^([a-z-]+):", frontmatter, re.MULTILINE)
        assert set(keys) <= {"name", "description", "license", "compatibility", "metadata"}
        name = re.search(r"^name: (.+)$", frontmatter, re.MULTILINE).group(1)
        assert name == path.parent.name and re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name)
        description = re.search(r"^description: (.+)$", frontmatter, re.MULTILINE).group(1)
        assert 1 <= len(description) <= 1024
        assert install.HARNESS_MARKER not in text


def test_github_workflow_flag_is_remembered(empty_repo, capsys):
    init(empty_repo, "--github-workflow", capsys=capsys)
    workflow = (empty_repo / ".github/workflows/taskrail.yml").read_text()
    assert "branches: [main]" in workflow and ".taskrail/bin/taskrail validate" in workflow
    (empty_repo / ".github/workflows/taskrail.yml").unlink()
    init(empty_repo, capsys=capsys)
    assert (empty_repo / ".github/workflows/taskrail.yml").exists()


def test_pre_commit_hook_is_added_once_and_keeps_an_existing_hook(empty_repo, capsys):
    hook = empty_repo / ".git/hooks/pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\necho existing\n")
    init(empty_repo, "--pre-commit", capsys=capsys)
    init(empty_repo, "--pre-commit", capsys=capsys)
    text = hook.read_text()
    assert "echo existing" in text
    assert text.count(install.HOOK_BEGIN) == 1
    assert os.access(hook, os.X_OK)


def test_pre_commit_hook_blocks_an_invalid_backlog(empty_repo, capsys, monkeypatch):
    monkeypatch.setenv("TASKRAIL_BIN", str(_python_shim(empty_repo)))
    init(empty_repo, "--pre-commit", capsys=capsys)
    git(empty_repo, "add", "-A")
    git(empty_repo, "commit", "-q", "-m", "init")  # a valid backlog passes the hook
    (empty_repo / "TODO.md").write_text("# TODO\n")  # no Epics section
    git(empty_repo, "add", "TODO.md")
    result = subprocess.run(["git", "commit", "-q", "-m", "break"], cwd=empty_repo, capture_output=True, text=True)
    assert result.returncode != 0
    assert "commit aborted" in result.stderr


def _python_shim(root: Path) -> Path:
    shim = root.parent / f"{root.name}-taskrail-shim"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m taskrail "$@"\n')
    shim.chmod(0o755)
    return shim


def test_wrapper_runs_the_cli(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    env = {**os.environ, "TASKRAIL_BIN": str(_python_shim(empty_repo))}
    result = subprocess.run([str(empty_repo / ".taskrail/bin/taskrail"), "validate"], cwd=empty_repo, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert "0 error(s)" in result.stdout


def test_wrapper_without_cli_or_uvx_explains_what_is_missing(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(empty_repo)}
    result = subprocess.run([str(empty_repo / ".taskrail/bin/taskrail"), "validate"], cwd=empty_repo, capture_output=True, text=True, env=env)
    if result.returncode != 2:
        pytest.skip("uvx or taskrail is installed system-wide")
    assert "neither a matching taskrail nor uvx" in result.stderr


def test_upgrade_pins_the_version_and_restores_skills(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    config = empty_repo / ".taskrail/config.toml"
    config.write_text(config.read_text().replace(install.release_tag(), "v0.0.1"))
    (empty_repo / ".claude/skills/taskrail-spike/SKILL.md").unlink()
    code, out, _ = run(empty_repo, "upgrade", "--json", capsys=capsys)
    assert code == 0
    report = json.loads(out)
    assert ".claude/skills/taskrail-spike/SKILL.md" in report["created"]
    assert f'version = "{install.release_tag()}"' in config.read_text()


def test_upgrade_needs_a_previous_init(repo, capsys):
    assert run(repo.root, "upgrade", capsys=capsys)[0] == 3


def test_unknown_integration(empty_repo, capsys):
    assert run(empty_repo, "init", "--integration", "vim", capsys=capsys)[0] == 2


def test_self_upgrade_dry_run(capsys, monkeypatch):
    code = main(["self", "upgrade", "--tag", "v0.1.0", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "uv tool install --force taskrail --from git+https://github.com/alexkander/taskrail.git@v0.1.0" in out


def test_release_tag_drops_development_suffixes():
    assert install.release_tag("0.1.0.dev0") == "v0.1.0"


def test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout(empty_repo, capsys, monkeypatch):
    monkeypatch.delenv("TASKRAIL_BIN", raising=False)
    init(empty_repo, capsys=capsys)
    config = empty_repo / ".taskrail/config.toml"
    source = Path(install.__file__).resolve().parents[2]  # the project root
    link = empty_repo / "vendor-taskrail"
    link.symlink_to(source)
    config.write_text(config.read_text().replace(f'"{install.release_tag()}"', '"local:vendor-taskrail"'))
    result = subprocess.run(
        [str(empty_repo / ".taskrail/bin/taskrail"), "--version"], cwd=empty_repo, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("taskrail ")


def test_upgrade_keeps_a_local_pin(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    config = empty_repo / ".taskrail/config.toml"
    config.write_text(config.read_text().replace(f'"{install.release_tag()}"', '"local:."'))
    assert run(empty_repo, "upgrade", capsys=capsys)[0] == 0
    assert 'version = "local:."' in config.read_text()
