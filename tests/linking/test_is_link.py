"""Tests for skillset.linking.is_link."""

from pathlib import Path

from skillset.linking import is_link


def test_detects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)

    assert is_link(link) is True


def test_regular_dir_is_not_link(tmp_path: Path) -> None:
    d = tmp_path / "regular"
    d.mkdir()
    assert is_link(d) is False


def test_nonexistent_path(tmp_path: Path) -> None:
    assert is_link(tmp_path / "nope") is False
