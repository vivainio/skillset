"""Tests for skillset.paths.get_global_skills_dir."""

from pathlib import Path

from skillset.paths import get_global_skills_dir


def test_returns_skills_dir_under_home(home_dir: Path) -> None:
    assert get_global_skills_dir() == home_dir / ".claude" / "skills"
