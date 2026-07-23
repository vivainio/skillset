"""Tests for skillset.manifest.get_install_options."""

from pathlib import Path

from skillset.manifest import get_install_options


def test_returns_none_when_missing(home_dir: Path) -> None:
    assert get_install_options("nonexistent") is None
