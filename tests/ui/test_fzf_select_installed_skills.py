"""Tests for the installed-skill removal picker."""

from unittest.mock import patch

from skillset.ui import fzf_select_installed_skills


def test_groups_skills_by_source_location(tmp_path):
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

    def select(items, prompt, preserve_order):
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
