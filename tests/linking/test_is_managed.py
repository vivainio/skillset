"""Tests for skillset.linking.is_managed."""

from pathlib import Path

from skillset.linking import SKILLSET_SOURCE_MARKER, is_managed


def test_symlink_is_managed(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)

    assert is_managed(link) is True


def test_managed_copy_is_managed(tmp_path: Path) -> None:
    d = tmp_path / "skill"
    d.mkdir()
    (d / SKILLSET_SOURCE_MARKER).write_text("source\n")
    assert is_managed(d) is True


def test_regular_dir_not_managed(tmp_path: Path) -> None:
    d = tmp_path / "regular"
    d.mkdir()
    assert is_managed(d) is False
