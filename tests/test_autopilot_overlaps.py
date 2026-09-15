"""`overlaps` and `known_overlaps` in `autopilot status`: files of the known conflict classes apart (T051)."""

import json

from conftest import git
from test_autopilot import commit_all, pilot, row, run, start, status_of  # noqa: F401

from taskrail import mergedriver
from taskrail.cli import main
from taskrail.config import load_config
from taskrail.project import load_project

DECISIONS_INDEX = "docs/autopilot/decisions/README.md"
MANIFEST = ".taskrail/installed.json"
SKILL_COPY = ".claude/skills/taskrail/SKILL.md"


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def append(root, path, text):
    target = root / path
    write(root, path, (target.read_text(encoding="utf-8") if target.exists() else "") + text)


def publish(pilot, message):
    """Commit the main checkout and push it, so lanes started from origin/main see it."""
    commit_all(pilot.root, message)
    git(pilot.root, "push", "-q", "origin", "main")


def two_lanes(pilot, capsys):
    run_id = start(pilot.root, capsys)
    return run_id, pilot.lane("T003", run_id), pilot.lane("T004", run_id)


def test_known_class_files_leave_overlaps_for_known_overlaps(pilot, capsys):
    write(pilot.root, "CHANGELOG.md", "# Changelog\n")
    publish(pilot, "changelog")
    run_id, first, second = two_lanes(pilot, capsys)
    for lane, task_id in ((first, "T003"), (second, "T004")):
        append(lane, "TODO.md", f"\n<!-- {task_id} -->\n")
        append(lane, "CHANGELOG.md", f"- {task_id}\n")
        append(lane, "docs/features/README.md", f"| {task_id} |\n")
        append(lane, DECISIONS_INDEX, f"| {task_id} |\n")
        write(lane, "shared.py", task_id)
        commit_all(lane, f"work {task_id}")
    write(first, "docs/bugs/README.md", "| T003 |\n")  # a known-class file only one lane touched

    report = status_of(pilot.root, capsys, run_id)
    assert "docs/bugs/README.md" in row(report, "T003")["touched"]
    assert report["overlaps"] == {"shared.py": ["T003", "T004"]}
    both = ["T003", "T004"]
    assert report["known_overlaps"] == {
        "CHANGELOG.md": {"class": "changelog", "tasks": both},
        "TODO.md": {"class": "backlog", "tasks": both},
        DECISIONS_INDEX: {"class": "index", "tasks": both},
        "docs/features/README.md": {"class": "index", "tasks": both},
    }


def test_an_epic_file_is_backlog_and_a_branch_only_changelog_is_changelog(pilot, capsys):
    assert main(["--root", str(pilot.root), "epic", "split", "E01"]) == 0
    publish(pilot, "split E01")
    epic_file = next(epic for epic in load_project(load_config(pilot.root))[0].backlogs[0].epics if epic.file).file
    run_id, first, second = two_lanes(pilot, capsys)
    for lane, task_id in ((first, "T003"), (second, "T004")):
        append(lane, epic_file, f"\n<!-- {task_id} -->\n")
        write(lane, "pkg/Changelog.md", f"- {task_id}\n")  # not tracked in the main checkout

    report = status_of(pilot.root, capsys, run_id)
    assert report["overlaps"] == {}
    assert report["known_overlaps"] == {
        epic_file: {"class": "backlog", "tasks": ["T003", "T004"]},
        "pkg/Changelog.md": {"class": "changelog", "tasks": ["T003", "T004"]},
    }


def test_the_manifest_and_the_copies_it_records_are_installed(pilot, capsys):
    write(pilot.root, MANIFEST, json.dumps({"version": "x", "files": {SKILL_COPY: "digest"}}))
    write(pilot.root, SKILL_COPY, "skill\n")
    publish(pilot, "install")
    run_id, first, second = two_lanes(pilot, capsys)
    for lane, task_id in ((first, "T003"), (second, "T004")):
        append(lane, SKILL_COPY, f"{task_id}\n")
        append(lane, MANIFEST, " ")

    report = status_of(pilot.root, capsys, run_id)
    assert report["overlaps"] == {}
    assert report["known_overlaps"] == {
        MANIFEST: {"class": "installed", "tasks": ["T003", "T004"]},
        SKILL_COPY: {"class": "installed", "tasks": ["T003", "T004"]},
    }

    write(pilot.root, MANIFEST, "<<<<<<< ours\n{}\n")  # unreadable: no installed paths, and no error
    report = status_of(pilot.root, capsys, run_id)
    assert report["overlaps"] == {MANIFEST: ["T003", "T004"], SKILL_COPY: ["T003", "T004"]}
    assert report["known_overlaps"] == {}


def test_text_lists_real_overlaps_before_known_ones(pilot, capsys):
    run_id, first, second = two_lanes(pilot, capsys)
    for lane, task_id in ((first, "T003"), (second, "T004")):
        append(lane, "TODO.md", f"\n<!-- {task_id} -->\n")

    code, out, _ = run(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)
    assert code == 0
    assert "files touched by more than one lane:" not in out
    assert "known conflict classes touched by more than one lane (resolved at hand-off):\n  TODO.md (backlog): T003, T004" in out

    write(first, "shared.py", "one")
    write(second, "shared.py", "two")
    code, out, _ = run(pilot.root, "autopilot", "status", "--run", run_id, capsys=capsys)
    lines = out.splitlines()
    real = lines.index("files touched by more than one lane:")
    known = lines.index("known conflict classes touched by more than one lane (resolved at hand-off):")
    assert real < known
    assert lines[real + 1] == "  shared.py: T003, T004"
    assert lines[known + 1] == "  TODO.md (backlog): T003, T004"


def test_the_merge_driver_paths_are_the_backlog_index_and_changelog_classes(pilot):
    write(pilot.root, "tools/CHANGELOG.md", "# Changelog\n")
    commit_all(pilot.root, "changelog")
    config = load_config(pilot.root)
    project, _ = load_project(config)
    known = mergedriver.known_conflict_paths(project)
    assert known["TODO.md"] == "backlog"
    assert known["docs/features/README.md"] == "index"
    assert known[DECISIONS_INDEX] == "index"
    assert known["tools/CHANGELOG.md"] == "changelog"
    assert set(known.values()) == {"backlog", "index", "changelog"}
    assert mergedriver.attribute_paths(config) == sorted(known)


def test_the_skill_tells_the_orchestrator_known_overlaps_are_expected():
    from test_autopilot_skill import flat, source

    text = source("SKILL.md")
    supervise = flat(text[text.index("## Supervise") : text.index("## Answer a gate")])
    assert "`overlaps`: compare them with the touch map" in supervise
    assert "`known_overlaps` are files of the known conflict classes: expected, and resolved at hand-off" in supervise
