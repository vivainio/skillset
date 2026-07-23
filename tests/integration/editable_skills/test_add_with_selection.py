"""skillset add /path -s alpha -- selective editable add."""

from skillset.commands import cmd_add
from skillset.paths import load_skillset
from tests.support import LocalEnv

from .conftest import FIXTURES, installed_skills


class TestAddEditableWithSelection:
    def test_only_selected_skill_linked(self, local_env: LocalEnv) -> None:
        cmd_add(repo=str(FIXTURES), skills=["alpha"])

        assert installed_skills(local_env.skills_dir) == {"alpha"}

    def test_toml_has_enabled_and_disabled_lists(self, local_env: LocalEnv) -> None:
        cmd_add(repo=str(FIXTURES), skills=["alpha"])

        data = load_skillset(local_env.toml_path)
        entry = next(iter(data["skills"].values()))
        assert list(entry["enabled"]) == ["alpha"]
        assert set(entry["disabled"]) == {"beta", "gamma"}

    def test_toml_has_editable_and_source(self, local_env: LocalEnv) -> None:
        cmd_add(repo=str(FIXTURES), skills=["alpha"])

        data = load_skillset(local_env.toml_path)
        entry = next(iter(data["skills"].values()))
        assert entry["editable"] is True
        assert entry["source"] == str(FIXTURES)

    def test_multiple_selected(self, local_env: LocalEnv) -> None:
        cmd_add(repo=str(FIXTURES), skills=["alpha", "gamma"])

        assert installed_skills(local_env.skills_dir) == {"alpha", "gamma"}
        data = load_skillset(local_env.toml_path)
        entry = next(iter(data["skills"].values()))
        assert set(entry["enabled"]) == {"alpha", "gamma"}
        assert list(entry["disabled"]) == ["beta"]
