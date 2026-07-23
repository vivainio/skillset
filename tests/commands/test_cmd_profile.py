"""Tests for the interactive profile command."""

from unittest.mock import patch

import pytest

from skillset.commands.profile import cmd_profile


def test_name_switches_directly(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("skillset.commands.profile.activate_profile", return_value=(3, 2)) as activate:
        cmd_profile("work")

    activate.assert_called_once_with("work")
    assert "Activated profile 'work'" in capsys.readouterr().out


def test_menu_can_save(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "work")
    with (
        patch("skillset.commands.profile.profile_names", return_value=[]),
        patch("skillset.commands.profile.active_profile", return_value=None),
        patch("skillset.commands.profile.select_one", return_value="Save current setup..."),
        patch("skillset.commands.profile.unmanaged_skill_names", return_value=[]),
        patch("skillset.commands.profile.save_profile", return_value=(2, [])) as save,
    ):
        cmd_profile()

    save.assert_called_once_with("work", include_unmanaged=False)


def test_save_can_include_unmanaged(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["work", "yes"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    with (
        patch("skillset.commands.profile.profile_names", return_value=[]),
        patch("skillset.commands.profile.active_profile", return_value=None),
        patch("skillset.commands.profile.select_one", return_value="Save current setup..."),
        patch("skillset.commands.profile.unmanaged_skill_names", return_value=["personal"]),
        patch("skillset.commands.profile.save_profile", return_value=(1, [])) as save,
    ):
        cmd_profile()

    save.assert_called_once_with("work", include_unmanaged=True)
