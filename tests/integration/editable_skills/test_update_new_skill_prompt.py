"""After removing a skill entry from a local yaml, update reports it -- no prompt."""

import pytest

from skillset.commands import cmd_add, cmd_update
from skillset.paths import load_skillset
from tests.support import LocalEnv

from .conftest import FIXTURES, remove_skill_from_toml


class TestLocalUpdateUntrackedSkill:
    def _setup(self, local_env: LocalEnv) -> None:
        """Add two editable skills (gamma marked disabled), then drop gamma from yaml."""
        cmd_add(repo=str(FIXTURES), skills=["alpha", "beta"])

        data = load_skillset(local_env.toml_path)
        entry = data["skills"]["editable_skills/fixtures"]
        assert "alpha" in entry["enabled"] and "beta" in entry["enabled"]
        assert "gamma" in entry["disabled"]

        remove_skill_from_toml(local_env.toml_path, "gamma")
        data = load_skillset(local_env.toml_path)
        entry = data["skills"]["editable_skills/fixtures"]
        assert "gamma" not in entry.get("enabled", [])
        assert "gamma" not in entry.get("disabled", [])

    def test_reported_not_prompted(
        self, local_env: LocalEnv, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Default local update reports gamma without prompting or touching yaml."""
        self._setup(local_env)

        # No input patch: any input() call would raise under pytest.
        cmd_update(file=str(local_env.toml_path))

        assert not (local_env.skills_dir / "gamma" / "SKILL.md").exists()
        data = load_skillset(local_env.toml_path)
        entry = data["skills"]["editable_skills/fixtures"]
        assert "gamma" not in entry.get("enabled", [])
        assert "gamma" not in entry.get("disabled", [])

        output = capsys.readouterr().out
        assert "New skills available" in output
        assert "gamma" in output

    def test_yes_accepts_new_skill(self, local_env: LocalEnv) -> None:
        """--yes links gamma and appends it to enabled."""
        self._setup(local_env)

        cmd_update(file=str(local_env.toml_path), new="yes")

        assert (local_env.skills_dir / "gamma").exists()
        data = load_skillset(local_env.toml_path)
        entry = data["skills"]["editable_skills/fixtures"]
        assert entry["editable"] is True
        assert "alpha" in entry["enabled"]
        assert "gamma" in entry["enabled"]

    def test_no_rejects_new_skill(
        self, local_env: LocalEnv, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--no keeps gamma unlinked and appends it to disabled."""
        self._setup(local_env)

        cmd_update(file=str(local_env.toml_path), new="no")

        assert not (local_env.skills_dir / "gamma" / "SKILL.md").exists()
        data = load_skillset(local_env.toml_path)
        entry = data["skills"]["editable_skills/fixtures"]
        assert "gamma" in entry.get("disabled", [])

        output = capsys.readouterr().out
        assert "skipped" in output

    def test_existing_skills_preserved(self, local_env: LocalEnv) -> None:
        """Alpha and beta remain linked regardless of gamma handling."""
        self._setup(local_env)

        cmd_update(file=str(local_env.toml_path))

        assert (local_env.skills_dir / "alpha").exists()
        assert (local_env.skills_dir / "beta").exists()
