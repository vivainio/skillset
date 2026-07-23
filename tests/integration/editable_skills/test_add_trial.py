"""skillset add /path -e --try -- trial mode does not write to toml, clean removes."""

from unittest.mock import patch

from skillset.commands import cmd_add, cmd_clean
from tests.support import LocalEnv

from .conftest import ALL_SKILLS, FIXTURES, installed_skills


class TestAddTrial:
    def test_trial_does_not_write_to_toml(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), trial=True)

        content = local_env.toml_path.read_text()
        assert "fixtures" not in content

    def test_trial_still_links_skills(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), trial=True)

        assert ALL_SKILLS.issubset(installed_skills(local_env.skills_dir))

    def test_clean_removes_trial_skills(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), trial=True)

        assert ALL_SKILLS.issubset(installed_skills(local_env.skills_dir))

        cmd_clean()

        remaining = installed_skills(local_env.skills_dir)
        assert not ALL_SKILLS & remaining

    def test_clean_does_not_delete_source_dir(self, local_env: LocalEnv) -> None:
        """Clean must not delete the editable source directory itself."""
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), trial=True)

        cmd_clean()

        assert FIXTURES.is_dir()
