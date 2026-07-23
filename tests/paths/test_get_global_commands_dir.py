"""Tests for skillset.paths.get_global_commands_dir."""

from pathlib import Path

from skillset.paths import get_global_commands_dir


def test_returns_commands_dir_under_home(home_dir: Path) -> None:
    assert get_global_commands_dir() == home_dir / ".claude" / "commands"
