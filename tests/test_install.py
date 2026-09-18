import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from conftest import git
from test_install_without_path import path_with_uv_but_no_taskrail

from taskrail import install
from taskrail.cli import main

SKILLS = ["taskrail", "taskrail-autopilot", "taskrail-bug", "taskrail-chore", "taskrail-feature", "taskrail-spike"]


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
    for path in [".taskrail/config.toml", "TASKRAIL.md", ".taskrail/bin/taskrail", ".gitignore"]:
        assert path in report["created"]
    assert sorted(p.parent.name for p in (empty_repo / ".claude/skills").glob("*/SKILL.md")) == SKILLS
    assert os.access(empty_repo / ".taskrail/bin/taskrail", os.X_OK)
    assert ".worktrees/" in (empty_repo / ".gitignore").read_text()
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert manifest["integrations"] == ["claude"]


# `init` configures no autopilot: the seeded block is a comment a repository uncomments itself.
def test_init_seeds_the_autopilot_section_commented_out(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    config = (empty_repo / ".taskrail/config.toml").read_text()
    for key in ["[autopilot]", "enabled = true", "max_lanes", "read_first", "governing", "escalate_gates"]:
        assert f"# {key}" in config
    assert tomllib.loads(config).get("autopilot") is None
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0
    code, _, err = run(empty_repo, "autopilot", "start", "--count", "1", capsys=capsys)
    assert code == 5 and "[autopilot].enabled = true" in err

    uncommented = re.sub(r"(?m)^# (\[autopilot\]|enabled|max_lanes|read_first|governing|escalate_gates)", r"\1", config)
    (empty_repo / ".taskrail/config.toml").write_text(uncommented)
    assert tomllib.loads(uncommented)["autopilot"]["enabled"] is True
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0
    assert run(empty_repo, "autopilot", "start", "--count", "1", capsys=capsys)[0] == 0


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
    assert not (empty_repo / "TASKRAIL.md").exists()


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


def test_github_workflow_checks_out_full_history(empty_repo, capsys):
    # validate's reopen check (DESIGN §7) sees nothing past a shallow clone's boundary.
    init(empty_repo, "--github-workflow", capsys=capsys)
    workflow = (empty_repo / install.WORKFLOW).read_text()
    assert "      - uses: actions/checkout@v7.0.1\n        with:\n          fetch-depth: 0\n" in workflow


def test_github_workflow_pins_every_action_to_an_exact_release_tag(empty_repo, capsys):
    # Not every action publishes a floating major tag: astral-sh/setup-uv stopped moving one
    # after v7, so `@v10` named a ref that exists nowhere and the job failed before it ran.
    # This asserts the shape, not that the tag exists: proving that needs the network, which no
    # test here may use. An exact tag is a form a human verifies once against the releases.
    init(empty_repo, "--github-workflow", capsys=capsys)
    workflow = (empty_repo / install.WORKFLOW).read_text()
    refs = re.findall(r"^\s*- uses: (.+)$", workflow, re.MULTILINE)
    assert refs
    loose = [ref for ref in refs if not re.fullmatch(r"[^@\s]+@v\d+\.\d+\.\d+", ref)]
    assert not loose, f"not pinned to an exact release tag: {loose}"


def test_upgrade_rewrites_an_unedited_workflow_from_an_earlier_template(empty_repo, capsys):
    init(empty_repo, "--github-workflow", capsys=capsys)
    earlier = install.workflow(["main"]).replace("        with:\n          fetch-depth: 0\n", "")
    assert "fetch-depth" not in earlier
    (empty_repo / install.WORKFLOW).write_text(earlier)
    manifest_path = empty_repo / install.MANIFEST
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][install.WORKFLOW] = install._digest(earlier)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    code, out, err = run(empty_repo, "upgrade", "--json", capsys=capsys)
    assert code == 0, err
    assert install.WORKFLOW in json.loads(out)["updated"]
    assert "fetch-depth: 0" in (empty_repo / install.WORKFLOW).read_text()


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
    (empty_repo / "TASKRAIL.md").write_text("# TODO\n")  # no Epics section
    git(empty_repo, "add", "TASKRAIL.md")
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


