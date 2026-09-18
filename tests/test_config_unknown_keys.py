"""`.taskrail/config.toml` names taskrail does not define: warned about, never an error (T094)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from conftest import BASE_CONFIG

from taskrail.cli import main
from taskrail.config import load_config, unknown_names
from taskrail.install import default_config

DESIGN = Path(__file__).resolve().parents[1] / "DESIGN.md"


def run(repo, *argv, capsys):
    code = main(["--root", str(repo.root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def unknown(repo, config: str):
    """The unknown-name issues of `config`, as `validate` would report them."""
    repo.write(".taskrail/config.toml", config)
    _, issues = repo.load()
    return [i for i in issues if i.code.startswith("config-unknown")]


def design_example() -> dict:
    """The example config of DESIGN.md §4."""
    section = DESIGN.read_text(encoding="utf-8").split("## 4. Configuration")[1]
    return tomllib.loads(re.search(r"```toml\n(.*?)```", section, re.S).group(1))


def test_an_unknown_key_in_a_known_table_warns_naming_the_key_and_the_table(repo):
    issues = unknown(repo, BASE_CONFIG + '\n[git]\nnonsens = true\n')
    assert len(issues) == 1
    issue = issues[0]
    assert (issue.severity, issue.code) == ("warning", "config-unknown-key")
    assert (issue.file, issue.line) == (".taskrail/config.toml", None)
    assert "`nonsens`" in issue.message and "[git]" in issue.message
    assert "ignores it" in issue.message


def test_an_unknown_top_level_key_warns(repo):
    issues = unknown(repo, BASE_CONFIG.replace('version = "v0.1.0"', 'version = "v0.1.0"\nnonsens = 1'))
    assert [(i.code, "top-level" in i.message and "`nonsens`" in i.message) for i in issues] == [
        ("config-unknown-key", True)
    ]


def test_an_unknown_table_warns_once_and_is_not_descended_into(repo):
    issues = unknown(repo, BASE_CONFIG + '\n[nonsens]\nfirst = 1\nsecond = 2\n')
    assert len(issues) == 1
    assert issues[0].code == "config-unknown-table"
    assert "[nonsens]" in issues[0].message
    assert "first" not in issues[0].message


def test_an_unknown_key_in_a_repeatable_table_names_its_entry(repo):
    config = BASE_CONFIG.replace('file = "TODO.md"', 'file = "TODO.md"\nnonsens = 1') + (
        "\n[autopilot]\nenabled = true\n"
        "\n[[autopilot.group]]\nname = \"ui\"\nlimit = 1\nnonsens = 2\n"
        "\n[[autopilot.resource]]\nname = \"PORT\"\nvalues = [\"5433\"]\nnonsens = 3\n"
    )
    messages = [i.message for i in unknown(repo, config)]
    assert len(messages) == 3
    assert all("`nonsens`" in message for message in messages)
    assert any("[[backlog]] `main`" in message for message in messages)
    assert any("[[autopilot.group]] `ui`" in message for message in messages)
    assert any("[[autopilot.resource]] `PORT`" in message for message in messages)


def test_the_free_form_tables_never_warn(repo):
    config = BASE_CONFIG.replace('test = "pytest"', 'deploy-to-staging = "make deploy"\ntest = "pytest"').replace(
        "custom = []", 'custom = ["Owner"]\naliases = { Pts = "Size" }'
    )
    assert unknown(repo, config) == []


def test_nothing_taskrail_defines_warns(repo):
    """The two drift guards: the config `init` seeds and the example of DESIGN.md §4."""
    assert unknown(repo, default_config("main")) == []
    assert unknown_names(design_example()) == []


def test_an_unknown_key_is_never_an_error(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[git]\nnonsens = true\n')
    assert load_config(repo.root).warnings  # it loads: nothing raises
    code, out, _ = run(repo, "validate", capsys=capsys)
    assert code == 0
    assert "warning: unknown key `nonsens` in [git]" in out
    assert "0 error(s), 1 warning(s)" in out
    assert run(repo, "list", capsys=capsys)[0] == 0


def test_validate_json_reports_the_warning_and_stays_valid(repo, capsys):
    repo.write(".taskrail/config.toml", BASE_CONFIG + '\n[git]\nnonsens = true\n')
    code, out, _ = run(repo, "validate", "--json", capsys=capsys)
    data = json.loads(out)
    assert code == 0 and data["valid"] is True
    assert [i for i in data["issues"] if i["code"] == "config-unknown-key"] == [
        {
            "severity": "warning",
            "code": "config-unknown-key",
            "message": "unknown key `nonsens` in [git]; taskrail ignores it",
            "file": ".taskrail/config.toml",
            "line": None,
        }
    ]


def test_a_near_miss_suggests_the_key_it_missed(repo):
    issues = unknown(repo, BASE_CONFIG + '\n[git]\nclam_remote = ""\n')
    assert len(issues) == 1
    assert "did you mean `claim_remote`?" in issues[0].message


def test_a_config_taskrail_defines_adds_no_issue(repo):
    assert repo.load()[1] == []
