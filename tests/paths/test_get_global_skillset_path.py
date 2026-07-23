"""Tests for skillset.paths.get_global_skillset_path."""

from pathlib import Path

from skillset.paths import get_global_skillset_path


def test_returns_skillset_yaml_under_home(home_dir: Path) -> None:
    assert get_global_skillset_path() == home_dir / ".claude" / "skillset.yaml"