def _break_manifest(root: Path, shape: str) -> None:
    path = root / install.MANIFEST
    if shape == "conflict markers":
        lines = path.read_text().splitlines(keepends=True)
        wrapper = next(i for i, line in enumerate(lines) if install.WRAPPER in line)
        lines[wrapper:wrapper] = ["<<<<<<< HEAD\n", '    "a": "1",\n', "=======\n", '    "b": "2",\n', ">>>>>>> a\n"]
        path.write_text("".join(lines))
    elif shape == "empty file":
        path.write_text("")
    elif shape == "not an object":
        path.write_text("[]\n")
    elif shape == "not UTF-8":
        path.write_bytes(b'{"version": "\xff"}\n')
    elif shape == "a directory":
        path.unlink()
        path.mkdir()


def _tree(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


@pytest.mark.parametrize("shape", ["conflict markers", "empty file", "not an object", "not UTF-8", "a directory"])
@pytest.mark.parametrize("command", [["init"], ["init", "--force"], ["upgrade"], ["upgrade", "--force"]], ids=" ".join)
def test_an_unreadable_manifest_stops_init_and_upgrade(empty_repo, capsys, shape, command):
    init(empty_repo, "--integration", "claude", "--github-workflow", capsys=capsys)
    _break_manifest(empty_repo, shape)
    before = _tree(empty_repo)
    code, _, err = run(empty_repo, *command, capsys=capsys)
    assert code == 2, err
    assert install.MANIFEST in err
    assert _tree(empty_repo) == before


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root reads any file")
def test_a_manifest_without_read_permission_stops_init_and_upgrade(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    manifest = empty_repo / install.MANIFEST
    manifest.chmod(0)
    try:
        for command in (["init"], ["upgrade"]):
            code, _, err = run(empty_repo, *command, capsys=capsys)
            assert code == 2, err
            assert install.MANIFEST in err
    finally:
        manifest.chmod(0o644)


def test_an_empty_object_manifest_is_still_treated_as_nothing_installed(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    (empty_repo / install.MANIFEST).write_text("{}\n")
    assert run(empty_repo, "upgrade", capsys=capsys)[0] == 3
    assert run(empty_repo, "init", capsys=capsys)[0] == 0


def test_unknown_integration(empty_repo, capsys):
    assert run(empty_repo, "init", "--integration", "vim", capsys=capsys)[0] == 2


def test_self_upgrade_dry_run(capsys, monkeypatch):
    code = main(["self", "upgrade", "--tag", "v0.2.0", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "uv tool install --force taskrail --from git+https://github.com/wadsworthai/taskrail.git@v0.2.0" in out


def test_release_tag_drops_development_suffixes():
    assert install.release_tag("0.1.0.dev0") == "v0.1.0"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
def test_wrapper_with_a_local_pin_runs_the_source_in_this_checkout(empty_repo, tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("TASKRAIL_BIN", raising=False)  # it would bypass the wrapper entirely
    init(empty_repo, capsys=capsys)
    config = empty_repo / ".taskrail/config.toml"
    source = Path(install.__file__).resolve().parents[2]  # the project root
    link = empty_repo / "vendor-taskrail"
    link.symlink_to(source)
    config.write_text(config.read_text().replace(f'"{install.release_tag()}"', '"local:vendor-taskrail"'))
    # The wrapper's `local:` branch runs `uv run --project <pin> taskrail`, and `uv` takes any
    # taskrail the environment already offers before the pin has to supply one. `uv run pytest`
    # offers two: VIRTUAL_ENV, and this checkout's .venv/bin first on PATH. Leave either in place
    # and the test passes with a pin that holds no taskrail source at all.
    env = {**os.environ, "PATH": path_with_uv_but_no_taskrail(tmp_path)}
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        [str(empty_repo / ".taskrail/bin/taskrail"), "--version"], cwd=empty_repo, capture_output=True,
        text=True, env=env, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("taskrail ")


def test_upgrade_keeps_a_local_pin(empty_repo, capsys):
    init(empty_repo, capsys=capsys)
    config = empty_repo / ".taskrail/config.toml"
    config.write_text(config.read_text().replace(f'"{install.release_tag()}"', '"local:."'))
    assert run(empty_repo, "upgrade", capsys=capsys)[0] == 0
    assert 'version = "local:."' in config.read_text()


# T025: executor skills follow the kinds a repository resolves, after `[kinds].allowed`.

KIND = 'name = "{name}"\nsummary = "x"\n{body}\n[[stage]]\nname = "a"\n'


def installed_skills(root, skills_dir=".claude/skills"):
    return sorted(p.parent.name for p in (root / skills_dir).glob("*/SKILL.md"))


def set_kinds(root, *allowed: str) -> None:
    """Rewrite the config's `[kinds]` table; no names removes it."""
    config = root / ".taskrail/config.toml"
    text = config.read_text().split("\n[kinds]\n")[0]
    if allowed:
        text += "\n[kinds]\nallowed = [" + ", ".join(f'"{name}"' for name in allowed) + "]\n"
    config.write_text(text)


def write_kind(root, layer, name, body):
    path = root / ".taskrail" / layer / name / "kind.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(KIND.format(name=name, body=body))


def upgrade(root, *argv, capsys):
    code, out, err = run(root, "upgrade", "--json", *argv, capsys=capsys)
    assert code == 0, err
    return json.loads(out)


def left_out_notes(report):
    return [note for note in report["notes"] if note.startswith("not installing")]


def withheld_notes(report):
    return [note for note in report["notes"] if "left in place" in note]


def seed_config(root, *allowed: str) -> None:
    (root / ".taskrail").mkdir()
    (root / ".taskrail/config.toml").write_text(install.default_config("main"))
    set_kinds(root, *allowed)


# 1. Without [kinds], every skill installs and nothing is noted.
def test_without_allowed_kinds_every_skill_installs_without_a_note(empty_repo, capsys):
    first = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert installed_skills(empty_repo) == SKILLS
    assert left_out_notes(first) == []
    second = init(empty_repo, capsys=capsys)
    assert second["created"] == second["updated"] == second["removed"] == second["skipped"] == []
    assert second["notes"] == []


# 2. With allowed = [bug, chore], only their executor skills and the core skill install.
@pytest.mark.parametrize(("integration", "skills_dir"), [("claude", ".claude/skills"), ("opencode", ".opencode/skills")])
def test_allowed_kinds_limit_the_executor_skills_installed(empty_repo, capsys, integration, skills_dir):
    seed_config(empty_repo, "bug", "chore")
    report = init(empty_repo, "--integration", integration, capsys=capsys)
    assert installed_skills(empty_repo, skills_dir) == ["taskrail", "taskrail-autopilot", "taskrail-bug", "taskrail-chore"]
    assert left_out_notes(report) == ["not installing skills that no allowed kind uses: taskrail-feature, taskrail-spike"]
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert not [path for path in manifest["files"] if "feature" in path or "spike" in path]
    again = init(empty_repo, capsys=capsys)
    assert again["created"] == again["updated"] == again["removed"] == again["skipped"] == []


# 3. Narrowing allowed removes the skills no longer wanted.
def test_narrowing_allowed_kinds_removes_their_skills_on_upgrade(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    set_kinds(empty_repo, "bug", "chore")
    report = upgrade(empty_repo, capsys=capsys)
    assert sorted(report["removed"]) == [".claude/skills/taskrail-feature/SKILL.md", ".claude/skills/taskrail-spike/SKILL.md"]
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot", "taskrail-bug", "taskrail-chore"]
    assert not (empty_repo / ".claude/skills/taskrail-feature").exists()
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert ".claude/skills/taskrail-feature/SKILL.md" not in manifest["files"]
    assert any("restart the agent session" in note for note in report["notes"])


# 4. A locally edited copy stays until --force.
def test_an_edited_skill_of_a_disallowed_kind_is_kept_unless_forced(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    skill = empty_repo / ".claude/skills/taskrail-feature/SKILL.md"
    skill.write_text(skill.read_text() + "\nLocal note.\n")
    set_kinds(empty_repo, "bug", "chore")
    report = upgrade(empty_repo, capsys=capsys)
    assert report["removed"] == [".claude/skills/taskrail-spike/SKILL.md"]
    assert report["skipped"] == [
        {"path": ".claude/skills/taskrail-feature/SKILL.md", "reason": "no longer installed here, but edited locally; left in place"}
    ]
    assert "Local note." in skill.read_text()
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert ".claude/skills/taskrail-feature/SKILL.md" in manifest["files"]
    forced = upgrade(empty_repo, "--force", capsys=capsys)
    assert forced["removed"] == [".claude/skills/taskrail-feature/SKILL.md"]
    assert not skill.exists()


# 5. Widening allowed again reinstalls them.
def test_widening_allowed_kinds_reinstalls_their_skills(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    set_kinds(empty_repo, "bug", "chore")
    upgrade(empty_repo, capsys=capsys)
    set_kinds(empty_repo)
    report = upgrade(empty_repo, capsys=capsys)
    assert sorted(report["created"]) == [".claude/skills/taskrail-feature/SKILL.md", ".claude/skills/taskrail-spike/SKILL.md"]
    assert installed_skills(empty_repo) == SKILLS
    assert left_out_notes(report) == []


# 6. A local kind that names a shipped executor skill installs it, by `skill` or by a route.
@pytest.mark.parametrize(
    "body",
    ['skill = "taskrail-spike"', '[[route]]\nwhen = { Area = "*" }\nskill = "taskrail-spike"'],
    ids=["skill", "route"],
)
def test_a_local_kind_naming_a_shipped_skill_installs_it(empty_repo, capsys, body):
    seed_config(empty_repo, "bug", "research")
    write_kind(empty_repo, "types", "research", body)
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot", "taskrail-bug", "taskrail-spike"]
    assert left_out_notes(report) == ["not installing skills that no allowed kind uses: taskrail-chore, taskrail-feature"]


# 7. The core skill always installs; a skill taskrail does not ship is ignored.
def test_core_skill_installs_when_only_a_local_kind_with_its_own_skill_is_allowed(empty_repo, capsys):
    seed_config(empty_repo, "spec")
    write_kind(empty_repo, "types", "spec", 'skill = "speckit-pipeline"')
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot"]
    assert report["skipped"] == []
    assert not any("speckit" in path for path in report["created"])


# 8. An override pointing a core kind at another skill stops installing the core kind's skill.
def test_an_override_replacing_a_core_kinds_skill_skips_that_skill(empty_repo, capsys):
    seed_config(empty_repo)
    write_kind(empty_repo, "overrides", "bug", 'skill = "my-bug"')
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot", "taskrail-chore", "taskrail-feature", "taskrail-spike"]
    assert left_out_notes(report) == ["not installing skills that no allowed kind uses: taskrail-bug"]


# 9. While kind resolution reports errors, nothing is removed and a note says why.
def test_kind_resolution_errors_withhold_removals_until_fixed(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    set_kinds(empty_repo, "bgu", "chore")  # a typo: kind-allowed-unknown
    report = upgrade(empty_repo, capsys=capsys)
    assert report["removed"] == [] and report["skipped"] == []
    assert installed_skills(empty_repo) == SKILLS
    assert withheld_notes(report) == [
        "kind resolution reports errors (run `taskrail validate`), so skills no longer wanted were left in place: "
        ".claude/skills/taskrail-bug/SKILL.md, .claude/skills/taskrail-feature/SKILL.md, .claude/skills/taskrail-spike/SKILL.md"
    ]
    manifest = json.loads((empty_repo / ".taskrail/installed.json").read_text())
    assert ".claude/skills/taskrail-bug/SKILL.md" in manifest["files"]

    set_kinds(empty_repo, "bug", "chore")
    fixed = upgrade(empty_repo, capsys=capsys)
    assert sorted(fixed["removed"]) == [".claude/skills/taskrail-feature/SKILL.md", ".claude/skills/taskrail-spike/SKILL.md"]
    assert withheld_notes(fixed) == []
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot", "taskrail-bug", "taskrail-chore"]


def test_kind_resolution_errors_still_install_from_the_resolved_kinds(empty_repo, capsys):
    seed_config(empty_repo, "bgu", "chore")
    report = init(empty_repo, "--integration", "claude", capsys=capsys)
    assert installed_skills(empty_repo) == ["taskrail", "taskrail-autopilot", "taskrail-chore"]
    assert withheld_notes(report) == []
