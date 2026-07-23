"""Tests for skillset.discovery.find_commands."""

from pathlib import Path

from skillset.discovery import find_commands


def test_finds_command_files(skill_repo: Path) -> None:
    commands = find_commands(skill_repo)
    names = [c.name for c in commands]
    assert "do-thing.md" in names


def test_finds_nested_commands(tmp_path: Path) -> None:
    nested = tmp_path / "commands" / "sub"
    nested.mkdir(parents=True)
    (nested / "nested-cmd.md").write_text("# cmd\n")
    (tmp_path / "commands" / "top-cmd.md").write_text("# cmd\n")

    commands = find_commands(tmp_path)
    names = sorted(c.name for c in commands)
    assert "nested-cmd.md" in names
    assert "top-cmd.md" in names


def test_excludes_hidden_directories(tmp_path: Path) -> None:
    hidden = tmp_path / ".hidden" / "commands"
    hidden.mkdir(parents=True)
    (hidden / "secret-cmd.md").write_text("# secret\n")

    # Also add a visible command so the function runs
    visible = tmp_path / "commands"
    visible.mkdir()
    (visible / "visible-cmd.md").write_text("# visible\n")

    commands = find_commands(tmp_path)
    names = [c.name for c in commands]
    assert "secret-cmd.md" not in names
    assert "visible-cmd.md" in names


def test_returns_empty_for_no_commands(tmp_path: Path) -> None:
    assert find_commands(tmp_path) == []
