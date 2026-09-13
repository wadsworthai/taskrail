from conftest import BASE_TODO

from taskrail.config import load_config
from taskrail.kinds import load_kinds

SPEC_KIND = """
name = "spec"
summary = "Specification-driven work."

[[route]]
when = { Spec = "—" }
skill = "new-spec"

[[route]]
when = { Spec = "*" }
skill = "amend-spec"

[[stage]]
name = "specify"
gate = "always"
"""


def test_core_kinds_load_cleanly(repo):
    kinds, issues = load_kinds(load_config(repo.root))
    assert sorted(kinds) == ["bug", "chore", "feature", "spike"]
    assert issues == []
    assert all(k.source == "core" for k in kinds.values())


def test_local_kind_routes_on_a_custom_column(repo):
    config = (repo.root / ".taskrail/config.toml").read_text().replace("custom = []", 'custom = ["Spec"]')
    repo.write(".taskrail/config.toml", config)
    repo.write(".taskrail/types/spec/kind.toml", SPEC_KIND)
    todo = BASE_TODO.replace("| Description |", "| Description | Spec |").replace(
        "|-------------|", "|-------------|------|"
    )
    todo = todo.replace("Base prices |", "Base prices | —    |")
    todo = todo.replace("| feature | 3   | T001       | Repricing      | Recompute   |", "| spec    | 3   | T001       | Repricing      | Recompute   | 0007 |")
    todo = todo.replace("Off by one  |", "Off by one  | —    |")
    repo.write("TODO.md", todo)
    project, issues = repo.load()
    assert issues == []
    assert project.kinds["spec"].skill_for(project.task("T002")) == "amend-spec"


def test_override_replaces_core_kind(repo):
    repo.write(
        ".taskrail/overrides/bug/kind.toml",
        'name = "bug"\nsummary = "Local bug flow."\nskill = "my-bug"\n[[stage]]\nname = "fix"\ngate = "always"\n',
    )
    kinds, _ = load_kinds(load_config(repo.root))
    assert kinds["bug"].source == "override"
    assert kinds["bug"].skill == "my-bug"


def test_override_for_unknown_kind_is_an_error(repo):
    repo.write(".taskrail/overrides/epic/kind.toml", 'name = "epic"\nsummary = "x"\nskill = "x"\n[[stage]]\nname = "a"\n')
    assert "override-unknown" in repo.codes()


def test_invalid_descriptor(repo):
    repo.write(
        ".taskrail/types/research/kind.toml",
        'name = "other"\nsummary = "x"\nbranch = "{ticket}"\n[[stage]]\nname = "a"\ngate = "sometimes"\n',
    )
    messages = [i.message for i in repo.load()[1] if i.code == "kind-invalid"]
    assert any("directory is `research`" in m for m in messages)
    assert any("unknown placeholder" in m for m in messages)
    assert any("gate must be one of" in m for m in messages)
    assert any("either `skill`" in m for m in messages)
