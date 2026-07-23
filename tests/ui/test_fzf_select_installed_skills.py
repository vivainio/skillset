"""Tests for the installed-skill removal picker."""

from pathlib import Path
from unittest.mock import patch

import pytest

from skillset.ui import fzf_select_installed_skills


def test_groups_skills_by_source_location(tmp_path: Path) -> None:
    source_a = tmp_path / "a"
    source_b = tmp_path / "b"
    (source_a / "alpha").mkdir(parents=True)
    (source_b / "zulu").mkdir(parents=True)
    installed = tmp_path / "installed"
    installed.mkdir()
    skill_z = installed / "zulu"
    skill_a = installed / "alpha"
    skill_z.symlink_to(source_b / "zulu")
    skill_a.symlink_to(source_a / "alpha")

    def select(items: list[str], prompt: str, preserve_order: bool) -> list[str]:
        assert items == [
            f"# {source_a}",
            "  alpha",
            f"# {source_b}",
            "  zulu",
        ]
        assert prompt == "Remove skills> "
        assert preserve_order is True
        return [items[2], items[3]]

    with patch("skillset.ui.fzf_select", side_effect=select):
        result = fzf_select_installed_skills([skill_z, skill_a], prompt="Remove skills> ")

    assert result == ["zulu"]


def test_groups_unmanaged_skills_separately(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "managed").mkdir(parents=True)
    installed = tmp_path / "installed"
    installed.mkdir()
    managed = installed / "managed"
    managed.symlink_to(source / "managed")
    unmanaged = installed / "personal"
    unmanaged.mkdir()

    def select(items: list[str], prompt: str, preserve_order: bool) -> list[str]:
        assert items == [
            f"# {source}",
            "  managed",
            "# Unmanaged",
            "  personal",
        ]
        return [items[2], items[3]]

    with patch("skillset.ui.fzf_select", side_effect=select):
        result = fzf_select_installed_skills(
            [unmanaged, managed],
            prompt="Remove skills> ",
        )

    assert result == ["personal"]


def test_groups_profile_stored_skills_as_unmanaged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    stored = store / "personal"
    stored.mkdir(parents=True)
    installed = tmp_path / "installed"
    installed.mkdir()
    personal = installed / "personal"
    personal.symlink_to(stored)
    monkeypatch.setattr("skillset.ui.get_profile_store_dir", lambda: store)

    def select(items: list[str], prompt: str, preserve_order: bool) -> list[str]:
        assert items == ["# Unmanaged", "  personal"]
        return [items[1]]

    with patch("skillset.ui.fzf_select", side_effect=select):
        result = fzf_select_installed_skills([personal], prompt="Remove skills> ")

    assert result == ["personal"]
