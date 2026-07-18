"""skillset add https://github.com/vivainio/agent-skills."""

from unittest.mock import patch

from skillset.commands import cmd_add

from .conftest import repo_skills


class TestAddWithGitHubUrl:
    def test_full_url(self, env):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="https://github.com/vivainio/agent-skills")

        skills_dir = env.home / ".claude" / "skills"
        installed = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        expected = repo_skills()
        assert expected
        assert expected.issubset(installed)

    def test_url_with_tree_subpath(self, env):
        with patch("builtins.input", return_value="y"):
            cmd_add(repo="https://github.com/vivainio/agent-skills/tree/main/extra-skills")

        skills_dir = env.home / ".claude" / "skills"
        installed = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        expected = repo_skills("extra-skills")
        assert expected
        assert expected.issubset(installed)
