"""Tests for skillset.manifest.load_manifest."""

from pathlib import Path

from skillset.manifest import load_manifest


def test_returns_empty_when_no_file(home_dir: Path) -> None:
    assert load_manifest() == {}
