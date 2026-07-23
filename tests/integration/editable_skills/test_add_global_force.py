"""skillset add /path -e -g -- force global install even with local skillset.toml."""

from unittest.mock import patch

from skillset.commands import cmd_add
from tests.support import LocalEnv

from .conftest import ALL_SKILLS, FIXTURES, installed_skills


class TestAddGlobalForce:
    def test_global_flag_installs_to_global_dir(self, local_env: LocalEnv) -> None:
        """With -g, skills go to global dir even when local skillset.toml exists."""
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), g=True)

        global_skills = local_env.home / ".claude" / "skills"
        assert ALL_SKILLS.issubset(installed_skills(global_skills))

        assert not local_env.skills_dir.exists() or not any(local_env.skills_dir.iterdir())
