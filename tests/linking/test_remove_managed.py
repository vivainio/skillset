"""Tests for skillset.linking.remove_managed."""

from pathlib import Path

import pytest

from skillset.linking import SKILLSET_SOURCE_MARKER, remove_managed


def test_removes_managed_copy(tmp_path: Path) -> None:
    d = tmp_path / "skill"
    d.mkdir()
    (d / SKILLSET_SOURCE_MARKER).write_text("x\n")
    (d / "content.md").write_text("x")

    remove_managed(d)
    assert not d.exists()


def test_removes_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)

    remove_managed(link)
    assert not link.exists()
    assert target.exists()


def test_raises_for_unmanaged_path(tmp_path: Path) -> None:
    d = tmp_path / "regular"
    d.mkdir()

    with pytest.raises(ValueError, match="Not a managed path"):
        remove_managed(d)
