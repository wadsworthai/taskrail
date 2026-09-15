"""T061: `[autopilot].read_first`, the documents the orchestrator reads first, apart from `governing`."""

import re

import pytest
from test_autopilot import ENABLED, commit_all, configure, pilot, row, run, start, status_of  # noqa: F401
from test_autopilot_skill import SKILL, flat, source
from test_install import empty_repo, init  # noqa: F401

from taskrail.config import AutopilotConfig, load_config
from taskrail.issues import ConfigError

# --- 1, 2. Configuration ---------------------------------------------------------------------------


def test_read_first_is_read_as_a_tuple(repo):
    configure(repo, ENABLED + 'read_first = ["CLAUDE.md", "docs/design"]\ngoverning = ["docs/adr"]\n')
    loaded = load_config(repo.root).autopilot
    assert loaded.read_first == ("CLAUDE.md", "docs/design")
    assert loaded.governing == ("docs/adr",)


@pytest.mark.parametrize("value", ['"CLAUDE.md"', '[""]', "[1]"])
def test_read_first_must_be_a_list_of_non_empty_strings(repo, value):
    configure(repo, ENABLED + f"read_first = {value}\n")
    with pytest.raises(ConfigError, match=re.escape("autopilot.read_first must be a list of non-empty strings")):
        load_config(repo.root)


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ("", ()),
        ('governing = ["docs/adr", "src/**/policy-*.py"]\n', ("docs/adr", "src/**/policy-*.py")),
        ('governing = ["docs/adr"]\nread_first = []\n', ()),
        ('governing = ["docs/adr"]\nread_first = ["CLAUDE.md"]\n', ("CLAUDE.md",)),
    ],
)
def test_an_absent_read_first_takes_the_governing_entries(repo, extra, expected):
    configure(repo, ENABLED + extra)
    assert load_config(repo.root).autopilot.read_first == expected
    assert AutopilotConfig().read_first == ()


# --- 3, 4. `autopilot status` ----------------------------------------------------------------------


def test_status_reports_read_first_and_the_missing_entries(pilot, capsys):
    (pilot.root / "docs" / "design").mkdir(parents=True)
    (pilot.root / "docs" / "design" / "index.md").write_text("x")
    (pilot.root / "CLAUDE.md").write_text("x")
    configure(pilot, ENABLED + 'read_first = ["CLAUDE.md", "docs/design", "docs/**/*.md", "GONE.md", "nothing/*.txt"]\n')
    report = status_of(pilot.root, capsys)
    assert report["runs"] == []
    assert report["read_first"] == ["CLAUDE.md", "docs/design", "docs/**/*.md", "GONE.md", "nothing/*.txt"]
    assert report["read_first_missing"] == ["GONE.md", "nothing/*.txt"]

    start(pilot.root, capsys)
    report = status_of(pilot.root, capsys)
    assert (report["read_first"][0], report["read_first_missing"]) == ("CLAUDE.md", ["GONE.md", "nothing/*.txt"])


def test_status_text_starts_with_read_first_lines(pilot, capsys):
    (pilot.root / "CLAUDE.md").write_text("x")
    configure(pilot, ENABLED + 'read_first = ["CLAUDE.md", "GONE.md"]\n')
    code, out, _ = run(pilot.root, "autopilot", "status", capsys=capsys)
    lines = out.splitlines()
    assert code == 0
    assert lines[:2] == ["read first: CLAUDE.md, GONE.md", "read first missing: GONE.md"]
    assert "no autopilot runs" in out

    configure(pilot, ENABLED + 'read_first = ["CLAUDE.md"]\n')
    run_id = start(pilot.root, capsys)
    out = run(pilot.root, "autopilot", "status", capsys=capsys)[1]
    assert out.splitlines()[0] == "read first: CLAUDE.md"
    assert "read first missing" not in out and f"run {run_id}" in out


def test_status_has_empty_read_first_lists_and_no_lines_without_entries(pilot, capsys):
    report = status_of(pilot.root, capsys)
    assert (report["read_first"], report["read_first_missing"]) == ([], [])
    out = run(pilot.root, "autopilot", "status", capsys=capsys)[1]
    assert "read first" not in out and "no autopilot runs" in out


# --- 5. Read-first documents never escalate --------------------------------------------------------


def test_a_touched_read_first_document_raises_no_escalation(pilot, capsys):
    configure(pilot, ENABLED + 'read_first = ["DESIGN.md"]\ngoverning = []\n')
    run_id = start(pilot.root, capsys)
    lane = pilot.lane("T003", run_id)
    (lane / "DESIGN.md").write_text("edited")
    commit_all(lane, "edit the design")
    found = row(status_of(pilot.root, capsys, run_id), "T003")
    assert "DESIGN.md" in found["touched"]
    assert (found["governing_touched"], found["escalation"]) == ([], [])


# --- 6. The skill names read_first, in the source and the installed copies -------------------------


def before_first_dispatch(text: str) -> str:
    return flat(re.search(r"^## Before the first dispatch$(.*?)^## ", text, re.MULTILINE | re.DOTALL).group(1))


def every_gate(text: str) -> str:
    return flat(re.search(r"^## Every gate$(.*?)^## ", text, re.MULTILINE | re.DOTALL).group(1))


def assert_skill_reads_read_first(skill: str, gate_review: str) -> None:
    section = before_first_dispatch(skill)
    assert "read the governing documents: the paths in `read_first`" in section
    assert "`read_first_missing`" in section
    assert "`[autopilot].governing` paths" not in section
    assert section.index("taskrail autopilot status --json") < section.index("read the governing documents")
    bullet = every_gate(gate_review)
    assert "governing documents first" in bullet and "`read_first`" in bullet
    assert "[autopilot].governing" not in bullet


def test_the_skill_source_reads_the_governing_documents_from_read_first():
    assert_skill_reads_read_first(source("SKILL.md"), source("references/gate-review.md"))


def test_the_installed_skill_copies_read_the_governing_documents_from_read_first(empty_repo, capsys):
    init(empty_repo, "--integration", "claude", capsys=capsys)
    installed = empty_repo / ".claude/skills" / SKILL
    assert_skill_reads_read_first(
        (installed / "SKILL.md").read_text(encoding="utf-8"),
        (installed / "references/gate-review.md").read_text(encoding="utf-8"),
    )
