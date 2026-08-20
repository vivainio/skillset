"""Tests for skillset.paths.get_claude_home and its effect on dependent paths."""

from pathlib import Path

import pytest

from skillset.paths import (
    abbrev,
    get_claude_home,
    get_global_agents_dir,
    get_global_commands_dir,
    get_global_skills_dir,
    get_global_skillset_path,
    get_profile_store_dir,
    get_profiles_path,
)


def test_defaults_to_home_dot_claude(home_dir: Path) -> None:
    assert get_claude_home() == home_dir / ".claude"


def test_honors_claude_config_dir_override(
    home_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "profile-b"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(override))
    assert get_claude_home() == override


def test_override_expands_user(home_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Path.expanduser() reads $HOME directly, not Path.home(), so set both.
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "~/other-profile")
    assert get_claude_home() == home_dir / "other-profile"


@pytest.mark.parametrize(
    "getter, suffix",
    [
        (get_global_skills_dir, "skills"),
        (get_global_commands_dir, "commands"),
        (get_global_agents_dir, "agents"),
        (get_global_skillset_path, "skillset.yaml"),
        (get_profiles_path, ".skillset/profiles.yaml"),
        (get_profile_store_dir, ".skillset/skills"),
    ],
)
def test_dependent_paths_follow_override(
    home_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    getter,
    suffix: str,
) -> None:
    override = tmp_path / "profile-b"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(override))
    assert getter() == override / suffix


def test_abbrev_shows_real_path_under_override(
    home_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "profile-b"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(override))
    # override lives under home_dir (== tmp_path), so it still gets `~`-shortened.
    assert abbrev(override / "skills" / "foo") == "~/profile-b/skills/foo"


def test_abbrev_shows_full_path_for_override_outside_home(
    home_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = Path("/elsewhere/profile-b")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(outside))
    assert abbrev(outside / "skills" / "foo") == str(outside / "skills" / "foo")


def test_abbrev_falls_back_to_home_without_override(home_dir: Path) -> None:
    assert abbrev(home_dir / ".claude" / "skills") == "~/.claude/skills"
