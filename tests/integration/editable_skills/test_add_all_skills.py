"""skillset add /path -- add all, then yaml uses enabled: ['*']."""

from unittest.mock import patch

from skillset.commands import cmd_add
from skillset.paths import load_skillset
from tests.support import LocalEnv

from .conftest import ALL_SKILLS, FIXTURES, installed_skills


class TestAddEditableAllSkills:
    def test_all_skills_linked(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES))

        assert ALL_SKILLS.issubset(installed_skills(local_env.skills_dir))

    def test_toml_lists_all_as_wildcard(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES))

        data = load_skillset(local_env.toml_path)
        entry = next(iter(data["skills"].values()))
        assert list(entry["enabled"]) == ["*"]
        assert "disabled" not in entry
