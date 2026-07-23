"""Tests for skillset.linking.remove_link."""

from pathlib import Path

from skillset.linking import remove_link


def test_removes_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)

    remove_link(link)
    assert not link.exists()
    assert target.exists()  # target preserved
