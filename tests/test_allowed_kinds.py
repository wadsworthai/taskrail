"""`[kinds].allowed`: a repository restricts the task kinds it accepts (T018)."""

import json

import pytest
from conftest import BASE_CONFIG, BASE_TODO, git

from taskrail.cli import main
from taskrail.config import load_config
from taskrail.issues import ConfigError
from taskrail.kinds import load_kinds

LOCAL_KIND = 'name = "{name}"\nsummary = "x"\nskill = "{skill}"\n[[stage]]\nname = "a"\n'
# The base backlog without its `feature` task, so a repository allowing only bug and chore is valid.
TODO_WITHOUT_FEATURE = BASE_TODO.replace("| ⬜ | T002 | feature |", "| ⬜ | T002 | chore   |")


def allow(repo, *names: str, raw: str | None = None) -> None:
    table = raw if raw is not None else "[kinds]\nallowed = [" + ", ".join(f'"{n}"' for n in names) + "]\n"
    repo.write(".taskrail/config.toml", BASE_CONFIG + "\n" + table)


def run(root, *argv, capsys):
    code = main(["--root", str(root), *argv])
    out, err = capsys.readouterr()
    return code, out, err


def issues_with(repo, code):
    return [i for i in repo.load()[1] if i.code == code]


# 1. No [kinds] table: unchanged.
def test_without_kinds_table_every_defined_kind_is_allowed(repo):
    config = load_config(repo.root)
    assert config.allowed_kinds == ()
    kinds, issues = load_kinds(config)
    assert sorted(kinds) == ["bug", "chore", "feature", "spike"]
    assert issues == []
    assert repo.load()[1] == []


# 2. Only allowed kinds resolve; `kind list` shows only them.
def test_only_allowed_core_kinds_resolve(repo, capsys):
    allow(repo, "bug", "chore")
    kinds, issues = load_kinds(load_config(repo.root))
    assert sorted(kinds) == ["bug", "chore"]
    assert issues == []
    code, out, _ = run(repo.root, "kind", "list", "--json", capsys=capsys)
    assert code == 0
    assert [k["name"] for k in json.loads(out)] == ["bug", "chore"]


# 3. A task of a disallowed kind is its own error; undefined kinds stay `task-kind-unknown`.
def test_task_of_a_disallowed_kind_is_an_error_naming_the_allowed_kinds(repo, capsys):
    allow(repo, "chore", "bug")
    found = issues_with(repo, "task-kind-disallowed")
    assert len(found) == 1
    assert (found[0].file, found[0].line) == ("TODO.md", 16)
    assert "`feature`" in found[0].message
    assert "bug, chore" in found[0].message
    assert issues_with(repo, "task-kind-unknown") == []
    code, out, _ = run(repo.root, "validate", capsys=capsys)
    assert code == 1
    assert "task-kind-disallowed" in out


def test_closed_tasks_of_a_disallowed_kind_are_errors_too(repo):
    allow(repo, "bug", "feature")
    found = issues_with(repo, "task-kind-disallowed")
    assert [i.line for i in found] == [15]  # T001 is a done chore


def test_undefined_kind_is_still_unknown_with_an_allowlist(repo):
    allow(repo, "bug", "chore", "feature")
    repo.write("TODO.md", BASE_TODO.replace("| bug     |", "| story   |"))
    assert repo.codes() == ["task-kind-unknown"]


# 4. Local kinds follow the allowlist.
def test_allowed_local_kind_resolves_and_validates_its_tasks(repo):
    allow(repo, "chore", "research", "bug")
    repo.write(".taskrail/types/research/kind.toml", LOCAL_KIND.format(name="research", skill="do-research"))
    repo.write("TODO.md", BASE_TODO.replace("| ⬜ | T002 | feature |", "| ⬜ | T002 | research|"))
    project, issues = repo.load()
    assert issues == []
    assert sorted(project.kinds) == ["bug", "chore", "research"]
    assert project.kinds["research"].source == "local"


def test_local_kind_left_out_of_the_allowlist_is_excluded_with_a_warning(repo):
    allow(repo, "bug", "chore")
    repo.write("TODO.md", TODO_WITHOUT_FEATURE)
    repo.write(".taskrail/types/research/kind.toml", LOCAL_KIND.format(name="research", skill="do-research"))
    project, issues = repo.load()
    assert "research" not in project.kinds
    warnings = [i for i in issues if i.severity == "warning"]
    assert [i.code for i in warnings] == ["kind-not-allowed"]
    assert warnings[0].file == ".taskrail/types/research/kind.toml"
    assert [i for i in issues if i.severity == "error"] == []


