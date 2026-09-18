"""`[[backlog]].file` is optional and defaults to `TASKRAIL.md` (T099).

taskrail must not take `TODO.md`, the one name a consuming repository most likely already uses
for its own list. The key is required today, so no config that loads at all omits it: a default
cannot change what any existing repository does, which is what criterion 2 and
`test_a_repository_that_names_its_file_is_untouched_by_init_and_upgrade` pin down.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import BASE_TODO, git

from taskrail.cli import main
from taskrail.config import DEFAULT_BACKLOG_FILE, load_config
from taskrail.install import DEFAULT_BACKLOG

MINIMAL = 'version = "v0.1.0"\n\n[[backlog]]\nname = "main"\nprefix = "T"\n'


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def empty_repo(tmp_path, monkeypatch):
    for key, value in {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
    }.items():
        monkeypatch.setenv(key, value)
    git(tmp_path, "init", "-q", "-b", "main")
    return tmp_path


def snapshot(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git/" not in str(p)}


# 1. `file` is optional and defaults to TASKRAIL.md.
def test_a_backlog_without_a_file_key_defaults_to_taskrail_md(tmp_path, capsys):
    write(tmp_path, ".taskrail/config.toml", MINIMAL)
    write(tmp_path, DEFAULT_BACKLOG_FILE, BASE_TODO)
    assert DEFAULT_BACKLOG_FILE == "TASKRAIL.md"
    assert load_config(tmp_path).backlogs[0].file == "TASKRAIL.md"
    code, out, err = run(tmp_path, "validate", capsys=capsys)
    assert code == 0, out + err
    code, out, _ = run(tmp_path, "show", "T002", "--json", capsys=capsys)
    assert json.loads(out)["file"] == "TASKRAIL.md"


# 2. A named `file` keeps its value; no default is applied over it.
def test_a_named_file_keeps_its_value(tmp_path, capsys):
    write(tmp_path, ".taskrail/config.toml", MINIMAL + 'file = "TODO.md"\n')
    write(tmp_path, "TODO.md", BASE_TODO)
    assert load_config(tmp_path).backlogs[0].file == "TODO.md"
    assert run(tmp_path, "validate", capsys=capsys)[0] == 0
    assert not (tmp_path / DEFAULT_BACKLOG_FILE).exists()


# 3. `init` seeds the key and the file under the new name.
def test_init_seeds_taskrail_md_and_names_it_in_the_config(empty_repo, capsys):
    code, out, err = run(empty_repo, "init", "--json", capsys=capsys)
    assert code == 0, err
    report = json.loads(out)
    assert "TASKRAIL.md" in report["created"]
    assert "TODO.md" not in report["created"]
    assert not (empty_repo / "TODO.md").exists()
    config = (empty_repo / ".taskrail/config.toml").read_text(encoding="utf-8")
    assert 'file = "TASKRAIL.md"' in config
    assert "TODO.md" not in config
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0


# 4. A repository that names TODO.md is untouched by `init`, and 5. by `upgrade`.
def test_a_repository_that_names_its_file_is_untouched_by_init_and_upgrade(empty_repo, capsys):
    write(empty_repo, ".taskrail/config.toml", MINIMAL + 'file = "TODO.md"\n')
    write(empty_repo, "TODO.md", BASE_TODO)
    before = snapshot(empty_repo)

    code, out, err = run(empty_repo, "init", "--json", capsys=capsys)
    assert code == 0, err
    report = json.loads(out)
    assert report["created"] == [] or "TODO.md" not in report["created"]
    assert "TODO.md" in report["unchanged"] and ".taskrail/config.toml" in report["unchanged"]
    assert not (empty_repo / "TASKRAIL.md").exists()
    assert {p: p.read_bytes() for p in before} == before

    code, out, err = run(empty_repo, "upgrade", "--json", capsys=capsys)
    assert code == 0, err
    assert "TODO.md" in json.loads(out)["unchanged"]
    assert not (empty_repo / "TASKRAIL.md").exists()
    # `upgrade` rewrites only the version pin; the backlog file and its name are left alone.
    assert (empty_repo / "TODO.md").read_bytes() == before[empty_repo / "TODO.md"]
    assert 'file = "TODO.md"' in (empty_repo / ".taskrail/config.toml").read_text(encoding="utf-8")


# 5. `upgrade` re-seeds a configured backlog file only when it is missing.
def test_upgrade_re_seeds_a_backlog_file_only_when_it_is_missing(empty_repo, capsys):
    assert run(empty_repo, "init", "--json", capsys=capsys)[0] == 0
    backlog = empty_repo / "TASKRAIL.md"
    backlog.write_text(BASE_TODO, encoding="utf-8")
    assert run(empty_repo, "upgrade", "--json", capsys=capsys)[0] == 0
    assert backlog.read_text(encoding="utf-8") == BASE_TODO

    backlog.unlink()
    code, out, err = run(empty_repo, "upgrade", "--json", capsys=capsys)
    assert code == 0, err
    assert "TASKRAIL.md" in json.loads(out)["created"]
    assert backlog.read_text(encoding="utf-8") == DEFAULT_BACKLOG


# 6. Omitting `file` where no TASKRAIL.md exists is reported, not silently wrong.
def test_an_omitted_file_with_no_taskrail_md_reports_backlog_missing(tmp_path, capsys):
    write(tmp_path, ".taskrail/config.toml", MINIMAL)
    code, out, _ = run(tmp_path, "validate", capsys=capsys)
    assert code == 1
    assert "TASKRAIL.md: error: backlog `main` file does not exist [backlog-missing]" in out


# 7. `file` stays a name taskrail defines, so T094 warns about a misspelling of it.
def test_file_stays_a_known_key_and_a_misspelling_warns(tmp_path, capsys):
    write(tmp_path, ".taskrail/config.toml", MINIMAL + 'file = "TODO.md"\n')
    write(tmp_path, "TODO.md", BASE_TODO)
    code, out, _ = run(tmp_path, "validate", "--json", capsys=capsys)
    assert code == 0
    assert [i for i in json.loads(out)["issues"] if i["code"].startswith("config-unknown")] == []

    write(tmp_path, ".taskrail/config.toml", MINIMAL + 'fille = "TODO.md"\n')
    code, out, _ = run(tmp_path, "validate", capsys=capsys)
    assert code == 1  # not 2: the config loads, and the default file is simply not there
    assert "unknown key `fille`" in out and "did you mean `file`?" in out
    assert "TASKRAIL.md: error: backlog `main` file does not exist [backlog-missing]" in out


# 8. `init` leaves a repository's own TODO.md alone instead of adopting it.
def test_init_does_not_adopt_a_repositorys_own_todo_md(empty_repo, capsys):
    own = "# Our TODO\n\n- [ ] ship the thing\n- [ ] fix the other thing\n"
    write(empty_repo, "TODO.md", own)
    code, out, err = run(empty_repo, "init", "--json", capsys=capsys)
    assert code == 0, err
    report = json.loads(out)
    assert "TASKRAIL.md" in report["created"]
    assert "TODO.md" not in report["created"] and "TODO.md" not in report["unchanged"]
    assert (empty_repo / "TODO.md").read_text(encoding="utf-8") == own
    assert run(empty_repo, "validate", capsys=capsys)[0] == 0


def test_the_seeded_file_is_headed_backlog_not_todo():
    assert DEFAULT_BACKLOG.startswith("# Backlog\n")
    assert "TODO" not in DEFAULT_BACKLOG
