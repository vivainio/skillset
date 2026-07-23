"""Tests for skillset.linking.link_commands."""

from pathlib import Path

import pytest

from skillset.linking import link_commands


def test_copy_mode(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    linked = link_commands(skill_repo, target, copy=True)
    assert "do-thing.md" in linked
    assert (target / "do-thing.md").exists()


def test_symlink_mode(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    linked = link_commands(skill_repo, target)
    assert "do-thing.md" in linked
    assert (target / "do-thing.md").is_symlink()


def test_replaces_existing_symlink(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    link_commands(skill_repo, target)
    # Re-link replaces existing
    linked = link_commands(skill_repo, target)
    assert "do-thing.md" in linked


def test_skips_non_link_existing(
    skill_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "commands"
    target.mkdir(parents=True)
    (target / "do-thing.md").write_text("manual file")

    linked = link_commands(skill_repo, target)
    assert "do-thing.md" not in linked
    output = capsys.readouterr().out
    assert "not a link" in output


def test_copy_replaces_existing_file(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    target.mkdir(parents=True)
    (target / "do-thing.md").write_text("old content")

    linked = link_commands(skill_repo, target, copy=True)
    assert "do-thing.md" in linked


def test_existing_only(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    # First link to create files
    link_commands(skill_repo, target)
    # existing_only re-links only what's there
    linked = link_commands(skill_repo, target, existing_only=True)
    assert "do-thing.md" in linked


def test_existing_only_empty(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    target.mkdir(parents=True)
    linked = link_commands(skill_repo, target, existing_only=True)
    assert linked == []


def test_with_filter(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    linked = link_commands(skill_repo, target, only={"do-thing.md"})
    assert "do-thing.md" in linked


def test_filter_excludes(skill_repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "commands"
    linked = link_commands(skill_repo, target, only={"nonexistent.md"})
    assert linked == []


def test_existing_only_with_only_set(skill_repo: Path, tmp_path: Path) -> None:
    """existing_only intersects with the explicit only set."""
    target = tmp_path / "commands"
    target.mkdir(parents=True)
    # Create an existing file
    (target / "do-thing.md").symlink_to(skill_repo / "commands" / "do-thing.md")

    linked = link_commands(
        skill_repo, target, only={"do-thing.md", "nonexistent.md"}, existing_only=True
    )
    assert "do-thing.md" in linked