# 5. Overrides follow the allowlist.
def test_override_of_a_disallowed_kind_is_excluded_with_a_warning(repo):
    allow(repo, "bug", "chore")
    repo.write("TODO.md", TODO_WITHOUT_FEATURE)
    repo.write(".taskrail/overrides/spike/kind.toml", LOCAL_KIND.format(name="spike", skill="my-spike"))
    project, issues = repo.load()
    assert "spike" not in project.kinds
    assert [(i.severity, i.code, i.file) for i in issues] == [
        ("warning", "kind-not-allowed", ".taskrail/overrides/spike/kind.toml")
    ]


def test_override_of_an_allowed_kind_still_replaces_it(repo):
    allow(repo, "bug", "chore")
    repo.write(".taskrail/overrides/bug/kind.toml", LOCAL_KIND.format(name="bug", skill="my-bug"))
    kinds, issues = load_kinds(load_config(repo.root))
    assert issues == []
    assert kinds["bug"].source == "override"
    assert kinds["bug"].skill == "my-bug"


# 6. A stale allowlist entry.
def test_allowed_name_that_no_layer_defines_is_an_error(repo):
    allow(repo, "bug", "chore", "feature", "spec")
    found = issues_with(repo, "kind-allowed-unknown")
    assert len(found) == 1
    assert "`spec`" in found[0].message


# 7. Configuration errors.
@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ('kinds = "bug"\n', "[kinds] must be a table"),
        ("[kinds]\nallowed = \"bug\"\n", "`allowed` must be list"),
        ("[kinds]\nallowed = []\n", "kinds.allowed must name at least one kind"),
        ("[kinds]\nallowed = [\"bug\", 3]\n", "kinds.allowed must be a list of kind names"),
        ("[kinds]\nallowed = [\"Bug\"]\n", "kinds.allowed must be a list of kind names"),
        ("[kinds]\nallowed = [\"bug\", \"bug\"]\n", "kinds.allowed names `bug` more than once"),
    ],
)
def test_malformed_kinds_table_is_a_configuration_error(repo, raw, message):
    if raw.startswith("kinds ="):
        repo.write(".taskrail/config.toml", raw + BASE_CONFIG)
    else:
        allow(repo, raw=raw)
    with pytest.raises(ConfigError) as caught:
        load_config(repo.root)
    assert message in str(caught.value)


# 8. `new` refuses a disallowed kind and writes nothing.
def test_new_with_a_disallowed_kind_writes_nothing(git_repo, capsys):
    allow(git_repo, "bug", "chore")
    git_repo.write("TODO.md", TODO_WITHOUT_FEATURE)
    before = (git_repo.root / "TODO.md").read_text()
    code, _, err = run(git_repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Refunds", capsys=capsys)
    assert code == 1
    assert "task-kind-disallowed" in err
    assert (git_repo.root / "TODO.md").read_text() == before


def test_new_in_a_workspace_with_a_disallowed_kind_refuses_before_branching(git_repo, capsys):
    allow(git_repo, "bug", "chore")
    git_repo.write("TODO.md", TODO_WITHOUT_FEATURE)
    git(git_repo.root, "add", "-A")
    git(git_repo.root, "commit", "-q", "-m", "allow bug and chore")
    code, _, err = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "feature", "--title", "Refunds", "--workspace", capsys=capsys
    )
    assert code == 2
    assert "kind `feature` is not allowed" in err
    assert git(git_repo.root, "branch", "--list") == "* main"
    assert not (git_repo.root / ".worktrees").exists()
    assert git(git_repo.root, "status", "--porcelain") == ""


def test_new_in_a_workspace_with_an_undefined_kind_says_it_is_not_defined(git_repo, capsys):
    allow(git_repo, "bug", "chore")
    git_repo.write("TODO.md", TODO_WITHOUT_FEATURE)
    code, _, err = run(
        git_repo.root, "new", "--epic", "E01", "--kind", "story", "--title", "Refunds", "--workspace", capsys=capsys
    )
    assert code == 2
    assert "kind `story` is not defined" in err
