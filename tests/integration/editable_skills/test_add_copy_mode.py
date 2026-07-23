"""skillset add /path -e --copy -- copies instead of symlinking."""

from unittest.mock import patch

import pytest

from skillset.commands import cmd_add
from tests.support import LocalEnv

from .conftest import ALL_SKILLS, FIXTURES, installed_skills


class TestAddCopyMode:
    def test_copy_creates_real_dirs(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), copy=True)

        for skill in ALL_SKILLS:
            skill_dir = local_env.skills_dir / skill
            if skill_dir.exists():
                assert skill_dir.is_dir()
                assert not skill_dir.is_symlink()

    def test_copy_output_says_copied(
        self, local_env: LocalEnv, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), copy=True)

        output = capsys.readouterr().out
        assert "Copied" in output

    def test_copy_installs_all_skills(self, local_env: LocalEnv) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=str(FIXTURES), copy=True)

        assert ALL_SKILLS.issubset(installed_skills(local_env.skills_dir))
