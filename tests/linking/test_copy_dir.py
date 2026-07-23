"""Tests for skillset.linking.copy_dir."""

from pathlib import Path

from skillset.linking import SKILLSET_SOURCE_MARKER, copy_dir, is_managed_copy


def test_copies_with_marker(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("hello")

    dst = tmp_path / "dst"
    copy_dir(src, dst, source_label="test/repo")

    assert (dst / "file.txt").read_text() == "hello"
    assert (dst / SKILLSET_SOURCE_MARKER).read_text().strip() == "test/repo"
    assert is_managed_copy(dst) is True


def test_overwrites_existing(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("new content")

    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "old.txt").write_text("old content")

    copy_dir(src, dst, source_label="test/repo")

    assert (dst / "file.txt").read_text() == "new content"
    assert not (dst / "old.txt").exists()
    assert is_managed_copy(dst) is True
