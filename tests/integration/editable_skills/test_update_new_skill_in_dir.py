"""New skills appear in the editable directory.

Simulates the scenario where someone adds new skills to a shared
editable skills repo and the user runs `skillset update`.

Local skillset.yaml: never prompts -- new skills are only reported,
unless --yes/--no is passed explicitly. Global: interactive a/i/s menu.
"""

import shutil
from unittest.mock import patch

import pytest

from skillset.commands import cmd_update
from skillset.paths import load_skillset

from .conftest import FIXTURES, installed_skills


@pytest.fixture
def editable_dir(tmp_path):
    """Copy fixtures to a mutable dir and return it."""
    d = tmp_path / "editable-skills"
    shutil.copytree(FIXTURES, d)
    return d


def _toml_text(editable_dir):
    return (
        "skills:\n"
        "  editable-skills:\n"
        "    editable: true\n"
        f"    source: {editable_dir}\n"
        "    enabled: [alpha, beta, gamma]\n"
    )


class TestUpdateNewSkillLocal:
    """Local skillset.yaml -- no interactive suggestions, ever."""

    def _setup(self, local_env, editable_dir):
        """Install all three original skills, then add two new ones to the dir."""
        local_env.toml_path.write_text(_toml_text(editable_dir))

        cmd_update(file=str(local_env.toml_path))
        assert installed_skills(local_env.skills_dir) == {"alpha", "beta", "gamma"}

        for name in ("delta", "epsilon"):
            skill_dir = editable_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")

    def test_no_prompt_only_report(self, local_env, editable_dir, capsys):
        """Default local update reports new skills without prompting or linking."""
        self._setup(local_env, editable_dir)
        toml_before = local_env.toml_path.read_text()

        # No input patch: any input() call would raise under pytest.
        cmd_update(file=str(local_env.toml_path))

        installed = installed_skills(local_env.skills_dir)
        assert "delta" not in installed
        assert "epsilon" not in installed

        # Yaml untouched -- it is a declaration, not a negotiation.
        assert local_env.toml_path.read_text() == toml_before

        output = capsys.readouterr().out
        assert "New skills available" in output
        assert "delta" in output
        assert "epsilon" in output

    def test_yes_adds_all(self, local_env, editable_dir):
        """Explicit --yes links new skills and appends them to enabled."""
        self._setup(local_env, editable_dir)

        cmd_update(file=str(local_env.toml_path), new="yes")

        installed = installed_skills(local_env.skills_dir)
        assert "delta" in installed
        assert "epsilon" in installed

        data = load_skillset(local_env.toml_path)
        enabled = list(data["skills"]["editable-skills"]["enabled"])
        assert "delta" in enabled
        assert "epsilon" in enabled
        assert "alpha" in enabled

    def test_no_ignores_all(self, local_env, editable_dir):
        """Explicit --no skips new skills and appends them to disabled."""
        self._setup(local_env, editable_dir)

        cmd_update(file=str(local_env.toml_path), new="no")

        installed = installed_skills(local_env.skills_dir)
        assert "delta" not in installed
        assert "epsilon" not in installed

        data = load_skillset(local_env.toml_path)
        disabled = list(data["skills"]["editable-skills"]["disabled"])
        assert "delta" in disabled
        assert "epsilon" in disabled

    def test_original_skills_preserved(self, local_env, editable_dir):
        """Original skills remain linked regardless of new skill handling."""
        self._setup(local_env, editable_dir)

        cmd_update(file=str(local_env.toml_path))

        for skill in ("alpha", "beta", "gamma"):
            assert (local_env.skills_dir / skill).exists()


class TestUpdateNewSkillGlobal:
    """Global skillset.yaml keeps the interactive a/i/s menu."""

    def _setup(self, env, editable_dir):
        toml_path = env.home / ".claude" / "skillset.yaml"
        toml_path.write_text(_toml_text(editable_dir))

        cmd_update(g=True)
        skills_dir = env.home / ".claude" / "skills"
        assert installed_skills(skills_dir) == {"alpha", "beta", "gamma"}

        for name in ("delta", "epsilon"):
            skill_dir = editable_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        return toml_path, skills_dir

    def test_add_all(self, env, editable_dir, capsys):
        """User chooses 'a' -- both new skills linked and appended to enabled."""
        toml_path, skills_dir = self._setup(env, editable_dir)

        with patch("builtins.input", return_value="a"):
            cmd_update(g=True)

        installed = installed_skills(skills_dir)
        assert "delta" in installed
        assert "epsilon" in installed

        data = load_skillset(toml_path)
        enabled = list(data["skills"]["editable-skills"]["enabled"])
        assert "delta" in enabled
        assert "epsilon" in enabled

        output = capsys.readouterr().out
        assert "New skills detected" in output
        assert "2 new skill(s)" in output

    def test_ignore_all(self, env, editable_dir, capsys):
        """User chooses 'i' -- neither new skill linked, appended to disabled."""
        toml_path, skills_dir = self._setup(env, editable_dir)

        with patch("builtins.input", return_value="i"):
            cmd_update(g=True)

        installed = installed_skills(skills_dir)
        assert "delta" not in installed
        assert "epsilon" not in installed

        data = load_skillset(toml_path)
        disabled = list(data["skills"]["editable-skills"].get("disabled", []))
        assert "delta" in disabled
        assert "epsilon" in disabled

        output = capsys.readouterr().out
        assert "skipped" in output

    def test_select_individually(self, env, editable_dir):
        """User chooses 's', then accepts delta and rejects epsilon."""
        toml_path, skills_dir = self._setup(env, editable_dir)

        responses = iter(["s", "y", "n"])
        with patch("builtins.input", side_effect=responses):
            cmd_update(g=True)

        installed = installed_skills(skills_dir)
        assert "delta" in installed
        assert "epsilon" not in installed

        data = load_skillset(toml_path)
        entry = data["skills"]["editable-skills"]
        assert "delta" in entry["enabled"]
        assert "epsilon" in entry.get("disabled", [])
