"""Tests for skillset.manifest.save_manifest."""

from pathlib import Path

from skillset.manifest import load_manifest, save_manifest


def test_round_trip(home_dir: Path) -> None:
    data = {"owner/repo": {"subpath": None, "copy": False, "scope": "global"}}
    save_manifest(data)
    assert load_manifest() == data
