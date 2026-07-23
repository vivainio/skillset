"""Tests for skillset.linking.is_managed_copy."""

from pathlib import Path

from skillset.linking import SKILLSET_SOURCE_MARKER, is_managed_copy


def test_detects_marker(tmp_path: Path) -> None:
    d = tmp_path / "skill"
    d.mkdir()
    (d / SKILLSET_SOURCE_MARKER).write_text("/some/path\n")
    assert is_managed_copy(d) is True


def test_no_marker(tmp_path: Path) -> None:
    d = tmp_path / "skill"
    d.mkdir()
    assert is_managed_copy(d) is False
