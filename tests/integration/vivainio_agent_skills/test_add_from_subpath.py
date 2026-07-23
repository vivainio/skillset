"""skillset add vivainio/agent-skills -p extra-skills -- skills from subdirectory."""

from unittest.mock import patch

from skillset.commands import cmd_add
from tests.support import Env

from .conftest import REPO, repo_skills, skills_outside


class TestAddFromSubpath:
    def test_subpath_installs_extra_skills(self, env: Env) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=REPO, subpath="extra-skills")

        skills_dir = env.home / ".claude" / "skills"
        installed = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        expected = repo_skills("extra-skills")
        assert expected
        assert expected.issubset(installed), f"Missing: {expected - installed}"

    def test_subpath_does_not_install_main_skills(self, env: Env) -> None:
        with patch("builtins.input", return_value="y"):
            cmd_add(repo=REPO, subpath="extra-skills")

        skills_dir = env.home / ".claude" / "skills"
        installed = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        unexpected = skills_outside("extra-skills") & installed
        assert not unexpected, f"Skills outside extra-skills should not be installed: {unexpected}"
